"""Run one inspection mission: headless (CSV + report) or with the live MuJoCo viewer.

macOS:  the interactive viewer must be started with  mjpython  (installed with the mujoco wheel):
          mjpython src/run_simulation.py --viewer --condition proposed --seed 7
        headless runs use plain python:
          python src/run_simulation.py --condition baseline --seed 7 --csv results/telemetry/demo_baseline.csv

Viewer extras
  * the module beacons turn  GREEN = inspected & healthy,  RED = flagged defective,  AMBER = shadow confounder rejected
  * the pace is real time (use --speed 4 to run 4x faster), the console prints every FSM event
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import mujoco
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "analytics"))

from solar_defect_detector import InspectionMission, MissionConfig  # noqa: E402

MODEL = os.path.join(ROOT, "models", "solar_defect_amr.xml")
GREEN, RED, AMBER = (0.1, 0.8, 0.2, 1), (0.95, 0.1, 0.1, 1), (1.0, 0.65, 0.0, 1)


def paint(m, name, rgba):
    gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, name)
    if gid >= 0:
        m.geom_matid[gid] = -1
        m.geom_rgba[gid] = rgba


def build_config(a) -> MissionConfig:
    from run_evaluation import make_config
    cfg = make_config(a.seed, a.condition)
    cfg.log_telemetry = a.csv is not None or not a.viewer or a.dashboard
    cfg.verbose = a.verbose
    if a.time_scale != 1.0:
        cfg.env.time_scale = a.time_scale
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["baseline", "proposed"], default="proposed")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--viewer", action="store_true")
    ap.add_argument("--speed", type=float, default=1.0, help="viewer pace multiplier (1 = real time)")
    ap.add_argument("--time-scale", type=float, default=1.0, help="sun/thermal time acceleration (demo only)")
    ap.add_argument("--csv", default=None, help="write the 500 Hz telemetry CSV here")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--dashboard", action="store_true", help="serve the live browser dashboard on http://127.0.0.1:8765/")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    cfg = build_config(a)
    mission = InspectionMission(cfg, MODEL)
    truth_ids = mission.gt.defect_panel_ids()
    print(f"seed {cfg.seed}  condition {cfg.condition}  weather {cfg.weather_label}  start {cfg.start_h:.2f} h  "
          f"{len(truth_ids)} hidden defects (not shown to the robot)")
    painted = set()
    dash = None
    if a.dashboard:
        from live_dashboard import LiveDashboard
        dash = LiveDashboard(mission, a.port, a.csv)
        print("live dashboard ->", dash.start(), " (open this in your browser)")

    if a.viewer:
        import mujoco.viewer as mv
        viewer = mv.launch_passive(mission.m, mission.d)
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
        viewer.cam.fixedcamid = mujoco.mj_name2id(mission.m, mujoco.mjtObj.mjOBJ_CAMERA, "overview")
        t_wall0 = time.time()
        last_ev = [0]

        def hook(ms):
            for rec in ms.detections:
                pid = rec["panel_id_est"]
                if pid not in painted:
                    painted.add(pid)
                    paint(ms.m, "MARK_" + pid, RED)
            for pid in set(ms.visited) - painted:
                paint(ms.m, "MARK_" + pid, GREEN)
            for e in ms.events[last_ev[0]:]:
                print(e)
            last_ev[0] = len(ms.events)
            if dash:
                dash.publish(ms)
            viewer.sync()
            lag = ms.d.time / a.speed - (time.time() - t_wall0)
            if lag > 0:
                time.sleep(min(lag, 0.05))
            return viewer.is_running()

        mission.hook = hook
        res = mission.run()
        viewer.close()
    else:
        if dash:
            def hook(ms):
                dash.publish(ms)
                lag = ms.d.time / a.speed - (time.time() - t_wall0)
                if lag > 0:
                    time.sleep(min(lag, 0.05))
                return True
            t_wall0 = time.time()
            mission.hook = hook
        res = mission.run()
        if dash:
            dash.publish(mission, finished=True)
            time.sleep(1.0)
        for e in res.events:
            print(e)

    print("\n=== mission report ===")
    m = res.metrics
    print(f"completed={bool(m['completed'])}  duration={m['duration_s']:.1f}s  wall={m['wall_s']:.1f}s  "
          f"time/MW={m['time_per_mw_h']:.2f} h/MW (scaled from the {mission.reg.cfg.farm_mw * 1000:.0f} kW test array)")
    print(f"found {m['tp']}/{m['n_defects']} defects, {m['fp']} false alarms, precision={m['precision']:.2f} recall={m['recall']:.2f}")
    print(f"tracking RMSE={m.get('track_rmse_m', float('nan')) * 100:.2f} cm  control effort={m['control_effort']:.0f}  "
          f"localisation error={m['loc_err_mean_m']:.2f} m")
    if a.csv and res.telemetry is not None:
        os.makedirs(os.path.dirname(os.path.abspath(a.csv)), exist_ok=True)
        res.telemetry.to_csv(a.csv)
        print("telemetry ->", a.csv, f"({res.telemetry.n} rows at 500 Hz)")


if __name__ == "__main__":
    main()
