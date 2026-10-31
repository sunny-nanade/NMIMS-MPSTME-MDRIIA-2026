#!/usr/bin/env python
"""Print every number used in the LinkedIn video, computed from the committed trial CSV.

Run from the group folder:
    python docs/submission/print_video_numbers.py > docs/submission/video_numbers_output.txt
    python docs/submission/print_video_numbers.py --csv PATH     # a test CSV that has its own .provenance.json

Reads analytics/campus_patrol_real_trials.csv (read only) and refuses (exit 2) unless the CSV's sha256 equals
"csv_sha256" in its provenance record. Nothing is simulated or typed in here: every figure, every count and every
window printed comes from the CSV or its provenance. Statistics come from analytics/statistical_validation.py
(Welch two-sided t, Welch-Satterthwaite df, Cohen's d with pooled sd, t-based 95 % CI of the mean difference,
Wilson and exact intervals for detection rates). A cell with no values prints "not measured", never a number.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(GROUP, "analytics"))
import statistical_validation as sv  # noqa: E402
import censored_revisit as cr  # noqa: E402

SCENES = sv.SCENES
CONDS = sv.CONDITIONS
UAV = sv.UAV_CONDITIONS


def col(rows, scene, cond, name):
    if name not in rows[0]:
        return np.array([])
    return sv.column(rows, scene, cond, name)


def ms(x, nd=4):
    return f"mean={x.mean():.{nd}f} sd={x.std(ddof=1):.{nd}f} n={len(x)}" if len(x) > 1 else \
        (f"value={x[0]:.{nd}f} n=1" if len(x) == 1 else "not measured (no values)")


def welch_block(rows, scene, metric, a_cond, b_cond, unit="s"):
    a, b = col(rows, scene, a_cond, metric), col(rows, scene, b_cond, metric)
    print(f"[{scene}] {a_cond} vs {b_cond}, metric {metric} (difference = {a_cond} - {b_cond})")
    if metric not in rows[0]:
        print(f"  column {metric} absent from this CSV (batch predates it): not measured")
        return
    w = sv.welch(a, b)
    if "error" in w:
        print(f"  {a_cond}: {ms(a)}; {b_cond}: {ms(b)}")
        print(f"  test not computed: {w['error']}")
        return
    print(f"  n_{a_cond}={w['na']} n_{b_cond}={w['nb']}")
    print(f"  mean_{a_cond}={w['ma']:.4f} {unit} sd={w['sa']:.4f} {unit}")
    print(f"  mean_{b_cond}={w['mb']:.4f} {unit} sd={w['sb']:.4f} {unit}")
    ratio = f"{w['ma'] / w['mb']:.4f}" if w["mb"] else "n/a"
    print(f"  mean_difference={w['diff']:.4f} {unit}  ratio {a_cond}/{b_cond}={ratio}")
    print(f"  Welch t={w['t']:.4f}  df={w['df']:.3f}  p(two-sided)={w['p']:.5e}  Cohen d={w['d']:.4f}")
    print(f"  95% CI of mean difference: {w['ci_lo']:.4f} to {w['ci_hi']:.4f} {unit}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=sv.DEFAULT_CSV)
    a = ap.parse_args(argv)
    try:
        rows, prov, digest = sv.load_validated(a.csv)
    except sv.Refused as e:
        print(f"[REFUSED] {e}")
        return 2
    print("VIDEO NUMBERS  (source: %s, %d rows, sha256 %s equals provenance csv_sha256)"
          % (os.path.basename(a.csv), len(rows), digest))
    print("command: python docs/submission/print_video_numbers.py   (run inside the group folder)")
    print("statistics: scipy %s, Welch two-sided, Welch-Satterthwaite df, Cohen's d (pooled sd), 95%% CI of mean difference"
          % __import__("scipy").__version__)
    print("timestep_s values in CSV:", sorted({r["timestep_s"] for r in rows}))
    n_cell = sorted({sum(1 for r in rows if r["scene"] == s and r["condition"] == c) for s in SCENES for c in CONDS})
    print("runs per cell (all six cells):", n_cell)
    gc = prov.get("guard_config", {}).get("walk_speed_mps")
    print("guard walk speed range (m/s), provenance guard_config.walk_speed_mps:", gc[0] if gc else "not recorded")
    print("guard walk speed source:", gc[1][:160] if gc else "not recorded")
    for s in SCENES:
        wtxt, eq = sv.windows_text(rows, prov, s)
        print(f"run windows [{s}] (duration_s): {wtxt}; equal window eqwin_s: "
              + (", ".join(f"{x:g} s" for x in eq) if eq else "not in this CSV"))
    print()

    print("=" * 78)
    print("1. cycle_time_s (mean time per completed ground lap; window-independent), guard_baseline vs UAV policy")
    print("=" * 78)
    for scene in SCENES:
        for cond in UAV:
            welch_block(rows, scene, sv.PRIMARY_METRIC, "guard_baseline", cond)
        welch_block(rows, scene, sv.PRIMARY_METRIC, "uav_sectors", "uav_offset_ring")
        print()

    print("=" * 78)
    print("1b. equal-window worst revisit (worst_revisit_ground_eqwin_s): longest unserviced interval of any ground")
    print("    checkpoint inside the common window eqwin_s. The guard value is right-censored (>= eqwin_s): NO t test,")
    print("    d or CI is computed on this metric; it is described by censored counts and the UAV maximum.")
    print("=" * 78)
    for scene in SCENES:
        for c in CONDS:
            cs = cr.cell_stats(rows, scene, c)
            if cs is None:
                print(f"[{scene}] {c:16s} not measured (no values)")
            elif cs["k_censored"] == cs["n"]:
                print(f"[{scene}] {c:16s} worst revisit {cr.guard_value_text(cs['window_s'])}; censored runs {cs['k_censored']} of {cs['n']}")
            else:
                print(f"[{scene}] {c:16s} {ms(col(rows, scene, c, sv.EQWIN_METRIC))} max={cs['max_s']:.4f}; "
                      f"censored runs {cs['k_censored']} of {cs['n']}")
        print(f"[{scene}] {cr.descriptive_line(rows, scene, 'guard_baseline', UAV)}")
        print()

    print("=" * 78)
    print("2. detection (detected = 1 if the intruder was verified inside the run window; windows differ, see header)")
    print("=" * 78)
    for scene in SCENES:
        for cond in CONDS:
            rs = sv.cell_rows(rows, scene, cond)
            k = sum(1 for r in rs if (r["detected"] or "").strip() in ("1", "1.0"))
            n = len(rs)
            wl, ex = sv.wilson_ci(k, n), sv.exact_ci(k, n)
            lat = col(rows, scene, cond, "detection_latency_s")
            dur = sorted({float(r["duration_s"]) for r in rs})
            print("[%s] %-16s detected %d/%d (%.4f) Wilson 95%% [%.4f, %.4f] exact 95%% [%.4f, %.4f]; mean detection_latency_s=%s (n_latency=%d); run duration_s=%s"
                  % (scene, cond, k, n, k / n, wl[0], wl[1], ex[0], ex[1],
                     "%.4f" % lat.mean() if len(lat) else "not measured", len(lat), ",".join(f"{x:g}" for x in dur)))
    for scene in SCENES:
        g = [(r["detected"] or "").strip() in ("1", "1.0") for r in sv.cell_rows(rows, scene, "guard_baseline")]
        u = [(r["detected"] or "").strip() in ("1", "1.0") for r in sv.cell_rows(rows, scene, "uav_sectors")]
        print(f"[{scene}] guard {sum(g)}/{len(g)} vs uav_sectors {sum(u)}/{len(u)}: the run windows differ by condition (header), "
              "so a detection-count difference is not a like-for-like comparison.")
    print()

    print("=" * 78)
    print("3. safety (UAV cells only; the guard has no UAV columns)")
    print("=" * 78)
    for scene in SCENES:
        for cond in UAV:
            rs = sv.cell_rows(rows, scene, cond)
            clr = col(rows, scene, cond, "min_obstacle_clearance_m")
            oc = [(int(r["seed"]), int(float(r["obstacle_contacts"]))) for r in rs if (r["obstacle_contacts"] or "") != ""]
            hit = [(s_, c_) for s_, c_ in oc if c_ > 0]
            sep = col(rows, scene, cond, "min_inter_uav_m")
            uu = sum(int(float(r["uav_uav_contacts"])) for r in rs if (r.get("uav_uav_contacts") or "") != "")
            print("[%s] %-16s runs=%d" % (scene, cond, len(rs)))
            print("   min of min_obstacle_clearance_m = %s" % ("%.4f m" % clr.min() if len(clr) else "not measured"))
            print("   obstacle_contacts: total=%d over %d runs; runs with contacts=%d of %d; seeds with contacts=%s"
                  % (sum(c_ for _, c_ in oc), len(oc), len(hit), len(oc), hit if hit else "none"))
            print("   min of min_inter_uav_m = %s; runs below the %.1f m design separation: %d of %d"
                  % ("%.4f m (mean of per-run minima %.4f m)" % (sep.min(), sep.mean()) if len(sep) else "not measured",
                     sv.D_SAFE_M, int((sep < sv.D_SAFE_M).sum()), len(sep)))
            print("   uav_uav_contacts total = %d" % uu)
        rs = [r for r in rows if r["scene"] == scene and r["condition"] in UAV]
        clean = sum(1 for r in rs if int(float(r["obstacle_contacts"])) == 0)
        print("[%s] UAV runs (both policies) with 0 obstacle contacts: %d of %d" % (scene, clean, len(rs)))
    print()

    print("=" * 78)
    print("4. other UAV metrics (mean, sd, n per cell)")
    print("=" * 78)
    for scene in SCENES:
        for cond in UAV:
            for m in ("tracking_rmse_m", "waypoint_rmse_m", "control_effort_N2s", "torque_effort_N2m2s", "worst_revisit_ground_s"):
                label = {"tracking_rmse_m": "cross-track RMSE (m)", "waypoint_rmse_m": "waypoint RMSE (m)",
                         "control_effort_N2s": "thrust effort sum F^2 dt (N^2 s)",
                         "torque_effort_N2m2s": "torque effort (N^2 m^2 s)",
                         "worst_revisit_ground_s": "worst revisit over own window (s)"}[m]
                x = col(rows, scene, cond, m)
                print("[%s] %-16s %-36s %s" % (scene, cond, label, ms(x) if m in rows[0] else "column absent from this CSV"))
    for scene in SCENES:
        print("[%s] guard_baseline worst_revisit_ground_s over its own window: %s" % (scene, ms(col(rows, scene, "guard_baseline", "worst_revisit_ground_s"))))
    print()
    print("END")
    return 0


if __name__ == "__main__":
    sys.exit(main())
