# Flood Disaster Relief Logistics & Fleet Cost-Parity Analytics
# CSBS Operational Optimization Model (Zero Currency Symbols)
# Group: MDRIIA Group 08

import math
import numpy as np

def compute_disaster_logistics_economics():
    """
    CSBS Technoeconomic Analysis
    Compares aerial UAV rapid response vs conventional motorized flood relief boats.
    Evaluates response latency reduction, dispatch throughput, and dimensionless payback horizon.
    """
    # Mission Geography Parameters (Flooded Urban / Semi-Urban District)
    mean_transit_distance_km = 8.5 # Distance from central relief staging hub to isolated sector
    
    # 1. Surface Motorized Boat Convoys
    v_boat_kmh = 7.2              # Severely slowed by submerged debris, downed powerlines
    t_boat_launch_prep_min = 35.0  # Launch staging and navigating debris channels
    t_boat_transit_one_way_min = (mean_transit_distance_km / v_boat_kmh) * 60.0
    t_boat_total_response_min = t_boat_launch_prep_min + t_boat_transit_one_way_min
    
    # 2. Autonomous Multirotor UAV Platform
    v_uav_kmh = 45.0              # Direct straight-line aerial corridor
    t_uav_launch_prep_min = 4.0   # Automated pre-flight telemetry check
    t_uav_transit_one_way_min = (mean_transit_distance_km / v_uav_kmh) * 60.0
    t_uav_delivery_winch_min = 2.5 # Visual hovering and winch deployment
    t_uav_total_response_min = t_uav_launch_prep_min + t_uav_transit_one_way_min + t_uav_delivery_winch_min
    
    # Response Time Acceleration
    time_saved_per_sortie_min = t_boat_total_response_min - t_uav_total_response_min
    acceleration_pct = (time_saved_per_sortie_min / t_boat_total_response_min) * 100.0
    
    # 3. Daily Fleet Capacity (12-Hour Operational Window)
    daily_sorties_boat = 12.0 / (t_boat_total_response_min / 60.0 * 2.0) # Round trip
    daily_sorties_uav = 12.0 / ((t_uav_transit_one_way_min * 2.0 + 20.0) / 60.0) # Including battery swap
    throughput_multiplier = daily_sorties_uav / daily_sorties_boat
    
    # 4. Dimensionless Fleet Cost Parity (Kappa)
    # Conventional boat operation normalized to 1.00
    c_boat_opex = 1.00
    c_uav_recharging = 0.08
    c_uav_battery_wear = 0.15
    c_uav_field_supervision = 0.08
    c_uav_total_opex = c_uav_recharging + c_uav_battery_wear + c_uav_field_supervision
    kappa = c_uav_total_opex / c_boat_opex # 0.31
    
    # Amortization Payback Horizon
    k_capex_fleet = 0.45 # Fleet capital cost normalized to seasonal emergency boat lease
    annual_opex_savings = 1.0 - kappa # 0.69
    payback_years = k_capex_fleet / annual_opex_savings
    payback_months = payback_years * 12.0

    print("=" * 65)
    print("MDRIIA GROUP 08 - FLOOD RELIEF LOGISTICS & FLEET ECONOMICS")
    print("=" * 65)
    print(f"Mean Dispatch Corridor:             {mean_transit_distance_km:.1f} km")
    print(f"Boat Convoy Response Time:          {t_boat_total_response_min:.1f} minutes")
    print(f"Autonomous UAV Response Time:       {t_uav_total_response_min:.1f} minutes")
    print(f"Response Latency Reduction:         {acceleration_pct:.1f}% ({time_saved_per_sortie_min:.1f} min saved)")
    print(f"Daily Sorties Delivered per Unit:   UAV: {daily_sorties_uav:.1f} vs Boat: {daily_sorties_boat:.1f}")
    print(f"Relief Throughput Expansion:        {throughput_multiplier:.2f}x sorties per operational shift")
    print(f"Operational Cost Parity (Kappa):    {kappa:.2f} (69.0% operational cost advantage)")
    print(f"Dimensionless Payback Horizon:      {payback_months:.1f} operational months ({payback_years:.2f} years)")
    print("=" * 65)

if __name__ == "__main__":
    compute_disaster_logistics_economics()
