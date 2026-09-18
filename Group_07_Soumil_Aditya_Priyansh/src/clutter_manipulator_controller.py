# Autonomous Mobile Manipulator Clutter Clearing Controller
# Group: MDRIIA Group 07
# Incorporates Pedagogical Student Task Boundaries (TODO Tags)

import math
import numpy as np

class HospitalMobileManipulatorController:
    """
    Autonomous Mobile Manipulator Clutter Clearing State Machine
    Simulates base approach, arm reaching, antipodal grasp, and disposal.
    """
    def __init__(self):
        # State Machine Definitions
        self.STATE_IDLE = 0
        self.STATE_APPROACH_BASE = 1
        self.STATE_REACH_ARM = 2
        self.STATE_CLOSE_GRIPPER = 3
        self.STATE_LIFT_OBJECT = 4
        self.STATE_DEPOSIT_BIN = 5
        self.current_state = self.STATE_IDLE

        # Damped Least Squares IK Parameters
        self.damping_lambda = 0.05
        self.kp_pos = 4.0

        # Telemetry Store
        self.cycle_times = []
        self.grasp_successes = []

    def compute_base_navigation(self, current_pos, target_pos):
        """
        Student Task Boundary - Soumil Patro (E050)
        # TODO [E050 - Soumil Patro]:
        # Implement potential field or differential drive waypoint controller
        # to navigate mobile base from current (x, y, yaw) to bedside approach pose.
        """
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        dist = math.hypot(dx, dy)
        target_yaw = math.atan2(dy, dx)
        return dist, target_yaw

    def compute_damped_ik(self, target_ee_pos, current_ee_pos, current_joint_angles):
        """
        Student Task Boundary - Aditya Raju Shah (E062)
        # TODO [E062 - Aditya Raju Shah]:
        # Complete full 5-joint Jacobian matrix evaluation and Levenberg-Marquardt
        # damped least squares calculation: dq = J^T (J J^T + lambda^2 I)^(-1) dx
        """
        err = np.array(target_ee_pos) - np.array(current_ee_pos)
        # Placeholder proportional step towards target
        delta_q = err * 0.25
        return delta_q

    def execute_clearing_cycle(self, object_id, object_pos, bin_pos):
        """
        Execute one full pick-and-place clearing cycle
        """
        self.current_state = self.STATE_APPROACH_BASE
        # Step 1: Base moves within 0.85m of target
        base_dist, _ = self.compute_base_navigation([0.0, 0.0], object_pos[:2])

        # Step 2: Arm reaches towards clutter centroid
        self.current_state = self.STATE_REACH_ARM
        reach_dq = self.compute_damped_ik(object_pos, [0.8, 0.0, 0.7], [0.0]*5)

        # Step 3: Gripper actuation & prehension check
        self.current_state = self.STATE_CLOSE_GRIPPER
        grasp_prob = 0.92  # Analytical grasp success probability
        success = np.random.rand() < grasp_prob

        # Step 4: Deposit in waste receptacle
        self.current_state = self.STATE_DEPOSIT_BIN
        cycle_duration = np.random.normal(28.5, 3.2)

        self.cycle_times.append(cycle_duration)
        self.grasp_successes.append(success)
        return success, cycle_duration

    def run_demonstration(self, num_items=6):
        print("=" * 65)
        print("MDRIIA GROUP 07 - AUTONOMOUS CLUTTER CLEARING PIPELINE")
        print("=" * 65)
        print(f"[INFO] Initializing mobile manipulator in hospital room scenario...")
        print(f"[INFO] Identified {num_items} bedside clutter objects for clearing.")

        cleared = 0
        total_time = 0.0
        for i in range(1, num_items + 1):
            obj_pos = [1.15 + np.random.uniform(-0.1, 0.1), 
                       -0.2 + (i * 0.1), 
                       0.78]
            succ, dt = self.execute_clearing_cycle(i, obj_pos, [0.4, 0.8, 0.25])
            total_time += dt
            if succ:
                cleared += 1
                status = "SUCCESS"
            else:
                status = "SLIP_REATTEMPT"
            print(f"  Item {i:02d}: {status} (Cycle: {dt:.1f} s, Cumulative: {total_time:.1f} s)")

        print("-" * 65)
        print(f"Summary: Cleared {cleared}/{num_items} items ({cleared/num_items*100:.1f}%) in {total_time/60.0:.2f} minutes.")
        print("=" * 65)

if __name__ == "__main__":
    controller = HospitalMobileManipulatorController()
    controller.run_demonstration(num_items=6)
