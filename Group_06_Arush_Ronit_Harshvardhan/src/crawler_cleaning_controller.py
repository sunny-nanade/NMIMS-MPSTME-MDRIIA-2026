"""
Waterless Solar Panel Cleaning Crawler Simulation
Group 06 - B.Tech CSBS MDRIIA
"""
def simulate_solar_cleaning():
    print("[MDRIIA Group 06] Simulating Photovoltaic Crawler Operation...")
    panel_area_m2 = 450.0
    crawler_speed_mps = 0.15
    cleaning_swath_m = 0.50
    
    rate_m2_per_min = crawler_speed_mps * cleaning_swath_m * 60.0
    total_time_min = panel_area_m2 / rate_m2_per_min
    
    # Soiling restoration: 18.5% power loss restored
    efficiency_gain = 0.185
    print(f"Total Array Area:     {panel_area_m2:.1f} m^2")
    print(f"Cleaning Rate:        {rate_m2_per_min:.2f} m^2/min")
    print(f"Total Cleaning Time:  {total_time_min:.1f} minutes")
    print(f"Restored Power Yield: +{efficiency_gain*100:.1f}% generation capacity")

if __name__ == "__main__":
    simulate_solar_cleaning()
