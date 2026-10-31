"""Viva-prep: re-derive the main-batch checks from the committed CSV and provenance (nothing is written).
Run from anywhere:  python docs/submission/viva_evidence/viva_batch_validation.py
Checks: row count, paired seeds, timestep, contacts, separation, laps, MANIFEST dt_check, provenance commit and hashes of the CSV."""
import csv, collections, hashlib, json, os, statistics as st

A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "analytics")
CSV, PROV = os.path.join(A, "campus_patrol_real_trials.csv"), os.path.join(A, "campus_patrol_real_trials.provenance.json")
rows = list(csv.DictReader(open(CSV)))
prov = json.load(open(PROV))
raw = open(CSV, "rb").read()
print(f"rows = {len(rows)}; trials_per_cell (provenance) = {prov['trials_per_cell']}; git_commit (provenance) = {prov['git_commit']}; timestep_s (provenance) = {prov['timestep_s']}")
print("csv sha256 file =", hashlib.sha256(raw).hexdigest(), "| provenance csv_sha256 =", prov["csv_sha256"],
      "| equal:", hashlib.sha256(raw).hexdigest() == prov["csv_sha256"])
cells = collections.defaultdict(list)
for r in rows:
    cells[(r["scene"], r["condition"])].append(r)
seeds = {k: sorted(int(r["seed"]) for r in v) for k, v in cells.items()}
print("cells:", len(cells), "| run_id unique:", len({r["run_id"] for r in rows}) == len(rows),
      "| identical seed sets in every cell:", len({tuple(v) for v in seeds.values()}) == 1,
      "| timestep values:", sorted({r["timestep_s"] for r in rows}))
def f(r, c):
    return float(r[c]) if r[c] != "" else None
for (sc, cd), v in sorted(cells.items()):
    line = f"{sc:9s} {cd:16s} n={len(v)} seeds {seeds[(sc, cd)][0]}..{seeds[(sc, cd)][-1]}"
    if cd != "guard_baseline":
        oc = [(int(r["seed"]), int(float(r["obstacle_contacts"]))) for r in v if float(r["obstacle_contacts"]) > 0]
        mi = [f(r, "min_inter_uav_m") for r in v]
        la = {k: [int(float(r[k])) for r in v] for k in ("n_laps_alpha", "n_laps_bravo")}
        line += (f" | obstacle_contacts total {sum(c for _, c in oc)} in {len(oc)} runs {oc}"
                 f" | uav_uav_contacts total {int(sum(float(r['uav_uav_contacts']) for r in v))}"
                 f" | min_inter_uav_m min {min(mi):.3f}, runs below 2.5 m {sum(x < 2.5 for x in mi)}"
                 f" | laps alpha min/median/max {min(la['n_laps_alpha'])}/{st.median(la['n_laps_alpha']):g}/{max(la['n_laps_alpha'])}"
                 f", bravo {min(la['n_laps_bravo'])}/{st.median(la['n_laps_bravo']):g}/{max(la['n_laps_bravo'])}")
    print(line)
mf = os.path.join(A, "runs", "MANIFEST.csv")
if os.path.isfile(mf):
    m = list(csv.DictReader(open(mf)))
    print("MANIFEST.csv rows", len(m), "| dt_check values", sorted({r.get("dt_check", "") for r in m}))
else:
    print("MANIFEST.csv not found")
