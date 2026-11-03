"""Simulated sensors: they convert hidden truth (MuJoCo state + environment + defects)
into noisy, imperfect measurements. The detector and the navigation estimator see
only what is returned here.

Proprioceptive : wheel encoders (4096 counts/rev, calibration error), gyro (bias + noise)
Exteroceptive  : side/front range finders (real MuJoCo ray casts against the module slabs),
                 fiducial reader (post markers), co-planar reference irradiance cell,
                 thermal camera (20 x 12 pixel panel image), optical camera (rule-based
                 feature scores -- a *simulated* optical detector, not a trained vision model)

Thermal camera model (per pixel)
--------------------------------
  T_app^4 = eps(theta) * T_obj^4 + (1 - eps(theta)) * T_refl^4   (Kelvin, broadband approximation)
  eps(theta) = 1 - R_fresnel(theta; n = 1.5)   -> falls at oblique viewing angles
  T_refl     = sky apparent temperature  (T_amb - 20 K * (1 - cloud))
  + sun glint: where the mirror direction of the line of sight lies near the sun,
    dT = 60 K * exp(-(angle/5 deg)^2) * DNI/800
  + Gaussian pixel noise, common-mode offset, random single-pixel spikes, frame drop-outs.
The values 0.4 K noise, 0.7 K common-mode, n = 1.5 and the glint amplitude are labelled
assumptions (documentation/model_assumptions.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import mujoco
import numpy as np

import robot_params as rp
from fault_injection import DefectKind, FaultConfig

SIGMA_SKY_K = 20.0
GLINT_AMP_K = 60.0
GLINT_WIDTH_DEG = 5.0
PIX_PER_CELL = 2


from thermal_optics import emissivity, fresnel_reflectance  # noqa: E402,F401


def wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


class PixelGrid:
    """Pixel centre offsets on a module (world frame, relative to the module centre)."""

    def __init__(self, registry):
        c = registry.cfg
        self.pa = c.cells_along * PIX_PER_CELL
        self.pc = c.cells_across * PIX_PER_CELL
        L_act = c.panel_l - 2 * c.frame_w
        W_act = c.panel_w - 2 * c.frame_w
        s = ((np.arange(self.pa) + 0.5) / self.pa - 0.5) * L_act
        t = ((np.arange(self.pc) + 0.5) / self.pc - 0.5) * W_act
        self.offsets = (s[:, None, None] * registry.up_slope[None, None, :]
                        + t[None, :, None] * registry.along_row[None, None, :])  # (pa,pc,3)


def glint_angles_deg(lens_pos: np.ndarray, panel_center: np.ndarray, reg, grid: PixelGrid,
                     sun_vec: np.ndarray) -> np.ndarray:
    """Angle [deg] between the specular reflection of each pixel's line of sight and the sun."""
    pts = panel_center[None, None, :] + grid.offsets
    v = pts - lens_pos[None, None, :]
    v = v / np.linalg.norm(v, axis=2, keepdims=True)
    n = reg.normal
    vn = v @ n
    r = v - 2.0 * vn[..., None] * n[None, None, :]
    cosang = np.clip(r @ sun_vec, -1.0, 1.0)
    return np.degrees(np.arccos(cosang))


def estimate_glint_risk(lens_pos, panel_center, reg, grid, sun_vec, dni_est: float) -> float:
    """Robot-side glint risk in [0,1] from geometry + ephemeris only (no ground truth)."""
    if sun_vec[2] <= 0.0 or dni_est < 100.0:
        return 0.0
    ang = glint_angles_deg(lens_pos, panel_center, reg, grid, sun_vec)
    risk = np.exp(-(ang.min() / (1.6 * GLINT_WIDTH_DEG)) ** 2) * min(1.0, dni_est / 500.0)
    return float(risk)


def view_angle_deg(lens_pos: np.ndarray, panel_center: np.ndarray, normal: np.ndarray) -> float:
    v = lens_pos - panel_center
    v = v / np.linalg.norm(v)
    return math.degrees(math.acos(float(np.clip(v @ normal, -1.0, 1.0))))


# --------------------------------------------------------------------------- frames
@dataclass
class ThermalFrame:
    pixels: np.ndarray          # (pa, pc) apparent temperature [deg C]
    t_sim: float


@dataclass
class OpticalFrame:
    crack: float
    obstruction: float
    shadow: float
    frame_offset_m: float       # measured along-row offset of the aim point from the nearest module centre
    t_sim: float


@dataclass
class Observation:
    thermal: ThermalFrame | None
    optical: OpticalFrame | None
    truth: dict = field(default_factory=dict)    # evaluation only -- never given to the detector


# --------------------------------------------------------------------------- suite
class SensorSuite:
    def __init__(self, model, data, registry, env, faults: FaultConfig, rng: np.random.Generator):
        self.m, self.d, self.reg, self.env, self.faults, self.rng = model, data, registry, env, faults, rng
        nm = lambda t, n: mujoco.mj_name2id(model, t, n)       # noqa: E731
        J, S = mujoco.mjtObj.mjOBJ_JOINT, mujoco.mjtObj.mjOBJ_SITE
        self.qadr_l = model.jnt_qposadr[nm(J, "wheel_left_joint")]
        self.qadr_r = model.jnt_qposadr[nm(J, "wheel_right_joint")]
        self.vadr_l = model.jnt_dofadr[nm(J, "wheel_left_joint")]
        self.vadr_r = model.jnt_dofadr[nm(J, "wheel_right_joint")]
        self.pan_q = model.jnt_qposadr[nm(J, "pan_joint")]
        self.tilt_q = model.jnt_qposadr[nm(J, "tilt_joint")]
        self.lift_q = model.jnt_qposadr[nm(J, "mast_lift_joint")]
        self.site = {n: nm(S, n) for n in ("imu", "rf_lf", "rf_lr", "rf_rf", "rf_rr", "rf_front",
                                           "thermal_lens", "optical_lens", "ref_pyranometer",
                                           "body_origin")}
        self.chassis = nm(mujoco.mjtObj.mjOBJ_BODY, "amr_chassis")
        self.gyro_adr = model.sensor_adr[nm(mujoco.mjtObj.mjOBJ_SENSOR, "imu_gyro")]
        self.grid = PixelGrid(registry)
        self.group_panel = np.array([0, 0, 0, 1, 0, 0], dtype=np.uint8)
        self.group_obst = np.array([1, 0, 0, 1, 0, 0], dtype=np.uint8)
        nf = faults.nav
        self.eps_l = rng.normal(0, nf.nominal_cal_std) + nf.enc_cal_err_left
        self.eps_r = rng.normal(0, nf.nominal_cal_std) + nf.enc_cal_err_right
        self.gyro_bias = rng.normal(0, nf.nominal_gyro_bias_std) + nf.gyro_bias
        self.counts = 4096.0
        self._last_q = None
        self._last_marker = None

    # ---------------------------------------------------------- proprioceptive
    def read_wheels(self):
        """Quantised wheel-angle increments [rad] since the last call and noisy speeds [rad/s]."""
        q = np.array([self.d.qpos[self.qadr_l], self.d.qpos[self.qadr_r]])
        quant = 2.0 * math.pi / self.counts
        q = np.round(q / quant) * quant
        if self._last_q is None:
            self._last_q = q.copy()
        dq = q - self._last_q
        self._last_q = q
        w = np.array([self.d.qvel[self.vadr_l], self.d.qvel[self.vadr_r]]) + self.rng.normal(0, 0.02, 2)
        return dq, w

    def odometry_increments(self, dq: np.ndarray):
        """(ds, dtheta) believed by the robot (wheel radius mis-calibrated by eps)."""
        r = rp.WHEEL_RADIUS
        dsl = r * (1.0 + self.eps_l) * dq[0]
        dsr = r * (1.0 + self.eps_r) * dq[1]
        return 0.5 * (dsl + dsr), (dsr - dsl) / rp.TRACK_WIDTH

    def read_gyro_z(self) -> float:
        return float(self.d.sensordata[self.gyro_adr + 2] + self.gyro_bias + self.rng.normal(0, 0.002))

    def servo_positions(self):
        return (float(self.d.qpos[self.pan_q]), float(self.d.qpos[self.tilt_q]),
                float(self.d.qpos[self.lift_q]))

    # ---------------------------------------------------------- range finders
    def _ray(self, site_name: str, direction: np.ndarray, groups, max_range=6.0):
        pnt = np.array(self.d.site_xpos[self.site[site_name]], dtype=np.float64)
        vec = np.ascontiguousarray(direction, dtype=np.float64)
        gid = np.zeros(1, dtype=np.int32)
        dist = mujoco.mj_ray(self.m, self.d, pnt, vec, groups, 1, self.chassis, gid)
        if dist < 0 or dist > max_range:
            return None
        return float(dist + self.rng.normal(0, 0.004))

    def body_axes(self):
        R = self.d.xmat[self.chassis].reshape(3, 3)
        return R[:, 0], R[:, 1]     # forward (x), left (y) in world

    def read_side_pair(self, left: bool):
        """(d_front, d_rear) distances [m] of the side pair facing the panel row, or None."""
        fwd, lft = self.body_axes()
        direction = lft if left else -lft
        names = ("rf_lf", "rf_lr") if left else ("rf_rf", "rf_rr")
        df = self._ray(names[0], direction, self.group_panel)
        dr = self._ray(names[1], direction, self.group_panel)
        if df is None or dr is None:
            return None
        return df, dr

    def read_front(self):
        fwd, _ = self.body_axes()
        return self._ray("rf_front", fwd, self.group_obst, max_range=4.0)

    # ---------------------------------------------------------- fiducials / irradiance
    def read_fiducial(self, lane_row: int, tol: float = 0.04):
        """Returns the surveyed x of a post marker when the robot crosses one, else None."""
        pos = self.d.xpos[self.chassis]
        if abs(pos[1] - self.reg.lane_y(lane_row)) > 1.0:
            return None
        for mx in self.reg.marker_xs():
            if abs(pos[0] - mx) < tol:
                if self._last_marker == mx:
                    return None
                self._last_marker = mx
                return float(mx + self.rng.normal(0, 0.015))
        self._last_marker = None if all(abs(pos[0] - mx) > 0.25 for mx in self.reg.marker_xs()) else self._last_marker
        return None

    def read_reference_irradiance(self) -> float:
        p = np.array(self.d.site_xpos[self.site["ref_pyranometer"]])
        g = self.env.reference_poa_at(p)
        return float(max(0.0, g * (1.0 + self.rng.normal(0, 0.02))))

    # ---------------------------------------------------------- cameras
    def lens_axis(self, name: str):
        sid = self.site[name]
        return (np.array(self.d.site_xpos[sid]), np.array(self.d.site_xmat[sid]).reshape(3, 3)[:, 0])

    def observe(self, t_sim: float, want_thermal=True, want_optical=True) -> Observation:
        lens, axis = self.lens_axis("thermal_lens")
        hit = self.reg.hit_panel(lens, axis)
        truth = {"hit_panel": None}
        if hit is None:
            return Observation(None, None, truth)
        p_idx, p_hit, _ = hit
        spec = self.reg.panels[p_idx]
        truth.update(hit_panel=spec.pid, hit_xyz=p_hit.copy(), lens=lens.copy(),
                     view_angle_deg=view_angle_deg(lens, spec.center, self.reg.normal),
                     distance=float(np.linalg.norm(lens - spec.center)))
        sf = self.faults.sensor
        thermal = optical = None
        if want_thermal and self.rng.random() >= sf.dropout_prob:
            thermal = ThermalFrame(self._thermal_pixels(p_idx, lens, sf), t_sim)
        if want_optical:
            optical = self._optical(p_idx, lens, p_hit, t_sim)
        return Observation(thermal, optical, truth)

    def _thermal_pixels(self, p_idx: int, lens: np.ndarray, sf) -> np.ndarray:
        env, reg, g = self.env, self.reg, self.grid
        spec = reg.panels[p_idx]
        t_cell = env.T_cells()[p_idx]                                   # (A,C) true
        t_obj = np.kron(t_cell, np.ones((PIX_PER_CELL, PIX_PER_CELL)))   # (pa,pc)
        d = float(np.linalg.norm(lens - spec.center))
        k = float(np.clip((d - 1.5) / 8.0, 0.0, 0.5))                    # optical blur grows with range
        if k > 0:
            p = np.pad(t_obj, 1, mode="edge")
            nb = 0.25 * (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:])
            t_obj = (1 - k) * t_obj + k * nb
        pts = spec.center[None, None, :] + g.offsets
        v = pts - lens[None, None, :]
        v /= np.linalg.norm(v, axis=2, keepdims=True)
        cos_t = np.clip(-(v @ reg.normal), 0.0, 1.0)
        eps = emissivity(np.arccos(cos_t))
        cloud = env.weather.cloud_cover
        t_refl_k = env.t_amb + 273.15 - SIGMA_SKY_K * (1.0 - cloud)
        t_app_k = (eps * (t_obj + 273.15) ** 4 + (1 - eps) * t_refl_k ** 4) ** 0.25
        t_app = t_app_k - 273.15
        if sf.glare_enabled and env.sun.is_up:
            ang = glint_angles_deg(lens, spec.center, reg, g, env.sun.vec)
            t_app = t_app + GLINT_AMP_K * np.exp(-(ang / GLINT_WIDTH_DEG) ** 2) * min(1.0, env.comp["dni"] / 800.0)
        sigma = 0.4 * sf.noise_scale * (1.0 + d / 6.0) / math.sqrt(max(0.3, float(eps.mean())))
        t_app = t_app + self.rng.normal(0, sigma, t_app.shape) + self.rng.normal(0, 0.7)
        spikes = self.rng.random(t_app.shape) < sf.spike_prob
        if spikes.any():
            t_app = t_app + spikes * self.rng.uniform(sf.spike_mag[0], sf.spike_mag[1], t_app.shape)
        return t_app

    def _optical(self, p_idx: int, lens: np.ndarray, p_hit: np.ndarray, t_sim: float) -> OpticalFrame:
        env, reg = self.env, self.reg
        spec = reg.panels[p_idx]
        d = float(np.linalg.norm(lens - spec.center))
        th = view_angle_deg(lens, spec.center, reg.normal)
        vis = math.exp(-d / 10.0) * math.sqrt(max(0.0, math.cos(math.radians(th))))
        if env.sun.is_up:
            ang = glint_angles_deg(lens, spec.center, reg, self.grid, env.sun.vec)
            frac = float((ang < 12.0).mean())
            vis *= (1.0 - 0.7 * min(1.0, frac * 4.0)) if env.comp["dni"] > 100 else 1.0
        sig = 0.06
        crack = obstr = 0.0
        for dfc in self.env.gt.by_panel(spec.pid):
            if dfc.kind is DefectKind.CRACK:
                crack = max(crack, dfc.severity * vis)
            elif dfc.kind is DefectKind.OBSTRUCTION:
                obstr = max(obstr, 0.95 * vis)
        shade_frac = float((env.shade_ext[p_idx] > 0.5).mean())
        shadow = min(1.0, 6.0 * shade_frac) * vis
        # frame-edge registration: along-row offset of the true aim point from the nearest module centre
        k_true = reg.nearest_col(float(p_hit[0]))
        off = float(p_hit[0] - reg.panel_x(k_true)) + self.rng.normal(0, 0.02)
        r = self.rng
        return OpticalFrame(max(0.0, crack + r.normal(0, sig)), max(0.0, obstr + r.normal(0, sig)),
                            max(0.0, shadow + r.normal(0, sig)), off, t_sim)
