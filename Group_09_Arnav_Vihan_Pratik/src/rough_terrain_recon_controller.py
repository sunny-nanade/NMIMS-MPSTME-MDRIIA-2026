# Autonomous Hazardous Terrain UGV Navigation Controller
# Group: MDRIIA Group 09
# Incorporates Pedagogical Student Task Boundaries (TODO Tags)

import math
import numpy as np

class HazardousTerrainUGVController:
    """
    Skid-Steer UGV Traversability Cost Mapping & Shared Autonomy Controller
    """
    def __init__(self):
        # UGV Kinematic Parameters
        self.track_width = 0.64   # m
        self.wheel_radius = 0.14  # m
        self.max_linear_speed = 1.2 # m/s
        self.max_angular_speed = 1.8 # rad/s

        # Position State
        self.pos = np.array([0.0, 0.0, 0.22])
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0

        # Shared Autonomy Latency Buffer
        self.latency_seconds = 0.35 # 350 ms simulated delay

    def compute_skid_steer_torques(self, v_linear, omega_angular):
        """
        Student Task Boundary - Arnav Saurabh Surve (E064)
        # TODO [E064 - Arnav Saurabh Surve]:
        # Implement instantaneous centers of rotation (ICR) skid-steer torque conversion:
        # omega_L = (v - omega * track_width / 2) / wheel_radius
        # omega_R = (v + omega * track_width / 2) / wheel_radius
        """
        omega_l = (v_linear - (omega_angular * self.track_width / 2.0)) / self.wheel_radius
        omega_r = (v_linear + (omega_angular * self.track_width / 2.0)) / self.wheel_radius
        return omega_l, omega_r

    def compute_traversability_cost(self, slope_deg, roughness_std, step_height_m):
        """
        Student Task Boundary - Vihan Shripad Joshi (E070)
        # TODO [E070 - Vihan Shripad Joshi]:
        # Implement 2.5D multi-criteria cost fusion:
        # C_trav = w_slope * (slope/slope_max) + w_rough * (rough/rough_max) + w_step * (step/step_max)
        """
        c_slope = min(1.0, slope_deg / 25.0)
        c_rough = min(1.0, roughness_std / 0.08)
        c_step = min(1.0, step_height_m / 0.15)
        composite_cost = 0.40 * c_slope + 0.30 * c_rough + 0.30 * c_step
        return composite_cost

    def evaluate_shared_autonomy_override(self, teleop_v, teleop_omega, forward_cost):
        """
        Student Task Boundary - Pratik Mangesh Gaikwad (E073)
        # TODO [E073 - Pratik Mangesh Gaikwad]:
        # Implement shared autonomy velocity attenuation:
        # If forward_cost > 0.65 (impassable rubble), scale down linear velocity
        # and steer towards lower gradient to prevent vehicle rollover.
        """
        if forward_cost > 0.65:
            # Autonomous safety override
            safe_v = teleop_v * 0.20
            safe_omega = teleop_omega + 0.45 * np.sign(teleop_omega if teleop_omega != 0 else 1.0)
            return safe_v, safe_omega, True
        return teleop_v, teleop_omega, False

    def run_reconnaissance_demonstration(self, num_waypoints=8):
        print("=" * 65)
        print("MDRIIA GROUP 09 - HAZARDOUS TERRAIN RECONNAISSANCE PIPELINE")
        print("=" * 65)
        print(f"[INFO] Initializing skid-steer UGV in rubble test environment...")
        print(f"[INFO] Simulated teleoperation network delay: {self.latency_seconds * 1000:.0f} ms.")

        traversed = 0
        total_time = 0.0

        for wp in range(1, num_waypoints + 1):
            slope = np.random.uniform(2.0, 22.0)
            roughness = np.random.uniform(0.01, 0.07)
            step_h = np.random.uniform(0.02, 0.14)
            cost = self.compute_traversability_cost(slope, roughness, step_h)

            cmd_v, cmd_w = 0.8, 0.0
            safe_v, safe_w, overridden = self.evaluate_shared_autonomy_override(cmd_v, cmd_w, cost)

            step_dt = 3.2 if not overridden else 5.4
            total_time += step_dt
            traversed += 1

            status = "AUTONOMOUS_OVERRIDE" if overridden else "OPERATOR_TRACKING"
            print(f"  WP {wp:02d}: Cost={cost:.2f} (Slope={slope:.1f} deg) -> {status} (v={safe_v:.2f} m/s)")

        print("-" * 65)
        print(f"Summary: Reached {traversed}/{num_waypoints} checkpoints in {total_time:.1f} s.")
        print("=" * 65)

if __name__ == "__main__":
    controller = HazardousTerrainUGVController()
    controller.run_reconnaissance_demonstration()
