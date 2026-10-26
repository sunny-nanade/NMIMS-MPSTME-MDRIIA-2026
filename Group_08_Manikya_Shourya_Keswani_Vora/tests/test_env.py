"""Smoke tests: python -m pytest tests -q   (or: python tests/test_env.py)"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rl import STAGES  # noqa: E402
from rl.skyhydro_env import SkyHydroDeliveryEnv  # noqa: E402
from rl.expert import run_episode  # noqa: E402


def test_scene_files_exist():
    for f in ("scene_flood.xml", "scene_flood_dynamic.xml", "scene_train.xml", "scene_manifest.json"):
        assert os.path.exists(os.path.join(ROOT, "environment", f)), f"missing {f} — run environment/scene_generator.py"


def test_reset_and_step_shapes():
    env = SkyHydroDeliveryEnv(seed=0)
    obs, info = env.reset(seed=0)
    assert obs.shape == env.observation_space.shape and np.all(np.isfinite(obs))
    obs, r, term, trunc, info = env.step(np.zeros(4, np.float32))
    assert obs.shape == (26,) and isinstance(r, float)
    env.close()


def test_flight_controller_holds_hover():
    env = SkyHydroDeliveryEnv(seed=1, start="warehouse")
    env.reset(seed=1)
    p0 = env.ctrl.pos()
    for _ in range(30):                                  # 3 s of hover command
        env.step(np.array([0, 0, 0, -1], np.float32))
    drift = np.linalg.norm(env.ctrl.pos() - p0)
    assert drift < 1.0, f"hover drift {drift:.2f} m"
    assert env.ctrl.tilt_deg() < 5


def test_expert_completes_stage1():
    env = SkyHydroDeliveryEnv(**STAGES[1])
    R, info, events = run_episode(env, seed=3)
    assert info.get("event") == "mission_complete", events
    assert info["delivered"] == 1


def test_live_water_animates():
    import mujoco
    sys.path.insert(0, os.path.join(ROOT, "environment"))
    from live_water import LiveWater
    m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "environment", "scene_flood_dynamic.xml"))
    w = LiveWater(m, os.path.join(ROOT, "environment"))
    assert w.ok, "live water not set up — run environment/scene_generator.py (or environment/live_water.py)"
    w.update(None, 0.0)
    a = w.tex[:, w.c0:w.c1].copy()
    w.update(None, 0.5)
    assert np.abs(a.astype(int) - w.tex[:, w.c0:w.c1]).mean() > 1.0     # the water moves


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
