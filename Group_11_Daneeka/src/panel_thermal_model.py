"""Per-cell PV temperature model with thermal inertia.

Steady-state temperature (Faiman 2008):
    T_ss = T_amb + G / (U0 + U1 * v)
with G the cell's plane-of-array irradiance [W/m^2], v the wind speed [m/s],
U0 = 25 W/(m^2 K) and U1 = 6.84 W s/(m^3 K) (Faiman's published default
coefficients; they lump absorbed fraction, electrical extraction and
convective/radiative loss).

Dynamics: first-order lag toward the steady state with time constant
    tau = C_th / (U0 + U1 * v)
where C_th is the areal heat capacity of a glass/cell/back-sheet laminate. The
value used (11 kJ/(m^2 K)) is an ASSUMPTION of the right order of magnitude for
a 3 mm glass module (glass alone is ~6 kJ/(m^2 K)); it gives tau of about 5 min
at v = 2 m/s. Each of the N x A x C cells has its own thermal state; lateral
conduction is represented by a small neighbour-averaging weight.

Extra (defect) heating is passed in by the environment as ``excess_ss`` [K]
and is lagged with the same time constant.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ThermalParams:
    u0: float = 25.0              # W/(m^2 K)  Faiman 2008
    u1: float = 6.84              # W s/(m^3 K) Faiman 2008
    c_th: float = 11000.0         # J/(m^2 K)  assumption
    lateral_k: float = 0.25       # neighbour-averaging weight (assumption)
    edge_wind_factor: float = 1.15  # first/last module in a row see more wind (assumption)
    mismatch_std_k: float = 0.4   # fixed per-cell mismatch at 1000 W/m^2 (assumption)
    soiling_max: float = 0.03     # max soiling loss fraction (assumption)


def _blur(field: np.ndarray, k: float) -> np.ndarray:
    """Mix each cell with the mean of its 4 neighbours (edge-replicated), last two axes."""
    p = np.pad(field, ((0, 0), (1, 1), (1, 1)), mode="edge")
    nb = 0.25 * (p[:, :-2, 1:-1] + p[:, 2:, 1:-1] + p[:, 1:-1, :-2] + p[:, 1:-1, 2:])
    return (1.0 - k) * field + k * nb


class PanelThermalModel:
    def __init__(self, registry, rng: np.random.Generator, params: ThermalParams | None = None):
        self.reg = registry
        self.p = params or ThermalParams()
        n = len(registry)
        A, C = registry.cfg.cells_along, registry.cfg.cells_across
        self.shape = (n, A, C)
        self.soiling = rng.uniform(0.0, self.p.soiling_max, size=n)             # per panel
        self.mismatch = rng.normal(0.0, self.p.mismatch_std_k, size=self.shape)  # per cell
        edge = (registry.cols == 1) | (registry.cols == registry.cfg.n_cols)
        self.wind_factor = np.where(edge, self.p.edge_wind_factor, 1.0)          # per panel
        self.T = np.zeros(self.shape)          # cell temperatures [deg C]
        self.excess = np.zeros(self.shape)     # lagged defect excess [K] (already inside T)

    def _u(self, wind: float) -> np.ndarray:
        return self.p.u0 + self.p.u1 * (wind * self.wind_factor)               # (N,)

    def steady_state(self, g_cell: np.ndarray, t_amb: float, wind: float,
                     excess_ss: np.ndarray | None = None) -> np.ndarray:
        u = self._u(wind)[:, None, None]
        g = g_cell * (1.0 - self.soiling[:, None, None])
        base = t_amb + g / u
        base = _blur(base, self.p.lateral_k)
        base = base + self.mismatch * (g_cell / 1000.0)
        if excess_ss is not None:
            base = base + excess_ss
        return base

    def tau(self, wind: float) -> np.ndarray:
        return self.p.c_th / self._u(wind)                                      # (N,) seconds

    def warm_start(self, g_cell, t_amb, wind, excess_ss=None):
        self.T = self.steady_state(g_cell, t_amb, wind, excess_ss)

    def step(self, dt: float, g_cell, t_amb: float, wind: float, excess_ss=None):
        """Advance by ``dt`` seconds of *physical* time (exact exponential integrator)."""
        t_ss = self.steady_state(g_cell, t_amb, wind, excess_ss)
        a = 1.0 - np.exp(-dt / self.tau(wind))                                  # (N,)
        self.T = self.T + (t_ss - self.T) * a[:, None, None]
        return self.T

    def panel_mean(self) -> np.ndarray:
        return self.T.mean(axis=(1, 2))
