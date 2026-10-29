#!/opt/miniconda3/bin/python3
"""
Parallel Trial Runner for Space Debris Capture Experimentation.
Runs reproducible Monte Carlo simulation trials under impedance and rigid control.
Saves trial-level summary metrics to analytics/real_trials_summary.csv and detailed
full-rate 500 Hz telemetry runs under analytics/runs/.
"""

import os
import sys
import argparse
import csv
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

# Resolve project paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
ANALYTICS_DIR = SCRIPT_DIR

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import debris_capture_controller as dcc
import mujoco


def _worker_run(params):
    ctrl, s, t, idx, total, save_dir = params
    trial_out = Path(save_dir) / f"{ctrl}_seed{s}_tumble{t:.1f}" if save_dir else None
    cmd_args = [
        '--headless',
        '--trial',
        '--duration', '22.0',
        '--controller', ctrl,
        '--seed', str(s),
        '--tumble', str(t)
    ]
    if trial_out:
        cmd_args.extend(['--out', str(trial_out)])
        
    args = dcc.arguments(cmd_args)
    t0 = time.monotonic()
    mission = dcc.Mission(args, mujoco)
    try:
        while not mission.done:
            mission.step()
        wall_time = time.monotonic() - t0
        report = mission.result(wall_time)
    finally:
        mission.close()
        
    return {
        'condition_index': idx,
        'controller': ctrl,
        'seed': s,
        'tumble_rate_dps': t,
        'success': int(report['success']),
        'failure_reason': report['failure'] or 'None',
        'sim_time_s': round(report['sim_seconds'], 3),
        'peak_contact_force_N': round(report['peak_contact_force_N'], 2),
        'contact_impulse_Ns': round(report['contact_impulse_Ns'], 3),
        'impact_peak_force_N': round(report.get('impact_peak_force_N', report['peak_contact_force_N']), 2),
        'impact_impulse_Ns': round(report.get('impact_impulse_Ns', report['contact_impulse_Ns']), 3),
        'attitude_disturbance_deg': round(report['attitude_disturbance_deg'], 3),
        'wheel_momentum_peak_Nms': round(report['wheel_momentum_peak_Nms'], 2),
        'torque_effort_Nm2s': round(report['torque_effort_Nm2s'], 2),
        'residual_spin_dps': round(report['residual_spin_deg_s'], 4)
    }


def run_trials(n_per_condition=30, tumble_range=(2.0, 15.0), base_seed=42, overwrite=False, max_workers=6):
    """
    Runs N trials per condition (impedance vs rigid) with matching seeds and tumble velocities.
    Outputs simulation-derived results to real_trials_summary.csv.
    """
    summary_csv = ANALYTICS_DIR / "real_trials_summary.csv"
    imp_csv = ANALYTICS_DIR / "impedance_real_trials.csv"
    rigid_csv = ANALYTICS_DIR / "rigid_pd_real_trials.csv"
    runs_dir = ANALYTICS_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    
    if summary_csv.exists() and not overwrite:
        print(f"[INFO] Dataset already exists at {summary_csv}. Use --overwrite to re-run.")
        return summary_csv

    print("=" * 70)
    print(f"RUNNING MONTE CARLO EXPERIMENT (N = {n_per_condition} per condition, Total = {n_per_condition * 2})")
    print(f"Sampling Rate: 500 Hz | Timestep: 0.002s | Microgravity: 0G | Workers: {max_workers}")
    print(f"Output Directory: {ANALYTICS_DIR}")
    print("=" * 70)

    rng = np.random.default_rng(base_seed)
    # Generate identical conditions for paired statistical comparison
    seeds = [int(s) for s in rng.integers(1000, 99999, size=n_per_condition)]
    tumbles = [float(t) for t in np.round(rng.uniform(tumble_range[0], tumble_range[1], size=n_per_condition), 2)]

    tasks = []
    for ctrl in ['impedance', 'rigid']:
        for i in range(n_per_condition):
            s = seeds[i]
            t = tumbles[i]
            save_dir_str = str(runs_dir) if i < 3 else None
            tasks.append((ctrl, s, t, i + 1, n_per_condition, save_dir_str))

    t_start = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker_run, task): task for task in tasks}
        completed = 0
        total_tasks = len(tasks)
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            completed += 1
            status = "SUCCESS" if res['success'] else f"FAIL ({res['failure_reason']})"
            print(f"[{completed:02d}/{total_tasks}] {res['controller']:9s} Seed {res['seed']:5d} | Tumble {res['tumble_rate_dps']:5.2f} dps -> {status:10s} (Impact: {res['impact_impulse_Ns']:5.1f} N*s, Peak: {res['impact_peak_force_N']:6.1f} N)")

    # Sort results deterministically by controller then condition_index
    results.sort(key=lambda r: (r['controller'] != 'impedance', r['condition_index']))
    for i, r in enumerate(results):
        r['trial_id'] = i + 1

    fieldnames = ['trial_id'] + [k for k in results[0].keys() if k != 'trial_id']
    with open(summary_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[SUCCESS] Wrote combined trial dataset: {summary_csv}")

    imp_records = [r for r in results if r['controller'] == 'impedance']
    with open(imp_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(imp_records)
    print(f"[SUCCESS] Wrote impedance dataset: {imp_csv}")

    rigid_records = [r for r in results if r['controller'] == 'rigid']
    with open(rigid_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rigid_records)
    print(f"[SUCCESS] Wrote rigid PD dataset: {rigid_csv}")
    print(f"[SUCCESS] All {len(results)} trials completed in {time.time() - t_start:.1f} seconds.")

    return summary_csv


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run Monte Carlo space debris capture trials")
    parser.add_argument('--trials', type=int, default=30, help="Number of trials per condition (N >= 30)")
    parser.add_argument('--seed', type=int, default=42, help="Random seed for initial conditions")
    parser.add_argument('--workers', type=int, default=6, help="Parallel worker processes")
    parser.add_argument('--overwrite', action='store_true', help="Overwrite existing dataset")
    args = parser.parse_args()

    run_trials(n_per_condition=args.trials, base_seed=args.seed, overwrite=args.overwrite, max_workers=args.workers)
