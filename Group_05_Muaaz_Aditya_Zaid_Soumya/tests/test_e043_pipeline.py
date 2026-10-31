"""
Benchmark pipeline checks | owner E043 Muaaz
  * contract-B telemetry: one row per 0.002 s physics step per vehicle, exact column order
  * contract-A row: column set, tracking RMSE / control effort / energy finite
  * determinism: the same (scene, condition, seed) gives an identical summary row
  * the guard and the UAV conditions are scored by the SAME checkpoint_metrics function
Short simulated windows only; the numbers here are test fixtures, never results.

  python -m pytest tests/test_e043_pipeline.py
"""
import csv
import gzip
import json
import math
import os
import sys

import numpy as np
import pytest

GROUP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GROUP, "src"))
sys.path.insert(0, os.path.join(GROUP, "analytics"))
import aerial_patrol_swarm as aps          # noqa: E402
import foot_patrol_baseline as fpb         # noqa: E402
import patrol_metrics                      # noqa: E402
import run_benchmark as rb                 # noqa: E402
import run_telemetry                       # noqa: E402

CONTRACT_A = ["run_id", "scene", "condition", "seed", "duration_s", "timestep_s", "mean_wind_mps", "gust_sigma_mps",
              "intruder_appear_s", "dock_jitter_m", "n_ground_laps", "cycle_time_s", "worst_revisit_ground_s",
              "mean_revisit_ground_s", "worst_revisit_gallery_s", "gallery_coverage", "detected",
              "detection_latency_s", "verify_time_s", "min_inter_uav_m", "tracking_rmse_m", "control_effort_N2s",
              "energy_wh", "min_obstacle_clearance_m", "obstacle_contacts", "uav_uav_contacts", "guard_speed_mps",
              "guard_stop_mean_s",
              # appended columns (append-only contract)
              "worst_revisit_ground_eqwin_s", "eqwin_s", "n_laps_alpha", "n_laps_bravo", "n_laps_guard",
              "waypoint_rmse_m", "torque_effort_N2m2s"]
CONTRACT_B = (["t", "run_id", "seed", "condition", "uav", "x", "y", "z", "vx", "vy", "vz", "xref", "yref", "zref",
               "ex", "ey", "ez"] + [f"f{k}" for k in range(8)] + ["fsm_state", "event", "roll", "pitch", "yaw"])


def read_gz(path):
    with gzip.open(path, "rt") as fh:
        r = csv.reader(fh)
        header = next(r)
        return header, [dict(zip(header, row)) for row in r]


def test_contract_columns():
    assert rb.COLUMNS == CONTRACT_A
    assert run_telemetry.COLUMNS == CONTRACT_B


def test_uav_telemetry_every_physics_step(tmp_path):
    path = str(tmp_path / "interior_uav_sectors_s5.csv.gz")
    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["interior"], seed=5, vision=False, frame_log=False,
                                            telemetry_path=path, run_id="interior_uav_sectors_s5",
                                            condition="uav_sectors")
    while ctl.current_time_s < 2.0 - 1e-9:
        ctl.step_simulation(dt=1.0 / 30.0)
    ctl.close_telemetry()
    header, rows = read_gz(path)
    assert header == CONTRACT_B
    assert ctl.model.opt.timestep == 0.002
    for uav, own, other in (("alpha", range(0, 4), range(4, 8)), ("bravo", range(4, 8), range(0, 4))):
        rs = [r for r in rows if r["uav"] == uav]
        t = np.array([float(r["t"]) for r in rs])
        assert len(rs) == round(ctl.current_time_s / 0.002)
        assert np.allclose(np.diff(t), 0.002, atol=1e-9)
        assert all(r[f"f{k}"] != "" for r in rs for k in own)
        assert all(r[f"f{k}"] == "" for r in rs for k in other)
        assert all(r["fsm_state"] for r in rs)
        # G-11: attitude columns present on every UAV row, finite, radians (|roll|, |pitch| < 90 deg)
        att = np.array([[float(r[c]) for c in ("roll", "pitch", "yaw")] for r in rs])
        assert np.all(np.isfinite(att)) and np.all(np.abs(att[:, :2]) < math.pi / 2) and np.all(np.abs(att[:, 2]) <= math.pi)


def test_guard_telemetry_every_physics_step(tmp_path):
    path = str(tmp_path / "exterior_guard_baseline_s5.csv.gz")
    rng = np.random.default_rng(5)
    g = fpb.FootPatrol(aps.SCENES["exterior"], 5, fpb.draw_guard_params(rng), 30.0, rng)
    g.run(3.0, telemetry_path=path, run_id="exterior_guard_baseline_s5")
    header, rows = read_gz(path)
    assert header == CONTRACT_B
    t = np.array([float(r["t"]) for r in rows])
    assert len(rows) == 1500 and set(r["uav"] for r in rows) == {"guard"}
    assert np.allclose(np.diff(t), 0.002, atol=1e-9)
    assert all(r[f"f{k}"] == "" and r["ex"] == "" for r in rows for k in range(8))
    assert all(r["roll"] == r["pitch"] == r["yaw"] == "" for r in rows)


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """Two runs of each job in separate directories (determinism) -- fixture rows, never results."""
    out = {}
    for job in (("interior", "uav_sectors", 7, 30.0), ("exterior", "uav_offset_ring", 7, 30.0),
                ("interior", "guard_baseline", 7, 600.0)):
        rows = []
        for k in range(2):
            d = str(tmp_path_factory.mktemp(f"runs{k}"))
            rows.append(rb.run_one((*job, d, False, False, None))["row"])
        out[job[:2]] = rows
    return out


def test_rmse_effort_energy_finite(runs):
    for key in (("interior", "uav_sectors"), ("exterior", "uav_offset_ring")):
        row = runs[key][0]
        for c in ("tracking_rmse_m", "control_effort_N2s", "energy_wh", "min_inter_uav_m", "waypoint_rmse_m",
                  "torque_effort_N2m2s", "worst_revisit_ground_eqwin_s"):
            assert row[c] is not None and math.isfinite(row[c]) and row[c] > 0, (key, c, row[c])
        assert set(row) == set(CONTRACT_A)


def test_same_seed_identical_summary_row(runs):
    for key, (r1, r2) in runs.items():
        assert r1 == r2, key


def test_not_applicable_columns_empty(runs):
    g = runs[("interior", "guard_baseline")][0]
    for c in rb.PER_CONDITION_NA["guard_baseline"]:
        assert g[c] is None, c
    u = runs[("interior", "uav_sectors")][0]
    for c in rb.PER_CONDITION_NA["uav_sectors"] + ["detected", "detection_latency_s", "verify_time_s"]:
        assert u[c] is None, c                        # vision off in the fixture -> not measured


def test_guard_and_uavs_share_one_metric_function(monkeypatch):
    assert fpb.checkpoint_metrics is patrol_metrics.checkpoint_metrics
    assert aps.checkpoint_metrics is patrol_metrics.checkpoint_metrics
    calls = []
    real = patrol_metrics.checkpoint_metrics

    def spy(visits, *a, **k):
        calls.append(sorted(visits))
        return real(visits, *a, **k)
    monkeypatch.setattr(fpb, "checkpoint_metrics", spy)
    monkeypatch.setattr(aps, "checkpoint_metrics", spy)
    rng = np.random.default_rng(1)
    g = fpb.FootPatrol(aps.SCENES["interior"], 1, fpb.draw_guard_params(rng), 30.0, rng).run(5.0)
    g.metrics()
    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["interior"], seed=1, vision=False, frame_log=False)
    ctl.patrol_metrics()
    assert len(calls) == 2 and calls[0] == calls[1], "guard and UAV visits must be scored by the same function"


def test_checkpoint_metrics_definitions_on_labelled_fixture():
    # FIXTURE (hand-made service times), not simulation output
    visits = {"patrol_cp0": [0.0, 10.0, 25.0], "patrol_cp1": [5.0, 16.0, 30.0],
              "atrium_cp0": [2.0, 40.0], "atrium_cp1": []}
    m = patrol_metrics.checkpoint_metrics(visits)
    assert m["worst_revisit_ground_s"] == 15.0
    assert m["mean_revisit_ground_s"] == pytest.approx((10 + 15 + 11 + 14) / 4)
    assert m["worst_revisit_gallery_s"] is None          # atrium_cp1 never serviced twice
    assert m["gallery_coverage"] == 0.5
    assert m["n_ground_laps"] == 3 and m["cycle_time_s"] == pytest.approx((30.0 - 5.0) / 2)
    once = patrol_metrics.checkpoint_metrics({"patrol_cp0": [1.0, 2.0], "patrol_cp1": [1.5]})
    assert once["worst_revisit_ground_s"] is None        # not observable within the window


def test_resume_rejects_stale_code_or_model_hash(tmp_path):
    """G-12: a cached summary is reused only when code_sha AND model_sha (and the run settings) match."""
    d = str(tmp_path)
    job = ("exterior", "uav_offset_ring", 3, 4.0, d, False, False, None)
    first = rb.run_one(job)
    assert not first["meta"].get("resumed")
    assert first["meta"]["code_sha"] == rb.code_sha() and first["meta"]["model_sha"] == rb.model_sha()
    assert rb.run_one(job)["meta"].get("resumed") is True          # same code + models -> reused
    path = os.path.join(d, "summary", "exterior_uav_offset_ring_s3.json")
    for key in ("code_sha", "model_sha"):
        doc = json.load(open(path))
        doc["meta"][key] = "0" * 16                                # summary written by other code / models
        doc["row"]["energy_wh"] = -1.0                             # marker: must not survive a rerun
        json.dump(doc, open(path, "w"))
        rerun = rb.run_one(job)
        assert not rerun["meta"].get("resumed"), key
        assert rerun["row"]["energy_wh"] == first["row"]["energy_wh"], key
    doc = json.load(open(path))
    del doc["meta"]["code_sha"]                                    # older runner without hashes -> stale
    json.dump(doc, open(path, "w"))
    assert not rb.run_one(job)["meta"].get("resumed")


def test_equal_window_worst_revisit_fixture():
    # FIXTURE (hand-made service times), not simulation output
    visits = {"patrol_cp0": [10.0, 50.0, 400.0], "patrol_cp1": [30.0], "atrium_cp0": [5.0]}
    assert patrol_metrics.worst_revisit_window(visits, 300.0) == pytest.approx(270.0)   # cp1: 30 -> 300
    assert patrol_metrics.worst_revisit_window({"patrol_cp0": [], "patrol_cp1": [1.0]}, 100.0) == 100.0
    assert patrol_metrics.worst_revisit_window({"atrium_cp0": [1.0]}, 100.0) is None


def test_per_condition_durations_one_invocation(tmp_path, monkeypatch):
    """G-08: --uav-duration sets the UAV runs while guards keep their own duration, in ONE CSV + provenance."""
    seen = []

    def fake_run_one(job):
        scene, cond, seed, dur = job[:4]
        seen.append((scene, cond, dur, (job[8] or {}).get("eqwin_s", rb.EQWIN_S) if len(job) > 8 else None))
        row = {c: None for c in rb.COLUMNS}
        row.update(run_id=f"{scene}_{cond}_s{seed}", scene=scene, condition=cond, seed=seed, duration_s=dur,
                   timestep_s=0.002)
        return {"row": row, "meta": {"wall_s": 0.0}}

    class FakePool:
        def __init__(self, n): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def imap_unordered(self, f, jobs): return map(fake_run_one, jobs)

    class FakeCtx:
        Pool = FakePool
    monkeypatch.setattr(rb.mp, "get_context", lambda *_: FakeCtx)
    out = str(tmp_path / "b.csv")
    monkeypatch.setattr(sys, "argv", ["run_benchmark.py", "--trials", "1", "--uav-duration", "300", "--out", out,
                                      "--no-vision", "--no-telemetry"])
    rb.main()
    durs = {(s, c): d for s, c, d, _ in seen}
    assert durs[("interior", "guard_baseline")] == 5000.0 and durs[("exterior", "guard_baseline")] == 1800.0
    assert all(durs[(s, c)] == 300.0 for s in rb.SCENES for c in ("uav_sectors", "uav_offset_ring"))
    prov = json.load(open(str(tmp_path / "b.provenance.json")))
    assert prov["windows"]["eqwin_s"] == rb.EQWIN_S == 300.0
    assert prov["windows"]["simulated_duration_s"]["interior"]["guard_baseline"] == 5000.0
    assert prov["windows"]["simulated_duration_s"]["exterior"]["uav_sectors"] == 300.0
    with open(out) as fh:
        assert len(list(csv.DictReader(fh))) == 6
