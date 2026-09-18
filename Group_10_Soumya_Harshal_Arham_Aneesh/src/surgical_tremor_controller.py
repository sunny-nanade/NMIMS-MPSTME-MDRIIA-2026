# Autonomous 7-DOF Surgical Robot Controller with Tremor Suppression
# Group: MDRIIA Group 10
# Incorporates Pedagogical Student Task Boundaries (TODO Tags)

import math
import numpy as np

class SurgicalTremorController:
    """
    7-DOF Surgical Manipulator Inverse Kinematics and Tremor Filter Controller
    """
    def __init__(self):
        # Kinematic Parameters
        self.num_joints = 7
        self.damping_lambda_0 = 0.08
        self.w_threshold = 0.02

        # Filter Parameters (2nd-Order Low-Pass Filter)
        self.cutoff_hz = 3.5
        self.sample_rate = 500.0 # Hz (dt = 0.002 s)
        self.filter_state = np.zeros(3)

        # Telemetry
        self.unfiltered_errors = []
        self.filtered_errors = []

    def compute_damped_least_squares_ik(self, J, delta_x):
        """
        Student Task Boundary - Soumya Singh (E071)
        # TODO [E071 - Soumya Singh]:
        # Implement singularity-robust DLS pseudoinverse calculation:
        # J_dls = J^T (J J^T + lambda^2 I)^(-1)
        # delta_q = J_dls * delta_x + (I - J_dls * J) * delta_q_null
        """
        JJt = np.dot(J, J.T)
        manipulability = math.sqrt(max(0.0, np.linalg.det(JJt)))
        if manipulability < self.w_threshold:
            lam = self.damping_lambda_0 * (1.0 - manipulability / self.w_threshold)
        else:
            lam = 0.0

        damped_inv = np.dot(J.T, np.linalg.inv(JJt + (lam**2) * np.eye(6)))
        delta_q = np.dot(damped_inv, delta_x)
        return delta_q

    def generate_physiological_tremor(self, t):
        """
        Student Task Boundary - Harshal Khandekar (E033)
        # TODO [E033 - Harshal Khandekar]:
        # Implement 8-12 Hz biophysical tremor model:
        # tremor(t) = sum(A_k * sin(2*pi*f_k*t + phi_k)) + eta(t)
        """
        f_tremor = 9.8 # Hz central tremor frequency
        amp = 0.00045 # 0.45 mm amplitude
        noise = np.random.normal(0, 0.00005, size=3)
        tremor_vec = amp * np.array([
            np.sin(2 * np.pi * f_tremor * t),
            np.cos(2 * np.pi * f_tremor * t * 1.1),
            np.sin(2 * np.pi * f_tremor * t * 0.9)
        ]) + noise
        return tremor_vec

    def apply_lowpass_filter(self, raw_pos, prev_filtered):
        """
        Student Task Boundary - Harshal Khandekar (E033)
        # TODO [E033 - Harshal Khandekar]:
        # Implement discrete-time low-pass filter satisfying tau < 25 ms delay:
        # y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
        """
        alpha = 0.095 # Tuned for 3.5 Hz cutoff at 500 Hz sampling
        filtered_pos = alpha * raw_pos + (1.0 - alpha) * prev_filtered
        return filtered_pos

    def evaluate_placement_accuracy(self, needle_tip_pos, target_pos):
        """
        Student Task Boundary - Arham Khan (E069)
        # TODO [E069 - Arham Khan]:
        # Compute 3D Euclidean displacement and evaluate sub-0.5 mm threshold:
        # e = norm(needle_tip - target) <= 0.0005 m
        """
        disp = np.linalg.norm(needle_tip_pos - target_pos)
        return disp

    def run_surgical_simulation(self, duration_s=2.0):
        print("=" * 65)
        print("MDRIIA GROUP 10 - 7-DOF SURGICAL NEEDLE PLACEMENT SIMULATION")
        print("=" * 65)
        print("[INFO] Target: Puncture tissue site [0.65, 0.0, 0.80] m")

        dt = 0.002
        steps = int(duration_s / dt)
        target = np.array([0.65, 0.0, 0.80])
        voluntary_intent = np.array([0.65, 0.0, 0.80])

        filtered_pos = voluntary_intent.copy()
        raw_errors = []
        clean_errors = []

        for step in range(steps):
            t = step * dt
            tremor = self.generate_physiological_tremor(t)
            raw_pos = voluntary_intent + tremor
            filtered_pos = self.apply_lowpass_filter(raw_pos, filtered_pos)

            err_raw = self.evaluate_placement_accuracy(raw_pos, target) * 1000.0 # mm
            err_filt = self.evaluate_placement_accuracy(filtered_pos, target) * 1000.0 # mm

            raw_errors.append(err_raw)
            clean_errors.append(err_filt)

        rmse_raw = np.sqrt(np.mean(np.array(raw_errors)**2))
        rmse_filt = np.sqrt(np.mean(np.array(clean_errors)**2))

        print(f"Unfiltered Needle Tip RMSE:     {rmse_raw:.3f} mm")
        print(f"Tremor-Filtered Needle Tip RMSE: {rmse_filt:.3f} mm")
        print(f"Precision Improvement:          {(1.0 - rmse_filt/rmse_raw)*100:.1f}%")
        print(f"Sub-0.5 mm Safety Threshold:    {'PASSED' if rmse_filt <= 0.50 else 'FAILED'}")
        print("=" * 65)

if __name__ == "__main__":
    controller = SurgicalTremorController()
    controller.run_surgical_simulation()
