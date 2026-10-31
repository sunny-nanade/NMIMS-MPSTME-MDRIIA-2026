"""
Tests for E075 (geofence tiers, hysteresis, noise, breach log, link loss) and
analytics/statistical_validation.py | owner E075 Zaid Rezaur Rahman

  python -m pytest tests/test_e075_geofence_stats.py -q

The statistics tests use a FIXTURE CSV built in tmp_path from a seeded generator. The
fixture exists only to check the code against scipy; none of its numbers is a result.
"""
import csv
import json
import os
import sys

import numpy as np
import pytest
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "analytics"))
import aerial_patrol_swarm as aps          # noqa: E402
import statistical_validation as sv        # noqa: E402


def make_ctl(scene):
    return aps.DualUAVSurveillanceController(model_path=aps.SCENES[scene], vision=False,
                                             wind_mps=0.0, gust_sigma=0.0)


@pytest.fixture(scope="module")
def ctls():
    return {s: make_ctl(s) for s in ("interior", "exterior")}


def fresh(ctl, hysteresis=True):
    ctl.geofence_hysteresis = hysteresis
    ctl.reset_geofence_state()
    ctl.current_time_s = 0.0
    return ctl


# Known points. interior zone x -21.4..-14.0, y -3.8..15.4 (VIP Lounge);
# exterior zone x -30..-12, y 24.5..32.5 (substation). Distances are from the zone edge.
KNOWN = {
    "interior": [((-17.7, 5.8, 0.0), 3), ((-14.0, 5.8, 0.0), 3),   # centre, on the edge
                 ((-12.0, 5.8, 0.0), 2), ((-9.0, 5.8, 0.0), 2),   # 2 m and 5 m outside
                 ((-8.0, 5.8, 0.0), 1), ((-0.0, 5.8, 0.0), 1),    # 6 m and 14 m outside
                 ((10.0, 5.8, 0.0), 0)],                          # 24 m outside
    "exterior": [((-21.0, 28.5, 0.0), 3), ((-12.0, 28.5, 0.0), 3),
                 ((-21.0, 35.0, 0.0), 2), ((-10.0, 34.0, 0.0), 2),  # 2.5 m, corner 2.5 m
                 ((-21.0, 42.0, 0.0), 1), ((-21.0, 60.0, 0.0), 0)],
}


@pytest.mark.parametrize("scene", ["interior", "exterior"])
def test_tiers_on_known_points(ctls, scene):
    ctl = ctls[scene]
    for pos, tier in KNOWN[scene]:
        fresh(ctl, hysteresis=False)
        status, t = ctl.evaluate_geofence_status(pos)
        assert t == tier, (scene, pos)
        assert status == ctl.GEOFENCE_STATUS[tier]
        assert ctl.geofence_raw_tier(pos) == tier


@pytest.mark.parametrize("scene", ["interior", "exterior"])
def test_polygon_comes_from_scene_geom_and_none_is_clear(ctls, scene):
    import mujoco
    ctl = ctls[scene]
    gid = mujoco.mj_name2id(ctl.model, mujoco.mjtObj.mjOBJ_GEOM, "substation_zone")
    (cx, cy), (hx, hy) = ctl.model.geom_pos[gid][:2], ctl.model.geom_size[gid][:2]
    poly = ctl._geofence_polygon()
    assert min(p[0] for p in poly) == pytest.approx(cx - hx) and max(p[0] for p in poly) == pytest.approx(cx + hx)
    assert min(p[1] for p in poly) == pytest.approx(cy - hy) and max(p[1] for p in poly) == pytest.approx(cy + hy)
    assert fresh(ctl).evaluate_geofence_status(None) == ("STATUS_0_ROUTINE_CLEAR", 0)


def test_ray_casting_on_a_non_convex_polygon():
    L = [(0, 0), (4, 0), (4, 1), (1, 1), (1, 4), (0, 4)]          # L shape
    pip = aps.DualUAVSurveillanceController._point_in_polygon
    assert pip(0.5, 3.0, L) and pip(3.0, 0.5, L)
    assert not pip(3.0, 3.0, L) and not pip(-1.0, 0.5, L)


def test_hysteresis_does_not_flap_on_a_boundary_hugging_path(ctls):
    ctl = ctls["exterior"]
    # clean readings alternating either side of the 5 m buffer threshold (4.9 m / 5.1 m outside)
    pts = [(-21.0, 32.5 + (4.9 if i % 2 == 0 else 5.1), 0.0) for i in range(40)]
    def changes(hyst):
        fresh(ctl, hysteresis=hyst)
        tiers = [ctl.evaluate_geofence_status(p)[1] for p in pts]
        return sum(1 for a, b in zip(tiers, tiers[1:]) if a != b)
    assert changes(False) == 39               # off: flips on every reading
    assert changes(True) == 0                 # on: enters tier 2 once, stays (needs > 7 m to leave)


def test_exit_margin_leaves_the_tier_only_past_the_margin(ctls):
    ctl = fresh(ctls["exterior"])
    assert ctl.evaluate_geofence_status((-21.0, 37.0, 0.0))[1] == 2          # 4.5 m
    assert ctl.evaluate_geofence_status((-21.0, 39.0, 0.0))[1] == 2          # 6.5 m: raw 1, held
    assert ctl.evaluate_geofence_status((-21.0, 40.0, 0.0))[1] == 1          # 7.5 m: past 5 + 2


def test_tier3_dwell_rejects_a_single_inside_reading(ctls):
    ctl = fresh(ctls["exterior"])
    inside, outside = (-21.0, 28.5, 0.0), (-21.0, 36.0, 0.0)
    assert ctl.evaluate_geofence_status(inside)[1] == 2                       # one reading: not confirmed
    assert ctl.evaluate_geofence_status(outside)[1] == 2
    fresh(ctl)
    tiers = [ctl.evaluate_geofence_status(inside)[1] for _ in range(ctl.GEOFENCE_CONFIRM_N)]
    assert tiers == [2] * (ctl.GEOFENCE_CONFIRM_N - 1) + [3]


def test_hysteresis_cuts_false_breaches_under_noise(ctls):
    ctl = ctls["interior"]
    # walker 1.5 m outside the long edge of the lounge; the true tier is never 3
    pts = [(-21.4 - 1.5, y, 0.0) for y in np.linspace(-8.0, 20.0, 300)]
    def false_breaches(hyst):
        total = 0
        for seed in range(20):
            fresh(ctl, hysteresis=hyst)
            ctl.reseed_geofence_noise(seed)
            prev = 0
            for p in pts:
                tier = ctl.evaluate_geofence_status(ctl.inject_position_noise(p, 1.5))[1]
                total += int(tier == 3 and prev != 3)
                prev = tier
        return total
    off, on = false_breaches(False), false_breaches(True)
    assert off > 20 and on <= off // 10


def test_noise_off_and_on(ctls):
    ctl = ctls["exterior"]
    p = np.array([1.0, 2.0, 3.0])
    assert np.array_equal(ctl.inject_position_noise(p, 0.0), p)               # off: unchanged
    ctl.reseed_geofence_noise(7)
    a = np.array([ctl.inject_position_noise(p, 1.5) for _ in range(4000)])
    assert a.shape == (4000, 3) and np.all(a[:, 2] == 3.0)                    # z untouched
    assert a[:, 0].std() == pytest.approx(1.5, rel=0.08) and a[:, 1].std() == pytest.approx(1.5, rel=0.08)
    assert abs(a[:, 0].mean() - 1.0) < 0.15
    ctl.reseed_geofence_noise(7)
    b = ctl.inject_position_noise(p, 1.5)
    assert np.array_equal(a[0], b)                                            # seeded and reproducible


def test_noise_does_not_touch_the_gust_rng(ctls):
    ctl = ctls["interior"]
    before = ctl.rng.bit_generator.state
    ctl.reseed_geofence_noise(1)
    for _ in range(10):
        ctl.inject_position_noise((0.0, 0.0, 0.0), 1.5)
    assert ctl.rng.bit_generator.state == before


@pytest.mark.parametrize("scene", ["interior", "exterior"])
def test_breach_log_schema(ctls, scene, tmp_path):
    ctl = fresh(ctls[scene], hysteresis=False)
    ctl._geofence_last_noisy = None
    inside = KNOWN[scene][0][0]
    far = KNOWN[scene][-1][0]
    ctl.current_time_s = 1.0
    ctl.evaluate_geofence_status(far)                                          # clean, tier 0: no event
    ctl.current_time_s = 2.0
    ctl.evaluate_geofence_status(inside)                                       # clean entry
    ctl.current_time_s = 3.0
    noisy_far = ctl.inject_position_noise(far, 1.5)
    ctl.evaluate_geofence_status(noisy_far)                                    # noisy exit
    path = ctl.write_geofence_breach_log(str(tmp_path / f"geofence_breach_log_{scene}.json"))
    doc = json.load(open(path))
    assert doc["scene"] == scene
    ev = doc["events"]
    assert [e["tier"] for e in ev] == [3, 0] and [e["event"] for e in ev] == ["escalate", "de-escalate"]
    for e in ev:
        assert set(e) == {"timestamp_s", "scene", "position", "tier", "status", "event", "noisy"}
        assert e["scene"] == scene and len(e["position"]) == 3 and e["status"] == ctl.GEOFENCE_STATUS[e["tier"]]
    assert [e["noisy"] for e in ev] == [False, True] and [e["timestamp_s"] for e in ev] == [2.0, 3.0]


def test_return_to_home_after_2_5_s_of_loss(ctls):
    ctl = ctls["interior"]
    ctl.telemetry_loss_windows = [(1.0, 20.0)]
    ctl._link_down_since = None
    try:
        assert ctl.telemetry_link_ok(0.5) and not ctl.telemetry_link_ok(1.0)
        assert not ctl.return_to_home_required(0.5)
        assert not ctl.return_to_home_required(1.0)
        assert not ctl.return_to_home_required(3.4)
        assert ctl.return_to_home_required(3.5)
    finally:
        ctl.telemetry_loss_windows = []
        ctl._link_down_since = None
    assert not ctl.return_to_home_required(30.0)                               # link up: never


# ---------------------------------------------------------------- statistics

COLS = ["run_id", "scene", "condition", "seed", "duration_s", "cycle_time_s", "worst_revisit_ground_s", "detected",
        "min_obstacle_clearance_m", "obstacle_contacts"]


def build_fixture(tmp_path, n=12):
    """FIXTURE only: seeded normal draws, used to check code against scipy."""
    rng = np.random.default_rng(2026)
    spec = {("interior", "guard_baseline"): (300.0, 40.0), ("interior", "uav_sectors"): (95.0, 15.0),
            ("interior", "uav_offset_ring"): (90.0, 22.0), ("exterior", "guard_baseline"): (310.0, 35.0),
            ("exterior", "uav_sectors"): (80.0, 10.0), ("exterior", "uav_offset_ring"): (79.0, 12.0)}
    rows, truth = [], {}
    for (scene, cond), (mu, sd) in spec.items():
        vals = rng.normal(mu, sd, n)
        truth[(scene, cond)] = vals
        for i, v in enumerate(vals):
            clr = "" if (scene == "exterior" or cond == "guard_baseline") else f"{rng.normal(1.1, 0.2):.4f}"
            rows.append({"run_id": f"FIXTURE_{scene}_{cond}_{i}", "scene": scene, "condition": cond, "seed": i,
                         "duration_s": "500", "cycle_time_s": repr(float(v) / 2.0), "detected": str(i % 2),
                         "worst_revisit_ground_s": repr(float(v)), "min_obstacle_clearance_m": clr,
                         "obstacle_contacts": "" if clr == "" else str(i % 2)})
    path = tmp_path / "campus_patrol_real_trials.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    (tmp_path / "campus_patrol_real_trials.provenance.json").write_text(
        json.dumps({"note": "FIXTURE for unit tests only", "not_applicable": ["guard_baseline: clearance"],
                    "csv_sha256": sv.file_sha256(str(path))}))
    return str(path), truth, rows


def test_welch_matches_scipy_reference(tmp_path):
    path, truth, _ = build_fixture(tmp_path)
    rows, _prov, _digest = sv.load_validated(path)
    for scene in ("interior", "exterior"):
        for ca, cb in (sv.PRIMARY_PAIR, sv.SECONDARY_PAIR):
            a, b = sv.column(rows, scene, ca, "worst_revisit_ground_s"), sv.column(rows, scene, cb, "worst_revisit_ground_s")
            r = sv.welch(a, b, 0.05)
            ref = stats.ttest_ind(a, b, equal_var=False)
            ci = ref.confidence_interval(0.95)
            assert r["t"] == pytest.approx(ref.statistic, rel=1e-10)
            assert r["p"] == pytest.approx(ref.pvalue, rel=1e-9)
            assert r["df"] == pytest.approx(ref.df, rel=1e-10)
            assert r["ci_lo"] == pytest.approx(ci.low, rel=1e-9) and r["ci_hi"] == pytest.approx(ci.high, rel=1e-9)
            sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
            assert r["d"] == pytest.approx((a.mean() - b.mean()) / sp, rel=1e-12)
            assert r["reject"] == bool(ref.pvalue < 0.05)


def test_script_runs_on_fixture_and_prints_everything(tmp_path, capsys):
    path, truth, _ = build_fixture(tmp_path)
    assert sv.main(["--csv", path, "--scene", "all"]) == 0
    out = capsys.readouterr().out
    for token in ("PRIMARY", "SECONDARY", "Welch t", "Welch-Satterthwaite", "two-sided p", "Cohen's d",
                  "95 % CI of the mean difference", "decision at alpha = 0.05", "min_obstacle_clearance_m",
                  "obstacle_contacts total", "scene: interior", "scene: exterior", "cycle_time_s", "Wilson", "exact"):
        assert token in out, token
    assert sv.main(["--csv", path, "--scene", "exterior"]) == 0
    assert "scene: interior" not in capsys.readouterr().out
    # deterministic text
    sv.main(["--csv", path]); first = capsys.readouterr().out
    sv.main(["--csv", path]); assert capsys.readouterr().out == first


def test_clearance_ci_and_contacts_match_scipy(tmp_path):
    path, _, _ = build_fixture(tmp_path)
    rows, _prov, _digest = sv.load_validated(path)
    x = sv.column(rows, "interior", "uav_sectors", "min_obstacle_clearance_m")
    m, lo, hi = sv.mean_ci(x)
    ref = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
    assert (lo, hi) == pytest.approx(ref, rel=1e-10) and m == pytest.approx(x.mean())
    assert sv.column(rows, "interior", "guard_baseline", "min_obstacle_clearance_m").size == 0   # not applicable


def test_refuses_simulated_and_unprovenanced_input(tmp_path, capsys):
    path, _, rows = build_fixture(tmp_path)
    prov = tmp_path / "campus_patrol_real_trials.provenance.json"
    good = prov.read_text()
    # 1. missing provenance
    prov.unlink()
    assert sv.main(["--csv", path]) == 2 and "provenance" in capsys.readouterr().out
    # 2. SIMULATED_ marker in the CSV
    prov.write_text(good)
    bad = tmp_path / "bad.csv"
    bad.write_text(open(path).read().replace("FIXTURE_interior_uav_sectors_0", "SIMULATED_interior_uav_sectors_0"))
    (tmp_path / "bad.provenance.json").write_text(good)
    assert sv.main(["--csv", str(bad)]) == 2 and "SIMULATED_" in capsys.readouterr().out
    # 3. SIMULATED_ marker in the provenance record
    (tmp_path / "bad.provenance.json").write_text(json.dumps({"source": "SIMULATED_scaffold", "not_applicable": []}))
    assert sv.main(["--csv", path.replace("campus_patrol_real_trials", "bad")]) == 2
    # 4. provenance without not_applicable
    prov.write_text(json.dumps({"note": "x"}))
    assert sv.main(["--csv", path]) == 2
    # 5. missing CSV
    assert sv.main(["--csv", str(tmp_path / "nope.csv")]) == 2
    # 6. the CSV was edited after its provenance record was written: the sha256 gate refuses it
    prov.write_text(good)
    open(path, "a").write("FIXTURE_edit,interior,uav_sectors,99,500,1,1,0,1,1\n")
    assert sv.main(["--csv", path]) == 2 and "sha256" in capsys.readouterr().out


def test_degenerate_groups_are_reported_not_crashed():
    assert "error" in sv.welch(np.array([1.0]), np.array([1.0, 2.0]))
    assert "error" in sv.welch(np.array([1.0, 1.0]), np.array([2.0, 2.0]))


def test_detection_intervals_match_scipy():
    for k, n in ((0, 3), (3, 3), (11, 30), (30, 30)):
        lo, hi = sv.exact_ci(k, n)
        ref = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
        assert (lo, hi) == pytest.approx((ref.low, ref.high), abs=1e-9)
        wl, wh = sv.wilson_ci(k, n)
        refw = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
        assert (wl, wh) == pytest.approx((refw.low, refw.high), abs=1e-9)
