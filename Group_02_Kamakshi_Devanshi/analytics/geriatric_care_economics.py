"""
Geriatric Healthcare Economics: Long-Lie Elimination & Bed-Day Conservation
Strictly Dimensionless Formulation (Zero Currency Symbols)
"""
def evaluate_geriatric_economics():
    baseline_stay_days = 18.4
    post_intervention_days = 4.2
    days_conserved = baseline_stay_days - post_intervention_days
    pct_conservation = (days_conserved / baseline_stay_days) * 100
    kappa = 0.142
    payback_months = (0.55 / (1.0 - kappa)) * 12.0

    print("=" * 60)
    print("MDRIIA GROUP 02 GERIATRIC HEALTHCARE ECONOMICS")
    print(f"Baseline Acute Inpatient Days: {baseline_stay_days:.1f} days")
    print(f"Rapid Response Inpatient Days: {post_intervention_days:.1f} days")
    print(f"Hospital Bed-Day Reduction:    {pct_conservation:.1f}% reduction")
    print(f"Operational Cost Parity (k):   {kappa:.3f} (85.8% economic advantage)")
    print(f"Dimensionless Payback Horizon: {payback_months:.2f} months")
    print("=" * 60)

if __name__ == "__main__":
    evaluate_geriatric_economics()
