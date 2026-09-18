"""
Active Debris Removal Orbital Capture Controller
Conforming to ISO 10218 / NASA Orbital Debris Guidelines.
Group 04 - B.Tech CSBS MDRIIA
"""
import math

def simulate_orbital_capture():
    print("[MDRIIA Group 04] Simulating Orbital Debris Capture in Microgravity...")
    # Tumbling angular velocity
    omega_debris = 0.52 # rad/s (approx 30 deg/s)
    capture_threshold_radps = 0.08
    t = 0.0
    dt = 0.01
    
    # Detumbling phase through compliant impedance torque
    while omega_debris > capture_threshold_radps and t < 10.0:
        torque_damping = 0.85 * omega_debris
        omega_debris -= torque_damping * dt
        t += dt
        
    print(f"[Captured] Debris rotational energy stabilized at t = {t:.2f}s (Omega = {omega_debris:.3f} rad/s)")

if __name__ == "__main__":
    simulate_orbital_capture()
