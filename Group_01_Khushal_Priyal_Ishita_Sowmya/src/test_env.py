"""
Sprint 0 Toolchain Verification Script
Course: MDRIIA (702CO0E012) | Group: MDRIIA_GROUP_01
Project: To what extent can an autonomous mobile medicine-delivery robot (simulated in MuJoCo with dynamic obstacle avoidance) reduce ICU nurses' non-patient-facing logistics transit time and optimize labor reallocation, where clinical studies document nurses spending approximately 28% of their shift on supply retrieval?
"""
import sys

def verify_environment():
    print(f"==================================================")
    print(f"MDRIIA GROUP 01 - ENVIRONMENT VERIFICATION")
    print(f"==================================================")
    print(f"[OK] Python Version: {sys.version.split()[0]}")
    
    try:
        import numpy as np
        print(f"[OK] NumPy Version: {np.__version__}")
    except ImportError:
        print("[ERROR] NumPy is not installed. Run: pip install numpy")
        
    try:
        import scipy
        print(f"[OK] SciPy Version: {scipy.__version__}")
    except ImportError:
        print("[ERROR] SciPy is not installed. Run: pip install scipy")
        
    try:
        import mujoco
        print(f"[OK] MuJoCo Version: {mujoco.__version__}")
        # Quick model verification
        xml_test = """<mujoco><worldbody><body name="floor"><geom type="plane" size="1 1 0.1"/></body></worldbody></mujoco>"""
        m = mujoco.MjModel.from_xml_string(xml_test)
        d = mujoco.MjData(m)
        mujoco.mj_step(m, d)
        print("[SUCCESS] MuJoCo physics engine compiled and stepped successfully!")
    except ImportError:
        print("[ERROR] MuJoCo is not installed. Run: pip install mujoco")
    except Exception as e:
        print(f"[ERROR] MuJoCo test step failed: {e}")

    print(f"==================================================")
    print(f"Toolchain check complete for Group 01.")

if __name__ == "__main__":
    verify_environment()
