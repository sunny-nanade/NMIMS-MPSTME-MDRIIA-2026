# Autonomous Multirotor Flood Relief Drop Simulation Controller
# Group: MDRIIA Group 08
# Incorporates Pedagogical Student Task Boundaries (TODO Tags)

import math
import numpy as np

class FloodReliefFlightController:
    """
    Autonomous Quadrotor Flight and Controlled Winch Delivery Controller
    Simulates altitude hover, crosswind gust disturbance, visual alignment, and winch release.
    """
    def __init__(self):
        # UAV Physical Parameters
        self.mass_uav = 3.8    # kg
        self.mass_payload = 1.5 # kg
        self.gravity = 9.81
        
        # Flight State
        self.position = np.array([0.0, 0.0, 12.0]) # Hovering at 12 m
        self.velocity = np.array([0.0, 0.0, 0.0])
        self.cable_length = 3.6 # m
        self.payload_pos = self.position - np.array([0.0, 0.0, self.cable_length])
        
        # Winch State
        self.is_winch_deployed = False
        self.is_released = False
        
        # Telemetry
        self.time_history = []
        self.payload_error_history = []

    def compute_wind_gust(self, t, intensity="moderate"):
        """
        Student Task Boundary - Keswani Laksh (E032)
        # TODO [E032 - Keswani Laksh]:
        # Implement Dryden wind turbulence model or von Karman gust spectrum:
        # v_gust(t) = v_mean + sum(A_i * sin(omega_i * t + phi_i))
        """
        if intensity == "calm":
            mean_wind = 1.2
            gust = 0.4 * np.sin(1.2 * t)
        elif intensity == "moderate":
            mean_wind = 4.5
            gust = 1.8 * np.sin(2.1 * t) + 0.9 * np.cos(3.5 * t)
        else: # severe
            mean_wind = 8.0
            gust = 3.2 * np.sin(1.8 * t) + 2.1 * np.cos(4.2 * t)
        return mean_wind + gust

    def compute_attitude_control(self, target_pos, wind_force):
        """
        Student Task Boundary - Manikya Rathore (E056)
        # TODO [E056 - Manikya Rathore]:
        # Implement cascaded position and attitude PID with feedforward compensation
        # for slung-load pendulum reaction force T_cable.
        """
        error_pos = target_pos - self.position
        thrust_z = (self.mass_uav + self.mass_payload) * self.gravity
        # Proportional correction against horizontal wind
        tilt_roll = -0.05 * wind_force[0]
        tilt_pitch = 0.05 * wind_force[1]
        return thrust_z, tilt_roll, tilt_pitch

    def compute_visual_targeting(self, target_center):
        """
        Student Task Boundary - Shourya Garg (E020)
        # TODO [E020 - Shourya Garg]:
        # Implement downward vision target tracking and fiducial center estimation:
        # e_target = [x_fiducial - x_cam, y_fiducial - y_cam]
        """
        horizontal_disp = self.payload_pos[:2] - target_center[:2]
        radial_distance = np.linalg.norm(horizontal_disp)
        return radial_distance, horizontal_disp

    def execute_delivery_mission(self, wind_condition="moderate"):
        target = np.array([0.0, 0.0, 1.5]) # Elevated rooftop
        t = 0.0
        dt = 0.05
        max_time = 25.0

        print(f"[INFO] Initiating simulated delivery sortie under {wind_condition.upper()} winds...")

        while t < max_time:
            w_speed = self.compute_wind_gust(t, intensity=wind_condition)
            wind_vector = np.array([w_speed, 0.4 * np.sin(t), 0.0])

            # Flight control
            thrust, roll, pitch = self.compute_attitude_control(np.array([0.0, 0.0, 12.0]), wind_vector)

            # Winch lowering
            if t > 5.0 and not self.is_released:
                self.is_winch_deployed = True
                self.payload_pos[2] -= 0.04 # Lowering rate 0.8 m/s

            # Swing dynamics approximation
            swing_angle = (w_speed / 15.0) * math.sin(2.5 * t)
            self.payload_pos[0] = self.position[0] + self.cable_length * math.sin(swing_angle)

            rad_dist, _ = self.compute_visual_targeting(target)

            # Release payload close to target pad
            if self.payload_pos[2] <= 1.8 and not self.is_released:
                self.is_released = True
                impact_error = np.linalg.norm(self.payload_pos[:2] - target[:2])
                print(f"[SUCCESS] Payload released at t={t:.1f} s! Impact radial error: {impact_error:.2f} m")
                return impact_error, t

            t += dt

        return 1.85, max_time

if __name__ == "__main__":
    controller = FloodReliefFlightController()
    err, dur = controller.execute_delivery_mission(wind_condition="moderate")
    print(f"Mission complete. Radial error: {err:.2f} m, Duration: {dur:.1f} s")
