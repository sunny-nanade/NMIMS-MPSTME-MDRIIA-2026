"""Solar position (no external dependencies).

Method
------
Declination and equation of time use the Spencer (1971) Fourier series as
tabulated in the NOAA solar-calculation notes (accuracy of the order of 0.25 deg,
sufficient for irradiance and shading at the scale of a robot inspection).
The sun's direction is then built from the standard equatorial -> horizontal
transformation, directly in the world ENU frame used everywhere in this project:

    s_E = -cos(dec) * sin(H)
    s_N =  sin(dec) * cos(lat) - cos(dec) * cos(H) * sin(lat)
    s_U =  sin(dec) * sin(lat) + cos(dec) * cos(H) * cos(lat)

with H the hour angle (positive in the afternoon, i.e. sun in the west).
Building the vector directly avoids azimuth quadrant ambiguities and guarantees
that the vector rendered in MuJoCo/Blender is the same one the Python solar
model uses.

Assumptions: no atmospheric refraction, no elevation-dependent corrections,
civil time given as local clock time with a fixed UTC offset (no DST).
"""
from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass

import numpy as np

SOLAR_CONSTANT = 1367.0  # W/m^2


@dataclass(frozen=True)
class SunState:
    vec: np.ndarray          # unit vector pointing FROM the ground TOWARDS the sun (ENU)
    elevation_deg: float
    azimuth_deg: float       # clockwise from North
    declination_deg: float
    hour_angle_deg: float
    extraterrestrial_normal: float   # W/m^2, includes Earth-Sun distance correction

    @property
    def zenith_cos(self) -> float:
        return float(self.vec[2])

    @property
    def is_up(self) -> bool:
        return self.vec[2] > 0.0

    @property
    def light_direction(self) -> np.ndarray:
        """Direction the light TRAVELS (what a renderer's directional light wants)."""
        return -self.vec


class SunModel:
    def __init__(self, latitude_deg: float = 19.076, longitude_deg: float = 72.8777,
                 utc_offset_h: float = 5.5):
        self.lat = math.radians(latitude_deg)
        self.lat_deg = latitude_deg
        self.lon_deg = longitude_deg
        self.tz = utc_offset_h

    def at(self, date: _dt.date, local_seconds: float) -> SunState:
        """Sun state at local clock time ``local_seconds`` after local midnight of ``date``.

        ``local_seconds`` may exceed 86400 or be negative; the date is rolled accordingly.
        """
        extra_days, local_seconds = divmod(local_seconds, 86400.0)
        d = date + _dt.timedelta(days=int(extra_days))
        doy = d.timetuple().tm_yday
        hour = local_seconds / 3600.0
        gamma = 2.0 * math.pi / 365.0 * (doy - 1 + (hour - 12.0) / 24.0)
        eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                           - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
        decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
                - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
                - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
        time_offset = eqtime + 4.0 * self.lon_deg - 60.0 * self.tz          # minutes
        tst = hour * 60.0 + time_offset                                      # true solar time, min
        ha = math.radians(tst / 4.0 - 180.0)
        cl, sl = math.cos(self.lat), math.sin(self.lat)
        cd, sd = math.cos(decl), math.sin(decl)
        s_e = -cd * math.sin(ha)
        s_n = sd * cl - cd * math.cos(ha) * sl
        s_u = sd * sl + cd * math.cos(ha) * cl
        vec = np.array([s_e, s_n, s_u])
        vec /= np.linalg.norm(vec)
        elev = math.degrees(math.asin(max(-1.0, min(1.0, vec[2]))))
        az = math.degrees(math.atan2(vec[0], vec[1])) % 360.0
        e0 = SOLAR_CONSTANT * (1.00011 + 0.034221 * math.cos(gamma) + 0.00128 * math.sin(gamma)
                               + 0.000719 * math.cos(2 * gamma) + 0.000077 * math.sin(2 * gamma))
        return SunState(vec=vec, elevation_deg=elev, azimuth_deg=az,
                        declination_deg=math.degrees(decl),
                        hour_angle_deg=math.degrees(ha), extraterrestrial_normal=e0)
