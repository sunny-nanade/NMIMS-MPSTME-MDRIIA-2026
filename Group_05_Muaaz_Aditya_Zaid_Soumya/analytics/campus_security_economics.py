# CSBS Campus Security Operations & OpEx Payback Optimization
# Strictly Dimensionless Formulation (Zero Currency Symbols)
# Group: MDRIIA Group 05

import math
import numpy as np

def compute_security_operations_economics():
    """
    CSBS Security Operations Formulation
    Evaluates patrol speedup, guard labor reallocation, and dimensionless OpEx payback
    """
    t_guard_patrol_min = 48.72
    t_dual_uav_patrol_min = 7.84
    
    # Speedup ratio
    speedup = t_guard_patrol_min / t_dual_uav_patrol_min
    cycle_time_reduction_pct = (1.0 - (t_dual_uav_patrol_min / t_guard_patrol_min)) * 100.0
    
    # Guard labor reallocation
    total_guard_shift_hours_per_day = 72.0  # 3 shifts of 3 guards (8 hrs each)
    reallocated_hours_per_day = 50.4        # 70% of walking hours reallocated
    labor_reallocation_pct = (reallocated_hours_per_day / total_guard_shift_hours_per_day) * 100.0
    
    # Dimensionless OpEx payback model
    # Baseline manual security cost normalized to 1.00
    c_baseline = 1.00
    c_hybrid = 0.66  # Hybrid autonomous aerial + human response team
    delta_opex_annual = c_baseline - c_hybrid  # 0.34 annual saving
    
    k_capex_normalized = 0.31  # Dual-UAV airframe, base station, and compute setup
    payback_years = k_capex_normalized / delta_opex_annual
    payback_months = payback_years * 12.0
    
    # Blind-spot coverage suppression
    blind_spot_baseline_pct = 35.8
    blind_spot_uav_pct = 1.2
    blind_spot_reduction_pct = ((blind_spot_baseline_pct - blind_spot_uav_pct) / blind_spot_baseline_pct) * 100.0
    
    print("=" * 65)
    print("MDRIIA GROUP 05 - CAMPUS SECURITY OPERATIONS & ECONOMIC OPTIMIZATION")
    print("=" * 65)
    print(f"Manual Guard Patrol Cycle Time:    {t_guard_patrol_min:.2f} minutes")
    print(f"Collaborative Dual-UAV Cycle Time: {t_dual_uav_patrol_min:.2f} minutes")
    print(f"Patrol Cycle Speedup Ratio:        {speedup:.2f}x faster ({cycle_time_reduction_pct:.1f}% reduction)")
    print(f"Guard Labor Reallocated to Interv.: {labor_reallocation_pct:.1f}% ({reallocated_hours_per_day:.1f} hrs/day)")
    print(f"Perimeter Blind-Spot Reduction:    {blind_spot_reduction_pct:.1f}% (down to {blind_spot_uav_pct:.1f}%)")
    print(f"Normalized Annual OpEx Advantage:  {delta_opex_annual:.2f} relative cost parity")
    print(f"Dimensionless Payback Horizon:     {payback_months:.2f} months ({payback_years:.3f} years)")
    print("=" * 65)

if __name__ == "__main__":
    compute_security_operations_economics()
