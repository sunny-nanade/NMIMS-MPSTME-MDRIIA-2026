import datetime as dt
import math

import numpy as np

from panel_registry import PanelRegistry
from solar_environment import EnvConfig, SolarEnvironment
from sun_position import SunModel


def test_sun_noon_elevation_mumbai_october():
    sm = SunModel(19.076, 72.8777, 5.5)
    best = max(sm.at(dt.date(2026, 10, 31), h * 3600).elevation_deg for h in np.arange(11, 13.5, 0.05))
    # declination ~ -14 deg on 31 Oct -> noon elevation ~ 90 - 19.1 - 14 = 56.9 deg (+/- 1)
    assert 55.5 < best < 58.5


def test_sun_below_horizon_at_night():
    sm = SunModel(19.076, 72.8777, 5.5)
    assert not sm.at(dt.date(2026, 10, 31), 2 * 3600).is_up


def test_irradiance_plausible_and_thermal_follows():
    reg = PanelRegistry()
    env = SolarEnvironment(reg, EnvConfig(), seed=1)
    g = env.g_cell.mean()
    assert 600 < g < 1100
    t = env.T_cells().mean()
    assert env.t_amb < t < env.t_amb + 45


def test_thermal_inertia_after_cloud():
    reg = PanelRegistry()
    env = SolarEnvironment(reg, EnvConfig(weather="overcast"), seed=1)
    t0 = env.T_cells().mean()
    env.advance(5.0)
    assert abs(env.T_cells().mean() - t0) < 1.0          # a few seconds cannot change a 350 s time constant much


def test_night_has_no_irradiance():
    reg = PanelRegistry()
    env = SolarEnvironment(reg, EnvConfig(start_s=2 * 3600.0), seed=1)
    assert env.g_cell.mean() < 5.0
