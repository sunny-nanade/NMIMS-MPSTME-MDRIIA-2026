import os

import mujoco

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_model_compiles_with_dossier_settings():
    m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "solar_defect_amr.xml"))
    assert abs(m.opt.timestep - 0.002) < 1e-12
    assert m.nu == 5
    assert abs(m.geom_solref[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "wheel_left_geom")][0] - 0.005) < 1e-9


def test_robot_rests_on_floor():
    m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "solar_defect_amr.xml"))
    d = mujoco.MjData(m)
    for _ in range(1500):
        mujoco.mj_step(m, d)
    assert 0.195 < d.qpos[2] < 0.205
