"""Pessimistic / base / optimistic business scenarios (all money in technician-hour units 'u'; dimensionless).
Every input is the one in solar_pv_roi.Inputs; the scenario scales the uncertain ones by +/-30 %.
Run: python analytics/business_scenarios.py"""
import os, sys
from dataclasses import replace
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solar_pv_roi import Inputs, load_sim_stats, economics, repair_queue, break_even_h_manual

i0, s = Inputs(), load_sim_stats()
sc = {
 "pessimistic": replace(i0, h_manual_per_mw=i0.h_manual_per_mw*0.7, robot_cost_u=i0.robot_cost_u*1.3,
                        maint_frac=i0.maint_frac*1.3, verify_h_per_flag=i0.verify_h_per_flag*1.3, supervision_frac=i0.supervision_frac*1.3),
 "base": i0,
 "optimistic": replace(i0, h_manual_per_mw=i0.h_manual_per_mw*1.3, robot_cost_u=i0.robot_cost_u*0.7,
                       maint_frac=i0.maint_frac*0.7, verify_h_per_flag=i0.verify_h_per_flag*0.7, supervision_frac=i0.supervision_frac*0.7),
}
rows = []
for k, i in sc.items():
    e = economics(i, s)
    rows.append(dict(scenario=k, h_manual=i.h_manual_per_mw, capex=e["capex_u"], c_base=e["c_base_u_per_yr"],
                     c_robot=e["c_robot_u_per_yr"], NCRI=e["NCRI"], T_payback_months=e["T_payback_months"], P_payback=e["P_payback"]))
df = pd.DataFrame(rows).round(3)
print(df.to_string(index=False))
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "business_scenarios.csv")
df.to_csv(out, index=False); print("->", out)
print("break-even manual h/MW (P=1):", round(break_even_h_manual(i0, s), 2))
