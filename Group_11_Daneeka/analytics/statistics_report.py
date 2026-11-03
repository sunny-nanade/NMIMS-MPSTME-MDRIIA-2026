"""Statistical comparison baseline vs proposed from analytics/solar_inspection_real_trials.csv.

For every metric: mean +/- SD per condition, Welch two-sided t-test (alpha = 0.05),
Cohen's d (pooled SD), 95 % CI of the difference of means (Welch-Satterthwaite df),
paired-t p-value as a sensitivity check (the seeds are shared between conditions).
Writes analytics/statistics_summary.csv and prints a markdown table.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIALS = os.path.join(ROOT, "analytics", "solar_inspection_real_trials.csv")

METRICS = [
    ("recall", "Recall (defects found / present)"),
    ("precision", "Precision (true flags / all flags)"),
    ("fp", "False alarms per mission (modules)"),
    ("fn", "Missed defective modules per mission"),
    ("loc_err_mean_m", "Mean localisation error of true detections [m]"),
    ("kind_accuracy", "Defect-type accuracy"),
    ("track_rmse_m", "Lane tracking RMSE [m]"),
    ("pose_err_rms_m", "Pose estimate RMS error [m]"),
    ("control_effort", "Control effort  int tau^2 dt  [N^2 m^2 s]"),
    ("duration_s", "Mission time [s]"),
    ("time_per_mw_h", "Inspection time per MW [h/MW]"),
]


def compare(a: np.ndarray, b: np.ndarray, paired_ok: bool = True):
    """a=baseline, b=proposed. Returns dict of statistics."""
    ok = ~(np.isnan(a) | np.isnan(b))
    a_, b_ = a[ok], b[ok]
    n1, n2 = len(a_), len(b_)
    m1, m2 = a_.mean(), b_.mean()
    s1, s2 = a_.std(ddof=1), b_.std(ddof=1)
    diff = m2 - m1
    se = np.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
    if se == 0:
        return dict(n=n1, mean_base=m1, sd_base=s1, mean_prop=m2, sd_prop=s2, diff=diff,
                    ci_lo=diff, ci_hi=diff, t=np.nan, p_welch=np.nan, d=np.nan, p_paired=np.nan)
    df = se ** 4 / ((s1 ** 2 / n1) ** 2 / (n1 - 1) + (s2 ** 2 / n2) ** 2 / (n2 - 1))
    tcrit = stats.t.ppf(0.975, df)
    t, p = stats.ttest_ind(b_, a_, equal_var=False)
    sp = np.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
    d = diff / sp if sp > 0 else np.nan
    pp = stats.ttest_rel(b_, a_).pvalue if n1 == n2 else np.nan
    return dict(n=n1, mean_base=m1, sd_base=s1, mean_prop=m2, sd_prop=s2, diff=diff,
                ci_lo=diff - tcrit * se, ci_hi=diff + tcrit * se, t=t, p_welch=p, d=d, p_paired=pp)


def main(path=TRIALS):
    df = pd.read_csv(path)
    base = df[df.condition == "baseline"].sort_values("seed").reset_index(drop=True)
    prop = df[df.condition == "proposed"].sort_values("seed").reset_index(drop=True)
    # a mission the proposed controller defers (irradiance below the validity limit for 3 consecutive
    # modules) is rescheduled, not failed: it is reported as a deferral and excluded from the paired
    # comparison together with its baseline twin (same seed)
    deferred = prop["deferred"].to_numpy(bool)
    print(f"deferred missions (proposed): {int(deferred.sum())} of {len(prop)}  seeds={list(prop.seed[deferred])}")
    base, prop = base[~deferred], prop[~deferred]
    rows = []
    for col, label in METRICS:
        r = compare(base[col].to_numpy(float), prop[col].to_numpy(float))
        r.update(metric=col, label=label)
        rows.append(r)
    out = pd.DataFrame(rows)[["metric", "label", "n", "mean_base", "sd_base", "mean_prop", "sd_prop",
                              "diff", "ci_lo", "ci_hi", "t", "p_welch", "d", "p_paired"]]
    out.to_csv(os.path.join(ROOT, "analytics", "statistics_summary.csv"), index=False)
    pd.set_option("display.width", 220)
    print(out.round(4).to_string(index=False))
    return out


if __name__ == "__main__":
    main(*(sys.argv[1:2] or []))
