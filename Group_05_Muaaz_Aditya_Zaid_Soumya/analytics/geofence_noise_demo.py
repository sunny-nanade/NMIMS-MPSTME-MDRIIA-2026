"""
Geofence noise demo | owner E075 Zaid Rezaur Rahman
FMEA evidence for the failure mode "false geofence alarm from position noise".

A walker follows two scripted paths in each scene (zone = geom 'substation_zone'):
  crossing : straight line through the zone centre, 25 m approach and 25 m exit
  skirt    : walks parallel to the zone's long edge, 1.5 m OUTSIDE it, so the TRUE
             position never enters the zone (any tier-3 alarm on this path is false)
Settings: position noise off/on x hysteresis off/on. Noise is Gaussian with
sigma = DualUAVSurveillanceController.GEOFENCE_NOISE_SIGMA_M (an ASSUMPTION, see the
controller; not a measured sensor figure), one seeded stream per run.

FALSE ALARM = the reported tier rises to 3 while the true (noise-free) tier is below 3.
Walking speed and sample rate are demo parameters printed in the header.

  python analytics/geofence_noise_demo.py [--seeds 100] [--rate-hz 10] [--sigma 1.5]

Writes analytics/geofence_breach_log_<scene>.json: seed-0 events of every setting and path
(each event carries a 'run' label) plus a per-run summary.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
import aerial_patrol_swarm as aps          # noqa: E402

WALK_SPEED_MPS = 1.35                      # same walking pace as the scene's intruder
SKIRT_OFFSET_M = 1.5


def build_paths(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    paths = {"crossing": [(x0 - 25.0, cy), (x1 + 25.0, cy)]}
    if (x1 - x0) >= (y1 - y0):               # skirt the long edge
        paths["skirt"] = [(x0 - 5.0, y0 - SKIRT_OFFSET_M), (x1 + 5.0, y0 - SKIRT_OFFSET_M)]
    else:
        paths["skirt"] = [(x0 - SKIRT_OFFSET_M, y0 - 5.0), (x0 - SKIRT_OFFSET_M, y1 + 5.0)]
    return paths


def sample_path(wps, rate_hz):
    (ax, ay), (bx, by) = wps
    length = float(np.hypot(bx - ax, by - ay))
    n = int(length / WALK_SPEED_MPS * rate_hz) + 1
    s = np.linspace(0.0, 1.0, n)
    return [(ax + (bx - ax) * u, ay + (by - ay) * u, 0.0) for u in s]


def run_once(ctl, samples, rate_hz, noise_on, hyst_on, seed, sigma):
    ctl.geofence_hysteresis = hyst_on
    ctl.reset_geofence_state()
    ctl.reseed_geofence_noise(seed)
    ctl._geofence_last_noisy = None
    prev, false_alarms, transitions = 0, 0, 0
    for i, p in enumerate(samples):
        ctl.current_time_s = i / rate_hz
        true_tier = ctl.geofence_raw_tier(p)
        meas = ctl.inject_position_noise(p, sigma if noise_on else 0.0)
        _, tier = ctl.evaluate_geofence_status(meas)
        if tier != prev:
            transitions += 1
            if tier == 3 and true_tier < 3:
                false_alarms += 1
        prev = tier
    return false_alarms, transitions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--rate-hz", type=float, default=10.0)
    ap.add_argument("--sigma", type=float, default=None, help="noise std per axis, m (default: controller assumption)")
    ap.add_argument("--no-write", action="store_true", help="do not write the breach logs")
    args = ap.parse_args()

    print("Geofence noise demo (false geofence alarm from position noise)")
    for scene in ("interior", "exterior"):
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES[scene], vision=False,
                                                wind_mps=0.0, gust_sigma=0.0)
        sigma = ctl.GEOFENCE_NOISE_SIGMA_M if args.sigma is None else args.sigma
        poly = ctl._geofence_polygon()
        paths = build_paths(poly)
        print()
        print(f"=== scene: {scene} ===")
        print("zone corners (m): " + " ".join(f"({x:.2f},{y:.2f})" for x, y in poly))
        print(f"tier 2 buffer {ctl.GEOFENCE_BUFFER_M} m, tier 1 advisory {ctl.GEOFENCE_ADVISORY_M} m, "
              f"hysteresis exit margin {ctl.GEOFENCE_EXIT_MARGIN_M} m + tier-3 dwell {ctl.GEOFENCE_CONFIRM_N} readings")
        print(f"noise sigma {sigma} m per axis (ASSUMPTION, range 0.5-3.0 m), walker {WALK_SPEED_MPS} m/s, "
              f"sampling {args.rate_hz} Hz, {args.seeds} seeds per cell")
        print(f"{'path':9s} {'noise':5s} {'hyst':5s} {'false alarms':>13s} {'per run':>9s} {'per min':>9s} "
              f"{'tier changes/run':>17s}")
        runs_log = []
        for pname, wps in paths.items():
            samples = sample_path(wps, args.rate_hz)
            minutes = len(samples) / args.rate_hz / 60.0
            for noise_on in (False, True):
                for hyst_on in (False, True):
                    fa_tot, tr_tot = 0, 0
                    n_seeds = args.seeds if noise_on else 1       # noise off is deterministic
                    for seed in range(n_seeds):
                        fa, tr = run_once(ctl, samples, args.rate_hz, noise_on, hyst_on, seed, sigma)
                        fa_tot += fa
                        tr_tot += tr
                        if seed == 0:
                            label = f"{pname}/noise_{'on' if noise_on else 'off'}/hyst_{'on' if hyst_on else 'off'}"
                            runs_log.append({"run": label, "seed": 0, "false_alarms": fa,
                                             "events": [dict(e, run=label) for e in ctl.geofence_events]})
                    print(f"{pname:9s} {'on' if noise_on else 'off':5s} {'on' if hyst_on else 'off':5s} "
                          f"{fa_tot:13d} {fa_tot / n_seeds:9.3f} {fa_tot / (n_seeds * minutes):9.3f} "
                          f"{tr_tot / n_seeds:17.2f}")
        if not args.no_write:
            ctl.geofence_events = [e for r in runs_log for e in r["events"]]
            path = ctl.write_geofence_breach_log(
                os.path.join(HERE, f"geofence_breach_log_{scene}.json"),
                extra={"noise_sigma_m": sigma, "noise_sigma_basis": "ASSUMPTION range 0.5-3.0 m",
                       "exit_margin_m": ctl.GEOFENCE_EXIT_MARGIN_M, "rate_hz": args.rate_hz,
                       "runs": [{k: v for k, v in r.items() if k != "events"} for r in runs_log]})
            print(f"breach log written: {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
