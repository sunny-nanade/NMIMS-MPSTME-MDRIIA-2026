# CSBS Campus Security FMEA (E077) | MDRIIA Group 05
# O and D come from measured failure rates (real-trials CSV, ablation CSV). S is team judgement.
"""
FMEA for the campus patrol, RPN = S x O x D (each 1-10).

Inputs
  analytics/campus_patrol_real_trials.csv + .provenance.json   (main batch; hash checked)
  analytics/ablation_trials.csv + .provenance.json              (G-15 ablation batch; hash checked)
If either file, or its provenance csv_sha256, is missing the script exits with an error.

Per-run ablation CSV schema (one row per run; analytics/run_ablations.py writes it, this script only reads it):
  run_id, mode, arm, flag, flag_value, scene, condition, seed, ... ; metric columns that do not belong to a
  mode are blank in that mode's rows (never imputed). All modes are measured in the interior scene only, so
  the exterior FMEA rows print "not measured".
    mode = separation   arm off = APF-only separation, on = layered separation (production)
           columns: min_inter_uav_m, uav_uav_contacts
    mode = fr18         arm off = FR-18 avoidance disabled, on = production
           columns: obstacle_contacts, min_obstacle_clearance_m
    mode = geofence     arm off = hysteresis disabled, on = production, with position noise
           columns: geofence_spurious_breaches = spurious breach-log events per run (a false geofence alarm);
                    also written: geofence_spurious_escalations (spurious tier rises), geofence_escalations,
                    geofence_breach_events, geofence_log_events. The spurious tier rises are reported next to
                    the FMEA row (print_fmea) because the hysteresis lowers but does not remove them.
    mode = twilight     arm off = twilight exposure fix disabled, on = production (lighting_scale 0.15)
           columns: detected (0/1), detection_latency_s (blank when not detected)
  The "on" arm must be the production code path; "off" toggles exactly one mitigation (explicit flag,
  recorded in the ablation provenance).

Per-mode rates (k = count, n = runs; all definitions are ASSUMPTIONS of this script, printed in the output)
  O from the failure rate p_O = k_O / n_O :
      separation          failure = min_inter_uav_m < D_SAFE_M (2.5 m)
      fr18                failure = obstacle_contacts > 0
      geofence            failure = run with >= 1 spurious breach event
      twilight            failure = run with no detection
  D from the escape rate p_D = k_D / n_D, the share of hazard events the system does not contain:
      separation          hazard = min_inter_uav_m < D_SAFE_M      escape = uav_uav_contacts > 0
      fr18                hazard = contact or clearance < NEAR_OBSTACLE_M     escape = contact
      geofence            hazard = run with >= 1 spurious breach event  escape = >= 2 events (repeated, not suppressed)
      twilight            hazard = detected run                       escape = detection_latency_s > LATE_DETECTION_S
  With no hazard event D = 1 (nothing escaped), except twilight with no detected run, D = 10.
  Rows without an ablation mode (intruder_not_detected) keep the team-judgement D and say so.

"before" = off arm (mitigation disabled), "after" = on arm (production). The 95 % interval on a
rate is Clopper-Pearson (exact binomial); off vs on is compared with Fisher's exact test (two-sided).
"""
import csv
import hashlib
import json
import math
import os

from scipy.stats import beta, fisher_exact

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "campus_patrol_real_trials.csv")
PROV_PATH = os.path.join(HERE, "campus_patrol_real_trials.provenance.json")
ABLATION_PATH = os.path.join(HERE, "ablation_trials.csv")
ABLATION_PROV_PATH = os.path.join(HERE, "ablation_trials.provenance.json")

SCENES = ("interior", "exterior")
UAV_CONDITIONS = ("uav_sectors", "uav_offset_ring")
D_SAFE_M = 2.5            # design separation, src/aerial_patrol_swarm.py (d_safe)
NEAR_OBSTACLE_M = 0.5     # ASSUMPTION: obstacle clearance below this counts as a near miss
LATE_DETECTION_S = 60.0   # ASSUMPTION: a detection later than this has escaped early containment

# Detection score from the escape rate p_D (upper bound inclusive): p_D = 0 -> 1, then the bands below.
DETECTION_BANDS = ((0.01, 2), (0.05, 3), (0.10, 4), (0.20, 5), (0.35, 6), (0.50, 7), (0.70, 8), (0.90, 9), (1.0, 10))


# ----------------------------------------------------------------------------- integrity
def verify_csv_sha256(csv_path, prov_path):
    """sha256 of csv_path, checked against the 'csv_sha256' key of the provenance JSON; exits loudly on any problem."""
    if not os.path.isfile(csv_path):
        raise SystemExit(f"missing data file: {csv_path}")
    if not os.path.isfile(prov_path):
        raise SystemExit(f"missing provenance file {prov_path}: cannot verify {os.path.basename(csv_path)}")
    with open(prov_path) as f:
        prov = json.load(f)
    expected = prov.get("csv_sha256")
    if not expected:
        raise SystemExit(f"{os.path.basename(prov_path)} has no 'csv_sha256' key: regenerate the data with its "
                         "batch script (it records the hash) before running the analysis")
    with open(csv_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != expected:
        raise SystemExit(f"{os.path.basename(csv_path)} changed: sha256 {digest} != {expected} recorded in "
                         f"{os.path.basename(prov_path)}")
    return digest


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ----------------------------------------------------------------------------- scores
def occurrence(k, n):
    """O score from k failures in n runs: round(10 + 4 log10 p), clipped 1..10, 1 when k = 0 (ASSUMPTION scale)."""
    if n <= 0:
        raise ValueError("occurrence needs at least one run")
    if k == 0:
        return 1
    return int(min(10, max(1, math.floor(10 + 4 * math.log10(k / n) + 0.5))))


def detection(k, n, empty=1):
    """D score from k escapes among n hazard events; `empty` is the score when there is no hazard event."""
    if n <= 0:
        return empty
    p = k / n
    if p == 0:
        return 1
    for upper, score in DETECTION_BANDS:
        if p <= upper:
            return score
    return 10


def occurrence_table():
    """[(O, lo, hi)] failure-rate band per O score, derived from the occurrence formula."""
    out = []
    for o in range(1, 11):
        lo = 0.0 if o == 1 else 10 ** ((o - 0.5 - 10) / 4)
        hi = 1.0 if o == 10 else 10 ** ((o + 0.5 - 10) / 4)
        out.append((o, lo, hi))
    return out


def clopper_pearson(k, n, alpha=0.05):
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def rate_text(k, n, score, label):
    lo, hi = clopper_pearson(k, n)
    return f"{label}={score} ({k}/{n}, 95% CI {lo:.2f}-{hi:.2f})"


def mapping_text():
    lines = ["Rate-to-score mapping (ASSUMPTION of this script, not a cited table)",
             "  Occurrence O from failure rate p = k/n  (O = round(10 + 4 log10 p), 1 if k = 0):"]
    for o, lo, hi in occurrence_table():
        lines.append(f"    O = {o:>2}  p in {'[0' if o == 1 else '[' + format(lo, '.4f')}, {hi:.4f}{']' if o == 10 else ')'}"
                     + ("   (and any p with k = 0)" if o == 1 else ""))
    lines.append("  Detection D from escape rate p_D = k_D/n_D:  p_D = 0 -> 1, "
                 + ", ".join(f"<= {u:g} -> {s}" for u, s in DETECTION_BANDS) + ".")
    lines.append(f"  Near miss: obstacle clearance < {NEAR_OBSTACLE_M:g} m; late detection: latency > {LATE_DETECTION_S:g} s (ASSUMPTIONS).")
    return lines


# ----------------------------------------------------------------------------- ablation data
GEOFENCE_COLUMNS = ("geofence_spurious_breaches",)


def _f(r, col):
    v = r.get(col, "")
    if v in ("", None):
        raise SystemExit(f"ablation row {r.get('run_id', '?')} has a blank {col}")
    return float(v)


def _geo(r):
    for col in GEOFENCE_COLUMNS:
        if col in r:
            return _f(r, col)
    raise SystemExit(f"ablation row {r.get('run_id', '?')}: none of {GEOFENCE_COLUMNS} present")


# mode -> (failure predicate, hazard predicate, escape predicate, D when no hazard event, required columns)
ABLATION_MODES = {
    "separation": (
        lambda r: _f(r, "min_inter_uav_m") < D_SAFE_M,
        lambda r: _f(r, "min_inter_uav_m") < D_SAFE_M,
        lambda r: _f(r, "uav_uav_contacts") > 0, 1, ("min_inter_uav_m", "uav_uav_contacts")),
    "fr18": (
        lambda r: _f(r, "obstacle_contacts") > 0,
        lambda r: _f(r, "obstacle_contacts") > 0 or _f(r, "min_obstacle_clearance_m") < NEAR_OBSTACLE_M,
        lambda r: _f(r, "obstacle_contacts") > 0, 1, ("obstacle_contacts", "min_obstacle_clearance_m")),
    "geofence": (
        lambda r: _geo(r) >= 1, lambda r: _geo(r) >= 1, lambda r: _geo(r) >= 2, 1, ("geofence_spurious_breaches",)),
    "twilight": (
        lambda r: r["detected"] != "1",
        lambda r: r["detected"] == "1",
        lambda r: _f(r, "detection_latency_s") > LATE_DETECTION_S, 10, ("detected", "detection_latency_s")),
}


def load_ablation(csv_path=ABLATION_PATH, prov_path=ABLATION_PROV_PATH):
    """Verified ablation rows. Exits with an error if the file, its provenance or its hash is missing."""
    if not os.path.isfile(csv_path):
        raise SystemExit(f"missing {csv_path}: the ablation batch (G-15) has not been run; the FMEA needs its "
                         "measured rates and will not print placeholders")
    verify_csv_sha256(csv_path, prov_path)
    rows = read_rows(csv_path)
    if not rows:
        raise SystemExit(f"{csv_path} has no rows")
    for col in ("mode", "arm", "seed"):
        if col not in rows[0]:
            raise SystemExit(f"{csv_path}: missing column {col}")
    for r in rows:
        if r["mode"] not in ABLATION_MODES:
            raise SystemExit(f"{csv_path}: unknown mode {r['mode']!r} (expected {sorted(ABLATION_MODES)})")
        if r["arm"] not in ("off", "on"):
            raise SystemExit(f"{csv_path}: arm must be off or on, got {r['arm']!r}")
        for col in ABLATION_MODES[r["mode"]][4]:
            if col not in r:
                raise SystemExit(f"{csv_path}: mode {r['mode']} needs column {col}")
    return rows


def ablation_arm(abl_rows, mode, arm, scene):
    """Rates of one arm: dict(n, k_o, n_h, k_d, D_empty) or None when the CSV has no such runs.
    Filters on the scene column when it exists; otherwise all rows of that mode are pooled."""
    fail, hazard, escape, d_empty, _ = ABLATION_MODES[mode]
    sel = [r for r in abl_rows if r["mode"] == mode and r["arm"] == arm
           and ("scene" not in r or r["scene"] in ("", scene))]
    if not sel:
        return None
    haz = [r for r in sel if hazard(r)]
    return dict(n=len(sel), k_o=sum(1 for r in sel if fail(r)), n_h=len(haz),
                k_d=sum(1 for r in haz if escape(r)), d_empty=d_empty)


# ----------------------------------------------------------------------------- the FMEA
# key, ablation mode, title, effect, S (judgement), D judgement before/after (used only without an ablation mode),
# mitigation state, mitigation, evidence
MODES = (
    ("uav_uav_conflict", "separation", "UAV-UAV conflict at sector crossing (d < 2.5 m)",
     "airframe contact, both vehicles lost", 9, None, None, "implemented (E043)",
     "layered altitude separation plus distance governor on top of APF (ablation off arm = APF only)",
     "tests/test_e043_separation.py; analytics/ablation_trials.csv mode=separation"),
    ("missed_intruder_twilight", "twilight", "Missed intruder at twilight (low light)",
     "no ALERT; patrol continues past the intruder", 8, None, None, "implemented (E051)",
     "twilight exposure fix in the detector path (ablation off arm = fix disabled)",
     "tests/test_e051_vision.py; analytics/ablation_trials.csv mode=twilight"),
    ("false_geofence_alarm", "geofence", "False geofence alarm from position noise",
     "spurious tier escalation, guard sent for nothing", 4, None, None, "implemented (E075)",
     "exit margin plus tier-3 dwell on evaluate_geofence_status (ablation off arm = hysteresis disabled, noisy position)",
     "tests/test_e075_geofence_stats.py; analytics/ablation_trials.csv mode=geofence"),
    ("intruder_not_detected", None, "Intruder not detected in a patrol run (any lighting)",
     "breach goes unnoticed", 8, 6, 4, "implemented (E043 with E051 detector)",
     "UAV patrol with camera detection replaces guard rounds",
     "CSV column detected (guard_baseline = before, UAV conditions = after); D = team judgement"),
    ("unseen_obstacle", "fr18", "Collision with an obstacle the UAV did not sense (FR-18)",
     "crash into furniture, column or wall; patrol aborted", 8, None, None, "implemented (E043)",
     "range-ring sensing of all obstacles with avoidance never disabled (FR-18; ablation off arm = avoidance disabled)",
     "tests/test_e043_obstacle_perception.py; analytics/ablation_trials.csv mode=fr18"),
)


def counts(rows, scene, conditions, failed):
    sel = [r for r in rows if r["scene"] == scene and r["condition"] in conditions]
    return sum(1 for r in sel if failed(r)), len(sel)


def fmea_table(rows, abl_rows):
    """Per (scene, mode) dict with the scores and the printed text. `rows` = main CSV, `abl_rows` = ablation CSV."""
    if not abl_rows:
        raise SystemExit("FMEA needs the ablation rows (analytics/ablation_trials.csv)")
    out = {}
    for scene in SCENES:
        for key, mode, title, effect, s, db_j, da_j, state, mitigation, evidence in MODES:
            row = dict(title=title, effect=effect, S=s, state=state, mitigation=mitigation, evidence=evidence,
                       mode=mode, scene=scene)
            if mode is None:   # main-CSV rate, judgement D
                before = (*counts(rows, scene, ("guard_baseline",), lambda r: r["detected"] != "1"),)
                after = (*counts(rows, scene, UAV_CONDITIONS, lambda r: r["detected"] != "1"),)
                for tag, (k, n), d in (("before", before, db_j), ("after", after, da_j)):
                    o = occurrence(k, n)
                    label = "guard_baseline" if tag == "before" else "uav_sectors + uav_offset_ring"
                    row[tag] = rate_text(k, n, o, "O") + f" [{label}; D = {d}, team judgement]"
                    row["O_" + tag], row["D_" + tag], row["rpn_" + tag] = o, d, s * o * d
                    row["k_" + tag], row["n_" + tag] = k, n
                row["fisher_p"] = fisher_exact([[before[0], before[1] - before[0]], [after[0], after[1] - after[0]]])[1]
                row["Db"], row["Da"] = db_j, da_j
                out[(scene, key)] = row
                continue
            arms = {a: ablation_arm(abl_rows, mode, a, scene) for a in ("off", "on")}
            if arms["off"] is None or arms["on"] is None:
                msg = f"not measured: ablation_trials.csv has no {mode} runs for both arms in scene {scene}"
                row.update(before=msg, after=msg, O_before=None, O_after=None, D_before=None, D_after=None,
                           rpn_before=None, rpn_after=None, Db=None, Da=None, fisher_p=None)
                out[(scene, key)] = row
                continue
            for tag, arm in (("before", "off"), ("after", "on")):
                a = arms[arm]
                o = occurrence(a["k_o"], a["n"])
                d = detection(a["k_d"], a["n_h"], a["d_empty"])
                row[tag] = (rate_text(a["k_o"], a["n"], o, "O") + "; "
                            + (rate_text(a["k_d"], a["n_h"], d, "D") + " of hazard runs" if a["n_h"]
                               else f"D={d} (no hazard run)")
                            + f" [arm {arm}]")
                row["O_" + tag], row["D_" + tag], row["rpn_" + tag] = o, d, s * o * d
                row["k_" + tag], row["n_" + tag] = a["k_o"], a["n"]
            row["Db"], row["Da"] = row["D_before"], row["D_after"]
            row["fisher_p"] = fisher_exact([[arms["off"]["k_o"], arms["off"]["n"] - arms["off"]["k_o"]],
                                            [arms["on"]["k_o"], arms["on"]["n"] - arms["on"]["k_o"]]])[1]
            out[(scene, key)] = row
    return out


def geofence_residual(abl_rows):
    """Mean spurious tier escalations and breach events per run, off vs on, from the ablation CSV (None if absent)."""
    out = {}
    for arm in ("off", "on"):
        sel = [r for r in abl_rows if r["mode"] == "geofence" and r["arm"] == arm]
        if not sel or any(r.get(c, "") in ("", None) for r in sel
                          for c in ("geofence_spurious_escalations", "geofence_spurious_breaches")):
            return None
        out[arm] = tuple(sum(_f(r, c) for r in sel) / len(sel)
                         for c in ("geofence_spurious_escalations", "geofence_spurious_breaches"))
    return out


def print_fmea(rows, abl_rows):
    table = fmea_table(rows, abl_rows)
    resid = geofence_residual(abl_rows)
    for scene in SCENES:
        print(f"FMEA, scene = {scene}  (RPN = S x O x D; O and D from measured rates, S = team judgement)")
        for key, *_ in MODES:
            r = table[(scene, key)]
            rpn_b = "not measured" if r["rpn_before"] is None else str(r["rpn_before"])
            rpn_a = "not measured" if r["rpn_after"] is None else str(r["rpn_after"])
            print(f"[{key}] {r['title']}")
            print(f"  effect: {r['effect']}")
            print(f"  S = {r['S']} (judgement)")
            print(f"  before: {r['before']}  RPN_before = {rpn_b}")
            print(f"  after : {r['after']}  RPN_after  = {rpn_a}")
            if r["fisher_p"] is not None:
                print(f"  failure rate before vs after, Fisher exact p = {r['fisher_p']:.3g}")
            if key == "false_geofence_alarm" and resid and r["rpn_before"] is not None:
                print(f"  residual (mean per run, off -> on): spurious tier escalations {resid['off'][0]:.1f} -> "
                      f"{resid['on'][0]:.1f}; spurious breach events {resid['off'][1]:.1f} -> {resid['on'][1]:.1f} "
                      "(the hysteresis lowers spurious tier rises but does not remove them)")
            print(f"  mitigation [{r['state']}]: {r['mitigation']}")
            print(f"  evidence: {r['evidence']}")
        print()
    for line in mapping_text():
        print(line)
    print("  95 % CI = Clopper-Pearson. Ablation arms: before = mitigation off, after = production code path.")
    return table


if __name__ == "__main__":
    verify_csv_sha256(CSV_PATH, PROV_PATH)
    print_fmea(read_rows(CSV_PATH), load_ablation())
