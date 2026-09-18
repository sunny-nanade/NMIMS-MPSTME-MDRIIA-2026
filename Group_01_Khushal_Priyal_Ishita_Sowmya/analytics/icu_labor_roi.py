"""
CSBS Technoeconomic Model: Nurse Labor Reallocation & Operational Parity
Strictly Dimensionless Formulation (Zero Currency Symbols)
Hendrich et al. Clinical Time-Motion Baseline.
"""
def evaluate_icu_amr_roi():
    n_nurses = 16
    shift_hours = 12.0
    shifts_day = 2
    logistics_fraction = 0.28
    amr_substitution = 0.72

    total_nurse_hours = n_nurses * shift_hours * shifts_day
    transit_baseline = total_nurse_hours * logistics_fraction
    reclaimed_bedside_hours = transit_baseline * amr_substitution
    annual_reclaimed_hours = reclaimed_bedside_hours * 365.25
    fte_unlocked = annual_reclaimed_hours / 2080.0
    kappa = 0.185
    payback_months = (0.65 / (1.0 - kappa)) * 12.0

    print("=" * 60)
    print("MDRIIA GROUP 01 CSBS TECHNOECONOMIC ASSESSMENT")
    print(f"Daily Reclaimed Direct Bedside: {reclaimed_bedside_hours:.2f} hours/day")
    print(f"Annual Clinical Hours Released: {annual_reclaimed_hours:.1f} hours/year")
    print(f"FTE Specialized Nurses Unlocked: {fte_unlocked:.2f} FTEs")
    print(f"Operational Cost Parity Ratio (k): {kappa:.3f} (81.5% operational gain)")
    print(f"Dimensionless Payback Horizon: {payback_months:.2f} months")
    print("=" * 60)

if __name__ == "__main__":
    evaluate_icu_amr_roi()
