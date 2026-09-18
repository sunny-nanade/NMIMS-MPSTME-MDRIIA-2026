# Surgical Clinical Precision & Operating Room Economics
# CSBS Operational Optimization Model (Zero Currency Symbols)
# Group: MDRIIA Group 10

import math
import numpy as np

def compute_surgical_economics():
    """
    CSBS Technoeconomic Analysis
    Evaluates operating room time efficiency, complication/revision reduction,
    and dimensionless capital amortization payback horizon.
    """
    # 1. Clinical Quality & Revision Mitigation
    annual_microsurgical_cases = 180.0
    baseline_revision_rate_pct = 8.2    # Percentage of cases requiring revision due to placement error
    robot_revision_rate_pct = 2.4       # Dramatic drop due to sub-0.5 mm precision
    revisions_eliminated_annually = annual_microsurgical_cases * ((baseline_revision_rate_pct - robot_revision_rate_pct) / 100.0)

    # 2. Operating Room Time Optimization (Minutes per procedure)
    t_conventional_manual_min = 145.0   # Lengthy due to manual tremor pauses and stabilization
    t_robot_assisted_min = 112.0        # Smooth continuous insertion with digital filtering
    time_saved_per_procedure_min = t_conventional_manual_min - t_robot_assisted_min
    annual_or_hours_unlocked = (annual_microsurgical_cases * time_saved_per_procedure_min) / 60.0

    # 3. Dimensionless Operating Room Cost Parity (Kappa)
    # Conventional manual surgical team overhead normalized to 1.00
    c_manual_surgery_opex = 1.00
    c_robot_sterilization_drapes = 0.07
    c_robot_annual_service = 0.11
    c_robot_specialist_technician = 0.06
    c_robot_total_opex = c_robot_sterilization_drapes + c_robot_annual_service + c_robot_specialist_technician
    kappa = c_robot_total_opex / c_manual_surgery_opex # 0.24

    # 4. Capital Investment Amortization Horizon
    k_capex_surgical_robot = 0.45 # Capital cost normalized to annual revision/OR overhead
    annual_opex_savings = 1.0 - kappa # 0.76
    payback_years = k_capex_surgical_robot / annual_opex_savings
    payback_months = payback_years * 12.0

    print("=" * 65)
    print("MDRIIA GROUP 10 - SURGICAL CLINICAL PRECISION & OR ECONOMICS")
    print("=" * 65)
    print(f"Annual Case Volume:                 {annual_microsurgical_cases:.0f} microsurgical procedures")
    print(f"Revision Procedure Reduction:       {baseline_revision_rate_pct:.1f}% -> {robot_revision_rate_pct:.1f}% ({revisions_eliminated_annually:.1f} revisions avoided)")
    print(f"OR Time Saved per Case:             {time_saved_per_procedure_min:.1f} minutes ({t_conventional_manual_min:.0f} min -> {t_robot_assisted_min:.0f} min)")
    print(f"Annual OR Suite Hours Reclaimed:    {annual_or_hours_unlocked:.1f} hours/year")
    print(f"Operational Cost Parity (Kappa):    {kappa:.2f} (76.0% net operating advantage)")
    print(f"Dimensionless Payback Horizon:      {payback_months:.1f} operating months ({payback_years:.2f} years)")
    print("=" * 65)

if __name__ == "__main__":
    compute_surgical_economics()
