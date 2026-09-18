# CSBS Commercial Space Economics & Active Debris Removal (ADR) Optimization
# Strictly Dimensionless Formulation (Zero Currency Symbols)
# Group: MDRIIA Group 04

import math
import numpy as np

def compute_space_sustainability_economics():
    """
    CSBS Commercial Space Economics Formulation
    Evaluates multi-target ADR sortie amortization and constellation asset value preservation
    """
    n_targets_per_sortie = 5
    p_capture_success = 0.925 # With compliant impedance control
    p_capture_rigid = 0.525   # With rigid PD baseline
    
    # Fractional propellant expenditure per rendezvous sortie
    kappa_prop = 0.08 
    
    # Multi-target Amortization Efficiency (Gamma_multi)
    # Normalized against dedicated single-target launch cost = 1.0
    gamma_impedance = (n_targets_per_sortie * p_capture_success) / (1.0 + kappa_prop * n_targets_per_sortie)
    gamma_rigid = (n_targets_per_sortie * p_capture_rigid) / (1.0 + kappa_prop * n_targets_per_sortie)
    
    # Constellation Asset Value Preservation Index (Psi)
    # Models avoidance of Kessler cascading collision probability
    lambda_kessler = 0.045
    psi_impedance = 1.0 - math.exp(-lambda_kessler * (n_targets_per_sortie * p_capture_success))
    psi_rigid = 1.0 - math.exp(-lambda_kessler * (n_targets_per_sortie * p_capture_rigid))
    
    # Regulatory compliance factor (FCC 5-year post-mission disposal rule)
    compliance_score = p_capture_success * 100.0
    
    print("=" * 65)
    print("MDRIIA GROUP 04 - COMMERCIAL SPACE SUSTAINABILITY & ADR ECONOMICS")
    print("=" * 65)
    print(f"Capture Success Rate (Compliant Impedance): {p_capture_success*100:.1f}%")
    print(f"Capture Success Rate (Rigid PD Baseline):   {p_capture_rigid*100:.1f}%")
    print(f"Multi-Target Amortization Ratio (Impedance): {gamma_impedance:.2f}x single-launch parity")
    print(f"Multi-Target Amortization Ratio (Rigid PD):  {gamma_rigid:.2f}x single-launch parity")
    print(f"Economic Efficiency Gain:                  +{((gamma_impedance/gamma_rigid) - 1.0)*100:.1f}%")
    print(f"Constellation Asset Preservation Index:     {psi_impedance:.3f} (vs {psi_rigid:.3f} rigid)")
    print(f"Regulatory License Compliance Probability:  {compliance_score:.1f}%")
    print("=" * 65)

if __name__ == "__main__":
    compute_space_sustainability_economics()
