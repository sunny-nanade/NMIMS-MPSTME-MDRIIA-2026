"""Fault models and the hidden ground truth.

IMPORTANT (separation of truth and observation): this module defines what is
*really* wrong with each module. Only the environment (physics), the sensor
simulation (which turns truth into noisy measurements) and the evaluator are
allowed to import it. ``defect_detection.py`` must never import it; a unit test
(tests/test_fault_detection.py) enforces this.

Defect kinds (all documented, parameterised models, none is a fixed temperature):

HOTSPOT      Cell-level overheating (e.g. cell mismatch / cracked-cell shunt).
             Steady excess = dT_ref * G_cell/1000 [K] on one cell
             (dT_ref = excess at 1000 W/m^2, drawn from U(16,40) K).
HOT_MODULE   Abnormal thermal response of the whole module (e.g. open string /
             failed bypass diode). Excess = dT_mod * G_mean/1000 on every cell,
             dT_mod ~ U(9,18) K.
CRACK        Visible cell crack: visible to the optical camera with severity
             s ~ U(0.4,1.0); small thermal side-effect of 3*s K * G/1000.
OBSTRUCTION  Opaque foreign object lying on 1-4 neighbouring cells (leaf, bird
             fouling). Visible to the optical camera; blocks direct beam on the
             covered cells (so it also creates a partial-shading thermal pattern).
EXT_SHADOW   NOT a module defect: an external object (cable tray, perch) floating
             above a module that casts a moving shadow. It is a *confounder*:
             partially shaded cells can run hot through reverse-bias heating,
             so a naive detector flags a healthy module.

Reverse-bias heating of partially shaded modules (any cause) is an engineering
assumption of this project: cells whose direct-beam shading exceeds 0.5 while
fewer than half of the module's cells are shaded get an excess of
KAPPA_RB * (G_beam_unshaded/1000) K. KAPPA_RB = 55 K is a labelled, uncalibrated assumption
(see documentation/model_assumptions.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

KAPPA_RB = 55.0          # K at 1000 W/m^2 beam, ASSUMPTION: chosen so a partly shaded cell runs ~+15-25 K above its unshaded neighbours at midday (net of the cooling from lost irradiance); not calibrated to measurements


class DefectKind(str, Enum):
    HOTSPOT = "HOTSPOT"
    HOT_MODULE = "HOT_MODULE"
    CRACK = "CRACK"
    OBSTRUCTION = "OBSTRUCTION"
    EXT_SHADOW = "EXT_SHADOW"      # confounder, not a defect

    @property
    def is_defect(self) -> bool:
        return self is not DefectKind.EXT_SHADOW


@dataclass
class DefectSpec:
    kind: DefectKind
    panel_id: str
    cells: list = field(default_factory=list)     # list[(i, j)] cell indices
    severity: float = 1.0                         # kind-specific (see module docstring)
    box_min: np.ndarray | None = None             # EXT_SHADOW only (world frame)
    box_max: np.ndarray | None = None

    def describe(self) -> dict:
        return {"kind": self.kind.value, "panel_id": self.panel_id,
                "cells": [list(map(int, c)) for c in self.cells],
                "severity": round(float(self.severity), 3)}


@dataclass
class NavFaults:
    enc_cal_err_left: float = 0.0     # fractional error of the left wheel radius used by odometry
    enc_cal_err_right: float = 0.0
    gyro_bias: float = 0.0            # rad/s added to the gyro
    init_x_error: float = 0.0         # initial odometry x offset [m] (mis-association scenario)
    nominal_gyro_bias_std: float = 5e-5     # ~10 deg/h class MEMS gyro
    nominal_cal_std: float = 0.003          # 0.3 % wheel-calibration spread


@dataclass
class SensorFaults:
    spike_prob: float = 0.0015        # per thermal pixel per frame (nominal sensor artefacts)
    spike_mag: tuple = (12.0, 35.0)   # K
    noise_scale: float = 1.0          # multiplies thermal pixel noise
    dropout_prob: float = 0.01        # whole-frame failure probability
    glare_enabled: bool = True        # physical sun glint is always computed; this just allows disabling


@dataclass
class FaultConfig:
    nav: NavFaults = field(default_factory=NavFaults)
    sensor: SensorFaults = field(default_factory=SensorFaults)
    label: str = "nominal"


class GroundTruth:
    """Hidden state of the farm: every defect and confounder."""

    def __init__(self, registry, defects: list[DefectSpec]):
        self.reg = registry
        self.defects = list(defects)
        self.shape = (len(registry), registry.cfg.cells_along, registry.cfg.cells_across)

    # ------------------------------------------------------------- queries
    def real_defects(self):
        return [d for d in self.defects if d.kind.is_defect]

    def defect_panel_ids(self) -> set:
        return {d.panel_id for d in self.real_defects()}

    def by_panel(self, pid: str):
        return [d for d in self.defects if d.panel_id == pid]

    def kinds_at(self, pid: str) -> set:
        return {d.kind.value for d in self.by_panel(pid) if d.kind.is_defect}

    def hotspot_cell_position(self, pid: str):
        """True 3-D position of the hottest-defect cell (for localisation-error evaluation)."""
        idx = self.reg.index(pid)
        for d in self.by_panel(pid):
            if d.kind in (DefectKind.HOTSPOT, DefectKind.CRACK, DefectKind.OBSTRUCTION) and d.cells:
                i, j = d.cells[0]
                return self.reg.cell_position(idx, i, j)
        return None

    def obstruction_mask(self) -> np.ndarray:
        m = np.zeros(self.shape, bool)
        for d in self.defects:
            if d.kind is DefectKind.OBSTRUCTION:
                p = self.reg.index(d.panel_id)
                for i, j in d.cells:
                    m[p, i, j] = True
        return m

    def ext_boxes(self):
        boxes = [d for d in self.defects if d.kind is DefectKind.EXT_SHADOW]
        if not boxes:
            return None
        return (np.array([b.box_min for b in boxes]), np.array([b.box_max for b in boxes]))

    # -------------------------------------------------------- thermal effect
    def excess_ss(self, g_cell: np.ndarray, shade: np.ndarray, g_beam_unshaded: float) -> np.ndarray:
        """Steady-state excess temperature [K] for every cell given current conditions."""
        ex = np.zeros(self.shape)
        for d in self.defects:
            p = self.reg.index(d.panel_id)
            if d.kind is DefectKind.HOTSPOT:
                for i, j in d.cells:
                    ex[p, i, j] += d.severity * g_cell[p, i, j] / 1000.0
            elif d.kind is DefectKind.HOT_MODULE:
                ex[p] += d.severity * float(g_cell[p].mean()) / 1000.0
            elif d.kind is DefectKind.CRACK:
                for i, j in d.cells:
                    ex[p, i, j] += 3.0 * d.severity * g_cell[p, i, j] / 1000.0
        # reverse-bias heating of partially shaded modules (any shading source)
        shaded = shade > 0.5
        frac = shaded.mean(axis=(1, 2))
        partial = (frac > 0.0) & (frac < 0.5)
        if partial.any():
            rb = KAPPA_RB * (g_beam_unshaded / 1000.0) * shade
            ex += np.where(partial[:, None, None] & shaded, rb, 0.0)
        return ex


# ---------------------------------------------------------------------- seeding
def seed_random_defects(registry, rng: np.random.Generator, n_defects: int | None = None,
                        n_confounders: int | None = None,
                        weights: dict | None = None) -> list[DefectSpec]:
    """Randomly seed defects and confounders on distinct modules (all drawn from ``rng``).

    Defaults: 4-7 defective modules out of N, 0-2 external-shadow confounders on
    different (healthy) modules. Kind probabilities: HOTSPOT 0.45, HOT_MODULE 0.15,
    CRACK 0.2, OBSTRUCTION 0.2.
    """
    n = len(registry)
    A, C = registry.cfg.cells_along, registry.cfg.cells_across
    if n_defects is None:
        n_defects = int(rng.integers(4, 8))
    if n_confounders is None:
        n_confounders = int(rng.integers(0, 3))
    w = weights or {DefectKind.HOTSPOT: 0.45, DefectKind.HOT_MODULE: 0.15,
                    DefectKind.CRACK: 0.20, DefectKind.OBSTRUCTION: 0.20}
    kinds = list(w.keys())
    probs = np.array([w[k] for k in kinds], float)
    probs /= probs.sum()
    chosen = rng.choice(n, size=n_defects + n_confounders, replace=False)
    out: list[DefectSpec] = []
    for t, p_idx in enumerate(chosen):
        pid = registry.ids[int(p_idx)]
        if t < n_defects:
            kind = kinds[int(rng.choice(len(kinds), p=probs))]
            out.append(make_defect(registry, kind, pid, rng))
        else:
            out.append(make_ext_shadow(registry, pid, rng))
    return out


def make_defect(registry, kind: DefectKind, pid: str, rng: np.random.Generator,
                cell: tuple | None = None, severity: float | None = None) -> DefectSpec:
    A, C = registry.cfg.cells_along, registry.cfg.cells_across
    if cell is None:
        cell = (int(rng.integers(1, A - 1)), int(rng.integers(1, C - 1)))   # not on the very edge
    if kind is DefectKind.HOTSPOT:
        sev = float(rng.uniform(16.0, 40.0)) if severity is None else severity
        return DefectSpec(kind, pid, [cell], sev)
    if kind is DefectKind.HOT_MODULE:
        sev = float(rng.uniform(9.0, 18.0)) if severity is None else severity
        return DefectSpec(kind, pid, [], sev)
    if kind is DefectKind.CRACK:
        sev = float(rng.uniform(0.4, 1.0)) if severity is None else severity
        return DefectSpec(kind, pid, [cell], sev)
    if kind is DefectKind.OBSTRUCTION:
        sev = 1.0 if severity is None else severity
        n_cells = int(rng.integers(1, 5))
        cells = [cell]
        i, j = cell
        for _ in range(n_cells - 1):
            di, dj = [(0, 1), (1, 0), (0, -1), (-1, 0)][int(rng.integers(0, 4))]
            i2, j2 = min(max(i + di, 0), A - 1), min(max(j + dj, 0), C - 1)
            if (i2, j2) not in cells:
                cells.append((i2, j2))
            i, j = i2, j2
        return DefectSpec(kind, pid, cells, sev)
    raise ValueError(kind)


def make_ext_shadow(registry, pid: str, rng: np.random.Generator,
                    offset_along: float | None = None, height: float = 0.40) -> DefectSpec:
    """External object (e.g. cable tray / perch) hovering ``height`` m above the module."""
    spec = registry.get(pid)
    if offset_along is None:
        offset_along = float(rng.uniform(-0.3, 0.3))
    centre = spec.center + spec.normal * height + spec.up_slope * offset_along
    half = np.array([0.30, 0.12, 0.06])           # AABB half-size (x, y, z) [m]
    return DefectSpec(DefectKind.EXT_SHADOW, pid, [], 1.0, centre - half, centre + half)
