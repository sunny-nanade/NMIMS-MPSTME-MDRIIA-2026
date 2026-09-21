# Verification and Test Environment Script
# Group: MDRIIA Group 03
# Project: Autonomous Last-Mile Ground AED Delivery Vehicle

import sys
import os

def run_environment_check():
    print("=" * 60)
    print("MDRIIA GROUP 03 - TOOLCHAIN AND PHYSICS VERIFICATION")
    print("=" * 60)
    print(f"[OK] Python Version: {sys.version.split()[0]}")
    
    try:
        import numpy as np
        print(f"[OK] NumPy Version: {np.__version__}")
    except ImportError:
        print("[ERROR] NumPy is missing. Install via: pip install numpy")
        return False
        
    try:
        import scipy
        print(f"[OK] SciPy Version: {scipy.__version__}")
    except ImportError:
        print("[ERROR] SciPy is missing. Install via: pip install scipy")
        return False

    try:
        import matplotlib
        print(f"[OK] Matplotlib Version: {matplotlib.__version__}")
    except ImportError:
        print("[ERROR] Matplotlib is missing. Install via: pip install matplotlib")
        return False

    try:
        import mujoco
        print(f"[OK] MuJoCo Version: {mujoco.__version__}")
        
        # Verify model compilation
        current_dir = os.path.dirname(os.path.abspath(__file__))
        xml_path = os.path.join(os.path.dirname(current_dir), "models", "aed_delivery_amr.xml")
        
        if os.path.exists(xml_path):
            model = mujoco.MjModel.from_xml_path(xml_path)
            data = mujoco.MjData(model)
            mujoco.mj_step(model, data)
            print(f"[SUCCESS] Loaded and stepped model: {xml_path}")
            print(f"[INFO] Model Bodies: {model.nbody}, Joints: {model.njnt}, Actuators: {model.nu}")
        else:
            print(f"[WARNING] Local XML not found at {xml_path}. Testing fallback string.")
            fallback = "<mujoco><worldbody><body name='b'><geom type='sphere' size='0.1'/></body></worldbody></mujoco>"
            m = mujoco.MjModel.from_xml_string(fallback)
            d = mujoco.MjData(m)
            mujoco.mj_step(m, d)
            print("[SUCCESS] Fallback physics step verified.")
    except ImportError:
        print("[ERROR] MuJoCo library not installed. Run: pip install mujoco")
        return False
    except Exception as e:
        print(f"[ERROR] Physics compilation failed: {e}")
        return False
        
    print("=" * 60)
    print("Verification complete. All required libraries are ready.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_environment_check()
    sys.exit(0 if success else 1)
