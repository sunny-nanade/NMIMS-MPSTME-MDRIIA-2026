"""Low-level control: differential-drive kinematics and wheel-velocity PI (500 Hz).

  omega_R = (v + w*b/2)/r ,  omega_L = (v - w*b/2)/r        (b = track width, r = wheel radius)
"""
from __future__ import annotations

import numpy as np

import robot_params as rp


def wheel_speeds(v: float, w: float):
    r, b = rp.WHEEL_RADIUS, rp.TRACK_WIDTH
    return (v - w * b / 2.0) / r, (v + w * b / 2.0) / r


class WheelController:
    """PI on wheel speed with viscous feed-forward and conditional-integration anti-windup."""

    def __init__(self, kp=2.5, ki=12.0, kff=0.05, limit=rp.WHEEL_TORQUE_LIMIT, slew=60.0):
        self.kp, self.ki, self.kff, self.limit, self.slew = kp, ki, kff, limit, slew
        self.i = np.zeros(2)
        self.u_prev = np.zeros(2)

    def reset(self):
        self.i[:] = 0.0
        self.u_prev[:] = 0.0

    def step(self, w_ref: np.ndarray, w_meas: np.ndarray, dt: float) -> np.ndarray:
        e = w_ref - w_meas
        u_raw = self.kp * e + self.i + self.kff * w_ref
        u = np.clip(u_raw, -self.limit, self.limit)
        # slew-rate limit (protects drivetrain, reduces jerk)
        du = np.clip(u - self.u_prev, -self.slew * dt, self.slew * dt)
        u = self.u_prev + du
        self.u_prev = u.copy()
        windup = (u_raw != np.clip(u_raw, -self.limit, self.limit)) & (e * u_raw > 0)
        self.i = np.where(windup, self.i, np.clip(self.i + self.ki * e * dt, -self.limit, self.limit))
        return u
