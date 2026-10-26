"""Closed-loop navigation entry point.

MDRIIA Group 03 - autonomous last-mile ground AED delivery rover.

Runs ONE episode of each requested controller (default: DWA and MPPI) on the vendored aedrover
package. Every controller sees the same seeded scenario and, unless --no-shield is given, the same
speed-and-separation safety filter, so the summaries are directly comparable. The controllers
themselves live in src/aedrover/nav; this file is only the entry point.

    python src/aed_navigation_controller.py --controllers dwa
    python src/aed_navigation_controller.py --family crowded --seed 1001
    python src/aed_navigation_controller.py --controllers dwa --telemetry analytics/kerb_crossing_telemetry.csv

MPPI plans with physics rollouts and needs minutes for a full episode; use --max-time to shorten.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from aedrover.control.safety_filter import SafetyFilter  # noqa: E402
from aedrover.nav.base import make_controller, registered_controllers, run_episode  # noqa: E402
from aedrover.sim.env import AEDRoverEnv  # noqa: E402
from aedrover.sim.scenario import FAMILIES  # noqa: E402
from aedrover.sim.vehicle_mjcf import VehicleParams  # noqa: E402

BUDGET_G = 3.0
TELEMETRY_COLUMNS = ["t_s", "x_m", "y_m", "yaw_rad", "v_cmd_mps", "delta_cmd_rad", "shock_g", "clearance_m"]


# keyword each controller uses for its top speed (as in the benchmark, one number caps every method)
SPEED_KEY = {"pure_pursuit": "v_cruise", "apf": "v_cruise", "apf_nocurb": "v_cruise", "dwa": "v_cruise",
             "dwa_nocurb": "v_cruise", "mppi": "v_max", "ppo": "v_max"}
BENCHMARK_SPEED_CAP = 2.0


def controller_kwargs(name, speed_cap):
    """Settings the benchmark used: the common speed cap and, for MPPI, the tuned cost weights."""
    kw = {}
    if speed_cap and name in SPEED_KEY:
        kw[SPEED_KEY[name]] = float(speed_cap)
    tuned = SRC.parent / "configs" / "mppi_tuned.json"
    if name == "mppi" and tuned.exists():
        kw.update(json.loads(tuned.read_text(encoding="utf-8"))["kwargs"])
    return kw


def run_one(name, family, seed, vehicle, shield_on, max_time, speed_cap=BENCHMARK_SPEED_CAP):
    """Run one episode; returns (episode metrics, scenario, shield, wall seconds)."""
    env = AEDRoverEnv(obs_mode="dict", veh=VehicleParams.by_name(vehicle), max_time=max_time)
    controller = make_controller(name, **controller_kwargs(name, speed_cap))
    shield = SafetyFilter() if shield_on else None
    t0 = time.perf_counter()
    episode = run_episode(env, controller, shield, seed=seed, options={"family": family}, record=True)
    return episode, env.scenario, shield, time.perf_counter() - t0


def write_telemetry(path, episode, scenario, name, family, seed):
    """Write the recorded trajectory (time, pose, commanded speed and steering, shock, clearance)."""
    frame = pd.DataFrame(episode["trajectory"], columns=TELEMETRY_COLUMNS)
    frame["controller"] = name
    frame["family"] = family
    frame["seed"] = seed
    frame["kerb_h_m"] = scenario.kerb_h
    frame["x_down_m"] = scenario.x_down
    frame["x_up_m"] = scenario.x_up
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def summary_line(name, episode, shield, wall):
    clearance = episode["min_clearance_m"]
    clear_txt = "n/a" if not np.isfinite(clearance) else f"{clearance:.2f} m"
    interventions = "shield off" if shield is None else f"shield interventions {shield.n_interventions}/{shield.n_calls}"
    return (
        f"[{name}] outcome={episode['outcome']}  time={episode['time_s']:.2f} s  path={episode['path_m']:.2f} m  "
        f"peak_shock={episode['peak_shock_g']:.2f} g (budget {BUDGET_G:g} g)  min_clearance={clear_txt}  "
        f"{interventions}  wall={wall:.1f} s"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run one episode of each requested controller.")
    ap.add_argument("--controllers", nargs="+", default=["dwa", "mppi"], help="registered controller names")
    ap.add_argument("--family", choices=FAMILIES, default="kerb", help="scenario family")
    ap.add_argument("--seed", type=int, default=1003, help="scenario seed (same scenario for every controller)")
    ap.add_argument("--vehicle", choices=("nominal", "optimized"), default="optimized")
    ap.add_argument("--no-shield", action="store_true", help="disable the safety filter")
    ap.add_argument("--max-time", type=float, default=90.0, help="episode time limit in seconds (benchmark: 90)")
    ap.add_argument("--speed-cap", type=float, default=BENCHMARK_SPEED_CAP,
                    help="top speed in m/s given to every controller (benchmark: 2.0; 0 keeps each controller's default)")
    ap.add_argument("--telemetry", default=None, help="write the trajectory of each controller to this CSV")
    args = ap.parse_args(argv)

    available = registered_controllers()
    unknown = [c for c in args.controllers if c not in available]
    if unknown:
        print(f"[ERROR] unknown controller(s) {unknown}; registered: {available}")
        return 2
    print("=" * 60)
    print(f"Autonomous ground AED delivery rover: family={args.family} seed={args.seed} vehicle={args.vehicle}")
    print("=" * 60)
    for name in args.controllers:
        if name == "mppi":
            print("[mppi] plans with physics rollouts; a full episode takes minutes on a laptop CPU ...", flush=True)
        episode, scenario, shield, wall = run_one(
            name, args.family, args.seed, args.vehicle, not args.no_shield, args.max_time, args.speed_cap)
        print(summary_line(name, episode, shield, wall))
        if args.telemetry:
            path = Path(args.telemetry)
            if len(args.controllers) > 1:
                path = path.with_name(f"{path.stem}_{name}{path.suffix}")
            print(f"[{name}] telemetry written to {write_telemetry(path, episode, scenario, name, args.family, args.seed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
