"""
CSBS Technoeconomic Analysis: Clinical Labor Reallocation & Operational Parity
Strictly Dimensionless Formulation (Zero Currency Symbols)

Assigned to: E054 Ishita Ranjan
Theoretical Baseline: Hendrich et al. (36-Hospital Time & Motion Study) & Michel et al. (2021)
"""

def evaluate_technoeconomic_model():
    print("=" * 70)
    print("CSBS CLINICAL LABOR REALLOCATION & TECHNOECONOMIC ASSESSMENT")
    print("=" * 70)
    
    # Clinical Baseline Parameters
    t_shift = 12.0                     # Shift length (hours)
    eta_base = 0.28                    # 28% of shift spent on logistical transit
    h_transit_base = eta_base * t_shift # 3.36 hours/shift per nurse
    
    # AMR Eligibility & Fleet Parameters
    psi = 0.80                         # 80% of medication tasks eligible for AMR
    a_amr = 0.95                       # 95% fleet operational availability
    h_reclaimed = psi * a_amr * h_transit_base # 2.5536 hours/nurse-shift
    
    # Expansion of Direct Patient Care (Baseline: 6.0 hours direct care)
    h_direct_baseline = 6.00
    delta_bedside = (h_reclaimed / h_direct_baseline) * 100.0
    
    # Ward-Scale Impact (N = 10 active nurses per shift)
    n_nurses_ward = 10
    fte_released = n_nurses_ward * (h_reclaimed / t_shift)
    
    # Dimensionless Operational Cost Parity Ratio (kappa)
    # kappa = (c_R * tau_R) / (c_N * tau_N)
    # Target: kappa <= 0.35
    kappa = 0.225
    
    # Dimensionless Payback Horizon (P_m) in Months
    # M_eq = Capital expenditure expressed as multiple of nurse annual compensation
    # mu = Maintenance cost fraction
    m_eq = 1.80
    mu = 0.12
    p_months = (12.0 * m_eq) / (fte_released * (1.0 - mu))
    
    print(f"Shift Logistics Baseline:         {h_transit_base:.2f} hours / nurse-shift (28% of shift)")
    print(f"Reclaimed Direct Bedside Care:    {h_reclaimed:.4f} hours / nurse-shift")
    print(f"Direct Patient Care Expansion:    +{delta_bedside:.2f}% relative increase")
    print(f"Ward Full-Time Capacity Released: {fte_released:.3f} FTE specialized nurses")
    print(f"Operational Cost Parity (kappa):  {kappa:.3f} (77.5% net operational savings)")
    print(f"Dimensionless Payback Horizon:    {p_months:.2f} months")
    print("=" * 70)

if __name__ == "__main__":
    evaluate_technoeconomic_model()
