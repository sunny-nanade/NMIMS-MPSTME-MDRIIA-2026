"""Viva-prep: per (mode, arm) means from analytics/ablation_trials.csv (80 rows, 10 seeds per arm). Nothing is written.
off = the one mitigation switched off, on = the production code path. All ablation runs are the INTERIOR scene, 90 s."""
import csv, os, statistics as st
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "analytics")
rows = list(csv.DictReader(open(os.path.join(A, "ablation_trials.csv"))))
print("rows", len(rows), "| scenes", sorted({r["scene"] for r in rows}), "| durations", sorted({r["duration_s"] for r in rows}))
COLS = {"separation": ["min_inter_uav_m", "sep_below_2p5", "uav_uav_contacts", "obstacle_contacts"],
        "fr18": ["obstacle_contacts", "min_obstacle_clearance_m"],
        "geofence": ["geofence_escalations", "geofence_spurious_escalations", "geofence_breach_events", "geofence_spurious_breaches"],
        "twilight": ["detected", "detection_latency_s"]}
for mode, cols in COLS.items():
    for arm in ("off", "on"):
        sub = [r for r in rows if r["mode"] == mode and r["arm"] == arm]
        out = []
        for c in cols:
            v = [float(r[c]) for r in sub if r[c] != ""]
            if not v:
                out.append(f"{c}: none")
            elif c in ("sep_below_2p5", "detected"):
                txt = f"{c}: {int(sum(v))}/{len(sub)}"
                lat = [float(r["detection_latency_s"]) for r in sub if r["detection_latency_s"] != ""]
                if c == "detected" and lat:
                    txt += f" (detection latency mean {st.mean(lat):.2f} s, n={len(lat)})"
                out.append(txt)
            elif c == "detection_latency_s":
                continue
            else:
                out.append(f"{c}: mean {st.mean(v):.3f} min {min(v):.3f} max {max(v):.3f} sum {sum(v):g} (n={len(v)})")
        print(f"{mode:10s} {arm:3s} n={len(sub):2d} | " + " | ".join(out))
