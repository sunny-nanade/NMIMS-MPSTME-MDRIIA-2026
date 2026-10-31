#!/usr/bin/env python
"""Print every number spoken or shown in the LinkedIn video next to its value in the final (rerun) batch.

Run from the group folder:
    python docs/submission/print_video_vs_final.py > docs/submission/VIDEO_VS_FINAL_NUMBERS.md

Nothing in the tables is typed. Sources:
  OLD (Part 1, the first batch the video was written from):
      docs/submission/video_numbers_output.txt   (committed, unchanged)  -> cycle time, revisit, detection, safety, tracking, effort
      docs/submission/VIDEO_NUMBERS.md           (committed, unchanged)  -> economics table, FMEA lines, queue lines
  NEW (final rerun):
      analytics/campus_patrol_real_trials.csv    via docs/submission/print_video_numbers.py (re-run here; it refuses unless the
                                                 CSV sha256 equals its provenance record)
      analytics/campus_security_economics_output.txt  -> economics, FMEA, queue lines
      analytics/statistical_validation_output.txt     -> cross-check of the Welch statistics
Reason phrases are explanations, not results; every number inside them is computed from the parsed values.
Currency is never printed. A value missing on one side prints "not in Part 1 doc" / "not in final", never a guess.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP = os.path.normpath(os.path.join(HERE, "..", ".."))
OLD_OUT = os.path.join(HERE, "video_numbers_output.txt")
OLD_MD = os.path.join(HERE, "VIDEO_NUMBERS.md")
SCRIPT_MD = os.path.join(HERE, "video_script_and_shotlist.md")
ECON_OUT = os.path.join(GROUP, "analytics", "campus_security_economics_output.txt")
STAT_OUT = os.path.join(GROUP, "analytics", "statistical_validation_output.txt")
CSV_PROV = os.path.join(GROUP, "analytics", "campus_patrol_real_trials.provenance.json")

SCENES = ("interior", "exterior")
UAVS = ("uav_sectors", "uav_offset_ring")
NUM = r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?"


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- video_numbers_output.txt parser (old and new format)
def parse_vn(text):
    d = {"welch": {}, "det": {}, "safe": {}, "met": {}, "eq": {}, "clean": {}, "guardrev": {}, "eqcen": {}}
    section = ""
    blk = None
    cell = None
    for ln in text.splitlines():
        m = re.match(r"^(\d+b?)\. ", ln)
        if m:
            section = m.group(1)
            blk = None
            continue
        m = re.match(r"^\[(\w+)\] (\w+) vs (\w+)(?:, metric (\w+))?", ln)
        if m and section in ("1", "1b"):
            sc, a, b, met = m.groups()
            blk = d["welch"].setdefault((sc, a, b, met or "cycle_time_s"), {"means": []})
            continue
        if blk is not None:
            m = re.match(r"\s+mean_(\S+)=(%s) s sd(?:_\w+)?=(%s)" % (NUM, NUM), ln)
            if m:
                blk["means"].append((m.group(2), m.group(3)))
                continue
            m = re.match(r"\s+mean_difference=(%s) s\s+(?:guard/uav ratio|ratio \S+)=(%s)" % (NUM, NUM), ln)
            if m:
                blk["diff"], blk["ratio"] = m.groups()
                continue
            m = re.match(r"\s+Welch t=(%s)\s+df=(%s)\s+p\(two-sided\)=(%s)\s+Cohen d=(%s)" % (NUM, NUM, NUM, NUM), ln)
            if m:
                blk["t"], blk["df"], blk["p"], blk["d"] = m.groups()
                continue
            m = re.match(r"\s+95%% CI of mean difference: (%s) to (%s)" % (NUM, NUM), ln)
            if m:
                blk["ci_lo"], blk["ci_hi"] = m.groups()
                continue
        if section == "1b":
            m = re.match(r"^\[(\w+)\] (\w+)\s+mean=(%s) sd=(%s) n=" % (NUM, NUM), ln)
            if m:
                d["eq"][(m.group(1), m.group(2))] = (m.group(3), m.group(4))
            m = re.match(r"^\[(\w+)\] (\w+)\s+.*censored runs (\d+) of (\d+)", ln)
            if m:
                d["eqcen"][(m.group(1), m.group(2))] = (m.group(3), m.group(4))
            m = re.match(r"^\[(\w+)\] (\w+)\s+worst revisit (>= \S+ s \(right-censored\));", ln)
            if m:
                d["eq"][(m.group(1), m.group(2))] = (m.group(3), None)
        if section == "2":
            m = re.match(r"^\[(\w+)\] (\w+)\s+detected (\d+)/(\d+)(.*?)mean detection_latency_s=(%s)\s+\(n_latency=(\d+)\);?\s+run duration_s=(%s)" % (NUM, NUM), ln)
            if m:
                sc, cond, k, n, mid, lat, nl, dur = m.groups()
                w = re.search(r"Wilson 95%% \[(%s), (%s)\]" % (NUM, NUM), mid)
                d["det"][(sc, cond)] = dict(k=int(k), n=int(n), lat=lat, nl=int(nl), dur="%g" % float(dur),
                                            wil=(float(w.group(1)), float(w.group(2))) if w else None)
        if section == "3":
            m = re.match(r"^\[(\w+)\] (uav_\w+)\s+runs=", ln)
            if m:
                cell = d["safe"].setdefault((m.group(1), m.group(2)), {})
                continue
            m = re.match(r"^\[(\w+)\] UAV runs \(both policies\) with 0 obstacle contacts: (\d+) of (\d+)", ln)
            if m:
                d["clean"][m.group(1)] = "%s of %s" % (m.group(2), m.group(3))
                continue
            if cell is not None:
                m = re.search(r"min of min_obstacle_clearance_m = (%s) m" % NUM, ln)
                if m:
                    cell["clr"] = m.group(1)
                m = re.search(r"obstacle_contacts: total=(\d+) over (\d+) runs; runs with contacts=(\d+) of (\d+)", ln)
                if m:
                    cell["contacts"], cell["runs_hit"] = m.group(1), "%s of %s" % (m.group(3), m.group(4))
                m = re.search(r"min of min_inter_uav_m = (%s) m" % NUM, ln)
                if m:
                    cell["sep"] = m.group(1)
                m = re.search(r"runs below the %s m design separation: (\d+) of (\d+)" % NUM, ln)
                if m:
                    cell["sep_below"] = "%s of %s" % m.groups()
                m = re.search(r"uav_uav_contacts total = (\d+)", ln)
                if m:
                    cell["uu"] = m.group(1)
        if section == "4":
            m = re.match(r"^\[(\w+)\] (uav_\w+)\s+(tracking_rmse_m|cross-track RMSE \(m\)|control_effort_N2s|thrust effort sum F\^2 dt \(N\^2 s\)|worst_revisit_ground_s|worst revisit over own window \(s\))\s+mean=(%s) sd=(%s)" % (NUM, NUM), ln)
            if m:
                key = {"tracking_rmse_m": "rmse", "cross-track RMSE (m)": "rmse", "control_effort_N2s": "thrust",
                       "thrust effort sum F^2 dt (N^2 s)": "thrust", "worst_revisit_ground_s": "rev",
                       "worst revisit over own window (s)": "rev"}[m.group(3)]
                d["met"][(m.group(1), m.group(2), key)] = (m.group(4), m.group(5))
            m = re.match(r"^\[(\w+)\] guard_baseline worst_revisit_ground_s (?:over its own window: )?mean=(%s) sd=(%s)" % (NUM, NUM), ln)
            if m:
                d["guardrev"][m.group(1)] = (m.group(2), m.group(3))
    return d


# ---------------------------------------------------------------- economics parsers
def parse_econ_new(text):
    r = {"cell": {}, "fmea": {}, "gate_pass": 0, "gate_total": 0, "h": {}, "wq_uav": {}, "wq_guard": {}}
    scene = cond = None
    fm_scene = fm_mode = None
    for ln in text.splitlines():
        m = re.match(r"^SCENE: (\w+)", ln)
        if m:
            scene = m.group(1)
            cond = None
            continue
        m = re.match(r"^(uav_\w+) cycle_time_s mean", ln)
        if m and scene:
            cond = m.group(1)
            r["cell"][(scene, cond)] = {}
            continue
        if re.match(r"^FMEA, scene = (\w+)", ln):
            fm_scene = re.match(r"^FMEA, scene = (\w+)", ln).group(1)
            scene = cond = None
            continue
        if scene and cond:
            c = r["cell"][(scene, cond)]
            if ln.startswith("  gate (") and "revisit" in ln:
                r["gate_total"] += 1
                r["gate_pass"] += 1 if ln.strip().endswith("PASS") else 0
            m = re.search(r"H_reclaimed (%s) guard-hours/day  delta FTE = [^=]*= (%s)" % (NUM, NUM), ln)
            if m:
                c["h"], c["fte"] = m.groups()
            m = re.match(r"\s+kappa (%s)" % NUM, ln)
            if m:
                c["kappa"] = m.group(1)
            m = re.search(r"NCRI = 1 - kappa (%s)\s+envelope (%s) \.\. (%s)" % (NUM, NUM, NUM), ln)
            if m:
                c["ncri"], c["ncri_lo"], c["ncri_hi"] = m.groups()
            m = re.match(r"\s+P_payback (%s)\s+envelope (%s) \.\. (%s)" % (NUM, NUM, NUM), ln)
            if m:
                c["p"], c["p_lo"], c["p_hi"] = m.groups()
            m = re.search(r"T_payback (%s) months" % NUM, ln)
            if m:
                c["t"] = m.group(1)
            m = re.search(r"break-even crossing \(full search, P_payback = 1\): capex_ratio = (%s)" % NUM, ln)
            if m:
                c["be"] = m.group(1)
            m = re.search(r"M/M/c lambda base .*?W_q=(%s) s" % NUM, ln)
            if m:
                c["wq"] = m.group(1)
            m = re.search(r"guard M/M/c base .*?W_q=(%s) s" % NUM, ln)
            if m:
                c["wq_guard"] = m.group(1)
        if fm_scene:
            m = re.match(r"^\[(\w+)\] ", ln)
            if m:
                fm_mode = m.group(1)
                r["fmea"][(fm_scene, fm_mode)] = {}
                continue
            if fm_mode:
                f = r["fmea"][(fm_scene, fm_mode)]
                m = re.match(r"\s+(before|after)\s*: (.*?)\s+RPN_(?:before|after)\s+= (.+)$", ln)
                if m:
                    f[m.group(1)] = m.group(3).strip()
                    o = re.search(r"O=\d+ \((\d+/\d+)", m.group(2))
                    f[m.group(1) + "_O"] = o.group(1) if o else None
    return r


def parse_econ_old(md):
    r = {"cell": {}, "fmea": {}, "gate": None, "h": [], "be_int_sec": None, "wq": None, "wq_guard": None, "sha": None}
    for m in re.finditer(r"^\| (\w+), (uav_\w+) \| (%s)[^|]*\| (%s) \((%s) \.\. (%s)\) \| (%s) \((%s) \.\. (%s)\) \| (%s) months" %
                         ((NUM,) * 8), md, re.M):
        sc, cond, kappa, ncri, nlo, nhi, p, plo, phi, t = m.groups()
        r["cell"][(sc, cond)] = dict(kappa=kappa, ncri=ncri, ncri_lo=nlo, ncri_hi=nhi, p=p, p_lo=plo, p_hi=phi, t=t)
    m = re.search(r"Revisit gate [^:]*: (PASS in all \d+ UAV cells)", md)
    r["gate"] = m.group(1) if m else None
    r["h"] = re.findall(r"H_reclaimed (%s) guard-hours/day  delta FTE = [^=]*= (%s)" % (NUM, NUM), md)
    m = re.search(r"P_payback = 1 at capex_ratio = (%s)" % NUM, md)
    r["be_int_sec"] = m.group(1) if m else None
    m = re.search(r"M/M/c lambda base .*?W_q=(%s) s" % NUM, md)
    r["wq"] = m.group(1) if m else None
    m = re.search(r"guard M/M/c base .*?W_q=(%s) s" % NUM, md)
    r["wq_guard"] = m.group(1) if m else None
    m = re.search(r"sha256 ([0-9a-f]{8,})", md)
    r["sha"] = m.group(1)[:16] if m else None
    for ln in md.splitlines():
        m = re.search(r"`(\w+)`.*?`RPN_before = (\d+)`.*?`RPN_after\s+= (\d+)`", ln)
        if m:
            low = ln.lower()
            sc = "interior" if low.find("interior") != -1 and (low.find("exterior") == -1 or low.find("interior") < low.find("exterior")) else "exterior"
            ks = re.findall(r"(\d+/\d+)", ln)
            r["fmea"][(sc, m.group(1))] = dict(before=m.group(2), after=m.group(3), ks=ks)
    return r


# ---------------------------------------------------------------- formatting helpers
def to_f(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def delta(old, new):
    mo = re.match(r"^(\d+)(?:/| of )(\d+)$", str(old))
    mn = re.match(r"^(\d+)(?:/| of )(\d+)$", str(new))
    if mo and mn and mo.group(2) == mn.group(2):
        return "%+d" % (int(mn.group(1)) - int(mo.group(1)))
    a, b = to_f(old), to_f(new)
    if a is None or b is None or "e" in str(old).lower() or "e" in str(new).lower():
        return "-"
    nd = max(len(str(old).split(".")[1]) if "." in str(old) else 0, len(str(new).split(".")[1]) if "." in str(new) else 0)
    return "%+.*f" % (nd, b - a)


class Table:
    def __init__(self, title, script_text):
        self.title, self.rows, self.script = title, [], script_text

    def add(self, label, old, new, reason):
        self.rows.append((label, old, new, reason))

    def render(self):
        out = ["", "### " + self.title, "", "| Quantity | Video (Part 1) | Final (rerun) | Change | In script text | Why |",
               "| :--- | :--- | :--- | :--- | :--- | :--- |"]
        for label, old, new, reason in self.rows:
            o = "not in Part 1 doc" if old is None else str(old)
            n = "not in final" if new is None else str(new)
            if old is None:
                ch = "new"
            elif new is None:
                ch = "dropped"
            elif str(old) == str(new):
                ch = "same"
            else:
                ch = delta(old, new)
            ins = "-"
            tok = str(old).split()[0] if old is not None else ""
            if len(tok) >= 5 and "." in tok:
                ins = "yes" if tok in self.script else "no"
            why = "unchanged: same seeds and same guard model" if ch == "same" and "guard" in label.lower() else reason
            if ch == "same" and "guard" not in label.lower():
                why = "unchanged"
            out.append("| %s | %s | %s | %s | %s | %s |" % (label, o, n, ch, ins, why))
        return "\n".join(out)


def main():
    old_txt, old_md, script = read(OLD_OUT), read(OLD_MD), read(SCRIPT_MD)
    r = subprocess.run([sys.executable, os.path.join(HERE, "print_video_numbers.py")], cwd=GROUP,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("[REFUSED] print_video_numbers.py exit %d: %s" % (r.returncode, (r.stdout + r.stderr)[:400]))
        return 2
    new_txt = r.stdout
    new_econ_txt = read(ECON_OUT)
    prov = json.load(open(CSV_PROV, encoding="utf-8"))
    o, n = parse_vn(old_txt), parse_vn(new_txt)
    eo, en = parse_econ_old(old_md), parse_econ_new(new_econ_txt)
    sha_new = re.search(r"sha256 ([0-9a-f]{64})", new_txt).group(1)
    commit_new = prov.get("git_commit", "not recorded")

    # windows, computed
    dur_old = {(k[0], k[1]): v["dur"] for k, v in o["det"].items()}
    dur_new = {(k[0], k[1]): v["dur"] for k, v in n["det"].items()}
    uav_old = sorted({dur_old[(s, c)] for s in SCENES for c in UAVS})
    uav_new = sorted({dur_new[(s, c)] for s in SCENES for c in UAVS})
    w_old, w_new = float(uav_old[0]), float(uav_new[0])
    win_old, win_new = "/".join(uav_old), "/".join(uav_new)

    R_FLIGHT = "flight fixes (G-06 atrium contact, G-07 separation, G-08 lap rules) change the flown paths; full rerun"
    R_FLIGHT_WIN = "flight fixes and the %s s UAV window (was %s s)" % (win_new, win_old)
    R_EXT_RING = "flight fixes, including the exterior patrol layer raised to 22 m (626b71f)"

    md = []
    P = md.append
    P("# Video numbers against the final batch")
    P("")
    P("Generated by `python docs/submission/print_video_vs_final.py > docs/submission/VIDEO_VS_FINAL_NUMBERS.md` (run inside the group folder). "
      "Nothing in the tables is typed: the Part 1 column is parsed from the committed `video_numbers_output.txt` and `VIDEO_NUMBERS.md` "
      "(both unchanged), the Final column from `print_video_numbers.py` re-run on the committed CSV, the committed economics output and the committed statistics output.")
    P("")
    P("## Which batch is which")
    P("")
    P("- The video script (`video_script_and_shotlist.md`) and the post were written from the **first batch** (Part 1): CSV sha256 starting `%s`, UAV windows %s s." % (eo["sha"] or "not recorded", win_old))
    P("- The Technical Dossier uses the **rerun**: CSV sha256 `%s`, generator commit `%s`, UAV windows %s s, equal comparison window %s s." %
      (sha_new, commit_new, win_new, "/".join(sorted({re.search(r'eqwin_s: (\d+) s', ln).group(1) for ln in new_txt.splitlines() if 'equal window eqwin_s' in ln}))))
    P("- Both are honest records of the code and data that existed when each was run. **The dossier is authoritative.** "
      "Where a spoken number differs, say the dossier number, or re-record. Do not read a Part 1 number on camera as if it were the final result.")
    P("")
    P("## Why numbers changed (applies to every row marked changed)")
    P("")
    P("1. Flight fixes between the two batches: G-06 (interior seed 7 atrium-tree contact), G-07 (UAV-UAV separation floor of 2.5 m), G-08 (every UAV completes laps; window-independent primary metric), plus the waypoint-copy fix to the offset_ring routes and the exterior patrol layer raised from 20 m to 22 m (Bravo 24 m to 26 m; 626b71f) so Alpha clears the 19.2 m roof beside leg patrol_cp6 -> cp7. The flown paths therefore differ run by run.")
    P("2. UAV window is %s s in the rerun (was %s s in Part 1). Anything summed or counted over the run (thrust effort, laps, detections that need time) scales with it. The guard windows are unchanged." % (win_new, win_old))
    P("3. Equal-window revisit (G-08): the Part 1 video used worst revisit over each run's own window, which is not comparable between a %s s UAV run and the guard's own longer run. The rerun adds a metric over one common window." % win_new)
    P("4. G-14: the interior detection path was reworked; the rerun measures it, it does not assume an improvement (see section 2).")
    P("5. Economics (E077): kappa, NCRI, payback and the FMEA are recomputed from the new CSV and the ablation CSV, so they move with the cycle times and revisits above. All cost inputs are still ASSUMPTION ranges; ratios only.")
    P("6. The guard condition uses the same seeds and the same guard model in both batches, so guard rows are expected to be identical.")
    P("")
    hit_cells = ["%s %s (%s runs)" % (k[0], k[1], v["runs_hit"]) for k, v in n["safe"].items() if not v["runs_hit"].startswith("0 ")]
    if hit_cells:
        P("A failed check is reported, not hidden: in the rerun these cells have obstacle contacts (section 3): %s. Their means include those runs." % "; ".join(hit_cells))
    else:
        P("Obstacle contacts in the rerun: none in any UAV cell (section 3, parsed from the final output).")
    P("")
    P("The **In script text** column is a plain text match: `yes` means the Part 1 value, as printed, appears in `video_script_and_shotlist.md`; `-` means a short count or integer that is not matched by this check.")

    # 1. cycle time
    P("")
    P("## 1. Cycle time per completed lap (cycle_time_s), guard against UAV")
    for sc in SCENES:
        t = Table("%s: guard_baseline vs UAV policies" % sc, script)
        for cond in UAVS:
            ob = o["welch"].get((sc, "guard_baseline", cond, "cycle_time_s"))
            nb = n["welch"].get((sc, "guard_baseline", cond, "cycle_time_s"))
            if cond == UAVS[0]:
                t.add("guard_baseline mean (s)", ob["means"][0][0], nb["means"][0][0], "")
                t.add("guard_baseline sd (s)", ob["means"][0][1], nb["means"][0][1], "")
            t.add("%s mean (s)" % cond, ob["means"][1][0], nb["means"][1][0], R_FLIGHT_WIN)
            t.add("%s sd (s)" % cond, ob["means"][1][1], nb["means"][1][1], R_FLIGHT_WIN)
            for key, lab in (("diff", "mean difference (s)"), ("ratio", "guard / UAV ratio"), ("t", "Welch t"),
                             ("df", "Welch df"), ("p", "p (two-sided)"), ("d", "Cohen's d"),
                             ("ci_lo", "95% CI low (s)"), ("ci_hi", "95% CI high (s)")):
                t.add("%s: %s" % (cond, lab), ob[key], nb[key], R_FLIGHT_WIN)
        md.append(t.render())
    sec = Table("Added in the rerun: UAV sectors vs offset_ring (SECONDARY test)", script)
    for sc in SCENES:
        nb = n["welch"].get((sc, "uav_sectors", "uav_offset_ring", "cycle_time_s"))
        if nb:
            for key, lab in (("diff", "mean difference sectors - offset_ring (s)"), ("t", "Welch t"), ("p", "p (two-sided)"), ("d", "Cohen's d")):
                sec.add("%s: %s" % (sc, lab), None, nb[key], "comparison not used in the video")
    md.append(sec.render())

    # cross-check with statistical_validation_output.txt
    stat = read(STAT_OUT)
    ok = bad = 0
    bad_list = []
    cur_scene = None
    cur_block = None
    for ln in stat.splitlines():
        m = re.match(r"=== scene: (\w+) ===", ln)
        if m:
            cur_scene = m.group(1)
        m = re.match(r"(PRIMARY|SECONDARY): (\w+) \(A\) vs (\w+) \(B\), metric cycle_time_s", ln)
        if m and cur_scene:
            cur_block = (cur_scene, m.group(2), m.group(3))
            continue
        m = re.match(r"\s+Welch t = (%s)\s+df \(Welch-Satterthwaite\) = (%s)" % (NUM, NUM), ln)
        if m and cur_block:
            nb = n["welch"].get(cur_block + ("cycle_time_s",))
            if nb:
                for a, b, nm in ((m.group(1), nb["t"], "t"), (m.group(2), nb["df"], "df")):
                    if a == b:
                        ok += 1
                    else:
                        bad += 1
                        bad_list.append((cur_block, nm, a, b))
            cur_block = None
    P("")
    P("Cross-check of the final Welch t and df against the committed `analytics/statistical_validation_output.txt`: %d values agree, %d differ%s." %
      (ok, bad, "" if not bad else " (" + "; ".join("%s %s: stats %s, script %s" % x for x in bad_list) + ")"))

    # 1b worst revisit
    P("")
    P("## 1b. Worst ground revisit")
    t = Table("Own-window worst revisit (the metric in the two boxplots of Part 1; window-dependent)", script)
    for sc in SCENES:
        og, ng = o["guardrev"].get(sc), n["guardrev"].get(sc)
        t.add("%s guard_baseline mean (s)" % sc, og[0] if og else None, ng[0] if ng else None, "")
        t.add("%s guard_baseline sd (s)" % sc, og[1] if og else None, ng[1] if ng else None, "")
        for cond in UAVS:
            a, b = o["met"].get((sc, cond, "rev")), n["met"].get((sc, cond, "rev"))
            t.add("%s %s mean (s)" % (sc, cond), a[0] if a else None, b[0] if b else None, R_FLIGHT_WIN)
            t.add("%s %s sd (s)" % (sc, cond), a[1] if a else None, b[1] if b else None, R_FLIGHT_WIN)
    md.append(t.render())
    t = Table("Equal-window worst revisit (window %s s for every condition; added in the rerun; right-censored, no test)" % win_new, script)
    for sc in SCENES:
        for cond in ("guard_baseline",) + UAVS:
            a, b = o["eq"].get((sc, cond)), n["eq"].get((sc, cond))
            c = n["eqcen"].get((sc, cond))
            note = "metric did not exist in Part 1 (G-08)"
            if cond == "guard_baseline":
                t.add("%s %s worst revisit (s)" % (sc, cond), a[0] if a else None, b[0] if b else None, note + "; guard value is a lower bound, no t test")
            else:
                t.add("%s %s mean (s)" % (sc, cond), a[0] if a else None, b[0] if b else None, note)
                t.add("%s %s sd (s)" % (sc, cond), a[1] if a else None, b[1] if b else None, note)
            t.add("%s %s censored runs (no revisit inside the window)" % (sc, cond), None, "%s of %s" % c if c else None, note)
    md.append(t.render())

    # 2 detection
    P("")
    P("## 2. Detection")
    t = Table("Detected out of N and mean detection latency of the detected runs", script)
    for sc in SCENES:
        for cond in ("guard_baseline",) + UAVS:
            a, b = o["det"].get((sc, cond)), n["det"].get((sc, cond))
            if cond == "guard_baseline":
                why = ""
            elif sc == "interior":
                why = "G-14 interior detection rework, flight fixes, %s s window (was %s s)" % (win_new, win_old)
            else:
                why = R_FLIGHT_WIN
            t.add("%s %s detected" % (sc, cond), "%d/%d" % (a["k"], a["n"]) if a else None, "%d/%d" % (b["k"], b["n"]) if b else None, why)
            t.add("%s %s latency (s, n_latency)" % (sc, cond), "%s (n=%d)" % (a["lat"], a["nl"]) if a else None,
                  "%s (n=%d)" % (b["lat"], b["nl"]) if b else None, why)
            t.add("%s %s run window (s)" % (sc, cond), a["dur"] if a else None, b["dur"] if b else None,
                  "" if cond == "guard_baseline" else "window shortened")
    md.append(t.render())
    P("")
    for sc in SCENES:
        g, s = n["det"][(sc, "guard_baseline")], n["det"][(sc, "uav_sectors")]
        ring = n["det"][(sc, "uav_offset_ring")]
        ov = lambda x, y: max(x["wil"][0], y["wil"][0]) <= min(x["wil"][1], y["wil"][1]) if x["wil"] and y["wil"] else None
        P("- Final, %s: the Wilson 95%% interval of the guard rate overlaps that of uav_sectors: %s, and that of uav_offset_ring: %s. "
          "The windows differ by condition, so a rate difference is not a like-for-like comparison." %
          (sc, "yes" if ov(g, s) else "no", "yes" if ov(g, ring) else "no"))
    P("- The video's honest-limits line (\"no interior detection improvement claimed\") stays correct only if you read the final counts above; do not say 11 of 30 for both on camera.")

    # 3 safety
    P("")
    P("## 3. Safety (UAV cells)")
    t = Table("Obstacle clearance, contacts and UAV-UAV separation", script)
    for sc in SCENES:
        for cond in UAVS:
            a, b = o["safe"].get((sc, cond), {}), n["safe"].get((sc, cond), {})
            why_c = "G-06 fixed the interior atrium contact" if sc == "interior" else (R_EXT_RING if cond == "uav_offset_ring" else R_FLIGHT)
            why_s = "G-07 separation fix"
            t.add("%s %s min obstacle clearance (m)" % (sc, cond), a.get("clr"), b.get("clr"), "flight fixes: paths and avoidance changed (G-06, G-07); minimum over 30 runs")
            t.add("%s %s obstacle contacts, total" % (sc, cond), a.get("contacts"), b.get("contacts"), why_c)
            t.add("%s %s runs with contacts" % (sc, cond), a.get("runs_hit"), b.get("runs_hit"), why_c)
            t.add("%s %s min inter-UAV distance (m)" % (sc, cond), a.get("sep"), b.get("sep"), why_s)
            t.add("%s %s runs below the design separation" % (sc, cond), a.get("sep_below"), b.get("sep_below"),
                  "check added after Part 1" if a.get("sep_below") is None else why_s)
            t.add("%s %s UAV-UAV contacts" % (sc, cond), a.get("uu"), b.get("uu"), "")
        t.add("%s UAV runs (both policies) with 0 obstacle contacts" % sc, o["clean"].get(sc), n["clean"].get(sc),
              "G-06 fixed the interior contact" if sc == "interior" else R_EXT_RING)
    md.append(t.render())
    P("")
    P("- The Part 1 wording \"0 contacts in 59 of 60 interior UAV runs; one contact found and being fixed\" is superseded for the interior by the final counts above (G-06). "
      "Do not say it on camera as the current result.")
    hit = [(k[0], k[1], v["runs_hit"], v["contacts"]) for k, v in n["safe"].items() if not v["runs_hit"].startswith("0 ")]
    if hit:
        P("- Final failures that the video did not know about: " + "; ".join("%s %s has contacts in %s runs (%s contacts in total)" % h for h in hit) +
          ". They are reported here and in the dossier; they are not hidden.")
    low = [(k[0], k[1], v["sep"]) for k, v in n["safe"].items() if to_f(v["sep"]) is not None and to_f(v["sep"]) < 2.5]
    P("- Separation: final UAV cells with a minimum inter-UAV distance below the 2.5 m design line: %s. The video's offset_ring statement (minimum below 2.5 m, from Part 1) is superseded by the final numbers (G-07)." %
      ("none" if not low else "; ".join("%s %s (%s m)" % x for x in low)))

    # 4 tracking/effort
    P("")
    P("## 4. Tracking and effort (mean over N runs)")
    t = Table("Cross-track RMSE and thrust effort (sum F^2 dt)", script)
    for sc in SCENES:
        for cond in UAVS:
            for key, lab in (("rmse", "cross-track RMSE (m)"), ("thrust", "thrust effort (N^2 s)")):
                a, b = o["met"].get((sc, cond, key)), n["met"].get((sc, cond, key))
                why = R_FLIGHT_WIN
                if key == "thrust" and a and b:
                    why = "summed over the run: window ratio %.3f, value ratio %.3f; plus flight fixes" % (w_new / w_old, float(b[0]) / float(a[0]))
                t.add("%s %s %s mean" % (sc, cond, lab), a[0] if a else None, b[0] if b else None, why)
                t.add("%s %s %s sd" % (sc, cond, lab), a[1] if a else None, b[1] if b else None, why)
    md.append(t.render())

    # 5 economics
    P("")
    P("## 5. Economics (E077): ratios only")
    P("")
    P("Revisit gate: Part 1 \"%s\" on the run's own-window metric; final: %d of %d UAV cells PASS on the equal-window metric." %
      (eo["gate"] or "not recorded", en["gate_pass"], en["gate_total"]))
    t = Table("kappa, NCRI, payback (assumed cost ranges; envelope over 512 corners)", script)
    for sc in SCENES:
        for cond in UAVS:
            a, b = eo["cell"].get((sc, cond), {}), en["cell"].get((sc, cond), {})
            why = "recomputed from the new CSV (cycle time and equal-window revisit changed)"
            t.add("%s %s kappa" % (sc, cond), a.get("kappa"), b.get("kappa"), why)
            t.add("%s %s NCRI" % (sc, cond), a.get("ncri"), b.get("ncri"), why)
            t.add("%s %s NCRI envelope" % (sc, cond), "%s .. %s" % (a["ncri_lo"], a["ncri_hi"]) if a else None,
                  "%s .. %s" % (b["ncri_lo"], b["ncri_hi"]) if b else None, why)
            t.add("%s %s P_payback" % (sc, cond), a.get("p"), b.get("p"), why)
            t.add("%s %s P_payback envelope" % (sc, cond), "%s .. %s" % (a["p_lo"], a["p_hi"]) if a else None,
                  "%s .. %s" % (b["p_lo"], b["p_hi"]) if b else None, why)
            t.add("%s %s T_payback (months)" % (sc, cond), a.get("t"), b.get("t"), why)
    for i, sc in enumerate(SCENES):
        a = eo["h"][i] if i < len(eo["h"]) else (None, None)
        b = en["cell"].get((sc, "uav_sectors"), {})
        t.add("%s H_reclaimed (guard-hours/day)" % sc, a[0], b.get("h"), "recomputed from the new CSV")
        t.add("%s delta FTE" % sc, a[1], b.get("fte"), "recomputed from the new CSV")
    t.add("interior uav_sectors break-even capex_ratio (P_payback = 1)", eo["be_int_sec"],
          en["cell"].get(("interior", "uav_sectors"), {}).get("be"), "recomputed; still outside the assumed range and the +/-30 % sweep")
    t.add("interior uav_sectors M/M/c base W_q, UAV (s)", eo["wq"], en["cell"].get(("interior", "uav_sectors"), {}).get("wq"), "mu from the new detection latency")
    t.add("interior uav_sectors M/M/c base W_q, guard (s)", eo["wq_guard"], en["cell"].get(("interior", "uav_sectors"), {}).get("wq_guard"), "")
    md.append(t.render())
    P("")
    if not n["safe"].get(("exterior", "uav_offset_ring"), {}).get("runs_hit", "0 ").startswith("0 "):
        P("Exterior uav_offset_ring economics use means that include the contact runs reported in section 3 (the economics output prints them in its DATA QUALITY block).")
        P("")
    P("Kappa, NCRI and payback depend on ASSUMPTION ranges; say \"assumed\" when speaking. P_payback below 1 means the fleet pays back inside its assumed service life (P_payback = T_payback / service life); analytics/campus_security_economics.py states this rule next to the formula in its header. No break-even inside the assumed capex_ratio range means it pays back at every capex_ratio in that range, not that it never pays back.")

    # 6 FMEA
    P("")
    P("## 6. FMEA risk priority numbers (RPN = S x O x D; S and part of D are team judgement)")
    t = Table("Before and after RPN", script)
    keys = sorted(set(eo["fmea"]) | set(en["fmea"]))
    for k in keys:
        a, b = eo["fmea"].get(k), en["fmea"].get(k)
        why = "Part 1 took O from the main batch; final takes before/after from the ablation off/on arms (before = mitigation disabled)"
        if a is None:
            why = "mode added after Part 1 (G-15), not spoken in the video"
        if k[1] == "intruder_not_detected":
            why = "same main-batch method in both; counts follow section 2"
        for which in ("before", "after"):
            v = b.get(which) if b else None
            r_ = why
            if v is not None and v.startswith("not measured"):
                r_ = "ablation arms were run in the interior scene only; not measured in the exterior"
            t.add("%s %s RPN %s" % (k[0], k[1], which), a[which] if a else None, v, r_)
        if k[1] == "intruder_not_detected" and b:
            t.add("%s %s occurrence k/n before, after" % k, ", ".join(a["ks"][:2]) if a and a["ks"] else None,
                  "%s, %s" % (b.get("before_O"), b.get("after_O")), "detection counts as in section 2")
    md.append(t.render())
    P("")
    P("Note on the FMEA: a Part 1 RPN and a final RPN for the same mode are not the same measurement. Part 1 derived occurrence from the main batch; the final derives it from the ablation arms (mitigation off, then on), so a larger before value is expected and is not a regression.")
    P("")
    P("The final FMEA adds the geofence and twilight modes with measured before/after RPN; those did not exist in the Part 1 doc and were not spoken in the video.")

    # integrity footer
    P("")
    P("## Reading rule for the video")
    P("")
    P("Every changed row above is a reason to re-read the script against the dossier before recording: the script's own header says that if its numbers differ from the final `VIDEO_NUMBERS.md`, the file wins. "
      "Where this page and the dossier disagree, the dossier wins. No SAP ID, URL or signature appears here; the LinkedIn URL stays a human field.")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
