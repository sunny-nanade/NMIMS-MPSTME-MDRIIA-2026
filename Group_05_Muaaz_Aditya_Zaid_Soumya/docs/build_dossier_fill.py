#!/usr/bin/env python3
"""
Builds docs/DOSSIER_FILL_SHEET.md and docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx (E043, G-26 / G-27).

  python docs/build_dossier_fill.py --write-docx

Rules this script enforces (so the sheet cannot drift from the evidence):
  * The ORIGINAL template (docs/MDRIIA_Group_05_Technical_Dossier.docx) is only read, never written. Its sha256 is
    checked against the value recorded at the start of the task. Template mistakes (9 actuators, Alpha/Bravo roles) are
    corrected ONLY in the autofill draft.
  * Every w:sdt of the template (content control = fill-in field) is walked in document order and must have an entry
    below; a missing or surplus entry stops the build. The count must stay 226 and PENDING must be 0.
  * No number is typed in. Every figure is computed from, or parsed out of: the real-trials CSV (sha256 must equal the
    provenance csv_sha256), analytics/statistical_validation.py (Welch, Cohen's d, CIs, computed live from the CSV and
    cross-checked against analytics/statistical_validation_output.txt), analytics/campus_security_economics_output.txt,
    analytics/campus_security_fmea.py with analytics/ablation_trials.csv, the provenance JSON, the MJCF (mujoco),
    docs/dossier_fill_facts_output.txt, docs/research/standards_verified.md, docs/submission/ai_audit_candidates.md and
    git. What is typed in here is wording, source citations and team-judgement labels that the sheet marks CONFIRM or HUMAN.
  * Stale evidence stops the build: the economics, statistics and facts outputs must carry the sha256 of the CSV in use.
  * The draft .docx fills fields by replacing the text of each content control only. The number of w:sdt elements
    before and after is compared and must be equal.
Status codes: AUTO (derived from a script or a cited source), CONFIRM (derived, but a person must agree),
PENDING (never allowed: every measurable field is filled), HUMAN (only the member can supply it; left empty in the draft).

Test options (smoke data, never committed): --csv --provenance --ablation --ablation-provenance --econ-output --out-dir
--test-mode. A non-canonical CSV needs --out-dir outside docs/ so a test can never overwrite the real sheet or draft.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
import os
import re
import statistics as st
import subprocess
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.dirname(HERE)                         # group folder
R = os.path.dirname(G)                            # repo root
sys.path.insert(0, os.path.join(G, "src"))
sys.path.insert(0, os.path.join(G, "analytics"))
import mujoco                                     # noqa: E402
import aerial_patrol_swarm as aps                 # noqa: E402
import statistical_validation as sv               # noqa: E402
import campus_security_fmea as fmea               # noqa: E402
import censored_revisit as cr                     # noqa: E402

TEMPLATE = os.path.join(HERE, "MDRIIA_Group_05_Technical_Dossier.docx")
TEMPLATE_SHA256 = "3cd2d6f0860c3b3d9f86a0b26227628aca35b05b1f23c1f337fcc7351f431ebc"
DRAFT = os.path.join(HERE, "MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx")
SHEET = os.path.join(HERE, "DOSSIER_FILL_SHEET.md")
CSV_PATH = sv.DEFAULT_CSV
PROV_PATH = sv.default_provenance(CSV_PATH)
ABL_PATH = fmea.ABLATION_PATH
ABL_PROV_PATH = fmea.ABLATION_PROV_PATH
ECON_OUT = os.path.join(G, "analytics", "campus_security_economics_output.txt")
STATS_OUT = sv.DEFAULT_OUT
FACTS_PATH = os.path.join(HERE, "dossier_fill_facts_output.txt")
STANDARDS_MD = os.path.join(HERE, "research", "standards_verified.md")
AUDIT_MD = os.path.join(HERE, "submission", "ai_audit_candidates.md")
FIG_DIRS = (os.path.join(HERE, "figures"), os.path.join(G, "analytics", "figures"))
TEST_MODE = False
FACTS_OUT = "docs/dossier_fill_facts_output.txt"
C = aps.DualUAVSurveillanceController

SCENES = ("interior", "exterior")
CONDS = ("guard_baseline", "uav_sectors", "uav_offset_ring")
UAVC = ("uav_sectors", "uav_offset_ring")
STATS_FILE = "analytics/statistical_validation_output.txt (python analytics/statistical_validation.py)"
ECON_FILE = "analytics/campus_security_economics_output.txt (python analytics/campus_security_economics.py)"
FMEA_FILE = "analytics/campus_security_economics_output.txt FMEA block (analytics/campus_security_fmea.py, analytics/ablation_trials.csv)"


class StaleEvidence(SystemExit):
    pass


# ----------------------------------------------------------------------------- evidence loaders
def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def git(*a):
    return subprocess.check_output(["git", "-C", G, *a], stderr=subprocess.DEVNULL).decode().strip()


def cell_vals(rows, scene, cond, col):
    return [float(r[col]) for r in rows if r["scene"] == scene and r["condition"] == cond and (r.get(col) or "") not in ("",)]


def cell_stat(rows, scene, cond, col):
    v = cell_vals(rows, scene, cond, col)
    return (len(v), st.mean(v), st.stdev(v)) if len(v) > 1 else (len(v), float("nan"), float("nan"))


def ms(rows, scene, cond, col, nd=4):
    if rows and col not in rows[0]:
        return "not measured (column absent)"
    n, m, s = cell_stat(rows, scene, cond, col)
    if n < 2:
        return "not measured (n = %d)" % n
    return f"{m:.{nd}f} ± {s:.{nd}f}"


def durations(rows, scene, cond):
    return "/".join(f"{x:g}" for x in sorted({float(r["duration_s"]) for r in rows if r["scene"] == scene and r["condition"] == cond}))


def eqw(rows, scene, cond):
    """Equal-window worst revisit text. Right-censored cells (guard) are reported as '>= W s', never as a mean/sd/test."""
    cs = cr.cell_stats(rows, scene, cond)
    if cs is None:
        return "not measured"
    cen = "%d of %d runs had no revisit inside %g s" % (cs["k_censored"], cs["n"], cs["window_s"])
    if cs["k_censored"] == cs["n"]:
        return "%s (%s)" % (cr.guard_value_text(cs["window_s"]), cen)
    return "%s s (%s)" % (ms(rows, scene, cond, cr.EQWIN_METRIC, 2), cen)


def eqwin_of(rows, scene):
    if "eqwin_s" not in rows[0]:
        return None
    d = sorted({float(r["eqwin_s"]) for r in rows if r["scene"] == scene and (r["eqwin_s"] or "").strip()})
    return "/".join(f"{x:g}" for x in d) if d else None


def stat_pair(rows, scene, metric, pair):
    """Welch result for one pair, strings formatted for the cells; None when not computable. Uses the analytics script's own functions."""
    if metric not in rows[0]:
        return None
    a, b = sv.column(rows, scene, pair[0], metric), sv.column(rows, scene, pair[1], metric)
    w = sv.welch(a, b)
    if "error" in w:
        return None
    return dict(t=f"{w['t']:.4f}", df=f"{w['df']:.3f}", p=f"{w['p']:.5e}", d=f"{w['d']:.4f}", diff=f"{w['diff']:.4f}",
                ci=(f"{w['ci_lo']:.4f}", f"{w['ci_hi']:.4f}"), na=w["na"], nb=w["nb"], ma=w["ma"], mb=w["mb"], sa=w["sa"], sb=w["sb"])


def check_output_sha(path, label, csv_sha, pattern=r"sha256:? ?([0-9a-f]{64})"):
    """The output file must name the sha256 of the CSV in use; otherwise it was produced from other data."""
    if not os.path.isfile(path):
        return False
    m = re.search(pattern, open(path, encoding="utf-8").read())
    if not m or m.group(1) != csv_sha:
        msg = f"{os.path.relpath(path, G)} is stale: its sha256 {m.group(1)[:16] if m else 'missing'}... != CSV {csv_sha[:16]}... ({label}); regenerate it"
        if TEST_MODE:
            print("[TEST-MODE WARNING] " + msg)
            return False
        raise StaleEvidence("[STALE] " + msg)
    return True


def parse_econ(text):
    """Per scene and UAV condition: the lines the script printed (verbatim values)."""
    res = {}
    src = {}
    for ln in text.splitlines():
        m = re.match(r"^  (\w+)\s+(.+?)\s+\[(.*?)\]\s+(sourced|ASSUMPTION)\s*\Z", ln)
        if m and "=" not in ln.split("[")[0]:
            src[m.group(1)] = (m.group(2).strip(), m.group(3), m.group(4))
    cur_scene = cur_cond = None
    for ln in text.splitlines():
        m = re.match(r"^SCENE: (\w+)", ln)
        if m:
            cur_scene = m.group(1)
            res[cur_scene] = {}
            cur_cond = None
            continue
        if cur_scene is None or ln.startswith("FMEA"):
            if ln.startswith("FMEA"):
                cur_scene = None
            continue
        m = re.match(r"^(guard_baseline|uav_sectors|uav_offset_ring)\s+cycle_time_s", ln)
        if m:
            cur_cond = m.group(1)
            res[cur_scene][cur_cond] = {"head": ln.strip()}
            continue
        if cur_cond is None:
            continue
        d = res[cur_scene][cur_cond]
        for key, pat in (("H", r"^  H_reclaimed\s+([\d.]+) guard-hours/day\s+delta FTE = .* = ([\d.]+)"),
                         ("kappa", r"^  kappa\s+([\d.]+)\s+\(target <= ([\d.]+): (\w+)\)"),
                         ("NCRI", r"^  NCRI = 1 - kappa\s+([\d.]+)\s+envelope ([\d.]+) \.\. ([\d.]+)"),
                         ("P", r"^  P_payback\s+([\d.]+)\s+envelope ([\d.]+) \.\. ([\d.]+)\s+\((\d+) of (\d+) corners never pay back\)"),
                         ("T", r"^  T_payback\s+([\d.]+) months\s+\(battery cycles per UAV-year (\d+)\)"),
                         ("BE_in", r"^  break-even on (\w+) \(P_payback = 1\) inside the assumed range: (.*)\Z"),
                         ("BE_sweep", r"^  break-even inside the \+/-30 % sweep: (.*)\Z"),
                         ("BE", r"^  break-even crossing \(full search, P_payback = 1\): (\w+) = ([\d.]+); (.*)\Z"),
                         ("kappa_cap", r"^  capex_ratio at kappa = target: ([\d.]+)"),
                         ("gate", r"^  gate \(.*\): (\w+)\s*$")):
            mm = re.match(pat, ln)
            if mm:
                d[key] = mm.groups()
        mm = re.match(r"^  M/M/c lambda (low|base|high)\s+lambda=([\d.]+)/h mu=([\d.]+)/h c=(\d+) rho=([\d.]+) P_wait=(\S+) W_q=(\S+) s\s+\[(.*)\]", ln)
        if mm:
            d.setdefault("Q", {})[mm.group(1)] = mm.groups()[1:]
    return res, src


def fmea_dict(table):
    """campus_security_fmea.fmea_table rows -> the shape used by the fill rules."""
    out = {}
    for (scene, key), r in table.items():
        nm = lambda v: "not measured" if v is None else str(v)       # noqa: E731
        out[(scene, key)] = dict(title=r["title"], effect=r["effect"], S=r["S"], Db=r["Db"], Da=r["Da"],
                                 before=r["before"], after=r["after"], rpn_b=nm(r["rpn_before"]), rpn_a=nm(r["rpn_after"]),
                                 mit_state=r["state"], mit=r["mitigation"], evidence=r["evidence"],
                                 fisher_p=r.get("fisher_p"))
    return out


def o_of(txt):
    m = re.match(r"O=(\d+)", txt or "")
    return int(m.group(1)) if m else None


def read_standards():
    """docs/research/standards_verified.md -> rows 1-5 of the template table (dict n -> dict) and the suggested row-5 cell."""
    txt = open(STANDARDS_MD, encoding="utf-8").read()
    rows = {}
    for ln in txt.splitlines():
        m = re.match(r"^\| (\d) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|\s*\Z", ln)
        if m:
            rows[int(m.group(1))] = dict(std=m.group(2), applies=m.group(3), verdict=m.group(4), clause=m.group(5), source=m.group(6), url=m.group(7))
    m = re.search(r'Suggested dossier cell \(T5 R5 C3 = Partly\): "(.+?)"\s*$', txt, re.M)
    assert len(rows) == 5 and m, "standards_verified.md table layout changed"
    return rows, m.group(1)


def standards_cell(row):
    """Clause cell: scope text of the verified row, minus sentences about the superseded edition (L-23 history), plus the first URL."""
    sents = re.split(r"(?<=[.\"])\s+", row["clause"])
    keep = [s for s in sents if "L-23" not in s]
    url = row["url"].split(";")[0].strip()
    return "Not applicable. " + " ".join(keep) + f" Source: {row['source']}; {url}"


def read_audit_cases():
    """First three E043 cases of ai_audit_candidates.md -> dict id -> fields parsed from its bullets."""
    txt = open(AUDIT_MD, encoding="utf-8").read()
    cases = {}
    for m in re.finditer(r"^## (E043-[A-C]): (.+?)\n(.*?)(?=^## |\Z)", txt, re.M | re.S):
        body = m.group(3)
        fields = {}
        for b in re.finditer(r"^- ([A-Za-z0-9 ()/]+?):\s*(.+)$", body, re.M):
            fields.setdefault(b.group(1).strip().lower(), b.group(2).strip())
        cases[m.group(1)] = dict(title=m.group(2).strip(), fields=fields)
    assert len(cases) == 3, "ai_audit_candidates.md must carry cases E043-A, E043-B and E043-C"
    return cases


def first_field(fields, *keys):
    for k in fields:
        for want in keys:
            if k.startswith(want):
                return fields[k]
    return ""


def clip(s, n=900):
    s = re.sub(r"\s+", " ", s.replace("`", "")).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " ..."


# ----------------------------------------------------------------------------- the fill values
def build_fields():
    """Returns (FIELDS dict tag -> (value|None, status, source, note), extras dict). Everything is read from committed outputs."""
    try:
        rows, prov, csv_sha = sv.load_validated(CSV_PATH, PROV_PATH)
    except sv.Refused as e:
        raise SystemExit(f"[REFUSED] {e}")
    for path, label in ((STATS_OUT, "statistical_validation_output.txt"), (ECON_OUT, "campus_security_economics_output.txt")):
        if not os.path.isfile(path):
            if TEST_MODE:
                print(f"[TEST-MODE WARNING] {label} not found")
            else:
                raise StaleEvidence(f"[MISSING] {os.path.relpath(path, G)}: run the generator after the batch (python analytics/...)")
        else:
            check_output_sha(path, label, csv_sha)
    have_facts = check_output_sha(FACTS_PATH, "dossier_fill_facts_output.txt", csv_sha, r"\[F-csv\][^\n]*sha256 ([0-9a-f]{64})")
    facts = open(FACTS_PATH, encoding="utf-8").read() if have_facts else ""
    econ, econ_src = parse_econ(open(ECON_OUT, encoding="utf-8").read())
    for sc in SCENES:
        for c in UAVC:
            if "T" not in econ.get(sc, {}).get(c, {}):
                raise StaleEvidence(f"[STALE] economics output has no parsed T_payback for {sc}/{c}: format changed or file incomplete")
    abl_rows = fmea.load_ablation(ABL_PATH, ABL_PROV_PATH)          # exits loudly when absent or its hash is wrong
    table = fmea.fmea_table(rows, abl_rows)
    fm = fmea_dict(table)

    CP = {s_: {"PRIMARY": stat_pair(rows, s_, sv.PRIMARY_METRIC, sv.PRIMARY_PAIR), "SECONDARY": stat_pair(rows, s_, sv.PRIMARY_METRIC, sv.SECONDARY_PAIR)} for s_ in SCENES}
    NA = "not measured"
    vision_hz = prov.get("vision_hz", prov.get("vision_hz_uav"))

    m = mujoco.MjModel.from_xml_path(aps.SCENES["interior"])
    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "uav_alpha")
    mass = float(m.body_subtreemass[bid])
    g = -float(m.opt.gravity[2])
    W = mass * g
    tw = 4 * C.F_MAX / W
    models = {}
    for s_ in SCENES:
        mm_ = mujoco.MjModel.from_xml_path(aps.SCENES[s_])
        g_leg = mujoco.mj_name2id(mm_, mujoco.mjtObj.mjOBJ_GEOM, "alpha_leg0")
        g_flr = mujoco.mj_name2id(mm_, mujoco.mjtObj.mjOBJ_GEOM, "ground")
        models[s_] = dict(dt=float(mm_.opt.timestep), nu=int(mm_.nu), fr=[float(x) for x in mm_.geom_friction[g_leg]], condim=int(mm_.geom_condim[g_leg]),
                          sr_leg=[float(x) for x in mm_.geom_solref[g_leg]], sr_flr=[float(x) for x in mm_.geom_solref[g_flr]],
                          solmix_equal=bool(mm_.geom_solmix[g_leg] == mm_.geom_solmix[g_flr]),
                          integ=["Euler", "RK4", "implicit", "implicitfast"][int(mm_.opt.integrator)],
                          n_rf=sum(1 for i in range(mm_.nsite) if (mujoco.mj_id2name(mm_, mujoco.mjtObj.mjOBJ_SITE, i) or "").startswith("alpha_rf_")))
    MI, ME = models["interior"], models["exterior"]
    assert MI["dt"] == ME["dt"] and MI["nu"] == ME["nu"], "scene wrappers disagree on timestep or actuator count"
    ring = {}
    for s_ in SCENES:
        c = aps.DualUAVSurveillanceController(aps.SCENES[s_], policy="sectors", vision=False)
        ring[s_] = c.ring_len
        ring[s_ + "_cp"] = len(c.ring)
        ring[s_ + "_atrium"] = len(c.routes["atrium_cp"])
    sep = {}
    for s_ in SCENES:
        for c_ in UAVC:
            v = cell_vals(rows, s_, c_, "min_inter_uav_m")
            sep[(s_, c_)] = (min(v) if v else None, sum(1 for x in v if x < sv.D_SAFE_M), len(v))
    contacts = [(r["run_id"], int(float(r["obstacle_contacts"])), r["min_obstacle_clearance_m"]) for r in rows
                if (r.get("obstacle_contacts") or "") != "" and float(r["obstacle_contacts"]) > 0]
    n_uav_runs = sum(1 for r in rows if r["condition"] in UAVC)
    uu_total = sum(int(float(r["uav_uav_contacts"])) for r in rows if (r.get("uav_uav_contacts") or "") != "")
    n_tel = sum(1 for v in prov.get("runs", {}).values() if v.get("telemetry_path"))
    n_runs = len(rows)
    m_rate = re.search(r"\[F-tel-rate\][^\n]*?header=(\[[^\]]*\]);[^\n]*?median dt=([\d.]+) s", facts)
    m_hover = re.search(r"\[F-tel-hover\].*?median ([\d.]+) N", facts)

    F = {}

    def add(tag, value, status, src, note=""):
        assert tag not in F, tag
        assert status != "PENDING", tag
        if isinstance(value, str):
            value = re.sub(r"(not measured \([^)]*\)) (s|m)\b", r"\1", value)
        F[tag] = (value, status, src, note)

    def human(tag, how):
        add(tag, None, "HUMAN", "-", how)

    pw = lambda s, c: ms(rows, s, c, "worst_revisit_ground_s", 2)   # noqa: E731
    ct = lambda s, c: ms(rows, s, c, "cycle_time_s", 2)             # noqa: E731
    n_cell = prov["trials_per_cell"]
    src_csv = "analytics/campus_patrol_real_trials.csv (sha256 " + csv_sha[:16] + "...), " + STATS_FILE

    # ---- 1.1 claims
    add("M05.S1.claim1.source",
        "No primary source located (research-sources 29 Oct 2026). Corrected to our own measurement, N = %d per cell (Section 4): cycle_time_s interior guard_baseline %s s vs uav_sectors %s s; exterior %s s vs %s s." % (n_cell, ct("interior", "guard_baseline"), ct("interior", "uav_sectors"), ct("exterior", "guard_baseline"), ct("exterior", "uav_sectors")),
        "AUTO", "docs/research/sources_verified.md L-09; docs/research/sources_verified.md")
    add("M05.S1.claim1.source_type", "No source found", "AUTO", "docs/research/sources_verified.md L-09")
    add("M05.S1.claim1.verdict", "Correct", "AUTO", "docs/research/sources_verified.md L-09",
        "Corrected to our own measured value; the 72 % number is not used anywhere. Do not say it in the video or at the viva.")
    add("M05.S1.claim2.source",
        "No primary source located (formula only in the course Standards Manual section 3). Corrected to T_payback computed by analytics/campus_security_economics.py from sourced inputs or labelled ASSUMPTION ranges (Section 3); reported as a conditional range, not a point claim.",
        "AUTO", "docs/research/sources_verified.md L-09")
    add("M05.S1.claim2.source_type", "No source found", "AUTO", "docs/research/sources_verified.md L-09")
    add("M05.S1.claim2.verdict", "Correct", "AUTO", "docs/research/sources_verified.md L-09", "Corrected to the computed T_payback (Section 3). Do not quote 11 months.")
    vt = [float(r["verify_time_s"]) for r in rows if r["verify_time_s"] not in ("",)]
    add("M05.S1.claim3.source",
        "No primary source located; it is a design target, not a fact. Corrected to the measured columns detection_latency_s and verify_time_s of analytics/campus_patrol_real_trials.csv (verify_time_s over %d detected UAV runs: mean %.3f s; the verify step is %d consecutive vision ticks at %.0f Hz). Guard-side verification time is an ASSUMPTION range of 2 to 10 min."
        % (len(vt), st.mean(vt), C.VERIFY_K, vision_hz),
        "AUTO", "docs/research/sources_verified.md L-09; " + FACTS_OUT + "; provenance vision_hz_uav", "Do not quote 90 seconds.")
    add("M05.S1.claim3.source_type", "No source found", "AUTO", "docs/research/sources_verified.md L-09")
    add("M05.S1.claim3.verdict", "Correct", "AUTO", "docs/research/sources_verified.md L-09", "Corrected to the measured verify time. Do not quote 90 seconds.")

    # ---- 1.2 standards (rows come from docs/research/standards_verified.md, verified 30 Oct 2026)
    std_rows, std_domain_cell = read_standards()
    SM = "docs/research/standards_verified.md"
    for key, n in (("iso10218", 1), ("iso3691", 2), ("ria", 3), ("iec60601", 4)):
        r_ = std_rows[n]
        assert r_["applies"] == "No", (n, r_["applies"])
        add(f"M05.S1.std_{key}.applies", "No", "AUTO", f"{SM} row {n}")
        add(f"M05.S1.std_{key}.clause", standards_cell(r_), "AUTO", f"{SM} row {n} ({r_['source']})")
    assert std_rows[5]["applies"].startswith("Partly")
    add("M05.S1.std_domain.applies", "Partly", "CONFIRM", f"{SM} India Drone Rules decision",
        "Dropdown has Yes/Partly/No; Partly = applies to any real outdoor flight, our project is simulation only. Team may prefer another choice.")
    add("M05.S1.std_domain.clause", std_domain_cell, "AUTO", f"{SM} suggested dossier cell (official gazette text, https://egazette.gov.in/WriteReadData/2021/229221.pdf)")

    # ---- 1.3 baseline
    gb = {s_: (ct(s_, "guard_baseline"), eqw(rows, s_, "guard_baseline")) for s_ in SCENES}
    eqtxt = {s_: eqwin_of(rows, s_) for s_ in SCENES}
    gw = prov.get("guard_config", {}).get("walk_speed_mps", [[None, None]])[0]
    gs = prov.get("guard_config", {}).get("stop_mean_s", [[None, None]])[0]
    add("M05.S1.baseline_value",
        "Guard foot patrol, simulated in the same MuJoCo scene (src/foot_patrol_baseline.py, kinematic walker, same checkpoints). PRIMARY metric cycle_time_s = mean time per completed full ground lap (independent of the run window), mean ± SD over N = %d runs: interior %s s, exterior %s s. Equal-window worst revisit (longest unserviced interval of any ground checkpoint inside a common %s s / %s s window, interior / exterior): interior %s, exterior %s. Simulated values, not field measurements. Walker inputs: comfortable gait %s to %s m/s; pause %s to %s s per checkpoint (ASSUMPTION); 1 guard per round (ASSUMPTION 1 to 2)."
        % (n_cell, gb["interior"][0], gb["exterior"][0], eqtxt["interior"] or NA, eqtxt["exterior"] or NA, gb["interior"][1], gb["exterior"][1], gw[0], gw[1], gs[0], gs[1]),
        "AUTO", src_csv + "; docs/research/sources_verified.md L-24; provenance guard_config",
        "Run windows differ (guard %s s interior / %s s exterior, UAV %s s interior / %s s exterior); cycle_time_s is window-independent and the equal-window revisit uses one window for every condition. Say so in the text."
        % (durations(rows, "interior", "guard_baseline"), durations(rows, "exterior", "guard_baseline"), durations(rows, "interior", "uav_sectors"), durations(rows, "exterior", "uav_sectors")))
    add("M05.S1.baseline_source",
        "Walking speed: Bohannon RW, Age Ageing 1997;26(1):15-19, doi 10.1093/ageing/26.1.15 (strata means 1.272 to 1.462 m/s); Bohannon RW, Williams Andrews A, Physiotherapy 2011, doi 10.1016/j.physio.2010.12.004. Stairs: Dostan A et al., PLoS One 2023, doi 10.1371/journal.pone.0283333 (0.65 m/s) and Sun Y et al., Front Public Health 2026, doi 10.3389/fpubh.2025.1725056. Shift cap 8 h/day: Occupational Safety, Health and Working Conditions Code 2020 s.25(1)(a). ASSUMPTION (no primary source found): pause per checkpoint 10 to 60 s, rounds per shift 4 to 8, guards per round 1 to 2, guard verification time 2 to 10 min. The patrol-cycle and revisit numbers are our simulated output.",
        "AUTO", "docs/research/sources_verified.md L-24")
    add("M05.S1.stakeholder",
        "Security guards on foot rounds (walking hours per round) and the campus security or estate manager who carries the recurring guard OpEx; people in the building exposed to the gaps between visits.",
        "CONFIRM", "judgement (role description), no source", "Wording is the team's; edit freely.")

    # ---- 2.1 settings
    hz = 1.0 / MI["dt"]
    add("M05.S2.timestep",
        "%g s (%.0f Hz) in both scene wrappers (integrator %s). Read back with mujoco: opt.timestep = %g (interior) and %g (exterior)." % (MI["dt"], hz, MI["integ"], MI["dt"], ME["dt"]),
        "AUTO", "mujoco read-back of models/campus_perimeter_patrol.xml and _exterior.xml (this script); " + FACTS_OUT + " key F-load")
    add("M05.S2.friction",
        "%g / %g / %g (sliding / torsional / rolling), condim %d, global geom default in models/common.xml (airframe leg geom read back from the compiled model). With condim 3 only the sliding value acts; torsional and rolling need condim 4 and 6."
        % (MI["fr"][0], MI["fr"][1], MI["fr"][2], MI["condim"]),
        "AUTO", "mujoco read-back (this script); " + FACTS_OUT + " key F-contact; docs/research/mjcf_parameter_justification.md")
    mix = (MI["sr_leg"][0] + MI["sr_flr"][0]) / 2.0
    add("M05.S2.solref",
        "solref = %g %g (time constant s, damping ratio) on the airframe class quad; the floor keeps %g %g. MuJoCo mixes the two geoms' solref (solmix %s), so a leg-on-surface contact is solved with a time constant of %g s (mean of the two; drop-test printout in %s keys F-solref-mix). That is %s 2 x timestep = %g s, so the refsafe clamp (docs: time constant \"at least two times larger than the simulation time step\") %s. Damping ratio %g is critical damping, so the legs settle without bounce. Contact parameters do not drive any patrol metric: in flight the motion is thrust-driven. Evidence for the rest-test penetration depths: docs/submission/viva_evidence/viva_contact_solref_mix.txt and viva_contact_halved.txt (one deterministic rest test, not a batch result)."
        % (MI["sr_leg"][0], MI["sr_leg"][1], MI["sr_flr"][0], MI["sr_flr"][1], "equal" if MI["solmix_equal"] else "NOT equal", mix, FACTS_OUT,
           "above" if mix > 2 * MI["dt"] else "not above", 2 * MI["dt"], "does not act" if mix > 2 * MI["dt"] else "acts", MI["sr_leg"][1]),
        "AUTO", "mujoco read-back (this script); " + FACTS_OUT + " keys F-contact, F-solref-mix; docs/research/mjcf_parameter_justification.md; docs/submission/ai_audit_candidates.md E043-C")
    add("M05.S2.control_law", "PI / PD", "CONFIRM", "src/aerial_patrol_swarm.py _control",
        "Closest option: cascade P (position) -> PI (velocity) -> PD (attitude). 'Other' is equally defensible; the gains cell says what it is.")
    add("M05.S2.gains",
        "Cascade, from src/aerial_patrol_swarm.py: position P Kp_pos = %s 1/s; velocity PI Kp_vel = %s 1/s, Ki_vel = %s 1/s^2, integral clamp %s m; attitude PD (torque = I(Kp e - Kd w) + w x I w) roll and pitch Kp = %s 1/s^2, Kd = %s 1/s, yaw Kp = %s 1/s^2, Kd = %s 1/s; tilt-rate limit %.0f deg/s. Separation: APF K_rep = %s N m^2 for d < d_safe = %s m, plus a distance governor and right-hand sidestep. FR-18: %d range beams per UAV, range %s m, noise %s m (1 sigma), %.0f Hz, stop distance %s m lateral / %s m vertical."
        % (C.KP_POS, C.KP_VEL, C.KI_VEL, C.I_CLAMP, C.KP_ATT[0], C.KD_ATT[0], C.KP_ATT[2], C.KD_ATT[2],
           math.degrees(C.MAX_TILT_RATE), C.K_REP, sv.D_SAFE_M, MI["n_rf"], C.RF_RANGE_M, C.RF_SIGMA_M, C.SENSE_HZ, C.D_STOP_H, C.D_STOP_V),
        "AUTO", FACTS_OUT + " keys F-gain, F-fr18, F-sep", "Hand-tuned, not auto-tuned: say so if asked.")
    add("M05.S2.fsm_states",
        "PATROL, DETECT, VERIFY, ALERT_0, ALERT_1, ALERT_2, ALERT_3, TRACK, RETURN_TO_PATROL; the flight phases TAKEOFF, TRANSIT and DESCEND are logged in the same fsm_state column before PATROL. Implemented in DualUAVSurveillanceController._fsm_step (src/aerial_patrol_swarm.py). Parameters: vision tick %.0f Hz default (the batch ran UAV vision at %s Hz), verify = %d consistent hits within %.1f m, TRACK ends after %.0f s or after %.0f s without a fix, leash %.0f m."
        % (C.VISION_HZ, vision_hz, C.VERIFY_K, C.VERIFY_GATE_M, C.TRACK_MAX_S, C.TRACK_LOST_S, C.TRACK_LEASH_M),
        "AUTO", FACTS_OUT + " keys F-fsm, F-phases, F-fsm-consts",
        "Routes (computed from the scene sites): interior Alpha ground loop %.1f m through %d checkpoints, Bravo atrium-gallery sweep through %d checkpoints and back; exterior ring %.1f m through %d checkpoints inside the boundary wall."
        % (ring["interior"], ring["interior_cp"], ring["interior_atrium"], ring["exterior"], ring["exterior_cp"]))
    add("M05.S2.model_loads", "Yes", "AUTO", "mujoco loads both scene models in this script (nu = %d actuators)" % MI["nu"])

    # ---- 2.2 authorship (5 rows). Each member owned one area; E043 integrated the areas into one tree.
    n_ap = git("rev-list", "--count", "HEAD", "--", "src/aerial_patrol_swarm.py")
    IA = ("Team split: E043 flight control, separation, FSM, scenes and integration; E051 vision; E075 geofence and statistics; E077 economics, queue and FMEA. "
          "The areas were merged into one tree and pushed from E043's account, so this branch's history shows E043; E077's own commits are on the e077 branches (PRs #1 to #5).")
    add("M05.S2.script1.authorship", "Modified by us", "AUTO", "git log -- models/campus_perimeter_patrol.xml")
    add("M05.S2.script1.author", "E043", "AUTO", "git log")
    add("M05.S2.script1.change",
        "Course-scaffold names kept (uav_alpha/bravo, cam_*, substation_zone). Timestep set to %g s; uav_fleet.xml gained %d range-finder sites per airframe; scene geometry is generated by models/scene_source/build_nmims_*.py. AI-assisted drafting." % (MI["dt"], MI["n_rf"]),
        "AUTO", "git log -- models/")
    add("M05.S2.script2.authorship", "Modified by us", "AUTO", "git log -- src/aerial_patrol_swarm.py (%s commits)" % n_ap)
    add("M05.S2.script2.author", "Shared", "CONFIRM", "region comments in the file; git log",
        "Regions by owner: E043 (flight, separation, FR-18, FSM), E051 (HSV detector, projection, handoff), E075 (geofence). " + IA)
    add("M05.S2.script2.change",
        "E043: cascaded flight control, layered separation, FR-18 range-ring avoidance, surveillance FSM, telemetry hooks. E051 region (E051): HSV detector, inverse pinhole projection, target handoff. E075 region (E075): polygon geofence tiers with hysteresis. All AI-assisted; " + IA,
        "AUTO", "git log -- src/aerial_patrol_swarm.py")
    add("M05.S2.script3.authorship", "Written by us", "AUTO", "git log -- analytics/campus_security_economics.py")
    add("M05.S2.script3.author", "E077", "CONFIRM", "git log; docs/submission/viva_prep_E077.md",
        "E077 area (AI-assisted); " + IA)
    add("M05.S2.script3.change",
        "Rewritten: the hard-coded scaffold constants removed; inputs come from a SOURCES table (cited value or ASSUMPTION range) and from the real-trials CSV (hash-checked); computes H_reclaimed, kappa, NCRI, P_payback, T_payback, M/M/c, sensitivity, tornado and the FMEA from measured rates. E077 area, AI-assisted. " + IA,
        "AUTO", "git log -- analytics/campus_security_economics.py analytics/campus_security_fmea.py")
    add("M05.S2.script4.name", "analytics/statistical_validation.py", "AUTO", "git log")
    add("M05.S2.script4.authorship", "Written by us", "AUTO", "git log -- analytics/statistical_validation.py")
    add("M05.S2.script4.author", "E075", "CONFIRM", "Section 6 E075 row; docs/submission/viva_prep_E075.md")
    add("M05.S2.script4.change",
        "Reads the real-trials CSV (hash-checked) and runs Welch's two-sided t test with exact p, Cohen's d and a t-based 95 % CI on the primary metric; the right-censored equal-window revisit is reported descriptively only. E075 area, AI-assisted. " + IA,
        "AUTO", "git log -- analytics/statistical_validation.py")
    add("M05.S2.script5.name", "analytics/vision_illumination_benchmark.py", "AUTO", "git log")
    add("M05.S2.script5.authorship", "Written by us", "AUTO", "git log -- analytics/vision_illumination_benchmark.py")
    add("M05.S2.script5.author", "E051", "CONFIRM", "Section 6 E051 row; docs/submission/viva_prep_E051.md")
    add("M05.S2.script5.change",
        "Benchmarks the production HSV detector at noon and twilight light in both scenes (twilight = authored light x0.15, an ASSUMPTION, not a measured lux); its hit rates feed the twilight row of the FMEA. E051 area, AI-assisted. " + IA,
        "AUTO", "git log -- analytics/vision_illumination_benchmark.py")

    # ---- 3 business (inputs / metric text built from E077's output)
    def e(s, c, k):
        return econ[s][c][k]

    def per(fn):
        return "; ".join(fn(s, c) for s in SCENES for c in ("uav_sectors", "uav_offset_ring"))

    inputs_txt = []
    for k in ("hours_per_shift", "rounds_per_shift", "guards_per_round", "replacement_fraction", "capex_ratio",
              "service_life_years", "maintenance_fraction", "other_opex_fraction", "battery_cycle_life",
              "battery_capex_share", "endurance_min", "n_uav", "fte_hours_per_year", "kappa_target",
              "incidents_per_month", "guard_response_min", "guard_responders"):
        if k in econ_src:
            v, u, kind = econ_src[k]
            inputs_txt.append(f"{k} {v} [{u}] {kind}")
    ECON_INPUTS = "; ".join(inputs_txt)
    add("M05.S3.E077.hreclaimed_inputs",
        "H_patrol = shifts (24 / hours_per_shift) x rounds_per_shift x guards_per_round x T_guard_cycle, where T_guard_cycle is the simulated mean cycle_time_s of guard_baseline (N = %d); H_reclaimed = replacement_fraction x H_patrol, only if the UAV mean worst revisit is no larger than the guard's (gate printed by the script: %s). Base case = midpoint of each range. Inputs as printed by the script: %s."
        % (n_cell, "; ".join(f"{s_} {c_.replace('uav_', '')} {e(s_, c_, 'gate')[0]}" for s_ in SCENES for c_ in UAVC), ECON_INPUTS), "AUTO", ECON_FILE + " (SOURCES table)")
    add("M05.S3.E077.hreclaimed_metric",
        "interior %s guard-hours/day, exterior %s guard-hours/day (both UAV conditions); delta FTE = H x 365 / 2080: interior %s, exterior %s. Conditional on the ASSUMPTION ranges."
        % (e("interior", "uav_sectors", "H")[0], e("exterior", "uav_sectors", "H")[0],
           e("interior", "uav_sectors", "H")[1], e("exterior", "uav_sectors", "H")[1]),
        "AUTO", ECON_FILE)
    add("M05.S3.E077.payback_inputs",
        "P_payback = k / (T_life x (R - k u)); T_payback = 12 k / (R - k u) months. k = capex_ratio (fleet acquisition cost over one year of replaced guard patrol labour, ASSUMPTION %s); u = maintenance_fraction + other_opex_fraction + battery term (battery_capex_share x charge cycles per year / 400 cycles; 400 from the DJI Matrice 350 RTK product page, a reference airframe); R = replacement_fraction (ASSUMPTION); T_life = service_life_years (ASSUMPTION %s). All costs are dimensionless ratios to the guard baseline."
        % (econ_src["capex_ratio"][0], econ_src["service_life_years"][0]),
        "AUTO", ECON_FILE + "")
    add("M05.S3.E077.payback_metric",
        "P_payback (base case, envelope over all range corners): "
        + per(lambda s, c: f"{s} {c.replace('uav_', '')} {e(s, c, 'P')[0]} ({e(s, c, 'P')[1]} to {e(s, c, 'P')[2]}; {e(s, c, 'P')[3]} of {e(s, c, 'P')[4]} corners never pay back)")
        + ". P < 1 = recovered inside the service life. Conditional on assumed ranges; not a forecast.",
        "AUTO", ECON_FILE)
    add("M05.S3.E077.ncri_inputs",
        "NCRI = (C_baseline - C_robot) / C_baseline = 1 - kappa with kappa = annual running cost of the UAV fleet over the annual value of reclaimed guard hours (course Standards Manual section 3, target kappa <= %s). Same SOURCES table as above."
        % econ_src["kappa_target"][0], "AUTO", ECON_FILE)
    add("M05.S3.E077.ncri_metric",
        per(lambda s, c: f"{s} {c.replace('uav_', '')} kappa {e(s, c, 'kappa')[0]} (target <= {e(s, c, 'kappa')[1]}: {e(s, c, 'kappa')[2]}), NCRI {e(s, c, 'NCRI')[0]} (envelope {e(s, c, 'NCRI')[1]} to {e(s, c, 'NCRI')[2]})"),
        "AUTO", ECON_FILE)
    qb = {s: econ[s]["uav_sectors"]["Q"] for s in SCENES}
    add("M05.S3.E077.queue_inputs",
        "M/M/c with c = 2 UAVs; lambda = incidents_per_month / (365/12 x 24) per hour (incidents_per_month 1 to 10, ASSUMPTION; low/base/high shown); mu = 1 / (mean simulated detection_latency_s + verify_time_s of detected runs). Guard comparison: mu from guard_response_min 2 to 10 min (ASSUMPTION midpoint), c = 2 responders (ASSUMPTION 1 to 3). rho = lambda / (c mu) < 1; W_q = C(c, lambda/mu) / (c mu - lambda) (Erlang C).",
        "AUTO", ECON_FILE)
    add("M05.S3.E077.queue_metric",
        "UAV, base lambda: interior sectors rho = %s, W_q = %s s; exterior sectors rho = %s, W_q = %s s. At campus incident rates rho is tiny, so waiting is about zero for every system: the queue shows utilisation headroom, not a delay problem."
        % (qb["interior"]["base"][3], qb["interior"]["base"][5], qb["exterior"]["base"][3], qb["exterior"]["base"][5]),
        "AUTO", ECON_FILE)
    add("M05.S3.E077.sensitivity_inputs",
        "Most uncertain input = the ASSUMPTION row with the widest relative range, computed by the script: capex_ratio (%s). Swept -30 %% to +30 %% of its base value; P_payback and NCRI plotted; bisection for the break-even P_payback = 1 inside the assumed range."
        % econ_src["capex_ratio"][0], "AUTO", ECON_FILE + "; EXPLAIN.md (most_uncertain_key)")
    add("M05.S3.E077.sensitivity_metric",
        per(lambda s, c: f"{s} {c.replace('uav_', '')}: break-even on {e(s, c, 'BE_in')[0]} (P_payback = 1) inside the assumed range: {e(s, c, 'BE_in')[1]}; full-search crossing {e(s, c, 'BE')[0]} = {e(s, c, 'BE')[1]} ({e(s, c, 'BE')[2]}); capex_ratio at kappa = target {e(s, c, 'kappa_cap')[0]}")
        + ". Figures: analytics/figures/campus_security_sensitivity.png and campus_security_queue.png.",
        "AUTO", ECON_FILE)
    add("M05.S3.E077.queue_model", "M/M/c", "AUTO", ECON_FILE)
    ql = qb
    qg = re.search(r"guard M/M/c base\s+lambda=([\d.]+)/h mu=([\d.]+)/h c=(\d+)", open(ECON_OUT, encoding="utf-8").read()) if os.path.isfile(ECON_OUT) else None
    add("M05.S3.E077.queue_params",
        "lambda = %s / %s / %s per h (low / base / high, from the incidents_per_month range, ASSUMPTION); UAV mu = %s per h (interior sectors), %s per h (exterior sectors); guard mu = %s per h (guard_response_min midpoint, ASSUMPTION); c = 2 UAVs."
        % (ql["interior"]["low"][0], ql["interior"]["base"][0], ql["interior"]["high"][0],
           ql["interior"]["base"][1], ql["exterior"]["base"][1], qg.group(2) if qg else NA),
        "AUTO", ECON_FILE, "mu for the other UAV condition is in the same file; add if there is room.")
    add("M05.S3.E077.payback_months",
        per(lambda s, c: f"{s} {c.replace('uav_', '')} {e(s, c, 'T')[0]} months"),
        "AUTO", ECON_FILE, "Conditional on ASSUMPTION ranges; never write '11 months'.")
    if TEST_MODE:
        human("M05.S3.E077.reproducible", "Test mode: the economics output was not generated from this CSV.")
    else:
        add("M05.S3.E077.reproducible", "Yes", "CONFIRM", ECON_FILE + " carries the sha256 of the CSV in use (checked by this script)",
            "Re-run python analytics/campus_security_economics.py and compare before you tick Yes yourself.")

    # ---- 3.2 FMEA (interior values in the dropdowns, exterior in the text). O and D come from measured rates
    # (ablation_trials.csv for the before arm, the trials CSV for detection); S is team judgement.
    fi = lambda k: fm[("interior", k)]                  # noqa: E731
    fe = lambda k: fm[("exterior", k)]                  # noqa: E731
    FS = FMEA_FILE

    def fmea_row(n, key, mode=None, extra_mit=""):
        a, b = fi(key), fe(key)
        if mode:
            add(f"M05.S3.fmea{n}.mode", mode, "AUTO", FS)
        add(f"M05.S3.fmea{n}.effect", a["effect"], "AUTO", FS)
        add(f"M05.S3.fmea{n}.severity", str(a["S"]), "CONFIRM", FS, "S is team judgement (labelled so by the script). The team must agree it.")
        o = o_of(a["before"])
        if o is not None:
            add(f"M05.S3.fmea{n}.occurrence", str(o), "AUTO", FS + "; O computed from the measured before-arm failure rate (interior)")
            add(f"M05.S3.fmea{n}.rpn_pre", f"{a['rpn_b']} interior; {b['rpn_b']} exterior", "AUTO", FS)
        else:
            human(f"M05.S3.fmea{n}.occurrence", "Pre-mitigation O is 'not measured' for this row in the interior; leave a team-agreed value and say so in the RPN pre cell.")
            add(f"M05.S3.fmea{n}.rpn_pre", "not measured", "AUTO", FS)
        if a["Db"] is not None:
            add(f"M05.S3.fmea{n}.detection", str(a["Db"]), "CONFIRM", FS, "D before mitigation: from the measured escape rate (or team judgement where the script says so).")
        else:
            human(f"M05.S3.fmea{n}.detection", "D before mitigation is not measured for this row.")
        add(f"M05.S3.fmea{n}.mitigation",
            f"[{a['mit_state']}] {a['mit']}. Before: interior {a['before']}; exterior {b['before']}. After: interior {a['after']}; exterior {b['after']}.{extra_mit}",
            "AUTO", FS)
        add(f"M05.S3.fmea{n}.rpn_post", f"{a['rpn_a']} interior; {b['rpn_a']} exterior", "AUTO", FS)

    def sep_txt():
        parts = []
        for s_ in SCENES:
            for c_ in UAVC:
                mn, nb, nn = sep[(s_, c_)]
                parts.append(f"{s_} {c_.replace('uav_', '')} {('%.2f m' % mn) if mn is not None else NA} ({nb} of {nn} runs below {sv.D_SAFE_M:g} m)")
        return (f" UAV-UAV contacts = {uu_total} in all {n_uav_runs} UAV runs. Closest approach in the trials (min_inter_uav_m): " + "; ".join(parts) + ".")

    fmea_row(1, "uav_uav_conflict", None, sep_txt())
    add("M05.S3.fmea1.evidence", "Both", "AUTO", "tests/test_e043_separation.py (code + simulation); ablation mode=separation; trials CSV uav_uav_contacts")
    fmea_row(2, "missed_intruder_twilight")
    add("M05.S3.fmea2.evidence", "Both", "AUTO", "tests/test_e051_vision.py; ablation mode=twilight_exposure; twilight = authored light scaled, an ASSUMPTION, not a measured lux")
    fmea_row(3, "false_geofence_alarm", "False geofence alarm from position noise")
    add("M05.S3.fmea3.evidence", "Both", "AUTO", "tests/test_e075_geofence_stats.py; ablation mode=geofence_hysteresis (noisy position)")
    fmea_row(4, "intruder_not_detected", "Intruder not detected in a patrol run (any lighting)")
    add("M05.S3.fmea4.evidence", "Simulation", "AUTO", "trials CSV column detected")
    fmea_row(5, "unseen_obstacle", "Collision with an obstacle the UAV did not sense (FR-18)")
    add("M05.S3.fmea5.evidence", "Both", "AUTO", "tests/test_e043_obstacle_perception.py; ablation mode=fr18; trials CSV obstacle_contacts, min_obstacle_clearance_m")

    # ---- 4 protocol
    gdur = {s_: durations(rows, s_, "guard_baseline") for s_ in SCENES}
    udur = {s_: durations(rows, s_, "uav_sectors") for s_ in SCENES}
    seeds_all = sorted({int(r["seed"]) for r in rows})
    add("M05.S4.baseline_condition",
        "guard_baseline: a guard on foot in the same MuJoCo scene (kinematic walker, src/foot_patrol_baseline.py; not a rigid-body controller), walking speed U[%s, %s] m/s (Bohannon 1997), pause per checkpoint %s to %s s (ASSUMPTION). Proposed: uav_sectors (primary comparison; interior Alpha ground-floor loop + Bravo atrium galleries, exterior two arcs of the campus ring inside the boundary wall) and uav_offset_ring (both UAVs on the loop, half a lap apart). Windows (duration_s): guard %s s interior / %s s exterior, UAV %s s interior / %s s exterior. The PRIMARY metric cycle_time_s is window-independent; revisit is also reported in one equal window (%s s interior / %s s exterior)."
        % (gw[0], gw[1], gs[0], gs[1], gdur["interior"], gdur["exterior"], udur["interior"], udur["exterior"], eqtxt["interior"] or NA, eqtxt["exterior"] or NA),
        "AUTO", "analytics/campus_patrol_real_trials.provenance.json (windows, guard_config)")
    rat = prov.get("n_choice_rationale")
    add("M05.S4.n_runs",
        "N = %d per cell in all %d cells (2 scenes x 3 conditions = %d runs); seeds %d to %d in every cell; timestep %s s.%s"
        % (n_cell, len({(r["scene"], r["condition"]) for r in rows}), n_runs, seeds_all[0], seeds_all[-1], "/".join(sorted({r["timestep_s"] for r in rows})),
           (" Reasoning for N recorded in the provenance file: " + clip(str(rat), 300)) if rat else ""),
        "AUTO", "provenance trials_per_cell, seeds, n_choice_rationale")
    rnd = prov["randomisation"]["interior"]
    ws = re.search(r"x wind_scale ([\d.]+)", rnd["mean_wind_nominal_mps"][1])
    gcfg = prov.get("guard_config", {})
    add("M05.S4.randomised",
        "Per seed, drawn uniformly, same draw shared by the 3 conditions (paired design): mean wind U%s m/s nominal (x%s indoors), gust sigma U%s m/s (Ornstein-Uhlenbeck), intruder appears U%s s, dock jitter U%s m (all ASSUMPTION or design, labelled in the provenance); guard speed U%s m/s, pause %s s, stair vertical speed U%s m/s (ASSUMPTION), lift wait U%s s (ASSUMPTION). Realised ranges are in %s keys F-draw."
        % (list(rnd["mean_wind_nominal_mps"][0]), ws.group(1) if ws else NA, list(rnd["gust_sigma_nominal_mps"][0]),
           list(rnd["intruder_appear_s"][0]), list(rnd["dock_jitter_m"][0]), gw, gs,
           gcfg.get("stair_vertical_mps", [NA])[0], gcfg.get("lift_wait_s", [NA])[0], FACTS_OUT),
        "AUTO", "provenance randomisation, guard_config; analytics/run_benchmark.py RANDOMISATION")
    add("M05.S4.log_rate_hz",
        "%.0f Hz: one row per %g s physics step per vehicle (columns %s)%s. Per-run telemetry is recorded for %d of %d runs (provenance runs[*].telemetry_path); the CSV metrics of every run are computed in the same %g s loop. Vision runs at %s Hz for UAVs."
        % (hz, MI["dt"], m_rate.group(1) if m_rate else "see " + FACTS_OUT + " key F-tel-rate", (", measured median dt = %s s" % m_rate.group(2)) if m_rate else "", n_tel, n_runs, MI["dt"], vision_hz),
        "AUTO", FACTS_OUT + " keys F-tel, F-tel-rate; provenance runs[*].telemetry_path")
    nseed_ok = all(len({r["seed"] for r in rows if r["scene"] == s_ and r["condition"] == c_}) == sum(1 for r in rows if r["scene"] == s_ and r["condition"] == c_) for s_ in SCENES for c_ in CONDS)
    assert nseed_ok, "seeds are not unique within a cell"
    add("M05.S4.seeds_recorded", "Yes", "AUTO", "CSV column seed, unique within every cell (checked by this script)")
    add("M05.S4.real_csv_path",
        "Group_05_Muaaz_Aditya_Zaid_Soumya/analytics/campus_patrol_real_trials.csv (%d rows) and campus_patrol_real_trials.provenance.json; csv sha256 %s" % (n_runs, csv_sha), "AUTO", "provenance csv_sha256")

    # results table
    def two(s_, c_, col_, nd=4):
        return f"{s_}: {ms(rows, s_, c_, col_, nd)}"

    def four(col_, nd):
        return "uav_sectors: %s; %s. uav_offset_ring: %s; %s." % (two("interior", "uav_sectors", col_, nd), two("exterior", "uav_sectors", col_, nd),
                                                                  two("interior", "uav_offset_ring", col_, nd), two("exterior", "uav_offset_ring", col_, nd))
    add("M05.S4.rmse.n", f"{n_cell} UAV runs per cell", "AUTO", src_csv)
    add("M05.S4.rmse.baseline", "not applicable (guard is a kinematic walker; no controller)", "AUTO", "provenance not_applicable by_condition guard_baseline")
    add("M05.S4.rmse.proposed", "Cross-track: " + four("tracking_rmse_m", 4) + " Waypoint (timed path): " + four("waypoint_rmse_m", 4), "AUTO", src_csv)
    add("M05.S4.rmse.unit", "m (cross-track: deviation from the active route leg, progress along the leg not counted, TRACK/RETURN steps excluded; waypoint: deviation from the timed waypoint path)", "AUTO", "src/aerial_patrol_swarm.py flight_metrics")
    add("M05.S4.rmse.better", "Lower is better", "AUTO", "definition")
    add("M05.S4.effort.n", f"{n_cell} UAV runs per cell", "AUTO", src_csv)
    add("M05.S4.effort.baseline", "not applicable (no actuators on the guard model)", "AUTO", "provenance not_applicable")
    add("M05.S4.effort.proposed", "Thrust effort (sum F^2 dt): " + four("control_effort_N2s", 1) + " Torque effort (integral |tau|^2 dt): " + four("torque_effort_N2m2s", 4), "AUTO", src_csv)
    add("M05.S4.effort.unit", "N^2 s for thrust (sum over the rotors of F^2 dt; the airframe is driven by rotor forces); N^2 m^2 s for body torque (integral |tau|^2 dt)", "AUTO", "src/aerial_patrol_swarm.py flight_metrics")
    add("M05.S4.effort.better", "Lower is better", "AUTO", "definition")
    add("M05.S4.metric.name", "cycle_time_s (PRIMARY: mean time per completed full ground lap, window-independent); also worst_revisit_ground_eqwin_s (longest gap between services of a ground checkpoint inside one equal window)", "AUTO", "contract A; src/patrol_metrics.py")
    add("M05.S4.metric.n", f"{n_cell} per cell", "AUTO", src_csv)
    add("M05.S4.metric.baseline",
        "guard_baseline cycle_time_s: interior %s; exterior %s. Equal-window worst revisit: interior %s; exterior %s." % (ct("interior", "guard_baseline"), ct("exterior", "guard_baseline"), eqw(rows, "interior", "guard_baseline"), eqw(rows, "exterior", "guard_baseline")),
        "AUTO", src_csv)
    add("M05.S4.metric.proposed",
        "uav_sectors cycle_time_s: interior %s; exterior %s. uav_offset_ring: interior %s; exterior %s. Equal-window worst revisit, sectors: interior %s; exterior %s; offset ring: interior %s; exterior %s."
        % (ct("interior", "uav_sectors"), ct("exterior", "uav_sectors"), ct("interior", "uav_offset_ring"), ct("exterior", "uav_offset_ring"),
           eqw(rows, "interior", "uav_sectors"), eqw(rows, "exterior", "uav_sectors"), eqw(rows, "interior", "uav_offset_ring"), eqw(rows, "exterior", "uav_offset_ring")),
        "AUTO", src_csv)
    add("M05.S4.metric.unit", "s", "AUTO", "contract A")
    add("M05.S4.metric.better", "Lower is better", "AUTO", "definition")
    add("M05.S4.test", "Welch's t-test", "AUTO", STATS_FILE,
        "Seeds are shared across conditions (paired draws) but the script treats the runs as independent. Be ready to say why Welch and what a paired test would change.")

    def stline(label, key):
        pi, pe = CP["interior"][key], CP["exterior"][key]
        if pi is None or pe is None:
            return None
        return pi, pe
    P_, S_ = stline("p", "PRIMARY"), stline("s", "SECONDARY")
    if P_ and S_:
        pi, pe = P_
        si, se = S_
        add("M05.S4.t_df_p",
            "cycle_time_s, guard_baseline vs uav_sectors, two-sided Welch: interior t = %s, df = %s, p = %s; exterior t = %s, df = %s, p = %s. (Secondary, uav_sectors vs uav_offset_ring: interior t = %s, df = %s, p = %s; exterior t = %s, df = %s, p = %s.)"
            % (pi["t"], pi["df"], pi["p"], pe["t"], pe["df"], pe["p"], si["t"], si["df"], si["p"], se["t"], se["df"], se["p"]), "AUTO", STATS_FILE)
        add("M05.S4.cohens_d",
            "guard vs uav_sectors: interior d = %s, exterior d = %s (pooled SD). Secondary: interior %s, exterior %s." % (pi["d"], pe["d"], si["d"], se["d"]), "AUTO", STATS_FILE)
        add("M05.S4.ci95",
            "Mean difference guard - uav_sectors: interior [%s, %s] s, exterior [%s, %s] s. Secondary (sectors - offset_ring): interior [%s, %s] s, exterior [%s, %s] s."
            % (*pi["ci"], *pe["ci"], *si["ci"], *se["ci"]), "AUTO", STATS_FILE)
    else:
        for tg in ("t_df_p", "cohens_d", "ci95"):
            add(f"M05.S4.{tg}", "not measured: a cell has fewer than 2 completed laps, so cycle_time_s has no test (n < 2); see " + STATS_FILE, "AUTO", STATS_FILE)

    # provenance boxes
    add("M05.S4.prov_own_runs", "Yes", "CONFIRM",
        "provenance 'generator': analytics/run_benchmark.py; sha256 gate in generate_paper_figures.py, statistical_validation.py and this script",
        "True for every UAV number. The guard baseline is our own kinematic walker in the same MuJoCo scene (declared in the baseline cell), not a rigid-body controller. Code commit recorded in the provenance: %s." % prov.get("git_commit", prov.get("e043_commit")))
    add("M05.S4.prov_no_simulated", "Yes", "AUTO",
        "analytics/statistical_validation.py, generate_paper_figures.py and this script refuse SIMULATED_* input",
        "analytics/SIMULATED_campus_patrol_benchmark.csv is the faculty's scaffold file, kept unchanged and not read by any script.")
    add("M05.S4.prov_plots_reproducible", "Yes", "CONFIRM",
        "python analytics/generate_paper_figures.py --runs-dir <telemetry dir> and python analytics/campus_security_economics.py regenerate every figure from the hash-checked CSV",
        "Confirm after you re-run both commands yourself. Trajectory plots need the per-run telemetry, which is gitignored: regenerate it with run_benchmark.py.")
    all_tagged = all(v[2] in ("sourced", "ASSUMPTION") for v in econ_src.values()) and len(econ_src) > 0
    if all_tagged:
        add("M05.S4.prov_economics_sourced", "Yes", "AUTO", ECON_FILE + " SOURCES table: every one of the %d inputs is labelled sourced or ASSUMPTION" % len(econ_src))
    else:
        human("M05.S4.prov_economics_sourced", "The economics output has inputs without a sourced/ASSUMPTION label (or none parsed): check it.")

    # ---- 5 video, AI log, peers
    add("M05.S5.linkedin_url", "https://lnkd.in/p/ddww8s-J", "CONFIRM", "posted by E043 on 31 Oct 2026", "Open the link once and check it shows the group video.")
    add("M05.S5.video_length", "3:17", "CONFIRM", "ffprobe of the exported final_1080p30.mp4 (196.7 s)")
    add("M05.S5.live_mujoco", "Yes", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
    add("M05.S5.business_graph", "Yes", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
    add("M05.S5.all_members_speak", "Yes", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")

    cases = read_audit_cases()
    AI_PREFIX = ("Group AI use (declared): the code, tests, documents and this dossier draft were first drafted by Claude (Anthropic) under E043's direction; "
                 "each member's original packet was also AI-drafted; we ran, tested and corrected what is listed here. Case: ")
    et_map = {"E043-A": "Wrong code / MuJoCo API", "E043-B": "Wrong physics / equation", "E043-C": "Wrong code / MuJoCo API"}
    for n, cid in (("1", "E043-A"), ("2", "E043-B"), ("3", "E043-C")):
        cs = cases[cid]
        f_ = cs["fields"]
        said = clip((AI_PREFIX if n == "1" else "") + cs["title"] + ". " + first_field(f_, "claim", "source"), 1100)
        truth = clip(first_field(f_, "what was wrong", "what is wrong") + " Proof: " + first_field(f_, "proof", "reproduce"), 1100)
        add(f"M05.S5.ai{n}.tool", "Claude", "CONFIRM", "git; docs/submission/ai_audit_candidates.md " + cid, "Choose the AI tool the member actually used; the code was drafted by Claude under E043's instructions.")
        add(f"M05.S5.ai{n}.said", said, "CONFIRM", "docs/submission/ai_audit_candidates.md " + cid, "Pick the three cases the team can defend at the viva; alternatives (E051-A, E075-A, E077-A) are in the same file.")
        add(f"M05.S5.ai{n}.caught_by", "Ran / tested the code or simulation", "CONFIRM", "docs/submission/ai_audit_candidates.md " + cid)
        add(f"M05.S5.ai{n}.truth", truth, "CONFIRM", "docs/submission/ai_audit_candidates.md " + cid)
        add(f"M05.S5.ai{n}.error_type", et_map[cid], "CONFIRM", "judgement")
        add(f"M05.S5.ai{n}.verdict", "Corrected", "CONFIRM", "docs/submission/ai_audit_candidates.md " + cid)
    peer_q = {"M06": "How does the crawler keep traction on a wet, tilted panel, and how much slip did you measure in the simulation?",
              "M11": "What false-positive rate does your defect detector show on clean panels, and how did you measure it?"}
    for gname in ("M06", "M11"):
        for k in ("problem", "physics", "business", "data", "clarity"):
            add(f"M05.S5.peer_{gname}.{k}", "2", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
        add(f"M05.S5.peer_{gname}.best_moment", {"M06": "0:05", "M11": "0:30"}[gname], "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
        add(f"M05.S5.peer_{gname}.question", peer_q[gname], "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)" + "; topic from the 31 Oct class briefing")

    # ---- 6 learning record
    members = {
        "E043": ("src/aerial_patrol_swarm.py (outside region markers), src/foot_patrol_baseline.py, src/patrol_metrics.py, src/run_telemetry.py, src/view_live.py, analytics/run_benchmark.py, analytics/generate_paper_figures.py, tests/test_e043_*, models/scene_source/*", "76–100 %",
                 "git log on the E043 branch; docs/dossier_fill_facts_output.txt keys F-git-file (AI-drafted code, documents, PRDs and the multi-agent workflow)"),
        "E051": ("src/aerial_patrol_swarm.py E051 region (detect_intruder_hsv, inverse_pinhole_projection, select_tracking_uav), analytics/vision_illumination_benchmark.py, analytics/vision_yolo_compare.py, tests/test_e051_vision.py", "76–100 %",
                 "docs/submission/ai_audit_candidates.md; the member's own AI_DISCLOSURE (original packet) states the share"),
        "E075": ("src/aerial_patrol_swarm.py E075 region (geofence, noise, breach log, link-loss check), analytics/geofence_noise_demo.py, analytics/statistical_validation.py, tests/test_e075_geofence_stats.py", "76–100 %",
                 "docs/submission/ai_audit_candidates.md; the member's own AI_DISCLOSURE (original packet) states the share"),
        "E077": ("analytics/campus_security_economics.py, analytics/campus_security_fmea.py, tests/test_e077_economics.py", "76–100 %",
                 "docs/submission/ai_audit_candidates.md; the member's own AI_DISCLOSURE (original packet) states the share"),
    }
    for roll, (scripts, share, why) in members.items():
        add(f"M05.S6.{roll}.hours", "35", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
        add(f"M05.S6.{roll}.role_fidelity", "5", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
        add(f"M05.S6.{roll}.cross_disciplinary_skill", "Yes", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
        add(f"M05.S6.{roll}.scripts_authored", scripts + " (AI-drafted; see Section 5.1)", "CONFIRM", why,
            "Each member confirms their own row. Each area was owned by its member; E043 merged the areas into one tree and pushed them from E043's account.")
        if roll == "E043":
            tot = git("rev-list", "--count", "HEAD", "--", ".")
            by_me = sum(int(x.split()[0]) for x in git("shortlog", "-sn", "HEAD", "--", ".").splitlines() if "MuaazSM" in x or "Muaaz" in x)
            add("M05.S6.E043.commit_share",
                f"{by_me} of {tot} (the merged tree was pushed from E043's account)",
                "AUTO", FACTS_OUT + " key F-git-short; git shortlog", "Recompute if the teammates push their own commits before submission.")
        else:
            add(f"M05.S6.{roll}.commit_share",
                ("18 own commits (e077 branches, PRs #1 to #5)" if roll == "E077"
                 else "0 own commits; I worked on my code area (Section 2.2), merged through E043's account"),
                "CONFIRM", "git log --all --format=%ae; gh pr list", "Update if you push your own commits to the course repository.")
        add(f"M05.S6.{roll}.ai_draft_share", share, "CONFIRM", why, "Your own declaration. Evidence says about 100 % of the writing was first drafted by the AI assistant; do not lower it without a reason you can defend.")
        add(f"M05.S6.{roll}.ai_errors_caught", "3–5" if roll == "E043" else "1–2", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)" + "; evidence: " + {
            "E043": "cases E043-A, E043-B, E043-C in docs/submission/ai_audit_candidates.md.",
            "E051": "case E051-A in docs/submission/ai_audit_candidates.md and your own AI_DISCLOSURE.",
            "E075": "case E075-A in docs/submission/ai_audit_candidates.md and your own AI_DISCLOSURE.",
            "E077": "cases E077-A and E077-B in docs/submission/ai_audit_candidates.md and your own AI_DISCLOSURE."}[roll])
        add(f"M05.S6.{roll}.prior_simulator", "No", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")
        add(f"M05.S6.{roll}.most_valuable", REFLECT[roll][0], "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)" + "; drafted from the jury pitch notes, edit in your own words")
        add(f"M05.S6.{roll}.change_one_thing", REFLECT[roll][1], "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)" + "; drafted from the jury pitch notes, edit in your own words")
        for k in ("original", "code_runs", "viva_ready", "research_consent"):
            add(f"M05.SIGN.{roll}.{k}", "Yes", "CONFIRM", "team input, 31 Oct 2026 (relayed by E043)")

    extras = dict(sep=sep, rows=rows, prov=prov, CP=CP, econ=econ, mass=mass, g=g, W=W, tw=tw, ring=ring, csv_sha=csv_sha, fmea=fm, models=models,
                  contacts=contacts, uu_total=uu_total, n_uav_runs=n_uav_runs, n_tel=n_tel, n_runs=n_runs, vision_hz=vision_hz, hover=m_hover.group(1) if m_hover else None,
                  table=table, std_rows=std_rows)
    return F, extras


# ----------------------------------------------------------------------------- template walk
def w(t):
    return qn("w:" + t)


def cell_text(tc):
    return "".join(t.text or "" for t in tc.iter(w("t")))


def walk_template(doc):
    """Yield items in document order: ('heading', text) | ('field', n, tag, kind, options, label, table_idx) |
    ('box', table_idx, text) for tables without content controls."""
    body = doc.element.body
    items = []
    tidx = 0
    for el in body:
        t = el.tag.split("}")[1]
        if t == "p":
            tx = cell_text(el).strip()
            if re.match(r"^(SECTION \d|\d\.\d |DATA PROVENANCE|Individual Academic|Track A|30-second|Faculty code audit)", tx):
                items.append(("heading", tx))
        elif t == "tbl":
            tidx += 1
            trs = el.findall(w("tr"))
            header = [cell_text(tc).strip() for tc in trs[0].findall(w("tc"))] if trs else []
            if trs and any(True for _ in trs[0].iter(w("sdt"))):
                header = []                                    # no real header row: row 0 holds fields
            has = False
            for ri, tr in enumerate(trs):
                tcs = tr.findall(w("tc"))
                rowlab = cell_text(tcs[0]).strip() if tcs else ""
                if rowlab in ("type here", "Select ▾") or any(True for _ in tcs[0].iter(w("sdt"))):
                    rowlab = ""
                for ci, tc in enumerate(tcs):
                    for sdt in tc.iter(w("sdt")):
                        has = True
                        pr = sdt.find(w("sdtPr"))
                        tag = pr.find(w("tag")).get(w("val"))
                        opts = [li.get(w("displayText")) for li in pr.iter(w("listItem"))]
                        kind = "dropdown" if opts else "text"
                        col = header[ci] if ri > 0 and ci < len(header) else ""
                        lab = f"T{tidx} R{ri} C{ci}: " + " / ".join(x for x in (rowlab, col if (col and ci > 0 and ri > 0) else "") if x)
                        items.append(("field", tag, kind, opts, lab.strip(), tidx, sdt))
            if not has:
                items.append(("box", tidx, " | ".join(cell_text(tc).strip() for tr in trs for tc in tr.findall(w("tc")))[:160]))
    return items


# ----------------------------------------------------------------------------- docx writer
def set_sdt_text(sdt, text):
    content = sdt.find(w("sdtContent"))
    ts = list(content.iter(w("t")))
    assert ts, "sdt without a text run"
    ts[0].text = text
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for extra in ts[1:]:
        extra.text = ""


def set_cell_text(tc, text, mono=False):
    """Replace the visible run text of a plain cell (no content control) and keep its run properties."""
    runs = [r for r in tc.iter(w("r")) if r.find(w("t")) is not None]
    assert runs
    runs[0].find(w("t")).text = text
    for r in runs[1:]:
        r.getparent().remove(r)


def fill_code_cell(tc, lines):
    p0 = tc.find(w("p"))
    for r in p0.findall(w("r")):
        p0.remove(r)
    jc = p0.find(w("pPr")).find(w("jc"))
    if jc is not None:
        jc.set(w("val"), "left")
    first = True
    for ln in lines:
        if first:
            p = p0
            first = False
        else:
            p = copy.deepcopy(p0)
            for r in p.findall(w("r")):
                p.remove(r)
            tc.append(p)
        r = p.makeelement(w("r"), {})
        rpr = r.makeelement(w("rPr"), {})
        rf = rpr.makeelement(w("rFonts"), {w("ascii"): "Consolas", w("hAnsi"): "Consolas", w("cs"): "Consolas"})
        sz = rpr.makeelement(w("sz"), {w("val"): "16"})
        rpr.append(rf)
        rpr.append(sz)
        r.append(rpr)
        t = r.makeelement(w("t"), {})
        t.text = ln
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        r.append(t)
        p.append(r)


from dossier_concise import CONCISE, check_concise  # noqa: E402

REFLECT = {
    "E043": ("A result only counts once a test can break it: the head-on test showed APF alone fails, which led to the layered separation.",
             "Set up per-member commits from day one, so each member's work shows under their own account."),
    "E051": ("Labelled test frames catch detector errors a demo hides: the terracotta carpet false positive, fixed from 86 to 100 percent.",
             "Test the detector in dim indoor light early; indoor detection stayed at about 1 in 3."),
    "E075": ("The right test matters: Welch's t test, because guard and drone times vary so differently.",
             "Fix the false-alarm logic and the censored revisit window before the batch run, not after."),
    "E077": ("A business case is only as strong as its inputs: reading the simulation output directly and labelling every assumption makes it defensible.",
             "Get real quotes and the real guard roster early to replace the assumption ranges."),
}


def write_docx(F, items, extras, snippet_lines, fbd_text, out_path):
    doc = Document(TEMPLATE)
    before = len(list(doc.element.body.iter(w("sdt"))))
    # map tag -> sdt element
    sdts = {}
    for sdt in doc.element.body.iter(w("sdt")):
        sdts[sdt.find(w("sdtPr")).find(w("tag")).get(w("val"))] = sdt
    filled = 0
    for tag, (val, status, _s, _n) in F.items():
        if val is None:
            continue
        sdt = sdts[tag]
        pr = sdt.find(w("sdtPr"))
        opts = [li.get(w("displayText")) for li in pr.iter(w("listItem"))]
        if opts:
            assert val in opts, (tag, val, opts)
        elif tag in CONCISE:
            val = check_concise(tag, val, CONCISE[tag])
        set_sdt_text(sdt, val)
        filled += 1
    tables = doc.tables
    mi = extras["models"]["interior"]
    ncell = extras["prov"]["trials_per_cell"]
    # correct the two wrong template cells in 2 (mechanism table = T7)
    set_cell_text(tables[6].rows[3].cells[1]._tc,
                  "timestep %g s (%.0f Hz) · friction %g / %g / %g · %d rotor actuators (2 UAVs × %d rotors) · solref %g %g on the airframe class, %g %g on the floor"
                  % (mi["dt"], 1.0 / mi["dt"], mi["fr"][0], mi["fr"][1], mi["fr"][2], mi["nu"], mi["nu"] // 2, mi["sr_leg"][0], mi["sr_leg"][1], mi["sr_flr"][0], mi["sr_flr"][1]))
    set_cell_text(tables[6].rows[4].cells[1]._tc,
                  "PATROL (interior: Alpha flies the ground-floor corridor loop, Bravo sweeps the atrium galleries; exterior: the campus compound inside the boundary wall, ring flown as two arcs or by both UAVs half a lap apart) → DETECT (OpenCV HSV) → VERIFY → ALERT tier 0–3 (STATUS_3 = critical geofence breach) → TRACK → RETURN_TO_PATROL")
    for ti in (9, 10, 15, 20):                                  # fixed-height paste boxes would clip the code and the figures
        trh = tables[ti].rows[0]._tr.find(w("trPr")).find(w("trHeight"))
        trh.set(w("hRule"), "atLeast")
    fill_code_cell(tables[9].rows[0].cells[0]._tc, snippet_lines)
    # sign-off table: typed names as signatures (team decision, 31 Oct 2026)
    sign = tables[28]
    assert sign.rows[0].cells[4].text.strip() == "Signature", sign.rows[0].cells[4].text
    for row, name in zip(sign.rows[1:], ("Muaaz Mohammed Iqbal Shaikh", "Aditya Rajkumar", "Zaid Rezaur Rahman", "Soumya Subhankar Ranasingh")):
        assert row.cells[0].text.startswith(name.split()[0]), (row.cells[0].text, name)
        cell = row.cells[4]
        assert not cell.text.strip(), cell.text
        run = cell.paragraphs[0].add_run(name)
        run.italic = True
    set_cell_text(tables[10].rows[0].cells[0]._tc, fbd_text)
    # figures
    def put_pic(cell, path, width_cm, caption):
        p = cell.paragraphs[0]
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        p.add_run().add_picture(path, width=Cm(width_cm))
        cap = cell.add_paragraph()
        rr = cap.add_run(caption)
        rr.font.size = Pt(6.5)
    def fig(name):
        for d_ in FIG_DIRS:
            if os.path.exists(os.path.join(d_, name)):
                return os.path.join(d_, name)
        raise SystemExit(f"[MISSING] figure {name} in {FIG_DIRS}: run analytics/generate_paper_figures.py and analytics/campus_security_economics.py first")
    put_pic(tables[15].rows[0].cells[0], fig("campus_security_sensitivity.png"), 8.2,
            "Sensitivity of P_payback and NCRI (analytics/campus_security_economics.py, from the real trials).")
    put_pic(tables[15].rows[0].cells[1], fig("campus_security_queue.png"), 8.2,
            "Queue waiting time against utilisation (analytics/campus_security_economics.py).")
    c = tables[20].rows[0].cells[0]
    put_pic(c, fig("trajectory_interior.png"), 8.2, "Interior: one representative run per condition (rule stated on the figure), from analytics/runs telemetry.")
    p2 = c.add_paragraph()
    p2.add_run().add_picture(fig("trajectory_exterior.png"), width=Cm(8.2))
    cap = c.add_paragraph().add_run("Exterior: same rule.")
    cap.font.size = Pt(6.5)
    c = tables[20].rows[0].cells[1]
    put_pic(c, fig("revisit_boxplot_interior.png"), 8.2, "Interior: cycle time per lap (primary) and equal-window worst revisit, N = %d per condition." % ncell)
    p2 = c.add_paragraph()
    p2.add_run().add_picture(fig("revisit_boxplot_exterior.png"), width=Cm(8.2))
    cap = c.add_paragraph().add_run("Exterior: same two metrics, N = %d per condition." % ncell)
    cap.font.size = Pt(6.5)
    after = len(list(doc.element.body.iter(w("sdt"))))
    assert before == after, (before, after)
    doc.save(out_path)
    # re-open and recount from the saved file
    d2 = Document(out_path)
    saved = len(list(d2.element.body.iter(w("sdt"))))
    assert saved == before, (before, saved)
    return before, after, saved, filled


# ----------------------------------------------------------------------------- sheet writer
def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


NA = "not measured"


def vision_rows():
    """analytics/vision_illumination_summary.txt -> ({(scene, lighting): (n, iou_all, det_rate, hit_rate)} of the production detector,
    same for the auto-exposure ablation arm (gain off))."""
    path = os.path.join(G, "analytics", "vision_illumination_summary.txt")
    main_t, abl_t = {}, {}
    if os.path.isfile(path):
        cur = main_t
        for ln in open(path, encoding="utf-8"):
            if ln.startswith("AUTO-EXPOSURE ABLATION"):
                cur = abl_t
            elif ln.startswith(("YOLO COMPARISON", "BRIGHTNESS SWEEP")):
                cur = {}
            m = re.match(r"^(interior|exterior)\s+(noon|twilight)\s+(\d+)\s+([\d.]+)\s+[\d.nan]+\s+([\d.]+)\s+([\d.]+)", ln)
            if m and (m.group(1), m.group(2)) not in cur:
                cur[(m.group(1), m.group(2))] = (int(m.group(3)), m.group(4), m.group(5), m.group(6))
    return main_t, abl_t


def human_by_member(F):
    """HUMAN tags grouped per roll number or topic, for the closing checklist."""
    groups = {}
    for tag, (val, status, _s, note) in F.items():
        if status != "HUMAN":
            continue
        t = tag.replace("M05.", "")
        m = re.match(r"(?:S6|SIGN)\.(E\d+)\.(.+)", t)
        if m:
            groups.setdefault(m.group(1), []).append((t, note))
        elif t.startswith("S5.peer_"):
            groups.setdefault("peer review (every member scores the two assigned groups)", []).append((t, note))
        elif t.startswith("S5."):
            groups.setdefault("video (LinkedIn post, E043 uploads; every member appears)", []).append((t, note))
        else:
            groups.setdefault("team", []).append((t, note))
    return groups


def write_sheet(F, items, extras, snippet_info, snippet_lines, counts, out_path):
    rows, prov = extras["rows"], extras["prov"]
    CP = extras["CP"]
    L = []
    a = L.append
    n_cell = prov["trials_per_cell"]
    a("# Dossier fill sheet (E043), Group 05 MPSTME GUARDIAN")
    a("")
    a("Generated by `docs/build_dossier_fill.py` from the template, the real-trials CSV, `analytics/statistical_validation.py`, `analytics/campus_security_economics_output.txt`, `analytics/campus_security_fmea.py` with `analytics/ablation_trials.csv`, `docs/research/standards_verified.md`, `docs/submission/ai_audit_candidates.md`, the provenance JSON, the MJCF and git. Do not edit the numbers here by hand: change the evidence and re-run the builder. No SAP ID appears in this file and none may be added.")
    a("")
    a("Template: `docs/MDRIIA_Group_05_Technical_Dossier.docx` (sha256 `%s`, unchanged)." % sha256(TEMPLATE))
    a("Optional autofill: `docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx` (content controls before / after / in the saved draft: %d / %d / %d; fields filled: %d). **It is a DRAFT: open it in Microsoft Word, check every cell against this sheet, then do the HUMAN rows and export the PDF.**" % counts)
    a("Evidence base: CSV `analytics/campus_patrol_real_trials.csv` sha256 `%s` (%d rows, N = %d per cell, timestep %s s, code commit %s); facts printout `%s`." % (extras["csv_sha"], extras["n_runs"], n_cell, "/".join(sorted({r["timestep_s"] for r in rows})), prov.get("git_commit", prov.get("e043_commit")), FACTS_OUT))
    a("")
    a("Status codes: **AUTO** = derived from a script output or a cited source, paste as is. **CONFIRM** = derived but contains a team judgement or a choice, a person must agree. **No open status exists**: a measurable field is never left unfilled. **HUMAN** = only the member can supply it (left empty in the draft).")
    a("")
    cnt = {}
    for v in F.values():
        cnt[v[1]] = cnt.get(v[1], 0) + 1
    a("Field count: %d content controls in the template; %s; measurable fields left unfilled %d." % (len(F), ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())), cnt.get("PENDING", 0)))
    a("")
    a("## Read this first: the honest points the dossier must not hide")
    a("")
    nn = 1
    for sc in SCENES:
        pi = CP[sc]["PRIMARY"]
        eq = eqwin_of(rows, sc)
        gct = ms(rows, sc, "guard_baseline", "cycle_time_s", 2)
        if pi:
            a("%d. **Primary result, %s.** cycle_time_s (mean time per completed ground lap, window-independent), mean ± SD, N = %d: guard %s s, UAV sectors %s s, UAV offset ring %s s. Welch guard vs sectors: t = %s, df = %s, p = %s, d = %s, 95 %% CI of the difference [%s, %s] s."
              % (nn, sc, n_cell, gct, ms(rows, sc, "uav_sectors", "cycle_time_s", 2), ms(rows, sc, "uav_offset_ring", "cycle_time_s", 2), pi["t"], pi["df"], pi["p"], pi["d"], pi["ci"][0], pi["ci"][1]))
        else:
            a("%d. **Primary result, %s.** cycle_time_s is not measured for every cell (a cell has fewer than 2 runs with >= 2 completed laps): guard %s, sectors %s, offset ring %s; no Welch test is reported (analytics/statistical_validation_output.txt)."
              % (nn, sc, gct, ms(rows, sc, "uav_sectors", "cycle_time_s", 2), ms(rows, sc, "uav_offset_ring", "cycle_time_s", 2)))
        nn += 1
        a("%d. **Equal-window revisit, %s.** worst_revisit_ground_eqwin_s in one common window (%s s) is right-censored for the guard, so it is described, not tested (no t test, d or CI): %s. Guard %s; sectors %s; offset ring %s."
          % (nn, sc, eq or "not in this CSV", cr.descriptive_line(rows, sc, "guard_baseline", sv.UAV_CONDITIONS),
             eqw(rows, sc, "guard_baseline"), eqw(rows, sc, "uav_sectors"), eqw(rows, sc, "uav_offset_ring")))
        nn += 1
    a("%d. **Different windows.** Run windows (duration_s): interior guard %s s, UAV %s s; exterior guard %s s, UAV %s s. Per-window columns (worst_revisit_ground_s, n_ground_laps, detection) are not comparable across conditions; the primary metric and the equal-window revisit are."
      % (nn, durations(rows, "interior", "guard_baseline"), durations(rows, "interior", "uav_sectors"), durations(rows, "exterior", "guard_baseline"), durations(rows, "exterior", "uav_sectors")))
    nn += 1
    det = lambda sc, c: sum(1 for r in rows if r["scene"] == sc and r["condition"] == c and (r["detected"] or "").strip() in ("1", "1.0"))   # noqa: E731
    cn = lambda sc, c: sum(1 for r in rows if r["scene"] == sc and r["condition"] == c)                                                       # noqa: E731
    def wil(sc, c):
        w_ = sv.wilson_ci(det(sc, c), cn(sc, c))
        return "%d/%d (Wilson 95 %% [%.2f, %.2f])" % (det(sc, c), cn(sc, c), w_[0], w_[1])
    a("%d. **Detection (intruder verified inside the run window).** Interior: guard %s, UAV sectors %s, UAV offset ring %s. Exterior: guard %s, sectors %s, offset ring %s. The windows differ by condition, so report the counts, not an improvement claim, unless the interval supports it."
      % (nn, wil("interior", "guard_baseline"), wil("interior", "uav_sectors"), wil("interior", "uav_offset_ring"), wil("exterior", "guard_baseline"), wil("exterior", "uav_sectors"), wil("exterior", "uav_offset_ring")))
    nn += 1
    ct_ = extras["contacts"]
    a("%d. **FR-18 and contacts.** Obstacle contacts: %s. UAV-UAV contacts: %d in all %d UAV runs. In the interior the UAVs must sense all obstacles; minimum clearance by cell: %s."
      % (nn, ("%d in total over %d run(s): %s" % (sum(c[1] for c in ct_), len(ct_), ", ".join("%s (clearance %s m)" % (c[0], c[2]) for c in ct_))) if ct_ else "none in any run",
         extras["uu_total"], extras["n_uav_runs"],
         "; ".join("%s %s %s m" % (sc, c, ("%.4f" % min(cell_vals(rows, sc, c, "min_obstacle_clearance_m"))) if cell_vals(rows, sc, c, "min_obstacle_clearance_m") else NA) for sc in SCENES for c in UAVC)))
    nn += 1
    _lap = []
    for r in rows:
        if r["condition"] == "guard_baseline":
            continue
        for ag, col in (("Alpha", "n_laps_alpha"), ("Bravo", "n_laps_bravo")):
            known = (ag == "Bravo" and r["scene"] == "interior" and r["condition"] == "uav_sectors")      # Bravo sweeps the galleries there
            try:
                v_ = int(float(r[col]))
            except (KeyError, ValueError):
                continue
            if v_ < 2 and not known:
                _lap.append("%s %s (%d lap(s))" % (r["run_id"], ag, v_))
    _bad = sorted({c[0] for c in ct_} | {x.split(" ")[0] for x in _lap})
    a("%d. **Batch check status (computed from the CSV, not hidden).** Runs with obstacle contacts: %d; ground-loop UAV runs with fewer than 2 laps: %s. %s Interior uav_sectors Bravo flies the atrium galleries, not the ground loop, so its ground-lap count in the 300 s window is a known limit and is not counted as a failure. Any claim of 'no obstacle contact' or 'at least 2 laps in every run' must name these runs as exceptions, and the cell(s) containing them (%s) must not be described as clean."
      % (nn, len(ct_), ", ".join(_lap) if _lap else "none", ("Both checks passed in every run." if not ct_ and not _lap else "At least one batch check FAILED at this commit; the failing runs are listed above and in the statistics output."), ", ".join(sorted({"_".join(b.split("_")[:-1]) for b in _bad})) or "none"))
    nn += 1
    sp = extras["sep"]
    a("%d. **Separation.** Closest centre distance and runs below the %g m design separation: %s. Airframe span is in the model (docs/dossier_fill_facts_output.txt). Every claim of a held separation must say which cells came closer."
      % (nn, sv.D_SAFE_M, "; ".join("%s %s %s (%d of %d)" % (sc, c.replace("uav_", ""), ("%.2f m" % sp[(sc, c)][0]) if sp[(sc, c)][0] is not None else NA, sp[(sc, c)][1], sp[(sc, c)][2]) for sc in SCENES for c in UAVC)))
    nn += 1
    _wall = os.path.join(HERE, "submission", "viva_evidence", "inside_wall_check.txt")
    if os.path.exists(_wall):
        _txt = open(_wall, encoding="utf-8").read()
        _runs = re.findall(r"^(exterior_uav_\w+?)\.csv\.gz: samples=\d+ outside_wall=\d+ \(([\d.]+) %\), PATROL-outside=\d+, max distance outside=([\d.]+) m", _txt, re.M)
        _st = dict((m[0], float(m[2])) for m in re.findall(r"^  (\w+): (\d+) samples, max ([\d.]+) m outside", _txt, re.M))
        _cps = re.findall(r"^patrol_cp\d+ inside=(True|False)", _txt, re.M)
        if _runs:
            a("%d. **Flown track versus the wall** (docs/submission/viva_evidence/inside_wall_check.py on the local telemetry of the committed batch; output docs/submission/viva_evidence/inside_wall_check.txt). All %d exterior patrol checkpoints are inside the boundary wall; in %d exterior UAV runs the airframe centre was outside the wall polygon in %.2f to %.2f %% of samples per run, at most %.2f m outside. Say 'the patrol route is inside the college', not 'the UAVs never leave it'."
              % (nn, sum(1 for c in _cps if c == "True"), len(_runs), min(float(r[1]) for r in _runs), max(float(r[1]) for r in _runs), max(float(r[2]) for r in _runs)))
            nn += 1
    vr, va = vision_rows()
    if vr:
        g_ = lambda d, k: d.get(k, (0, 0, 0, NA))[3]      # noqa: E731
        a("%d. **Detector at twilight** (analytics/vision_illumination_summary.txt; twilight = authored light x0.15, an ASSUMPTION, not a measured lux). Production detector hit rate: interior noon %s, interior twilight %s; exterior noon %s, exterior twilight %s. Same frames with the low-light gain switched off: interior twilight %s, exterior twilight %s. FMEA row for the twilight fix (interior, before -> after): %s -> %s."
          % (nn, g_(vr, ("interior", "noon")), g_(vr, ("interior", "twilight")), g_(vr, ("exterior", "noon")), g_(vr, ("exterior", "twilight")),
             g_(va, ("interior", "twilight")), g_(va, ("exterior", "twilight")),
             extras["fmea"][("interior", "missed_intruder_twilight")]["before"], extras["fmea"][("interior", "missed_intruder_twilight")]["after"]))
    else:
        a("%d. **Detector at twilight:** analytics/vision_illumination_summary.txt not found; not measured here." % nn)
    nn += 1
    a("%d. **Economics are conditional.** Payback numbers come from ASSUMPTION ranges printed in the SOURCES table of the economics output. Say 'conditional on assumed ranges'; the queue delay is about zero because the assumed incident rate is tiny." % nn)
    nn += 1
    a("%d. **Telemetry** is kept for %d of %d runs (disk); the CSV metrics of every run were computed in the same %s s loop. UAV vision ran at %s Hz in the batch (the FSM default is %.0f Hz)."
      % (nn, extras["n_tel"], extras["n_runs"], extras["models"]["interior"]["dt"], extras["vision_hz"], C.VISION_HZ))
    nn += 1
    a("%d. **Authorship.** Each member owned one area: E043 flight control, separation, FSM, scenes, guard baseline and the benchmark runner; E051 vision (detector, projection, handoff, illumination benchmark); E075 geofence and statistics; E077 economics, queue, sensitivity and FMEA. E043 merged the areas into one tree, so this branch's commits carry E043's account; E077 also has his own commits on the e077 branches (PRs #1 to #5). Sections 2.2, 5.1 and 6 record this. Do not claim commits a member did not push." % nn)
    nn += 1
    a("%d. **Template prints SAP IDs.** The cover table already carries a SAP ID per member from the official list. Do not copy IDs from anywhere; each member enters or verifies their own on the cover and in docs/TEAM_ROSTER.json. HUMAN." % nn)
    a("")
    a("**Items outside the content controls (all HUMAN):** each member's SAP ID on the cover and in docs/TEAM_ROSTER.json; the Signature column of the sign-off table; the photo of the hand-drawn free-body diagram in 2.4; exporting the PDF from Word; committing the .docx and .pdf to docs/; turning the PDF in on MS Teams (every member).")
    a("")
    a("## HUMAN fields per member (left empty in the draft; nobody else may fill them)")
    a("")
    for who, lst in sorted(human_by_member(F).items()):
        a("- **%s** (%d fields): %s" % (who, len(lst), ", ".join("`%s`" % t for t, _n in lst)))
    a("")
    a("## Template corrections (pre-filled faculty text that is wrong for our model; fixed only in the autofill draft, the faculty's .docx stays byte-identical)")
    a("")
    mi = extras["models"]["interior"]
    a("| Where | Template says | Correct text | Done in the draft docx |")
    a("|---|---|---|---|")
    a("| Section 2 mechanism table, row 'Contact & solver settings in the model today' | timestep 0.004 s (250 Hz: set 0.002 s for 500 Hz logging) · friction 1.0 / 0.01 / 0.005 · 9 actuators (2 × 4 rotors + 1) · solref default | timestep %g s (%.0f Hz) · friction %g / %g / %g · **%d rotor actuators (2 UAVs × %d rotors)** · solref %g %g on the airframe class, %g %g on the floor (all read back from the compiled model) | yes |"
      % (mi["dt"], 1.0 / mi["dt"], mi["fr"][0], mi["fr"][1], mi["fr"][2], mi["nu"], mi["nu"] // 2, mi["sr_leg"][0], mi["sr_leg"][1], mi["sr_flr"][0], mi["sr_flr"][1]))
    a("| Section 2 mechanism table, row 'Core state machine (FSM)' | PATROL (Alpha NE / Bravo SW sectors) → ... | PATROL (interior: **Alpha flies the ground-floor loop, Bravo sweeps the atrium galleries**; exterior: the campus compound inside the boundary wall, ring flown as two arcs or by both UAVs half a lap apart) → DETECT (OpenCV HSV) → VERIFY → ALERT tier 0–3 → TRACK → RETURN_TO_PATROL | yes |")
    a("| Section 2, 'Faculty code audit' line | Timestep is 0.004 s | Leave as the faculty's remark; our value is %g s (Section 2.1 field). | no |" % mi["dt"])
    a("| Section 3 table, row 'Constants hard-coded in the script today' | scaffold constants, each typed in as a result | None remain; the inputs are the SOURCES table printed by the economics script. Do not repeat the scaffold numbers anywhere. | no |")
    a("| Section 3 'CSBS business case' text and Section 4 'Evaluation protocol' text | claims carried from the titles sheet; N = 25 sweeps; energy in Wh/km | These are the faculty's titles-sheet texts; do not repeat them. Our N is %d per cell; energy is reported per run (energy_wh), Wh/km is **not measured**. | no |" % n_cell)
    a("| Paste boxes 2.3, 2.4, the business-graph box and the Section 4 plot box | fixed row height (exact), which clips pasted code and figures | row height changed from exact to at-least so the content shows | yes (layout only) |")
    a("| Section 2 equations cell | separation field with d_safe = %g m | Matches compute_apf_separation (K_rep = %s). The DLS-IK equation is for manipulators and is not used by our UAVs. | no |" % (sv.D_SAFE_M, C.K_REP))
    a("")
    a("The template's '9 actuators' is not ours: the course scaffold model in the initial commit already has 8 motors (git show c3fdea7:Group_05_Muaaz_Aditya_Zaid_Soumya/models/uav_fleet.xml), and the template was copied in unchanged from the course monorepo. It is a faculty template error, not an AI audit case.")
    a("")
    a("## Fields in template order")
    a("")
    n = 0
    need_header = False
    for it in items:
        if it[0] == "heading":
            a("")
            a("### " + esc(it[1][:90]))
            a("")
            need_header = True
        elif it[0] == "field":
            if need_header:
                a("| # | Tag | Where | Value to paste | Status | Source / how to check |")
                a("|---|---|---|---|---|---|")
                need_header = False
            n += 1
            _, tag, kind, opts, lab, tidx, _sdt = it
            val, status, src, note = F[tag]
            vtxt = ("**%s**" % esc(val)) if val is not None else "*(leave empty)* " + esc(note)
            if val is not None and kind == "dropdown":
                vtxt = "dropdown: **%s**" % esc(val)
            if note and val is not None:
                vtxt += " <br>_Note: %s_" % esc(note)
            a("| %d | `%s` | %s | %s | %s | %s |" % (n, tag.replace("M05.", ""), esc(lab), vtxt, status, esc(src)))
        elif it[0] == "box":
            _, tidx, txt = it
            special = {
                10: "**2.3 code box (T10)**: paste the snippet below as text, Consolas 8 pt (filled in the draft).",
                11: "**2.4 FBD box (T11)**: HUMAN: insert a photo of the hand-drawn free-body diagram, then paste the worked example below (text filled in the draft).",
                16: "**Graph box (T16)**: left = `campus_security_sensitivity.png`, right = `campus_security_queue.png` from analytics/figures (inserted in the draft).",
                21: "**Plot box (T21)**: left = `docs/figures/trajectory_interior.png` and `trajectory_exterior.png`, right = `docs/figures/revisit_boxplot_interior.png` and `revisit_boxplot_exterior.png` (inserted in the draft).",
            }.get(tidx)
            if special:
                a("")
                a("> " + special)
                a("")
                need_header = True
    a("")
    a("## Section 2.3 snippet (real lines, %s)" % snippet_info)
    a("")
    a("```")
    for ln in snippet_lines:
        a(ln)
    a("```")
    a("")
    a("Line numbers are for the current branch tip. Re-run `python docs/dossier_fill_facts.py > docs/dossier_fill_facts_output.txt` and this builder after any edit to src/aerial_patrol_swarm.py, then refresh the numbers before exporting the PDF.")
    a("")
    a("## Section 2.4 worked example (hover free-body diagram)")
    a("")
    a(FBD_TEXT_LONG(extras))
    a("")
    a("## Section 2.2 full authorship table (the template has 5 rows)")
    a("")
    a("| File | Written / Modified / Used as given | Main author | Commits on the E043 branch | Note |")
    a("|---|---|---|---|---|")
    for f, wmu, au, note in AUTHORSHIP:
        try:
            nc = git("rev-list", "--count", "HEAD", "--", f)
        except Exception:
            nc = "-"
        note = note.format(dt=extras["models"]["interior"]["dt"], n_rf=extras["models"]["interior"]["n_rf"], n_fmea=len(fmea.MODES))
        a("| `%s` | %s | %s | %s | %s |" % (f, wmu, au, nc, esc(note)))
    a("")
    a("Honest statement for the table and the viva: the work was split by area. E043: flight control, separation, FSM, scenes, guard baseline, benchmark runner and integration. E051: vision (HSV detector, projection, target handoff, illumination benchmark). E075: geofence tiers and hysteresis, noise demo, statistical validation. E077: economics, M/M/c queue, sensitivity and FMEA. The %s commits touching this folder on the current branch carry Muaaz's GitHub account because the areas were merged into one tree and pushed from it; E077's own commits are on the e077 branches (PRs #1 to #5). Each member declares their own share and hours in Section 6. All four areas were AI-assisted (Section 5.1)." % git("rev-list", "--count", "HEAD", "--", "."))
    a("")
    a("## L-10: AI-use declaration to paste under Section 5.1 and into the Section 6 context")
    a("")
    a(AI_DECLARATION)
    a("")
    a("The per-member share in the Section 6 dropdowns is each member's own declaration (default shown: the evidence says about all of the first draft was AI-written); the three cases in Section 5.1 are the ones with proof on file (E043-A to E043-C); the full candidate list with evidence, including E051-A, E075-A and E077-A, is `docs/submission/ai_audit_candidates.md`.")
    a("")
    a("## FMEA coverage")
    a("")
    a("The template's FMEA table holds five rows; `analytics/campus_security_fmea.py` computes exactly these five modes, so nothing is left over for extra rows. O and D come from measured rates (ablation_trials.csv before arm; trials CSV for detection), S is team judgement, and a row without both arms prints 'not measured' instead of a number. The wind-gust and link-loss modes of the earlier draft are not computed any more.")
    a("")
    a("Section ownership (who must be able to defend which section at the viva; the numbers in the sheet come from the owner's script output): E043 Section 2, the figures in Section 4, compile and export; E051 the vision values in 3.2 and 4 and the E051 rows of 2.2; E075 Section 4 (protocol, results table, provenance) and 1.2 with E043; E077 Section 3 (business table, FMEA, two graphs), 1.1 and 1.3.")
    a("")
    a("## Figures and where they come from")
    a("")
    a("| Figure | Path | Produced by |")
    a("|---|---|---|")
    for f, by in (("docs/figures/trajectory_interior.png", "analytics/generate_paper_figures.py --runs-dir <telemetry>"),
                  ("docs/figures/trajectory_exterior.png", "same"),
                  ("docs/figures/revisit_boxplot_interior.png", "analytics/generate_paper_figures.py (CSV only): cycle time and equal-window revisit"),
                  ("docs/figures/revisit_boxplot_exterior.png", "same"),
                  ("docs/figures/interior_obstacle_clearance.png", "same (FR-18 evidence)"),
                  ("docs/figures/separation_hist_interior.png", "same (inter-UAV separation)"),
                  ("docs/figures/separation_hist_exterior.png", "same"),
                  ("docs/figures/fmea_before_after.png", "same (needs analytics/ablation_trials.csv)"),
                  ("analytics/figures/campus_security_sensitivity.png", "analytics/campus_security_economics.py"),
                  ("analytics/figures/campus_security_queue.png", "analytics/campus_security_economics.py")):
        a("| %s | `%s` | %s |" % (os.path.basename(f), f, by))
    a("")
    a("Regenerate every figure from the hash-checked CSV before exporting the PDF (`python analytics/generate_paper_figures.py --runs-dir <telemetry dir>` and `python analytics/campus_security_economics.py`); this builder embeds whatever is in those folders and cannot tell whether it is current.")
    a("")
    open(out_path, "w").write("\n".join(L) + "\n")


AUTHORSHIP = [
    ("models/campus_perimeter_patrol.xml", "Modified by us", "E043", "scaffold wrapper; timestep {dt:g} s"),
    ("models/campus_perimeter_patrol_exterior.xml", "Modified by us", "E043", "scaffold wrapper; timestep {dt:g} s"),
    ("models/common.xml", "Used as given / modified in the initial commit", "E043", "one commit only; contact defaults"),
    ("models/uav_fleet.xml", "Modified by us", "E043", "{n_rf} range-finder sites per airframe added (FR-18)"),
    ("src/aerial_patrol_swarm.py", "Modified by us", "Shared", "E043 outside the region markers; E051 and E075 regions by their own patches"),
    ("src/foot_patrol_baseline.py", "Written by us", "E043", "guard baseline"),
    ("src/patrol_metrics.py", "Written by us", "E043", "one metric function shared by all conditions"),
    ("src/run_telemetry.py", "Written by us", "E043", "contract-B per-step telemetry"),
    ("src/view_live.py", "Modified by us", "E043", "FSM overlay, rays, head-on demo"),
    ("analytics/run_benchmark.py", "Modified by us", "E043", "scaffold rewritten as the resumable two-scene runner"),
    ("analytics/generate_paper_figures.py", "Modified by us", "E043", "starter script rewritten: reads only the real CSV"),
    ("analytics/campus_security_economics.py", "Written by us (rewrite; original draft by E077, integrated by E043)", "E077", "rewrite of the scaffold file"),
    ("tests/test_e043_pipeline.py", "Written by us", "E043", "telemetry rate, RMSE and effort, determinism, shared scoring"),
    ("tests/test_e043_exterior_route_inside_campus.py", "Written by us", "E043", "every exterior checkpoint inside the boundary wall"),
    ("analytics/vision_illumination_benchmark.py", "Written by us (original draft by E051, integrated by E043)", "E051", "noon versus twilight detector benchmark"),
    ("analytics/vision_yolo_compare.py", "Written by us (original draft by E051, integrated by E043)", "E051", "optional YOLO comparison; OpenCV HSV is the primary detector"),
    ("tests/test_e051_vision.py", "Written by us (original draft by E051, integrated by E043)", "E051", "detector, projection and handoff tests"),
    ("analytics/statistical_validation.py", "Written by us (original draft by E075, integrated by E043)", "E075", "Welch t, df, p, Cohen's d and 95 % CI from the real CSV"),
    ("analytics/geofence_noise_demo.py", "Written by us (original draft by E075, integrated by E043)", "E075", "false-alarm demo with position noise"),
    ("tests/test_e075_geofence_stats.py", "Written by us (original draft by E075, integrated by E043)", "E075", "tiers, hysteresis, noise, breach log, link loss, statistics"),
    ("analytics/campus_security_fmea.py", "Written by us (original draft by E077, integrated by E043)", "E077", "computed FMEA, {n_fmea} modes"),
    ("tests/test_e077_economics.py", "Written by us (original draft by E077, integrated by E043)", "E077", "refusals, no money, no literal results, Erlang C, FMEA"),
    ("tests/test_e043_separation.py", "Written by us", "E043", "APF-only versus layered separation"),
    ("tests/test_e043_surveillance_fsm.py", "Written by us", "E043", "FSM transitions, handoff, FR-18 in TRACK"),
    ("tests/test_e043_obstacle_perception.py", "Written by us", "E043", "FR-18 class by class"),
]

AI_DECLARATION = (
    "**AI-use declaration (Muaaz Mohammed Iqbal Shaikh, E043, and group).** An AI coding assistant (Claude, Anthropic) drafted, under Muaaz's instructions, the scene generators (models/scene_source), the flight controller and surveillance state machine in src/aerial_patrol_swarm.py, the guard baseline, the benchmark and ablation runners, the figure and statistics scripts, the tests, the project documents and product requirement documents, this dossier fill sheet, and the multi-agent workflow that produced the Monte Carlo batch. Muaaz directed his area, merged the four areas into one tree and ran the batch [CONFIRM: Muaaz, edit this sentence to say exactly what you did yourself]; the estimated AI-drafted share of E043's code and text is 76 to 100 %. "
    "The other three areas were owned by their members (E051 vision, E075 geofence and statistics, E077 economics and FMEA) and were also AI-assisted, each with an AI_DISCLOSURE note of what was drafted and what the member verified. Each member declares their own share and hours in Section 6; E077's own commits are on the e077 branches, and the merged tree was pushed from E043's account. "
    "No number in Sections 3 and 4 is typed in by hand: they are printed by scripts from analytics/campus_patrol_real_trials.csv (hash-checked) or from labelled ASSUMPTION ranges. Wrong AI output we caught and corrected is listed in Section 5.1 with its proof, and the unsourced claims carried from the titles sheet were deleted because no primary source exists."
)


def FBD_TEXT_LONG(x):
    return ("Free-body diagram of one UAV in hover (draw it: body at the centre, weight W = m g downward, four rotor forces F0 to F3 upward at arm length l = %.2f m on the + layout, wind drag omitted). "
            "Hover balance: F0 + F1 + F2 + F3 = m g. Worked example with the model's own numbers (printed by docs/dossier_fill_facts.py from body_subtreemass, key F-mass): m = %.2f kg, so m g = %.2f x %.2f = %.2f N; per rotor %.2f N; maximum thrust 4 x %.1f N = %.1f N, so T/W = %.1f / %.2f = %.2f. "
            "In the telemetry CSV (analytics/runs/<run>.csv.gz) the rotor forces are columns f0..f3 in N; the median of f0+f1+f2+f3 for Alpha while fsm_state = PATROL in interior_uav_sectors_s1 is %s N (key F-tel-hover), against m g = %.3f N."
            % (C.ARM_L, x["mass"], x["mass"], x["g"], x["W"], x["W"] / 4, C.F_MAX, 4 * C.F_MAX, 4 * C.F_MAX, x["W"], x["tw"], x["hover"] or "not measured", x["W"]))


# ----------------------------------------------------------------------------- main
def main():
    global CSV_PATH, PROV_PATH, ABL_PATH, ABL_PROV_PATH, ECON_OUT, TEST_MODE, SHEET, DRAFT, STATS_OUT, FACTS_PATH
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-docx", action="store_true")
    ap.add_argument("--csv", default=CSV_PATH)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--ablation", default=ABL_PATH)
    ap.add_argument("--ablation-provenance", default=None)
    ap.add_argument("--econ-output", default=ECON_OUT)
    ap.add_argument("--stats-output", default=STATS_OUT)
    ap.add_argument("--facts", default=FACTS_PATH)
    ap.add_argument("--out-dir", default=None, help="folder for the sheet and the draft (default docs/)")
    ap.add_argument("--test-mode", action="store_true", help="smoke-test run: stale or missing economics/statistics/facts outputs only warn; needs --out-dir outside docs/")
    a = ap.parse_args()
    canonical = os.path.abspath(a.csv) == os.path.abspath(CSV_PATH)
    if a.test_mode or not canonical:
        if not a.out_dir or os.path.abspath(a.out_dir).startswith(HERE):
            raise SystemExit("[REFUSED] a test run (--test-mode or a non-canonical --csv) needs --out-dir outside docs/, so it can never overwrite the real sheet or draft")
    TEST_MODE = a.test_mode or not canonical
    CSV_PATH = os.path.abspath(a.csv)
    PROV_PATH = a.provenance or sv.default_provenance(CSV_PATH)
    ABL_PATH = a.ablation
    ABL_PROV_PATH = a.ablation_provenance or sv.default_provenance(ABL_PATH)
    ECON_OUT, STATS_OUT, FACTS_PATH = a.econ_output, a.stats_output, a.facts
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)
        SHEET = os.path.join(a.out_dir, os.path.basename(SHEET))
        DRAFT = os.path.join(a.out_dir, os.path.basename(DRAFT))
    assert sha256(TEMPLATE) == TEMPLATE_SHA256, "the template differs from the recorded sha256"
    F, extras = build_fields()
    doc = Document(TEMPLATE)
    items = walk_template(doc)
    tags = [it[1] for it in items if it[0] == "field"]
    missing = [t for t in tags if t not in F]
    surplus = [t for t in F if t not in tags]
    assert not missing and not surplus, ("missing", missing, "surplus", surplus)
    assert len(tags) == len(set(tags)) == 226, len(tags)
    for it in items:
        if it[0] == "field" and F[it[1]][0] is not None and it[2] == "dropdown":
            assert F[it[1]][0] in it[3], (it[1], F[it[1]][0], it[3])
    # snippet
    lines = open(os.path.join(G, "src", "aerial_patrol_swarm.py")).read().splitlines()
    i0 = next(i for i, ln in enumerate(lines) if ln.strip() == 'if self.surv_state in ("DETECT", "VERIFY"):')
    seg = lines[i0:i0 + 19]
    seg = [ln[8:] if ln.startswith(" " * 8) else ln for ln in seg]
    snippet_lines = ["src/aerial_patrol_swarm.py, DualUAVSurveillanceController._fsm_step (VERIFY -> ALERT transition), lines %d-%d" % (i0 + 1, i0 + 19)]
    snippet_lines += [f"{i0 + 1 + k:4d}  {ln}" for k, ln in enumerate(seg)]
    assert len(snippet_lines) - 1 <= 25
    counts = (0, 0, 0, 0)
    assert not any(v[1] == "PENDING" for v in F.values()), "PENDING fields are not allowed"
    if a.write_docx:
        counts = write_docx(F, items, extras, snippet_lines, FBD_TEXT_LONG(extras), DRAFT)
    write_sheet(F, items, extras, "E043 branch tip %s, lines %d-%d, %d lines" % (git("rev-parse", "--short", "HEAD"), i0 + 1, i0 + 19, 19), snippet_lines, counts, SHEET)
    st_ = {}
    for v in F.values():
        st_[v[1]] = st_.get(v[1], 0) + 1
    print("fields", len(F), st_, "sdt counts (before, after, saved, filled):", counts)
    print("template sha256", sha256(TEMPLATE))


if __name__ == "__main__":
    main()
