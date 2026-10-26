"""500 Hz closed-loop telemetry for the capstone Monte Carlo (course dossier, Section 4).

``TelemetryRecorder`` hooks the rover's per-physics-step callback, so one row is written for every
MuJoCo step (timestep 0.002 s = 500 Hz) rather than once per control cycle. Columns are in SI
units; REP-103 frame (x forward, y left, z up).

======================= ===========================================================================
column                  meaning
======================= ===========================================================================
t_s                     simulation time [s]
fsm_state               mission FSM state (empty for planners without an FSM)
x_m, y_m, yaw_rad       chassis pose; ``roll_rad``, ``pitch_rad`` attitude
v_mps, wz_radps         forward speed (chassis frame) and yaw rate
v_cmd_mps, delta_cmd    command held during the control cycle (after FSM cap and safety filter)
y_ref_m, e_y_m          planned route centreline (y = 0) and cross-track error ``y - y_ref``
tau_fl..tau_rr_Nm       drive-motor torques; ``tau_steer_fl/fr_Nm`` steering torques
slip_fl..slip_rr        longitudinal slip ratio ``(w r - v_w) / max(|w r|, |v_w|)``
payload_g               payload dynamic acceleration magnitude (gravity removed) [g]
stability_index         ``1 - |roll| / 18 deg`` (18 deg: course roll limit), clipped to [0, 1]
======================= ===========================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..sim.metrics import G

ROLL_LIMIT_RAD = math.radians(18.0)   # course controller guide: |phi| <= 18 deg
MIN_SLIP_SPEED = 0.3                  # m/s, below this the slip ratio is undefined and reported as 0
WHEELS = ("fl", "fr", "rl", "rr")

COLUMNS = (
    ["t_s", "fsm_state", "x_m", "y_m", "yaw_rad", "roll_rad", "pitch_rad", "v_mps", "wz_radps",
     "v_cmd_mps", "delta_cmd_rad", "y_ref_m", "e_y_m"]
    + [f"tau_{w}_Nm" for w in WHEELS] + ["tau_steer_fl_Nm", "tau_steer_fr_Nm"]
    + [f"slip_{w}" for w in WHEELS] + ["payload_g", "stability_index"]
)


@dataclass
class RunSummary:
    rows: int
    log_rate_hz: float
    rmse_m: float
    effort_Nm2s: float
    peak_abs_slip: float
    min_stability_index: float


class TelemetryRecorder:
    def __init__(self, rover, y_ref: float = 0.0):
        self.rover, self.y_ref = rover, y_ref
        self._rows: list[tuple] = []
        self.state = ""
        self.v_cmd = 0.0
        self.delta_cmd = 0.0

    # ----------------------------------------------------------- life cycle
    def attach(self) -> None:
        self.rover.on_substep = self._sample

    def detach(self) -> None:
        self.rover.on_substep = None

    def clear(self) -> None:
        self._rows.clear()

    def command(self, state: str, v_cmd: float, delta_cmd: float) -> None:
        """Declare the command and FSM state held for the physics steps that follow."""
        self.state, self.v_cmd, self.delta_cmd = state, float(v_cmd), float(delta_cmd)

    # --------------------------------------------------------------- sample
    def _sample(self, rv) -> None:
        d = rv.d
        yaw, pitch, roll = rv.yaw_pitch_roll()
        vb = rv.body_velocity()
        wz = rv.yaw_rate()
        x, y = rv.pos[0], rv.pos[1]
        up = d.xmat[rv.w.b_chassis, 6:9]
        dyn = (rv.payload_acc() - G * up) / G
        # hub speed of each wheel from rigid-body kinematics: v_w = vx - wz * y_wheel
        v_hub = vb[0] - wz * (rv._wy - 0.0)
        w_r = rv.wheel_speeds() * rv.p.wheel_radius
        denom = np.maximum(np.maximum(np.abs(w_r), np.abs(v_hub)), MIN_SLIP_SPEED)
        slip = np.where(np.maximum(np.abs(w_r), np.abs(v_hub)) < MIN_SLIP_SPEED, 0.0,
                        (w_r - v_hub) / denom)
        tau_drive = d.actuator_force[rv.a_drive]
        tau_steer = d.actuator_force[rv.a_steer]
        stab = float(np.clip(1.0 - abs(roll) / ROLL_LIMIT_RAD, 0.0, 1.0))
        self._rows.append((
            d.time, self.state, x, y, yaw, roll, pitch, float(vb[0]), wz, self.v_cmd, self.delta_cmd,
            self.y_ref, y - self.y_ref, *tau_drive, *tau_steer, *slip, float(np.linalg.norm(dyn)),
            stab))

    # -------------------------------------------------------------- outputs
    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self._rows, columns=list(COLUMNS))

    def summarise(self, df: pd.DataFrame | None = None, dt_phys: float = 0.002,
                  transit_only: bool = True) -> RunSummary:
        df = self.frame() if df is None else df
        return summarise_frame(df, dt_phys, transit_only)


def summarise_frame(df: pd.DataFrame, dt_phys: float = 0.002, transit_only: bool = True) -> RunSummary:
    """Tracking RMSE, control effort and log rate from a 500 Hz frame.

    RMSE = sqrt(mean(e_y^2)); ``peak_abs_slip`` is the 99th percentile of |slip| over the four wheels
    (the absolute maximum is dominated by the launch from rest); effort E = sum_over_actuators(tau^2) * dt (N^2 m^2 s), the discrete
    form of the integral of tau^2 dt required by the course. ``transit_only`` drops the stationary
    AED_HANDOVER rows so they neither dilute the RMSE nor add zero-torque time.
    """
    if len(df) < 2:
        return RunSummary(len(df), float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))
    t = df["t_s"].to_numpy()
    rate = (len(df) - 1) / (t[-1] - t[0])
    tr = df[df["fsm_state"] != "AED_HANDOVER"] if transit_only else df
    e = tr["e_y_m"].to_numpy()
    tau_cols = [c for c in df.columns if c.startswith("tau_")]
    effort = float(np.sum(tr[tau_cols].to_numpy() ** 2) * dt_phys)
    slip_cols = [f"slip_{w}" for w in WHEELS]
    return RunSummary(
        rows=len(df),
        log_rate_hz=float(rate),
        rmse_m=float(np.sqrt(np.mean(e**2))) if len(e) else float("nan"),
        effort_Nm2s=effort,
        peak_abs_slip=float(np.percentile(np.abs(tr[slip_cols].to_numpy()), 99)) if len(tr) else float("nan"),
        min_stability_index=float(tr["stability_index"].min()) if len(tr) else float("nan"),
    )
