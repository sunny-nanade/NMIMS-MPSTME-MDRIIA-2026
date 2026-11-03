"""Dynamic solar environment: sun, weather, shading, irradiance and thermal state
for every module, advanced in step with the physics simulation.

Time handling
-------------
``t_env`` is the local clock time (seconds after local midnight of ``date``).
Each simulation second advances the environment by ``time_scale`` seconds, so a
demo can run the sun and the thermal dynamics faster than real time
(``time_scale = 1`` is real time; the Monte-Carlo experiments use 1).
The thermal state is warmed up by integrating the same model for
``warmup_s`` seconds *before* the start time, so inertia is already present at t=0.

Nothing here assigns a temperature directly: every cell's temperature is the
result of its own irradiance (angle of incidence, row/object shading, cloud
band, diffuse, reflected), the ambient temperature, the wind and the thermal
lag.
"""
from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field

import numpy as np

from fault_injection import GroundTruth
from irradiance_model import (WEATHER_PRESETS, Weather, cell_shading, poa_at_point,
                              poa_cells)
from panel_thermal_model import PanelThermalModel, ThermalParams
from sun_position import SunModel, SunState


@dataclass
class EnvConfig:
    date: _dt.date = _dt.date(2026, 10, 31)
    start_s: float = 11.5 * 3600.0           # local clock time at t=0 [s]
    time_scale: float = 1.0                  # environment seconds per simulated second
    weather: str | Weather = "clear"
    latitude_deg: float = 19.076             # Mumbai (assumption; change for your site)
    longitude_deg: float = 72.8777
    utc_offset_h: float = 5.5
    altitude_km: float = 0.014
    ambient_mean_c: float = 29.0             # late-October Mumbai daily mean (assumption)
    ambient_amp_c: float = 4.5               # half peak-to-peak diurnal swing (assumption)
    ambient_peak_h: float = 14.0
    warmup_s: float = 1800.0
    moving_cloud: bool = False               # travelling cloud-shadow band over the farm
    cloud_speed_ms: float = 1.5
    cloud_width_m: float = 6.0
    cloud_transmittance: float = 0.25        # beam transmitted inside the band
    thermal: ThermalParams = field(default_factory=ThermalParams)

    def resolve_weather(self) -> Weather:
        if isinstance(self.weather, Weather):
            return self.weather
        return WEATHER_PRESETS[self.weather]


class SolarEnvironment:
    def __init__(self, registry, config: EnvConfig | None = None,
                 ground_truth: GroundTruth | None = None, seed: int = 0):
        self.reg = registry
        self.cfg = config or EnvConfig()
        self.gt = ground_truth or GroundTruth(registry, [])
        self.rng = np.random.default_rng(seed)
        self.weather = self.cfg.resolve_weather()
        self.sun_model = SunModel(self.cfg.latitude_deg, self.cfg.longitude_deg,
                                  self.cfg.utc_offset_h)
        self.thermal = PanelThermalModel(registry, self.rng, self.cfg.thermal)
        self._ext_boxes = self.gt.ext_boxes()
        self._obst = self.gt.obstruction_mask()
        self._wind_dev = 0.0
        self._cloud_x0 = float(self.rng.uniform(-8.0, 0.0))
        self.t_env = self.cfg.start_s
        self.t_sim = 0.0
        # state (filled by _forcing)
        self.sun: SunState | None = None
        self.t_amb = 0.0
        self.wind = 0.0
        self.g_cell = None
        self.shade_ext = None
        self.shade_total = None
        self.comp: dict = {}
        self.reset()

    # ------------------------------------------------------------------ core
    def _ambient(self, t_s: float) -> float:
        h = (t_s / 3600.0) % 24.0
        return (self.cfg.ambient_mean_c + self.weather.ambient_offset_c
                + self.cfg.ambient_amp_c * math.cos(2.0 * math.pi * (h - self.cfg.ambient_peak_h) / 24.0))

    def _step_wind(self, dt: float):
        tau = 60.0
        a = math.exp(-dt / tau)
        self._wind_dev = (self._wind_dev * a + self.weather.wind_gust_std_ms
                          * math.sqrt(max(0.0, 1.0 - a * a)) * float(self.rng.standard_normal()))
        self.wind = max(0.3, self.weather.wind_mean_ms + self._wind_dev)

    def _cloud_transmission(self, t_s: float) -> np.ndarray | float:
        if not self.cfg.moving_cloud:
            return 1.0
        xc = self._cloud_x0 + self.cfg.cloud_speed_ms * (t_s - self.cfg.start_s + self.cfg.warmup_s)
        # cloud band repeats every 60 m so the demo keeps seeing passages
        x = self.reg.cell_centers[..., 0]
        d = ((x - xc + 30.0) % 60.0) - 30.0
        band = 1.0 / (1.0 + np.exp((np.abs(d) - self.cfg.cloud_width_m / 2.0) / 0.6))
        return 1.0 - (1.0 - self.cfg.cloud_transmittance) * band

    def _forcing(self, t_s: float):
        self.sun = self.sun_model.at(self.cfg.date, t_s)
        self.t_amb = self._ambient(t_s)
        self.shade_ext = cell_shading(self.reg, self.sun.vec, self._ext_boxes, None)
        self.shade_total = np.maximum(self.shade_ext, self._obst.astype(float))
        r = poa_cells(self.reg, self.sun, self.weather, self.shade_total, self.cfg.altitude_km)
        ct = self._cloud_transmission(t_s)
        g = r["G_beam_unshaded"] * (1.0 - self.shade_total) * ct + r["G_diffuse"] + r["G_reflected"]
        self.g_cell = g
        self.comp = dict(r, cloud_t_mean=float(np.mean(ct)))
        self._beam_unshaded = r["G_beam_unshaded"] * float(np.mean(ct))

    def _excess(self):
        return self.gt.excess_ss(self.g_cell, self.shade_total, self._beam_unshaded)

    def reset(self):
        """Initialise the thermal state by integrating from ``start - warmup``."""
        t0 = self.cfg.start_s - self.cfg.warmup_s
        self._wind_dev = 0.0
        self._step_wind(0.0)
        self._forcing(t0)
        self.thermal.warm_start(self.g_cell, self.t_amb, self.wind, self._excess())
        dt = 10.0
        t = t0
        while t < self.cfg.start_s - 1e-9:
            t += dt
            self._step_wind(dt)
            self._forcing(t)
            self.thermal.step(dt, self.g_cell, self.t_amb, self.wind, self._excess())
        self.t_env = self.cfg.start_s
        self.t_sim = 0.0
        self._forcing(self.t_env)

    def advance(self, dt_sim: float):
        """Advance by ``dt_sim`` simulated seconds (environment advances by scale * dt)."""
        dt_env = dt_sim * self.cfg.time_scale
        self.t_sim += dt_sim
        self.t_env += dt_env
        self._step_wind(dt_env)
        self._forcing(self.t_env)
        self.thermal.step(dt_env, self.g_cell, self.t_amb, self.wind, self._excess())

    # ----------------------------------------------------------- accessors
    @property
    def date_time_str(self) -> str:
        s = self.t_env % 86400.0
        return f"{self.cfg.date.isoformat()} {int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d}"

    def T_cells(self) -> np.ndarray:
        """TRUE cell temperatures [deg C], shape (N, A, C). Ground-truth model state."""
        return self.thermal.T

    def panel_snapshot(self, pid: str) -> dict:
        """Model-state values for one module (these are simulated state, not sensor data)."""
        p = self.reg.index(pid)
        spec = self.reg.get(pid)
        T = self.thermal.T[p]
        return {
            "panel_id": pid, "row": spec.row, "col": spec.col,
            "x_m": float(spec.center[0]), "y_m": float(spec.center[1]), "z_m": float(spec.center[2]),
            "tilt_deg": self.reg.cfg.tilt_deg, "azimuth_deg": 180.0,
            "G_poa_mean_Wm2": float(self.g_cell[p].mean()),
            "G_poa_min_Wm2": float(self.g_cell[p].min()),
            "T_ambient_C": float(self.t_amb), "wind_ms": float(self.wind),
            "T_panel_mean_C": float(T.mean()), "T_cell_max_C": float(T.max()),
            "T_cell_min_C": float(T.min()),
            "shaded_cell_fraction": float((self.shade_total[p] > 0.5).mean()),
            "sun_elevation_deg": float(self.sun.elevation_deg),
            "sun_azimuth_deg": float(self.sun.azimuth_deg),
            "dni_Wm2": float(self.comp["dni"]), "dhi_Wm2": float(self.comp["dhi"]),
            "ghi_Wm2": float(self.comp["ghi"]), "cos_aoi": float(self.comp["cos_aoi"]),
            "time": self.date_time_str,
        }

    def reference_poa_at(self, point: np.ndarray) -> float:
        """True POA irradiance on a co-planar reference cell at ``point`` (before sensor noise)."""
        g = poa_at_point(self.reg, point, self.sun, self.weather, self._ext_boxes)
        # beam share affected by moving cloud: approximate with farm-mean transmission
        g_beam = self.comp["G_beam_unshaded"]
        ct = float(self.comp.get("cloud_t_mean", 1.0))
        return g - g_beam * (1.0 - ct) if g > self.comp["G_diffuse"] + self.comp["G_reflected"] else g
