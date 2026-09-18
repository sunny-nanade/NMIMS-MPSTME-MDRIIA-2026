"""
Sprint 0 Toolchain Verification Script
Course: MDRIIA (702CO0E012) | Group: MDRIIA_GROUP_04
Project: How can a multi-arm robotic gripper mechanism simulated in MuJoCo utilize impedance contact control to synchronize with and capture tumbling non-cooperative orbital debris in LEO while mitigating collision impulse and momentum transfer?
"""
import sys

def verify_environment():
    print(f"==================================================")
    print(f"MDRIIA GROUP 04 - ENVIRONMENT VERIFICATION")
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
    print(f"Toolchain check complete for Group 04.")

if __name__ == "__main__":
    verify_environment()
