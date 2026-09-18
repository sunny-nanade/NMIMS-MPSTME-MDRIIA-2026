# CSBS Photovoltaic Degradation & LCOE Payback Optimization
# Strictly Dimensionless Formulation (Zero Currency Symbols)
# Group: MDRIIA Group 06

import math
import numpy as np

def compute_photovoltaic_economics():
    """
    CSBS Solar Economics Formulation
    Evaluates power loss recovery, water abatement, and dimensionless OpEx payback
    """
    monthly_soiling_loss_pct = 16.8
    restored_power_pct = 16.2
    
    # Water resource savings
    water_use_manual_L_per_m2 = 4.20
    water_use_robot_L_per_m2 = 0.00
    water_abatement_pct = 100.0
    
    # Dimensionless OpEx payback model
    # Contracted manual cleaning OpEx normalized to 1.00
    c_manual_opex = 1.00
    c_crawler_opex = 0.28  # Power + brush replacement wear
    delta_opex_annual = c_manual_opex - c_crawler_opex  # 0.72 annual saving
    
    k_capex_normalized = 0.65  # Normalized capital cost of crawler unit
    payback_years = k_capex_normalized / delta_opex_annual
    payback_months = payback_years * 12.0
    
    # Energy yield multiplier
    generation_multiplier = 1.0 / (1.0 - (restored_power_pct / 100.0))
    
    print("=" * 65)
    print("MDRIIA GROUP 06 - PV DEGRADATION & LCOE PAYBACK OPTIMIZATION")
    print("=" * 65)
    print(f"Monthly Soiling Generation Loss:   {monthly_soiling_loss_pct:.1f}%")
    print(f"Autonomous Restored Generation:    +{restored_power_pct:.1f}% generation recovery")
    print(f"Energy Yield Multiplier:           {generation_multiplier:.3f}x baseline soiled array")
    print(f"Water Abatement Efficiency:        {water_abatement_pct:.1f}% (saves {water_use_manual_L_per_m2:.1f} L/m^2)")
    print(f"Normalized Annual OpEx Advantage:  {delta_opex_annual:.2f} relative cost parity")
    print(f"Dimensionless Payback Horizon:     {payback_months:.2f} months ({payback_years:.3f} years)")
    print("=" * 65)

if __name__ == "__main__":
    compute_photovoltaic_economics()
