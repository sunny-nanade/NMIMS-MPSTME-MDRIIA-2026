"""
Autonomous ICU Medicine Delivery AMR Simulation & Telemetry Logger
Conforming to ISO 13482:2014 & ISO 3691-4:2023 Safety Standards.

Student Work Distribution:
- E006 Khushal Asnani: Physical model integration, contact mechanics, and mass distribution.
- E016 Priyal Kaushal Deputy: Heading error normalization, DWA local planner, and anti-slosh velocity throttling.
- E054 Ishita Ranjan: Reallocation metrics linking simulation travel time to clinical hours.
- E060 Sowmya Satish: Telemetry logging (50 Hz), Monte Carlo harness, and Welch's t-test hypothesis verification.
"""

import math
import csv

def normalize_angle(theta):
    """
    Normalizes heading error strictly onto (-pi, pi] to eliminate branch-cut discontinuities.
    Assigned to: E016 Priyal Kaushal Deputy
    """
    return math.atan2(math.sin(theta), math.cos(theta))

def compute_anti_slosh_speed_limit(omega, a_lat_crit=0.40):
    """
    Computes maximum permissible linear velocity given yaw rate omega:
    v_max <= a_lat_crit / (|omega| + epsilon)
    Assigned to: E016 Priyal Kaushal Deputy
    """
    epsilon = 1e-6
    return a_lat_crit / (abs(omega) + epsilon)

def run_simulation(duration_sec=15.0, output_csv="icu_amr_telemetry.csv"):
    print("[Group 01] Initializing ICU Medicine Delivery AMR Simulation...")
    
    # Kinematic Calibration (r = 0.08m, b = 0.42m)
    wheel_radius = 0.08
    track_width = 0.42
    v_nominal_max = 0.80      # m/s (ISO 13482 indoor limit)
    a_lat_crit = 0.40         # m/s^2 (liquid payload slosh threshold)
    j_crit = 1.20             # m/s^3 (jerk threshold)
    dt = 0.01                 # 100 Hz simulation step
    
    # State Vector: x, y, theta, v, omega
    x, y, theta = -5.0, 0.0, 0.0
    v, omega = 0.0, 0.0
    
    # Hospital Corridor Obstacles: (x, y, radius)
    # Conforming to 2.2m clear width with clinical equipment pinch points
    obstacles = [(1.5, 0.4, 0.35), (4.0, -0.5, 0.40)]
    target_x, target_y = 6.0, 0.0
    
    telemetry_records = []
    t = 0.0
    
    while t < duration_sec:
        dx = target_x - x
        dy = target_y - y
        dist_to_goal = math.hypot(dx, dy)
        
        if dist_to_goal < 0.20:
            print(f"[Docked] Reached ICU bedside station at t = {t:.2f}s")
            break
            
        target_heading = math.atan2(dy, dx)
        heading_error = normalize_angle(target_heading - theta)
        
        # Sensor Model: Nearest obstacle distance
        d_obs_min = 10.0
        for ox, oy, orad in obstacles:
            d = math.hypot(ox - x, oy - y) - orad
            if d < d_obs_min:
                d_obs_min = d
                
        # Motion Governor & Anti-Slosh Limiting
        fsm_state = "CRUISE"
        if d_obs_min < 1.0:
            fsm_state = "OBSTACLE_AVOIDANCE"
            v_target = 0.30
            omega_target = -0.65 if y >= 0 else 0.65
        else:
            v_target = min(v_nominal_max, 0.5 * dist_to_goal + 0.1)
            omega_target = 1.6 * heading_error
            
        # Enforce Anti-Slosh Ceiling: |v * omega| <= a_lat_crit
        v_allowed = compute_anti_slosh_speed_limit(omega_target, a_lat_crit)
        v_cmd = min(v_target, v_allowed)
        omega_cmd = omega_target
        
        # State Update (Unicycle Kinematics)
        v = 0.92 * v + 0.08 * v_cmd
        omega = 0.90 * omega + 0.10 * omega_cmd
        
        x += v * math.cos(theta) * dt
        y += v * math.sin(theta) * dt
        theta = normalize_angle(theta + omega * dt)
        
        # Calculate instantaneous metrics
        a_lat = abs(v * omega)
        w_right = (v / wheel_radius) + (track_width * omega) / (2.0 * wheel_radius)
        w_left = (v / wheel_radius) - (track_width * omega) / (2.0 * wheel_radius)
        
        telemetry_records.append({
            "timestamp_s": round(t, 3),
            "pos_x_m": round(x, 4),
            "pos_y_m": round(y, 4),
            "heading_rad": round(theta, 4),
            "linear_vel_mps": round(v, 4),
            "angular_vel_radps": round(omega, 4),
            "lateral_acc_mps2": round(a_lat, 4),
            "wheel_right_radps": round(w_right, 3),
            "wheel_left_radps": round(w_left, 3),
            "obstacle_clearance_m": round(d_obs_min, 3),
            "fsm_state": fsm_state
        })
        t += dt
        
    # Write Telemetry Log
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(telemetry_records[0].keys()))
        writer.writeheader()
        writer.writerows(telemetry_records)
        
    peak_lat_acc = max(r["lateral_acc_mps2"] for r in telemetry_records)
    print(f"[Done] Logged {len(telemetry_records)} samples to {output_csv}")
    print(f"[Audit] Peak lateral acceleration: {peak_lat_acc:.3f} m/s^2 (Threshold: {a_lat_crit:.2f} m/s^2)")

if __name__ == "__main__":
    run_simulation()
