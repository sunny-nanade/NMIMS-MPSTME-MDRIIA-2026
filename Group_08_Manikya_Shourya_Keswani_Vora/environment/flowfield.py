"""
flowfield.py — how the flood water actually moves through the valley.

Solves 2-D potential flow (Laplace's equation for the velocity potential)
over every wet cell of the valley on a 1 m grid, with every building
footprint as a solid obstacle (no flow through walls) and the torrent
entering from the gorge at the head of the valley. The result:

  dir    unit flow direction — water bends around both sides of each building
  speed  m/s — the valley's current profile (fast channel, slower streets,
         torrent in the gorge) modulated by the potential-flow speed-up/slow-
         down: water piles up and slows in front of a building, accelerates
         through gaps between buildings
  impact where the current runs into an upstream wall (pile-up, splashing)
  shear  along the side walls the water scrapes past
  wake   the turbulent wake trailing downstream of each building

Used by the water shader (foam, waves and texture advected along the flow,
wakes) and to move the floating debris. Cached in assets/flowfield.npz.
"""
import math
import os

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, binary_dilation

import scene_generator as sg

RES = 1.0           # metres per cell


def building_footprints(layout):
    """Axis-aligned footprints (cx, cy, hx, hy) of every building standing in the flood."""
    fp = [(h.x, h.y, h.footprint, h.footprint) for h in layout.houses]
    for b in layout.background_houses:
        for ox, oy, fx, fy, bz, hh in b.parts:
            if bz == 0:
                fp.append((b.x + ox, b.y + oy, fx, fy))
    return fp


def compute(terrain, layout):
    L = sg.DOMAIN_HALF
    n = int(round(2 * L / RES)) + 1
    xs = np.linspace(-L, L, n)
    ys = np.linspace(-L, L, n)                                # rows run −y → +y here
    X, Y = np.meshgrid(xs, ys)

    def grid_sample(g, x, y):
        gi = (x + L) / (2 * L) * (sg.GRID - 1)
        gj = (L - y) / (2 * L) * (sg.GRID - 1)               # terrain grids: row 0 = +y
        return map_coordinates(g, [gj, gi], order=1, mode="nearest")

    ground = grid_sample(terrain.heights, X, Y)
    surface = grid_sample(terrain.water, X, Y)
    wet = surface > ground + 0.15
    solid = np.zeros_like(wet)
    for cx, cy, hx, hy in building_footprints(layout):
        solid |= (np.abs(X - cx) <= hx) & (np.abs(Y - cy) <= hy)
    fluid = wet & ~solid

    # ---- potential flow:  lap(phi) = 0 in the fluid, no-flux at walls/banks,
    #      phi = 1 where the torrent enters (top of the gorge), 0 at the outlet
    idx = -np.ones(fluid.shape, int)
    cells = np.argwhere(fluid)
    idx[fluid] = np.arange(len(cells))
    inlet = fluid & (Y > L - 8)
    outlet = fluid & (Y < -L + 6)
    rows, cols, vals = [], [], []
    b = np.zeros(len(cells))
    for k, (i, j) in enumerate(cells):
        if inlet[i, j] or outlet[i, j]:
            rows.append(k); cols.append(k); vals.append(1.0)
            b[k] = 1.0 if inlet[i, j] else 0.0
            continue
        diag = 1e-7
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ii, jj = i + di, j + dj
            if 0 <= ii < n and 0 <= jj < n and fluid[ii, jj]:
                rows.append(k); cols.append(idx[ii, jj]); vals.append(-1.0)
                diag += 1.0
        rows.append(k); cols.append(k); vals.append(diag)
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(len(cells), len(cells)))
    phi = np.zeros(fluid.shape)
    phi[fluid] = spsolve(A, b)

    # velocity = −grad(phi), using only fluid neighbours (no flux through walls)
    def dphi(axis):
        p = np.where(fluid, phi, np.nan)
        fwd = np.roll(p, -1, axis) - p
        bwd = p - np.roll(p, 1, axis)
        g = np.where(np.isnan(fwd), bwd, np.where(np.isnan(bwd), fwd, 0.5 * (fwd + bwd)))
        return np.nan_to_num(g) / RES
    gx, gy = -dphi(1), -dphi(0)
    mag = np.hypot(gx, gy)
    ux = np.where(mag > 0, gx / (mag + 1e-12), 0.0)
    uy = np.where(mag > 0, gy / (mag + 1e-12), -1.0)
    ux, uy = gaussian_filter(ux, 0.7), gaussian_filter(uy, 0.7)
    nrm = np.hypot(ux, uy) + 1e-9
    ux, uy = ux / nrm, uy / nrm

    # local speed-up / slow-down relative to the surrounding flow
    w = gaussian_filter(fluid.astype(float), 10.0) + 1e-6
    mag_ref = gaussian_filter(np.where(fluid, mag, 0.0), 10.0) / w
    fac = np.clip((mag / (mag_ref + 1e-12)) ** 0.7, 0.15, 2.2)
    fac = np.where(fluid, gaussian_filter(fac, 0.8), 0.0)

    # the valley's current profile (channel, streets, gorge torrent) — same as the shader
    N = X - sg.centerline(Y)
    chan = sg._smooth((-N - 1.0) / 5.0) * sg._smooth((N - sg.CHANNEL_LEFT_N - 1.0) / 4.0)
    wgy, wgx = np.gradient(terrain.water, 2 * L / (sg.GRID - 1))
    gorge = sg._smooth(grid_sample(np.hypot(wgx, wgy), X, Y) / 0.10)
    base = (2.5 + 9.0 * chan) + 13.0 * gorge
    speed = base * fac

    # ---- interaction with buildings
    dist, (ni, nj) = distance_transform_edt(~solid, return_indices=True)
    dist = dist * RES
    nx = (X - xs[nj]); ny = (Y - ys[ni])
    nn = np.hypot(nx, ny) + 1e-9
    nx, ny = nx / nn, ny / nn                                 # outward wall normal
    toward = np.clip(-(ux * nx + uy * ny), 0, 1)              # current heading into the wall
    impact = np.exp(-dist / 1.6) * toward * fluid
    shear = np.exp(-dist / 2.0) * (1 - toward) * np.clip(1 - np.abs(ux * nx + uy * ny), 0, 1) * fluid
    wake = binary_dilation(solid, iterations=1).astype(float) * 1.0
    for _ in range(70):                                       # smear downstream along the flow
        src = map_coordinates(wake, [(Y - uy * 1.0 + L) / RES, (X - ux * 1.0 + L) / RES], order=1, mode="nearest")
        wake = np.maximum(wake, 0.965 * src)
    wake = np.where(solid, 0.0, wake) * fluid

    return dict(L=L, res=RES, ux=ux.astype(np.float32), uy=uy.astype(np.float32),
                speed=speed.astype(np.float32), impact=impact.astype(np.float32),
                shear=shear.astype(np.float32), wake=wake.astype(np.float32),
                fluid=fluid, solid=solid)


def load_or_compute(terrain, layout, path):
    if os.path.exists(path):
        d = dict(np.load(path))
        return {k: (v.item() if v.ndim == 0 else v) for k, v in d.items()}
    f = compute(terrain, layout)
    np.savez_compressed(path, **f)
    return f


class Flow:
    """Bilinear lookups into the flow grids (world x, y in metres)."""

    def __init__(self, f):
        self.f = f
        self.L, self.res = float(f["L"]), float(f["res"])

    def sample(self, key, x, y):
        g = self.f[key]
        x, y = np.asarray(x, float), np.asarray(y, float)
        shp = np.broadcast(x, y).shape
        x, y = np.broadcast_to(x, shp).ravel(), np.broadcast_to(y, shp).ravel()
        v = map_coordinates(g, [(y + self.L) / self.res, (x + self.L) / self.res], order=1, mode="nearest")
        return v.reshape(shp) if shp else float(v[0])

    def velocity(self, x, y):
        s = self.sample("speed", x, y)
        return self.sample("ux", x, y) * s, self.sample("uy", x, y) * s
