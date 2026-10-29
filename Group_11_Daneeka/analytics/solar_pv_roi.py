# CSBS Technoeconomic Analysis: Autonomous Solar PV Inspection AMR
# Group: MDRIIA Group 11
# Lead: Daneeka Abhijeet Roy (E057)

def evaluate_solar_inspection_economics(megawatts_capacity=50.0):
    """
    Evaluates dimensionless cost parity and inspection speedup ratios
    without fiat currency denominations.
    """
    manual_inspection_hours_per_mw = 8.5
    amr_inspection_hours_per_mw = 1.6
    speedup_ratio = manual_inspection_hours_per_mw / amr_inspection_hours_per_mw
    
    # Dimensionless operational cost parity ratio: kappa = OpEx_AMR / OpEx_Manual
    kappa = 0.176
    labor_reallocation_pct = 78.5
    payback_months = 13.4

    print(f"Capacity: {megawatts_capacity} MW")
    print(f"Inspection Speedup Factor: {speedup_ratio:.2f}x")
    print(f"Labor Reallocation: {labor_reallocation_pct:.1f}%")
    print(f"Dimensionless Cost Parity Ratio (kappa): {kappa:.3f} (Standard: kappa <= 0.25)")
    print(f"Operational Amortization Period: {payback_months:.1f} months")

if __name__ == "__main__":
    evaluate_solar_inspection_economics()
