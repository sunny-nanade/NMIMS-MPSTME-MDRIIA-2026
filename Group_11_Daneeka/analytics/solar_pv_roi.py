"""CSBS techno-economic model: labour reallocation, NCRI / kappa, payback, queueing, sensitivity.

NOTHING final is hard-coded: every result below is computed from
  (a) the simulation trials (analytics/solar_inspection_real_trials.csv, produced by the controller),
  (b) the parameter table INPUTS, each tagged SOURCE (secondary, with citation), SIM (computed from
      the trials) or ASSUMPTION (a labelled value that the sensitivity analysis varies).
All money is dimensionless: one unit  u = the cost of one technician-hour  (so costs are ratios to the
manual-inspection cost and no currency appears anywhere).

Replaces the starter constants (8.5 h/MW, 1.6 h/MW, kappa 0.176, 78.5 %, 13.4 months): none of them
had a source; they are not used here.
Run:  python analytics/solar_pv_roi.py        (writes results/business_results.json + figures)
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIALS = os.path.join(ROOT, "analytics", "solar_inspection_real_trials.csv")
FIGS = os.path.join(ROOT, "results", "figures")

# --------------------------------------------------------------------------- inputs
SRC_SOLARBUILDER = ("SOURCE (secondary, trade press, NOT peer-reviewed): Solar Builder magazine, 'This Drone for Hire: "
                    "Meeting the Challenges of Solar O&M with Aerial Thermography' - G. Shambo (Borrego O&M) quotes an "
                    "unnamed study: manual inspection 10 h/MW; drone 15-18 min/MW. Read 30-Oct-2026.")


@dataclass
class Inputs:
    plant_mw: float = 50.0                 # ASSUMPTION: utility-scale plant
    module_wp: float = 400.0               # ASSUMPTION (same module power as the simulated farm)
    inspections_per_year: float = 2.0      # ASSUMPTION: two thermographic surveys per year
    h_manual_per_mw: float = 10.0          # SOURCE (secondary) - see SRC_SOLARBUILDER; most uncertain input
    supervision_frac: float = 0.15         # ASSUMPTION: fraction of robot time a technician is attending (set-up, relocation)
    verify_h_per_flag: float = 0.03        # ASSUMPTION: 2 min remote review of one flagged module's images
    defect_prevalence: float = 0.01        # ASSUMPTION: fraction of field modules with a thermal/visual defect (NOT the 12 % stress density used in the simulation)
    robot_cost_u: float = 1500.0           # ASSUMPTION: purchase cost of one AMR in technician-hour units
    maint_frac: float = 0.10               # ASSUMPTION: annual maintenance as a fraction of CapEx
    life_years: float = 8.0                # ASSUMPTION: service life T_life
    valid_hours_per_year: float = 1000.0   # ASSUMPTION: hours/yr with irradiance >= 600 W/m2 usable for inspection (see IEC TS 62446-3 note)
    fleet_availability: float = 0.8        # ASSUMPTION
    spare_robots: int = 1                  # ASSUMPTION: one spare unit
    repair_h_per_module: float = 1.0       # ASSUMPTION: technician time to repair/replace one module
    tech_hours_per_day: float = 8.0
    technicians: int = 2                   # ASSUMPTION: repair crew size for the queue


@dataclass
class SimStats:
    """Numbers measured by the simulation (see analytics/run_evaluation.py)."""
    h_robot_per_mw: float
    recall: float
    fp_rate: float            # false flags per healthy module
    modules_per_mw: float


def load_sim_stats(path: str = TRIALS, condition: str = "proposed", module_wp: float = 400.0) -> SimStats:
    df = pd.read_csv(path)
    df = df[(df.condition == condition)]
    if "deferred" in df:
        df = df[df.deferred == 0]
    n_mod_sim = 40
    healthy = n_mod_sim - df.n_defects
    return SimStats(h_robot_per_mw=float(df.time_per_mw_h.mean()),
                    recall=float(df.recall.mean()),
                    fp_rate=float((df.fp / healthy).mean()),
                    modules_per_mw=1e6 / module_wp)


# --------------------------------------------------------------------------- model
def economics(i: Inputs, s: SimStats, manual_recall: float | None = None) -> dict:
    mw, n = i.plant_mw, i.inspections_per_year
    n_modules = mw * s.modules_per_mw
    # annual manual cost (u/yr). Assumes manual inspection verifies as it goes (no extra review hours).
    c_base = i.h_manual_per_mw * mw * n
    # robot fleet sized from the workload and the usable inspection window
    robot_hours = s.h_robot_per_mw * mw * n
    fleet = math.ceil(robot_hours / (i.valid_hours_per_year * i.fleet_availability)) + i.spare_robots
    capex = fleet * i.robot_cost_u
    flagged_per_survey = n_modules * (i.defect_prevalence * s.recall + (1 - i.defect_prevalence) * s.fp_rate)
    labour_supervision = i.supervision_frac * robot_hours
    labour_verify = i.verify_h_per_flag * flagged_per_survey * n
    maint = i.maint_frac * capex
    c_robot = labour_supervision + labour_verify + maint
    delta = c_base - c_robot
    ncri = delta / c_base
    kappa = c_robot / c_base
    out = dict(
        n_modules=n_modules, c_base_u_per_yr=c_base, robot_hours_per_yr=robot_hours, fleet=fleet, capex_u=capex,
        flagged_per_survey=flagged_per_survey, c_robot_u_per_yr=c_robot, labour_supervision=labour_supervision,
        labour_verify=labour_verify, maintenance=maint, delta_opex_u_per_yr=delta, NCRI=ncri, kappa=kappa)
    if delta > 0:
        out["T_payback_months"] = capex / delta * 12.0
        out["P_payback"] = capex / (i.life_years * delta)
    else:
        out["T_payback_months"] = float("inf")
        out["P_payback"] = float("inf")
    # labour reallocation: technician hours per MW freed (manual hours minus residual human hours)
    resid = (labour_supervision + labour_verify) / (mw * n)
    out["H_reclaimed_h_per_MW"] = i.h_manual_per_mw - resid
    out["reallocation_fraction"] = out["H_reclaimed_h_per_MW"] / i.h_manual_per_mw
    return out


# --------------------------------------------------------------------------- queueing
def mm1_wq(lam: float, mu: float) -> float:
    if lam >= mu:
        return float("inf")
    return (lam / mu) / (mu - lam)


def erlang_c(c: int, a: float) -> float:
    """P(wait) for M/M/c with offered load a = lam/mu (needs a < c)."""
    if a >= c:
        return 1.0
    s = sum(a ** k / math.factorial(k) for k in range(c))
    top = a ** c / (math.factorial(c) * (1 - a / c))
    return top / (s + top)


def mmc_wq(lam: float, mu: float, c: int) -> float:
    a = lam / mu
    if a >= c:
        return float("inf")
    return erlang_c(c, a) / (c * mu - lam)


def repair_queue(i: Inputs, s: SimStats) -> dict:
    n_modules = i.plant_mw * s.modules_per_mw
    true_flags = n_modules * i.defect_prevalence * s.recall * i.inspections_per_year / 365.0     # per day
    mu = i.tech_hours_per_day / i.repair_h_per_module                                       # repairs per technician-day
    lam = true_flags
    return dict(lam_per_day=lam, mu_per_tech_per_day=mu, c=i.technicians, rho_mm1=lam / mu,
                rho_mmc=lam / (i.technicians * mu),
                Wq_mm1_days=mm1_wq(lam, mu), Wq_mmc_days=mmc_wq(lam, mu, i.technicians))


# --------------------------------------------------------------------------- sensitivity
SENS_PARAMS = ["h_manual_per_mw", "robot_cost_u", "defect_prevalence", "supervision_frac",
               "verify_h_per_flag", "valid_hours_per_year", "maint_frac", "life_years"]


def sensitivity(i: Inputs, s: SimStats, frac: float = 0.30):
    base = economics(i, s)
    rows = []
    for name in SENS_PARAMS:
        r = {"param": name}
        for tag, k in (("lo", 1 - frac), ("hi", 1 + frac)):
            e = economics(replace(i, **{name: getattr(i, name) * k}), s)
            r[f"NCRI_{tag}"], r[f"P_{tag}"], r[f"T_{tag}"] = e["NCRI"], e["P_payback"], e["T_payback_months"]
        rows.append(r)
    return base, pd.DataFrame(rows)


def break_even_h_manual(i: Inputs, s: SimStats, target="P"):
    """Manual hours/MW at which P_payback = 1 (target 'P') or NCRI = 0 (target 'N')."""
    def f(h):
        e = economics(replace(i, h_manual_per_mw=h), s)
        return (e["P_payback"] - 1.0) if target == "P" else e["NCRI"]
    try:
        return brentq(lambda h: f(h) if np.isfinite(f(h)) else 1e6, 0.5, 40.0)
    except ValueError:
        return float("nan")


# --------------------------------------------------------------------------- plots
def plot_sensitivity(i, s, df, base):
    os.makedirs(FIGS, exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    # (a) tornado of NCRI
    d = df.copy()
    d["span"] = (d.NCRI_hi - d.NCRI_lo).abs()
    d = d.sort_values("span")
    y = np.arange(len(d))
    ax[0].barh(y, d.NCRI_lo - base["NCRI"], left=base["NCRI"], color="#c0504d", label="-30 % input")
    ax[0].barh(y, d.NCRI_hi - base["NCRI"], left=base["NCRI"], color="#4f81bd", label="+30 % input")
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(d.param)
    ax[0].axvline(base["NCRI"], color="k", lw=0.8)
    ax[0].set_xlabel("NCRI  (dimensionless)")
    ax[0].set_title("NCRI: one-at-a-time +/-30 % sensitivity")
    ax[0].legend(loc="lower right")
    # (b) payback vs manual hours/MW and the robot cost
    hs = np.linspace(0.7 * i.h_manual_per_mw, 1.3 * i.h_manual_per_mw, 40)
    for k, lab in ((0.7, "robot cost -30 %"), (1.0, "robot cost base"), (1.3, "robot cost +30 %")):
        pp = [min(economics(replace(i, h_manual_per_mw=h, robot_cost_u=i.robot_cost_u * k), s)["P_payback"], 3) for h in hs]
        ax[1].plot(hs, pp, label=lab)
    ax[1].axhline(1.0, color="k", ls="--", lw=0.8)
    ax[1].set_xlabel("manual inspection hours per MW  (SOURCE, most uncertain)")
    ax[1].set_ylabel("P_payback = CapEx / (T_life * dOpEx)   [<1 pays back within life]")
    ax[1].set_ylim(0, 3)
    be = break_even_h_manual(i, s, "P")
    if np.isfinite(be):
        ax[1].axvline(be, color="gray", ls=":")
        ax[1].text(be, 2.6, f" break-even {be:.1f} h/MW", fontsize=8)
    ax[1].set_title("Payback horizon vs the most uncertain inputs")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "sensitivity.png"), dpi=170)
    plt.close(fig)


def plot_queue(i, s):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    mu = i.tech_hours_per_day / i.repair_h_per_module
    rho = np.linspace(0.05, 0.97, 200)
    for c in (1, 2, 3, 4):
        w = [mmc_wq(r * c * mu, mu, c) * 24 for r in rho]
        ax.plot(rho, w, label=f"M/M/{c}")
    q = repair_queue(i, s)
    ax.scatter([q["rho_mmc"]], [q["Wq_mmc_days"] * 24], color="k", zorder=5)
    ax.annotate(f"operating point (c={q['c']})", (q["rho_mmc"], q["Wq_mmc_days"] * 24), textcoords="offset points", xytext=(8, 8), fontsize=8)
    ax.set_yscale("log")
    ax.set_xlabel("utilisation rho = lambda / (c mu)")
    ax.set_ylabel("mean wait in queue W_q  [hours]")
    ax.set_title("Repair-queue delay for flagged modules")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "queue_wq_vs_rho.png"), dpi=170)
    plt.close(fig)


# --------------------------------------------------------------------------- main
def main():
    i = Inputs()
    s_prop = load_sim_stats(condition="proposed", module_wp=i.module_wp)
    s_base = load_sim_stats(condition="baseline", module_wp=i.module_wp)
    res = {}
    for name, s in (("proposed", s_prop), ("baseline_controller", s_base)):
        e = economics(i, s)
        res[name] = dict(sim=s.__dict__, economics=e, queue=repair_queue(i, s))
    base, df = sensitivity(i, s_prop)
    plot_sensitivity(i, s_prop, df, base)
    plot_queue(i, s_prop)
    res["break_even_h_manual_P1"] = break_even_h_manual(i, s_prop, "P")
    res["break_even_h_manual_NCRI0"] = break_even_h_manual(i, s_prop, "N")
    res["sensitivity"] = df.to_dict(orient="records")
    res["inputs"] = i.__dict__
    res["source_notes"] = {"h_manual_per_mw": SRC_SOLARBUILDER,
                           "everything_else_tagged_ASSUMPTION": "see the Inputs dataclass comments; each is varied in the sensitivity graph"}
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "business_results.json"), "w") as f:
        json.dump(res, f, indent=2, default=lambda o: None if o != o else str(o))
    for k in ("proposed", "baseline_controller"):
        e = res[k]["economics"]
        print(f"\n[{k}]  robot hours/MW (SIM) = {res[k]['sim']['h_robot_per_mw']:.2f}  recall = {res[k]['sim']['recall']:.2f}  "
              f"false-flag rate = {res[k]['sim']['fp_rate']:.3f}")
        print(f"  fleet={e['fleet']}  CapEx={e['capex_u']:.0f} u  C_base={e['c_base_u_per_yr']:.0f} u/yr  C_robot={e['c_robot_u_per_yr']:.0f} u/yr")
        print(f"  NCRI={e['NCRI']:.3f}  kappa={e['kappa']:.3f}  P_payback={e['P_payback']:.3f}  T_payback={e['T_payback_months']:.1f} months  "
              f"H_reclaimed={e['H_reclaimed_h_per_MW']:.2f} h/MW ({100 * e['reallocation_fraction']:.1f} %)")
        q = res[k]["queue"]
        print(f"  queue: lambda={q['lam_per_day']:.2f}/day  mu={q['mu_per_tech_per_day']:.1f}/tech/day  c={q['c']}  "
              f"rho={q['rho_mmc']:.2f}  Wq(M/M/1)={q['Wq_mm1_days']:.2f} d  Wq(M/M/c)={q['Wq_mmc_days'] * 24:.2f} h")
    print(f"\nbreak-even manual hours/MW: P=1 at {res['break_even_h_manual_P1']:.2f}; NCRI=0 at {res['break_even_h_manual_NCRI0']:.2f}")
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
