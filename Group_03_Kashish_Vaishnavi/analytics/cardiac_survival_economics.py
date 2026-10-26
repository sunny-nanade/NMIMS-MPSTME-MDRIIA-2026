"""Dimensionless survival and economics comparison (no currency anywhere).

MDRIIA Group 03 - autonomous last-mile ground AED delivery rover.

Uses the vendored clinical module (src/aedrover/clinical):
  * survival versus time to first shock, Larsen et al. (1993): 0.67 - 0.023 t_cpr - 0.011 t_defib
    - 0.021 t_acls (minutes from collapse), plus the guideline rule of thumb as a sensitivity model;
  * ambulance response times from a lognormal fitted to the Central Norway urban median and 90th
    percentile (Naess et al. 2024);
  * the operating-burden ratio kappa, the payback horizon and the staff capacity freed.

Every input that is not taken from a paper is an ASSUMPTION and is printed as such. By default the
rover speed is the mean speed of the successful episodes of one controller in
analytics/aed_delivery_benchmark.csv, so the simulation feeds the clinical comparison.

    python analytics/cardiac_survival_economics.py
    python analytics/cardiac_survival_economics.py --speed-source assumption --radius 500
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aedrover.clinical import (  # noqa: E402
    KAPPA_TARGET,
    EconomicsInputs,
    ScenarioParams,
    breakeven_radius,
    compare_modes,
    get_model,
    qaly_gain_per_encounter,
)


def measured_speed(csv_path, controller):
    """Mean speed [m/s] of the successful benchmark episodes of ``controller`` and their count."""
    frame = pd.read_csv(csv_path)
    ok = frame[(frame["controller"] == controller) & frame["success"].astype(bool)]
    if ok.empty:
        raise SystemExit(f"[ERROR] no successful episodes of {controller!r} in {csv_path}")
    return float(ok["mean_speed"].mean()), len(ok)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--radius", type=float, default=1000.0, help="straight-line radius in metres (ASSUMPTION)")
    ap.add_argument("--controller", default="dwa", help="benchmark controller that supplies the rover speed")
    ap.add_argument("--speed-source", choices=("benchmark", "assumption"), default="benchmark")
    ap.add_argument("--n", type=int, default=2000, help="simulated arrests")
    ap.add_argument("--resamples", type=int, default=1000, help="bootstrap resamples")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--life-years", type=float, default=None, help="optional life expectancy for QALYs (ASSUMPTION)")
    ap.add_argument("--qol", type=float, default=None, help="optional quality-of-life weight for QALYs (ASSUMPTION)")
    args = ap.parse_args(argv)

    base = ScenarioParams()
    if args.speed_source == "benchmark":
        speed, n_ok = measured_speed(ROOT / "analytics" / "aed_delivery_benchmark.csv", args.controller)
        speed_note = f"measured: mean speed of {n_ok} successful {args.controller} episodes in the benchmark CSV"
    else:
        speed, speed_note = base.rover_speed_mps, "ASSUMPTION (package default)"
    params = ScenarioParams(radius_m=args.radius, rover_speed_mps=speed)
    d = params.dispatch

    print("=" * 72)
    print("MDRIIA GROUP 03 - CARDIAC SURVIVAL AND DIMENSIONLESS ECONOMICS")
    print("=" * 72)
    print("Scenario inputs")
    print(f"  radius                     {params.radius_m:8.0f} m        [ASSUMPTION]")
    print(f"  rover speed                {params.rover_speed_mps:8.2f} m/s      [{speed_note}]")
    print(f"  route factor               {params.route_factor:8.2f}          [ASSUMPTION]")
    print(f"  ambulance response         median {params.ems_median_min:.1f} min, p90/median {params.ems_p90_over_median:.2f}  [Naess 2024, urban]")
    print(f"  collapse-to-call           {d.collapse_to_call_min:8.1f} min      [ASSUMPTION]")
    print(f"  call-to-alert              {d.call_to_alert_min:8.1f} min      [ASSUMPTION]")
    print(f"  hand-off (AED and pads)    {d.handoff_min:8.1f} min      [ASSUMPTION]")
    print(f"  bystander CPR at           {d.bystander_cpr_delay_min:8.1f} min      [ASSUMPTION]")

    gains = {}
    for model_name in ("larsen1993", "rule_of_thumb"):
        model = get_model(model_name)
        table = compare_modes(model, params, n=args.n, seed=args.seed, parallel=True,
                              modes=("ambulance", "rover"), n_resamples=args.resamples)
        print("-" * 72)
        print(f"Survival, rover dispatched in parallel with the ambulance, model {model_name}")
        for _, row in table.iterrows():
            line = f"  {row['mode']:<10} survival {row['mean_survival']:.3f} [{row['survival_ci_low']:.3f}, {row['survival_ci_high']:.3f}]"
            if row["mode"] != "ambulance":
                line += (f"  gain {100 * row['abs_gain']:+.1f} pp [{100 * row['abs_gain_ci_low']:+.1f}, "
                         f"{100 * row['abs_gain_ci_high']:+.1f}]  shocks first {100 * row['p_faster']:.0f}%")
                gains[model_name] = float(row["abs_gain"])
            print(line)
        be = breakeven_radius(params.rover_speed_mps, params.route_factor, d.call_to_alert_min, d.handoff_min,
                              params.ems_median_min, model, ems_p90_over_median=params.ems_p90_over_median)
        if be.flag == "crossing":
            print(f"  rover alone matches ambulance alone at a straight-line radius of {be.radius_m:.0f} m")
        else:
            print(f"  break-even: {be.flag}")

    econ = EconomicsInputs()
    print("-" * 72)
    print("Dimensionless economics (all inputs are ASSUMPTIONS: ratios to the annual value of reclaimed labour)")
    print(f"  energy {econ.energy_ratio:.2f}, maintenance {econ.maintenance_ratio:.2f}, infrastructure {econ.infrastructure_ratio:.2f}")
    print(f"  capital parity factor {econ.capex_parity_factor:.2f} years, reclaimed task hours {econ.annual_reclaimed_task_hours:.0f} per year")
    print(f"  kappa                      {econ.kappa:8.3f}          (target <= {KAPPA_TARGET:g}: {'met' if econ.meets_target else 'not met'})")
    print(f"  payback horizon            {econ.payback_months:8.1f} months")
    print(f"  staff capacity freed       {econ.delta_fte:8.2f} FTE")
    if args.life_years is not None and args.qol is not None:
        gain = gains["larsen1993"]
        qaly = qaly_gain_per_encounter(gain, args.life_years, args.qol)
        print(f"  QALYs per encounter        {qaly:8.3f}          (Larsen gain x {args.life_years:g} years x {args.qol:g}; ASSUMPTION inputs)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
