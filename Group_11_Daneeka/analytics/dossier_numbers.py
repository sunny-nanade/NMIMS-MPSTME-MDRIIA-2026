"""Prints the numbers for the dossier tables straight from the CSV files (copy from here, never retype from memory)."""
import os, pandas as pd, json
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
st = pd.read_csv(f"{R}/analytics/statistics_summary.csv")
tr = pd.read_csv(f"{R}/analytics/solar_inspection_real_trials.csv")
print("# Section 4 (held-out seeds 3000-3029)")
print(f"Runs: {len(tr)//2} per condition; deferred (proposed): {int(tr[tr.condition=='proposed'].deferred.sum())}; seeds recorded in the CSV `seed` column")
print("Randomised: weather preset, start time U(10,14) h, defect count/kind/cell/severity, confounders, wheel-calibration and gyro-bias draws, noise")
print("Logging: 500 Hz (one row per 0.002 s physics step); full CSV written for demo runs (results/telemetry)")
print(st[["label","n","mean_base","sd_base","mean_prop","sd_prop","diff","ci_lo","ci_hi","p_welch","d"]].round(4).to_string(index=False))
b = json.load(open(f"{R}/results/business_results.json"))
e, q = b["proposed"]["economics"], b["proposed"]["queue"]
print("\n# Section 3")
print({k: round(v, 3) for k, v in e.items() if isinstance(v, float)})
print({k: round(v, 3) for k, v in q.items() if isinstance(v, float)})
print("break-even manual h/MW (P=1):", round(b["break_even_h_manual_P1"], 2))
print(pd.read_csv(f"{R}/analytics/fmea_table.csv")[["failure_mode","S","O_pre","D_pre","RPN_pre","O_post","D_post","RPN_post"]].to_string(index=False))
