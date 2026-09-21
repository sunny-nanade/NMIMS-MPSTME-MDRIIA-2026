# Closed-Loop Navigation and Telemetry Controller
# Autonomous Last-Mile Ground AED Delivery Robot
# Group: MDRIIA Group 03

import os
import sys
import math
import numpy as np

class AEDDeliveryController:
    """
    Autonomous Navigation, Curb-Climbing, and Telemetry Controller
    Student Implementation Boundaries:
    - E026 (Kashish): Suspension dynamics, vertical shock limiters, and wheel normal force balancing
    - E046 (Vaishnavi): Path planning, pedestrian obstacle avoidance, and curb torque vectoring
    - E057 (Daneeka): Clinical survival decay estimation and telemetry logging
    """
    def __init__(self, target_distance_m=1800.0):
        self.target_dist = target_distance_m
        self.cruise_speed_mps = 3.5
        self.curb_speed_mps = 1.2
        self.max_shock_g = 3.0
        self.traversed_dist = 0.0
        self.current_time_s = 0.0
        
        # Telemetry history buffer
        self.telemetry = {
            "time_s": [],
            "distance_m": [],
            "velocity_mps": [],
            "payload_accel_g": [],
            "curb_impact_force_N": [],
            "survival_prob": []
        }

    def compute_apf_forces(self, current_pos, goal_pos, obstacle_positions):
        """
        # TODO [E046 - Vaishnavi Parashar]:
        Implement the Artificial Potential Field (APF) obstacle avoidance routine.
        - Calculate attractive gradient toward goal_pos
        - Calculate repulsive gradient for each obstacle within 2.5 m influence radius
        - Apply Weinberg et al. (2023) sidewalk corridor lateral boundaries (0.6 m - 1.2 m)
        """
        # Baseline stub: direct forward vector
        delta = np.array(goal_pos) - np.array(current_pos)
        dist = np.linalg.norm(delta)
        if dist > 0.01:
            unit_heading = delta / dist
        else:
            unit_heading = np.array([1.0, 0.0])
        return unit_heading

    def curb_climbing_torque_vectoring(self, wheel_contact_flags, pitch_angle_rad):
        """
        # TODO [E026 - Kashish Praveen Jain]:
        Implement dynamic torque vectoring for 12 cm vertical curb climbing.
        - Detect front wheel curb impact from contact flags
        - Reduce vehicle speed to curb_speed_mps (1.2 m/s) to attenuate impact shock
        - Boost front actuator torque proportionally to pitch angle to overcome curb lip
        - Restrict roll angle to |phi| <= 18 deg to prevent vehicle rollover
        """
        # Baseline stub: constant torque limit
        base_torque = 80.0
        if any(wheel_contact_flags):
            return base_torque * 1.5
        return base_torque

    def evaluate_larsen_survival(self, transit_time_min, cpr_delay_min=1.0):
        """
        # TODO [E057 - Daneeka Abhijeet Roy]:
        Implement the Larsen et al. (1993) resuscitation survival probability formulation.
        Formula: P(survival) = 0.67 - 0.023 * t_CPR - 0.046 * t_defib
        Bound output probability in range [0.05, 0.70].
        """
        # Baseline implementation
        p_survival = 0.67 - (0.023 * cpr_delay_min) - (0.046 * transit_time_min)
        return float(np.clip(p_survival, 0.05, 0.70))

    def step_simulation(self, dt=0.01):
        """Execute a single simulation step and log telemetry."""
        self.current_time_s += dt
        
        # Determine speed based on route progress (curbs at 500 m and 1200 m)
        is_curb_zone = (495.0 <= self.traversed_dist <= 505.0) or (1195.0 <= self.traversed_dist <= 1205.0)
        target_v = self.curb_speed_mps if is_curb_zone else self.cruise_speed_mps
        
        self.traversed_dist += target_v * dt
        
        # Simulate payload shock acceleration
        if is_curb_zone:
            shock_g = 2.68 + np.random.normal(0, 0.08)
            curb_force = 1250.0 + np.random.normal(0, 50.0)
        else:
            shock_g = 0.45 + np.random.normal(0, 0.03)
            curb_force = 0.0
            
        t_min = self.current_time_s / 60.0
        survival_prob = self.evaluate_larsen_survival(t_min)
        
        # Log to buffer
        self.telemetry["time_s"].append(round(self.current_time_s, 2))
        self.telemetry["distance_m"].append(round(self.traversed_dist, 2))
        self.telemetry["velocity_mps"].append(round(target_v, 2))
        self.telemetry["payload_accel_g"].append(round(shock_g, 3))
        self.telemetry["curb_impact_force_N"].append(round(curb_force, 1))
        self.telemetry["survival_prob"].append(round(survival_prob, 4))
        
        return self.traversed_dist >= self.target_dist

def main():
    print("=" * 60)
    print("Starting Autonomous Ground AED Delivery Controller Test Run...")
    print("=" * 60)
    controller = AEDDeliveryController(target_distance_m=1800.0)
    
    done = False
    while not done and controller.current_time_s < 600.0:
        done = controller.step_simulation(dt=0.05)
        
    final_time_min = controller.current_time_s / 60.0
    final_p = controller.telemetry["survival_prob"][-1]
    
    print(f"Mission Completed in: {final_time_min:.2f} minutes ({controller.current_time_s:.1f} s)")
    print(f"Total Traversed Distance: {controller.traversed_dist:.1f} m")
    print(f"Predicted Patient Survival Probability: {final_p*100:.2f}%")
    print("=" * 60)

if __name__ == "__main__":
    main()
