# Sprint 0 Toolchain and MuJoCo Simulation Environment Verification
# Group: MDRIIA Group 09
# Domain: Hazardous Terrain UGV & Traversability Mapping

import sys
import os

def run_environment_verification():
    print("=" * 60)
    print("MDRIIA GROUP 09 - TOOLCHAIN AND PHYSICS VERIFICATION")
    print("=" * 60)
    print(f"[OK] Python Version: {sys.version.split()[0]}")

    # 1. Verify Scientific Stack
    for pkg in ["numpy", "scipy", "matplotlib"]:
        try:
            mod = __import__(pkg)
            print(f"[OK] {pkg.capitalize()} Version: {mod.__version__}")
        except ImportError:
            print(f"[ERROR] Required library missing: {pkg}. Run: pip install {pkg}")

    # 2. Verify MuJoCo Physics Engine
    try:
        import mujoco
        print(f"[OK] MuJoCo Version: {mujoco.__version__}")

        model_path = os.path.join(os.path.dirname(__file__), "..", "models", "hazardous_terrain_ugv.xml")
        if os.path.exists(model_path):
            m = mujoco.MjModel.from_xml_path(model_path)
            d = mujoco.MjData(m)
            mujoco.mj_step(m, d)
            print(f"[SUCCESS] Successfully compiled MJCF model: {os.path.basename(model_path)}")
            print(f"[INFO] System DoF: {m.nv}, Actuators: {m.nu}, Geoms: {m.ngeom}")
        else:
            print(f"[WARNING] Model file not found at {model_path}")
    except ImportError:
        print("[ERROR] MuJoCo library not installed. Run: pip install mujoco")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] MuJoCo model compilation error: {e}")
        sys.exit(1)

    print("=" * 60)
    print("Sprint 0 toolchain check complete.")

if __name__ == "__main__":
    run_environment_verification()
