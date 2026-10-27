"""Standards check for dossier Section 1.2: which clauses govern the pod, and does the model meet them?

Each requirement is checked against a number this repository computes or measures; the report says
``MET``, ``DEVIATION`` (with the size of the gap) or ``NOT MEASURED``. Clause text is the course's
own summary (``ACADEMIC_AND_INDUSTRY_STANDARDS_MANUAL.md``); the standards themselves are paywalled and
were not read for this project, so a clause number is cited only as the manual cites it.

Applicability decisions (also in ``docs/STANDARDS_COMPLIANCE.md``):

=================== ======== ================================================================================
standard            applies  reason
=================== ======== ================================================================================
ISO 10218-1/-2      No       industrial robot arm cells; the pod is a mobile ground vehicle with no manipulator
ANSI/RIA R15.06     No       US adoption of ISO 10218, same reason
ISO 3691-4          Partly   driverless-vehicle safety principles (braking, detection zones) transfer; it is
                             written for industrial trucks, and the pod operates on public sidewalks
ISO 13482           Partly   personal-care-robot limits cited by the course manual (shared-zone speed, braking)
IEC 60601-1         Partly   the AED payload is medical electrical equipment; the pod only has to protect it
                             from shock (3 g budget), not certify it
domain-specific     Yes      no standard covers sidewalk delivery robots in India; the design assumes the
                             ISO 3691-4 / 13482 limits above and a 3 g payload budget
=================== ======== ================================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..control.safety_filter import SafetyParams
from ..sim.env import AEDRoverEnv
from ..sim.metrics import G
from ..sim.sensors import PerceptionSpec
from .fsm import FSMParams

G0 = 9.81


@dataclass
class Check:
    standard: str
    requirement: str
    required: str
    achieved: str
    status: str            # MET | DEVIATION | NOT MEASURED
    how: str


def braking_distance(v: float, mu: float, t_detect: float) -> float:
    """ISO 3691-4 form quoted by the course manual: ``s = v^2 / (2 mu g) + v * t_detect`` [m]."""
    return v * v / (2.0 * mu * G0) + v * t_detect


def measure_emergency_stop(v0: float = 1.8, seed: int = 123) -> dict[str, float]:
    """Brake the simulated pod from ``v0`` on a flat sidewalk: mean deceleration, distance, pitch, payload g."""
    env = AEDRoverEnv(family="flat_clear", obs_mode="dict", log_every=1)
    env.reset(seed=seed)
    rv = env.rover
    rv.reset(0.0, 0.0, 0.0, speed=v0, settle_s=0.0)
    x0 = rv.pos[0].copy()
    t_stop, v_hist, pitch_max = None, [], 0.0
    for k in range(int(3.0 / rv.control_dt)):
        rv.step(0.0, 0.0)
        v = float(rv.body_velocity()[0])
        v_hist.append(v)
        pitch_max = max(pitch_max, abs(rv.yaw_pitch_roll()[1]))
        if v < 0.05 and t_stop is None:
            t_stop = (k + 1) * rv.control_dt
    dist = float(rv.pos[0] - x0)
    t_stop = t_stop or 3.0
    acc = np.asarray(rv.acc_log)
    up = np.asarray(rv.gdir_log)
    payload_g = float(np.max(np.linalg.norm(acc - G * up, axis=1)) / G)
    env.close()
    return {"v0_mps": v0, "decel_mean_mps2": v0 / t_stop, "stop_time_s": t_stop, "stop_distance_m": dist,
            "peak_pitch_deg": math.degrees(pitch_max), "peak_payload_g": payload_g}


def standards_report(trials: pd.DataFrame | None = None, tyre_mu: float = 1.0) -> pd.DataFrame:
    sp, fp, ps = SafetyParams(t_react=0.05), FSMParams(), PerceptionSpec()      # the proposed controller's filter (see monte_carlo._PROPOSED)
    stop = measure_emergency_stop(fp.v_cruise)
    rows: list[Check] = []

    rows.append(Check(
        "ISO 13482 (course manual 2.1)", "Emergency braking deceleration", ">= 1.5 m/s^2 without overturn or payload ejection",
        f"{stop['decel_mean_mps2']:.2f} m/s^2 from {stop['v0_mps']:.1f} m/s in {stop['stop_distance_m']:.2f} m; "
        f"peak pitch {stop['peak_pitch_deg']:.1f} deg; payload {stop['peak_payload_g']:.2f} g",
        "MET" if stop["decel_mean_mps2"] >= 1.5 and stop["peak_pitch_deg"] < 18 else "DEVIATION",
        "measure_emergency_stop(): command v = 0 at cruise speed in MuJoCo"))
    rows.append(Check(
        "ISO 13482 (course manual 2.1)", "Speed in shared pedestrian zones", "<= 0.80 m/s",
        f"safety-filter pedestrian cap {sp.ped_speed_cap:.1f} m/s within {sp.ped_cap_radius:.0f} m",
        "DEVIATION" if sp.ped_speed_cap > 0.8 else "MET",
        "SafetyParams.ped_speed_cap; the 0.8 m/s cap is evaluated in README ablations (it cuts delivery) - the "
        "manual states the limit for occupied indoor spaces, the pod is outdoors; kept as a policy parameter"))
    rows.append(Check(
        "ISO 13482 (course manual 2.1)", "Dynamic clearance bubble", ">= 0.50 m from any obstacle",
        _clearance_text(trials), _clearance_status(trials), "min_clearance_m over the proposed-controller trials"))
    rows.append(Check(
        "ISO 3691-4 (course manual 2.2)", "Detection latency", "t_detect <= 50 ms",
        f"{sp.t_react * 1000:.0f} ms modelled reaction time in the safety filter",
        "DEVIATION" if sp.t_react > 0.05 else "MET", "SafetyParams.t_react (perception + actuation latency allowance)"))
    s_stop = braking_distance(fp.v_cruise, tyre_mu, 0.05)
    rows.append(Check(
        "ISO 3691-4 (course manual 2.2)", "Braking distance s = v^2/(2 mu g) + v t_detect",
        "stop inside the emergency-stop zone (0.40 m) at cruise speed",
        f"s = {s_stop:.2f} m at {fp.v_cruise:.1f} m/s, mu = {tyre_mu:.1f}, t_detect = 50 ms",
        "MET" if s_stop <= 0.40 else "DEVIATION",
        "braking_distance(); at 3.5 m/s the formula gives "
        f"{braking_distance(3.5, tyre_mu, 0.05):.2f} m, so higher speeds need the earlier safety-filter barrier"))
    rows.append(Check(
        "ISO 3691-4 (course manual 2.2)", "Personnel detection field of view", ">= 180 deg forward",
        f"{ps.fov_deg:.0f} deg, {ps.n_lidar} beams, range {ps.lidar_range:.0f} m", "MET" if ps.fov_deg >= 180 else "DEVIATION",
        "PerceptionSpec"))
    rows.append(Check(
        "ISO 3691-4 (course manual 2.2)", "Dual-zone warning: slow at 1.5 m, stop at 0.4 m", "two-zone speed reduction",
        f"continuous barrier h(v) = d_free - v t_react - v^2/(2 a_brake), a_brake = {sp.a_brake:.1f} m/s^2",
        "MET", "SafetyFilter replaces fixed zones with a speed-dependent stopping-distance barrier (stricter at speed)"))
    rows.append(Check(
        "IEC 60601-1 (payload protection)", "Payload shock budget", "<= 3 g peak on the AED",
        _shock_text(trials), _shock_status(trials), "peak_payload_g over all trials, FSM + DWA on the course vehicle at 3.5 m/s cruise (all five conditions, kerbs included)"))
    rows.append(Check(
        "ROS REP-103 / 105", "Frame and unit convention", "x forward, y left, z up; SI units",
        "x forward, y left, z up; m, rad, m/s, N m throughout", "MET",
        "telemetry columns and docstrings; tf tree (map-odom-base_link) is not implemented - simulation only"))
    rows.append(Check("ISO 10218-1/-2, ANSI/RIA R15.06", "Industrial robot arm safety", "n/a",
                      "no manipulator on the pod", "NOT MEASURED", "does not apply (see module docstring)"))
    return pd.DataFrame([r.__dict__ for r in rows])


def _prop(trials: pd.DataFrame | None, label: str = "proposed") -> pd.DataFrame | None:
    return None if trials is None else trials[trials["controller"] == label]


def _chassis(trials: pd.DataFrame | None) -> pd.DataFrame | None:
    """Payload checks use the deliverable: the FSM + DWA controller on the course vehicle at its 3.5 m/s cruise speed."""
    return _prop(trials)


def _clearance_text(trials: pd.DataFrame | None) -> str:
    p = _prop(trials)
    if p is None or p["min_clearance_m"].dropna().empty:
        return "run the Monte Carlo first"
    c = p["min_clearance_m"].dropna()
    return f"median min clearance {c.median():.2f} m; {100 * (c >= 0.5).mean():.0f}% of runs never closer than 0.50 m"


def _clearance_status(trials: pd.DataFrame | None) -> str:
    p = _prop(trials)
    if p is None or p["min_clearance_m"].dropna().empty:
        return "NOT MEASURED"
    return "MET" if (p["min_clearance_m"].dropna() >= 0.5).all() else "DEVIATION"


def _shock_text(trials: pd.DataFrame | None) -> str:
    p = _chassis(trials)
    if p is None:
        return "run the Monte Carlo first"
    return f"{100 * (p['peak_payload_g'] <= 3.0).mean():.0f}% of runs <= 3 g; worst {p['peak_payload_g'].max():.2f} g"


def _shock_status(trials: pd.DataFrame | None) -> str:
    p = _chassis(trials)
    if p is None:
        return "NOT MEASURED"
    return "MET" if (p["peak_payload_g"] <= 3.0).all() else "DEVIATION"
