"""
Rapid Dispatch & Time-to-First-Shock Simulation
Group 03 - B.Tech CSBS MDRIIA
"""
import math

def simulate_aed_dispatch():
    print("[MDRIIA Group 03] Simulating Urban Ground AED Dispatch...")
    dist_km = 1.8
    urban_traffic_speed_kmh = 8.5 # Congested ambulance
    amr_sidewalk_speed_kmh = 22.0 # Autonomous sidewalk/bike-lane vehicle
    
    t_ambulance_min = (dist_km / urban_traffic_speed_kmh) * 60.0
    t_amr_min = (dist_km / amr_sidewalk_speed_kmh) * 60.0 + 0.5 # Dispatch delay
    
    # AHA Survival Model: 10% drop per minute without defibrillation
    def survival_prob(t_min):
        return max(0.05, 0.70 * math.exp(-0.09 * t_min))
        
    p_ambulance = survival_prob(t_ambulance_min)
    p_amr = survival_prob(t_amr_min)
    
    print(f"Ambulance Arrival Time: {t_ambulance_min:.2f} min -> Survival Probability: {p_ambulance*100:.1f}%")
    print(f"Autonomous AMR Arrival:  {t_amr_min:.2f} min -> Survival Probability: {p_amr*100:.1f}%")
    print(f"Absolute Survival Gain: +{(p_amr - p_ambulance)*100:.1f}% percentage points")

if __name__ == "__main__":
    simulate_aed_dispatch()
