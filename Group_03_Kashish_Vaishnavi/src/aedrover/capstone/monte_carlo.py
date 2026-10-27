"""Capstone Monte Carlo: baseline vs proposed controller, 500 Hz telemetry, recorded seeds.

Every row of the output CSV (``analytics/aed_delivery_real_trials.csv``) is one MuJoCo episode of
this repository's own controllers; nothing is sampled from a target distribution. Randomised per
run, from the stated scenario sampler (``sim/scenario.py``): kerb height, tyre friction, obstacle
and pedestrian layout, pedestrian speeds, and the sensor noise seed. The seed of every run is a
column, so any row can be re-run exactly.

Conditions (the titles-sheet protocol: free-flow, lane-splitting, pedestrian-crowd sidewalk):

=============== ================ =====================================================================
condition       scenario family  what it stresses
=============== ================ =====================================================================
free_flow       flat_clear       empty flat sidewalk, no kerb
lane_splitting  mixed            kerb crossing with static obstacles and pedestrians (narrow gaps)
crowd           crowded          dense pedestrian flow
kerb            kerb             12 cm class kerb up and down at varied tyre friction
slippery        slippery         low-friction surface (wet kerb)
=============== ================ =====================================================================

Controllers (label -> planner, FSM, safety filter):

* ``baseline_unshielded``  pure pursuit at constant speed, no safety filter (unmitigated reference for the FMEA)
* ``baseline``             pure pursuit at constant speed + the same safety filter
* ``proposed``             mission FSM supervising a dynamic-window planner + the safety filter
* ``proposed_codesigned`` the same software on the co-designed chassis (larger wheels, softer suspension and
                          payload isolator; experiment 06). Isolates the mechanical mitigation of payload shock.
"""

from __future__ import annotations

import functools
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..analysis.stats import TTestResult, welch_t, wilson_ci
from ..clinical.decision import DispatchTimes
from ..control.safety_filter import SafetyFilter, SafetyParams
from ..nav.base import make_controller
from ..parallel import pmap
from ..sim.env import AEDRoverEnv
from ..sim.vehicle_mjcf import VehicleParams
from . import fsm as _fsm  # noqa: F401  (registers fsm_dwa)
from .fsm import FSMParams
from .telemetry import TelemetryRecorder, summarise_frame

CONDITIONS = {
    "free_flow": "flat_clear",
    "lane_splitting": "mixed",
    "crowd": "crowded",
    "kerb": "kerb",
    "slippery": "slippery",
}
CRUISE_MPS = 3.5              # ROAD_CRUISE speed in the course guide (the CURB_SIDEWALK speed is 1.2 m/s, FSMParams.v_curb)
# Settings chosen on TUNING seeds (60000+, experiments/10_capstone_tuning.py), never on the evaluation seeds (70000+): the kerb friction
# belief is the lowest friction the sampler draws (0.35), and the safety filter assumes a 50 ms reaction time (the ISO 3691-4 figure).
_PROPOSED = {"v_cruise": CRUISE_MPS, "fsm_kwargs": {"v_cruise": CRUISE_MPS, "mu_belief": 0.35}, "safety_kwargs": {"t_react": 0.05}}
# label -> (planner, safety filter, vehicle preset, planner kwargs). ``course`` is the starter pack's vehicle (VehicleParams.course);
# ``optimized`` is this repository's co-designed chassis (experiment 06).
CONTROLLERS = {
    "baseline_unshielded": ("pure_pursuit", False, "course", {}),
    "baseline": ("pure_pursuit", True, "course", {}),
    "baseline_fast": ("pure_pursuit", True, "course", {"v_cruise": CRUISE_MPS}),   # naive controller at the course cruise speed: the unmitigated FMEA reference
    "proposed": ("fsm_dwa", True, "course", _PROPOSED),
    "proposed_codesigned": ("fsm_dwa", True, "optimized", _PROPOSED),   # same software on the mechanically co-designed chassis
}
SEED_BASE = 70_000            # disjoint from the repo's tuning/validation/evaluation/ablation ranges
HUB_RADIUS_M = 500.0          # micro-hub response radius [m]: inside the 0.46-0.58 km rover break-even of README RQ3
                              # (the course brief's 1.5 km radius is swept in analytics/aed_delivery_roi.py)
ROUTE_FACTOR = 1.54           # path / straight-line distance measured on Mumbai OSM geometry (docs/OSM_ROUTES.md)
LOG_HZ_TARGET = 500.0
PRIMARY_METRIC = "ttfs_min"


@dataclass(frozen=True)
class McJob:
    condition: str
    label: str
    seed: int
    save_telemetry: str = ""        # path of a 500 Hz CSV to write for this run ("" = do not)
    handover_s: float = FSMParams().handover_s


@functools.lru_cache(maxsize=3)
def _env(vehicle: str = "course") -> AEDRoverEnv:
    return AEDRoverEnv(obs_mode="dict", veh=VehicleParams.by_name(vehicle), log_every=1, control_dt=0.02)   # log_every=1 -> 500 Hz


def ttfs_minutes(mean_speed_mps: float, route_m: float | None = None) -> float:
    """Time to first shock from collapse for the mission: dispatch chain + d / v_bar + handover.

    ``d / v_bar`` extrapolates the simulated 36 m segment's mean speed over the hub-radius route;
    the dispatch and handover terms are the clinical model's ``DispatchTimes`` defaults.
    """
    if not np.isfinite(mean_speed_mps) or mean_speed_mps <= 0:
        return float("nan")
    d = DispatchTimes()
    route = HUB_RADIUS_M * ROUTE_FACTOR if route_m is None else route_m
    return d.collapse_to_call_min + d.call_to_alert_min + route / mean_speed_mps / 60.0 + d.handoff_min


def run_mc_job(job: McJob) -> dict:
    name, shielded, vehicle, kwargs = CONTROLLERS[job.label]
    env = _env(vehicle)
    ctrl = make_controller(name, **kwargs)
    shield = SafetyFilter(SafetyParams(**kwargs.get("safety_kwargs", {}))) if shielded else None
    family = CONDITIONS[job.condition]
    t0 = time.perf_counter()

    env.reset(seed=job.seed, options={"family": family})
    ctrl.reset(env)
    if shield is not None:
        shield.reset()
    rec = TelemetryRecorder(env.rover, y_ref=0.0)
    rec.attach()
    fsm = getattr(ctrl, "fsm", None)
    info: dict = {}
    try:
        while True:
            obs = env.obs
            v, delta = ctrl.act(obs)
            if shield is not None:
                v, delta = shield(obs, v, delta)
            rec.command(fsm.state.value if fsm else "", v, delta)
            _, _, term, trunc, info = env.step(np.array([v, delta]), want_obs=True)
            if term or trunc:
                break
        ep = info["episode"]
        transit_df = rec.frame()
        transit = summarise_frame(transit_df, env.rover.dt_phys)
        if ep["outcome"] == "goal" and fsm is not None:
            fsm.begin_handover(env._t)
        if ep["outcome"] == "goal":                                  # stationary AED handover phase
            rec.command("AED_HANDOVER" if fsm else "", 0.0, 0.0)
            for _ in range(int(job.handover_s / env.dt)):
                env.rover.step(0.0, 0.0)
        full = rec.frame()
    finally:
        rec.detach()

    mean_speed = ep["path_m"] / ep["time_s"] if ep["success"] and ep["time_s"] > 0 else float("nan")
    if job.save_telemetry:
        Path(job.save_telemetry).parent.mkdir(parents=True, exist_ok=True)
        full.to_csv(job.save_telemetry, index=False, float_format="%.6g")
    row = {
        "condition": job.condition, "family": family, "controller": job.label, "seed": job.seed,
        "outcome": ep["outcome"], "success": int(ep["success"]),
        "transit_s": ep["time_s"], "path_m": ep["path_m"], "mean_speed_mps": mean_speed,
        "ttfs_min": ttfs_minutes(mean_speed),
        "tracking_rmse_m": transit.rmse_m, "control_effort_Nm2s": transit.effort_Nm2s,
        "peak_payload_g": ep["peak_shock_g"], "shock_over_3g": int(ep["shock_over_budget"]),
        "peak_abs_slip": transit.peak_abs_slip, "min_stability_index": transit.min_stability_index,
        "min_clearance_m": ep["min_clearance_m"],
        "interventions": shield.n_interventions if shield else 0,
        "log_rate_hz": float(len(transit_df) - 1) / float(transit_df["t_s"].iloc[-1] - transit_df["t_s"].iloc[0]),
        "telemetry_rows": len(full), "fsm_transitions": len(fsm.transitions) if fsm else 0,
        "kerb_h_m": ep.get("sc_kerb_h", float("nan")), "tyre_mu": ep.get("sc_tyre_mu", float("nan")),
        "wall_s": time.perf_counter() - t0,
    }
    return row


def make_mc_jobs(n: int, conditions=None, labels=None, telemetry_dir: str | Path | None = None) -> list[McJob]:
    """``n`` paired seeds per condition; every controller sees the same ``n`` scenarios."""
    conditions = list(conditions or CONDITIONS)
    labels = list(labels or CONTROLLERS)
    jobs = []
    for ci, c in enumerate(conditions):
        for label in labels:
            for k in range(n):
                seed = SEED_BASE + 1000 * ci + k
                save = ""
                if telemetry_dir and c == "lane_splitting" and label == "proposed" and k == 0:
                    save = str(Path(telemetry_dir) / "representative_run_500hz.csv")
                jobs.append(McJob(c, label, seed, save))
    return jobs


def run_monte_carlo(n: int = 50, workers: int | None = None, telemetry_dir: str | Path | None = None,
                    conditions=None, labels=None) -> pd.DataFrame:
    jobs = make_mc_jobs(n, conditions, labels, telemetry_dir)
    return pd.DataFrame(pmap(run_mc_job, jobs, workers=workers, desc="capstone-mc"))


# ----------------------------------------------------------------- statistics
def compare(df: pd.DataFrame, metric: str, condition: str | None = None,
            a: str = "baseline", b: str = "proposed") -> TTestResult:
    """Welch t-test of ``metric`` between controllers ``a`` and ``b`` over successful runs of a condition.

    ``mean_diff = mean(a) - mean(b)``; a positive difference means ``a`` is larger. Failed runs have no
    transit time, so the success rate is tested separately by :func:`success_table`.
    """
    sub = df if condition is None else df[df["condition"] == condition]
    x = sub[(sub["controller"] == a) & (sub["success"] == 1)][metric].dropna()
    y = sub[(sub["controller"] == b) & (sub["success"] == 1)][metric].dropna()
    return welch_t(x, y)


PROTOCOL_CONDITIONS = ("free_flow", "lane_splitting", "crowd")   # the titles-sheet evaluation protocol
MEASURES = {
    "ttfs_min": "min", "transit_s": "s", "tracking_rmse_m": "m", "control_effort_Nm2s": "N^2 m^2 s",
    "peak_payload_g": "g", "peak_abs_slip": "-", "min_stability_index": "-",
}


def statistics_table(df: pd.DataFrame, a: str = "baseline", b: str = "proposed") -> pd.DataFrame:
    """Welch t, Cohen's d and 95 % CI of ``a - b`` for every measure, per condition, ALL conditions and PROTOCOL.

    ``PROTOCOL`` pools the three titles-sheet conditions (free-flow, lane-splitting, crowd); ``ALL`` also
    includes the kerb and slippery stress conditions. Only successful runs have a transit time.
    """
    groups: list[tuple[str, pd.DataFrame]] = [("PROTOCOL", df[df["condition"].isin(PROTOCOL_CONDITIONS)]), ("ALL", df)]
    groups += [(c, df[df["condition"] == c]) for c in CONDITIONS if c in set(df["condition"])]
    rows = []
    for name, sub in groups:
        for metric, unit in MEASURES.items():
            xa = sub[(sub["controller"] == a) & (sub["success"] == 1)][metric].dropna()
            xb = sub[(sub["controller"] == b) & (sub["success"] == 1)][metric].dropna()
            if len(xa) < 2 or len(xb) < 2:
                rows.append({"condition": name, "metric": metric, "unit": unit, "n_a": len(xa), "n_b": len(xb),
                             "note": "fewer than 2 successful runs in a group"})
                continue
            r = welch_t(xa, xb)
            rows.append({
                "condition": name, "metric": metric, "unit": unit, "n_a": r.n1, "n_b": r.n2,
                f"mean_{a}": xa.mean(), f"sd_{a}": xa.std(ddof=1), f"mean_{b}": xb.mean(), f"sd_{b}": xb.std(ddof=1),
                "mean_diff_a_minus_b": r.mean_diff, "t": r.t, "df": r.df, "p": r.p, "cohens_d": r.d,
                "diff_ci95_low": r.diff_ci_low, "diff_ci95_high": r.diff_ci_high, "note": "",
            })
    return pd.DataFrame(rows)


def success_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["condition", "controller"])["success"].agg(["sum", "count"]).reset_index()
    lo, hi = wilson_ci(g["sum"].to_numpy(), g["count"].to_numpy())
    g["rate"] = g["sum"] / g["count"]
    g["ci95_low"], g["ci95_high"] = lo, hi
    return g.rename(columns={"sum": "successes", "count": "n"})
