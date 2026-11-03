import numpy as np

from panel_registry import PanelRegistry, make_id, parse_id


def test_ids_roundtrip_and_count():
    reg = PanelRegistry()
    assert len(reg) == 40
    assert parse_id(make_id(3, 7)) == (3, 7)
    assert reg.ids[0] == "PV_R01_C01" and reg.ids[-1] == "PV_R04_C10"


def test_ray_hits_expected_panel():
    reg = PanelRegistry()
    spec = reg.get("PV_R02_C05")
    origin = spec.center + 2.0 * spec.normal
    hit = reg.hit_panel(origin, -spec.normal)
    assert hit is not None and reg.ids[hit[0]] == "PV_R02_C05"


def test_ray_misses_between_rows():
    reg = PanelRegistry()
    assert reg.hit_panel(np.array([5.0, 3.0, 1.2]), np.array([0.0, 0.0, -1.0])) is None


def test_cell_positions_lie_in_module_plane():
    reg = PanelRegistry()
    p = reg.index("PV_R01_C01")
    d = reg.cell_centers[p] - reg.centers[p]
    assert np.allclose(d @ reg.normal, 0.0, atol=1e-9)
