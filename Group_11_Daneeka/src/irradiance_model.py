"""Clear-sky, weather-adjusted and per-cell plane-of-array (POA) irradiance.

Components
----------
1. Clear sky: Hottel (1976) atmospheric transmittance for the beam component and
   the Liu-Jordan diffuse correlation (as presented in Duffie & Beckman,
   *Solar Engineering of Thermal Processes*). Climate-type correction factors
   for "tropical" are applied; a ``haze`` multiplier (assumption) lets the user
   represent the typically hazier Mumbai atmosphere.
2. Clouds: Kasten-Czeplak (1980) global-irradiance reduction
   GHI = GHI_clear * (1 - 0.75 * N^3.4), N = cloud fraction 0..1. The beam
   share is reduced consistently and diffuse is raised (engineering
   approximation, documented in documentation/model_assumptions.md).
3. POA on a tilted plane: beam * cos(AOI) * (1 - shade) + isotropic sky diffuse
   (Liu-Jordan) + ground-reflected (albedo).
4. Shading: every PV cell centre is ray-traced towards the sun against the
   module rows (one rectangle per row) and against box-shaped external objects.
   So row-to-row shading, end effects and object shadows are resolved per cell.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Weather:
    cloud_cover: float = 0.0     # N, 0 (clear) .. 1 (overcast)
    haze: float = 0.85           # beam transmittance multiplier (assumption)
    albedo: float = 0.20         # ground reflectance (gravel/compacted soil, assumption)
    ambient_offset_c: float = 0.0
    wind_mean_ms: float = 2.0
    wind_gust_std_ms: float = 0.6


WEATHER_PRESETS = {
    "clear": Weather(cloud_cover=0.0, haze=0.85, wind_mean_ms=2.0),
    "hazy": Weather(cloud_cover=0.1, haze=0.70, wind_mean_ms=1.5),
    "partly_cloudy": Weather(cloud_cover=0.4, haze=0.85, wind_mean_ms=3.0, ambient_offset_c=-1.0),
    "overcast": Weather(cloud_cover=0.9, haze=0.85, wind_mean_ms=3.5, ambient_offset_c=-3.0),
    "windy_clear": Weather(cloud_cover=0.0, haze=0.85, wind_mean_ms=6.0, wind_gust_std_ms=1.5),
}


def clear_sky_hottel(elev_deg: float, e0n: float, altitude_km: float = 0.014,
                     haze: float = 1.0):
    """Return (DNI, DHI, GHI) in W/m^2 for a clear sky (Hottel 1976, tropical climate)."""
    cosz = math.sin(math.radians(elev_deg))
    if cosz <= 0.01:
        return 0.0, 0.0, 0.0
    a = altitude_km
    a0 = (0.4237 - 0.00821 * (6.0 - a) ** 2) * 0.95
    a1 = (0.5055 + 0.00595 * (6.5 - a) ** 2) * 0.98
    k = (0.2711 + 0.01858 * (2.5 - a) ** 2) * 1.02
    tau_b = a0 + a1 * math.exp(-k / cosz)
    dni = e0n * tau_b * haze
    tau_d = 0.2710 - 0.2939 * tau_b
    dhi = e0n * cosz * max(tau_d, 0.0)
    ghi = dni * cosz + dhi
    return dni, dhi, ghi


def apply_clouds(dni_clear: float, dhi_clear: float, ghi_clear: float, cosz: float, n: float):
    """Kasten-Czeplak cloud reduction; returns (DNI, DHI, GHI)."""
    n = min(max(n, 0.0), 1.0)
    if ghi_clear <= 0.0 or cosz <= 0.01:
        return 0.0, 0.0, 0.0
    ghi = ghi_clear * (1.0 - 0.75 * n ** 3.4)
    dhi = min(ghi, dhi_clear * (1.0 - n) + n * 0.9 * ghi)
    dni = max(0.0, (ghi - dhi) / cosz)
    return dni, dhi, ghi


def irradiance_components(sun, weather: Weather, altitude_km: float = 0.014):
    """Horizontal/normal irradiance for a SunState and Weather."""
    cosz = sun.zenith_cos
    d, f, g = clear_sky_hottel(sun.elevation_deg, sun.extraterrestrial_normal,
                               altitude_km, weather.haze)
    return apply_clouds(d, f, g, cosz, weather.cloud_cover)


def _ray_rect_shadow(points: np.ndarray, s: np.ndarray, centers, half_w, half_l,
                     normal: np.ndarray, along: np.ndarray, up: np.ndarray,
                     skip_row_of_point: np.ndarray | None = None) -> np.ndarray:
    """True where the ray point->sun is blocked by one of the rectangles.

    points: (M,3); centers: (R,3); skip_row_of_point: (M,) row index (0-based) to ignore
    (a cell cannot be shaded by its own module).
    """
    M = points.shape[0]
    R = centers.shape[0]
    denom = float(normal @ s)
    if abs(denom) < 1e-9:
        return np.zeros(M, bool)
    # t = n.(c - p) / n.s  for each (point,row)
    t = ((centers[None, :, :] - points[:, None, :]) @ normal) / denom       # (M,R)
    hit = points[:, None, :] + t[:, :, None] * s[None, None, :]              # (M,R,3)
    rel = hit - centers[None, :, :]
    inside = (np.abs(rel @ along) <= half_w[None, :]) & (np.abs(rel @ up) <= half_l[None, :])
    blocked = inside & (t > 1e-4)
    if skip_row_of_point is not None:
        blocked[np.arange(M), skip_row_of_point] = False
    return blocked.any(axis=1)


def _ray_box_shadow(points: np.ndarray, s: np.ndarray, box_min: np.ndarray,
                    box_max: np.ndarray) -> np.ndarray:
    """Slab-method ray/AABB test for M points against B boxes. Returns (M,) bool."""
    if box_min.shape[0] == 0:
        return np.zeros(points.shape[0], bool)
    inv = np.where(np.abs(s) < 1e-12, 1e12, 1.0 / s)
    t1 = (box_min[None, :, :] - points[:, None, :]) * inv
    t2 = (box_max[None, :, :] - points[:, None, :]) * inv
    tmin = np.minimum(t1, t2).max(axis=2)
    tmax = np.maximum(t1, t2).min(axis=2)
    return ((tmax >= np.maximum(tmin, 1e-4))).any(axis=1)


def cell_shading(registry, sun_vec: np.ndarray, ext_boxes: tuple | None = None,
                 obstruction_mask: np.ndarray | None = None) -> np.ndarray:
    """Per-cell direct-beam shading fraction in [0,1], shape (N,A,C).

    ``ext_boxes``: (box_min (B,3), box_max (B,3)) for external objects.
    ``obstruction_mask``: (N,A,C) bool for opaque foreign objects lying ON the module.
    """
    N = len(registry)
    A, C = registry.cfg.cells_along, registry.cfg.cells_across
    if sun_vec[2] <= 0.0:
        return np.ones((N, A, C))
    pts = registry.cell_centers.reshape(-1, 3)
    occ = registry.rect_occluders()
    skip = np.repeat(registry.rows - 1, A * C)
    sh = _ray_rect_shadow(pts, sun_vec, occ["center"], occ["half_w"], occ["half_l"],
                          registry.normal, registry.along_row, registry.up_slope, skip)
    if ext_boxes is not None:
        sh |= _ray_box_shadow(pts, sun_vec, ext_boxes[0], ext_boxes[1])
    out = sh.reshape(N, A, C).astype(float)
    if obstruction_mask is not None:
        out = np.maximum(out, obstruction_mask.astype(float))
    return out


def poa_cells(registry, sun, weather: Weather, shade: np.ndarray,
              altitude_km: float = 0.014):
    """Plane-of-array irradiance per cell.

    Returns dict with G_poa (N,A,C), G_beam_unshaded (scalar per cell, same for all),
    dni, dhi, ghi, cos_aoi.
    """
    dni, dhi, ghi = irradiance_components(sun, weather, altitude_km)
    n = registry.normal
    cos_aoi = max(float(n @ sun.vec), 0.0) if sun.is_up else 0.0
    beta = registry.cfg.tilt
    g_beam = dni * cos_aoi
    g_diff = dhi * (1.0 + math.cos(beta)) / 2.0
    g_refl = ghi * weather.albedo * (1.0 - math.cos(beta)) / 2.0
    g = g_beam * (1.0 - shade) + g_diff + g_refl
    return {"G_poa": g, "G_beam_unshaded": g_beam, "G_diffuse": g_diff, "G_reflected": g_refl,
            "dni": dni, "dhi": dhi, "ghi": ghi, "cos_aoi": cos_aoi}


def poa_at_point(registry, point: np.ndarray, sun, weather: Weather,
                 ext_boxes: tuple | None = None):
    """POA irradiance on an unshaded-by-itself reference sensor at ``point`` (robot-mounted
    reference cell co-planar with the array). Row shadows and external boxes apply."""
    pts = np.asarray(point, float).reshape(1, 3)
    occ = registry.rect_occluders()
    sh = 0.0
    if sun.is_up:
        b = _ray_rect_shadow(pts, sun.vec, occ["center"], occ["half_w"], occ["half_l"],
                             registry.normal, registry.along_row, registry.up_slope, None)
        sh = float(b[0])
        if ext_boxes is not None and not b[0]:
            sh = float(_ray_box_shadow(pts, sun.vec, ext_boxes[0], ext_boxes[1])[0])
    else:
        sh = 1.0
    r = poa_cells(registry, sun, weather, np.array([[[sh]]]))
    return float(r["G_poa"].ravel()[0])
