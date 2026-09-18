"""
Campus Security Operations & Labor Reallocation Model
Strictly Dimensionless Formulation (Zero Currency Symbols)
"""
def evaluate_campus_security_roi():
    guard_shift_hours_reallocated = 14.5
    kappa = 0.215
    payback_months = (0.60 / (1.0 - kappa)) * 12.0
    print("=" * 60)
    print("MDRIIA GROUP 05 SECURITY LABOR REALLOCATION")
    print(f"Daily Security Patrol Hours Reallocated: {guard_shift_hours_reallocated:.1f} h/day")
    print(f"Operational Cost Parity (k):             {kappa:.3f} (78.5% net advantage)")
    print(f"Dimensionless Payback Horizon:           {payback_months:.2f} months")
    print("=" * 60)

if __name__ == "__main__":
    evaluate_campus_security_roi()
