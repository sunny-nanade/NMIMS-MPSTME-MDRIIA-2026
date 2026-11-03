"""The detector must never see ground truth, and must separate defects from confounders."""
import ast
import os

import numpy as np
import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


def _imports(fname):
    tree = ast.parse(open(os.path.join(SRC, fname)).read())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    return mods


def test_detector_does_not_import_ground_truth():
    for f in ("defect_detection.py", "thermal_optics.py", "navigation.py", "robot_controller.py"):
        assert "fault_injection" not in _imports(f), f
        assert "solar_environment" not in _imports(f), f


def test_controller_never_passes_truth_to_detector_or_sensors_of_the_robot():
    """Static check: no line of the FSM that talks to the detector mentions the ground-truth object."""
    lines = open(os.path.join(SRC, "solar_defect_detector.py")).read().splitlines()
    for i, ln in enumerate(lines):
        if "self.det." in ln or "Detector(" in ln:
            assert "self.gt" not in ln and "truth" not in ln.lower(), (i + 1, ln)


@pytest.mark.slow
def test_hotspot_flagged_and_shadow_confounder_rejected():
    from fault_injection import DefectKind, make_defect, make_ext_shadow
    from solar_defect_detector import InspectionMission, MissionConfig
    from panel_registry import PanelRegistry
    reg = PanelRegistry()
    rng = np.random.default_rng(3)
    defects = [make_defect(reg, DefectKind.HOTSPOT, "PV_R01_C03", rng, cell=(5, 3), severity=30.0),
               make_ext_shadow(reg, "PV_R01_C07", rng)]
    cfg = MissionConfig(condition="proposed", seed=3, defects=defects, rows=[1], log_telemetry=False)
    model = os.path.join(os.path.dirname(SRC), "models", "solar_defect_amr.xml")
    res = InspectionMission(cfg, model).run()
    flagged = {d["panel_id_est"] for d in res.detections}
    assert "PV_R01_C03" in flagged
    assert "PV_R01_C07" not in flagged
