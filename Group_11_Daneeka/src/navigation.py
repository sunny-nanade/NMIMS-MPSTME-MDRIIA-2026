"""Localisation and motion planning for the inspection AMR.

PoseEstimator
    Dead reckoning from quantised wheel encoders (with a per-run wheel-radius calibration error)
    and a biased gyro, optionally corrected by
      * panel-plane range pairs  -> lateral position y and heading (absolute w.r.t. the array),
      * surveyed post fiducials  -> along-row position x.
    Each correction can be switched off (used to define the *baseline* controller).

Planner helpers
    PID with anti-windup (conditional integration + clamped output), lane-following law,
    go-to-pose law (rotate-in-place / pure-pursuit style) and the serpentine route.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import robot_params as rp


def wrap(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


class PID:
    def __init__(self, kp, ki=0.0, kd=0.0, out_limit=1e9, i_limit=1e9, d_tau=0.05):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.out_limit, self.i_limit, self.d_tau = out_limit, i_limit, d_tau
        self.i = 0.0
        self._prev = None
        self._d = 0.0

    def reset(self):
        self.i, self._prev, self._d = 0.0, None, 0.0

    def step(self, err: float, dt: float) -> float:
        if self._prev is None:
            self._prev = err
        a = dt / (self.d_tau + dt)
        self._d += a * ((err - self._prev) / dt - self._d)
        self._prev = err
        u_unsat = self.kp * err + self.i + self.kd * self._d
        u = max(-self.out_limit, min(self.out_limit, u_unsat))
        # conditional integration (anti-windup): integrate only if not pushing further into saturation
        if u == u_unsat or (u_unsat - u) * err < 0.0:
            self.i = max(-self.i_limit, min(self.i_limit, self.i + self.ki * err * dt))
        return u


@dataclass
class EstimatorConfig:
    use_gyro: bool = True
    use_range: bool = True
    use_fiducial: bool = True
    gyro_weight: float = 0.98
    range_heading_gain: float = 0.08     # per update (50 Hz)
    range_y_gain: float = 0.10
    fiducial_gain: float = 0.9


class PoseEstimator:
    def __init__(self, x, y, theta, cfg: EstimatorConfig | None = None):
        self.cfg = cfg or EstimatorConfig()
        self.x, self.y, self.theta = float(x), float(y), float(theta)
        self.range_valid = False

    @property
    def pose(self):
        return self.x, self.y, self.theta

    def predict(self, ds: float, dth_enc: float, gyro_z: float, dt: float):
        c = self.cfg
        dth = (c.gyro_weight * gyro_z * dt + (1 - c.gyro_weight) * dth_enc) if c.use_gyro else dth_enc
        th_mid = self.theta + 0.5 * dth
        self.x += ds * math.cos(th_mid)
        self.y += ds * math.sin(th_mid)
        self.theta = wrap(self.theta + dth)

    def update_range(self, pair, side: int, yp: float, theta_ref: float):
        """pair=(d_front, d_rear); side=+1 left sensors, -1 right sensors; yp=panel-plane y at sensor height."""
        self.range_valid = False
        if not self.cfg.use_range or pair is None:
            return None
        df, dr = pair
        a, b = rp.RF_X, rp.RF_Y
        psi = math.atan((dr - df) / (2 * a)) if side > 0 else math.atan((df - dr) / (2 * a))
        if abs(psi) > 0.5:
            return None
        d = 0.5 * (df + dr)
        y_meas = yp - (b + d) * math.cos(psi) if side > 0 else yp - (b + d) * math.cos(psi)
        th_meas = theta_ref + psi
        self.theta = wrap(self.theta + self.cfg.range_heading_gain * wrap(th_meas - self.theta))
        self.y += self.cfg.range_y_gain * (y_meas - self.y)
        self.range_valid = True
        return psi, y_meas

    def update_fiducial(self, x_meas: float | None):
        if self.cfg.use_fiducial and x_meas is not None:
            self.x += self.cfg.fiducial_gain * (x_meas - self.x)
            return True
        return False


class LaneFollower:
    """Cross-track + heading law about a straight lane. direction=+1 east, -1 west."""

    def __init__(self, k_psi=2.2, y_pid: PID | None = None):
        self.k_psi = k_psi
        self.y_pid = y_pid or PID(1.4, 0.15, 0.25, out_limit=1.0, i_limit=0.4)

    def reset(self):
        self.y_pid.reset()

    def command(self, est: PoseEstimator, y_lane: float, direction: int, v_des: float, dt: float):
        th_ref = 0.0 if direction > 0 else math.pi
        e_psi = wrap(est.theta - th_ref)
        e_y = est.y - y_lane
        corr = self.y_pid.step(e_y * direction, dt)           # + => turn right when heading east
        w = -self.k_psi * e_psi - corr
        w = max(-rp.OMEGA_MAX, min(rp.OMEGA_MAX, w))
        v = v_des * max(0.2, 1.0 - 1.5 * abs(e_psi) - 0.6 * abs(e_y))
        return v, w


class GoToPose:
    """Drive to (x,y) then optionally rotate to a final heading."""

    def __init__(self, k_rho=0.9, k_alpha=2.4, pos_tol=0.06, ang_tol=0.04):
        self.k_rho, self.k_alpha, self.pos_tol, self.ang_tol = k_rho, k_alpha, pos_tol, ang_tol

    def command(self, est: PoseEstimator, tx: float, ty: float, final_heading: float | None,
                v_max: float = rp.V_CRUISE):
        dx, dy = tx - est.x, ty - est.y
        rho = math.hypot(dx, dy)
        if rho > self.pos_tol:
            alpha = wrap(math.atan2(dy, dx) - est.theta)
            if abs(alpha) > 0.6:
                return 0.0, max(-rp.OMEGA_MAX, min(rp.OMEGA_MAX, 2.0 * alpha)), False
            v = min(v_max, self.k_rho * rho) * math.cos(alpha)
            w = max(-rp.OMEGA_MAX, min(rp.OMEGA_MAX, self.k_alpha * alpha))
            return max(v, 0.08), w, False
        if final_heading is None:
            return 0.0, 0.0, True
        e = wrap(final_heading - est.theta)
        if abs(e) < self.ang_tol:
            return 0.0, 0.0, True
        return 0.0, max(-0.8, min(0.8, 2.0 * e)), False


def serpentine_plan(registry, rows=None):
    """Inspection legs: list of dicts {row, direction, x_start, x_end, lane_y, head_side}.

    Row 1 is inspected heading east (rows on the robot's LEFT); the next row west (rows on the RIGHT), ...
    """
    c = registry.cfg
    rows = rows or list(range(1, c.n_rows + 1))
    legs = []
    for k, r in enumerate(rows):
        east = (k % 2 == 0)
        x0, x1 = registry.x_west - 0.4, registry.x_east + 0.4
        legs.append(dict(row=r, direction=+1 if east else -1,
                         x_start=x0 if east else x1, x_end=x1 if east else x0,
                         lane_y=registry.lane_y(r), side=+1 if east else -1))
    return legs
