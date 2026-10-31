"""Viva-prep summary (not a dossier script): per scene x condition mean and sample sd of selected columns of the real trials CSV."""
import csv, math, os, statistics as st
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "analytics", "campus_patrol_real_trials.csv")
rows = list(csv.DictReader(open(P)))
cols = ["tracking_rmse_m", "control_effort_N2s", "energy_wh", "min_inter_uav_m", "min_obstacle_clearance_m", "obstacle_contacts",
        "uav_uav_contacts", "cycle_time_s", "worst_revisit_ground_s", "detected", "detection_latency_s", "verify_time_s", "duration_s", "timestep_s", "gallery_coverage", "n_laps_alpha", "n_laps_bravo", "n_ground_laps", "worst_revisit_ground_eqwin_s", "torque_effort_N2m2s", "waypoint_rmse_m"]
print("file", P, "rows", len(rows))
for sc in ("interior", "exterior"):
    for cd in ("guard_baseline", "uav_sectors", "uav_offset_ring"):
        sub = [r for r in rows if r["scene"] == sc and r["condition"] == cd]
        print(f"{sc} {cd} n={len(sub)}")
        for c in cols:
            v = [float(r[c]) for r in sub if r[c] != ""]
            if c == "worst_revisit_ground_eqwin_s" and v:   # right-censored at eqwin_s: no sd, no test
                w = float(sub[0]["eqwin_s"]); k = sum(1 for x in v if x >= w - 1e-6)
                print(f"   {c:26s} n={len(v):2d} censored (>= {w:g} s, no revisit inside the window) {k} of {len(v)}; max={max(v):.4f}"
                      + (f" mean={st.mean(v):.4f} sd={st.stdev(v):.4f}" if k < len(v) and len(v) > 1 else " (guard value is a lower bound, no mean/sd)"))
                continue
            if not v: print(f"   {c:26s} (empty / not applicable)"); continue
            sd = st.stdev(v) if len(v) > 1 else float('nan')
            print(f"   {c:26s} n={len(v):2d} mean={st.mean(v):.4f} sd={sd:.4f} min={min(v):.4f} max={max(v):.4f}" + (f" sum={sum(v):.0f}" if c in ("obstacle_contacts","uav_uav_contacts","detected") else ""))
