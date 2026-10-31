"""E077 economics: formulas, determinism and the no-currency rule."""
import contextlib
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
from pathlib import Path

import pytest

GROUP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GROUP / "analytics"))
import campus_security_economics as econ  # noqa: E402
import campus_security_fmea as fmea  # noqa: E402

P0 = econ.base_case()
TMP_ROOT = None


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_provenance(csv_path, extra=None):
    """A provenance JSON built in tmp for a CSV (never the committed one)."""
    prov = Path(str(csv_path)[:-4] + ".provenance.json")
    prov.write_text(json.dumps(dict({"csv_sha256": sha(csv_path)}, **(extra or {}))))
    return prov


def synthetic_ablation(dirpath):
    """Tiny synthetic ablation CSV, only ever in tmp_path: 4 modes x 2 arms x 10 seeds with hand-countable rates."""
    rows = []
    for seed in range(1, 11):
        # separation: off = APF only, 6/10 runs closer than 2.5 m, 2 of those with a contact; on = never closer
        close = seed <= 6
        rows.append(dict(mode="separation", arm="off", seed=seed, min_inter_uav_m=2.0 if close else 3.5,
                         uav_uav_contacts=1 if seed <= 2 else 0))
        rows.append(dict(mode="separation", arm="on", seed=seed, min_inter_uav_m=3.2, uav_uav_contacts=0))
        # obstacle avoidance: off = 5/10 contacts, on = 0 contacts and clearance above the near-miss distance
        rows.append(dict(mode="fr18", arm="off", seed=seed, obstacle_contacts=1 if seed <= 5 else 0,
                         min_obstacle_clearance_m=0.0 if seed <= 5 else 0.8))
        rows.append(dict(mode="fr18", arm="on", seed=seed, obstacle_contacts=0, min_obstacle_clearance_m=0.9))
        # geofence: off = 4 runs with >= 1 spurious breach event (3 of them with >= 2), on = none
        rows.append(dict(mode="geofence", arm="off", seed=seed,
                         geofence_spurious_breaches=3 if seed <= 3 else (1 if seed == 4 else 0)))
        rows.append(dict(mode="geofence", arm="on", seed=seed, geofence_spurious_breaches=0))
        # twilight: off = 4/10 detected (2 of them later than 60 s), on = 10/10 detected, all quick
        rows.append(dict(mode="twilight", arm="off", seed=seed, detected=1 if seed <= 4 else 0,
                         detection_latency_s=(100.0 if seed <= 2 else 20.0) if seed <= 4 else ""))
        rows.append(dict(mode="twilight", arm="on", seed=seed, detected=1, detection_latency_s=15.0))
    cols = ["run_id", "mode", "arm", "seed", "min_inter_uav_m", "uav_uav_contacts", "obstacle_contacts",
            "min_obstacle_clearance_m", "geofence_spurious_breaches", "detected", "detection_latency_s"]
    path = Path(dirpath) / "ablation_trials.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        for r in rows:
            w.writerow(dict(run_id=f"{r['mode']}_{r['arm']}_s{r['seed']}", **{k: v for k, v in r.items()}))
    return path, write_provenance(path)


@pytest.fixture(scope="module")
def ablation(tmp_path_factory):
    return synthetic_ablation(tmp_path_factory.mktemp("abl"))


def abl_args(ablation):
    return ["--ablation", str(ablation[0]), "--ablation-provenance", str(ablation[1])]


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        econ.main(argv)
    return out.getvalue()


@pytest.fixture(scope="module")
def output(tmp_path_factory, ablation):
    return run(abl_args(ablation) + ["--fig-dir", str(tmp_path_factory.mktemp("fig"))])


def forced_metrics(fail_cell=None):
    """Real metrics, every UAV cell forced to pass the revisit gate except fail_cell (forced to fail)."""
    _, metrics = econ.load_metrics()
    for scene in econ.SCENES:
        g = metrics[(scene, "guard_baseline")]["worst_s"]
        for cond in econ.UAV_CONDITIONS:
            cell = (scene, cond)
            w = metrics[cell]["window_s"]
            vals = [w if cell == fail_cell else w - 1.0]       # a UAV run at the window is censored -> gate FAIL
            metrics[cell] = dict(metrics[cell], worst_s=g + (1.0 if cell == fail_cell else -1.0),
                                 worst_values=vals, worst_max_s=max(vals))
    return metrics


def test_csv_is_the_recorded_real_trials_file():
    """The expected hash is read from the provenance JSON; no script carries a constant."""
    assert not hasattr(econ, "CSV_SHA256")
    assert econ.verify_csv_sha256(econ.CSV_PATH, econ.PROV_PATH) == sha(econ.CSV_PATH)
    for name in ("campus_security_economics.py", "campus_security_fmea.py", "campus_security_dossier_fill.py"):
        text = (GROUP / "analytics" / name).read_text()
        assert not re.search(r"[\"'][0-9a-f]{64}[\"']", text), name


def test_provenance_hash_check_fails_loudly(tmp_path):
    csv_path = tmp_path / "t.csv"
    csv_path.write_text("a,b\n1,2\n")
    with pytest.raises(SystemExit, match="missing provenance"):
        econ.verify_csv_sha256(csv_path, tmp_path / "t.provenance.json")
    prov = tmp_path / "t.provenance.json"
    prov.write_text(json.dumps({"generator": "x"}))
    with pytest.raises(SystemExit, match="no 'csv_sha256' key"):
        econ.verify_csv_sha256(csv_path, prov)
    write_provenance(csv_path)
    assert econ.verify_csv_sha256(csv_path, prov) == sha(csv_path)
    csv_path.write_text("a,b\n1,3\n")       # edited after the provenance was written
    with pytest.raises(SystemExit, match="changed"):
        econ.verify_csv_sha256(csv_path, prov)


def test_main_reads_hash_from_a_provenance_built_in_tmp(tmp_path, ablation):
    csv_copy = tmp_path / "real.csv"
    csv_copy.write_bytes(Path(econ.CSV_PATH).read_bytes())
    prov = write_provenance(csv_copy)
    out = run(["--no-figures", "--csv", str(csv_copy), "--provenance", str(prov)] + abl_args(ablation))
    assert f"sha256 {sha(csv_copy)} (matches provenance csv_sha256)" in out
    with open(csv_copy, "ab") as f:
        f.write(b"\n")
    with pytest.raises(SystemExit, match="changed"):
        run(["--no-figures", "--csv", str(csv_copy), "--provenance", str(prov)] + abl_args(ablation))


def test_every_input_is_sourced_or_a_labelled_assumption_range():
    for name, (value, unit, kind, cite) in econ.SOURCES.items():
        assert kind in ("sourced", "ASSUMPTION") and unit and cite, name
        assert econ.is_range(value) == (kind == "ASSUMPTION"), name
        if econ.is_range(value):
            assert value[0] < value[1], name


def test_base_case_is_the_midpoint_and_capex_ratio_is_most_uncertain():
    assert P0["capex_ratio"] == pytest.approx(0.65)
    assert P0["rounds_per_shift"] == 6 and P0["hours_per_shift"] == 8
    assert econ.most_uncertain()[0] == "capex_ratio"


def test_h_patrol_and_reclaimed_hours_by_hand():
    # 3 shifts x 6 rounds x 1.5 guards x 1 h cycle = 27 guard-h/day
    assert econ.h_patrol(P0, 3600.) == pytest.approx(27.)
    metrics = forced_metrics()
    _, res = econ.analyse(metrics)
    t_guard = metrics[("interior", "guard_baseline")]["cycle_s"]
    r = res[("interior", "uav_sectors")]
    assert r["gate"] and r["H"] == pytest.approx(0.75 * 27 * t_guard / 3600)
    assert r["fte"] == pytest.approx(r["H"] * 365 / 2080)


def test_kappa_payback_and_months_are_consistent():
    t = 60.
    u = econ.running_fraction(P0, t)
    k, R, life = P0["capex_ratio"], P0["replacement_fraction"], P0["service_life_years"]
    assert econ.kappa(P0, t) == pytest.approx(k * u / R)
    assert econ.p_payback(P0, t) == pytest.approx(k / (life * (R - k * u)))
    assert econ.t_payback_months(P0, t) == pytest.approx(12 * k / (R - k * u))
    # P_payback x T_life x 12 = T_payback in months
    assert econ.p_payback(P0, t) * life * 12 == pytest.approx(econ.t_payback_months(P0, t))
    never = dict(P0, capex_ratio=100.)
    assert math.isinf(econ.p_payback(never, t)) and math.isinf(econ.t_payback_months(never, t))


def test_battery_term_counts_charges_from_the_uav_cycle():
    # 3 shifts x 6 rounds x 0.75 replaced x 0.02 h x 365 days = 98.55 flight h; / 22.5 min per charge
    assert econ.cycles_per_uav_year(P0, 72.) == pytest.approx(98.55 * 60 / 22.5)


def test_erlang_c_known_values():
    assert econ.erlang_c(1, .5) == pytest.approx(.5)          # M/M/1: P_wait = rho
    assert econ.erlang_c(2, 1.) == pytest.approx(1 / 3)
    rho, pw, wq = econ.mmc(1., 2., 1)                          # M/M/1: W_q = rho / (mu - lambda)
    assert rho == pytest.approx(.5) and wq == pytest.approx(.5 / (2 - 1) * 3600)
    assert math.isinf(econ.mmc(5., 1., 2)[2])


def test_bisection_finds_a_root_and_reports_none_without_sign_change():
    assert econ.bisect(lambda x: x * x - 2, 0, 2) == pytest.approx(math.sqrt(2), abs=1e-8)
    assert econ.bisect(lambda x: x + 1, 0, 2) is None


def test_corner_envelope_has_two_to_the_assumption_count():
    assert len(list(econ.corners(P0))) == 2 ** 9


def test_fmea_occurrence_scale_and_interval():
    assert fmea.occurrence(0, 60) == 1
    assert fmea.occurrence(1, 60) == 3
    assert fmea.occurrence(39, 60) == 9
    assert fmea.occurrence(60, 60) == 10
    lo, hi = fmea.clopper_pearson(0, 60)
    assert lo == 0 and hi == pytest.approx(1 - 0.025 ** (1 / 60))


def test_fmea_detection_bands_and_occurrence_table():
    assert fmea.detection(0, 10) == 1 and fmea.detection(0, 0) == 1 and fmea.detection(0, 0, empty=10) == 10
    assert [fmea.detection(k, 100) for k in (1, 5, 10, 20, 35, 50, 70, 90, 91)] == [2, 3, 4, 5, 6, 7, 8, 9, 10]
    table = fmea.occurrence_table()
    assert [t[0] for t in table] == list(range(1, 11))
    for o, lo, hi in table[1:]:           # every band edge maps back to its own score
        assert fmea.occurrence(round(lo * 10_000), 10_000) in (o, o - 1 if o > 1 else 1)
    assert "Occurrence O" in "\n".join(fmea.mapping_text())


def test_fmea_before_after_from_ablation_rates(ablation):
    rows = econ.load_metrics()[0]
    table = fmea.fmea_table(rows, fmea.load_ablation(*ablation))
    sep = table[("interior", "uav_uav_conflict")]
    # off: 6/10 closer than 2.5 m -> p = 0.6 -> O = round(10 + 4 log10 0.6) = 9; 2 of those 6 contacts -> p_D = 1/3 -> D = 6
    assert (sep["O_before"], sep["D_before"], sep["rpn_before"]) == (9, 6, 9 * 9 * 6)
    # on: nothing closer than 2.5 m -> O = 1, D = 1
    assert (sep["O_after"], sep["D_after"], sep["rpn_after"]) == (1, 1, 9)
    obs = table[("interior", "unseen_obstacle")]
    # off: 5/10 contacts -> O = round(10 + 4 log10 0.5) = 9; hazard = 5, escapes = 5 -> p_D = 1 -> D = 10
    assert (obs["O_before"], obs["D_before"]) == (9, 10) and (obs["O_after"], obs["D_after"]) == (1, 1)
    geo = table[("exterior", "false_geofence_alarm")]
    # off: 4/10 runs with a spurious breach event -> O = 8; 3 of 4 repeated -> p_D = 0.75 -> D = 9
    assert (geo["O_before"], geo["D_before"]) == (8, 9) and (geo["O_after"], geo["D_after"]) == (1, 1)
    twi = table[("interior", "missed_intruder_twilight")]
    # off: 6/10 missed -> O = 9; detected = 4, late = 2 -> p_D = 0.5 -> D = 7; on: 0 missed, 0 late
    assert (twi["O_before"], twi["D_before"]) == (9, 7) and (twi["O_after"], twi["D_after"]) == (1, 1)
    assert twi["fisher_p"] < 0.05
    low = table[("interior", "intruder_not_detected")]
    assert low["Db"] == 6 and "team judgement" in low["before"]
    text = io.StringIO()
    with contextlib.redirect_stdout(text):
        fmea.print_fmea(rows, fmea.load_ablation(*ablation))
    assert "pending" not in text.getvalue().lower()


def test_fmea_scene_column_filters_and_missing_scene_is_not_measured(tmp_path):
    path = tmp_path / "ablation_trials.csv"
    path.write_text("run_id,mode,arm,seed,scene,obstacle_contacts,min_obstacle_clearance_m\n"
                    + "".join(f"o{a}{i},fr18,{a},{i},interior,{int(a == 'off' and i < 3)},0.7\n"
                              for a in ("off", "on") for i in range(10)))
    write_provenance(path)
    table = fmea.fmea_table(econ.load_metrics()[0], fmea.load_ablation(path, path.with_suffix(".provenance.json")))
    assert table[("interior", "unseen_obstacle")]["O_before"] == occ(3, 10)
    ext = table[("exterior", "unseen_obstacle")]
    assert ext["rpn_before"] is None and ext["before"].startswith("not measured")


def occ(k, n):
    return fmea.occurrence(k, n)


def test_fmea_requires_the_ablation_csv_and_never_prints_pending(tmp_path):
    with pytest.raises(SystemExit, match="ablation batch"):
        fmea.load_ablation(tmp_path / "absent.csv", tmp_path / "absent.provenance.json")
    path = tmp_path / "ablation_trials.csv"
    path.write_text("run_id,mode,arm,seed\nx,separation,off,1\n")
    with pytest.raises(SystemExit, match="missing provenance"):
        fmea.load_ablation(path, tmp_path / "nope.json")
    write_provenance(path)
    with pytest.raises(SystemExit, match="needs column"):
        fmea.load_ablation(path, path.with_suffix(".provenance.json"))
    with pytest.raises(SystemExit, match="ablation batch"):
        run(["--no-figures", "--ablation", str(tmp_path / "absent.csv")])
    src = (GROUP / "analytics" / "campus_security_fmea.py").read_text() + \
          (GROUP / "analytics" / "campus_security_dossier_fill.py").read_text()
    assert not re.search(r"pending E0(51|75|77) merge|PENDING_", src)


def test_t_based_confidence_interval():
    from scipy.stats import t as student_t
    vals = [10., 12., 11., 15., 9.]
    m, lo, hi = econ.t_ci(vals)
    h = student_t.ppf(0.975, 4) * (sum((v - 11.4) ** 2 for v in vals) / 4) ** 0.5 / 5 ** 0.5
    assert m == pytest.approx(11.4) and hi - m == pytest.approx(h) and m - lo == pytest.approx(h)
    assert h > 1.96 * (sum((v - 11.4) ** 2 for v in vals) / 4) ** 0.5 / 5 ** 0.5      # wider than the z interval
    assert math.isnan(econ.t_ci([3.])[1])


def test_equal_window_revisit_is_the_gate_metric_when_present(tmp_path):
    rows = econ.load_metrics()[0]
    cols = list(rows[0]) + [econ.EQWIN_COL]
    path = tmp_path / "t.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, **{econ.EQWIN_COL: "123.5" if r["scene"] == "interior" else ""}))
    _, metrics = econ.load_metrics(path)
    assert metrics[("interior", "uav_sectors")]["basis"] == econ.EQWIN_COL
    assert metrics[("interior", "uav_sectors")]["worst_s"] == pytest.approx(123.5)
    assert metrics[("exterior", "uav_sectors")]["basis"] == "worst_revisit_ground_s"


def test_breakeven_crossing_tornado_and_stress_cases():
    p0, res = econ.analyse(forced_metrics())
    r = res[("interior", "uav_sectors")]
    key = r["key"]
    assert r["crossing"] is not None
    assert econ.p_payback(dict(p0, **{key: r["crossing"]}), r["t_uav"]) == pytest.approx(1.0, abs=1e-6)
    assert r["cross_dist"] == pytest.approx(r["crossing"] - p0[key])
    # tornado: every ASSUMPTION input of P_payback, widest swing first, endpoints equal the model at +/-30 %
    names = [k for k, _, _ in r["tornado"]]
    assert sorted(names) == sorted(k for k in econ.COST_INPUTS if econ.SOURCES[k][2] == "ASSUMPTION")
    swings = [abs(b - a) for _, a, b in r["tornado"]]
    assert swings == sorted(swings, reverse=True)
    k0, lo_p, hi_p = r["tornado"][0]
    assert lo_p == pytest.approx(econ.p_payback(dict(p0, **{k0: p0[k0] * 0.7}), r["t_uav"]))
    # stress cases: lambda = rho c mu, W_q from Erlang C, c = 1 is M/M/1
    rows1 = econ.stress_rows(10., 1)
    assert [x[0] for x in rows1] == list(econ.STRESS_RHOS)
    rho, lam, lam_m, pw, wq = rows1[1]
    assert lam == pytest.approx(8.) and pw == pytest.approx(0.8) and wq == pytest.approx(0.8 / (10 - 8) * 3600)
    assert econ.stress_rows(10., 2)[0][1] == pytest.approx(10.)       # rho 0.5, c 2, mu 10 -> lambda 10
    assert all(wq > 1 for *_, wq in econ.stress_rows(r["mu"], 1)[1:])  # non-trivial regime
    qt = econ.tornado_queue(p0, 36.)
    assert {lab for lab, _, _ in qt} >= {"human_confirm_s (UAV)", "guard_response_min (guard)"}


FIGURE_NAMES = ("campus_security_sensitivity.png", "campus_security_queue.png",
                "campus_security_breakeven.png", "campus_security_tornado.png")


def test_output_and_figures_are_deterministic(tmp_path, ablation):
    assert run(abl_args(ablation) + ["--no-figures"]) == run(abl_args(ablation) + ["--no-figures"])
    a, b = tmp_path / "a", tmp_path / "b"
    run(abl_args(ablation) + ["--fig-dir", str(a)])
    run(abl_args(ablation) + ["--fig-dir", str(b)])
    for name in FIGURE_NAMES:
        assert (a / name).stat().st_size > 10_000
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
        with open(a / name, "rb") as f:
            head = f.read(33)
        assert head[:8] == b"\x89PNG\r\n\x1a\n"
        dpi_chunk = (a / name).read_bytes().split(b"pHYs")[1][:9]
        assert int.from_bytes(dpi_chunk[:4], "big") == pytest.approx(300 / 0.0254, abs=2), name   # 300 DPI


def test_no_currency_in_output(output):
    assert not re.search(r"[\x24\u20b9\u20ac\u00a3\u00a5]|\b(rupee[s]?|rs\.?|inr|usd|dollar[s]?|euros?|lakhs?|crores?)\b",
                         output, re.I)
    assert "SOURCES" in output and output.count("SCENE:") == 2 and output.count("FMEA, scene =") == 2


def _failed_gate_results():
    """Real metrics with one cell forced to fail the revisit gate (UAV worst revisit above the guard's)."""
    return econ.analyse(forced_metrics(("interior", "uav_sectors")))


def test_gate_fail_reports_kappa_ncri_and_payback_as_na():
    p0, res = _failed_gate_results()
    bad, good = res[("interior", "uav_sectors")], res[("interior", "uav_offset_ring")]
    assert not bad["gate"] and bad["H"] == 0 and bad["fte"] == 0
    for k in ("kappa", "kappa_env", "P", "P_env", "T", "sweep_P", "sweep_NCRI", "be", "be_sweep", "k_target"):
        assert bad[k] is None, k
    assert good["gate"] and good["kappa"] is not None and good["P"] is not None
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        econ.print_results(p0, res)
    block = out.getvalue().split("uav_sectors cycle_time_s", 1)[1].split("uav_offset_ring cycle_time_s", 1)[0]
    assert "): FAIL" in block and "gate (" in block
    for label in ("kappa", "NCRI = 1 - kappa", "P_payback", "T_payback"):
        assert f"{label} {econ.NA}" in block, label
    assert "envelope" not in block.split("FAIL", 1)[1].split("M/M/c", 1)[0]


def test_gate_fail_figures_are_annotated_not_plotted(tmp_path):
    p0, res = _failed_gate_results()
    paths = econ.save_figures(p0, res, str(tmp_path))
    assert len(paths) == 4 and all(Path(x).stat().st_size > 10_000 for x in paths)


@pytest.fixture(scope="module")
def fill():
    pytest.importorskip("lxml")
    import campus_security_dossier_fill as mod
    return mod


def dossier_fields(fill, ablation, fail_cell=None, rows=None):
    real_rows = econ.load_metrics()[0] if rows is None else rows
    p0, res = econ.analyse(forced_metrics(fail_cell))
    return fill.fields(p0, res, fmea.fmea_table(real_rows, fmea.load_ablation(*ablation)), real_rows)


def test_dossier_gate_claim_is_computed_from_the_data(fill, ablation):
    f = dossier_fields(fill, ablation)
    assert "gate PASS in all 4 cells" in f["M05.S3.E077.hreclaimed_inputs"]
    f = dossier_fields(fill, ablation, ("interior", "uav_sectors"))
    assert "gate PASS in 3 of 4 cells" in f["M05.S3.E077.hreclaimed_inputs"]
    for tag in ("ncri_metric", "payback_metric", "payback_months", "sensitivity_metric"):
        assert econ.NA in f["M05.S3.E077." + tag], tag
    assert "interior sectors kappa" not in f["M05.S3.E077.ncri_metric"].replace(f"kappa {econ.NA}", "")


def test_dossier_close_run_claim_is_computed_from_the_data(fill):
    rows = [dict(r) for r in econ.load_metrics()[0]]
    for r in rows:
        if r["condition"] != "guard_baseline":
            r["min_inter_uav_m"] = "3.5"
    assert fill.close_claim(rows).startswith("no UAV run closer than 2.5 m")
    ring = [r for r in rows if r["condition"] == "uav_offset_ring"]
    for r in ring[:3]:
        r["min_inter_uav_m"] = "1.9"
    n_uav = sum(1 for r in rows if r["condition"] != "guard_baseline")
    assert fill.close_claim(rows) == f"all 3 of {n_uav} UAV runs closer than 2.5 m were uav_offset_ring runs"
    next(r for r in rows if r["condition"] == "uav_sectors")["min_inter_uav_m"] = "2.0"
    text = fill.close_claim(rows)
    assert "uav_offset_ring (3)" in text and "uav_sectors (1)" in text and not text.startswith("all")


def test_dossier_fmea_fields_come_from_ablation_not_pending(fill, ablation):
    f = dossier_fields(fill, ablation)
    assert f["M05.S3.fmea2.occurrence"] == "9" and f["M05.S3.fmea2.detection"] == "7"
    assert f["M05.S3.fmea3.occurrence"] == "8" and f["M05.S3.fmea1.occurrence"] == "9"
    for tag, val in f.items():
        assert "pending" not in val.lower(), tag
    assert "Ablation, mitigation off -> on" in f["M05.S3.fmea2.mitigation"]


def test_dossier_refuses_figures_older_than_the_csv(fill, tmp_path):
    csv_path = tmp_path / "t.csv"
    csv_path.write_text("a\n1\n")
    png = tmp_path / "campus_security_x.png"
    png.write_bytes(b"png")
    now = os.path.getmtime(csv_path)
    os.utime(png, (now + 10, now + 10))
    fill.check_figures_fresh(csv_path, [png])                        # newer: fine
    os.utime(png, (now - 10, now - 10))
    with pytest.raises(SystemExit, match="stale figure"):
        fill.check_figures_fresh(csv_path, [png])
    with pytest.raises(SystemExit, match="missing figure"):
        fill.check_figures_fresh(csv_path, [tmp_path / "absent.png"])


def test_dossier_main_refuses_a_csv_that_does_not_match_its_provenance(fill, tmp_path, monkeypatch):
    bad = tmp_path / "t.csv"
    bad.write_text("a\n1\n")
    prov = write_provenance(bad)
    bad.write_text("a\n2\n")
    monkeypatch.setattr(fill.econ, "CSV_PATH", str(bad))
    monkeypatch.setattr(fill.econ, "PROV_PATH", str(prov))
    with pytest.raises(SystemExit, match="changed"):
        fill.main()


def test_gate_is_every_uav_run_below_the_equal_window_and_prints_reasoning(output):
    import censored_revisit as cr
    assert "right-censored" in output and cr.GATE_REASONING in output
    assert "gate (every UAV worst revisit < 300 s; max" in output
    rows, metrics = econ.load_metrics()
    for scene in econ.SCENES:
        u = metrics[(scene, "uav_sectors")]
        assert u["window_s"] == 300.0 and u["worst_max_s"] == max(u["worst_values"])


def _gate_with(max_run, scene="interior", cond="uav_sectors"):
    _, metrics = econ.load_metrics()
    cell = metrics[(scene, cond)]
    vals = list(cell["worst_values"])
    vals[0] = max_run
    metrics[(scene, cond)] = dict(cell, worst_values=vals, worst_max_s=max(vals))
    _, res = econ.analyse(metrics)
    return res[(scene, cond)]["gate"]


def test_gate_edge_cases_uav_run_at_the_window_fails():
    assert _gate_with(299.0) is True
    assert _gate_with(300.0) is False
    assert _gate_with(301.0) is False
