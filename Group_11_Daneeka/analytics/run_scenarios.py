"""Fault / stress scenarios (feeds the FMEA occurrence and detection scores).

Each scenario changes ONE thing relative to the nominal Monte Carlo and runs N paired missions
(baseline and proposed share the seed). Results: analytics/scenario_real_trials.csv
Scenarios
  glint_stress   sun placed where the camera sees specular glint: site latitude 6 N, 21-Jun, 11:20-11:50
                 (verified: at the project site, Mumbai, the camera never sees glint in any month)
  nav_drift      gyro bias 0.002 rad/s and +/-2 % wheel-radius calibration error (poor calibration / slip)
  misassociation initial along-row odometry offset 0.4-0.8 m (dock mis-alignment)
  low_irradiance start 16:15-16:45 (sun low, G below the 600 W/m2 validity limit)
  sensor_stress  thermal noise x3, spike probability 1 %, frame drop-out 10 %
Usage: python analytics/run_scenarios.py --n 30 --workers 2
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import multiprocessing as mp
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "analytics"))

from fault_injection import FaultConfig, NavFaults, SensorFaults  # noqa: E402
from run_evaluation import FIELDS, MODEL, SEED0, make_config  # noqa: E402
from solar_defect_detector import InspectionMission  # noqa: E402

SCENARIOS = ["glint_stress", "nav_drift", "misassociation", "low_irradiance", "sensor_stress"]


def scenario_config(name, seed, cond):
    cfg = make_config(seed, cond, name)
    r = np.random.default_rng(seed + 999)
    env, nav, sen = cfg.env, NavFaults(), SensorFaults()
    env.weather, env.moving_cloud = "clear", False
    cfg.weather_label = "clear"
    if name == "glint_stress":
        env.latitude_deg, env.date = 6.0, dt.date(2026, 6, 21)
        env.start_s = float(r.uniform(11.3, 11.8)) * 3600
    elif name == "nav_drift":
        nav = NavFaults(enc_cal_err_left=0.02, enc_cal_err_right=-0.02, gyro_bias=0.002)
    elif name == "misassociation":
        nav = NavFaults(init_x_error=float(r.uniform(0.4, 0.8)) * (1 if r.random() < 0.5 else -1))
    elif name == "low_irradiance":
        env.start_s = float(r.uniform(16.25, 16.75)) * 3600
    elif name == "sensor_stress":
        sen = SensorFaults(noise_scale=3.0, spike_prob=0.01, dropout_prob=0.10)
    cfg.faults = FaultConfig(nav, sen, label=name)
    cfg.start_h = env.start_s / 3600
    return cfg


def run_one(args):
    name, seed, cond = args
    cfg = scenario_config(name, seed, cond)
    res = InspectionMission(cfg, MODEL).run()
    row = dict(res.metrics)
    row.update(weather=name, start_h=round(cfg.start_h, 3), scenario=name)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", nargs="*", default=SCENARIOS)
    ap.add_argument("--out", default=os.path.join(ROOT, "analytics", "scenario_real_trials.csv"))
    a = ap.parse_args()
    jobs = [(s, SEED0 + 5000 + k, c) for s in a.only for k in range(a.n) for c in ("baseline", "proposed")]
    t0, rows = time.time(), []
    with mp.Pool(a.workers) as pool:
        for i, row in enumerate(pool.imap(run_one, jobs), 1):
            rows.append(row)
            print(f"[{i}/{len(jobs)}] {row['scenario']:15s} seed {row['seed']} {row['condition']:9s} "
                  f"recall={row['recall']:.2f} fp={row['fp']} contact={row['obstacle_contact_s']:.1f}s "
                  f"done={row['completed']} elapsed {time.time() - t0:.0f}s", flush=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS + ["scenario"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
