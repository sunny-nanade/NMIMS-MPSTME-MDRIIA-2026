"""Pure optics helpers shared by the sensor model and the detector (no ground-truth access)."""
import numpy as np


def fresnel_reflectance(theta_rad: np.ndarray, n: float = 1.5) -> np.ndarray:
    ci = np.clip(np.cos(theta_rad), 1e-6, 1.0)
    si = np.sqrt(np.clip(1.0 - ci ** 2, 0.0, 1.0))
    st = si / n
    ct = np.sqrt(np.clip(1.0 - st ** 2, 0.0, 1.0))
    rs = ((ci - n * ct) / (ci + n * ct)) ** 2
    rp_ = ((n * ci - ct) / (n * ci + ct)) ** 2
    return 0.5 * (rs + rp_)


def emissivity(theta_rad: np.ndarray, n: float = 1.5) -> np.ndarray:
    return 1.0 - fresnel_reflectance(theta_rad, n)
