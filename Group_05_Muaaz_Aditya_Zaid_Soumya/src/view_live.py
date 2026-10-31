#!/usr/bin/env python3
"""
Live interactive viewer of the dual-UAV patrol | MDRIIA Group 05 | Owner: E043 Muaaz

macOS requires mjpython for the passive viewer:
  mjpython src/view_live.py --policy offset_ring
  mjpython src/view_live.py --rays                    # FR-18 range-ring beams + nearest obstacle
  mjpython src/view_live.py --demo headon --rays      # the head-on separation encounter, handled
  mjpython src/view_live.py --demo headon --apf-only  # same encounter, guide APF alone (airframes touch)
  mjpython src/view_live.py --scene exterior --appear 25   # intruder early: watch DETECT -> ... -> TRACK
Windows / Linux:
  python src/view_live.py

Mouse: left-drag rotate, right-drag pan, scroll zoom, double-click a body to track it.
Press [ / ] in the viewer to cycle cameras (atrium, galleries, Wall of Fame, lifts,
cafeteria, VIP Lounge, chase and on-board cameras).

--rays draws every beam of both UAVs' range rings (green: free to the 8 m range limit,
amber: hit an obstacle) and marks the nearest obstacle return of each UAV with a red
beam and a red sphere at the hit point. Readings are the noisy values the controller uses.

FR-17 overlay (top-left, mujoco.viewer Handle.set_texts): each UAV's surveillance FSM state
(TAKEOFF / TRANSIT / DESCEND / PATROL / DETECT / VERIFY / ALERT_<tier> / TRACK / RETURN_TO_PATROL),
the mission state and alert status of the open incident, and the sim time. With --demo headon the
overlay also shows the live and minimum centre distance and whether the layered separation held.
Vision (the surveillance cameras + E051 detector) runs off-screen at VISION_HZ; if the off-screen
renderer cannot start next to the viewer, or E051's detector is a stub, the FSM stays in PATROL and
the overlay says why.
"""
import argparse
import os
import sys
import time

import mujoco
import numpy as np
from mujoco import viewer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aerial_patrol_swarm as aps   # noqa: E402

GREEN = np.array([0.2, 0.9, 0.3, 0.6], dtype=np.float32)
AMBER = np.array([1.0, 0.7, 0.1, 0.9], dtype=np.float32)
RED = np.array([1.0, 0.1, 0.1, 1.0], dtype=np.float32)


def fsm_overlay(ctl, extra=None):
    """Left / right text columns for the FR-17 overlay."""
    left, right = ["Alpha", "Bravo", "Mission", "Alert", "Vision", "t"], []
    right.append(ctl.uavs["alpha"]["fsm"])
    right.append(ctl.uavs["bravo"]["fsm"])
    right.append(getattr(ctl, "surv_state", "PATROL"))
    right.append(getattr(ctl, "alert_status", "-"))
    right.append(f"{ctl.vision_status} @ {ctl.vision_hz:g} Hz" if ctl.vision_enabled else "off")
    right.append(f"{ctl.current_time_s:7.2f} s")
    for k, v in (extra or []):
        left.append(k)
        right.append(v)
    return "\n".join(left), "\n".join(right)


def head_on_segment(model, span=60.0, alt=20.0):
    """60 m centre span of the patrol ring's east leg (patrol_cp5 -> patrol_cp6), inside the campus
    wall between the main building and the east wall -- as in tests/test_e043_separation.py."""
    a, b = (model.site_pos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, n)].copy()
            for n in ("patrol_cp5", "patrol_cp6"))
    a[2] = b[2] = alt
    u = (b - a) / np.linalg.norm(b - a)
    mid = (a + b) / 2.0
    return mid - u * span / 2.0, mid + u * span / 2.0


def setup_head_on(ctl):
    """The separation encounter of tests/test_e043_separation.py: 6 m/s each, same altitude, no wind."""
    A, B = ctl.uavs["alpha"], ctl.uavs["bravo"]
    p0, p1 = head_on_segment(ctl.model)
    for u, (s, e) in ((A, (p0, p1)), (B, (p1, p0))):
        ctl.data.qpos[u["qadr"]:u["qadr"] + 3] = s
        ctl.data.qpos[u["qadr"] + 3:u["qadr"] + 7] = (1, 0, 0, 0)
        u.update(phase="patrol", fsm="PATROL", route=[(e.copy(), None)] * 2, idx=0,
                 layer=0.0, home=s[:2].copy())
    mujoco.mj_forward(ctl.model, ctl.data)
    return (p0 + p1) / 2.0


def draw_rays(scn, ctl):
    scn.ngeom = 0
    for u in ctl.uavs.values():
        if u.get("rf") is None or u.get("rf_sids") is None:
            continue
        org = ctl.data.site_xpos[u["rf_sids"][0]]
        rf = u["rf"]
        near = int(np.argmin(rf)) if np.isfinite(rf).any() else -1
        for i, (r, dvec) in enumerate(zip(rf, u["rf_dirs"])):
            if scn.ngeom >= scn.maxgeom - 2:
                return
            hit = np.isfinite(r)
            end = org + dvec * (r if hit else ctl.RF_RANGE_M)
            color = RED if i == near else (AMBER if hit else GREEN)
            g = scn.geoms[scn.ngeom]
            mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_LINE, np.zeros(3), np.zeros(3), np.zeros(9), color)
            mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_LINE, 3.0 if i == near else 1.5, org, end)
            scn.ngeom += 1
            if i == near:
                g = scn.geoms[scn.ngeom]
                mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_SPHERE, np.array([0.08, 0, 0]), end,
                                    np.eye(3).ravel(), RED)
                scn.ngeom += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="interior", choices=tuple(aps.SCENES))
    ap.add_argument("--policy", default="sectors", choices=("sectors", "offset_ring"))
    ap.add_argument("--wind", type=float, default=None)
    ap.add_argument("--speed", type=float, default=1.0, help="playback speed vs real time")
    ap.add_argument("--rays", action="store_true", help="draw the FR-18 range-ring beams and nearest obstacle")
    ap.add_argument("--demo", choices=("headon",), default=None,
                    help="headon: the separation encounter (inside the campus wall), handled by the layered logic")
    ap.add_argument("--apf-only", action="store_true", help="with --demo headon: disable the governor (shows the failure)")
    ap.add_argument("--no-vision", action="store_true", help="skip the surveillance cameras (FSM stays in PATROL)")
    ap.add_argument("--appear", type=float, default=20.0, help="intruder appearance time, s")
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args()

    if a.demo == "headon":
        # --apf-only switches the production separation layer off exactly as the tests and the ablation do
        # (layered_separation=False = the guide's APF alone). D_WARN is no longer read by the governor.
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], policy="sectors",
                                                wind_mps=0.0, gust_sigma=0.0, vision=False,
                                                layered_separation=not a.apf_only)
        headon_mid = setup_head_on(ctl)
    else:
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES[a.scene], policy=a.policy,
                                                wind_mps=a.wind, seed=a.seed, intruder_appear_s=a.appear,
                                                vision=not a.no_vision)
        if ctl.vision_enabled:
            try:                                  # off-screen renderer for the surveillance cameras
                ctl.renderer = mujoco.Renderer(ctl.model, 480, 640)
            except Exception as exc:              # noqa: BLE001  -- report, never fake detections
                print(f"vision off: off-screen renderer unavailable next to the viewer ({exc})")
                ctl.vision_enabled = False
    frame = 1 / 60
    with viewer.launch_passive(ctl.model, ctl.data) as v:
        if a.demo == "headon":
            v.cam.lookat[:] = headon_mid
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 45, 0, -20
        elif a.scene == "interior":
            v.cam.lookat[:] = (0, -8, 6)
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 30, 250, -18
        else:
            v.cam.lookat[:] = (0, -15, 15)
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 150, 215, -28
        dmin = float("inf")
        last = None
        while v.is_running():
            t0 = time.perf_counter()
            ctl.step_simulation(dt=frame * a.speed)
            extra = []
            if a.demo == "headon":
                pa = ctl.data.qpos[ctl.uavs["alpha"]["qadr"]:ctl.uavs["alpha"]["qadr"] + 3]
                pb = ctl.data.qpos[ctl.uavs["bravo"]["qadr"]:ctl.uavs["bravo"]["qadr"] + 3]
                d = float(np.linalg.norm(pa - pb))
                if d < dmin:
                    dmin = d
                    print(f"\rt = {ctl.current_time_s:5.2f} s   min centre distance {dmin:5.2f} m "
                          f"(bound 2.5 m, airframes touch below 0.76 m)", end="", flush=True)
                held = "CONTACT" if ctl.uav_uav_contacts else ("held" if dmin >= ctl.d_safe_m else "below 2.5 m bound")
                extra = [("Mode", "APF only (failure)" if a.apf_only else "layered separation"),
                         ("Separation", f"{d:6.2f} m (min {dmin:5.2f} m)"), ("Result", held)]
            states = (ctl.uavs["alpha"]["fsm"], ctl.uavs["bravo"]["fsm"])
            if states != last:                    # FSM transitions also go to the terminal
                print(f"\n[{ctl.current_time_s:7.2f} s] alpha {states[0]:17s} bravo {states[1]}", end="", flush=True)
                last = states
            if a.rays:
                with v.lock():
                    draw_rays(v.user_scn, ctl)
            v.set_texts((None, None, *fsm_overlay(ctl, extra)))     # FR-17 overlay (takes the lock itself)
            v.sync()
            time.sleep(max(0.0, frame - (time.perf_counter() - t0)))


if __name__ == "__main__":
    main()
