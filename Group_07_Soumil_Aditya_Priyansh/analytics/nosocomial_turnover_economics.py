# Hospital Room Turnaround & Nosocomial Cleaning Economics
# CSBS Operational Optimization Model (Zero Currency Symbols)
# Group: MDRIIA Group 07

import math
import numpy as np

def compute_turnaround_economics():
    """
    CSBS Technoeconomic Analysis
    Evaluates patient-room turnaround time reduction, expanded bed capacity,
    and dimensionless OpEx payback horizon.
    """
    # Operational Turnaround Baselines (Minutes per room)
    t_manual_baseline = 15.2        # Standard housekeeping turnaround
    t_clutter_clearing_manual = 5.2 # Time spent sorting clutter by hand
    t_terminal_disinfect = 10.0     # Time spent on high-touch clinical disinfection
    
    # Autonomous Clearing Performance
    t_clutter_clearing_robot = 2.1  # Autonomous mobile manipulator clearing
    # Disinfection begins in parallel with linen staging
    t_turnaround_robot = t_clutter_clearing_robot + (t_terminal_disinfect * 0.65) # Focused protocol
    
    delta_turnaround_min = t_manual_baseline - t_turnaround_robot
    turnaround_acceleration_pct = (delta_turnaround_min / t_manual_baseline) * 100.0

    # Ward Capacity Impact (30-bed surgical/medical ward)
    beds_per_ward = 30
    daily_discharges_per_ward = 7.5
    hours_saved_daily_ward = (daily_discharges_per_ward * delta_turnaround_min) / 60.0
    annual_bed_hours_reclaimed = hours_saved_daily_ward * 365.0

    # Dimensionless Operational Cost Parity (Kappa)
    # Manual housekeeping OpEx normalized to 1.00
    c_manual_opex = 1.00
    c_robot_maintenance = 0.16
    c_robot_energy_supervision = 0.12
    c_robot_total_opex = c_robot_maintenance + c_robot_energy_supervision
    kappa = c_robot_total_opex / c_manual_opex  # 0.28
    
    # Capital Investment Amortization Horizon
    k_capex_normalized = 0.58  # Mobile manipulator capital cost normalized to annual labor
    annual_opex_savings = 1.0 - kappa  # 0.72
    payback_years = k_capex_normalized / annual_opex_savings
    payback_months = payback_years * 12.0

    print("=" * 65)
    print("MDRIIA GROUP 07 - HOSPITAL ROOM TURNAROUND & ECONOMIC METRICS")
    print("=" * 65)
    print(f"Manual Baseline Turnaround:         {t_manual_baseline:.1f} min/room")
    print(f"Autonomous-Assisted Turnaround:     {t_turnaround_robot:.1f} min/room")
    print(f"Turnaround Time Reduction:          {turnaround_acceleration_pct:.1f}% ({delta_turnaround_min:.1f} min saved)")
    print(f"Daily Ward Labor Reclaimed:         {hours_saved_daily_ward:.2f} hours/day")
    print(f"Annual Ward Bed-Hours Unlocked:     {annual_bed_hours_reclaimed:.1f} bed-hours/year")
    print(f"Operational Cost Parity (Kappa):    {kappa:.2f} (72.0% annual OpEx advantage)")
    print(f"Dimensionless Payback Horizon:      {payback_months:.1f} months ({payback_years:.2f} years)")
    print("=" * 65)

if __name__ == "__main__":
    compute_turnaround_economics()
