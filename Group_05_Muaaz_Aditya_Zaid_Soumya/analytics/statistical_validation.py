"""
Statistical validation of the patrol trials | owner E075 Zaid Rezaur Rahman

Reads analytics/campus_patrol_real_trials.csv (contract A: one row per run) and its provenance record
analytics/campus_patrol_real_trials.provenance.json. Nothing is typed in here: every number printed is computed
from the CSV. It REFUSES (exit 2) a missing file, a CSV without a provenance record, a provenance
"csv_sha256" that is not the sha256 of the CSV (the file was edited or regenerated without provenance), a provenance
record that is not a JSON object with a "not_applicable" entry, and any file that contains SIMULATED_ markers.

  python analytics/statistical_validation.py [--scene interior|exterior|all] [--alpha 0.05]
         [--csv PATH] [--provenance PATH] [--out analytics/statistical_validation_output.txt]

Tests, within one scene, groups = the rows of one condition, runs treated as independent (seeds are shared across
conditions, so a paired test is a valid alternative; it is not run here):
  PRIMARY    guard_baseline vs uav_sectors      on cycle_time_s (mean time per completed full ground lap;
             independent of the run window, so it is fair although the guard runs longer than the UAVs;
             needs >= 2 lap completions in a run, else the cell is empty)
  SECONDARY  uav_sectors    vs uav_offset_ring  on cycle_time_s
  worst_revisit_ground_eqwin_s (longest unserviced interval of any ground checkpoint inside ONE common window, column
  eqwin_s) is NOT tested: the guard value is right-censored at the window (no revisit inside it, value = eqwin_s, sd 0),
  so t, d and CI would be meaningless. It is reported descriptively: per cell the count of censored runs (value >=
  eqwin_s, analytics/censored_revisit.py), the guard as ">= eqwin_s (right-censored)", and the UAV worst revisit max.
  The un-windowed worst_revisit_ground_s is reported per condition as context only.
Welch two-sided t test (no equal-variance assumption):
  diff = mean(A) - mean(B);  se = sqrt(sA^2/nA + sB^2/nB);  t = diff / se
  df (Welch-Satterthwaite) = se^4 / ( (sA^2/nA)^2/(nA-1) + (sB^2/nB)^2/(nB-1) )
  p = 2 * P(T_df > |t|)   (exact, scipy.stats.t.sf)
  95 % CI of the difference = diff +/- t_{1-alpha/2, df} * se
  Cohen's d = diff / s_pooled,  s_pooled = sqrt( ((nA-1) sA^2 + (nB-1) sB^2) / (nA + nB - 2) )
Also per scene and condition: detection rate k/n with the Wilson score interval and the exact (Clopper-Pearson)
interval, detection latency, thrust effort (sum F^2 dt, N^2 s) and torque effort (integral |tau|^2 dt, N^2 m^2 s),
cross-track RMSE and waypoint RMSE, minimum obstacle clearance (interior: all obstacles are sensed, FR-18), minimum
UAV-UAV separation and contact counts, laps per agent. Columns that the CSV does not carry (an older batch) are
reported as "column absent", never imputed. sd is the sample sd (ddof = 1); mean CIs use t with n-1 df.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import censored_revisit as cr  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(HERE, "campus_patrol_real_trials.csv")
DEFAULT_OUT = os.path.join(HERE, "statistical_validation_output.txt")
SCENES = ("interior", "exterior")
CONDITIONS = ("guard_baseline", "uav_sectors", "uav_offset_ring")
UAV_CONDITIONS = ("uav_sectors", "uav_offset_ring")
PRIMARY_PAIR = ("guard_baseline", "uav_sectors")
SECONDARY_PAIR = ("uav_sectors", "uav_offset_ring")
PRIMARY_METRIC = "cycle_time_s"
EQWIN_METRIC = "worst_revisit_ground_eqwin_s"
REQUIRED_COLS = ("run_id", "scene", "condition", "seed", "duration_s", "cycle_time_s", "worst_revisit_ground_s",
                 "detected", "min_obstacle_clearance_m", "obstacle_contacts")
D_SAFE_M = 2.5   # design separation of the controller (src/aerial_patrol_swarm.py d_safe); same constant as campus_security_fmea.D_SAFE_M


class Refused(Exception):
    pass


def default_provenance(csv_path):
    return os.path.splitext(csv_path)[0] + ".provenance.json"


def file_sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load_validated(csv_path, prov_path=None):
    """Return (rows, provenance, sha256) after the provenance, hash and SIMULATED_ gates. Raises Refused."""
    prov_path = prov_path or default_provenance(csv_path)
    if os.path.basename(csv_path).startswith("SIMULATED_"):
        raise Refused(f"{csv_path} is a SIMULATED_* placeholder")
    if not os.path.isfile(csv_path):
        raise Refused(f"CSV not found: {csv_path}")
    if not os.path.isfile(prov_path):
        raise Refused(f"no provenance record for {os.path.basename(csv_path)} (expected {os.path.basename(prov_path)})")
    csv_text = open(csv_path, newline="").read()
    prov_text = open(prov_path).read()
    for name, text in (("CSV", csv_text), ("provenance", prov_text)):
        if re.search(r"SIMULATED_", text):          # case sensitive: the windows block legitimately says simulated_duration_s
            raise Refused(f"{name} contains SIMULATED_ markers")
    try:
        prov = json.loads(prov_text)
    except ValueError as e:
        raise Refused(f"provenance is not valid JSON: {e}")
    if not isinstance(prov, dict) or "not_applicable" not in prov:
        raise Refused('provenance must be a JSON object with a "not_applicable" entry (contract A)')
    digest = file_sha256(csv_path)
    if prov.get("csv_sha256") != digest:
        raise Refused(f"{os.path.basename(csv_path)} sha256 {digest} != provenance csv_sha256 {prov.get('csv_sha256')}: "
                      "the CSV was edited or regenerated without its provenance record")
    rows = list(csv.DictReader(csv_text.splitlines()))
    if not rows:
        raise Refused("CSV has no rows")
    missing = [c for c in REQUIRED_COLS if c not in rows[0]]
    if missing:
        raise Refused(f"CSV lacks required columns: {', '.join(missing)}")
    for r in rows:
        if r["scene"] not in SCENES or r["condition"] not in CONDITIONS:
            raise Refused(f"unknown scene/condition in run {r['run_id']}: {r['scene']}/{r['condition']}")
    return rows, prov, digest


def has_col(rows, name):
    return name in rows[0]


def column(rows, scene, condition, name):
    """Numeric values of one column for one (scene, condition); empty cells skipped."""
    out = []
    for r in rows:
        if r["scene"] == scene and r["condition"] == condition:
            v = (r.get(name) or "").strip()
            if v == "":
                continue
            try:
                out.append(float(v))
            except ValueError:
                raise Refused(f"non-numeric value '{v}' in column {name} (run {r['run_id']})")
    return np.array(out, dtype=float)


def cell_rows(rows, scene, condition):
    return [r for r in rows if r["scene"] == scene and r["condition"] == condition]


def welch(a, b, alpha=0.05):
    """Welch two-sided t test of mean(a) - mean(b). Returns a dict, or {'error': reason}."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return {"error": f"need n >= 2 in both groups (n = {na}, {nb})"}
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se2 = va / na + vb / nb
    if se2 == 0.0:
        return {"error": "both groups have zero variance; t undefined"}
    se = math.sqrt(se2)
    diff = ma - mb
    t = diff / se
    df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    p = 2.0 * stats.t.sf(abs(t), df)
    tcrit = stats.t.ppf(1.0 - alpha / 2.0, df)
    sp2 = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
    d = diff / math.sqrt(sp2) if sp2 > 0 else float("nan")
    return {"na": na, "nb": nb, "ma": ma, "mb": mb, "sa": math.sqrt(va), "sb": math.sqrt(vb),
            "diff": diff, "se": se, "t": t, "df": df, "p": p, "d": d,
            "ci_lo": diff - tcrit * se, "ci_hi": diff + tcrit * se, "reject": bool(p < alpha)}


def mean_ci(x, alpha=0.05):
    """(mean, lo, hi) with a t interval, or None for n < 2."""
    n = len(x)
    if n < 2:
        return None
    m, s = x.mean(), x.std(ddof=1)
    h = stats.t.ppf(1.0 - alpha / 2.0, n - 1) * s / math.sqrt(n)
    return m, m - h, m + h


def wilson_ci(k, n, alpha=0.05):
    """Wilson score interval for a binomial proportion k/n."""
    if n == 0:
        return None
    z = stats.norm.ppf(1.0 - alpha / 2.0)
    ph = k / n
    den = 1.0 + z * z / n
    centre = (ph + z * z / (2 * n)) / den
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def exact_ci(k, n, alpha=0.05):
    """Clopper-Pearson exact binomial interval."""
    if n == 0:
        return None
    lo = 0.0 if k == 0 else stats.beta.ppf(alpha / 2.0, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1.0 - alpha / 2.0, k + 1, n - k)
    return lo, hi


def windows_text(rows, prov, scene):
    """Run windows per condition (from the CSV duration_s and eqwin_s columns) as printable text."""
    parts = []
    for c in CONDITIONS:
        d = sorted({float(r["duration_s"]) for r in cell_rows(rows, scene, c)})
        parts.append(f"{c} {'/'.join(f'{x:g}' for x in d)} s")
    eq = sorted({float(r["eqwin_s"]) for r in rows if r["scene"] == scene and (r.get("eqwin_s") or "").strip()}) \
        if has_col(rows, "eqwin_s") else []
    return "; ".join(parts), eq


def fmt_p(p):
    return f"{p:.6e}"


def pair_lines(rows, scene, metric, pair, label, alpha, unit=""):
    ca, cb = pair
    L = [f"{label}: {ca} (A) vs {cb} (B), metric {metric}"]
    if not has_col(rows, metric):
        return L + [f"  column {metric} absent from this CSV (batch predates it); test not computed"], None
    a, b = column(rows, scene, ca, metric), column(rows, scene, cb, metric)
    for name, x in ((ca, a), (cb, b)):
        if len(x):
            sd = f"{x.std(ddof=1):.4f}" if len(x) > 1 else "n/a"
            L.append(f"  {name:16s} n={len(x):3d}  mean={x.mean():.4f}  sd={sd}")
        else:
            L.append(f"  {name:16s} n=  0  (no values: not measured for this cell)")
    r = welch(a, b, alpha)
    if "error" in r:
        L.append(f"  test not computed: {r['error']}")
        return L, None
    L += [f"  mean difference A - B = {r['diff']:.4f}   se = {r['se']:.4f}",
          f"  Welch t = {r['t']:.4f}   df (Welch-Satterthwaite) = {r['df']:.3f}   two-sided p = {fmt_p(r['p'])}",
          f"  Cohen's d = {r['d']:.4f}  (pooled sd = sqrt(((nA-1)sA^2 + (nB-1)sB^2)/(nA+nB-2)))",
          f"  {100 * (1 - alpha):.0f} % CI of the mean difference (t, Welch df): [{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]"]
    verdict = "REJECT equal means" if r["reject"] else "FAIL TO REJECT equal means"
    L.append(f"  decision at alpha = {alpha}: p {'<' if r['reject'] else '>='} {alpha} -> {verdict}")
    return L, r


def metric_lines(rows, scene, name, label, alpha, per=CONDITIONS, with_min=False):
    L = []
    if not has_col(rows, name):
        return [f"  {label}: column {name} absent from this CSV"]
    for c in per:
        x = column(rows, scene, c, name)
        if not len(x):
            L.append(f"  {c:16s} {label}: not applicable or not measured (no values)")
            continue
        ci = mean_ci(x, alpha)
        s = f"n={len(x)} mean={x.mean():.4f}"
        if ci:
            s += f" sd={x.std(ddof=1):.4f} {100 * (1 - alpha):.0f} % CI [{ci[1]:.4f}, {ci[2]:.4f}]"
        if with_min:
            s += f" min={x.min():.4f} max={x.max():.4f}"
        L.append(f"  {c:16s} {label}: {s}")
    return L


def censored_lines(rows, scene):
    """Equal-window worst revisit, descriptive only (right-censored; no t test, d or CI is computed on it)."""
    L = [f"Equal-window worst revisit ({EQWIN_METRIC}), descriptive only: right-censored at eqwin_s, NO t test / d / CI"]
    if not has_col(rows, EQWIN_METRIC):
        return L + [f"  column {EQWIN_METRIC} absent from this CSV"]
    for c in CONDITIONS:
        st_ = cr.cell_stats(rows, scene, c)
        if st_ is None:
            L.append(f"  {c:16s} not measured (no values)")
            continue
        cen = f"censored runs (no revisit inside {st_['window_s']:g} s): {st_['k_censored']} of {st_['n']}"
        if st_["k_censored"] == st_["n"]:
            L.append(f"  {c:16s} worst revisit {cr.guard_value_text(st_['window_s'])}; {cen}")
        else:
            x = np.array(st_["values"])
            L.append(f"  {c:16s} n={st_['n']} mean={x.mean():.4f} sd={x.std(ddof=1):.4f} min={x.min():.4f} "
                     f"max={x.max():.4f} (values >= {st_['window_s']:g} s are lower bounds); {cen}")
    L.append("  " + cr.descriptive_line(rows, scene, "guard_baseline", UAV_CONDITIONS))
    return L


def scene_report(rows, prov, scene, alpha):
    L = [f"=== scene: {scene} ==="]
    for c in CONDITIONS:
        L.append(f"  runs {c}: {len(cell_rows(rows, scene, c))}")
    wtxt, eq = windows_text(rows, prov, scene)
    L.append(f"  run windows (duration_s): {wtxt}")
    L.append("  equal window for the revisit comparison (eqwin_s): "
             + (", ".join(f"{x:g} s" for x in eq) if eq else "column absent or empty (batch predates equal-window revisit)"))
    L.append(f"  Caption: PRIMARY metric {PRIMARY_METRIC} = mean time per completed full ground lap, window-independent; "
             f"equal-window revisit = longest unserviced interval of any ground checkpoint inside the common window (descriptive only, right-censored, no test); "
             f"Welch two-sided t (Satterthwaite df), exact p, Cohen's d (pooled sd), t-based {100 * (1 - alpha):.0f} % CI of the difference; "
             "runs treated as independent; N per cell as printed.")
    L.append("")
    out = {}
    for pair, label in ((PRIMARY_PAIR, "PRIMARY"), (SECONDARY_PAIR, "SECONDARY")):
        lines, res = pair_lines(rows, scene, PRIMARY_METRIC, pair, label, alpha)
        L += lines
        out[("cycle", pair)] = res
    L.append("Context only (window-dependent, never a cross-condition comparison): worst_revisit_ground_s over each run's own window")
    L += metric_lines(rows, scene, "worst_revisit_ground_s", "worst_revisit_ground_s", alpha)
    L += censored_lines(rows, scene)
    L.append("")
    L.append(f"DETECTION (intruder verified inside the run window; windows differ by condition, see above; "
             f"{100 * (1 - alpha):.0f} % intervals)")
    for c in CONDITIONS:
        cr = cell_rows(rows, scene, c)
        n = len(cr)
        k = sum(1 for r in cr if (r["detected"] or "0").strip() in ("1", "1.0"))
        w, e = wilson_ci(k, n, alpha), exact_ci(k, n, alpha)
        lat = column(rows, scene, c, "detection_latency_s")
        lt = f"; detection_latency_s mean={lat.mean():.2f} s (n={len(lat)})" if len(lat) else "; detection_latency_s not measured (no detected run)"
        if n:
            L.append(f"  {c:16s} detected {k}/{n} = {k / n:.4f}  Wilson [{w[0]:.4f}, {w[1]:.4f}]  exact [{e[0]:.4f}, {e[1]:.4f}]{lt}")
    L.append("")
    L.append("UAV EFFORT AND TRACKING (UAV cells; the guard is a kinematic walker, no actuators)")
    L += metric_lines(rows, scene, "control_effort_N2s", "thrust effort sum F^2 dt (N^2 s)", alpha, UAV_CONDITIONS)
    L += metric_lines(rows, scene, "torque_effort_N2m2s", "torque effort int |tau|^2 dt (N^2 m^2 s)", alpha, UAV_CONDITIONS)
    L += metric_lines(rows, scene, "tracking_rmse_m", "cross-track RMSE (m)", alpha, UAV_CONDITIONS)
    L += metric_lines(rows, scene, "waypoint_rmse_m", "waypoint RMSE (m)", alpha, UAV_CONDITIONS)
    L += metric_lines(rows, scene, "energy_wh", "energy (Wh)", alpha, UAV_CONDITIONS)
    for nm in ("n_laps_alpha", "n_laps_bravo", "n_laps_guard", "n_ground_laps"):
        L += metric_lines(rows, scene, nm, nm, alpha, with_min=True)
    L.append("")
    L.append("SAFETY (FR-18 obstacle sensing; in the interior the UAVs must sense all obstacles)")
    L += metric_lines(rows, scene, "min_obstacle_clearance_m", "min_obstacle_clearance_m", alpha, UAV_CONDITIONS, with_min=True)
    L += metric_lines(rows, scene, "min_inter_uav_m", "min_inter_uav_m (m)", alpha, UAV_CONDITIONS, with_min=True)
    for c in UAV_CONDITIONS:
        cr = cell_rows(rows, scene, c)
        oc = [float(r["obstacle_contacts"]) for r in cr if (r["obstacle_contacts"] or "").strip() != ""]
        uu = [float(r["uav_uav_contacts"]) for r in cr if has_col(rows, "uav_uav_contacts") and (r["uav_uav_contacts"] or "").strip() != ""]
        sep = [float(r["min_inter_uav_m"]) for r in cr if (r.get("min_inter_uav_m") or "").strip() != ""]
        L.append(f"  {c:16s} obstacle_contacts total={int(sum(oc))} over {len(oc)} runs ({sum(1 for x in oc if x > 0)} runs with contact); "
                 f"uav_uav_contacts total={int(sum(uu))} over {len(uu)} runs; runs with min_inter_uav_m < {D_SAFE_M} m: "
                 f"{sum(1 for x in sep if x < D_SAFE_M)} of {len(sep)}")
    L.append("")
    return L, out


def build_report(rows, prov, digest, csv_path, alpha, scenes):
    L = [f"file: {os.path.basename(csv_path)}   rows: {len(rows)}   sha256: {digest} (matches provenance csv_sha256)   alpha: {alpha}",
         f"primary metric: {PRIMARY_METRIC}; equal-window metric: {EQWIN_METRIC}",
         f"provenance: generator {prov.get('generator')}, git_commit {prov.get('git_commit', prov.get('e043_commit'))}, "
         f"trials_per_cell {prov.get('trials_per_cell')}, timestep_s {prov.get('timestep_s')}", ""]
    for s in scenes:
        lines, _ = scene_report(rows, prov, s, alpha)
        L += lines
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", default="all", choices=("interior", "exterior", "all"))
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--out", default=None, help="also write the report here (default analytics/statistical_validation_output.txt "
                                                "only when --csv is the canonical file; always printed)")
    args = ap.parse_args(argv)
    try:
        rows, prov, digest = load_validated(args.csv, args.provenance)
        lines = build_report(rows, prov, digest, args.csv, args.alpha, SCENES if args.scene == "all" else (args.scene,))
    except Refused as e:
        print(f"[REFUSED] {e}")
        return 2
    text = "\n".join(lines) + "\n"
    print(text, end="")
    out = args.out
    if out is None and os.path.abspath(args.csv) == os.path.abspath(DEFAULT_CSV) and args.scene == "all":
        out = DEFAULT_OUT
    if out:
        with open(out, "w") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
