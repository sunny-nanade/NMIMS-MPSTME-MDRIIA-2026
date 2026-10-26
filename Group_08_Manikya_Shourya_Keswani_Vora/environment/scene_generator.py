"""
scene_generator.py — Layer A (environment), Sprint 3 of the SkyHydro Roadmap
Owners: Manikya Rathore (E056, lead) / Keswani Laksh (E032)

Generates the flood-relief MJCF scene as ONE continuous mountain valley
(modelled on aerial footage of a Himalayan flash flood): steep green
hillsides on both sides, a muddy flood river running down the valley
floor between them with grey boulder/gravel bars, and a town of
multi-storey flat-roofed buildings on the right bank, flooded at ground
level. The water is a single flat plane at WATER_Z; it only shows where
the terrain dips below it, so the shoreline follows the hills naturally
instead of sitting as a separate square "base".

Mission content (unchanged semantics from the earlier versions):
  * n_houses MISSION houses — rooftop drop markers + standing survivor
    figures (some houses already evacuated → 0 survivors, dim marker).
  * one warehouse with a rooftop pickup pad + staged relief canisters.
  * background buildings and trees are pure scenery (no markers, not in
    the mission FSM's house registry).
  * the OFFICIAL single-slot winch+pendulum UAV (with the motor body=
    bug fixed, see the <actuator> comment), held in a hover by MuJoCo's
    per-body gravity compensation (gravcomp) — NOT a flight controller;
    that is separate, not-yet-built work.

Camera: MuJoCo's `record` sample ignores named <camera> elements and
always uses the default free camera, which reads its target/distance
from <statistic center/extent> and its angle from <visual><global
azimuth/elevation>. So framing is set there (see CAMERA_* below).

Usage:
    python scene_generator.py --houses 5 --seed 1 --output scene_flood.xml
    python scene_generator.py --houses 5 --seed 1 --mask-output scene_flood_mask.xml
      (mask variant: identical scene, water drawn flat magenta — used by
       the post-processing step to know exactly which pixels are water)
"""

from __future__ import annotations

import argparse
import math
import os
import random
from dataclasses import dataclass, field

import numpy as np
from PIL import Image


# ----------------------------------------------------------------------
# World / terrain constants
# ----------------------------------------------------------------------
DOMAIN_HALF = 120.0        # terrain spans [-120, 120] m in x and y
GRID = 481                 # heightfield samples per side (0.5 m spacing)
WATER_Z = 1.2              # flood surface height (ground floors of the town are under ~1.2 m of water)
CHANNEL_Z = -2.0           # river channel bed
TERRACE_Z = 0.0            # flat bank the town is built on
LEFT_TOE_N = -55.0         # across-valley distance where the left (steep) hillside starts
RIGHT_TOE_N = 34.0         # where the right hillside starts
CHANNEL_LEFT_N = -24.0     # left edge of the main river channel (left-bank terrace beyond it)
TOWN_N_MIN, TOWN_N_MAX = 3.0, 30.0     # right-bank town strip (across-valley coords)
TOWN_Y_MIN, TOWN_Y_MAX = -38.0, 42.0   # right-bank town, along the valley
LTOWN_N_MIN, LTOWN_N_MAX = -48.0, -26.0   # left-bank town strip
LTOWN_Y_MIN, LTOWN_Y_MAX = -32.0, 36.0

# Camera (default free camera used by `record`)
CAMERA_AZIMUTH = 106.0     # degrees; ~90 = looking up-valley (+y)
CAMERA_ELEVATION = -36.0   # degrees; negative = looking down
CAMERA_EXTENT = 100.0       # free-camera distance = 1.5 * extent
CAMERA_FOVY = 45.0

# Warehouse sits on a levelled pad high on the right hillside; the river's
# source is a gorge cut through the V-notch at the head of the valley.
WAREHOUSE_N = 82.0         # across-valley position of the hilltop pad (on the summit plateau)
WAREHOUSE_Y = 30.0
PAD_R_IN, PAD_R_OUT = 11.0, 18.0
GORGE_N = -6.0             # gorge centre line (aligned with the V-notch)
UAV_SCALE = 3.5            # drone airframe drawn at small-helicopter size (~5.3 m rotor-tip span, smaller than a roof)

# Buildings
HOUSE_FOOTPRINT_MIN = 3.0
HOUSE_FOOTPRINT_MAX = 3.4
HOUSE_HEIGHT_MIN = 3.0     # half-heights → 6–10 m tall (2–3 storeys), like the hotels in the reference
HOUSE_HEIGHT_MAX = 5.0
WAREHOUSE_FOOTPRINT = 6.0
WAREHOUSE_HEIGHT = 3.0
ROOF_SLAB = 0.12           # thickness of the flat roof slab
STOREY_M = 3.0

WALL_COLORS = ["0.86 0.84 0.79 1", "0.84 0.78 0.62 1", "0.88 0.87 0.84 1", "0.72 0.64 0.55 1", "0.80 0.66 0.55 1",
               "0.68 0.75 0.79 1", "0.72 0.80 0.70 1", "0.62 0.58 0.52 1"]
TIN_COLORS = ["0.24 0.42 0.31 1", "0.21 0.40 0.42 1", "0.33 0.41 0.50 1", "0.55 0.56 0.56 1", "0.44 0.34 0.26 1"]
ROOF_COLORS = ["0.26 0.40 0.30 1", "0.30 0.44 0.33 1", "0.36 0.42 0.48 1", "0.52 0.52 0.51 1", "0.40 0.42 0.42 1", "0.28 0.42 0.32 1"]
WINDOW_RGBA = "0.22 0.25 0.29 1"

HOUSE_DROP_ZONE_OUTER_RGBA = "0.85 0.85 0.2 1"
HOUSE_DROP_ZONE_BULLSEYE_RGBA = "0.85 0.2 0.2 1"
WAREHOUSE_PAD_OUTER_RGBA = "0.2 0.55 0.85 1"
WAREHOUSE_PAD_BULLSEYE_RGBA = "0.95 0.55 0.1 1"

SURVIVOR_SHIRT_COLORS = ["0.75 0.25 0.3 1", "0.2 0.35 0.65 1", "0.3 0.55 0.35 1",
                         "0.55 0.4 0.7 1", "0.85 0.55 0.15 1", "0.25 0.25 0.3 1"]
SKIN_RGBA = "0.76 0.6 0.48 1"

WATER_RGBA = "0.42 0.35 0.27 1"   # muddy, silt-laden flood water (fallback when the live-water texture is absent)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def gorge_surface(y):
    """Water-surface height of the torrent coming down the gorge from the
    V-notch (equals the flood level WATER_Z on the valley floor)."""
    y = np.asarray(y, dtype=float)
    return WATER_Z + 12.5 * _smooth((y - 60.0) / 55.0)


def centerline(y):
    """x-position of the valley's centre line at a given y (gentle meander,
    bending away at the far end so the valley closes behind a hill)."""
    y = np.asarray(y, dtype=float)
    return 12.0 * np.sin(y / 40.0 + 0.5) + 0.004 * np.maximum(y - 45.0, 0.0) ** 2


# ----------------------------------------------------------------------
# Terrain
# ----------------------------------------------------------------------
def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _noise(rng, shape, cells_xy):
    """Smooth value noise in [0,1]: random grid of (cy, cx) cells upsampled bicubically."""
    cx, cy = cells_xy
    g = rng.random((cy, cx)).astype(np.float32)
    img = Image.fromarray(g, mode="F").resize((shape[1], shape[0]), Image.BICUBIC)
    a = np.asarray(img)
    a = (a - a.min()) / max(a.max() - a.min(), 1e-6)
    return a


def _fbm(rng, shape, base_cells, octaves=4, aniso=(1.0, 1.0)):
    total = np.zeros(shape, np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = base_cells * (2 ** o)
        total += amp * _noise(rng, shape, (max(2, int(c * aniso[0])), max(2, int(c * aniso[1]))))
        norm += amp
        amp *= 0.5
    return total / norm


@dataclass
class Terrain:
    heights: np.ndarray        # (GRID, GRID), row 0 = +y (image convention), metres
    xs: np.ndarray             # column x coords
    ys: np.ndarray             # row y coords (descending)
    zmin: float
    zmax: float
    slope_left: np.ndarray     # 0..1 masks used for texturing
    slope_right: np.ndarray
    gravel: np.ndarray
    water: np.ndarray = None   # water-surface height grid (WATER_Z, rising up the gorge)
    pad_z: float = 0.0         # ground height of the hilltop warehouse pad
    pad_x: float = 0.0

    def water_at(self, x: float, y: float) -> float:
        fx = (x + DOMAIN_HALF) / (2 * DOMAIN_HALF) * (GRID - 1)
        fy = (DOMAIN_HALF - y) / (2 * DOMAIN_HALF) * (GRID - 1)
        i, j = int(np.clip(round(fy), 0, GRID - 1)), int(np.clip(round(fx), 0, GRID - 1))
        return float(self.water[i, j])

    def height_at(self, x: float, y: float) -> float:
        fx = (x + DOMAIN_HALF) / (2 * DOMAIN_HALF) * (GRID - 1)
        fy = (DOMAIN_HALF - y) / (2 * DOMAIN_HALF) * (GRID - 1)
        j0, i0 = int(np.clip(math.floor(fx), 0, GRID - 2)), int(np.clip(math.floor(fy), 0, GRID - 2))
        tx, ty = fx - j0, fy - i0
        h = self.heights
        return float((h[i0, j0] * (1 - tx) + h[i0, j0 + 1] * tx) * (1 - ty)
                     + (h[i0 + 1, j0] * (1 - tx) + h[i0 + 1, j0 + 1] * tx) * ty)


def build_terrain(seed: int) -> Terrain:
    rng = np.random.default_rng(seed + 777)
    xs = np.linspace(-DOMAIN_HALF, DOMAIN_HALF, GRID)
    ys = np.linspace(DOMAIN_HALF, -DOMAIN_HALF, GRID)
    X, Y = np.meshgrid(xs, ys)
    n = X - centerline(Y)          # signed across-valley distance (−: left bank, +: right bank)
    shape = X.shape

    # valley floor: deep river channel in the middle, flat flooded terraces
    # (towns) on both banks
    h = CHANNEL_Z + (TERRACE_Z - CHANNEL_Z) * np.maximum(_smooth((n + 4.0) / 4.0),
                                                         _smooth((-n + CHANNEL_LEFT_N) / 3.0))

    # grey boulder/gravel bars poking out of the channel, plus a wide
    # gravel flat along the toe of the left hillside (white boulder fields
    # in the reference photo)
    bars = _fbm(rng, shape, 10, octaves=3, aniso=(0.6, 1.4))
    bar_mask = _smooth((bars - 0.53) / 0.07) * _smooth((-n - 7.0) / 4.0) * _smooth((n - CHANNEL_LEFT_N - 3.0) / 3.0)
    toe = _smooth((-n + (LEFT_TOE_N + 14.0)) / 6.0)   # 0 in the channel, 1 for the last ~14 m before the left hillside
    toe_edge = _fbm(rng, shape, 16, octaves=2)   # ragged edge so the gravel flat isn't a ruler-straight strip
    toe = _smooth((-n + (LEFT_TOE_N + 3.0 + 4.0 * toe_edge)) / 2.0)
    # (mid-channel gravel bars are fully submerged by this flood — only the
    #  boulder flat along the toe of the left hillside stays above water)
    gravel_amount = np.maximum(0.0 * bar_mask, toe)
    gravel_top = WATER_Z + 0.35 + 0.7 * _fbm(rng, shape, 40, octaves=2)
    h = np.where(n < -4.0, h + (gravel_top - h) * gravel_amount, h)

    # hillsides — steep and high on the left, a bit gentler on the right
    ridges = _fbm(rng, shape, 6, octaves=5)
    sl = np.clip((-n - (-LEFT_TOE_N)) / 38.0, 0.0, 1.0)
    sr = np.clip((n - RIGHT_TOE_N) / 42.0, 0.0, 1.0)
    left_h = 64.0 * sl ** 1.15 + 14.0 * (ridges - 0.5) * np.clip(sl * 4, 0, 1)
    right_h = 44.0 * sr ** 1.05 + 10.0 * (ridges - 0.5) * np.clip(sr * 4, 0, 1)
    h = np.maximum(h, np.where(sl > 0, gravel_top * toe + left_h, h))
    h = np.maximum(h, np.where(sr > 0, TERRACE_Z + right_h, h))

    # the far end of the valley rises into a ridge so the view up-valley
    # ends in mountains, not at the edge of the terrain
    far = _smooth((Y - 60.0) / 40.0)
    h = h + far * 50.0 * (0.35 + 0.65 * _smooth((np.abs(n) - 5.0) / 30.0)) + far * 6.0 * (ridges - 0.3)

    # guarantee the town strip is exactly flat ground
    town = ((n > TOWN_N_MIN - 3) & (n < TOWN_N_MAX + 2) & (Y > TOWN_Y_MIN - 6) & (Y < TOWN_Y_MAX + 8)) | \
           ((n > LTOWN_N_MIN - 2) & (n < LTOWN_N_MAX + 1) & (Y > LTOWN_Y_MIN - 6) & (Y < LTOWN_Y_MAX + 6))
    h = np.where(town, TERRACE_Z, h)

    # river source: a gorge cut down through the V-notch at the head of the
    # valley, carrying a torrent that drops to the flood level
    gy = _smooth((Y - 48.0) / 10.0)
    gw = 82.0 - 10.0 * _smooth((Y - 70.0) / 40.0)      # torrent from the notch: wider than the flooded town valley
    dn = np.abs(n - GORGE_N) / gw
    Ws = gorge_surface(Y)
    carve = Ws - 2.6 + 6.0 * dn ** 2 + 2.0 * (ridges - 0.5) * np.clip(dn, 0, 1)   # deep, full channel
    h = np.where(gy > 0, np.minimum(h, carve + (1 - gy) * 200.0), h)
    water = WATER_Z + (Ws - WATER_Z) * _smooth((1.0 - dn) / 0.25)

    # level pad high on the right hillside for the warehouse
    pad_x = float(centerline(WAREHOUSE_Y)) + WAREHOUSE_N
    pi = int(round((DOMAIN_HALF - WAREHOUSE_Y) / (2 * DOMAIN_HALF) * (GRID - 1)))
    pj = int(round((pad_x + DOMAIN_HALF) / (2 * DOMAIN_HALF) * (GRID - 1)))
    pad_z = float(h[pi, pj])
    wpad = _smooth((PAD_R_OUT - np.hypot(X - pad_x, Y - WAREHOUSE_Y)) / (PAD_R_OUT - PAD_R_IN))
    h = h * (1 - wpad) + pad_z * wpad

    return Terrain(heights=h.astype(np.float32), xs=xs, ys=ys,
                   zmin=float(h.min()) - 0.5, zmax=float(h.max()),
                   slope_left=sl, slope_right=sr, gravel=gravel_amount,
                   water=water.astype(np.float32), pad_z=pad_z, pad_x=pad_x)


def write_hfield_bin(terrain: Terrain, path: str) -> None:
    """MuJoCo custom binary hfield: int32 nrow, int32 ncol, float32 data.
    Binary rows run from −y to +y (opposite of PNG — verified with a
    probe render), so flip our image-convention array. MuJoCo normalises
    the data to [0,1] and scales by size[2]; zmin is restored via the
    geom's z-offset."""
    data = np.flipud(terrain.heights - terrain.zmin).astype(np.float32)
    with open(path, "wb") as f:
        f.write(np.array([GRID, GRID], np.int32).tobytes())
        f.write(data.tobytes())


def write_water_hfield_bin(terrain: Terrain, path: str) -> float:
    """Water surface as a second heightfield: flat at WATER_Z over the
    valley, rising up the gorge to the V-notch. Returns its height range."""
    rise = terrain.water - WATER_Z
    with open(path, "wb") as f:
        f.write(np.array([GRID, GRID], np.int32).tobytes())
        f.write(np.flipud(rise).astype(np.float32).tobytes())
    return float(rise.max())


SURFACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "surface")


def _tiled(name: str, tile_m: float, size: int, offset: int = 0, rot: int = 0) -> np.ndarray:
    """A real photo texture from the Unity Standard Assets pack
    (Environment/TerrainAssets/SurfaceTextures, converted from .psd to .png),
    tiled across the terrain so one tile covers tile_m metres."""
    src = Image.open(os.path.join(SURFACE_DIR, name)).convert("RGB")
    px = max(8, int(round(tile_m / (2 * DOMAIN_HALF) * size)))
    t = np.asarray(src.resize((px, px), Image.LANCZOS), dtype=np.float32) / 255.0
    t = np.rot90(t, rot)
    reps = size // px + 2
    big = np.tile(t, (reps, reps, 1))
    return big[offset:offset + size, offset:offset + size]


CANOPY_COLORS = [(0.11, 0.31, 0.12), (0.16, 0.39, 0.14), (0.22, 0.45, 0.16), (0.09, 0.27, 0.15),
                 (0.28, 0.47, 0.17), (0.13, 0.35, 0.18), (0.19, 0.42, 0.20)]


def _canopy_layer(size: int, seed: int, leaf: np.ndarray, density: np.ndarray) -> np.ndarray:
    """Dense forest canopy seen from the air (like the reference aerial
    photo): thousands of individual tree crowns, each a lumpy dome lit from
    the sun's side with a shaded far side, packed edge to edge over dark
    gaps. Leaf micro-detail comes from the real GrassHill photo texture."""
    rng = np.random.default_rng(seed + 99)
    mpp = 2 * DOMAIN_HALF / size
    out = np.empty((size, size, 3), np.float32)
    out[:] = (0.03, 0.07, 0.035)
    leaf_l = leaf.mean(axis=2)
    leaf_l = leaf_l / max(leaf_l.mean(), 1e-6)
    sprites = []
    for k in range(14):
        rm = rng.uniform(1.7, 3.3)
        Rp = max(4, int(rm / mpp))
        yy, xx = np.mgrid[-Rp:Rp + 1, -Rp:Rp + 1].astype(np.float32) / Rp
        ang = np.arctan2(yy, xx)
        edge = 1 + sum(rng.uniform(0.02, 0.07) * np.sin(nn * ang + rng.uniform(0, 6.28)) for nn in (2, 3, 4, 6, 9))
        d = np.sqrt(xx ** 2 + yy ** 2) / edge
        alpha = _smooth((1.0 - d) / 0.2)
        dome = np.sqrt(np.clip(1 - d ** 2, 0, 1))
        # sun from −x, −y (texture: left and bottom): lit side bright, far side in shade
        side = np.clip((-xx + yy) / 1.4, -1, 1)
        # leaf clumps inside the crown
        clump = np.zeros_like(xx)
        for _ in range(9):
            cx_, cy_, cr = rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(0.25, 0.45)
            clump += np.clip(1 - ((xx - cx_) ** 2 + (yy - cy_) ** 2) / cr ** 2, 0, 1) ** 0.7
        clump = clump / max(clump.max(), 1e-6)
        shade = 0.42 + 0.33 * dome + 0.28 * side * dome + 0.22 * clump
        sprites.append((Rp, alpha.astype(np.float32), shade.astype(np.float32)))
    spacing = int(2.9 / mpp)
    jit = spacing * 0.45
    cells = [(r, c) for r in range(0, size, spacing) for c in range(0, size, spacing)]
    order = rng.permutation(len(cells))
    for oi in order:
        r, c = cells[oi]
        r = int(r + rng.uniform(-jit, jit)); c = int(c + rng.uniform(-jit, jit))
        if not (0 <= r < size and 0 <= c < size):
            continue
        if rng.random() > density[r, c]:
            continue
        Rp, alpha, shade = sprites[rng.integers(len(sprites))]
        r0, r1, c0, c1 = r - Rp, r + Rp + 1, c - Rp, c + Rp + 1
        sr0, sc0 = max(0, -r0), max(0, -c0)
        r0c, c0c, r1c, c1c = max(r0, 0), max(c0, 0), min(r1, size), min(c1, size)
        a = alpha[sr0:sr0 + (r1c - r0c), sc0:sc0 + (c1c - c0c)][..., None]
        sh = shade[sr0:sr0 + (r1c - r0c), sc0:sc0 + (c1c - c0c)]
        col = np.array(CANOPY_COLORS[rng.integers(len(CANOPY_COLORS))], np.float32) * rng.uniform(0.85, 1.12)
        tile = col[None, None, :] * (sh * (0.75 + 0.25 * leaf_l[r0c:r1c, c0c:c1c]))[..., None]
        out[r0c:r1c, c0c:c1c] = out[r0c:r1c, c0c:c1c] * (1 - a) + tile * a
    return out


def write_terrain_texture(terrain: Terrain, path: str, seed: int, size: int = 4096) -> None:
    """Colour map draped 1:1 over the heightfield (top of image = +y), built
    from REAL photographic ground textures (Unity Standard Assets:
    GrassHill, GrassRocky, Cliff, Sand) instead of flat colours: grass and
    darker forest floor on the hillsides, bare cliff rock on the steepest
    parts, landslide scars of raw earth on the left slope, pale grey boulder
    fields on the gravel bars and wet silt below the waterline. Two tile
    scales/rotations of each texture are blended by large-scale noise so
    the tiling doesn't show."""
    rng = np.random.default_rng(seed + 4242)
    H = np.asarray(Image.fromarray(terrain.heights, mode="F").resize((size, size), Image.BILINEAR))
    gy, gx = np.gradient(H, (2 * DOMAIN_HALF) / size)
    slope = np.sqrt(gx ** 2 + gy ** 2)
    shape = (size, size)
    xs = np.linspace(-DOMAIN_HALF, DOMAIN_HALF, size)
    ys = np.linspace(DOMAIN_HALF, -DOMAIN_HALF, size)
    X, Y = np.meshgrid(xs, ys)
    n = X - centerline(Y)
    del X, Y, xs, ys

    def mix2(name, tile_a, tile_b, m):
        a = _tiled(name, tile_a, size)
        b = _tiled(name, tile_b, size, offset=37, rot=1)
        return a * (1 - m[..., None]) + b * m[..., None]

    veg_noise = _fbm(rng, shape, 12, octaves=5)
    blotch = _fbm(rng, shape, 30, octaves=3)
    tilemix = _fbm(rng, shape, 20, octaves=2)
    canopy = _fbm(rng, shape, 90, octaves=3)      # tree-crown scale clumping

    grass = mix2("GrassHillAlbedo.png", 5.0, 7.3, tilemix) * np.array([0.92, 0.95, 0.9], np.float32)
    rocky = mix2("GrassRockyAlbedo.png", 4.5, 6.7, tilemix)
    forest = grass * np.array([0.52, 0.62, 0.5], np.float32)         # shaded forest floor
    veg_w = _smooth((veg_noise - 0.4) / 0.25)[..., None]
    patch_w = (_smooth((blotch - 0.62) / 0.12) * 0.7)[..., None]     # stony patches in the grass
    meadow = (grass * (1 - patch_w) + rocky * patch_w) * (0.88 + 0.2 * canopy)[..., None]
    forest_w = _smooth((veg_noise - 0.30) / 0.14)        # mostly forested hillsides, with open meadows
    crowns = _canopy_layer(size, seed, grass, np.clip(forest_w * 1.05, 0, 1))
    veg = meadow * (1 - forest_w[..., None]) + crowns * forest_w[..., None]
    del grass, forest, veg_w, patch_w, crowns, meadow

    cliff = mix2("CliffAlbedoSpecular.png", 10.0, 14.0, tilemix) * 1.1
    steep = _smooth((slope - 2.0) / 0.9)[..., None]
    hill = veg * (1 - steep) + cliff * steep
    del veg, cliff, steep

    sand = mix2("SandAlbedo.png", 6.0, 8.5, tilemix)
    streak = _fbm(rng, shape, 3, octaves=3, aniso=(0.5, 8.0))
    scar = (_smooth((streak - 0.72) / 0.06) * _smooth((-n - 40.0) / 6.0) * (1 - _smooth((-n - 85.0) / 10.0)))[..., None]
    hill = hill * (1 - scar) + sand * 0.85 * scar
    del scar, streak

    lum = rocky.mean(axis=2, keepdims=True)
    boulders = _fbm(rng, shape, 140, octaves=2)
    stones = (0.3 * rocky + 0.7 * lum) * 1.45 * (0.85 + 0.25 * boulders[..., None])
    silt = sand * np.array([0.62, 0.58, 0.54], np.float32)
    del rocky, lum, sand

    above = _smooth((H - (WATER_Z - 0.05)) / 0.12)[..., None]
    on_hill = _smooth((H - (WATER_Z + 1.9)) / 3.0)[..., None]
    land = stones * (1 - on_hill) + hill * on_hill
    wet = (1 - _smooth((H - (WATER_Z + 0.05)) / 0.55))[..., None]      # dark wet band at the waterline
    land = land * (1 - 0.42 * wet)
    col = silt * (1 - above) + land * above
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8), mode="RGB").save(path)


# ----------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------
@dataclass
class House:
    house_id: str
    x: float
    y: float
    footprint: float
    height: float
    survivor_count: int
    wall: str = WALL_COLORS[0]
    roof: str = "0.55 0.56 0.56 1"


@dataclass
class Warehouse:
    x: float
    y: float
    footprint: float = WAREHOUSE_FOOTPRINT
    height: float = WAREHOUSE_HEIGHT
    payloads_available: int = 12
    z: float = 0.0             # ground level (hilltop pad)


@dataclass
class BackgroundHouse:
    x: float
    y: float
    fx: float                  # bounding half-extents of the whole building
    fy: float
    height: float              # bounding half-height
    wall: str
    roof: str
    shape: str = "block"
    parts: list = field(default_factory=list)   # (ox, oy, fx, fy, base_z, half_h) per box


BUILDING_SHAPES = [("block", 0.28), ("tower", 0.12), ("stepped", 0.18), ("L", 0.15), ("row", 0.15), ("shed", 0.12)]


def _make_parts(shape: str, rng: random.Random) -> list:
    """Box parts (body-local, ground at z=0) for a building of the given shape."""
    st = lambda a, b: rng.randint(a, b) * STOREY_M / 2.0        # storeys -> half-height
    if shape == "tower":
        f = rng.uniform(2.2, 2.6)
        return [(0.0, 0.0, f, f, 0.0, st(4, 5))]
    if shape == "stepped":
        fx, fy, h1 = rng.uniform(2.8, 3.1), rng.uniform(3.2, 3.6), st(2, 3)
        return [(0.0, 0.0, fx, fy, 0.0, h1),
                (rng.choice([-1, 1]) * 0.6, rng.choice([-1, 1]) * 0.7, fx * 0.6, fy * 0.6, 2 * h1 + ROOF_SLAB, st(1, 2))]
    if shape == "L":
        return [(-0.9, 0.0, 2.1, rng.uniform(3.2, 3.6), 0.0, st(2, 4)),
                (1.3, rng.choice([-1, 1]) * 1.6, 1.7, 1.8, 0.0, st(1, 2))]
    if shape == "row":
        return [(0.0, -1.85, 2.3, 1.8, 0.0, st(1, 3)), (0.0, 1.85, 2.3, 1.8, 0.0, st(1, 3))]
    if shape == "shed":
        return [(0.0, 0.0, rng.uniform(2.8, 3.1), rng.uniform(3.0, 3.6), 0.0, st(1, 1))]
    return [(0.0, 0.0, rng.uniform(2.5, 3.1), rng.uniform(2.8, 3.6), 0.0, st(2, 4))]


@dataclass
class Tree:
    x: float
    y: float
    z: float
    trunk_h: float
    canopy_r: float
    kind: str = "pine"         # tree mesh asset name, e.g. pine1, broad0
    yaw: float = 0.0


@dataclass
class SceneLayout:
    zone_size: float
    houses: list[House] = field(default_factory=list)
    warehouse: Warehouse | None = None
    background_houses: list[BackgroundHouse] = field(default_factory=list)
    trees: list[Tree] = field(default_factory=list)
    seed: int = 0


def generate_layout(
    n_houses: int = 5,
    survivors_per_house_range: tuple[int, int] = (2, 3),
    seed: int = 0,
    warehouse_end: str = "upstream",
    n_trees: int = 650,
    terrain: Terrain | None = None,
) -> SceneLayout:
    """Town of flat-roofed blocks on the right-bank terrace, laid out in
    rows along the valley (local across-valley coordinate n, along-valley
    y). Warehouse at one end of the strip; n_houses mission houses picked
    from the middle rows; the rest are scenery. Trees are scattered on
    the hillsides and sit on the actual terrain height."""
    if not (3 <= n_houses <= 8):
        raise ValueError(f"n_houses should be 4-5 per the mission scenario (3-8 tolerated); got {n_houses}")
    rng = random.Random(seed)
    terrain = terrain or build_terrain(seed)

    # warehouse: on the levelled hilltop pad above the town (warehouse_end kept for CLI compatibility)
    warehouse = Warehouse(x=round(terrain.pad_x, 2), y=round(WAREHOUSE_Y, 2), z=round(terrain.pad_z, 3))

    # candidate lots on BOTH banks: rows along y, columns across each terrace
    lots = []
    for cols, y0, y1 in (((6.0, 13.0, 20.0, 27.0), TOWN_Y_MIN, TOWN_Y_MAX),
                         ((-44.0, -37.0, -30.0), LTOWN_Y_MIN, LTOWN_Y_MAX)):
        row_y = y0 + 4.0
        while row_y < y1 - 2.0:
            for col_n in cols:
                lots.append((col_n + rng.uniform(-0.3, 0.3), row_y + rng.uniform(-0.4, 0.4)))
            row_y += rng.uniform(8.3, 8.9)

    # mission (drop) houses: scattered over the whole town — far apart, at
    # most two per column so they never line up in a row
    cands = list(lots)
    rng.shuffle(cands)
    chosen = []
    max_side = n_houses - 2                 # at least two drop houses on each bank
    for min_gap in (20.0, 17.0, 14.0, 11.0):
        chosen = []
        for p in cands:
            side_count = sum(1 for q in chosen if (q[0] < 0) == (p[0] < 0))
            if (all(math.hypot(p[0] - q[0], p[1] - q[1]) > min_gap for q in chosen)
                    and side_count < max_side
                    and sum(1 for q in chosen if abs(q[0] - p[0]) < 2.0) < 2
                    and not any(abs(q[0] - p[0]) < 2.0 and abs(q[1] - p[1]) < 36.0 for q in chosen)):
                chosen.append(p)
            if len(chosen) == n_houses:
                break
        if len(chosen) == n_houses:
            break
    if len(chosen) < n_houses:
        raise RuntimeError("Not enough room on the terrace for the requested mission houses.")

    houses = []
    for i, (ln, ly) in enumerate(sorted(chosen, key=lambda p: p[1])):
        fp = rng.uniform(HOUSE_FOOTPRINT_MIN, HOUSE_FOOTPRINT_MAX)
        survivors = 0 if rng.random() < 0.35 else rng.randint(*survivors_per_house_range)
        houses.append(House(
            house_id=f"house_{i + 1}",
            x=round(float(centerline(ly)) + ln, 2), y=round(ly, 2),
            footprint=round(fp, 2), height=rng.choice([1.5, 3.0, 3.0, 4.5, 4.5, 6.0]),   # 1–4 storeys
            survivor_count=survivors, wall=rng.choice(WALL_COLORS), roof="0.58 0.58 0.57 1",
        ))

    bg = []
    for ln, ly in lots:
        if (ln, ly) in chosen:
            continue
        if any(math.hypot(ln - q[0], ly - q[1]) < 7.6 for q in chosen):
            continue                  # open space beside each drop house
        if rng.random() < 0.12:      # a few empty lots, so the town isn't a perfect grid
            continue
        shape = rng.choices([b for b, _ in BUILDING_SHAPES], [w for _, w in BUILDING_SHAPES])[0]
        parts = _make_parts(shape, rng)
        bfx = max(abs(ox) + fx for ox, oy, fx, fy, bz, hh in parts)
        bfy = max(abs(oy) + fy for ox, oy, fx, fy, bz, hh in parts)
        top = max(bz + 2 * hh for ox, oy, fx, fy, bz, hh in parts)
        bg.append(BackgroundHouse(
            x=round(float(centerline(ly)) + ln, 2), y=round(ly, 2),
            fx=round(bfx, 2), fy=round(bfy, 2), height=round(top / 2, 2),
            wall=rng.choice(WALL_COLORS), roof=rng.choice(ROOF_COLORS), shape=shape, parts=parts,
        ))

    # trees on the hillsides (and a few along the right bank behind the town)
    trees = []
    trng = random.Random(seed * 31 + 7)   # separate stream: tree species/rotation
    attempts = 0
    while len(trees) < n_trees and attempts < n_trees * 30:
        attempts += 1
        ty = rng.uniform(-DOMAIN_HALF + 8, DOMAIN_HALF - 8)
        side = rng.random()
        if side < 0.55:
            tn = rng.uniform(LEFT_TOE_N - 70.0, LEFT_TOE_N - 3.0)
        else:
            tn = rng.uniform(RIGHT_TOE_N - 1.0, RIGHT_TOE_N + 55.0)
        tx = float(centerline(ty)) + tn
        if abs(tx) > DOMAIN_HALF - 4:
            continue
        z = terrain.height_at(tx, ty)
        if z < terrain.water_at(tx, ty) + 1.0:
            continue
        if math.hypot(tx - warehouse.x, ty - warehouse.y) < PAD_R_OUT + 2.0:
            continue
        trunk_h, canopy_r = rng.uniform(1.0, 2.0), rng.uniform(0.9, 1.7)
        u = trng.random()
        if z < 12.0:
            sp = "oak" if u < 0.5 else ("chir" if u < 0.9 else "deodar")
        elif z < 28.0:
            sp = "chir" if u < 0.35 else ("deodar" if u < 0.85 else "oak")
        else:
            sp = "fir" if u < 0.55 else "deodar"
        kind = f"{sp}{trng.randrange(2)}"
        trees.append(Tree(x=round(tx, 2), y=round(ty, 2), z=round(z - 0.3, 2),
                          trunk_h=round(trunk_h, 2), canopy_r=round(canopy_r, 2),
                          kind=kind, yaw=round(trng.uniform(0, 2 * math.pi), 3)))

    return SceneLayout(zone_size=2 * DOMAIN_HALF, houses=houses, warehouse=warehouse,
                       background_houses=bg, trees=trees, seed=seed)


# ----------------------------------------------------------------------
# MJCF pieces
# ----------------------------------------------------------------------
# ---- 3D grass ----------------------------------------------------------
# Tufts of curved, tapering blades fanning out from one point (like a real
# grass clump), 0.5–1.0 m tall, planted on the open meadow slopes (and
# sparsely under the forest edge) and following the true ground height.
# Batched into ~16 m patches, three shades per patch. Blades are
# double-sided (MuJoCo culls back faces — verified with a probe render).
GRASS_COLORS = ["0.20 0.33 0.10 1", "0.30 0.45 0.14 1", "0.42 0.56 0.19 1"]
_GRASS_PATCHES: list = []


def _grass_tuft(meshes, x, y, z, rng):
    nb = rng.randint(6, 9)
    scale = rng.uniform(0.75, 1.25)
    for _ in range(nb):
        a = rng.uniform(0, 2 * math.pi)
        lean = math.radians(rng.uniform(8, 38))
        curve = rng.uniform(0.15, 0.45)
        Hb = rng.uniform(0.5, 1.0) * scale
        w0 = rng.uniform(0.07, 0.13) * scale
        dx, dy = math.cos(a), math.sin(a)
        px_, py_ = -dy, dx
        bx, by = x + dx * 0.06 * rng.random(), y + dy * 0.06 * rng.random()

        def pt(s_):
            out_ = math.sin(lean) * s_ * Hb + curve * s_ * s_ * Hb
            up_ = math.cos(lean) * s_ * Hb - 0.35 * curve * s_ * s_ * Hb
            return bx + dx * out_, by + dy * out_, z + up_
        p0, pm, p1 = pt(0.0), pt(0.55), pt(1.0)
        wm = w0 * 0.55
        vs, fs = meshes[rng.choices([0, 1, 2], [0.35, 0.4, 0.25])[0]]
        o = len(vs)
        vs += [(p0[0] - px_ * w0 / 2, p0[1] - py_ * w0 / 2, p0[2]), (p0[0] + px_ * w0 / 2, p0[1] + py_ * w0 / 2, p0[2]),
               (pm[0] - px_ * wm / 2, pm[1] - py_ * wm / 2, pm[2]), (pm[0] + px_ * wm / 2, pm[1] + py_ * wm / 2, pm[2]), p1]
        for a_, b_, c_ in ((0, 1, 3), (0, 3, 2), (2, 3, 4)):
            fs.append((o + a_, o + b_, o + c_))
            fs.append((o + a_, o + c_, o + b_))      # back side


def write_grass(terrain: Terrain, assets_dir: str, seed: int, layout=None, density: float = 1.7) -> None:
    _GRASS_PATCHES.clear()
    d = os.path.join(assets_dir, "grass")
    os.makedirs(d, exist_ok=True)
    # same meadow/forest split as the ground texture (same noise stream)
    veg = _fbm(np.random.default_rng(seed + 4242), (GRID, GRID), 12, octaves=5)
    forest_w = _smooth((veg - 0.30) / 0.14)
    Hh = terrain.heights
    gy, gx = np.gradient(Hh, 2 * DOMAIN_HALF / (GRID - 1))
    slope = np.hypot(gx, gy)
    on_hill = _smooth((Hh - (WATER_Z + 1.9)) / 3.0)
    wgt = ((1 - forest_w) + 0.3 * forest_w) * on_hill * (1 - _smooth((slope - 1.5) / 0.6))
    wgt = np.where(terrain.water > WATER_Z + 0.05, 0.0, wgt)

    def w_at(x, y):
        j = int(round((x + DOMAIN_HALF) / (2 * DOMAIN_HALF) * (GRID - 1)))
        i = int(round((DOMAIN_HALF - y) / (2 * DOMAIN_HALF) * (GRID - 1)))
        if not (0 <= i < GRID and 0 <= j < GRID):
            return 0.0
        return float(wgt[i, j])

    r = random.Random(seed + 5150)
    cell, idx, total = 16.0, 0, 0
    c0 = -DOMAIN_HALF + 4
    for cxi in np.arange(c0, DOMAIN_HALF - 4, cell):
        for cyi in np.arange(c0, DOMAIN_HALF - 4, cell):
            samples = [w_at(cxi + r.uniform(0, cell), cyi + r.uniform(0, cell)) for _ in range(12)]
            mean_w = sum(samples) / len(samples)
            n_t = int(density * cell * cell * mean_w)
            if n_t < 12:
                continue
            meshes = [([], []), ([], []), ([], [])]
            placed = 0
            for _ in range(n_t * 4):
                if placed >= n_t:
                    break
                x, y = cxi + r.uniform(0, cell), cyi + r.uniform(0, cell)
                if layout is not None and math.hypot(x - layout.warehouse.x, y - layout.warehouse.y) < PAD_R_IN:
                    continue
                if r.random() > w_at(x, y):
                    continue
                _grass_tuft(meshes, x, y, terrain.height_at(x, y) - 0.05, r)
                placed += 1
            for c, (vs, fs) in enumerate(meshes):
                if len(vs) >= 4:
                    name = f"grass_{idx}_{c}"
                    _write_obj(os.path.join(d, name + ".obj"), vs, fs)
                    _GRASS_PATCHES.append((name, c))
            idx += 1
            total += placed
    print(f"grass: {total} tufts in {idx} patches")


def grass_assets_xml() -> str:
    out = [f'<material name="grass_c{c}" rgba="{col}" specular="0.05" shininess="0.1"/>' for c, col in enumerate(GRASS_COLORS)]
    out += [f'<mesh name="{n}" file="assets/grass/{n}.obj" inertia="shell"/>' for n, _ in _GRASS_PATCHES]
    return "\n    ".join(out)


def grass_geoms_xml() -> str:
    return "\n".join(f'    <geom name="{n}" type="mesh" mesh="{n}" material="grass_c{c}" group="1" contype="0" conaffinity="0"/>'
                     for n, c in _GRASS_PATCHES)


# ---- building facade detail (meshes) -----------------------------------
# Each building gets two generated meshes in its own body frame: "win"
# (individual glazed windows) and "trim" (window sills, floor bands,
# balconies with solid railings, roof parapets), plus a black rooftop water
# tank and a stair cabin on background buildings. Mission (drop) houses and
# the warehouse keep a flat, open roof — no parapet or rooftop clutter.
GLASS_RGBA = "0.13 0.17 0.21 1"
TRIM_RGBA = "0.91 0.90 0.87 1"
METAL_RGBA = "0.30 0.31 0.32 1"
STAIN_RGBA = "0.33 0.27 0.19 0.55"      # mud line left by the flood on the walls
_BUILDING_MESHES: dict = {}
_GABLE_MESHES: dict = {}
_WALL_MESHES: dict = {}
WALL_TILE_M = 3.0


def _write_obj_uv(path, verts, uvs, norms, faces):
    with open(path, "w") as f:
        for v in verts:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for t in uvs:
            f.write(f"vt {t[0]:.4f} {t[1]:.4f}\n")
        for n_ in norms:
            f.write(f"vn {n_[0]:.4f} {n_[1]:.4f} {n_[2]:.4f}\n")
        for tri in faces:
            f.write("f " + " ".join(f"{a + 1}/{a + 1}/{a + 1}" for a in tri) + "\n")


def _wall_shell(prefix, fx, fy, hh, shift, wall, gable=None):
    """Plastered outer walls as a UV-mapped mesh (MuJoCo's own box mapping
    stretches 2D textures vertically on side faces, which made the plaster
    look like siding). u runs along each facade, v up the wall, 3 m tiles.
    Optional gable-end triangles (for pitched roofs) are included."""
    import zlib
    r = random.Random(zlib.crc32((prefix + "w").encode()))
    uo, vo = r.random(), r.random()
    ox, oy, oz = shift
    V, T, N, F = [], [], [], []
    quads = [((1, 0, 0), [(fx, -fy), (fx, fy)]), ((-1, 0, 0), [(-fx, fy), (-fx, -fy)]),
             ((0, 1, 0), [(fx, fy), (-fx, fy)]), ((0, -1, 0), [(-fx, -fy), (fx, -fy)])]
    for nrm, ((x0, y0), (x1, y1)) in quads:
        L = math.hypot(x1 - x0, y1 - y0)
        b0 = len(V)
        for (x, y, z, u) in ((x0, y0, -hh, 0.0), (x1, y1, -hh, L), (x1, y1, hh, L), (x0, y0, hh, 0.0)):
            V.append((x + ox, y + oy, z + oz)); T.append((u / WALL_TILE_M + uo, (z + oz) / WALL_TILE_M + vo)); N.append(nrm)
        F += [(b0, b0 + 1, b0 + 2), (b0, b0 + 2, b0 + 3)]
        uo += 0.37
    if gable:
        for tri, nrm in gable:
            b0 = len(V)
            for (x, y, z) in tri:
                V.append((x, y, z)); N.append(nrm)
                T.append(((x if abs(nrm[0]) < 0.5 else y) / WALL_TILE_M + uo, z / WALL_TILE_M + vo))
            F.append((b0, b0 + 1, b0 + 2))
    _WALL_MESHES[prefix] = (V, T, N, F, wall_mat(wall).replace("wall_", "wallm_"))
    return f'<geom name="{prefix}_walls" type="mesh" mesh="{prefix}_walls" material="{wall_mat(wall).replace("wall_", "wallm_")}" contype="0" conaffinity="0" mass="1"/>'


def wall_mat(color: str) -> str:
    return f"wall_{WALL_COLORS.index(color)}" if color in WALL_COLORS else "wall_0"


def _tile_noise(n, rng, sig_x, sig_y):
    f = np.fft.fft2(rng.standard_normal((n, n)))
    kx = np.fft.fftfreq(n)[None, :]; ky = np.fft.fftfreq(n)[:, None]
    a = np.real(np.fft.ifft2(f * np.exp(-((kx * sig_x) ** 2 + (ky * sig_y) ** 2))))
    return (a - a.mean()) / (a.std() + 1e-9)


def write_building_textures(assets_dir: str, seed: int = 11) -> None:
    """Seamless greyscale detail textures (tinted per material via rgba):
    weathered plaster (grain, blotches, rain streaks running down), stained
    concrete for flat roofs, and corrugated tin sheet (ribs + rust/dirt) in
    two orientations so the ribs always run down the roof slope."""
    d = os.path.join(assets_dir, "buildings")
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(seed)
    n = 512
    grain = _tile_noise(n, rng, 250, 250)
    blot = _tile_noise(n, rng, 18, 18)
    streak = _tile_noise(n, rng, 45, 2)            # occasional long rain streaks (image columns = vertical on walls)
    mottle = _tile_noise(n, rng, 40, 40)
    pl = 0.90 + 0.015 * grain + 0.035 * blot + 0.02 * mottle - 0.09 * np.clip(streak - 1.7, 0, None)
    Image.fromarray((np.clip(pl, 0, 1) * 255).astype(np.uint8), "L").convert("RGB").save(os.path.join(d, "plaster.png"))
    cblot = _tile_noise(n, rng, 10, 10)
    cg = _tile_noise(n, rng, 200, 200)
    co = 0.80 + 0.06 * cblot + 0.03 * cg - 0.08 * np.clip(_tile_noise(n, rng, 30, 30) - 1.0, 0, None)
    Image.fromarray((np.clip(co, 0, 1) * 255).astype(np.uint8), "L").convert("RGB").save(os.path.join(d, "concrete.png"))
    x = np.arange(n)[None, :] / n
    ribs = 0.80 + 0.20 * np.sin(2 * np.pi * 12 * x) ** 2
    rust = np.clip(_tile_noise(n, rng, 14, 30) - 0.8, 0, None)
    tin = ribs * (0.95 + 0.03 * _tile_noise(n, rng, 100, 100)) - 0.12 * rust
    t8 = (np.clip(np.broadcast_to(tin, (n, n)), 0, 1) * 255).astype(np.uint8)
    Image.fromarray(t8, "L").convert("RGB").save(os.path.join(d, "tin_cols.png"))
    Image.fromarray(np.ascontiguousarray(t8.T), "L").convert("RGB").save(os.path.join(d, "tin_rows.png"))


def _box(mesh, c, h):
    """Append an axis-aligned box (centre c, half-extents h) with flat
    per-face normals (4 unique vertices per face)."""
    vs, ns, fs = mesh
    cx, cy, cz = c
    hx, hy, hz = h
    faces = [((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
             ((-1, 0, 0), [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)]),
             ((0, 1, 0), [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)]),
             ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
             ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
             ((0, 0, -1), [(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)])]
    for nrm, corners in faces:
        base = len(vs)
        for sx, sy, sz in corners:
            vs.append((cx + sx * hx, cy + sy * hy, cz + sz * hz))
        ns.append(nrm)
        ni = len(ns) - 1
        fs.append((base, base + 1, base + 2, ni))
        fs.append((base, base + 2, base + 3, ni))


def _write_obj_n(path, mesh):
    vs, ns, fs = mesh
    with open(path, "w") as f:
        for v in vs:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for n_ in ns:
            f.write(f"vn {n_[0]:.5f} {n_[1]:.5f} {n_[2]:.5f}\n")
        for a, b, c, ni in fs:
            f.write(f"f {a + 1}//{ni + 1} {b + 1}//{ni + 1} {c + 1}//{ni + 1}\n")


def _facade_detail(prefix: str, fx: float, fy: float, half_h: float, kind: str, wall: str,
                   shift=(0.0, 0.0, 0.0), on_ground: bool = True, roof: str = "flat", tin: int = 0) -> str:
    """Architectural detail for one box part of a building (body-local,
    part centred at `shift`):
      glass   — window panes
      trim    — window frames + mullions, sills, concrete sunshades (chajjas),
                corner/intermediate pilasters, floor beams, balcony slabs,
                roof parapet
      metal   — balcony railings with balusters, AC units, drain pipes,
                rolling shutters on the street level
      stain   — translucent mud line left by the flood (ground-level parts)
    plus, on the top part: a flat concrete roof with water tank and stair
    cabin, or a pitched corrugated-tin gable roof."""
    import zlib
    rng = random.Random(zlib.crc32(prefix.encode()))
    glass, trim, metal, stain, door = ([], [], []), ([], [], []), ([], [], []), ([], [], []), ([], [], [])
    n_storeys = max(1, int(round(2 * half_h / STOREY_M)))
    fh = 2 * half_h / n_storeys
    facades = [("x", 1, fy, fx), ("x", -1, fy, fx), ("y", 1, fx, fy), ("y", -1, fx, fy)]

    def put(mesh, axis, sign, off, u, d, z, hu, hd, hz):
        if axis == "x":
            _box(mesh, (sign * (off + d), u, z), (hd, hu, hz))
        else:
            _box(mesh, (u, sign * (off + d), z), (hu, hd, hz))

    ww, wh = (0.75, 0.7) if kind == "warehouse" else (0.5, 0.62)
    balcony_face = rng.randrange(4) if kind in ("bg", "mission") else None
    shop_face = rng.randrange(4) if (on_ground and kind == "bg" and rng.random() < 0.6) else None
    pipe_face = rng.randrange(4)

    # pilasters (RCC columns) at the corners, floor beams, top beam
    for sxp in (-1, 1):
        for syp in (-1, 1):
            _box(trim, (sxp * (fx + 0.02), syp * (fy + 0.02), 0), (0.16, 0.16, half_h))
    for si in range(1, n_storeys):
        _box(trim, (0, 0, -half_h + si * fh), (fx + 0.06, fy + 0.06, 0.11))
    _box(trim, (0, 0, half_h - 0.12), (fx + 0.06, fy + 0.06, 0.12))

    for si in range(n_storeys):
        z0 = -half_h + si * fh
        zc = z0 + fh * 0.55
        for fi, (axis, sign, hl, off) in enumerate(facades):
            L = 2 * hl
            nwin = max(1, int((L - 0.9) / 1.9))
            if si == 0 and fi == shop_face:
                # rolling metal shutter(s) on the street level
                put(metal, axis, sign, off, 0.0, 0.03, z0 + 1.25, hl * 0.72, 0.04, 1.15)
                put(trim, axis, sign, off, 0.0, 0.2, z0 + 2.55, hl * 0.8, 0.22, 0.05)          # awning slab
                continue
            door_k = nwin // 2 if (si == 0 and on_ground and kind in ("bg", "mission")) else -1
            for k in range(nwin):
                u = -hl + L * (k + 0.5) / nwin
                if k == door_k:
                    # open doorway at street level — the flood pours in through it
                    put(door, axis, sign, off, u, 0.012, z0 + 1.1, 0.55, 0.02, 1.1)
                    put(trim, axis, sign, off, u, 0.05, z0 + 2.27, 0.66, 0.05, 0.07)          # lintel
                    put(trim, axis, sign, off, u - 0.61, 0.05, z0 + 1.1, 0.05, 0.05, 1.1)     # jambs
                    put(trim, axis, sign, off, u + 0.61, 0.05, z0 + 1.1, 0.05, 0.05, 1.1)
                    continue
                put(glass, axis, sign, off, u, 0.02, zc, ww, 0.03, wh)
                put(trim, axis, sign, off, u, 0.05, zc + wh + 0.04, ww + 0.07, 0.05, 0.045)      # frame top
                put(trim, axis, sign, off, u, 0.05, zc - wh - 0.04, ww + 0.07, 0.05, 0.045)      # frame bottom
                put(trim, axis, sign, off, u - ww - 0.04, 0.05, zc, 0.045, 0.05, wh)            # frame sides
                put(trim, axis, sign, off, u + ww + 0.04, 0.05, zc, 0.045, 0.05, wh)
                put(trim, axis, sign, off, u, 0.045, zc, 0.025, 0.04, wh)                       # mullion
                put(trim, axis, sign, off, u, 0.045, zc + 0.18, ww, 0.04, 0.022)                # transom
                put(trim, axis, sign, off, u, 0.11, zc - wh - 0.12, ww + 0.14, 0.11, 0.035)      # sill
                put(trim, axis, sign, off, u, 0.24, zc + wh + 0.2, ww + 0.2, 0.24, 0.035)        # chajja sunshade
                if rng.random() < 0.12 and si > 0:                                              # AC unit
                    put(metal, axis, sign, off, u + ww + 0.45, 0.18, zc - 0.25, 0.28, 0.18, 0.2)
            if fi == balcony_face and si > 0:
                bw = min(hl * 0.6, 1.8)
                put(trim, axis, sign, off, 0.0, 0.55, z0 + 0.06, bw, 0.55, 0.07)                 # slab
                put(metal, axis, sign, off, 0.0, 1.07, z0 + 1.02, bw, 0.03, 0.03)                # top rail
                put(metal, axis, sign, off, 0.0, 1.07, z0 + 0.2, bw, 0.02, 0.02)                 # bottom rail
                nb = int(bw * 2 / 0.22)
                for j in range(nb + 1):                                                         # balusters
                    put(metal, axis, sign, off, -bw + j * 2 * bw / nb, 1.07, z0 + 0.6, 0.015, 0.015, 0.42)
                for e in (-1, 1):
                    put(metal, axis, sign, off, e * bw, 0.55, z0 + 1.02, 0.02, 0.55, 0.03)
            if fi == pipe_face:
                put(metal, axis, sign, off, hl - 0.35, 0.07, 0.0, 0.05, 0.05, half_h)           # drain pipe
    if on_ground:   # flood mud-line on the walls, from the waterline up ~0.7 m
        zb = -half_h + WATER_Z - 0.4
        _box(stain, (0, 0, zb + 0.55), (fx + 0.015, fy + 0.015, 0.55))

    extra = ""
    roof_z = half_h + ROOF_SLAB
    ox, oy, oz = shift
    gv = None
    if kind == "bg" and roof == "flat":
        px, py = fx + 0.18, fy + 0.18
        _box(trim, (0, py, roof_z + 0.3), (px, 0.09, 0.3))
        _box(trim, (0, -py, roof_z + 0.3), (px, 0.09, 0.3))
        _box(trim, (px, 0, roof_z + 0.3), (0.09, py, 0.3))
        _box(trim, (-px, 0, roof_z + 0.3), (0.09, py, 0.3))
        tx, ty = rng.uniform(-fx + 1.0, fx - 1.0), rng.uniform(-fy + 1.0, fy - 1.0)
        sx, sy = -0.55 * fx if tx > 0 else 0.55 * fx, -0.5 * fy if ty > 0 else 0.5 * fy
        if min(fx, fy) > 1.9:
            extra = (f"""
      <geom name="{prefix}_tank" type="cylinder" size="0.55 0.5" pos="{ox + tx:.2f} {oy + ty:.2f} {oz + roof_z + 0.5:.2f}" rgba="0.08 0.08 0.09 1" contype="0" conaffinity="0" mass="1"/>
      <geom name="{prefix}_stair" type="box" size="1.0 0.9 1.1" pos="{ox + sx:.2f} {oy + sy:.2f} {oz + roof_z + 1.1:.2f}" rgba="{wall}" contype="0" conaffinity="0" mass="1"/>""")
    elif kind == "bg" and roof == "gable":
        th = math.radians(24)
        top = half_h + ROOF_SLAB
        tinc = TIN_COLORS[tin % len(TIN_COLORS)]
        gv, gf = [], []
        if fx >= fy:      # ridge along x, slopes fall toward ±y
            span = fy + 0.45
            Lh = span / math.cos(th) / 2
            zc_ = top + span / 2 * math.tan(th)
            for sgn in (1, -1):
                extra += (f"""
      <geom name="{prefix}_roof{'p' if sgn > 0 else 'n'}" type="box" size="{fx + 0.45:.2f} {Lh:.3f} 0.04" pos="{ox:.2f} {oy + sgn * span / 2:.3f} {oz + zc_:.3f}" euler="{-sgn * th:.4f} 0 0" material="tin_c{tin % len(TIN_COLORS)}" contype="0" conaffinity="0" mass="1"/>""")
            ridge = top + fy * math.tan(th)
            for e in (-1, 1):
                tri = [(e * fx + ox, -e * fy + oy, top + oz), (e * fx + ox, e * fy + oy, top + oz), (e * fx + ox, oy, ridge + oz)]
                gv.append((tri, (e, 0, 0)))
        else:             # ridge along y, slopes fall toward ±x
            span = fx + 0.45
            Lh = span / math.cos(th) / 2
            zc_ = top + span / 2 * math.tan(th)
            for sgn in (1, -1):
                extra += (f"""
      <geom name="{prefix}_roof{'p' if sgn > 0 else 'n'}" type="box" size="{Lh:.3f} {fy + 0.45:.2f} 0.04" pos="{ox + sgn * span / 2:.3f} {oy:.2f} {oz + zc_:.3f}" euler="0 {sgn * th:.4f} 0" material="tin_r{tin % len(TIN_COLORS)}" contype="0" conaffinity="0" mass="1"/>""")
            ridge = top + fx * math.tan(th)
            for e in (-1, 1):
                tri = [(e * fx + ox, e * fy + oy, top + oz), (-e * fx + ox, e * fy + oy, top + oz), (ox, e * fy + oy, ridge + oz)]
                gv.append((tri, (0, e, 0)))
        _GABLE_MESHES[prefix] = gv

    for mesh in (glass, trim, metal, stain, door):
        vs = mesh[0]
        for k, v in enumerate(vs):
            vs[k] = (v[0] + shift[0], v[1] + shift[1], v[2] + shift[2])
    _BUILDING_MESHES[prefix] = {"win": glass, "trim": trim, "metal": metal, "stain": stain, "door": door}
    out = [_wall_shell(prefix, fx, fy, half_h, shift, wall, gable=_GABLE_MESHES.get(prefix) if roof == "gable" and kind == "bg" else None)]
    for part, mat in (("win", "glass"), ("trim", "trim"), ("metal", "metal"), ("stain", "stain"), ("door", "doorway")):
        if len(_BUILDING_MESHES[prefix][part][0]) >= 4:
            out.append(f'<geom name="{prefix}_{part}" type="mesh" mesh="{prefix}_{part}" material="{mat}" contype="0" conaffinity="0" mass="1"/>')
    return "\n      ".join(out) + extra


def building_assets_xml() -> str:
    out = ['<texture name="plaster_tex" type="2d" file="assets/buildings/plaster.png"/>',
           '<texture name="concrete_tex" type="2d" file="assets/buildings/concrete.png"/>',
           '<texture name="tin_cols_tex" type="2d" file="assets/buildings/tin_cols.png"/>',
           '<texture name="tin_rows_tex" type="2d" file="assets/buildings/tin_rows.png"/>',
           '<material name="glass" rgba="' + GLASS_RGBA + '" specular="0.75" shininess="0.9" reflectance="0"/>',
           '<material name="trim" rgba="' + TRIM_RGBA + '" specular="0.05"/>',
           '<material name="metal" rgba="' + METAL_RGBA + '" specular="0.35" shininess="0.5"/>',
           '<material name="stain" rgba="' + STAIN_RGBA + '" specular="0"/>',
           '<material name="doorway" rgba="0.06 0.05 0.045 1" specular="0"/>',
           '<material name="roof_concrete" texture="concrete_tex" texuniform="true" texrepeat="0.5 0.5" rgba="0.78 0.77 0.74 1" specular="0.05"/>']
    for i, c in enumerate(WALL_COLORS):
        out.append(f'<material name="wall_{i}" texture="plaster_tex" texuniform="true" texrepeat="0.67 0.67" rgba="{c}" specular="0.04"/>')
    for i, c in enumerate(TIN_COLORS):
        out.append(f'<material name="tin_c{i}" texture="tin_cols_tex" texuniform="true" texrepeat="0.67 0.67" rgba="{c}" specular="0.3" shininess="0.4"/>')
        out.append(f'<material name="tin_r{i}" texture="tin_rows_tex" texuniform="true" texrepeat="0.67 0.67" rgba="{c}" specular="0.3" shininess="0.4"/>')
    for prefix, parts in _BUILDING_MESHES.items():
        for part, mesh in parts.items():
            if len(mesh[0]) >= 4:
                out.append(f'<mesh name="{prefix}_{part}" file="assets/buildings/{prefix}_{part}.obj" inertia="shell"/>')
    for i, c in enumerate(WALL_COLORS):
        out.append(f'<material name="wallm_{i}" texture="plaster_tex" texrepeat="1 1" rgba="{c}" specular="0.04"/>')
    for prefix in _WALL_MESHES:
        out.append(f'<mesh name="{prefix}_walls" file="assets/buildings/{prefix}_walls.obj" inertia="shell"/>')
    return "\n    ".join(out)


def write_building_meshes(assets_dir: str) -> None:
    d = os.path.join(assets_dir, "buildings")
    os.makedirs(d, exist_ok=True)
    for prefix, parts in _BUILDING_MESHES.items():
        for part, mesh in parts.items():
            if len(mesh[0]) >= 4:
                _write_obj_n(os.path.join(d, f"{prefix}_{part}.obj"), mesh)
    for prefix, (V, T, N, F, _) in _WALL_MESHES.items():
        _write_obj_uv(os.path.join(d, f"{prefix}_walls.obj"), V, T, N, F)


def _survivor_mjcf(house_id: str, idx: int, local_x: float, local_y: float, roof_local_z: float) -> str:
    """Simplified standing human (capsules + sphere head), arms raised —
    a lightweight stand-in, NOT the full MS-Human-700 model."""
    shirt = SURVIVOR_SHIRT_COLORS[idx % len(SURVIVOR_SHIRT_COLORS)]
    leg_h, torso_h, head_r = 0.42, 0.32, 0.11
    z0 = roof_local_z
    return f"""
      <body name="{house_id}_survivor{idx+1}" pos="{local_x:.2f} {local_y:.2f} {z0:.3f}">
        <geom name="{house_id}_survivor{idx+1}_legs" type="capsule" fromto="0 0 {leg_h} 0 0 0.03" size="0.07" rgba="0.15 0.15 0.2 1"/>
        <geom name="{house_id}_survivor{idx+1}_torso" type="capsule" fromto="0 0 {leg_h + 2*torso_h} 0 0 {leg_h}" size="0.11" rgba="{shirt}"/>
        <geom name="{house_id}_survivor{idx+1}_head" type="sphere" pos="0 0 {leg_h + 2*torso_h + head_r + 0.02}" size="{head_r}" rgba="{SKIN_RGBA}"/>
        <geom name="{house_id}_survivor{idx+1}_arm_l" type="capsule" fromto="0.11 0 {leg_h + 2*torso_h - 0.05} 0.32 0 {leg_h + 2*torso_h + 0.25}" size="0.045" rgba="{shirt}"/>
        <geom name="{house_id}_survivor{idx+1}_arm_r" type="capsule" fromto="-0.11 0 {leg_h + 2*torso_h - 0.05} -0.32 0 {leg_h + 2*torso_h + 0.25}" size="0.045" rgba="{shirt}"/>
      </body>"""


def _house_mjcf(h: House) -> str:
    roof_top = h.height + ROOF_SLAB
    arc_r = min(h.footprint - 0.6, 2.6)
    survivors = "".join(
        _survivor_mjcf(h.house_id, i, arc_r * math.cos(2 * math.pi * i / max(h.survivor_count, 1) + math.pi / 4),
                       arc_r * math.sin(2 * math.pi * i / max(h.survivor_count, 1) + math.pi / 4), roof_top + 0.01)
        for i in range(h.survivor_count))
    if h.survivor_count > 0:
        outer, bull = HOUSE_DROP_ZONE_OUTER_RGBA, HOUSE_DROP_ZONE_BULLSEYE_RGBA
    else:
        outer, bull = "0.55 0.55 0.52 1", "0.4 0.4 0.38 1"
    return f"""
    <body name="{h.house_id}" pos="{h.x} {h.y} {h.height}">
      <geom name="{h.house_id}_block" type="box" size="{h.footprint - 0.015:.3f} {h.footprint - 0.015:.3f} {h.height}" material="{wall_mat(h.wall)}"/>
      {_facade_detail(h.house_id, h.footprint, h.footprint, h.height, 'mission', h.wall)}
      <geom name="{h.house_id}_roof" type="box" size="{h.footprint + 0.2:.2f} {h.footprint + 0.2:.2f} {ROOF_SLAB / 2}" pos="0 0 {h.height + ROOF_SLAB / 2:.3f}" material="roof_concrete"/>
      <geom name="{h.house_id}_drop_outer" type="cylinder" size="{min(2.0, h.footprint - 0.5)} 0.02" pos="0 0 {roof_top + 0.02:.3f}" rgba="{outer}"/>
      <site name="{h.house_id}_target_center" pos="0 0 {roof_top + 0.04:.3f}"/>
      <!-- survivor_count={h.survivor_count} (ground truth; Layer B must recover it via the person detector) -->
{survivors}
    </body>"""


def _background_house_mjcf(idx: int, b: BackgroundHouse) -> str:
    """Scenery building made of one or more boxes (block / tower / stepped /
    L-shape / two-height row / low shed), each with its own windows, floor
    bands, balcony, parapet and flat roof; rooftop tank + stair cabin on top."""
    parts_xml = []
    rb = random.Random(idx * 131 + 7)
    roof = "gable" if rb.random() < 0.55 else "flat"       # pitched tin roofs like the hill-town reference
    tin = rb.randrange(len(TIN_COLORS))
    top_i = max(range(len(b.parts)), key=lambda i: b.parts[i][4] + 2 * b.parts[i][5])
    for i, (ox, oy, fx, fy, bz, hh) in enumerate(b.parts):
        cz = bz + hh
        pre = f"bg_house_{idx}_p{i}"
        kind = "bg" if (i == top_i or b.shape in ("row", "L")) else "bg_lower"
        parts_xml.append(f'''
      <geom name="{pre}_block" type="box" size="{fx - 0.015:.3f} {fy - 0.015:.3f} {hh:.2f}" pos="{ox:.2f} {oy:.2f} {cz:.2f}" material="{wall_mat(b.wall)}"/>
      {_facade_detail(pre, fx, fy, hh, kind, b.wall, shift=(ox, oy, cz), on_ground=(bz == 0), roof=roof, tin=tin)}
      <geom name="{pre}_roof" type="box" size="{fx + 0.25:.2f} {fy + 0.25:.2f} {ROOF_SLAB / 2}" pos="{ox:.2f} {oy:.2f} {cz + hh + ROOF_SLAB / 2:.3f}" material="roof_concrete"/>''')
    return f"""
    <body name="bg_house_{idx}" pos="{b.x} {b.y} 0">{"".join(parts_xml)}
    </body>"""


# Tree models: Himalayan mountain species, built procedurally as meshes
# (assets/trees/*.obj) branch by branch:
#   deodar  — Cedrus deodara: broad cone of flat, drooping branch tiers, blue-green
#   fir     — Abies pindrow / Himalayan spruce: tall narrow dark spire
#   chir    — Pinus roxburghii (chir pine): tall bare trunk, open crown of
#             light yellow-green needle tufts
#   oak     — Quercus leucotrichophora (banj oak): rounded grey-green crown
# Each tree = trunk/branch mesh + two foliage meshes (shade and lit tones).
# Species are placed by altitude like on real Himalayan slopes: oak and
# chir pine low down, deodar mid-slope, fir/spruce near the ridges.
TREE_SPECIES = {
    "deodar": dict(variants=[(13.0, 4.2), (16.0, 5.0)], leaf=("0.10 0.22 0.19 1", "0.17 0.31 0.25 1")),
    "fir":    dict(variants=[(14.0, 2.4), (17.0, 2.8)], leaf=("0.06 0.15 0.10 1", "0.11 0.23 0.15 1")),
    "chir":   dict(variants=[(14.0, 2.6), (17.0, 3.0)], leaf=("0.26 0.36 0.13 1", "0.36 0.46 0.18 1")),
    "oak":    dict(variants=[(8.5, 3.4), (10.0, 4.0)], leaf=("0.21 0.29 0.16 1", "0.31 0.38 0.22 1")),
}


def _write_obj(path, verts, faces):
    with open(path, "w") as f:
        for v in verts:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for a, b, c in faces:
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")


def _icosphere(subdiv=1):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(subdiv):
        cache, nf = {}, []
        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = (v[a] + v[b]) / 2
                v.append(m / np.linalg.norm(m)); cache[key] = len(v) - 1
            return cache[key]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return v, f


_ICO1 = _icosphere(1)
_ICO0 = _icosphere(0)


class _Mesh:
    def __init__(self):
        self.v, self.f = [], []

    def blob(self, center, axes, yaw, pitch, rng, jitter=0.18, lowpoly=False):
        """Lumpy ellipsoid foliage clump: semi-axes (a along branch, b across, c up),
        rotated by yaw (about z) then pitched down along the branch."""
        bv, bf = _ICO0 if lowpoly else _ICO1
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        o = len(self.v)
        for p in bv:
            k = 1 + rng.uniform(-jitter, jitter)
            x, y, z = p[0] * axes[0] * k, p[1] * axes[1] * k, p[2] * axes[2] * k
            x, z = x * cp - z * sp, x * sp + z * cp          # pitch about local y
            x, y = x * cy - y * sy, x * sy + y * cy          # yaw about z
            self.v.append((center[0] + x, center[1] + y, center[2] + z))
        self.f += [(o + a, o + b, o + c) for a, b, c in bf]

    def limb(self, p0, p1, r0, r1, segs=6):
        """Tapered cylinder from p0 to p1 (trunk or branch)."""
        p0, p1 = np.array(p0, float), np.array(p1, float)
        ax = p1 - p0; L = np.linalg.norm(ax); ax /= L
        tmp = np.array([1.0, 0, 0]) if abs(ax[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(ax, tmp); u /= np.linalg.norm(u); w = np.cross(ax, u)
        o = len(self.v)
        for c, r in ((p0, r0), (p1, r1)):
            for j in range(segs):
                a = 2 * math.pi * j / segs
                q = c + r * (math.cos(a) * u + math.sin(a) * w)
                self.v.append(tuple(q))
        for j in range(segs):
            b0, b1, t0, t1 = o + j, o + (j + 1) % segs, o + segs + j, o + segs + (j + 1) % segs
            self.f += [(b0, b1, t1), (b0, t1, t0)]

    def save(self, path):
        _write_obj(path, self.v, self.f)


def _build_tree(species, H, R, rng):
    wood, dark, lit = _Mesh(), _Mesh(), _Mesh()
    pick = lambda: lit if rng.random() < 0.38 else dark
    if species in ("deodar", "fir"):
        narrow = species == "fir"
        wood.limb((0, 0, 0), (0, 0, H * 0.93), 0.16 + 0.018 * H, 0.05)
        tiers = 13 if narrow else 10
        for k in range(tiers):
            f = k / (tiers - 1)
            z = H * ((0.14 if narrow else 0.20) + (0.80 if narrow else 0.72) * f)
            rk = R * (1 - 0.88 * f) ** (1.0 if narrow else 0.85)
            nb = rng.randint(6, 8) if not narrow else rng.randint(5, 7)
            for j in range(nb):
                a = 2 * math.pi * (j + rng.uniform(-0.3, 0.3)) / nb + k * 0.6
                L = rk * rng.uniform(0.8, 1.1)
                droop = math.radians(rng.uniform(8, 18) + (10 if narrow else 0))
                cx, cy = math.cos(a) * L * 0.5, math.sin(a) * L * 0.5
                th = (0.55 if not narrow else 0.65) * rng.uniform(0.85, 1.2)
                pick().blob((cx, cy, z - L * 0.5 * math.sin(droop)), (L * 0.55, max(0.5, L * 0.32), th), a, droop, rng)
                # drooping branch tip (characteristic of deodar)
                tx, ty = math.cos(a) * L * 0.95, math.sin(a) * L * 0.95
                pick().blob((tx, ty, z - L * math.sin(droop) - 0.25), (L * 0.18 + 0.2, 0.35, 0.3), a, droop + 0.5, rng, lowpoly=True)
        pick().blob((0, 0, H * 0.97), (0.35, 0.35, H * 0.07), 0, 0, rng)          # leader
    elif species == "chir":
        lean = rng.uniform(-0.04, 0.04)
        top = (H * lean, H * lean * 0.5, H * 0.92)
        wood.limb((0, 0, 0), top, 0.22 + 0.015 * H, 0.06)
        for j in range(rng.randint(6, 8)):
            zb = H * rng.uniform(0.58, 0.88)
            a = rng.uniform(0, 2 * math.pi)
            L = R * rng.uniform(0.5, 1.0)
            base = (top[0] * zb / top[2], top[1] * zb / top[2], zb)
            tip = (base[0] + math.cos(a) * L, base[1] + math.sin(a) * L, zb + rng.uniform(0.3, 1.2))
            wood.limb(base, tip, 0.08, 0.03, segs=5)
            pick().blob(tip, (rng.uniform(0.9, 1.4), rng.uniform(0.8, 1.2), rng.uniform(0.55, 0.8)), a, 0, rng, jitter=0.28)
        pick().blob((top[0], top[1], top[2] + 0.4), (1.2, 1.1, 0.9), 0, 0, rng, jitter=0.28)
    else:  # oak
        wood.limb((0, 0, 0), (0, 0, H * 0.55), 0.22 + 0.02 * H, 0.12)
        cz = H * 0.66
        for j in range(10):
            if j == 0:
                c, r = (0, 0, cz + 0.4), R * 0.62
            else:
                a = rng.uniform(0, 2 * math.pi); d = R * rng.uniform(0.3, 0.6)
                c, r = (math.cos(a) * d, math.sin(a) * d, cz + rng.uniform(-0.25, 0.35) * R), R * rng.uniform(0.38, 0.52)
            pick().blob(c, (r, r, r * 0.82), rng.uniform(0, 6.28), 0, rng, jitter=0.2)
    return wood, dark, lit


def tree_kinds() -> list:
    return [f"{sp}{i}" for sp, d in TREE_SPECIES.items() for i in range(len(d["variants"]))]


def write_tree_meshes(assets_dir: str, seed: int = 5) -> None:
    d = os.path.join(assets_dir, "trees")
    os.makedirs(d, exist_ok=True)
    rng = random.Random(seed)
    for sp, info in TREE_SPECIES.items():
        for i, (H, R) in enumerate(info["variants"]):
            wood, dark, lit = _build_tree(sp, H, R, rng)
            wood.save(os.path.join(d, f"{sp}{i}_wood.obj"))
            dark.save(os.path.join(d, f"{sp}{i}_dark.obj"))
            lit.save(os.path.join(d, f"{sp}{i}_lit.obj"))


def tree_assets_xml() -> str:
    out = []
    for nm in tree_kinds():
        for part in ("wood", "dark", "lit"):
            out.append(f'<mesh name="{nm}_{part}" file="assets/trees/{nm}_{part}.obj" inertia="shell"/>')
    for sp, info in TREE_SPECIES.items():
        out.append(f'<material name="{sp}_dark" rgba="{info["leaf"][0]}" specular="0.04" shininess="0.1"/>')
        out.append(f'<material name="{sp}_lit" rgba="{info["leaf"][1]}" specular="0.04" shininess="0.1"/>')
    out.append('<material name="bark" rgba="0.30 0.23 0.17 1" specular="0.02"/>')
    return "\n    ".join(out)


def _tree_mjcf(idx: int, t: Tree) -> str:
    sp = t.kind.rstrip("0123456789")
    qw, qz = math.cos(t.yaw / 2), math.sin(t.yaw / 2)
    return f"""
    <body name="tree_{idx}" pos="{t.x} {t.y} {t.z}" quat="{qw:.4f} 0 0 {qz:.4f}">
      <geom name="tree_{idx}_wood" type="mesh" mesh="{t.kind}_wood" material="bark" contype="0" conaffinity="0" mass="1"/>
      <geom name="tree_{idx}_dark" type="mesh" mesh="{t.kind}_dark" material="{sp}_dark" contype="0" conaffinity="0" mass="1"/>
      <geom name="tree_{idx}_lit" type="mesh" mesh="{t.kind}_lit" material="{sp}_lit" contype="0" conaffinity="0" mass="1"/>
    </body>"""


def _warehouse_mjcf(w: Warehouse) -> str:
    roof_top = w.height + ROOF_SLAB
    return f"""
    <geom name="warehouse_hardstand" type="box" size="{w.footprint + 3.5} {w.footprint + 3.5} 0.3" pos="{w.x} {w.y} {w.z + 0.05:.3f}" rgba="0.56 0.55 0.52 1"/>
    <body name="warehouse" pos="{w.x} {w.y} {w.z + w.height:.3f}">
      <geom name="warehouse_block" type="box" size="{w.footprint - 0.015:.3f} {w.footprint - 0.015:.3f} {w.height}" material="wall_7"/>
      {_facade_detail("warehouse", w.footprint, w.footprint, w.height, "warehouse", "0.62 0.58 0.52 1", on_ground=False)}
      <geom name="warehouse_roof" type="box" size="{w.footprint + 0.2} {w.footprint + 0.2} {ROOF_SLAB / 2}" pos="0 0 {w.height + ROOF_SLAB / 2:.3f}" material="roof_concrete"/>
      <geom name="warehouse_pad_outer" type="cylinder" size="{min(3.0, w.footprint - 0.5)} 0.02" pos="0 0 {roof_top + 0.02:.3f}" rgba="{WAREHOUSE_PAD_OUTER_RGBA}"/>
      <geom name="warehouse_pad_bullseye" type="cylinder" size="{min(0.9, w.footprint - 1.5)} 0.025" pos="0 0 {roof_top + 0.025:.3f}" rgba="{WAREHOUSE_PAD_BULLSEYE_RGBA}"/>
      <site name="warehouse_pickup_center" pos="0 0 {roof_top + 0.04:.3f}"/>
      <!-- payloads_available={w.payloads_available} -->
    </body>"""


def _warehouse_payload_rack_mjcf(w: Warehouse, n_visible: int = 6) -> str:
    bodies = []
    cols, spacing = 3, 0.5
    start_x = w.x - (cols - 1) * spacing / 2.0
    for idx in range(min(n_visible, 12)):
        row, col = divmod(idx, cols)
        bodies.append(f"""
    <body name="warehouse_payload_{idx + 1}" pos="{start_x + col * spacing:.2f} {w.y - w.footprint + 1.5 + row * spacing:.2f} {w.z + w.height * 2 + ROOF_SLAB + 0.2:.2f}">
      <freejoint name="warehouse_payload_{idx + 1}_free"/>
      <geom name="warehouse_payload_{idx + 1}_geom" type="cylinder" size="0.14 0.18" rgba="0.9 0.15 0.15 1" mass="1.5"/>
    </body>""")
    return "".join(bodies)


def _baseline_uav_mjcf(hover_x: float, hover_y: float, hover_z: float, S: float = UAV_SCALE, dynamic: bool = False) -> str:
    """The official single-slot winch+pendulum UAV, drawn at small-helicopter
    size (airframe scaled by S; ~5.3 m rotor-tip span next to 1.7 m survivors).
    Official masses are kept on the official parts; the added rotor discs,
    motor pods and skids are visual-only (tiny mass, no collision). Arms are
    laid out horizontally with fromto — the official file's arm capsules
    point straight up (capsules run along z; its quats only spin them about z).
    gravcomp="1" holds the airframe in place for the visual — NOT a flight controller."""
    tip = 0.531 * S / math.sqrt(2)          # arm tip x/y offset
    arm_r = 0.018 * S
    arms = []
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1)), start=1):
        x, y = sx * tip, sy * tip
        arms.append(f'''
      <geom name="arm{k}" type="capsule" fromto="0 0 0 {x:.3f} {y:.3f} 0" size="{arm_r:.3f}" rgba="0.1 0.1 0.1 1" mass="0.25"/>
      <geom name="motor{k}" type="cylinder" size="{0.03 * S:.3f} {0.035 * S:.3f}" pos="{x:.3f} {y:.3f} {0.03 * S:.3f}" rgba="0.15 0.15 0.17 1" mass="0.001" contype="0" conaffinity="0"/>
      <geom name="rotor{k}" type="cylinder" size="{0.23 * S:.3f} 0.012" pos="{x:.3f} {y:.3f} {0.075 * S:.3f}" rgba="0.08 0.08 0.08 0.25" mass="0.001" contype="0" conaffinity="0"/>
      <body name="prop{k}" pos="{x:.3f} {y:.3f} {0.085 * S:.3f}">
        <joint name="uav_prop{k}" type="hinge" axis="0 0 1" damping="0"/>
        <geom name="prop{k}_blade" type="box" size="{0.22 * S:.3f} {0.014 * S:.3f} 0.01" rgba="0.08 0.08 0.08 1" mass="0.001" contype="0" conaffinity="0"/>
      </body>''')
    arms_xml = "".join(arms)
    skid_z, skid_y = -0.17 * S, 0.14 * S
    return f"""
    <body name="uav_chassis" {'' if dynamic else 'mocap="true" '}pos="{hover_x} {hover_y} {hover_z}">{'<freejoint name="uav_root_joint"/>' if dynamic else ''}
      <geom name="fuselage" type="cylinder" size="{0.18 * S:.3f} {0.06 * S:.3f}" rgba="0.2 0.25 0.3 1" mass="2.2"/>
      <geom name="canopy" type="ellipsoid" size="{0.16 * S:.3f} {0.12 * S:.3f} {0.07 * S:.3f}" pos="0 0 {0.05 * S:.3f}" rgba="0.85 0.86 0.88 1" mass="0.001" contype="0" conaffinity="0"/>
      <geom name="beacon" type="sphere" size="{0.015 * S:.3f}" pos="0 0 {0.12 * S:.3f}" rgba="1 0.25 0.1 1" mass="0.001" contype="0" conaffinity="0"/>
      <geom name="gimbal_cam" type="sphere" size="{0.035 * S:.3f}" pos="{0.13 * S:.3f} 0 {-0.07 * S:.3f}" rgba="0.08 0.08 0.1 1" mass="0.001" contype="0" conaffinity="0"/>
{arms_xml}
      <geom name="skid_l" type="capsule" fromto="{-0.2 * S:.3f} {skid_y:.3f} {skid_z:.3f} {0.2 * S:.3f} {skid_y:.3f} {skid_z:.3f}" size="{0.012 * S:.3f}" rgba="0.12 0.12 0.12 1" mass="0.001" contype="0" conaffinity="0"/>
      <geom name="skid_r" type="capsule" fromto="{-0.2 * S:.3f} {-skid_y:.3f} {skid_z:.3f} {0.2 * S:.3f} {-skid_y:.3f} {skid_z:.3f}" size="{0.012 * S:.3f}" rgba="0.12 0.12 0.12 1" mass="0.001" contype="0" conaffinity="0"/>
      <geom name="strut_l" type="capsule" fromto="0 {0.08 * S:.3f} {-0.05 * S:.3f} 0 {skid_y:.3f} {skid_z:.3f}" size="{0.01 * S:.3f}" rgba="0.12 0.12 0.12 1" mass="0.001" contype="0" conaffinity="0"/>
      <geom name="strut_r" type="capsule" fromto="0 {-0.08 * S:.3f} {-0.05 * S:.3f} 0 {-skid_y:.3f} {skid_z:.3f}" size="{0.01 * S:.3f}" rgba="0.12 0.12 0.12 1" mass="0.001" contype="0" conaffinity="0"/>
      <site name="downward_cam_site" pos="0 0 {-0.06 * S:.3f}" quat="0.7071 0.7071 0 0"/>
      <site name="winch_anchor" pos="0 0 {-0.08 * S:.3f}"/>
      <site name="thrust_center" pos="0 0 0"/>
      <body name="winch_cable" pos="0 0 {-0.15 * S:.3f}">
        <joint name="cable_pitch" type="hinge" axis="0 1 0" range="-1.2 1.2"/>
        <joint name="cable_roll" type="hinge" axis="1 0 0" range="-1.2 1.2"/>
        <geom name="cable_geom" type="capsule" size="0.03 1.8" pos="0 0 -1.8" rgba="0.7 0.7 0.7 0.9" mass="0.15"/>
        <body name="relief_payload" pos="0 0 -3.6">
          <geom name="payload_box" type="cylinder" size="0.31 0.4" rgba="0.9 0.15 0.15 1" mass="1.5"/>
          <geom name="cross_h" type="box" size="0.2 0.055 0.044" pos="0 0.312 0" rgba="1 1 1 1" mass="0.01"/>
          <geom name="cross_v" type="box" size="0.055 0.2 0.044" pos="0 0.312 0" rgba="1 1 1 1" mass="0.01"/>
          <site name="payload_sensor" pos="0 0 0"/>
        </body>
      </body>
    </body>
    <!-- gimbal-stabilised survey camera: follows the drone but stays level,
         so the scan beam always points straight down at the roofs -->
    <body name="scan_gimbal" mocap="true" pos="{hover_x} {hover_y} {hover_z}">
      <geom name="scan_beam" type="mesh" mesh="scan_beam" material="beam_mat" group="4" contype="0" conaffinity="0" mass="0.001"/>
      <geom name="scan_lens" type="sphere" size="{0.03 * S:.3f}" pos="0 0 {-0.12 * S:.3f}" material="beam_lens" contype="0" conaffinity="0" mass="0.001"/>
    </body>"""


def _person_mjcf(name: str, x: float, y: float, z: float, pose: str, shirt: str, yaw: float = 0.0, blanket: bool = False) -> str:
    """Simple human figure (capsules + sphere head): standing, sitting or waving."""
    qw, qz = math.cos(yaw / 2), math.sin(yaw / 2)
    g = []
    if pose == "sit":
        g.append(f'<geom type="capsule" fromto="0 -0.1 0.12 0.42 -0.1 0.12" size="0.07" rgba="0.18 0.18 0.22 1"/>')
        g.append(f'<geom type="capsule" fromto="0 0.1 0.12 0.42 0.1 0.12" size="0.07" rgba="0.18 0.18 0.22 1"/>')
        tb, tt = 0.15, 0.72
    else:
        g.append(f'<geom type="capsule" fromto="0 -0.08 0.03 0 -0.08 0.45" size="0.07" rgba="0.18 0.18 0.22 1"/>')
        g.append(f'<geom type="capsule" fromto="0 0.08 0.03 0 0.08 0.45" size="0.07" rgba="0.18 0.18 0.22 1"/>')
        tb, tt = 0.47, 1.05
    g.append(f'<geom type="capsule" fromto="0 0 {tb} 0 0 {tt}" size="0.13" rgba="{shirt}"/>')
    g.append(f'<geom type="sphere" pos="0 0 {tt + 0.17}" size="0.11" rgba="{SKIN_RGBA}"/>')
    if pose == "wave":
        g.append(f'<geom type="capsule" fromto="0 0.14 {tt - 0.05} 0.05 0.33 {tt + 0.4}" size="0.045" rgba="{shirt}"/>')
        g.append(f'<geom type="capsule" fromto="0 -0.14 {tt - 0.05} 0 -0.18 {tt - 0.45}" size="0.045" rgba="{shirt}"/>')
    else:
        g.append(f'<geom type="capsule" fromto="0 0.15 {tt - 0.05} 0.02 0.18 {tt - 0.48}" size="0.045" rgba="{shirt}"/>')
        g.append(f'<geom type="capsule" fromto="0 -0.15 {tt - 0.05} 0.02 -0.18 {tt - 0.48}" size="0.045" rgba="{shirt}"/>')
    if blanket:   # orange thermal rescue blanket over the shoulders
        g.append(f'<geom type="box" pos="-0.02 0 {tt - 0.15}" size="0.17 0.22 0.25" rgba="0.92 0.55 0.12 1"/>')
    body = "\n        ".join(x_.replace("<geom ", '<geom contype="0" conaffinity="0" mass="0.01" ') for x_ in g)
    return f"""
    <body name="{name}" pos="{x:.2f} {y:.2f} {z:.2f}" quat="{qw:.4f} 0 0 {qz:.4f}">
        {body}
    </body>"""


def _rescue_camp_mjcf(w: Warehouse) -> str:
    """Rescued civilians gathered at the hilltop storage base (some wrapped
    in thermal blankets, some sitting, a medic in white), a blue relief tent
    and supply crates — so the base reads as the evacuation point."""
    rng = random.Random(4242)
    gz = w.z + 0.36
    out = []
    # relief tent on the valley side of the hardstand
    tx, ty = w.x - 7.9, w.y + 2.5
    out.append(f"""
    <body name="relief_tent" pos="{tx:.2f} {ty:.2f} {gz:.2f}">
      <geom type="box" size="1.2 2.0 0.05" pos="0 0 0.05" rgba="0.35 0.33 0.3 1" contype="0" conaffinity="0"/>
      <geom type="box" size="0.05 2.1 0.95" pos="-0.62 0 1.0" euler="0 -0.55 0" rgba="0.15 0.38 0.72 1" contype="0" conaffinity="0"/>
      <geom type="box" size="0.05 2.1 0.95" pos="0.62 0 1.0" euler="0 0.55 0" rgba="0.15 0.38 0.72 1" contype="0" conaffinity="0"/>
    </body>""")
    for k in range(5):
        cx, cy = w.x - 7.6 + rng.uniform(-0.8, 0.8), w.y - 3.2 - k * 0.9
        out.append(f'\n    <geom name="crate_{k}" type="box" size="0.4 0.35 0.3" pos="{cx:.2f} {cy:.2f} {gz + 0.3:.2f}" rgba="0.55 0.45 0.3 1" contype="0" conaffinity="0"/>')
    shirts = SURVIVOR_SHIRT_COLORS + ["0.6 0.6 0.62 1", "0.35 0.3 0.25 1"]
    spots = []
    for k in range(9):                        # along the valley-facing (−x) side
        spots.append((w.x - 7.3 + rng.uniform(-1.1, 1.1), w.y - 8.5 + k * 1.15 + rng.uniform(-0.3, 0.3)))
    for k in range(7):                        # along the south (−y) side
        spots.append((w.x - 4.5 + k * 1.3 + rng.uniform(-0.3, 0.3), w.y - 7.8 + rng.uniform(-1.0, 1.0)))
    for k, (px, py) in enumerate(spots):
        pose = rng.choices(["stand", "sit", "wave"], [0.5, 0.35, 0.15])[0]
        out.append(_person_mjcf(f"rescued_{k}", px, py, gz, pose, rng.choice(shirts),
                                yaw=rng.uniform(0, 6.28), blanket=rng.random() < 0.45))
    out.append(_person_mjcf("medic", w.x - 6.0, w.y - 6.4, gz, "stand", "0.95 0.95 0.95 1", yaw=2.4))
    return "".join(out)


def _helicopter_mjcf(x: float, y: float, z: float) -> str:
    """Rescue helicopter (~13 m long, 11.6 m main rotor): fuselage, glazed
    cockpit, tail boom, fin, stabiliser, skids. Main and tail rotors are
    child bodies on hinge joints that the renderer spins every physics step.
    Mocap body — flies a scripted circuit around the valley."""
    c = 'contype="0" conaffinity="0" mass="1"'
    return f"""
    <body name="helicopter" mocap="true" pos="{x:.2f} {y:.2f} {z:.2f}">
      <geom type="ellipsoid" size="2.4 1.15 1.2" pos="0 0 0" rgba="0.93 0.93 0.92 1" {c}/>
      <geom type="ellipsoid" size="1.3 1.17 0.5" pos="0.2 0 -0.5" rgba="0.95 0.45 0.10 1" {c}/>
      <geom type="ellipsoid" size="1.05 0.95 0.78" pos="1.65 0 0.22" rgba="0.12 0.16 0.2 1" {c}/>
      <geom type="box" size="1.1 0.6 0.35" pos="-0.4 0 1.25" rgba="0.82 0.82 0.82 1" {c}/>
      <geom type="capsule" fromto="-1.9 0 0.35 -7.3 0 0.8" size="0.32" rgba="0.93 0.93 0.92 1" {c}/>
      <geom type="box" size="0.55 0.07 0.85" pos="-7.25 0 1.45" euler="0 -0.35 0" rgba="0.95 0.45 0.10 1" {c}/>
      <geom type="box" size="0.35 1.15 0.05" pos="-6.4 0 0.75" rgba="0.93 0.93 0.92 1" {c}/>
      <geom type="capsule" fromto="-1.6 1.15 -1.6 1.9 1.15 -1.6" size="0.07" rgba="0.2 0.2 0.2 1" {c}/>
      <geom type="capsule" fromto="-1.6 -1.15 -1.6 1.9 -1.15 -1.6" size="0.07" rgba="0.2 0.2 0.2 1" {c}/>
      <geom type="capsule" fromto="0.9 1.15 -1.6 0.7 0.7 -0.9" size="0.06" rgba="0.2 0.2 0.2 1" {c}/>
      <geom type="capsule" fromto="0.9 -1.15 -1.6 0.7 -0.7 -0.9" size="0.06" rgba="0.2 0.2 0.2 1" {c}/>
      <geom type="capsule" fromto="-0.9 1.15 -1.6 -0.8 0.7 -0.9" size="0.06" rgba="0.2 0.2 0.2 1" {c}/>
      <geom type="capsule" fromto="-0.9 -1.15 -1.6 -0.8 -0.7 -0.9" size="0.06" rgba="0.2 0.2 0.2 1" {c}/>
      <geom type="cylinder" size="5.8 0.01" pos="0 0 1.95" rgba="0.15 0.15 0.15 0.13" {c}/>
      <body name="heli_rotor" pos="0 0 1.95">
        <joint name="heli_main_rotor" type="hinge" axis="0 0 1" damping="0" armature="0.1"/>
        <geom type="cylinder" size="0.3 0.18" rgba="0.3 0.3 0.3 1" {c}/>
        <geom type="box" size="5.8 0.22 0.03" pos="0 0 0.1" rgba="0.12 0.12 0.12 1" {c}/>
        <geom type="box" size="0.22 5.8 0.03" pos="0 0 0.1" rgba="0.12 0.12 0.12 1" {c}/>
      </body>
      <body name="heli_tail" pos="-7.35 0.4 1.0">
        <joint name="heli_tail_rotor" type="hinge" axis="0 1 0" damping="0" armature="0.01"/>
        <geom type="box" size="1.0 0.03 0.1" rgba="0.12 0.12 0.12 1" {c}/>
        <geom type="box" size="0.1 0.03 1.0" rgba="0.12 0.12 0.12 1" {c}/>
      </body>
    </body>"""


# Floating flood debris (mocap bodies moved along the computed flow field):
# (kind, weight). Geometry is centred on the water line so the lower part
# is hidden under the surface like something actually floating.
DEBRIS_KINDS = [("log", 9), ("tree", 4), ("barrel", 7), ("tank", 3), ("crate", 5), ("plank", 6),
                ("sheet", 5), ("mattress", 2), ("car", 2), ("branch", 6)]
N_DEBRIS = 48


def debris_items(seed: int = 1):
    rng = random.Random(seed * 977 + 5)
    kinds = [k for k, _ in DEBRIS_KINDS]
    w = [wt for _, wt in DEBRIS_KINDS]
    return [(i, rng.choices(kinds, w)[0], rng.random()) for i in range(N_DEBRIS)]


def _debris_mjcf(i: int, kind: str, u: float) -> str:
    c = 'contype="0" conaffinity="0" mass="1"'
    if kind == "log":
        L = 1.8 + 2.5 * u
        g = f'<geom type="capsule" size="{0.22 + 0.15 * u:.2f} {L:.2f}" euler="0 1.5708 0" rgba="0.36 0.27 0.19 1" {c}/>'
    elif kind == "branch":
        g = (f'<geom type="capsule" size="0.08 {1.0 + u:.2f}" euler="0 1.5708 0.3" rgba="0.33 0.25 0.17 1" {c}/>'
             f'<geom type="ellipsoid" size="0.7 0.5 0.18" pos="{0.8 + u:.2f} 0.2 0.05" rgba="0.24 0.34 0.15 1" {c}/>')
    elif kind == "tree":
        L = 3.0 + 2.0 * u
        g = (f'<geom type="capsule" size="0.25 {L:.2f}" euler="0 1.5708 0" rgba="0.34 0.26 0.18 1" {c}/>'
             f'<geom type="ellipsoid" size="1.6 1.3 0.5" pos="{L + 0.8:.2f} 0 0.15" rgba="0.17 0.31 0.14 1" {c}/>'
             f'<geom type="ellipsoid" size="1.1 0.9 0.4" pos="{L - 0.6:.2f} 0.8 0.1" rgba="0.21 0.36 0.16 1" {c}/>'
             f'<geom type="ellipsoid" size="0.9 0.8 0.35" pos="{L + 0.2:.2f} -0.9 0.1" rgba="0.19 0.33 0.15 1" {c}/>')
    elif kind == "barrel":
        col = ["0.15 0.35 0.75 1", "0.92 0.92 0.9 1", "0.95 0.55 0.1 1", "0.2 0.5 0.3 1"][int(u * 4) % 4]
        g = f'<geom type="cylinder" size="0.3 0.45" euler="1.5708 0 0" pos="0 0 0.1" rgba="{col}" {c}/>'
    elif kind == "tank":
        g = f'<geom type="cylinder" size="0.55 0.5" euler="1.5708 0 0" pos="0 0 0.15" rgba="0.08 0.08 0.09 1" {c}/>'
    elif kind == "crate":
        g = f'<geom type="box" size="0.4 0.35 0.3" pos="0 0 0.12" euler="0 0 {u:.2f}" rgba="0.55 0.43 0.28 1" {c}/>'
    elif kind == "plank":
        g = f'<geom type="box" size="{1.0 + u:.2f} 0.13 0.04" pos="0 0 0.03" rgba="0.6 0.48 0.33 1" {c}/>'
    elif kind == "sheet":
        col = TIN_COLORS[int(u * len(TIN_COLORS)) % len(TIN_COLORS)]
        g = f'<geom type="box" size="1.4 0.9 0.02" pos="0 0 0.03" euler="0.05 0.04 0" rgba="{col}" {c}/>'
    elif kind == "mattress":
        g = f'<geom type="box" size="0.95 0.7 0.1" pos="0 0 0.06" rgba="0.85 0.82 0.74 1" {c}/>'
    else:  # car, mostly submerged
        col = ["0.9 0.9 0.9 1", "0.55 0.56 0.6 1", "0.15 0.25 0.45 1", "0.7 0.12 0.1 1"][int(u * 4) % 4]
        g = (f'<geom type="box" size="2.1 0.9 0.45" pos="0 0 -0.15" rgba="{col}" {c}/>'
             f'<geom type="box" size="1.1 0.82 0.32" pos="-0.2 0 0.55" rgba="{col}" {c}/>'
             f'<geom type="box" size="1.0 0.84 0.22" pos="-0.2 0 0.6" rgba="0.12 0.15 0.18 1" {c}/>')
    return f"""
    <body name="debris_{i}" mocap="true" pos="0 {-200 - i:.1f} -50">
      {g}
    </body>"""


def helicopter_orbit():
    """Circuit flown by the helicopter: a circle over the valley, centred on
    the flooded towns (centre, radius m, altitude m, period s)."""
    cy = 8.0
    return (float(centerline(cy)) - 8.0, cy), 46.0, 50.0, 22.0


def flight_altitude(layout: SceneLayout) -> float:
    """Survey altitude: high enough that the drone AND its hanging payload
    (~4.5 m below it) clear every roof in town, including the towers."""
    tops = [2 * h.height + ROOF_SLAB for h in layout.houses] + [2 * b.height + ROOF_SLAB + 2.2 for b in layout.background_houses]
    return max(tops) + 8.0


def flight_waypoints(layout: SceneLayout) -> list:
    """Scan route: over each drop roof in turn (down-valley to up-valley)."""
    z = flight_altitude(layout)
    hs = sorted(layout.houses, key=lambda h: h.y)
    return [(h.x, h.y, z) for h in hs]


def write_scan_beam(path: str, length: float) -> None:
    """Translucent scan frustum under the drone's camera (like an aerial
    survey beam): small aperture at the gimbal, ~7 x 6 m footprint at the
    bottom. Drawn in geom group 4 only."""
    top_z, bx, by = -0.45, 3.6, 3.0
    v = [(-0.25, -0.25, top_z), (0.25, -0.25, top_z), (0.25, 0.25, top_z), (-0.25, 0.25, top_z),
         (-bx, -by, -length), (bx, -by, -length), (bx, by, -length), (-bx, by, -length)]
    f = [(0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7), (4, 5, 6), (4, 6, 7)]
    _write_obj(path, v, f)


def camera_params(layout: SceneLayout) -> dict:
    """Free-camera target: centre of the town, slightly toward the river."""
    ty = 2.0
    return dict(center=(float(centerline(ty)) - 4.0, ty, 2.0), extent=CAMERA_EXTENT,
                azimuth=CAMERA_AZIMUTH, elevation=CAMERA_ELEVATION, fovy=CAMERA_FOVY)


def _light_house_mjcf(h: House) -> str:
    """Training-scene mission house: plain box + flat roof + drop marker +
    survivors (no facade meshes — fast to load and simulate)."""
    roof_top = h.height + ROOF_SLAB
    arc_r = min(h.footprint - 0.6, 2.6)
    survivors = "".join(
        _survivor_mjcf(h.house_id, i, arc_r * math.cos(2 * math.pi * i / max(h.survivor_count, 1) + math.pi / 4),
                       arc_r * math.sin(2 * math.pi * i / max(h.survivor_count, 1) + math.pi / 4), roof_top + 0.01)
        for i in range(h.survivor_count))
    outer = HOUSE_DROP_ZONE_OUTER_RGBA if h.survivor_count > 0 else "0.55 0.55 0.52 1"
    return f"""
    <body name="{h.house_id}" pos="{h.x} {h.y} {h.height}">
      <geom name="{h.house_id}_block" type="box" size="{h.footprint} {h.footprint} {h.height}" rgba="{h.wall}"/>
      <geom name="{h.house_id}_roof" type="box" size="{h.footprint + 0.2:.2f} {h.footprint + 0.2:.2f} {ROOF_SLAB / 2}" pos="0 0 {h.height + ROOF_SLAB / 2:.3f}" rgba="0.6 0.6 0.58 1"/>
      <geom name="{h.house_id}_drop_outer" type="cylinder" size="{min(2.0, h.footprint - 0.5)} 0.02" pos="0 0 {roof_top + 0.02:.3f}" rgba="{outer}"/>
      <site name="{h.house_id}_target_center" pos="0 0 {roof_top + 0.04:.3f}"/>
{survivors}
    </body>"""


def _light_bg_mjcf(idx: int, b: BackgroundHouse) -> str:
    parts = "".join(
        f'''
      <geom name="bg_house_{idx}_p{i}" type="box" size="{fx:.2f} {fy:.2f} {hh:.2f}" pos="{ox:.2f} {oy:.2f} {bz + hh:.2f}" rgba="{b.wall}"/>'''
        for i, (ox, oy, fx, fy, bz, hh) in enumerate(b.parts))
    return f"""
    <body name="bg_house_{idx}" pos="{b.x} {b.y} 0">{parts}
    </body>"""


def _light_warehouse_mjcf(w: Warehouse) -> str:
    roof_top = w.height + ROOF_SLAB
    return f"""
    <geom name="warehouse_hardstand" type="box" size="{w.footprint + 3.5} {w.footprint + 3.5} 0.3" pos="{w.x} {w.y} {w.z + 0.05:.3f}" rgba="0.56 0.55 0.52 1"/>
    <body name="warehouse" pos="{w.x} {w.y} {w.z + w.height:.3f}">
      <geom name="warehouse_block" type="box" size="{w.footprint} {w.footprint} {w.height}" rgba="0.62 0.58 0.52 1"/>
      <geom name="warehouse_roof" type="box" size="{w.footprint + 0.2} {w.footprint + 0.2} {ROOF_SLAB / 2}" pos="0 0 {w.height + ROOF_SLAB / 2:.3f}" rgba="0.5 0.5 0.5 1"/>
      <geom name="warehouse_pad_outer" type="cylinder" size="{min(3.0, w.footprint - 0.5)} 0.02" pos="0 0 {roof_top + 0.02:.3f}" rgba="{WAREHOUSE_PAD_OUTER_RGBA}"/>
      <geom name="warehouse_pad_bullseye" type="cylinder" size="{min(0.9, w.footprint - 1.5)} 0.025" pos="0 0 {roof_top + 0.025:.3f}" rgba="{WAREHOUSE_PAD_BULLSEYE_RGBA}"/>
      <site name="warehouse_pickup_center" pos="0 0 {roof_top + 0.04:.3f}"/>
    </body>"""


def render_scene_xml(layout: SceneLayout, terrain: Terrain, mask_mode: bool = False,
                     drone: str = "mocap", light: bool = False) -> str:
    """drone: "mocap" (scripted, for the cinematic renderer) or "dynamic"
    (free-flying physics body driven by the rotor motors + flight
    controller — for simulate.py and RL).  light=True: fast training scene
    (plain boxes, no trees/grass/facade meshes, untextured ground)."""
    cam = camera_params(layout)
    cx, cy, cz = cam["center"]
    h1 = layout.houses[len(layout.houses) // 2]
    wp = flight_waypoints(layout)
    (hcx, hcy), hr, hz, _ = helicopter_orbit()
    heli_start = (hcx + hr, hcy, hz)
    if drone == "dynamic":
        w_ = layout.warehouse
        uav_body = _baseline_uav_mjcf(w_.x - 12.0, w_.y, w_.z + 2 * w_.height + 10.0, dynamic=True)
    else:
        uav_body = _baseline_uav_mjcf(wp[0][0], wp[0][1], wp[0][2])
    _BUILDING_MESHES.clear()
    _GABLE_MESHES.clear()
    _WALL_MESHES.clear()
    if light:
        house_bodies = "".join(_light_house_mjcf(h) for h in layout.houses)
        warehouse_body = _light_warehouse_mjcf(layout.warehouse)
        bg_bodies = "".join(_light_bg_mjcf(i, b) for i, b in enumerate(layout.background_houses))
        tree_bodies = ""
    else:
        house_bodies = "".join(_house_mjcf(h) for h in layout.houses)
        warehouse_body = _warehouse_mjcf(layout.warehouse)
        bg_bodies = "".join(_background_house_mjcf(i, b) for i, b in enumerate(layout.background_houses))
        tree_bodies = "".join(_tree_mjcf(i, t) for i, t in enumerate(layout.trees))
    summary = "\n".join(
        f"       {h.house_id}: pos=({h.x}, {h.y}), footprint={2*h.footprint:.1f}m sq, height={2*h.height:.1f}m, "
        f"survivors={h.survivor_count} [ground truth]" for h in layout.houses)

    if mask_mode:
        water_mat = '<material name="water_mat" rgba="1 0 1 1" emission="1" specular="0" shininess="0" reflectance="0"/>'
    else:
        water_mat = (f'<material name="water_mat" rgba="{WATER_RGBA}" specular="0.3" shininess="0.5" reflectance="0"/>')
        if not light and os.path.exists(os.path.join(ASSETS_DIR, "water_tex.png")):
            # animated flood water (environment/live_water.py): same look as the cinematic video;
            # simulate.py streams the animation into this texture while the sim runs
            water_mat = ('<texture name="water_tex" type="2d" file="assets/water_tex.png"/>\n    '
                         '<material name="water_mat" texture="water_tex" texrepeat="1 1" texuniform="false" '
                         'rgba="1 1 1 1" specular="0.45" shininess="0.75" reflectance="0"/>')

    zrange = terrain.zmax - terrain.zmin
    water_rise = float((terrain.water - WATER_Z).max())
    return f"""<mujoco model="skyhydro_flood_valley_scene">
  <compiler angle="radian" coordinate="local"/>
  <option gravity="0 0 -9.81" timestep="0.002" integrator="RK4"/>

  <!-- Framing for the default free camera (the one MuJoCo's `record` tool uses) -->
  <statistic center="{cx:.2f} {cy:.2f} {cz:.2f}" extent="{cam['extent']}"/>

  <visual>
    <!-- overcast monsoon light, like the reference footage -->
    <headlight ambient="0.38 0.38 0.40" diffuse="0.35 0.35 0.35" specular="0.08 0.08 0.08"/>
    <global offwidth="1280" offheight="960" azimuth="{cam['azimuth']}" elevation="{cam['elevation']}" fovy="{cam['fovy']}"/>
    <quality shadowsize="4096"/>
    <map znear="0.02" zfar="40" shadowclip="2.5"/>
  </visual>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.70 0.74 0.78" rgb2="0.88 0.89 0.89" width="256" height="256"/>
    <hfield name="terrain" file="assets/terrain.bin" size="{DOMAIN_HALF} {DOMAIN_HALF} {zrange:.3f} 1.0"/>
    {'<material name="terrain_mat" rgba="0.30 0.42 0.22 1" specular="0.05"/>' if light else '<texture name="terrain_tex" type="2d" file="assets/terrain_tex.png"/>'}
    {'' if light else '<material name="terrain_mat" texture="terrain_tex" texrepeat="1 1" texuniform="false" specular="0.05" shininess="0.05"/>'}
    <hfield name="water_surface" file="assets/water.bin" size="{DOMAIN_HALF} {DOMAIN_HALF} {water_rise:.3f} 0.05"/>
    {water_mat}
    <material name="water_mask_mat" rgba="1 0 1 1" emission="1" specular="0" shininess="0" reflectance="0"/>
    <mesh name="scan_beam" file="assets/scan_beam.obj" inertia="shell"/>
    <material name="beam_mat" rgba="0.30 0.64 1.0 0.34" emission="1" specular="0"/>
    <material name="beam_lens" rgba="0.5 0.8 1 1" emission="1"/>
    {'' if light else tree_assets_xml()}
    {'' if light else grass_assets_xml()}
    {'' if light else building_assets_xml()}
  </asset>

  <default>
    <joint damping="0.1" armature="0.005"/>
    <geom friction="0.7 0.01 0.001" solref="0.01 1" solimp="0.9 0.95 0.001"/>
    <motor ctrlrange="-40 40" ctrllimited="true"/>
  </default>

  <!-- ====================================================================
       Generated by extended/environment/scene_generator.py  seed={layout.seed}
       Mountain-valley flash-flood scene: {len(layout.houses)} mission houses,
       {len(layout.background_houses)} background buildings, {len(layout.trees)} trees.
{summary}
       warehouse: pos=({layout.warehouse.x}, {layout.warehouse.y}), payloads_available={layout.warehouse.payloads_available}
       ==================================================================== -->

  <worldbody>
    <light name="sun" directional="true" pos="0 0 1" dir="0.35 0.45 -0.82"
           diffuse="0.62 0.60 0.56" specular="0.25 0.25 0.25" ambient="0.08 0.08 0.09" castshadow="true"/>
    <light name="sky_fill" directional="true" pos="0 0 1" dir="-0.2 -0.3 -0.93"
           diffuse="0.22 0.24 0.27" specular="0 0 0" castshadow="false"/>
    <geom name="terrain" type="hfield" hfield="terrain" pos="0 0 {terrain.zmin:.3f}" material="terrain_mat" group="1"/>
{'' if light else grass_geoms_xml()}
    <geom name="flood_water" type="hfield" hfield="water_surface" pos="0 0 {WATER_Z}" material="water_mat" group="2" contype="0" conaffinity="0"/>
    <geom name="flood_water_mask" type="hfield" hfield="water_surface" pos="0 0 {WATER_Z}" material="water_mask_mat" group="3" contype="0" conaffinity="0"/>
{tree_bodies}
{bg_bodies}
{house_bodies}
{warehouse_body}
{_warehouse_payload_rack_mjcf(layout.warehouse)}
{uav_body}
{_rescue_camp_mjcf(layout.warehouse)}
{_helicopter_mjcf(*heli_start)}
{"" if light else "".join(_debris_mjcf(i, k, u) for i, k, u in debris_items(layout.seed))}
  </worldbody>

  <actuator>
    <!-- Fix vs. official models/skyhydro_flood_uav.xml: <motor body=...> is not
         valid MJCF (the real MuJoCo 3.3.0 compiler rejects it); site
         transmission on a "thrust_center" site gives the same pure-vertical
         thrust. -->
    <motor name="rotor1_thrust" site="thrust_center" gear="0 0 1 0 0 0" ctrlrange="0 35"/>
    <motor name="rotor2_thrust" site="thrust_center" gear="0 0 1 0 0 0" ctrlrange="0 35"/>
    <motor name="rotor3_thrust" site="thrust_center" gear="0 0 1 0 0 0" ctrlrange="0 35"/>
    <motor name="rotor4_thrust" site="thrust_center" gear="0 0 1 0 0 0" ctrlrange="0 35"/>
  </actuator>

  <sensor>
    <accelerometer name="uav_accel" site="downward_cam_site"/>
    <gyro name="uav_gyro" site="downward_cam_site"/>
  </sensor>
</mujoco>
"""


def write_manifest(layout: SceneLayout, terrain: Terrain, path: str) -> None:
    """Scene facts the RL environment needs (no need to import this module
    there): drop houses + survivors, warehouse pickup pad, every building as
    an axis-aligned box (for collision/clearance checks), terrain/water grids."""
    import json
    boxes = []
    for h in layout.houses:
        boxes.append([h.x, h.y, h.height + ROOF_SLAB / 2, h.footprint + 0.2, h.footprint + 0.2, h.height + ROOF_SLAB / 2])
    for b in layout.background_houses:
        for ox, oy, fx, fy, bz, hh in b.parts:
            boxes.append([b.x + ox, b.y + oy, bz + hh + 0.6, fx + 0.3, fy + 0.3, hh + 0.6])
    w = layout.warehouse
    boxes.append([w.x, w.y, w.z + w.height + ROOF_SLAB / 2, w.footprint + 0.2, w.footprint + 0.2, w.height + ROOF_SLAB / 2])
    man = {
        "domain_half": DOMAIN_HALF, "grid": GRID, "water_z": WATER_Z,
        "terrain_bin": "assets/terrain.bin", "terrain_zmin": terrain.zmin,
        "water_bin": "assets/water.bin",
        "houses": [{"id": h.house_id, "x": h.x, "y": h.y, "roof_z": 2 * h.height + ROOF_SLAB,
                    "footprint": h.footprint, "drop_radius": min(2.0, h.footprint - 0.5),
                    "survivors": h.survivor_count} for h in layout.houses],
        "warehouse": {"x": w.x, "y": w.y, "roof_z": w.z + 2 * w.height + ROOF_SLAB, "footprint": w.footprint,
                      "pad_radius": min(3.0, w.footprint - 0.5), "payloads": w.payloads_available},
        "boxes": boxes,
        "survey_altitude": flight_altitude(layout),
        "helicopter_orbit": dict(zip(("center", "radius", "altitude", "period"), helicopter_orbit())),
        "seed": layout.seed,
    }
    with open(path, "w") as f:
        json.dump(man, f, indent=1)


def generate_scene(n_houses: int = 5, seed: int = 0, output_path: str = "scene_flood.xml",
                   warehouse_end: str = "upstream", n_trees: int = 650,
                   mask_output: str | None = None, water_anim: bool = True, water_res: int = 1536) -> SceneLayout:
    terrain = build_terrain(seed)
    layout = generate_layout(n_houses=n_houses, seed=seed, warehouse_end=warehouse_end,
                             n_trees=n_trees, terrain=terrain)
    out_dir = os.path.dirname(os.path.abspath(output_path))
    assets = os.path.join(out_dir, "assets")
    os.makedirs(assets, exist_ok=True)
    write_hfield_bin(terrain, os.path.join(assets, "terrain.bin"))
    write_terrain_texture(terrain, os.path.join(assets, "terrain_tex.png"), seed)
    write_water_hfield_bin(terrain, os.path.join(assets, "water.bin"))
    write_tree_meshes(assets)
    write_grass(terrain, assets, seed, layout)
    with open(output_path, "w") as f:
        f.write(render_scene_xml(layout, terrain))
    write_building_meshes(assets)
    write_building_textures(assets)
    write_scan_beam(os.path.join(assets, "scan_beam.obj"), flight_altitude(layout) - WATER_Z - 0.2)
    # physics variants: full-detail scene with a free-flying drone (viewer / simulate.py)
    # and a lightweight scene for fast RL training
    with open(os.path.join(out_dir, "scene_flood_dynamic.xml"), "w") as f:
        f.write(render_scene_xml(layout, terrain, drone="dynamic"))
    with open(os.path.join(out_dir, "scene_train.xml"), "w") as f:
        f.write(render_scene_xml(layout, terrain, drone="dynamic", light=True))
    if mask_output:
        with open(mask_output, "w") as f:
            f.write(render_scene_xml(layout, terrain, mask_mode=True))
    write_manifest(layout, terrain, os.path.join(out_dir, "scene_manifest.json"))
    import flowfield
    np.savez_compressed(os.path.join(assets, "flowfield.npz"), **flowfield.compute(terrain, layout))
    if water_anim:
        # bake the animated video-style water and re-write the full-detail scenes to use it
        import live_water
        live_water.build(out_dir, res=water_res)
        global ASSETS_DIR
        ASSETS_DIR = assets
        with open(output_path, "w") as f:
            f.write(render_scene_xml(layout, terrain))
        with open(os.path.join(out_dir, "scene_flood_dynamic.xml"), "w") as f:
            f.write(render_scene_xml(layout, terrain, drone="dynamic"))
    total = sum(h.survivor_count for h in layout.houses)
    print(f"Wrote {output_path}: {len(layout.houses)} mission houses ({total} survivors), "
          f"{len(layout.background_houses)} background buildings, {len(layout.trees)} trees, "
          f"warehouse at ({layout.warehouse.x}, {layout.warehouse.y}).")
    return layout


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate the SkyHydro flood-valley scene (Sprint 3).")
    p.add_argument("--houses", type=int, default=5, help="Number of MISSION houses (4-5 per the scenario).")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--warehouse-end", choices=["upstream", "downstream"], default="upstream")
    p.add_argument("--trees", type=int, default=650)
    p.add_argument("--output", default="scene_flood.xml")
    p.add_argument("--mask-output", default=None, help="Also write a water-mask variant of the scene.")
    p.add_argument("--no-water-anim", action="store_true", help="skip baking the animated live water (flat-colour water)")
    p.add_argument("--water-res", type=int, default=1536, help="live-water texture resolution (1024 fast, 2048 sharp)")
    return p


if __name__ == "__main__":
    a = build_arg_parser().parse_args()
    generate_scene(n_houses=a.houses, seed=a.seed, output_path=a.output,
                   warehouse_end=a.warehouse_end, n_trees=a.trees, mask_output=a.mask_output,
                   water_anim=not a.no_water_anim, water_res=a.water_res)
