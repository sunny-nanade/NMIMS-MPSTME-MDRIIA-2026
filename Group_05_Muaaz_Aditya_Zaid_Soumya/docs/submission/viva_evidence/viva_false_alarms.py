"""Viva-prep summary: false alarms and verify rejects per cell, from runs[*].surveillance in the provenance JSON (not a CSV column)."""
import json, collections, os
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "analytics", "campus_patrol_real_trials.provenance.json")
runs = json.load(open(P))["runs"]
agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for rid, x in sorted(runs.items()):
    s = x.get("surveillance")
    if not s:
        continue
    scene, cond = rid.split("_", 1)[0], rid.split("_", 1)[1].rsplit("_s", 1)[0]
    a = agg[(scene, cond)]
    a[0] += 1; a[1] += s["false_alarms"]; a[2] += s["verify_rejects"]; a[3] = max(a[3], s["false_alarms"])
    a[4] += len(s.get("incidents", []))
print("run ids with surveillance records:", sum(v[0] for v in agg.values()), "of", len(runs))
for (sc, cd), v in sorted(agg.items()):
    print(f"{sc:9s} {cd:16s} runs={v[0]:2d} false_alarms total={v[1]:3d} mean/run={v[1]/v[0]:.2f} max/run={v[3]} verify_rejects total={v[2]:3d} incidents total={v[4]}")
