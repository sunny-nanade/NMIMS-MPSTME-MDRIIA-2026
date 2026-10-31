# Build the integrated dossier draft from the autofill draft (E077) | MDRIIA Group 05
"""
  python analytics/campus_security_dossier_fill.py      (needs lxml: pip install lxml)

Reads docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx (never written) and
writes docs/MDRIIA_Group_05_Technical_Dossier_INTEGRATED_DRAFT.docx:
  * Section 3 values are computed here by analytics/campus_security_economics.py and
    campus_security_fmea.py from the real-trials CSV; nothing is typed in.
  * Only the text of existing content controls (w:sdt) is replaced; the number of
    content controls before and after must be equal.
  * The two business graphs are replaced by analytics/figures/campus_security_*.png.
  * Before anything is written it checks: the real-trials CSV sha256 against "csv_sha256" in its
    provenance JSON; the ablation CSV likewise; and that every embedded campus_security_*.png is
    not older than the CSV (run analytics/campus_security_economics.py first). Any failure exits with an error.
  * "gate PASS in N cells" and "runs closer than 2.5 m were ..." are computed from the data here.
  * HUMAN fields (SAP IDs, hours, reflections, LinkedIn, peer-review scores,
    signatures) are not touched.
"""
import io
import os
import subprocess
import sys
import zipfile

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import campus_security_economics as econ  # noqa: E402
import campus_security_fmea as fmea  # noqa: E402

SRC = os.path.join(G, "docs", "MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx")
DST = os.path.join(G, "docs", "MDRIIA_Group_05_Technical_Dossier_INTEGRATED_DRAFT.docx")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W, "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
OUT_FILE = "analytics/campus_security_economics_output.txt"
# business graphs in the draft: relationship id -> replacement figure
FIGURES = {"rId10": "campus_security_sensitivity.png", "rId11": "campus_security_queue.png"}
# caption in the draft (matched by its start) -> replacement text
CAPTIONS = {
    "Sensitivity of P_payback and NCRI (":
        f"Sensitivity of P_payback and NCRI to capex_ratio, -{econ.SWEEP:.0%} to +{econ.SWEEP:.0%} (E077, analytics/campus_security_economics.py on the real-trials CSV).",
    "Queue waiting time against utilisation (":
        "Queue waiting time and utilisation against arrival rate, M/M/c with c = 1 and 2 (E077, same script; stress range and service-time inputs labelled in the figure).",
}


def check_figures_fresh(csv_path, fig_paths):
    """Exit with an error if any figure is missing or older than the CSV it was computed from."""
    csv_mtime = os.path.getmtime(csv_path)
    for path in fig_paths:
        if not os.path.isfile(path):
            raise SystemExit(f"missing figure {path}: run analytics/campus_security_economics.py first")
        if os.path.getmtime(path) < csv_mtime:
            raise SystemExit(f"stale figure {path}: older than {os.path.basename(csv_path)}; "
                             "re-run analytics/campus_security_economics.py before filling the dossier")


def close_claim(rows):
    """Which UAV conditions the runs closer than D_SAFE_M belong to, computed from the data."""
    uav = [r for r in rows if r["condition"] != "guard_baseline"]
    close = [r for r in uav if float(r["min_inter_uav_m"]) < fmea.D_SAFE_M]
    conds = sorted({r["condition"] for r in close})
    if not close:
        return f"no UAV run closer than {fmea.D_SAFE_M:g} m (0 of {len(uav)})"
    if len(conds) == 1:
        return f"all {len(close)} of {len(uav)} UAV runs closer than {fmea.D_SAFE_M:g} m were {conds[0]} runs"
    return (f"{len(close)} of {len(uav)} UAV runs were closer than {fmea.D_SAFE_M:g} m, in "
            + ", ".join(f"{c} ({sum(1 for r in close if r['condition'] == c)})" for c in conds))


def git(*args):
    return subprocess.check_output(["git", "-C", G, *args], text=True).strip()


def rng(name):
    """'lo to hi' for an ASSUMPTION range, or the single value, read from econ.SOURCES."""
    v = econ.SOURCES[name][0]
    return f"{v[0]:g} to {v[1]:g}" if econ.is_range(v) else f"{v:g}"


def na_or(r, fn):
    """fn(r) when the revisit gate passed, else the 'n/a (gate FAIL)' marker (no kappa, NCRI or payback is claimed)."""
    return fn(r) if r["gate"] else econ.NA


def fields(p0, res, fm, rows):
    cells = [(s, c) for s in econ.SCENES for c in econ.UAV_CONDITIONS]
    name = lambda s, c: f"{s} {c.replace('uav_', '')}"  # noqa: E731
    per = lambda fn: "; ".join(fn(s, c, res[(s, c)]) for s, c in cells)  # noqa: E731
    src = []
    for k, (v, unit, kind, _) in econ.SOURCES.items():
        val = f"{v[0]:g} to {v[1]:g}" if econ.is_range(v) else f"{v:g}"
        src.append(f"{k} {val} [{unit}] {kind}")
    key, rel = econ.most_uncertain()
    lo, hi = econ.SOURCES[key][0]
    ri, re_ = res[("interior", "uav_sectors")], res[("exterior", "uav_sectors")]
    n_pass = sum(1 for sc, cd in cells if res[(sc, cd)]["gate"])
    gate_text = (f"gate PASS in all {len(cells)} cells" if n_pass == len(cells) else
                 f"gate PASS in {n_pass} of {len(cells)} cells; FAIL cells report kappa, NCRI and payback as {econ.NA}: "
                 + ", ".join(name(sc, cd) for sc, cd in cells if not res[(sc, cd)]["gate"]))
    inc_lo, inc_hi = econ.SOURCES["incidents_per_month"][0]
    inc_mid = p0["incidents_per_month"]
    g_min_lo, g_min_hi = econ.SOURCES["guard_response_min"][0]
    c_lo, c_hi = econ.SOURCES["guard_responders"][0]
    life_cycles = econ.SOURCES["battery_cycle_life"][0]
    n_scripts = sum(1 for fn in os.listdir(os.path.join(G, "tests")) if fn.startswith("test_e077_"))
    uav_rows = [r for r in rows if r["condition"] != "guard_baseline"]
    close_text = close_claim(rows)
    n_guard = sum(1 for r in rows if r["condition"] == "guard_baseline" and r["scene"] == "interior")

    def be(s, c, r):
        if not r["gate"]:
            return f"{name(s, c)}: break-even {econ.NA}"
        if r["be"] is not None:
            return f"{name(s, c)}: break-even {key} = {r['be']:.3f}"
        need = econ.bisect(lambda x: econ.p_payback(dict(p0, **{key: x}), r["t_uav"]) - 1, 1e-9, 1e3)
        return (f"{name(s, c)}: no break-even inside the assumed range ({lo:g}, {hi:g}) or the -{econ.SWEEP:.0%}/+{econ.SWEEP:.0%} sweep; "
                f"P_payback = 1 only at {key} = {need:.3f}; {key} at kappa = target {r['k_target']:.3f}")

    def fm_text(scene, k):
        return fm[(scene, k)]

    f = {}
    # ---- 2.2 authorship
    f["M05.S2.script2.change"] = (
        "E043: cascaded flight control, layered separation, FR-18 range-ring avoidance, surveillance FSM, telemetry hooks. "
        "The E051 region (detect_intruder_hsv, HSV detector) and the E075 region (evaluate_geofence_status with hysteresis) are committed in "
        "src/aerial_patrol_swarm.py; the code hash used for the trials CSV is recorded in its provenance file. AI-drafted, then run and tested.")
    f["M05.S2.script3.change"] = (
        "Rewritten by E077: the eight hard-coded constants removed; reads cycle_time_s, worst_revisit_ground_s, detection_latency_s and "
        "verify_time_s from the real-trials CSV; SOURCES table (cited value or ASSUMPTION range); H_reclaimed, delta FTE, kappa/NCRI, P_payback, "
        "T_payback, M/M/c (Erlang C), +/-30 % sensitivity with bisection. Also E077: analytics/campus_security_fmea.py, tests/test_e077_*.py, "
        "and the optional runtime in integrations/guardian_runtime/ and integrations/multi_uav_jev/ (not used for any number in Sections 3-4). "
        "AI-assisted (Claude), run and checked by E077.")
    # ---- 3.1 business model
    f["M05.S3.E077.hreclaimed_inputs"] = (
        f"H_patrol = shifts (24 / hours_per_shift) x rounds_per_shift x guards_per_round x T_guard_cycle, where T_guard_cycle is the simulated "
        f"mean cycle_time_s of guard_baseline (N = {n_guard}); H_reclaimed = replacement_fraction x H_patrol, only if every UAV "
        f"worst revisit is below the equal window (the guard's equal-window revisit is right-censored, a lower bound, so it is not compared; {gate_text}). Base case = midpoint of each range. "
        f"Inputs as printed by the script (SOURCES table, citations in {OUT_FILE}): " + "; ".join(src) + ".")
    f["M05.S3.E077.hreclaimed_metric"] = (
        f"interior {ri['H']:.2f} guard-hours/day, exterior {re_['H']:.2f} guard-hours/day (both UAV conditions); "
        f"delta FTE = H x 365 / {p0['fte_hours_per_year']:g}: interior {ri['fte']:.3f}, exterior {re_['fte']:.3f}. "
        "Conditional on the ASSUMPTION ranges.")
    f["M05.S3.E077.payback_inputs"] = (
        f"P_payback = k / (T_life x (R - k u)); T_payback = 12 k / (R - k u) months. k = capex_ratio (fleet acquisition cost over one year "
        f"of the guard patrol labour H_patrol, ASSUMPTION {lo:g} to {hi:g}); u = maintenance_fraction + other_opex_fraction + battery term "
        "(battery_capex_share x charge cycles per UAV-year / battery_cycle_life; cycles per UAV-year = replaced rounds per year x simulated UAV cycle_time_s "
        f"/ endurance_min; {life_cycles:g} from the DJI Matrice 350 RTK product page, a reference airframe); R = replacement_fraction (ASSUMPTION); "
        f"T_life = service_life_years (ASSUMPTION {rng('service_life_years')}). All costs are dimensionless ratios to the guard baseline.")
    f["M05.S3.E077.payback_metric"] = (
        "P_payback (base case, envelope over all range corners): "
        + per(lambda s, c, r: f"{name(s, c)} " + na_or(r, lambda r: f"{econ.fmt(r['P'])} ({econ.fmt(r['P_env'][0])} to {econ.fmt(r['P_env'][1])}; "
                              f"{r['never']} of {r['n_corners']} corners never pay back)"))
        + ". P < 1 = recovered inside the service life. Conditional on assumed ranges; not a forecast.")
    f["M05.S3.E077.ncri_inputs"] = (
        "NCRI = (C_baseline - C_robot) / C_baseline = 1 - kappa with kappa = annual running cost of the UAV fleet (k u) over the annual "
        f"value of reclaimed guard hours (R) (course Standards Manual section 3, target kappa <= {p0['kappa_target']:g}). Same SOURCES table as above.")
    f["M05.S3.E077.ncri_metric"] = per(
        lambda s, c, r: f"{name(s, c)} " + na_or(
            r, lambda r: f"kappa {r['kappa']:.3f} (target <= {p0['kappa_target']:g}: "
                         f"{'met' if r['kappa'] <= p0['kappa_target'] else 'not met'}), NCRI {1 - r['kappa']:.3f} "
                         f"(envelope {1 - r['kappa_env'][1]:.3f} to {1 - r['kappa_env'][0]:.3f})")
        if r["gate"] else f"{name(s, c)} kappa {econ.NA}, NCRI {econ.NA}")
    f["M05.S3.E077.queue_inputs"] = (
        f"M/M/c with c = {int(p0['n_uav'])} UAVs; lambda = incidents_per_month / (365/12 x 24) per hour (incidents_per_month {rng('incidents_per_month')}, "
        "ASSUMPTION; low/base/high shown); mu = 1 / (mean simulated detection_latency_s + verify_time_s of detected runs). Guard comparison: "
        f"mu from guard_response_min {g_min_lo:g} to {g_min_hi:g} min (ASSUMPTION midpoint), c = {int(p0['guard_responders'])} responders "
        f"(ASSUMPTION {c_lo:g} to {c_hi:g}). rho = lambda / (c mu) < 1; "
        "W_q = C(c, lambda/mu) / (c mu - lambda) (Erlang C).")
    f["M05.S3.E077.queue_metric"] = (
        "UAV, base lambda: " + per(lambda s, c, r: f"{name(s, c)} rho = {r['queue']['base'][0]:.5f}, W_q = {r['queue']['base'][2]:.2e} s")
        + f"; guard (base lambda, ASSUMPTION mu and c) rho = {ri['guard'][2]['base'][0]:.5f}, W_q = {ri['guard'][2]['base'][2]:.2e} s. "
        "At campus incident rates rho is tiny, so waiting is about zero for every system: the queue shows utilisation headroom, not a delay problem.")
    f["M05.S3.E077.sensitivity_inputs"] = (
        f"Most uncertain input = the ASSUMPTION input of P_payback and kappa with the widest relative range (hi - lo) / midpoint, computed by "
        f"the script: {key} ({lo:g} to {hi:g}, relative range {rel[key]:.3f}). Swept -{econ.SWEEP:.0%} to +{econ.SWEEP:.0%} of its base value {p0[key]:g}; "
        "P_payback and NCRI plotted; bisection for the break-even P_payback = 1 inside the assumed range and inside the sweep.")
    f["M05.S3.E077.sensitivity_metric"] = (
        "; ".join(be(s, c, res[(s, c)]) for s, c in cells)
        + ". Figures: analytics/figures/campus_security_sensitivity.png and campus_security_queue.png.")
    f["M05.S3.E077.queue_model"] = "M/M/c"
    f["M05.S3.E077.queue_params"] = (
        f"lambda = {ri['lam']['low']:.5f} / {ri['lam']['base']:.5f} / {ri['lam']['high']:.5f} per h (low / base / high, from {inc_lo:g} / {inc_mid:g} / {inc_hi:g} "
        "incidents per month, ASSUMPTION); UAV mu = "
        + ", ".join(f"{res[(s, c)]['mu']:.3f} per h ({name(s, c)})" for s, c in cells)
        + f"; guard mu = {ri['guard'][0]:.3f} per h ({p0['guard_response_min']:g} min, ASSUMPTION midpoint); UAV c = {int(p0['n_uav'])}, guard c = {int(p0['guard_responders'])}.")
    f["M05.S3.E077.payback_months"] = per(lambda s, c, r: f"{name(s, c)} " + na_or(r, lambda r: f"{econ.fmt(r['T'], 1)} months"))
    f["M05.S3.E077.reproducible"] = "Yes"
    # ---- 3.2 FMEA (interior value in the dropdown, exterior in the text); O and D from the ablation CSV
    def ablation_row(n, key, dropdown=True):
        i, e = fm_text("interior", key), fm_text("exterior", key)
        def pair(tag):
            return "; ".join(f"{sc} {x[tag]}" for sc, x in (("interior", i), ("exterior", e)) if x["rpn_" + tag] is not None) \
                or "not measured"
        if i["O_before"] is not None:
            f[f"M05.S3.fmea{n}.occurrence"] = str(i["O_before"])
            f[f"M05.S3.fmea{n}.detection"] = str(i["D_before"])
        rpn = lambda tag: "; ".join(f"{x['rpn_' + tag]} {sc}" for sc, x in (("interior", i), ("exterior", e))  # noqa: E731
                                    if x["rpn_" + tag] is not None) or "not measured"
        f[f"M05.S3.fmea{n}.rpn_pre"] = rpn("before") + " (mitigation off arm)"
        f[f"M05.S3.fmea{n}.rpn_post"] = rpn("after") + " (production arm)"
        f[f"M05.S3.fmea{n}.mitigation"] = (
            f"[{i['state']}] {i['mitigation']}. Ablation, mitigation off -> on: {pair('before')} -> {pair('after')}. "
            f"O and D from measured rates, scale in analytics/campus_security_fmea.py (ASSUMPTION). Evidence: {i['evidence']}.")
        if i["O_before"] is not None and dropdown:
            f[f"M05.S3.fmea{n}.evidence"] = "Both"

    ablation_row(1, "uav_uav_conflict")
    ablation_row(2, "missed_intruder_twilight")
    ablation_row(3, "false_geofence_alarm")
    a, b = fm_text("interior", "intruder_not_detected"), fm_text("exterior", "intruder_not_detected")
    f["M05.S3.fmea4.occurrence"] = str(a["O_before"])
    f["M05.S3.fmea4.rpn_pre"] = f"{a['rpn_before']} interior; {b['rpn_before']} exterior (guard_baseline, CSV column detected)"
    f["M05.S3.fmea4.mitigation"] = (
        f"[implemented (E043 with E051 detector)] UAV patrol with camera detection replaces guard rounds. "
        f"After: interior {a['after']}; exterior {b['after']}. D is team judgement here (no ablation arm).")
    f["M05.S3.fmea4.rpn_post"] = f"{a['rpn_after']} interior; {b['rpn_after']} exterior"
    ablation_row(5, "unseen_obstacle")
    contacts = sum(1 for r in rows if r["condition"] != "guard_baseline" and int(float(r["uav_uav_contacts"])) > 0)
    n_uav_runs = sum(1 for r in rows if r["condition"] != "guard_baseline")
    f["M05.S3.fmea1.mitigation"] += (f" Main batch: {close_text[0].upper() + close_text[1:]}; "
                                     f"UAV-UAV contacts {contacts} of {n_uav_runs} UAV runs.")
    # ---- 4 provenance (tick only what is true now)
    f["M05.S4.prov_economics_sourced"] = "Yes"
    # ---- 6 contribution
    f["M05.S6.E077.scripts_authored"] = (
        "analytics/campus_security_economics.py, campus_security_fmea.py, campus_security_dossier_fill.py; tests/test_e077_*.py ({n_scripts} files); "
        "integrations/guardian_runtime/ and integrations/multi_uav_jev/ (optional runtime, not used for Sections 3-4); demo/*guardian*. "
        "AI-assisted (Claude); run, tested and reviewed by E077.")
    counts = git("shortlog", "-sne", "HEAD", "--", ".")
    mine = sum(int(line.split()[0]) for line in counts.splitlines() if "Subhankar" in line)
    total = sum(int(line.split()[0]) for line in counts.splitlines())
    f["M05.S6.E077.commit_share"] = (
        f"{mine} of {total} commits touching the group folder on integration/e043-e077-guardian at {git('rev-parse', '--short', 'HEAD')} "
        "(git shortlog -sn HEAD -- <folder>), including the merge commit")
    return f


def set_text(sdt, value):
    content = sdt.find("w:sdtContent", NS)
    texts = content.findall(".//w:t", NS)
    if not texts:
        raise ValueError("content control without text")
    texts[0].text = value
    texts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in texts[1:]:
        run = t.getparent()
        run.getparent().remove(run)


def main():
    econ.verify_csv_sha256(econ.CSV_PATH, econ.PROV_PATH)
    abl = fmea.load_ablation()       # verifies its own hash; exits if the ablation batch has not been run
    check_figures_fresh(econ.CSV_PATH, [os.path.join(econ.FIG_DIR, png) for png in FIGURES.values()])
    rows, metrics = econ.load_metrics()
    p0, res = econ.analyse(metrics)
    fm = fmea.fmea_table(rows, abl)
    values = fields(p0, res, fm, rows)
    zin = zipfile.ZipFile(SRC)
    doc = etree.fromstring(zin.read("word/document.xml"))
    sdts = {s.find("w:sdtPr/w:tag", NS).get(f"{{{W}}}val"): s for s in doc.iter(f"{{{W}}}sdt")}
    before = len(sdts)
    for tag, value in values.items():
        sdt = sdts[tag]
        options = [li.get(f"{{{W}}}displayText") for li in sdt.iter(f"{{{W}}}listItem")]
        if options and value not in options:
            raise ValueError(f"{tag}: {value!r} is not one of {options}")
        set_text(sdt, value)
    for old, new in CAPTIONS.items():
        hits = [t for t in doc.iter(f"{{{W}}}t") if t.text and t.text.startswith(old)]
        if len(hits) != 1:
            raise ValueError(f"caption not found once: {old}")
        hits[0].text = new
    rels = etree.fromstring(zin.read("word/_rels/document.xml.rels"))
    targets = {r.get("Id"): r.get("Target") for r in rels}
    media = {}
    for rid, png in FIGURES.items():
        blip = doc.find(f".//a:blip[@r:embed='{rid}']", NS)
        anchor = next(a for a in blip.iterancestors() if a.tag in (f"{{{NS['wp']}}}inline", f"{{{NS['wp']}}}anchor"))
        data = open(os.path.join(econ.FIG_DIR, png), "rb").read()
        w_px, h_px = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        extent = anchor.find("wp:extent", NS)
        cx = int(extent.get("cx"))
        cy = round(cx * h_px / w_px)
        extent.set("cy", str(cy))
        for ext in anchor.iterfind(".//a:ext", NS):
            if ext.get("cx") == str(cx):
                ext.set("cy", str(cy))
        media["word/" + targets[rid]] = data
    after = len(list(doc.iter(f"{{{W}}}sdt")))
    if after != before:
        raise SystemExit(f"content control count changed: {before} -> {after}")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "word/document.xml":
                data = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
            else:
                data = media.get(item.filename, zin.read(item.filename))
            zout.writestr(item, data)
    with open(DST, "wb") as out:
        out.write(buf.getvalue())
    print(f"wrote {os.path.relpath(DST, G)}: {len(values)} fields set, "
          f"{len(FIGURES)} figures replaced, {after} content controls (unchanged)")


if __name__ == "__main__":
    main()
