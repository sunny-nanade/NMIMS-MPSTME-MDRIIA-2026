# CSBS Campus Security Operations & OpEx Payback (E077) | MDRIIA Group 05
# Strictly dimensionless: every cost is a ratio to the guard baseline. No currency.
"""
Reads the guard and UAV metrics from analytics/campus_patrol_real_trials.csv
(cycle_time_s, worst_revisit_ground_s, detection_latency_s, verify_time_s) per
scene and condition, and combines them with the inputs in SOURCES. Each input
is either sourced (citation printed) or a labelled ASSUMPTION range.

  python analytics/campus_security_economics.py            # print everything
  python analytics/campus_security_economics.py --no-figures
  (needs analytics/campus_patrol_real_trials.provenance.json with "csv_sha256", and
   analytics/ablation_trials.csv with its provenance, for the FMEA; exits with an error otherwise)

Revisit gate: when every run of a scene has worst_revisit_ground_eqwin_s (worst revisit over the same
equal window for guard and UAV, computed from each run's own trajectory) the guard value is right-censored
(>= eqwin_s, a lower bound), so the gate PASSES only if EVERY UAV worst revisit in the cell is < eqwin_s
(analytics/censored_revisit.py; the output prints this reasoning). Otherwise (older CSV without the column) it
falls back to worst_revisit_ground_s with the UAV mean no larger than the guard's, and the output says which. The primary metric is cycle_time_s per completed lap (window-independent).
All means carry 95 % t-based confidence intervals (scipy.stats.t, n - 1 degrees of freedom).

Cost unit L = one year of the guard patrol labour H_patrol (so L = 1).
  H_patrol    = (24 / hours_per_shift) x rounds_per_shift x guards_per_round x T_guard_cycle   [guard-h/day]
  H_reclaimed = replacement_fraction x H_patrol, only if the UAV mean worst revisit
                passes the revisit gate; delta FTE = H_reclaimed x 365 / 2080
  k = capex_ratio (fleet acquisition / L), R = replacement_fraction (saving per year / L)
  u = maintenance_fraction + other_opex_fraction + battery_capex_share x cycles_per_UAV_year / battery_cycle_life
  kappa = k u / R  (annual fleet running cost over the annual value of reclaimed hours);  NCRI = 1 - kappa
  P_payback = k / (T_life (R - k u))  (< 1 = pays back inside the service life);  T_payback = 12 k / (R - k u) months
  M/M/c: rho = lambda / (c mu);  W_q = C(c, lambda/mu) / (c mu - lambda)  (Erlang C)
Base case = midpoint of every range; envelope = min/max over all range corners.
"""
import argparse
import csv
import itertools
import math
import os
import statistics as st
import sys

from scipy.stats import t as student_t

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import campus_security_fmea as fmea  # noqa: E402
import censored_revisit as cr  # noqa: E402

CSV_PATH = fmea.CSV_PATH
PROV_PATH = fmea.PROV_PATH   # carries "csv_sha256": the expected hash is read from here, never typed in a script
verify_csv_sha256 = fmea.verify_csv_sha256
EQWIN_COL = "worst_revisit_ground_eqwin_s"
FIG_DIR = os.path.join(HERE, "figures")
SCENES = ("interior", "exterior")
UAV_CONDITIONS = ("uav_sectors", "uav_offset_ring")
HOURS_PER_MONTH = 365 / 12 * 24
SWEEP = 0.30
RHO_STRESS = 0.4        # ASSUMPTION: operating point of the queue tornado
STRESS_RHOS = (0.5, 0.8, 0.9, 0.95)
NA = "n/a (gate FAIL)"   # printed instead of kappa, NCRI and payback when the revisit gate fails

# name: (value or (low, high), unit, "sourced" | "ASSUMPTION", citation)
SOURCES = {
    "hours_per_shift": (8, "h/shift", "sourced",
        "OSH and Working Conditions Code 2020 s.25(1)(a), 8 h/day cap (docs/research/sources_verified.md); 3 x 8 h pattern itself is an ASSUMPTION"),
    "rounds_per_shift": ((4, 8), "rounds/shift", "ASSUMPTION", "no primary source found (sources_verified.md)"),
    "guards_per_round": ((1, 2), "guards", "ASSUMPTION", "no primary source found (sources_verified.md)"),
    "replacement_fraction": ((0.5, 1.0), "ratio", "ASSUMPTION", "share of guard rounds the UAV rounds replace"),
    "capex_ratio": ((0.2, 1.1), "ratio to one year of guard patrol labour", "ASSUMPTION", "no primary source"),
    "service_life_years": ((2, 5), "years", "ASSUMPTION", "no primary source found (sources_verified.md)"),
    "maintenance_fraction": ((0.05, 0.20), "fraction of CapEx per year", "ASSUMPTION", "no primary source found (sources_verified.md)"),
    "other_opex_fraction": ((0.02, 0.10), "fraction of CapEx per year", "ASSUMPTION", "insurance, connectivity, spares; no primary source"),
    "battery_cycle_life": (400, "charge cycles", "sourced",
        "DJI Enterprise Matrice 350 RTK product page, '400 Battery Cycles' (reference airframe, not our model)"),
    "battery_capex_share": ((0.03, 0.08), "fraction of fleet CapEx per replacement of all packs", "ASSUMPTION", "no primary source"),
    "endurance_min": ((15, 30), "min per charge", "ASSUMPTION", "no primary source"),
    "n_uav": (2, "vehicles", "sourced", "project design: two UAVs in src/aerial_patrol_swarm.py"),
    "fte_hours_per_year": (2080, "h/year", "sourced", "course Academic & Industry Standards Manual s.3 (delta FTE formula)"),
    "kappa_target": (0.25, "ratio", "sourced",
        "course Academic & Industry Standards Manual s.3, as cited in docs/submission/viva_prep_E077.md (manual not in this repo)"),
    "incidents_per_month": ((1, 10), "incidents/month", "ASSUMPTION", "no primary source found (sources_verified.md)"),
    "guard_response_min": ((2, 10), "min", "ASSUMPTION", "no primary source found (sources_verified.md)"),
    "guard_responders": ((1, 3), "responders (c)", "ASSUMPTION", "no primary source"),
    "human_confirm_s": ((30, 120), "s", "ASSUMPTION",
        "human operator confirmation after the UAV verify step; used only in the queue stress cases, not the base-case queue"),
}
# Inputs that enter P_payback and kappa; the corner envelope runs over the ASSUMPTION ones.
COST_INPUTS = ("rounds_per_shift", "guards_per_round", "replacement_fraction", "capex_ratio",
               "service_life_years", "maintenance_fraction", "other_opex_fraction",
               "battery_capex_share", "endurance_min")


def is_range(v):
    return isinstance(v, tuple)


def base_case():
    return {k: (sum(v[0]) / 2 if is_range(v[0]) else v[0]) for k, v in SOURCES.items()}


def most_uncertain():
    """ASSUMPTION input of P_payback/kappa with the widest relative range (hi - lo) / midpoint."""
    rel = {k: (SOURCES[k][0][1] - SOURCES[k][0][0]) / (sum(SOURCES[k][0]) / 2) for k in COST_INPUTS}
    return max(rel, key=rel.get), rel


# ----------------------------------------------------------------------------- measured inputs
def t_ci(values, conf=0.95):
    """(mean, lo, hi): t-based confidence interval of the mean (n - 1 degrees of freedom); lo = hi = nan if n < 2."""
    n = len(values)
    m = st.mean(values)
    if n < 2:
        return m, math.nan, math.nan
    h = float(student_t.ppf(0.5 + conf / 2, n - 1)) * st.stdev(values) / math.sqrt(n)
    return m, m - h, m + h


def cell_window(sel):
    """The single eqwin_s of a cell, from the CSV column (no typed constant)."""
    w = sorted({float(r["eqwin_s"]) for r in sel})
    if len(w) != 1:
        raise ValueError(f"one eqwin_s per cell expected, got {w}")
    return w[0]


def load_metrics(path=CSV_PATH):
    """(rows, metrics) per (scene, condition). worst_s is the gate metric of the scene: the equal-window revisit
    when every run of the scene has it, else worst_revisit_ground_s (basis says which)."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for scene in SCENES:
        in_scene = [r for r in rows if r["scene"] == scene]
        eq = bool(in_scene) and all(r.get(EQWIN_COL, "") != "" for r in in_scene)
        worst_col = EQWIN_COL if eq else "worst_revisit_ground_s"
        for cond in ("guard_baseline",) + UAV_CONDITIONS:
            sel = [r for r in in_scene if r["condition"] == cond]
            vals = lambda col: [float(r[col]) for r in sel if r.get(col, "") != ""]  # noqa: E731
            cyc, wor = vals("cycle_time_s"), vals(worst_col)
            det = [r for r in sel if r["detected"] == "1"]
            service = None
            if det and all(r["verify_time_s"] != "" for r in det):
                service = st.mean(float(r["detection_latency_s"]) + float(r["verify_time_s"]) for r in det)
            out[(scene, cond)] = dict(n=len(sel), cycle_s=st.mean(cyc), cycle_ci=t_ci(cyc), n_cycle=len(cyc),
                                      worst_s=st.mean(wor), worst_ci=(None if eq else t_ci(wor)), n_worst=len(wor),  # no CI on the censored eqwin metric
                                      basis=worst_col, n_detected=len(det), service_s=service,
                                      worst_max_s=max(wor), worst_values=wor,
                                      window_s=cell_window(sel) if eq else None)
    return rows, out


# ----------------------------------------------------------------------------- the model
def h_patrol(p, t_guard_cycle_s):
    return (24 / p["hours_per_shift"]) * p["rounds_per_shift"] * p["guards_per_round"] * t_guard_cycle_s / 3600


def cycles_per_uav_year(p, t_uav_cycle_s):
    """Each replaced round is one UAV cycle flown by every UAV; one charge per endurance_min of flight."""
    flight_h = (24 / p["hours_per_shift"]) * p["rounds_per_shift"] * p["replacement_fraction"] * t_uav_cycle_s / 3600 * 365
    return flight_h * 60 / p["endurance_min"]


def running_fraction(p, t_uav_cycle_s):
    battery = p["battery_capex_share"] * cycles_per_uav_year(p, t_uav_cycle_s) / p["battery_cycle_life"]
    return p["maintenance_fraction"] + p["other_opex_fraction"] + battery


def kappa(p, t_uav_cycle_s):
    return p["capex_ratio"] * running_fraction(p, t_uav_cycle_s) / p["replacement_fraction"]


def net_saving(p, t_uav_cycle_s):
    return p["replacement_fraction"] - p["capex_ratio"] * running_fraction(p, t_uav_cycle_s)


def p_payback(p, t_uav_cycle_s):
    s = net_saving(p, t_uav_cycle_s)
    return math.inf if s <= 0 else p["capex_ratio"] / (p["service_life_years"] * s)


def t_payback_months(p, t_uav_cycle_s):
    s = net_saving(p, t_uav_cycle_s)
    return math.inf if s <= 0 else 12 * p["capex_ratio"] / s


def corners(p0):
    keys = [k for k in COST_INPUTS if SOURCES[k][2] == "ASSUMPTION"]
    for combo in itertools.product(*(SOURCES[k][0] for k in keys)):
        yield dict(p0, **dict(zip(keys, combo)))


def erlang_c(c, a):
    """Probability an arrival waits, M/M/c with offered load a = lambda/mu < c."""
    top = a ** c / math.factorial(c) * c / (c - a)
    return top / (sum(a ** k / math.factorial(k) for k in range(c)) + top)


def mmc(lam_h, mu_h, c):
    rho = lam_h / (c * mu_h)
    if rho >= 1:
        return rho, 1.0, math.inf
    pw = erlang_c(c, lam_h / mu_h)
    return rho, pw, pw / (c * mu_h - lam_h) * 3600


def bisect(f, lo, hi, tol=1e-9):
    """Root of f in [lo, hi] by bisection, or None if f does not change sign."""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid)
        if fm == 0 or hi - lo < tol:
            return mid
        if flo * fm < 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2




def crossing_capex(p, t_uav):
    """capex_ratio at which P_payback = 1 (searched over the whole range where a saving exists), or None."""
    u = running_fraction(p, t_uav)
    k_max = p["replacement_fraction"] / u            # net saving is zero here
    return bisect(lambda x: p_payback(dict(p, capex_ratio=x), t_uav) - 1, 1e-9, k_max * (1 - 1e-9))


def tornado_cost(p0, t_uav):
    """[(input, P at -30 %, P at +30 %)] for every ASSUMPTION input of P_payback, widest swing first."""
    rows = []
    for k in COST_INPUTS:
        if SOURCES[k][2] != "ASSUMPTION":
            continue
        lo = p_payback(dict(p0, **{k: p0[k] * (1 - SWEEP)}), t_uav)
        hi = p_payback(dict(p0, **{k: p0[k] * (1 + SWEEP)}), t_uav)
        rows.append((k, lo, hi))
    return sorted(rows, key=lambda r: -(abs(r[2] - r[1]) if not (math.isinf(r[1]) or math.isinf(r[2])) else math.inf))


def tornado_queue(p0, service_s):
    """[(label, % change of W_q at -30 %, at +30 %)] at the stress operating point rho = RHO_STRESS (ASSUMPTION)."""
    cu, h0 = int(p0["n_uav"]), p0["human_confirm_s"]
    mu0 = 3600 / (service_s + h0)
    lam_u = RHO_STRESS * cu * mu0
    gc0, gmu0 = int(p0["guard_responders"]), 60 / p0["guard_response_min"]
    lam_g = RHO_STRESS * gc0 * gmu0
    base_u, base_g = mmc(lam_u, mu0, cu)[2], mmc(lam_g, gmu0, gc0)[2]
    pct = lambda w, b: 100 * (w / b - 1)  # noqa: E731
    out = []
    for lab, fn in (
        ("human_confirm_s (UAV)", lambda f: pct(mmc(lam_u, 3600 / (service_s + h0 * f), cu)[2], base_u)),
        ("incident rate (UAV)", lambda f: pct(mmc(lam_u * f, mu0, cu)[2], base_u)),
        ("guard_response_min (guard)", lambda f: pct(mmc(lam_g, 60 / (p0["guard_response_min"] * f), gc0)[2], base_g)),
        ("guard_responders (guard)", lambda f: pct(mmc(lam_g, gmu0, max(1, round(gc0 * f)))[2], base_g)),
        ("incident rate (guard)", lambda f: pct(mmc(lam_g * f, gmu0, gc0)[2], base_g)),
    ):
        out.append((lab, fn(1 - SWEEP), fn(1 + SWEEP)))
    return sorted(out, key=lambda r: -abs(r[2] - r[1]) if not math.isinf(abs(r[2] - r[1])) else -1e18)


def queue_systems(p0, res):
    """name -> (mu per hour, label). UAV mu = 1 / (measured mean detection_latency_s + verify_time_s + human_confirm_s midpoint)."""
    systems = {}
    for scene in SCENES:
        svc = [3600 / res[(scene, c)]["mu"] for c in UAV_CONDITIONS if res[(scene, c)]["mu"]]
        if svc:
            mu = 3600 / (st.mean(svc) + p0["human_confirm_s"])
            systems["UAV " + scene] = (mu, f"UAV {scene}: measured latency + verify, plus human_confirm_s "
                                            f"{p0['human_confirm_s']:g} s (ASSUMPTION midpoint)")
    systems["guard"] = (60 / p0["guard_response_min"],
                        f"guard: guard_response_min {p0['guard_response_min']:g} min (ASSUMPTION midpoint)")
    return systems


def stress_rows(mu, c):
    """[(rho, lambda per h, lambda per month, P_wait, W_q s)] for the stress utilisations."""
    out = []
    for rho in STRESS_RHOS:
        lam = rho * c * mu
        r, pw, wq = mmc(lam, mu, c)
        out.append((rho, lam, lam * HOURS_PER_MONTH, pw, wq))
    return out


# ----------------------------------------------------------------------------- report
def fmt(x, nd=3):
    return "never" if math.isinf(x) else f"{x:.{nd}f}"


def ci_text(ci, nd=2):
    return "CI n/a (n < 2)" if math.isnan(ci[1]) else f"95% t-CI {ci[1]:.{nd}f} to {ci[2]:.{nd}f}"


def print_sources():
    print("SOURCES (every input: sourced with citation, or a labelled ASSUMPTION range)")
    for k, (v, unit, kind, cite) in SOURCES.items():
        val = f"{v[0]:g} to {v[1]:g}" if is_range(v) else f"{v:g}"
        print(f"  {k:<22} {val:<12} [{unit}]  {kind}")
        print(f"      source: {cite}")
    print()


def analyse(metrics):
    """All numbers for every scene and UAV condition (base case, envelope, sweep, break-even, queue)."""
    p0 = base_case()
    key, _ = most_uncertain()
    lo, hi = SOURCES[key][0]
    res = {}
    for scene in SCENES:
        g = metrics[(scene, "guard_baseline")]
        for cond in UAV_CONDITIONS:
            u = metrics[(scene, cond)]
            t_uav = u["cycle_s"]
            if u.get("window_s") is not None:   # equal-window basis: guard is right-censored (lower bound)
                gate = cr.revisit_gate(u["worst_values"], u["window_s"])
            else:                               # fallback basis: per-run windows, mean comparison
                gate = u["worst_s"] <= g["worst_s"]
            H = p0["replacement_fraction"] * h_patrol(p0, g["cycle_s"]) if gate else 0.0
            if gate:
                env = [(kappa(c, t_uav), p_payback(c, t_uav)) for c in corners(p0)]
                sweep = [p0[key] * (1 + x) for x in (-SWEEP, -SWEEP / 2, 0.0, SWEEP / 2, SWEEP)]
                be = bisect(lambda x: p_payback(dict(p0, **{key: x}), t_uav) - 1, lo, hi)
                be_sweep = bisect(lambda x: p_payback(dict(p0, **{key: x}), t_uav) - 1, sweep[0], sweep[-1])
                k_target = bisect(lambda x: kappa(dict(p0, capex_ratio=x), t_uav) - p0["kappa_target"], 1e-9, 1e3)
                cross = crossing_capex(p0, t_uav)
                econ = dict(
                    kappa=kappa(p0, t_uav),
                    kappa_env=(min(e[0] for e in env), max(e[0] for e in env)),
                    P=p_payback(p0, t_uav), P_env=(min(e[1] for e in env), max(e[1] for e in env)),
                    never=sum(1 for e in env if math.isinf(e[1])), n_corners=len(env),
                    T=t_payback_months(p0, t_uav), sweep=sweep,
                    sweep_P=[p_payback(dict(p0, **{key: x}), t_uav) for x in sweep],
                    sweep_NCRI=[1 - kappa(dict(p0, **{key: x}), t_uav) for x in sweep],
                    be=be, be_sweep=be_sweep, k_target=k_target, crossing=cross,
                    cross_dist=None if cross is None else cross - p0[key],
                    cross_rel=None if cross is None else (cross - p0[key]) / p0[key],
                    tornado=tornado_cost(p0, t_uav))
            else:   # gate FAIL: the saving is not earned, so kappa, NCRI and payback are not reported
                econ = dict(kappa=None, kappa_env=None, P=None, P_env=None, never=None, n_corners=None,
                            T=None, sweep=None, sweep_P=None, sweep_NCRI=None, be=None, be_sweep=None,
                            k_target=None, crossing=None, cross_dist=None, cross_rel=None, tornado=None)
            low_rate, high_rate = SOURCES["incidents_per_month"][0]
            lam = {"low": low_rate / HOURS_PER_MONTH, "base": p0["incidents_per_month"] / HOURS_PER_MONTH,
                   "high": high_rate / HOURS_PER_MONTH}
            mu = 3600 / u["service_s"] if u["service_s"] else None
            queue = {n: mmc(lam[n], mu, int(p0["n_uav"])) for n in ("low", "base", "high")} if mu else {}
            guard_mu = 60 / p0["guard_response_min"]
            guard_c = int(p0["guard_responders"])
            res[(scene, cond)] = dict(
                gate=gate, H=H, fte=H * 365 / p0["fte_hours_per_year"], t_uav=t_uav,
                cycles=cycles_per_uav_year(p0, t_uav), key=key, **econ,
                lam=lam, mu=mu, queue=queue,
                guard=(guard_mu, guard_c, {n: mmc(lam[n], guard_mu, guard_c) for n in lam}),
                guard_cycle_s=g["cycle_s"], guard_worst_s=g["worst_s"], uav_worst_s=u["worst_s"],
                window_s=u.get("window_s"), uav_worst_max_s=u["worst_max_s"],
                guard_censored=(cr.censored_count(g["worst_values"], g["window_s"]) if g.get("window_s") is not None else None),
                n_guard_worst=g["n_worst"],
                guard_cycle_ci=g["cycle_ci"], uav_cycle_ci=u["cycle_ci"],
                guard_worst_ci=g["worst_ci"], uav_worst_ci=u["worst_ci"], basis=g["basis"],
                n_guard=g["n_cycle"], n_uav_runs=u["n_cycle"])
    return p0, res


def print_results(p0, res):
    key, rel = most_uncertain()
    print(f"Base case = midpoint of each range. Most uncertain cost input = {key} "
          f"(relative range {rel[key]:.3f}); swept -{SWEEP:.0%} .. +{SWEEP:.0%} of its base value {p0[key]:g}, "
          "and over the full range up to the break-even.")
    lo, hi = SOURCES[key][0]
    for scene in SCENES:
        print()
        print(f"SCENE: {scene}")
        first = res[(scene, UAV_CONDITIONS[0])]
        eqb = first["basis"] == EQWIN_COL
        basis = ("worst_revisit_ground_eqwin_s (equal window for guard and UAV)" if eqb
                 else "worst_revisit_ground_s (each run's own window)")
        print(f"revisit gate metric: {basis}")
        print(f"guard_baseline cycle_time_s mean {first['guard_cycle_s']:.2f} s ({ci_text(first['guard_cycle_ci'])}, n={first['n_guard']})")
        if eqb:
            print(f"guard_baseline worst revisit {cr.guard_value_text(first['window_s'])}: {first['guard_censored']} of "
                  f"{first['n_guard_worst']} guard runs had no revisit inside {first['window_s']:g} s (lower bound, not a mean)")
            print(f"revisit gate reasoning: {cr.GATE_REASONING}")
        else:
            print(f"guard_baseline worst revisit mean {first['guard_worst_s']:.2f} s ({ci_text(first['guard_worst_ci'])})")
        for cond in UAV_CONDITIONS:
            r = res[(scene, cond)]
            print(f"{cond} cycle_time_s mean {r['t_uav']:.2f} s ({ci_text(r['uav_cycle_ci'])}, n={r['n_uav_runs']})  "
                  f"worst revisit mean {r['uav_worst_s']:.2f} s ("
                  f"{'descriptive, no CI: equal-window metric' if r['uav_worst_ci'] is None else ci_text(r['uav_worst_ci'])}), "
                  f"max {r['uav_worst_max_s']:.2f} s")
            if r["window_s"] is not None:
                print(f"  gate (every UAV worst revisit < {r['window_s']:g} s; max {r['uav_worst_max_s']:.2f} s): {'PASS' if r['gate'] else 'FAIL'}")
            else:
                print(f"  gate (UAV worst revisit <= guard worst revisit): {'PASS' if r['gate'] else 'FAIL'}")
            print(f"  H_reclaimed {r['H']:.2f} guard-hours/day  delta FTE = {r['H']:.2f} x 365 / {p0['fte_hours_per_year']:g} = {r['fte']:.3f}")
            if not r["gate"]:
                print(f"  kappa {NA}")
                print(f"  NCRI = 1 - kappa {NA}")
                print(f"  P_payback {NA}")
                print(f"  T_payback {NA}")
            else:
                met = "met" if r["kappa"] <= p0["kappa_target"] else "not met"
                print(f"  kappa {r['kappa']:.3f}  (target <= {p0['kappa_target']:g}: {met})")
                print(f"  NCRI = 1 - kappa {1 - r['kappa']:.3f}  envelope {1 - r['kappa_env'][1]:.3f} .. {1 - r['kappa_env'][0]:.3f}")
                print(f"  P_payback {fmt(r['P'])}  envelope {fmt(r['P_env'][0])} .. {fmt(r['P_env'][1])}  "
                      f"({r['never']} of {r['n_corners']} corners never pay back)")
                print(f"  T_payback {fmt(r['T'], 1)} months  (battery cycles per UAV-year {r['cycles']:.0f})")
                if r["be"] is None:
                    be = f"none inside the assumed range ({lo:g}, {hi:g})"
                else:
                    be = f"{key} = {r['be']:.3f}"
                print(f"  break-even on {key} (P_payback = 1) inside the assumed range: {be}")
                print(f"  sweep {key} " + "  ".join(f"{x:.3f}: P {fmt(pp)} NCRI {n:.3f}"
                                                     for x, pp, n in zip(r["sweep"], r["sweep_P"], r["sweep_NCRI"])))
                inside = "none inside the +/-30 % sweep" if r["be_sweep"] is None else f"{r['be_sweep']:.3f}"
                print(f"  break-even inside the +/-30 % sweep: {inside}")
                if r["crossing"] is None:
                    print("  break-even crossing (full search): none")
                else:
                    in_rng = "inside" if lo <= r["crossing"] <= hi else "outside"
                    in_swp = "inside" if r["sweep"][0] <= r["crossing"] <= r["sweep"][-1] else "outside"
                    print(f"  break-even crossing (full search, P_payback = 1): {key} = {r['crossing']:.3f}; distance from base "
                          f"{r['cross_dist']:+.3f} ({r['cross_rel']:+.1%}); {in_rng} the assumed range ({lo:g}, {hi:g}), {in_swp} the +/-30 % sweep")
                print(f"  capex_ratio at kappa = target: {fmt(r['k_target'])}")
            for n in ("low", "base", "high"):
                if r["mu"] is None:
                    continue
                rho, pw, wq = r["queue"][n]
                print(f"  M/M/c lambda {n:<4}  lambda={r['lam'][n]:.5f}/h mu={r['mu']:.3f}/h c={int(p0['n_uav'])} "
                      f"rho={rho:.5f} P_wait={pw:.3e} W_q={wq:.3e} s  [UAV; mu = 1 / mean(detection_latency_s + verify_time_s), detected runs]")
            gmu, gc, gq = r["guard"]
            rho, pw, wq = gq["base"]
            print(f"  guard M/M/c base  lambda={r['lam']['base']:.5f}/h mu={gmu:.3f}/h c={gc} rho={rho:.5f} "
                  f"P_wait={pw:.3e} W_q={wq:.3e} s  [guard_response_min and guard_responders midpoints, ASSUMPTION]")
    print()
    print_tornado(p0, res)
    print()
    print_stress(p0, res)


def tornado_cells(res):
    """One gate-PASS cell per scene for the tornado (uav_offset_ring preferred), as {scene: cond}."""
    out = {}
    for scene in SCENES:
        for cond in ("uav_offset_ring", "uav_sectors"):
            if res[(scene, cond)]["gate"]:
                out[scene] = cond
                break
    return out


def print_tornado(p0, res):
    print(f"TORNADO: every ASSUMPTION input of P_payback at -{SWEEP:.0%} / +{SWEEP:.0%} of its base value, others at base")
    for scene, cond in tornado_cells(res).items():
        r = res[(scene, cond)]
        print(f"  {scene} {cond}: base P_payback {fmt(r['P'])}")
        for k, lo_p, hi_p in r["tornado"]:
            print(f"    {k:<22} base {p0[k]:g}  P at -30 %: {fmt(lo_p)}   P at +30 %: {fmt(hi_p)}")
    for scene in SCENES:
        if scene not in tornado_cells(res):
            print(f"  {scene}: {NA}")
    systems = queue_systems(p0, res)
    print(f"TORNADO (queue): % change of W_q for -{SWEEP:.0%} / +{SWEEP:.0%} of each queue ASSUMPTION, at the stress operating point "
          f"rho = {RHO_STRESS:g} (ASSUMPTION), c as base")
    for scene in SCENES:
        if "UAV " + scene in systems:
            svc = 3600 / systems["UAV " + scene][0] - p0["human_confirm_s"]
            print(f"  (UAV mu from {scene}; guard rows use the ASSUMPTION guard mu and c):")
            for lab, a, b in tornado_queue(p0, svc):
                print(f"    {lab:<28} W_q change at -30 %: {a:+.1f} %   at +30 %: {b:+.1f} %")
            break


def print_stress(p0, res):
    print("QUEUE STRESS CASES (G-17): lambda raised until the queue is non-trivial; every input labelled")
    print(f"  lambda range is an ASSUMPTION; base incident rate {p0['incidents_per_month']:g}/month "
          f"({p0['incidents_per_month'] / HOURS_PER_MONTH:.5f}/h)")
    for name, (mu, label) in queue_systems(p0, res).items():
        print(f"  {label}; mu = {mu:.3f}/h")
        for c in (1, 2):
            print(f"    c = {c}:")
            for rho, lam, lam_m, pw, wq in stress_rows(mu, c):
                print(f"      rho {rho:.2f}  lambda {lam:.3f}/h ({lam_m:.0f} incidents/month)  P_wait {pw:.3f}  W_q {wq:.1f} s")


# ----------------------------------------------------------------------------- figures
def _save(fig, path):
    fig.savefig(path, dpi=300, metadata={"Software": None})


def save_figures(p0, res, out_dir=FIG_DIR):
    """campus_security_sensitivity / queue / breakeven / tornado .png at 300 DPI; returns the four paths."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(out_dir, exist_ok=True)
    key, _ = most_uncertain()
    lo_a, hi_a = SOURCES[key][0]
    failed = [f"{scene} {cond.replace('uav_', '')}" for (scene, cond), r in res.items() if not r["gate"]]
    passed = {k: r for k, r in res.items() if r["gate"]}
    footer = "Inputs: real-trials CSV + ASSUMPTION ranges at their midpoints (analytics/campus_security_economics.py)"

    # ---- sensitivity (+/-30 %)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
    for (scene, cond), r in passed.items():
        xs = [p0[key] * (1 + x / 100) for x in range(-30, 31)]
        lab = f"{scene} {cond.replace('uav_', '')}"
        a1.plot(xs, [p_payback(dict(p0, **{key: x}), r["t_uav"]) for x in xs], label=lab)
        a2.plot(xs, [1 - kappa(dict(p0, **{key: x}), r["t_uav"]) for x in xs], label=lab)
    a1.axhline(1, color="k", ls="--", lw=1)
    a1.set(xlabel=f"{key} (ratio to one year of guard patrol labour)", ylabel="P_payback (dimensionless)",
           title="P_payback, base case, +/-30 % sweep")
    a2.axhline(1 - p0["kappa_target"], color="k", ls="--", lw=1)
    a2.set(xlabel=f"{key} (ratio)", ylabel="NCRI = 1 - kappa", title=f"NCRI (dashed: kappa = {p0['kappa_target']:g})")
    if passed:
        a1.legend(fontsize=8)
    for i, name in enumerate(failed):
        for ax in (a1, a2):
            ax.text(0.02, 0.97 - 0.06 * i, f"{name}: {NA}", transform=ax.transAxes, fontsize=7, va="top")
    fig.text(0.5, 0.005, footer, ha="center", fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    sens = os.path.join(out_dir, "campus_security_sensitivity.png")
    _save(fig, sens)
    plt.close(fig)

    # ---- queue stress: rho and W_q against lambda, c = 1, 2
    systems = queue_systems(p0, res)
    colors = {n: f"C{i}" for i, n in enumerate(systems)}
    fig, (b1, b2) = plt.subplots(1, 2, figsize=(11, 4.4))
    lam_lo, lam_hi = (v / HOURS_PER_MONTH for v in SOURCES["incidents_per_month"][0])
    for name, (mu, _) in systems.items():
        for c, ls in ((1, "-"), (2, "--")):
            lams = [10 ** (-3 + 5 * i / 400) for i in range(401)]
            lams = [x for x in lams if x < c * mu * 0.999]
            b1.plot(lams, [x / (c * mu) for x in lams], ls, color=colors[name], label=f"{name}, c={c}")
            b2.plot(lams, [mmc(x, mu, c)[2] for x in lams], ls, color=colors[name], label=f"{name}, c={c}")
    for ax in (b1, b2):
        ax.axvspan(lam_lo, lam_hi, color="0.85", label="base incident range (ASSUMPTION)")
        ax.set_xscale("log")
        ax.set_xlabel("arrival rate lambda (incidents per hour; stress range is an ASSUMPTION)")
    b1.axhline(1, color="k", lw=0.8)
    b1.set(ylabel="utilisation rho = lambda / (c mu)", title="Utilisation against arrival rate")
    b2.set(yscale="log", ylabel="W_q (s, Erlang C)", title="Waiting time against arrival rate")
    b2.legend(fontsize=6, loc="lower right")
    fig.text(0.5, 0.005, "mu: UAV = 1/(measured mean detection_latency_s + verify_time_s + human_confirm_s ASSUMPTION midpoint); "
             "guard = 1/guard_response_min ASSUMPTION midpoint", ha="center", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    queue = os.path.join(out_dir, "campus_security_queue.png")
    _save(fig, queue)
    plt.close(fig)

    # ---- break-even over a range that contains the crossing
    fig, ax = plt.subplots(figsize=(7, 4.4))
    crosses = [r["crossing"] for r in passed.values() if r["crossing"] is not None]
    xmax = max([hi_a * 1.1] + [1.4 * c for c in crosses])
    xs = [xmax * i / 300 for i in range(1, 301)]
    ax.axvspan(lo_a, hi_a, color="0.9", label=f"assumed range {lo_a:g} to {hi_a:g}")
    ax.axvspan(p0[key] * (1 - SWEEP), p0[key] * (1 + SWEEP), color="C9", alpha=0.25, label="+/-30 % sweep")
    for i, ((scene, cond), r) in enumerate(passed.items()):
        ys = [p_payback(dict(p0, **{key: x}), r["t_uav"]) for x in xs]
        ax.plot(xs, [min(y, 5) for y in ys], color=f"C{i}", label=f"{scene} {cond.replace('uav_', '')}")
        if r["crossing"] is not None:
            ax.plot([r["crossing"]], [1], "o", color=f"C{i}")
            ax.text(0.98, 0.68 - 0.055 * i, f"{scene} {cond.replace('uav_', '')}: crossing {r['crossing']:.2f} "
                    f"({r['cross_rel']:+.0%} from base)", transform=ax.transAxes, fontsize=7, color=f"C{i}", ha="right")
    ax.axhline(1, color="k", ls="--", lw=1)
    ax.axvline(p0[key], color="k", lw=0.8)
    ax.text(p0[key], 4.6, " base", fontsize=7)
    ax.set(xlabel=f"{key} (ratio to one year of guard patrol labour)", ylabel="P_payback (clipped at 5)", ylim=(0, 5),
           title="Break-even: P_payback = 1 crossing")
    for i, name in enumerate(failed):
        ax.text(0.02, 0.97 - 0.05 * i, f"{name}: {NA}", transform=ax.transAxes, fontsize=7, va="top")
    ax.legend(fontsize=6.5, loc="upper left" if not failed else "center left")
    fig.text(0.5, 0.005, footer, ha="center", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    be_path = os.path.join(out_dir, "campus_security_breakeven.png")
    _save(fig, be_path)
    plt.close(fig)

    # ---- tornado
    fig, (t1, t2) = plt.subplots(1, 2, figsize=(11, 4.6))
    cells = tornado_cells(res)
    if cells:
        scene, cond = next(iter(cells.items()))
        r = res[(scene, cond)]
        rows = r["tornado"][::-1]
        base = r["P"]
        cap = 5.0
        for i, (k, a, b) in enumerate(rows):
            for v, col in ((a, "C0"), (b, "C1")):
                t1.barh(i, min(v, cap) - base, left=base, color=col, height=0.6)
        t1.set_yticks(range(len(rows)), [k for k, _, _ in rows])
        t1.axvline(base, color="k", lw=0.8)
        t1.axvline(1, color="k", ls="--", lw=0.8)
        t1.set(xlabel="P_payback (dashed: 1)", title=f"P_payback, ASSUMPTION inputs -30 % (blue) / +30 % (orange)\n{scene} {cond}", )
        t1.title.set_fontsize(10)
    else:
        t1.text(0.5, 0.5, f"P_payback tornado {NA}", ha="center", transform=t1.transAxes)
    svc_scene = next((s for s in SCENES if "UAV " + s in systems), None)
    if svc_scene:
        svc = 3600 / systems["UAV " + svc_scene][0] - p0["human_confirm_s"]
        rows = tornado_queue(p0, svc)[::-1]
        for i, (lab, a, b) in enumerate(rows):
            for v, col in ((a, "C0"), (b, "C1")):
                t2.barh(i, v, color=col, height=0.6)
        t2.set_yticks(range(len(rows)), [lab for lab, _, _ in rows])
        t2.axvline(0, color="k", lw=0.8)
        t2.set_xscale("symlog", linthresh=100)
        t2.set(xlabel="change of W_q (%, symlog axis)",
               title=f"Queue W_q at rho = {RHO_STRESS:g} (ASSUMPTION),\ninputs -30 % (blue) / +30 % (orange)")
    fig.text(0.5, 0.005, footer, ha="center", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    tor = os.path.join(out_dir, "campus_security_tornado.png")
    _save(fig, tor)
    plt.close(fig)
    return sens, queue, be_path, tor


def print_data_quality(rows):
    """Per scene and UAV condition: runs with obstacle contacts and runs where a ground-loop UAV lapped < 2 times.
    Computed from the CSV so a failed batch check is visible next to the numbers that include those runs."""
    print("DATA QUALITY of the main batch (computed from the CSV; the means above include every run)")
    for scene in SCENES:
        for cond in UAV_CONDITIONS:
            sel = [r for r in rows if r["scene"] == scene and r["condition"] == cond]
            if not sel:
                continue
            hit = sorted((int(r["seed"]), int(float(r["obstacle_contacts"]))) for r in sel
                         if float(r["obstacle_contacts"]) > 0)
            lap_cols = ("n_laps_alpha",) if (scene, cond) == ("interior", "uav_sectors") else ("n_laps_alpha", "n_laps_bravo")
            low = sorted((int(r["seed"]), c, int(float(r[c]))) for r in sel for c in lap_cols
                         if r.get(c, "") not in ("", None) and float(r[c]) < 2)
            print(f"  {scene} {cond}: runs with obstacle_contacts > 0: {len(hit)}/{len(sel)}"
                  + (f" (seed, contacts) {hit}" if hit else "")
                  + f"; UAV laps < 2: {len(low)}" + (f" (seed, column, laps) {low}" if low else "")
                  + (f"; min_obstacle_clearance_m min {min(float(r['min_obstacle_clearance_m']) for r in sel):.3f}"))
    print("  interior uav_sectors Bravo laps are excluded from the lap check (known 300 s limitation).")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--fig-dir", default=FIG_DIR)
    ap.add_argument("--csv", default=CSV_PATH)
    ap.add_argument("--provenance", default=PROV_PATH)
    ap.add_argument("--ablation", default=fmea.ABLATION_PATH)
    ap.add_argument("--ablation-provenance", default=fmea.ABLATION_PROV_PATH)
    a = ap.parse_args(argv)
    digest = verify_csv_sha256(a.csv, a.provenance)
    abl_rows = fmea.load_ablation(a.ablation, a.ablation_provenance)
    rows, metrics = load_metrics(a.csv)
    print("=" * 72)
    print("MDRIIA GROUP 05 - CSBS CAMPUS SECURITY ECONOMICS (E077), dimensionless")
    print(f"Data: analytics/campus_patrol_real_trials.csv, {len(rows)} rows, sha256 {digest} (matches provenance csv_sha256)")
    print(f"Ablation: analytics/ablation_trials.csv, {len(abl_rows)} rows")
    print("=" * 72)
    print_sources()
    p0, res = analyse(metrics)
    print_results(p0, res)
    print()
    print_data_quality(rows)
    print()
    fmea.print_fmea(rows, abl_rows)
    if not a.no_figures:
        group = os.path.dirname(HERE)
        for path in save_figures(p0, res, a.fig_dir):
            inside = os.path.splitdrive(path)[0] == os.path.splitdrive(group)[0]
            print(f"figure: {os.path.relpath(path, group) if inside else path}")


if __name__ == "__main__":
    main()
