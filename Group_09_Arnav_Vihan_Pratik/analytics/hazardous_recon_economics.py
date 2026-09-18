# Hazardous Industrial Inspection Safety & Workload Economics
# CSBS Operational Optimization Model (Zero Currency Symbols)
# Group: MDRIIA Group 09

import math
import numpy as np

def compute_hazard_recon_economics():
    """
    CSBS Technoeconomic Analysis
    Compares autonomous UGV hazardous inspection vs manual hazmat entry.
    Evaluates human hazard elimination, operator NASA-TLX cognitive workload reduction,
    and dimensionless capital amortization payback horizon.
    """
    # 1. Human Hazard Elimination
    annual_confined_space_entries_baseline = 48.0 # Critical inspections / year
    ugv_autonomous_inspections = 46.0            # Inspections handled entirely by UGV
    human_exposure_reduction_pct = (ugv_autonomous_inspections / annual_confined_space_entries_baseline) * 100.0

    # 2. Operator Cognitive Workload (NASA-TLX Score [0-100])
    # Under high teleoperation latency (800 ms)
    tlx_manual_teleop = 78.4       # Severe mental demand, temporal stress, frustration
    tlx_shared_autonomy = 28.2     # Supervisory monitoring, autonomous obstacle rejection
    workload_reduction_pct = ((tlx_manual_teleop - tlx_shared_autonomy) / tlx_manual_teleop) * 100.0

    # 3. Inspection Mission Latency
    t_hazmat_prep_and_entry_hours = 6.5  # Hazmat suit donning, gas clearance, safety protocols
    t_ugv_deployment_hours = 1.2         # Automated deployment and traversability mapping
    mission_time_acceleration_pct = ((t_hazmat_prep_and_entry_hours - t_ugv_deployment_hours) / t_hazmat_prep_and_entry_hours) * 100.0

    # 4. Dimensionless Operational Cost Parity (Kappa)
    # Manual human inspection team normalized to 1.00
    c_human_team_opex = 1.00
    c_ugv_energy = 0.04
    c_ugv_maintenance = 0.11
    c_ugv_teleop_supervisor = 0.07
    c_ugv_total_opex = c_ugv_energy + c_ugv_maintenance + c_ugv_teleop_supervisor
    kappa = c_ugv_total_opex / c_human_team_opex # 0.22

    # Capital Investment Amortization Horizon
    k_capex_ugv = 0.30 # UGV capital cost normalized to annual specialized safety contracting
    annual_opex_savings = 1.0 - kappa # 0.78
    payback_years = k_capex_ugv / annual_opex_savings
    payback_months = payback_years * 12.0

    print("=" * 65)
    print("MDRIIA GROUP 09 - HAZARDOUS RECONNAISSANCE SAFETY & ECONOMICS")
    print("=" * 65)
    print(f"Human High-Hazard Exposure Drop:     {human_exposure_reduction_pct:.1f}% ({ugv_autonomous_inspections:.0f} entries eliminated)")
    print(f"Operator NASA-TLX Workload Drop:     {workload_reduction_pct:.1f}% ({tlx_manual_teleop:.1f} -> {tlx_shared_autonomy:.1f})")
    print(f"Inspection Protocol Acceleration:    {mission_time_acceleration_pct:.1f}% ({t_hazmat_prep_and_entry_hours:.1f}h -> {t_ugv_deployment_hours:.1f}h)")
    print(f"Operational Cost Parity (Kappa):     {kappa:.2f} (78.0% operational cost advantage)")
    print(f"Dimensionless Payback Horizon:       {payback_months:.1f} operational months ({payback_years:.2f} years)")
    print("=" * 65)

if __name__ == "__main__":
    compute_hazard_recon_economics()
