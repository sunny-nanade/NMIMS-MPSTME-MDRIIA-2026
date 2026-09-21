import os
import sys

def verify_environment():
    print("==================================================================")
    print("MDRIIA GROUP 11: SMOKE TEST & PHYSICS ENVIRONMENT VERIFICATION")
    print("Domain: Solar PV Defect Inspection & Anomaly Detection AMR")
    print("Lead: Daneeka Abhijeet Roy (E057)")
    print("==================================================================")
    try:
        import mujoco
        print("[SUCCESS] DeepMind MuJoCo engine successfully imported.")
    except ImportError:
        print("[FAIL] DeepMind MuJoCo is not installed in the active environment.")
        return False

    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(os.path.dirname(script_dir), "models", "solar_defect_amr.xml")

    if not os.path.exists(model_path):
        print(f"[FAIL] MJCF XML model not found at: {model_path}")
        return False

    try:
        model = mujoco.MjModel.from_xml_path(model_path)
        data = mujoco.MjData(model)
        for _ in range(50):
            mujoco.mj_step(model, data)
        print(f"[SUCCESS] Physics model compiled and stepped successfully.")
        print(f"Bodies: {model.nbody} | Geoms: {model.ngeom} | Actuators: {model.nu}")
        return True
    except Exception as e:
        print(f"[FAIL] Error stepping physics model: {e}")
        return False

if __name__ == "__main__":
    success = verify_environment()
    sys.exit(0 if success else 1)
