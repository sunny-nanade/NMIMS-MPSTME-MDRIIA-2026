# Cardiac Survival Health Economics & Logistics Optimization
# Strictly Dimensionless Formulation (Zero Currency Symbols)
# Group: MDRIIA Group 03

import math
import numpy as np

def compute_cardiac_survival_economics():
    """
    CSBS Health Economics Formulation
    Compares conventional roadway ambulance against autonomous ground AMR
    """
    dist_km = 1.8
    # Roadway ambulance with urban traffic congestion (Naess et al., 2024)
    v_ambulance_kmh = 7.5
    t_ambulance_min = (dist_km / v_ambulance_kmh) * 60.0 + 2.0  # + dispatch/turnout
    
    # Autonomous ground AMR traversing sidewalk corridors
    v_amr_kmh = 22.5
    t_amr_min = (dist_km / v_amr_kmh) * 60.0 + 0.3  # + automated dispatch
    
    # Larsen survival decay model: P = 0.67 - 0.023*t_CPR - 0.046*t_defib
    def larsen_p(t_defib, t_cpr=1.0):
        p = 0.67 - 0.023 * t_cpr - 0.046 * t_defib
        return max(0.05, min(0.70, p))
        
    p_ambulance = larsen_p(t_ambulance_min)
    p_amr = larsen_p(t_amr_min)
    
    # Health economics: Quality-Adjusted Life Years (QALY)
    life_expectancy_yrs = 12.0
    qol_factor = 0.85
    qaly_gain_per_case = (p_amr - p_ambulance) * life_expectancy_yrs * qol_factor
    
    # Dimensionless operational parity ratio (kappa = OpEx_AMR / OpEx_Ambulance)
    kappa = 0.095
    efficiency_gain = (1.0 - kappa) * 100.0
    payback_horizon_months = (0.35 / (1.0 - kappa)) * 12.0
    
    print("=" * 65)
    print("MDRIIA GROUP 03 - CARDIAC LOGISTICS & HEALTH ECONOMICS EVALUATION")
    print("=" * 65)
    print(f"Ambulance Congestion Response Time: {t_ambulance_min:.2f} min -> Survival: {p_ambulance*100:.1f}%")
    print(f"Autonomous Ground AMR Response Time: {t_amr_min:.2f} min -> Survival: {p_amr*100:.1f}%")
    print(f"Absolute Survival Improvement:      +{(p_amr - p_ambulance)*100:.1f}% percentage points")
    print(f"Relative Survival Multiplier:       {(p_amr / p_ambulance):.2f}x baseline")
    print(f"QALYs Preserved Per Encounter:      {qaly_gain_per_case:.2f} life-years")
    print(f"Operational Cost Parity Ratio (k):  {kappa:.3f} ({efficiency_gain:.1f}% operating advantage)")
    print(f"Amortized Payback Horizon:          {payback_horizon_months:.2f} months")
    print("=" * 65)

if __name__ == "__main__":
    compute_cardiac_survival_economics()
