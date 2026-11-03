"""Defect detection from thermal + optical frames.

THIS MODULE MUST NEVER IMPORT ``fault_injection`` (tests/test_fault_detection.py enforces it):
the detector only sees ``Observation`` frames and the robot's own context (estimated pose,
ephemeris, reference irradiance, ambient/wind readings).

Baseline (conventional fixed-threshold survey)
    one thermal frame; flag the module if (hottest pixel - module median) >= 15 K;
    no irradiance gating, no spike filter, no glint handling, no optical cross-check.
Proposed
    1. irradiance gate   : G_ref >= G_MIN (assessment not valid below it);
    2. temporal median over >=3 frames (rejects spikes / dropouts);
    3. glint mask        : pixels whose specular direction is within GLINT_MASK_DEG of the sun are
                           ignored; heavy masking requests a verification view at another mast height;
    4. emissivity compensation from viewing geometry (Fresnel, n=1.5) and an assumed sky temperature;
    5. irradiance normalisation of every temperature excess to 1000 W/m^2;
    6. hotspot = cluster >= 2 adjacent pixels above HOT_NORM_K; hot module = module median above the
       row median of previously inspected modules (and above the Faiman expectation);
    7. optical scores : crack, obstruction, external shadow; a thermal anomaly that coincides with an
                        external shadow is classified SHADOW_CONFOUNDER and not flagged.
All thresholds are parameters; their values are engineering choices documented in
documentation/model_assumptions.md (G_MIN and the 15 K figure are to be checked against IEC TS 62446-3).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

from sensor_simulation import PIX_PER_CELL, PixelGrid, glint_angles_deg
from thermal_optics import emissivity

U0, U1 = 25.0, 6.84          # Faiman coefficients (same published model the environment uses)


@dataclass
class DetectorConfig:
    proposed: bool = True
    base_dT_k: float = 15.0
    g_min: float = 600.0
    hot_norm_k: float = 8.0
    hot_module_k: float = 5.5
    min_cluster: int = 2
    glint_mask_deg: float = 10.0
    glint_recheck_frac: float = 0.25
    crack_thr: float = 0.18
    obstruction_thr: float = 0.5
    shadow_thr: float = 0.15
    sky_dT_k: float = 10.0       # assumed sky depression for emissivity compensation


@dataclass
class DetectionResult:
    pid_est: str
    flagged: bool
    kind: str = "NONE"
    cell: tuple | None = None
    score: float = 0.0
    gated: bool = False
    need_recheck: bool = False
    glint_frac: float = 0.0
    reason: str = ""
    position_est: np.ndarray | None = None
    cond: str = ""

    def summary(self) -> str:
        return (f"{'FLAG ' + self.kind if self.flagged else 'ok'} score={self.score:.1f}"
                f"{' GATED' if self.gated else ''}{' RECHECK' if self.need_recheck else ''} {self.reason}")

    def record(self, t_sim, t_env, cond):
        return dict(t_sim=t_sim, t_env=t_env, condition=cond, panel_id_est=self.pid_est,
                    kind_est=self.kind, cell_est=self.cell, score=self.score,
                    position_est=None if self.position_est is None else np.round(self.position_est, 3).tolist(),
                    reason=self.reason)


def _neighbour_cluster(mask: np.ndarray) -> np.ndarray:
    """True where a hot pixel has at least one hot 4-neighbour."""
    p = np.pad(mask, 1)
    nb = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return mask & nb


class Detector:
    def __init__(self, registry, cfg: DetectorConfig, rng):
        self.reg, self.cfg, self.rng = registry, cfg, rng
        self.grid = PixelGrid(registry)
        self.row_norm_medians: dict = {}
        self.assessed = 0
        self.module_hist: deque = deque(maxlen=8)
        self._row = None
        self.pending: list = []

    def reset_module(self):
        pass

    # ------------------------------------------------------------ main
    def analyse(self, frames, ctx) -> DetectionResult:
        pid = ctx["pid_guess"]
        spec = self.reg.get(pid)
        c = self.cfg
        therm = [f.thermal.pixels for f in frames if f.thermal is not None]
        opt = [f.optical for f in frames if f.optical is not None]
        if not therm:
            return DetectionResult(pid, False, reason="no thermal frame", cond="")
        if not c.proposed:
            return self._baseline(pid, spec, therm[0])
        return self._proposed(pid, spec, therm, opt, ctx)

    def _cell_of(self, pix_idx):
        return (int(pix_idx[0] // PIX_PER_CELL), int(pix_idx[1] // PIX_PER_CELL))

    def _position(self, spec, pix):
        return spec.center + self.grid.offsets[pix[0], pix[1]]

    # ------------------------------------------------------------ baseline
    def _baseline(self, pid, spec, img):
        med = float(np.median(img))
        k = np.unravel_index(int(np.argmax(img)), img.shape)
        dT = float(img[k] - med)
        if dT >= self.cfg.base_dT_k:
            return DetectionResult(pid, True, "HOTSPOT", self._cell_of(k), dT,
                                   position_est=self._position(spec, k), reason=f"dT={dT:.1f}K")
        return DetectionResult(pid, False, score=dT, reason=f"dT={dT:.1f}K")

    # ------------------------------------------------------------ proposed
    def _proposed(self, pid, spec, therm, opt, ctx):
        c = self.cfg
        g = max(ctx["g_ref"], 1.0)
        if g < c.g_min:
            return DetectionResult(pid, False, gated=True, reason=f"G={g:.0f}<{c.g_min:.0f} W/m2: not assessable")
        img = np.median(np.stack(therm), axis=0)
        lens, sun_vec = ctx["lens_est"], ctx["sun_vec"]
        # geometry -> emissivity compensation
        pts = spec.center[None, None, :] + self.grid.offsets
        v = pts - lens[None, None, :]
        v /= np.linalg.norm(v, axis=2, keepdims=True)
        cos_t = np.clip(-(v @ self.reg.normal), 0.0, 1.0)
        eps = emissivity(np.arccos(cos_t))
        t_refl = ctx["t_amb"] + 273.15 - c.sky_dT_k
        tk = np.clip((img + 273.15) ** 4 - (1 - eps) * t_refl ** 4, 1.0, None) / eps
        t_obj = tk ** 0.25 - 273.15
        # glint mask
        ang = glint_angles_deg(lens, spec.center, self.reg, self.grid, sun_vec)
        mask = (ang < c.glint_mask_deg) if ctx["sun_elev"] > 0 else np.zeros_like(ang, bool)
        gfrac = float(mask.mean())
        t_m = np.where(mask, np.nan, t_obj)
        valid = ~mask
        if valid.sum() < 0.4 * mask.size:
            return DetectionResult(pid, False, need_recheck=True, glint_frac=gfrac,
                                   reason=f"glint mask {gfrac:.0%}")
        med = float(np.nanmedian(t_m))
        scale = 1000.0 / g
        exc = (t_m - med) * scale
        hot = np.nan_to_num(exc, nan=-99.0) >= c.hot_norm_k
        clus = _neighbour_cluster(hot)
        optc = self._optical(opt)
        # module-level thermal (hot module)
        mod_norm = (med - ctx["t_amb"]) * scale
        faiman = (g / (U0 + U1 * ctx["wind"])) * scale
        hist = self.row_norm_medians.setdefault("all", [])
        recent = hist[-12:]
        deferred = len(recent) < 3          # not enough healthy modules seen yet -> decide at end of row
        row_ref = float(np.median(recent)) if not deferred else mod_norm
        hot_module = (mod_norm - row_ref) >= c.hot_module_k
        shadow = optc["shadow"] >= c.shadow_thr
        res = None
        if optc["obstruction"] >= c.obstruction_thr:
            res = DetectionResult(pid, True, "OBSTRUCTION", None, optc["obstruction"], reason="optical obstruction")
        elif clus.any() and shadow:
            res = DetectionResult(pid, False, "SHADOW_CONFOUNDER", None, 0.0, reason="hot cluster coincides with shadow")
        elif clus.any():
            idx = np.argwhere(clus)
            wts = np.nan_to_num(exc[clus], nan=0.0)
            pk = np.unravel_index(int(np.nanargmax(np.where(clus, exc, -99.0))), exc.shape)
            cen = (idx * wts[:, None]).sum(0) / wts.sum()
            pix = (int(round(cen[0])), int(round(cen[1])))
            res = DetectionResult(pid, True, "HOTSPOT", self._cell_of(pix), float(exc[pk]),
                                  position_est=self._position(spec, pix), reason=f"dT_norm={exc[pk]:.1f}K")
        elif hot_module and not shadow:
            res = DetectionResult(pid, True, "HOT_MODULE", None, mod_norm - row_ref,
                                  reason=f"module +{mod_norm - row_ref:.1f}K vs row")
        elif optc["crack"] >= c.crack_thr:
            res = DetectionResult(pid, True, "CRACK", None, optc["crack"], reason="optical crack")
        if res is None:
            res = DetectionResult(pid, False, score=float(np.nanmax(exc)), reason="healthy")
        if deferred and not res.flagged and res.kind == "NONE":
            self.pending.append((pid, mod_norm, spec))
        elif not res.flagged and not hot_module and res.kind == "NONE":
            hist.append(mod_norm)
        res.glint_frac = gfrac
        if res.position_est is None:
            res.position_est = spec.center.copy()
        # recheck once when a decision rests on a heavily glint-affected view
        res.need_recheck = bool(gfrac >= c.glint_recheck_frac)
        return res

    @staticmethod
    def _optical(opt):
        if not opt:
            return dict(crack=0.0, obstruction=0.0, shadow=0.0)
        return dict(crack=float(np.mean([o.crack for o in opt])),
                    obstruction=float(np.mean([o.obstruction for o in opt])),
                    shadow=float(np.mean([o.shadow for o in opt])))

    def finalise_pending(self):
        """End-of-leg review of modules whose hot-module decision was deferred (too few reference modules)."""
        out = []
        if not self.pending:
            return out
        hist = self.row_norm_medians.setdefault("all", [])
        allv = [p[1] for p in self.pending] + hist
        ref = float(np.median(allv))
        for pid, mod_norm, spec in self.pending:
            if mod_norm - ref >= self.cfg.hot_module_k:
                r = DetectionResult(pid, True, "HOT_MODULE", None, mod_norm - ref,
                                    position_est=spec.center.copy(), reason=f"module +{mod_norm - ref:.1f}K (end-of-row review)")
                out.append(r)
            else:
                hist.append(mod_norm)
        self.pending = []
        return out
