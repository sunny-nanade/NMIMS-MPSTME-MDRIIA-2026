"""Right-censoring of the equal-window worst revisit (analytics/censored_revisit.py, statistical_validation output)."""
import csv
import os
import sys

import pytest

GROUP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(GROUP, "analytics"))
import censored_revisit as cr  # noqa: E402
import statistical_validation as sv  # noqa: E402

M = cr.EQWIN_METRIC


def _rows(guard, uav, w=300.0):
    out = []
    for cond, vals in (("guard_baseline", guard), ("uav_sectors", uav), ("uav_offset_ring", uav)):
        for i, v in enumerate(vals):
            out.append({"scene": "interior", "condition": cond, "seed": str(i), M: str(v), "eqwin_s": str(w)})
    return out


def test_censored_count_and_descriptive_line():
    rows = _rows([300.0] * 29 + [250.0], [50.0, 99.5])
    cs = cr.cell_stats(rows, "interior", "guard_baseline")
    assert (cs["k_censored"], cs["n"], cs["window_s"]) == (29, 30, 300.0)
    assert cr.cell_stats(rows, "interior", "uav_sectors")["k_censored"] == 0
    assert cr.descriptive_line(rows, "interior") == \
        "29 of 30 guard runs had no revisit inside 300 s; UAV worst revisit max 99.50 s"


def test_window_comes_from_the_csv_not_a_constant():
    rows = _rows([120.0] * 3, [10.0], w=120.0)
    assert cr.cell_stats(rows, "interior", "guard_baseline")["k_censored"] == 3
    assert "inside 120 s" in cr.descriptive_line(rows, "interior")


def test_gate_edge_cases():
    assert cr.revisit_gate([10.0, 299.999], 300.0)
    assert not cr.revisit_gate([10.0, 300.0], 300.0)      # a UAV run exactly at the window is censored -> FAIL
    assert not cr.revisit_gate([10.0, 350.0], 300.0)
    assert not cr.revisit_gate([], 300.0)


def test_real_csv_guard_cells_are_fully_censored_and_no_ttest_printed():
    rows, prov, digest = sv.load_validated(sv.DEFAULT_CSV)
    for scene in sv.SCENES:
        g = cr.cell_stats(rows, scene, "guard_baseline")
        assert g["k_censored"] == g["n"] == 30
        for c in sv.UAV_CONDITIONS:
            assert cr.cell_stats(rows, scene, c)["k_censored"] == 0
    text = "\n".join(sv.build_report(rows, prov, digest, sv.DEFAULT_CSV, 0.05, sv.SCENES))
    assert "30 of 30 guard runs had no revisit inside 300 s; UAV worst revisit max" in text
    assert ">= 300 s (right-censored)" in text
    # Welch blocks exist only for cycle_time_s: 2 pairs x 2 scenes, none for the equal-window metric
    assert text.count("Welch t =") == 4
    assert f"metric {M}" not in text
    assert "EQUAL-WINDOW" not in text
