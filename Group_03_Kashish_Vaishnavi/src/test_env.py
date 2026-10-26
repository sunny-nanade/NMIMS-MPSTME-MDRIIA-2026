"""Verification and test-environment script.

MDRIIA Group 03 - autonomous last-mile ground AED delivery rover.

Checks the Python toolchain, compiles models/aed_delivery_amr.xml with plain MuJoCo, steps it,
and checks that the vendored package (src/aedrover) can build and step a simulation environment.
Exit status 0 means every check passed.
"""

import importlib
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))

REQUIRED = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("matplotlib", "matplotlib"),
    ("pandas", "pandas"),
    ("yaml", "pyyaml"),
    ("gymnasium", "gymnasium"),
    ("mujoco", "mujoco"),
]


def run_environment_check():
    print("=" * 60)
    print("MDRIIA GROUP 03 - TOOLCHAIN AND PHYSICS VERIFICATION")
    print("=" * 60)
    if sys.version_info < (3, 10):
        print(f"[ERROR] Python {sys.version.split()[0]} is too old; Python 3.10 or newer is required.")
        return False
    print(f"[OK] Python Version: {sys.version.split()[0]}")

    for module, pip_name in REQUIRED:
        try:
            mod = importlib.import_module(module)
        except ImportError:
            print(f"[ERROR] {module} is missing. Install via: pip install {pip_name}")
            return False
        print(f"[OK] {module} Version: {getattr(mod, '__version__', 'unknown')}")

    import mujoco
    import numpy as np

    xml_path = ROOT / "models" / "aed_delivery_amr.xml"
    if not xml_path.exists():
        print(f"[ERROR] Model file not found: {xml_path}")
        return False
    try:
        model = mujoco.MjModel.from_xml_path(str(xml_path))
        data = mujoco.MjData(model)
        for _ in range(500):
            mujoco.mj_step(model, data)
    except Exception as exc:  # compilation or stepping failure
        print(f"[ERROR] Physics compilation failed: {exc}")
        return False
    if not (np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()):
        print("[ERROR] Simulation state became non-finite while settling the rover.")
        return False
    print(f"[SUCCESS] Loaded and stepped model: {xml_path}")
    print(f"[INFO] Model Bodies: {model.nbody}, Joints: {model.njnt}, Actuators: {model.nu}")
    print(f"[INFO] Simulated time: {data.time:.2f} s, chassis height: {data.qpos[2]:.3f} m")

    try:
        from aedrover.sim import AEDRoverEnv, VehicleParams

        env = AEDRoverEnv(veh=VehicleParams.optimized(), obs_mode="dict")
        env.reset(seed=0, options={"family": "flat_clear"})
        for _ in range(25):
            env.step(np.array([1.0, 0.0]))
    except Exception as exc:
        print(f"[ERROR] Vendored package aedrover failed: {exc}")
        return False
    print("[OK] Vendored package aedrover: environment reset and 25 control steps")

    print("=" * 60)
    print("Verification complete. All required libraries are ready.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    sys.exit(0 if run_environment_check() else 1)
