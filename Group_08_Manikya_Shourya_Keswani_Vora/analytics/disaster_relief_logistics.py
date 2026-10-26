"""
Group 08 SkyHydro: CSBS techno-economic model (dimensionless, no currency).
Owner: E067 (CSBS Business & Techno-economic Systems Analyst)

Question: for URGENT small relief items (medicines, insulin, antivenom, ORS: <= 3 kg)
to households cut off by floodwater, how does a small UAV fleet compare with sending a
rescue boat for each request?  (Bulk food/water still goes by boat; this model does not
claim the UAV replaces boats for bulk supply.)

Every cost is a ratio to ONE BOAT-HOUR (boat + crew + fuel = 1.0), so no money appears.
Every input is either
  [SIM]   computed from our own MuJoCo trials (analytics/flood_relief_real_trials.csv), or
  [ASSUMPTION]  a labelled operating assumption that is varied in the sensitivity graph.

Outputs (all re-computed on every run, nothing hard-coded):
  H_reclaimed   boat-crew hours per day freed by UAV sorties
  kappa, NCRI   cost-parity ratio C_uav/C_boat per delivery, NCRI = 1 - kappa
  P_payback     CapEx / (T_life * annual OpEx saving)   (dimensionless; < 1 = pays back within life)
  T_payback     CapEx / monthly saving (months)
  M/M/c queue   Erlang-C waiting time for c UAVs vs boats; response-latency reduction
  sensitivity   +-30 % tornado on every assumption + break-even of the most influential one
  FMEA          RPN = S x O x D before / after mitigation

Run:  python analytics/disaster_relief_logistics.py        (writes figures to docs/figures/)
"""
import csv
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRIALS = os.path.join(HERE, "flood_relief_real_trials.csv")
FIG = os.path.join(ROOT, "docs", "figures")
sys.path.insert(0, os.path.join(ROOT, "src"))

# ----------------------------------------------------------------- assumptions
# (value, short label, why / where it comes from)
ASSUME = {
    "d_km":          (5.0,  "one-way corridor, relief hub -> cut-off cluster (km)", "ASSUMPTION: typical isolated-village distance; varied 2-10 km"),
    "v_boat_kmh":    (8.0,  "effective boat speed in debris-laden flood water (km/h)", "ASSUMPTION: slowed by current, debris, submerged obstacles"),
    "t_boat_prep_h": (0.5,  "boat launch, loading and channel finding per sortie (h)", "ASSUMPTION"),
    "crew_boat":     (4,    "crew per rescue boat (persons)", "ASSUMPTION"),
    "t_uav_turn_h":  (10/60, "UAV turnaround: battery swap + canister loading (h)", "ASSUMPTION"),
    "r_uav":         (0.15, "UAV operating cost per flight-hour / boat-hour", "ASSUMPTION: energy + battery wear + operator share"),
    "capex_bh":      (300.0, "one UAV system (airframe, 2 packs, charger, GCS) in boat-hours", "ASSUMPTION"),
    "lambda_h":      (2.0,  "urgent small-item requests per hour", "ASSUMPTION"),
    "c_uav":         (2,    "UAVs in the fleet", "design choice"),
    "c_boat":        (4,    "boats assigned to urgent requests", "ASSUMPTION: smallest boat team with a stable queue (rho < 1)"),
    "ops_h_day":     (12.0, "daylight operating window (h/day)", "ASSUMPTION: VLOS daylight ops"),
    "season_days":   (60.0, "flood-operation days per year", "ASSUMPTION"),
    "life_yr":       (3.0,  "UAV system service life (years)", "ASSUMPTION"),
}
SENS_KEY = "capex_bh"             # most UNCERTAIN input (no verified price data) -> sensitivity graph + break-even
V_UAV = 8.0                       # m/s  [SIM] cruise speed flown by our controller (V_CRUISE)


def load_sim():
    """[SIM] inputs from our own MuJoCo trials (proposed controller)."""
    import flood_relief_drop_sim as F
    rows = list(csv.DictReader(open(TRIALS)))
    prop = [r for r in rows if r["controller"] == "proposed"]
    rel = [float(r["t_release_s"]) for r in prop if r["t_release_s"]]
    # time to fly the trial's own 45 m sortie before reaching the drop zone (same min-jerk planner)
    start = F.PAD + np.array([0, 0, 0.9])
    t_takeoff = F.seg_time(start, np.array([*start[:2], F.Z_CRUISE]), F.V_CLIMB)
    t_cruise = F.seg_time(np.array([*start[:2], F.Z_CRUISE]), np.array([0, 0, F.Z_CRUISE]), F.V_CRUISE)
    t_appr = F.seg_time(np.array([0, 0, F.Z_CRUISE]), np.array([0, 0, F.Z_HOVER]), F.V_CLIMB)
    t_site_s = float(np.mean(rel)) - (t_takeoff + t_cruise + t_appr)
    p_success = sum(r["outcome"] == "delivered" for r in prop) / len(prop)
    endurance_min = float(np.mean([float(r["endurance_min"]) for r in prop]))
    by_wind = {}
    for w in sorted({float(r["wind_ms"]) for r in prop}):
        sub = [r for r in prop if float(r["wind_ms"]) == w]
        by_wind[w] = sum(r["outcome"] == "delivered" for r in sub) / len(sub)
    return dict(t_site_h=t_site_s / 3600.0, t_site_s=t_site_s, p_success=p_success,
                endurance_min=endurance_min, success_by_wind=by_wind, n_trials=len(prop))


# ----------------------------------------------------------------- queueing
def erlang_c(c, a):
    """Probability that an arrival waits (Erlang C), a = lambda/mu offered load."""
    if a >= c:
        return 1.0
    s = sum(a ** k / math.factorial(k) for k in range(c))
    top = a ** c / math.factorial(c) * c / (c - a)
    return top / (s + top)


def mmc_wq(lam, mu, c):
    rho = lam / (c * mu)
    if rho >= 1:
        return float("inf"), rho
    return erlang_c(c, lam / mu) / (c * mu - lam), rho


# ----------------------------------------------------------------- the model
def model(p, sim):
    d = p["d_km"]
    # cycle times (h)
    t_boat_trip = p["t_boat_prep_h"] + 2 * d / p["v_boat_kmh"]                   # dedicated round trip
    t_uav_flight = 2 * d * 1000 / V_UAV / 3600 + sim["t_site_h"]                  # [SIM] speed + drop-site time
    t_uav_cycle = t_uav_flight + p["t_uav_turn_h"]
    # one delivery needs 1/p_success sorties on average (aborted drops are re-flown)   [SIM]
    k_retry = 1.0 / max(sim["p_success"], 1e-6)
    # cost per delivery in boat-hours
    C_boat = t_boat_trip * 1.0
    C_uav = k_retry * t_uav_flight * p["r_uav"]
    kappa = C_uav / C_boat
    ncri = 1.0 - kappa
    # demand and labour
    deliveries_day = p["lambda_h"] * p["ops_h_day"]
    H_reclaimed = deliveries_day * t_boat_trip * p["crew_boat"]                    # crew-hours/day
    # payback
    capex = p["capex_bh"] * p["c_uav"]
    saving_year = (C_boat - C_uav) * deliveries_day * p["season_days"]
    P_payback = capex / (p["life_yr"] * saving_year) if saving_year > 0 else float("inf")
    T_payback_months = capex / (saving_year / 12.0) if saving_year > 0 else float("inf")
    # queueing (requests wait for a free vehicle; service = full cycle)
    mu_uav = 1.0 / (k_retry * t_uav_cycle)
    mu_boat = 1.0 / t_boat_trip
    wq_uav, rho_uav = mmc_wq(p["lambda_h"], mu_uav, int(p["c_uav"]))
    wq_boat, rho_boat = mmc_wq(p["lambda_h"], mu_boat, int(p["c_boat"]))
    # response latency = wait + outbound leg
    lat_uav = wq_uav + d * 1000 / V_UAV / 3600 + sim["t_site_h"]
    lat_boat = wq_boat + p["t_boat_prep_h"] + d / p["v_boat_kmh"]
    lat_red = 1 - lat_uav / lat_boat if math.isfinite(lat_boat) else 1.0
    range_ok = t_uav_flight * 60 < 0.75 * sim["endurance_min"]                    # 25 % battery reserve
    return dict(t_boat_trip_h=t_boat_trip, t_uav_flight_h=t_uav_flight, t_uav_cycle_h=t_uav_cycle,
                k_retry=k_retry, C_boat=C_boat, C_uav=C_uav, kappa=kappa, NCRI=ncri,
                deliveries_day=deliveries_day, H_reclaimed=H_reclaimed, capex=capex,
                saving_year=saving_year, P_payback=P_payback, T_payback_months=T_payback_months,
                mu_uav=mu_uav, mu_boat=mu_boat, rho_uav=rho_uav, rho_boat=rho_boat,
                Wq_uav_min=wq_uav * 60, Wq_boat_min=wq_boat * 60,
                latency_uav_min=lat_uav * 60, latency_boat_min=lat_boat * 60,
                latency_reduction=lat_red, range_ok=range_ok)


FMEA = [
    # mode, effect, S, O, D (before), mitigation, S, O, D (after), evidence
    ("Payload swing in 15 m/s crosswind -> drop outside target",
     "kit lands in water / wrong roof; re-fly, lost medicine", 8, 7, 5,
     "vision-guided canister centring + anti-sway + steady release window; ABORT instead of blind drop", 8, 3, 2, "Both"),
    ("Battery depletion before return to base",
     "UAV ditched in flood water, fleet capacity lost", 9, 3, 6,
     "integrated power model; ABORT/RTB when predicted SoC at pad < 25 %", 9, 2, 2, "Code"),
    ("Canister released while still swinging (timed release)",
     "drop error grows with swing; kit damaged", 7, 6, 6,
     "release only when canister error < 0.35 m and relative speed < 0.35 m/s (else wait / abort)", 7, 2, 2, "Both"),
    ("Vision measurement noise / glare on the drop marker",
     "wrong centring, off-zone drop", 6, 4, 6,
     "alpha-beta filter on 30 Hz camera data; 5 cm noise tested in every trial", 6, 3, 3, "Simulation"),
    ("Rotor thrust saturation in gusts (tilt limit)",
     "position loss near buildings, possible crash", 9, 3, 5,
     "35 deg tilt limit, thrust headroom (T/W >= 2.2 at 3 kg), integral wind rejection; crash check in every run", 9, 2, 3, "Both"),
]


def tornado(base, sim, key="P_payback", frac=0.30):
    out = []
    for k, (v, label, src) in ASSUME.items():
        if k in ("c_uav", "c_boat", "crew_boat"):
            continue
        lo = dict(base); hi = dict(base)
        lo[k] = v * (1 - frac); hi[k] = v * (1 + frac)
        out.append((k, label, model(lo, sim)[key], model(hi, sim)[key]))
    ref = model(base, sim)[key]
    out.sort(key=lambda r: abs(r[3] - r[2]), reverse=True)
    return ref, out


def break_even(base, sim, key, target=1.0, metric="P_payback", lo=0.01, hi=50.0):
    """Value of input `key` at which metric == target (bisection)."""
    f = lambda x: model({**base, key: x}, sim)[metric] - target
    a, b = base[key] * lo, base[key] * hi
    fa, fb = f(a), f(b)
    if not (math.isfinite(fa) and math.isfinite(fb)) or fa * fb > 0:
        return float("nan")
    for _ in range(80):
        m = 0.5 * (a + b)
        if f(m) * fa > 0:
            a, fa = m, f(m)
        else:
            b = m
    return 0.5 * (a + b)


def figures(base, sim, res, tor, be_key, be_val):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(FIG, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

    # sensitivity: P_payback (left) and NCRI (right) vs the most influential input, break-even marked
    k = be_key
    x_hi = max(base[k] * 2.0, be_val * 1.25 if math.isfinite(be_val) else 0)
    xs = np.linspace(base[k] * 0.4, x_hi, 160)
    P = [min(model({**base, k: x}, sim)["P_payback"], 3) for x in xs]
    N = [model({**base, k: x}, sim)["NCRI"] for x in xs]
    fig, ax = plt.subplots(figsize=(3.7, 2.8))
    ax.plot(xs, P, color="#1f6fb4", lw=2, label="P_payback")
    ax.axhline(1.0, color="#999", ls="--", lw=1)
    ax.axvline(base[k], color="#444", lw=0.8)
    ax.axvspan(base[k] * 0.7, base[k] * 1.3, color="#1f6fb4", alpha=0.08, label="±30 %")
    if math.isfinite(be_val) and be_val <= xs[-1]:
        ax.axvline(be_val, color="#c0392b", ls=":", lw=1.2)
        ax.annotate(f"break-even\n{be_val:.0f}", (be_val, 1.0), xytext=(6, -30), textcoords="offset points", color="#c0392b", fontsize=8)
    ax.set_xlabel({"capex_bh": "UAV system CapEx (boat-hours per UAV)"}.get(k, k)); ax.set_ylabel("P_payback (–)")
    ax2 = ax.twinx(); ax2.plot(xs, N, color="#27ae60", lw=1.5, label="NCRI"); ax2.set_ylabel("NCRI (–)", color="#27ae60")
    ax2.set_ylim(0, 1); ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=7, loc="center left")
    ax.set_title(f"Sensitivity to {k} (ours: P = {res['P_payback']:.2f}, NCRI = {res['NCRI']:.2f})", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_business_sensitivity.png"), dpi=200); plt.close(fig)

    # tornado of all assumptions (+-30 %)
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    lbl = [r[0] for r in tor[1]][::-1]
    lo = [r[2] for r in tor[1]][::-1]; hi = [r[3] for r in tor[1]][::-1]
    ref = tor[0]
    for i, (a, b) in enumerate(zip(lo, hi)):
        ax.barh(i, a - ref, left=ref, color="#7fb3d5"); ax.barh(i, b - ref, left=ref, color="#1f6fb4")
    ax.set_yticks(range(len(lbl))); ax.set_yticklabels(lbl, fontsize=7)
    ax.axvline(ref, color="#444", lw=0.8)
    ax.set_xlabel("P_payback (–)   light: input −30 %, dark: +30 %"); ax.set_title("Tornado: which input moves payback most", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_business_tornado.png"), dpi=200); plt.close(fig)

    # queueing: Wq vs utilisation for c = 1, 2, 3 UAVs + operating point
    fig, ax = plt.subplots(figsize=(3.7, 2.8))
    mu = res["mu_uav"]
    for c, col in ((1, "#7fb3d5"), (2, "#1f6fb4"), (3, "#0b3d66")):
        rh = np.linspace(0.05, 0.95, 100)
        ax.plot(rh, [mmc_wq(r * c * mu, mu, c)[0] * 60 for r in rh], color=col, label=f"c = {c} UAV")
    ax.plot(res["rho_uav"], res["Wq_uav_min"], "o", color="#c0392b")
    ax.annotate(f"ours: ρ={res['rho_uav']:.2f}, Wq={res['Wq_uav_min']:.1f} min", (res["rho_uav"], res["Wq_uav_min"]),
                xytext=(-120, 10), textcoords="offset points", color="#c0392b", fontsize=8)
    ax.set_ylim(0, 60); ax.set_xlabel("utilisation ρ = λ/(cμ)"); ax.set_ylabel("W_q (min)")
    ax.set_title("M/M/c queue: relief requests"); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_business_queue.png"), dpi=200); plt.close(fig)


def main():
    sim = load_sim()
    base = {k: v[0] for k, v in ASSUME.items()}
    res = model(base, sim)
    tor = tornado(base, sim)
    top_key = tor[1][0][0]
    be = break_even(base, sim, SENS_KEY, 1.0, "P_payback", hi=200.0)
    be_top = break_even(base, sim, top_key, 1.0, "P_payback")
    be_ncri = break_even(base, sim, "r_uav", 0.0, "NCRI")
    figures(base, sim, res, tor, SENS_KEY, be)

    print("=" * 72)
    print("MDRIIA GROUP 08 - SkyHydro techno-economics (unit cost = 1 boat-hour)")
    print("=" * 72)
    print(f"[SIM] {sim['n_trials']} proposed-controller trials: success {sim['p_success']:.1%}, "
          f"drop-site time {sim['t_site_s']:.1f} s, endurance {sim['endurance_min']:.1f} min")
    print("      success by wind:", {f"{w:.0f} m/s": f"{v:.0%}" for w, v in sim["success_by_wind"].items()})
    for k, (v, label, src) in ASSUME.items():
        print(f"  {k:<14} = {v:<8.4g} {label}  [{src}]")
    print("-" * 72)
    print(f"boat round trip            {res['t_boat_trip_h']*60:6.1f} min   UAV flight {res['t_uav_flight_h']*60:5.1f} min, cycle {res['t_uav_cycle_h']*60:5.1f} min")
    print(f"range check (25% reserve)  {'OK' if res['range_ok'] else 'EXCEEDED'}")
    print(f"H_reclaimed                {res['H_reclaimed']:6.1f} boat-crew hours/day ({res['deliveries_day']:.0f} urgent deliveries/day)")
    print(f"kappa = C_uav/C_boat       {res['kappa']:6.3f}   (C_uav {res['C_uav']:.3f}, C_boat {res['C_boat']:.3f} boat-h per delivery)")
    print(f"NCRI = 1 - kappa           {res['NCRI']:6.3f}")
    print(f"P_payback                  {res['P_payback']:6.3f}   (CapEx {res['capex']:.0f} boat-h, life {base['life_yr']:.0f} yr)")
    print(f"T_payback                  {res['T_payback_months']:6.2f} months  (saving {res['saving_year']:.0f} boat-h/yr)")
    print(f"M/M/c UAV  c={base['c_uav']}: lambda {base['lambda_h']}/h, mu {res['mu_uav']:.2f}/h, rho {res['rho_uav']:.3f}, Wq {res['Wq_uav_min']:.2f} min")
    print(f"M/M/c boat c={base['c_boat']}: mu {res['mu_boat']:.2f}/h, rho {res['rho_boat']:.3f}, Wq {res['Wq_boat_min']:.2f} min")
    print(f"response latency           UAV {res['latency_uav_min']:.1f} min vs boat {res['latency_boat_min']:.1f} min "
          f"-> reduction {res['latency_reduction']:.1%}")
    print(f"sensitivity (+-30 %): most influential input = {top_key} (break-even P=1 at {be_top:.3g}); "
          f"most uncertain input = {SENS_KEY}: break-even P_payback = 1 at {SENS_KEY} = {be:.4g}")
    print(f"NCRI break-even (kappa = 1) at r_uav = {be_ncri:.3g}")
    for k, label, lo, hi in tor[1]:
        print(f"   {k:<14} P_payback {lo:6.3f} .. {hi:6.3f}")
    print("-" * 72)
    print("FMEA (RPN = S x O x D)")
    for mode, eff, s, o, dd, mit, s2, o2, d2, ev in FMEA:
        print(f"  {mode[:55]:<55} RPN {s*o*dd:4d} -> {s2*o2*d2:4d}  [{ev}]")
    print("=" * 72)
    json.dump({"sim": sim, "assumptions": base, "results": res, "most_influential": top_key,
               "break_even_most_influential": be_top, "sens_key": SENS_KEY, "break_even": be, "ncri_break_even_r_uav": be_ncri,
               "tornado": [(k, lo, hi) for k, _, lo, hi in tor[1]],
               "fmea": [dict(mode=m, rpn_pre=s*o*d, rpn_post=s2*o2*d2) for m, e, s, o, d, mi, s2, o2, d2, ev in FMEA]},
              open(os.path.join(HERE, "business_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
