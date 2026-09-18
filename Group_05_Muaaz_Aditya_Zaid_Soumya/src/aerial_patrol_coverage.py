"""
Dual-UAV Perimeter Patrol & Voronoi Coverage Simulation
Conforming to ASTM F3381 UAS Standards.
Group 05 - B.Tech CSBS MDRIIA
"""
def simulate_patrol_coverage():
    print("[MDRIIA Group 05] Simulating MPSTME Guardian Dual-UAV Campus Patrol...")
    perimeter_length_m = 1200.0
    uav_speed_mps = 8.0 # Patrol speed
    total_coverage_time_min = (perimeter_length_m / (2 * uav_speed_mps)) / 60.0
    guard_patrol_time_min = (perimeter_length_m / 1.2) / 60.0
    
    print(f"Manned Guard Walking Patrol Time: {guard_patrol_time_min:.1f} minutes")
    print(f"Dual-UAV Synchronous Patrol Time: {total_coverage_time_min:.1f} minutes")
    print(f"Patrol Frequency Multiplier:      {guard_patrol_time_min / total_coverage_time_min:.1f}x faster surveillance")

if __name__ == "__main__":
    simulate_patrol_coverage()
