"""
water_shader.py — physically-motivated water shading for the SkyHydro
flood scene, applied to frames rendered by skyrender (real MuJoCo output).

MuJoCo's renderer draws the flood water as one flat-coloured surface (no
shaders, no animated textures). This step replaces exactly the visible
water pixels (from the mask pass) with a proper water shader evaluated per
pixel in world space:

  * Surface waves: a spectrum of directional wave trains travelling with the
    current (plus standing waves in the rapids), whose amplitude follows the
    local turbulence — choppy in the gorge and river channel, calmer over
    the flooded town.
  * Ripple detail from the Unity Standard Assets water bump maps
    (Water/Textures/WaterBump.jpg at two scales, Water4/Textures/SmallWaves.png
    for broad swell), scrolled downstream with the current.
  * Lighting: Fresnel-weighted reflection of the overcast sky and of the
    forested valley walls, turbid silt-laden body colour (lighter in the
    shallows), sun glints on wave crests, and the real shadows cast by the
    buildings/trees/drone (taken from the MuJoCo render).
  * Foam from Unity's Water4/Textures/SimpleFoam.png, streaked along the
    current: whitewater in the gorge torrent, over shallow gravel, on wave
    crests in the channel, and in bow waves/wakes around flooded buildings.
  * Distance haze and detail fading to avoid shimmer.

Inputs (from skyrender): A scene without scan beam, B water mask, C scene
with scan beam, D planar-reflection render (mirrored camera) + Dm coverage,
E scene with the water hidden. Real reflections of the buildings, trees,
drone and helicopter come from D (rippled by the wave normals); the
submerged ground shows through from E where the water is very shallow.
The scan beam is added back as (C - A) after shading.
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates, gaussian_filter

ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "environment")
sys.path.insert(0, ENV)
import scene_generator as sg
import flowfield

UNITY = os.path.join(ENV, "assets", "water_unity")

ap = argparse.ArgumentParser()
ap.add_argument("prefix", help="skyrender output prefix (reads <prefix>_A.raw ... _E.raw)"); ap.add_argument("out")
ap.add_argument("--fps", type=float, default=24.0)
ap.add_argument("--cam", default=None, help="override camera: extent,elevation,azimuth,center_y")
ap.add_argument("--W", type=int, default=1280); ap.add_argument("--H", type=int, default=960)
ap.add_argument("--ref", type=float, default=None, help="shadow reference luminance (keep chunks consistent)")
ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=None)
ap.add_argument("--path", default=None, help="motion script used for the render (for debris foam)")
ap.add_argument("--xml", default=None, help="scene XML used for the render (mocap order)")
args = ap.parse_args()
W, H = args.W, args.H
FSZ = W * H * 3
os.makedirs(args.out, exist_ok=True)

terrain = sg.build_terrain(1)
layout = sg.generate_layout(n_houses=5, seed=1, terrain=terrain)
cam = sg.camera_params(layout)
if args.cam:
    ext, el_, az_, cy_ = map(float, args.cam.split(","))
    cam.update(extent=ext, elevation=el_, azimuth=az_, center=(float(sg.centerline(cy_)), cy_, 0.0))

# ---------------------------------------------------------------- camera
az, el = math.radians(cam["azimuth"]), math.radians(cam["elevation"])
fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
up = np.array([-math.sin(el) * math.cos(az), -math.sin(el) * math.sin(az), math.cos(el)])
right = np.cross(fwd, up)
eye = np.array(cam["center"]) - 1.5 * cam["extent"] * fwd
th = math.tan(math.radians(cam["fovy"]) / 2)
U, V = np.meshgrid((2 * (np.arange(W) + 0.5) / W - 1) * th * (W / H), (1 - 2 * (np.arange(H) + 0.5) / H) * th)
ray = fwd[None, None] + U[..., None] * right + V[..., None] * up
rz = np.minimum(ray[..., 2], -1e-6)


def gs(grid, px, py, order=1):
    gi = (px + sg.DOMAIN_HALF) / (2 * sg.DOMAIN_HALF) * (sg.GRID - 1)
    gj = (sg.DOMAIN_HALF - py) / (2 * sg.DOMAIN_HALF) * (sg.GRID - 1)
    return map_coordinates(grid, [gj, gi], order=order, mode="nearest")


t = (sg.WATER_Z - eye[2]) / rz
for _ in range(12):        # intersect rays with the (sloped) water surface
    PX, PY = eye[0] + t * ray[..., 0], eye[1] + t * ray[..., 1]
    t = (gs(terrain.water, PX, PY) - eye[2]) / rz
PX, PY = eye[0] + t * ray[..., 0], eye[1] + t * ray[..., 1]
PZ = gs(terrain.water, PX, PY)
DIST = t * np.linalg.norm(ray, axis=-1)
Vd = -ray / np.linalg.norm(ray, axis=-1, keepdims=True)        # surface -> eye
PIX_ANG = 2 * th / H
FOOT = DIST * PIX_ANG / np.clip(Vd[..., 2], 0.15, 1.0)          # pixel footprint on the water (m)

# ------------------------------------------------------- static per-pixel fields
N = PX - sg.centerline(PY)
depth = PZ - gs(terrain.heights, PX, PY)
wgy, wgx = np.gradient(terrain.water, 2 * sg.DOMAIN_HALF / (sg.GRID - 1))
gorge = sg._smooth(gs(np.hypot(wgx, wgy), PX, PY) / 0.10)
chan = sg._smooth((-N - 1.0) / 5.0)
shallow = sg._smooth((1.0 - depth) / 0.8)
# the solved flow field: direction bends around every building, speed piles
# up / slows in front of walls and accelerates through the gaps
FLOW = flowfield.Flow(flowfield.load_or_compute(terrain, layout, os.path.join(ENV, "assets", "flowfield.npz")))
UX, UY = FLOW.sample("ux", PX, PY), FLOW.sample("uy", PX, PY)
speed = FLOW.sample("speed", PX, PY)
IMPACT = FLOW.sample("impact", PX, PY)
SHEAR = FLOW.sample("shear", PX, PY)
wake = FLOW.sample("wake", PX, PY)
VX, VY = UX * speed, UY * speed
turb = np.clip(0.30 + 0.55 * chan + 1.0 * gorge + 0.45 * shallow, 0.25, 1.6) + 0.5 * wake + 0.9 * IMPACT + 0.35 * SHEAR

fine_fade = np.clip(1.0 - (DIST - 90.0) / 200.0, 0.15, 1.0)
mid_fade = np.clip(1.0 - (DIST - 200.0) / 350.0, 0.35, 1.0)

# reflection environment: valley walls (forest) vs overcast sky
L = np.array([-0.35, -0.45, 0.82]); L /= np.linalg.norm(L)        # direction to the sun
SKY_HOR, SKY_ZEN = np.array([0.82, 0.84, 0.86]), np.array([0.60, 0.66, 0.74])
HILL = np.array([0.07, 0.15, 0.08])

# ------------------------------------------------------- Unity textures
def load_gray(name):
    return np.asarray(Image.open(os.path.join(UNITY, name)).convert("L"), np.float32) / 255.0


def grad_maps(h):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
    gy = -(np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2           # rows run toward −y
    s = np.sqrt((gx ** 2 + gy ** 2).mean())
    return gx / s, gy / s


bump = gaussian_filter(load_gray("WaterBump.jpg"), 0.8, mode="wrap")
BGX, BGY = grad_maps(bump)
swell = gaussian_filter(load_gray("SmallWaves.png"), 0.6, mode="wrap")
SGX, SGY = grad_maps(swell)
FOAM = load_gray("SimpleFoam.png")
FOAM = (FOAM - FOAM.min()) / (FOAM.max() - FOAM.min())


MIPS = {}


def mip_stack(m):
    key = id(m)
    if key not in MIPS:
        MIPS[key] = [m] + [gaussian_filter(m, 2.0 ** (l - 1), mode="wrap") for l in range(1, 8)]
    return MIPS[key]


def tex(m, tile_x, tile_y, xs, ys, foot=None):
    """Bilinear, tiling, and filtered to the pixel footprint (trilinear-style
    blend between pre-blurred levels) so fine texture never aliases."""
    n = m.shape[0]
    cr = [-ys / tile_y * n, xs / tile_x * n]
    if foot is None:
        return map_coordinates(m, cr, order=1, mode="grid-wrap")
    stack = mip_stack(m)
    texels = foot * n / min(tile_x, tile_y)
    lev = np.clip(np.log2(np.maximum(texels, 1e-6)) + 1.0, 0, len(stack) - 1.001)
    l0 = np.floor(lev).astype(int); w = lev - l0
    out = np.zeros_like(xs)
    for l in np.unique(l0):
        sel = l0 == l
        c = [cr[0][sel], cr[1][sel]]
        a = map_coordinates(stack[l], c, order=1, mode="grid-wrap")
        b = map_coordinates(stack[l + 1], c, order=1, mode="grid-wrap")
        out[sel] = a * (1 - w[sel]) + b * w[sel]
    return out


# directional wave trains (relative to the current, which runs toward −y)
rng = np.random.default_rng(7)
WAVES = []
# a broad random spectrum (no visible regular stripes): 16 trains, wavelengths
# 1.1–11 m, directions spread ±65° about the current, a few standing waves
lams = np.exp(rng.uniform(np.log(1.1), np.log(11.0), 16))
for j, lam in enumerate(sorted(lams)):
    k = 2 * math.pi / lam
    a = math.radians(rng.normal(0, 32))
    a = max(-1.13, min(1.13, a))
    kd = np.array([math.sin(a), -math.cos(a)])           # propagation direction (mostly downstream)
    c = math.sqrt(9.81 / k)
    slope = (0.075 if lam < 4 else 0.05) * rng.uniform(0.7, 1.3)
    WAVES.append((k, kd, c, slope, j % 5 == 2, rng.uniform(0, 6.28)))

RAW = {k: np.memmap(f"{args.prefix}_{k}.raw", dtype=np.uint8, mode="r") for k in ("A", "B", "C", "D", "Dm", "E")}

# floating debris positions per frame (from the motion script), for foam rings + wakes
DEBRIS = None
if args.path and args.xml:
    import re
    order = re.findall(r'<body name="([^"]+)"[^>]*mocap="true"', open(args.xml).read())
    cols_ = [k for k, nme in enumerate(order) if nme.startswith("debris_")]
    if cols_:
        allp = np.loadtxt(args.path, ndmin=2)
        DEBRIS = np.stack([allp[:, 7 * k:7 * k + 3] for k in cols_], 1)       # frames x n x 3
FM_T = 1.2                                       # flow-map cycle (s)


def fm_phase(tt, shift):
    f = (tt / FM_T + shift) % 1.0
    cycle = math.floor(tt / FM_T + shift)
    r = np.random.default_rng(int(cycle * 7919 + shift * 13 + 1000))
    return f * FM_T, 1.0 - abs(2.0 * f - 1.0), r.uniform(0, 40, 2)
nf = min(len(RAW[k]) for k in ("A", "B", "C", "D", "E")) // FSZ
# screen-space directions of world x/y, for rippling the reflection image
SCR_R = right[:2]; SCR_U = up[:2]
print("frames:", nf)
REF = None


def frame(key, i, flip=True):
    a = np.asarray(RAW[key][i * FSZ:(i + 1) * FSZ]).reshape(H, W, 3)
    return np.flipud(a) if flip else a     # D (mirrored camera) is already the right way up when not flipped


for i in range(args.start, min(nf, args.end if args.end is not None else nf)):
    A = frame("A", i).astype(np.float32) / 255
    Bm = frame("B", i)
    Cf = frame("C", i).astype(np.float32) / 255
    Dr = frame("D", i, flip=False).astype(np.float32) / 255
    Dcov = np.asarray(RAW["Dm"][i * W * H:(i + 1) * W * H]).reshape(H, W).astype(np.float32) / 255
    Ef = frame("E", i).astype(np.float32) / 255
    m = ((Bm[..., 0] > 200) & (Bm[..., 2] > 200) & (Bm[..., 1] < 70) & (t > 0)).astype(np.float32)
    soft = np.clip(gaussian_filter(m, 0.7) * 1.3, 0, 1) * (gaussian_filter(m, 1.5) > 0.05)
    idx = soft > 0
    tt = i / args.fps
    x, y, z = PX[idx], PY[idx], PZ[idx]
    sp, tb = speed[idx], turb[idx]
    fo = FOOT[idx]
    ff, mf = fine_fade[idx], mid_fade[idx]

    # ---- surface slope: everything is carried ALONG the solved flow field
    #      (flow-map advection, two blended phases) so waves, ripples and foam
    #      bend around the buildings instead of passing through them
    vx_i, vy_i = VX[idx], VY[idx]
    imp_i, sh_i, wk_i = IMPACT[idx], SHEAR[idx], wake[idx]
    sx = np.zeros_like(x); sy = np.zeros_like(x); hgt = np.zeros_like(x)
    PH = []
    for shift in (0.0, 0.5):
        tau, wgt_, off = fm_phase(tt, shift)
        qx, qy = x - vx_i * tau + off[0], y - vy_i * tau + off[1]
        PH.append((qx, qy, wgt_))
        for k, kd, c, slope, stationary, ph in WAVES:
            if stationary:
                continue
            phase = k * (kd[0] * qx + kd[1] * qy) - k * c * tt + ph
            amp = slope * tb * (mf if 2 * math.pi / k > 3 else ff) * wgt_
            cphase = np.cos(phase)
            sx += amp * kd[0] * cphase; sy += amp * kd[1] * cphase; hgt += amp / k * np.sin(phase)
        d1x, d1y = tex(BGX, 5.0, 7.5, qx, qy, fo), tex(BGY, 5.0, 7.5, qx, qy, fo)
        d2x, d2y = tex(BGX, 1.9, 2.6, qx + 0.7, qy, fo), tex(BGY, 1.9, 2.6, qx + 0.7, qy, fo)
        s3x, s3y = tex(SGX, 16.0, 22.0, qx, qy, fo), tex(SGY, 16.0, 22.0, qx, qy, fo)
        det = 0.045 * (0.6 + 0.6 * tb)
        sx += wgt_ * (det * (d1x * mf + 0.8 * d2x * ff) + 0.05 * tb * s3x * mf)
        sy += wgt_ * (det * (d1y * mf + 0.8 * d2y * ff) + 0.05 * tb * s3y * mf)
    # standing waves: in the torrent, and piled up against the walls the current hits
    for k, kd, c, slope, stationary, ph in WAVES:
        if not stationary:
            continue
        phase = k * (kd[0] * x + kd[1] * y) + ph
        amp = slope * tb * ff * (0.3 + 0.9 * (gorge[idx] + 0.5 * chan[idx]) + 1.5 * imp_i)
        cphase = np.cos(phase)
        sx += amp * kd[0] * cphase; sy += amp * kd[1] * cphase; hgt += amp / k * np.sin(phase)
    # churning, boiling water against upstream walls and in the wakes
    if np.any(imp_i + wk_i > 0.05):
        ch1 = tex(BGX, 1.4, 1.4, x * 1.0 + 3.1 * tt, y - 2.3 * tt, fo) * (1.4 * imp_i + 0.7 * wk_i + 0.4 * sh_i)
        ch2 = tex(BGY, 1.4, 1.4, x - 2.7 * tt, y * 1.0 + 1.9 * tt, fo) * (1.4 * imp_i + 0.7 * wk_i + 0.4 * sh_i)
        sx += 0.09 * ch1; sy += 0.09 * ch2
    Nn = np.stack([-sx, -sy, np.ones_like(sx)], 1)
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    Vv = Vd[idx]

    # ---- lighting ----
    ndv = np.clip((Nn * Vv).sum(1), 0.02, 1)
    F = 0.02 + 0.98 * (1 - ndv) ** 5
    Rr = 2 * ndv[:, None] * Nn - Vv
    rel = np.arcsin(np.clip(Rr[:, 2], -1, 1))
    nn_ = N[idx]
    rn = Rr[:, 0]
    dwall = np.where(rn < 0, (nn_ - (sg.LEFT_TOE_N - 6)) / np.maximum(-rn, 1e-3), (sg.RIGHT_TOE_N + 6 - nn_) / np.maximum(rn, 1e-3))
    dwall = np.minimum(dwall, np.where(Rr[:, 1] > 0, (100.0 - y) / np.maximum(Rr[:, 1], 1e-3), 1e9))
    wall_el = np.arctan2(42.0 - z, np.maximum(dwall * np.hypot(Rr[:, 0], Rr[:, 1]), 1.0))
    occ = sg._smooth((wall_el - rel) / 0.08)[:, None]
    sky = SKY_HOR + (SKY_ZEN - SKY_HOR) * np.clip(Rr[:, 2], 0, 1)[:, None] ** 0.6
    env = sky * (1 - occ) + HILL * occ
    # real reflections (buildings, trees, drone, helicopter) from the mirrored
    # render, displaced by the wave normals so they wobble with the surface
    rows, cols = np.nonzero(idx)
    kpx = 55.0 * np.clip(110.0 / DIST[idx], 0.4, 1.6)
    dc = (sx * SCR_R[0] + sy * SCR_R[1]) * kpx
    dr = -(sx * SCR_U[0] + sy * SCR_U[1]) * kpx
    rr_, cc_ = rows + dr, cols + dc
    rcov = map_coordinates(Dcov, [rr_, cc_], order=1, mode="nearest")[:, None]
    rcol = np.stack([map_coordinates(Dr[..., ch], [rr_, cc_], order=1, mode="nearest") for ch in range(3)], 1)
    refl = env * (1 - rcov) + rcol * 0.92 * rcov

    # turbid, silt-laden water body: lighter where shallow, slow drifting sediment plumes
    sed = sum(w_ * tex(FOAM, 60.0, 90.0, qx_ * 0.5, qy_, fo) for qx_, qy_, w_ in PH)
    sed = sed.mean() + (sed - sed.mean()) / max(math.sqrt(sum(w_ * w_ for _, _, w_ in PH)), 0.5)
    shallow_i = shallow[idx][:, None]
    body = np.array([0.33, 0.26, 0.18]) * (1 - shallow_i) + np.array([0.48, 0.40, 0.30]) * shallow_i
    body = body * (0.88 + 0.22 * sed[:, None])
    # very shallow water: the submerged ground (from the no-water render) shows through
    vis = (np.exp(-np.clip(depth[idx], 0, None) / 0.22) * 0.65)[:, None]
    body = body * (1 - vis) + Ef[idx] * 0.72 * vis
    ndl = np.clip(Nn @ L, 0, 1)
    sky_fac = np.clip(Nn[:, 2], 0, 1)
    crest = np.clip(hgt / (0.05 + 0.08 * tb), -1, 1)
    diffuse = body * (0.30 + 0.62 * ndl + 0.18 * sky_fac)[:, None] + np.array([0.05, 0.04, 0.025]) * np.clip(crest, 0, 1)[:, None]
    Hh = L[None, :] + Vv
    Hh /= np.linalg.norm(Hh, axis=1, keepdims=True)
    ndh = np.clip((Nn * Hh).sum(1), 0, 1)
    spec = (0.55 * ndh ** 300 + 0.07 * ndh ** 30)[:, None] * np.array([1.0, 0.98, 0.94])

    # real shadows from the MuJoCo render (buildings, trees, drone)
    lum = A[idx].mean(1)
    if REF is None:
        REF = args.ref if args.ref else np.percentile(lum, 75)
        print("shadow reference", REF, flush=True)
    shadow = np.clip(lum / REF, 0.4, 1.08)[:, None]

    calm = (1 - chan[idx]) * (1 - gorge[idx])
    Fv = np.clip(F * 3.0 + 0.07 + 0.10 * calm, 0, 1)[:, None]   # calmer street water mirrors more
    col = diffuse * (1 - Fv) * shadow + refl * Fv * (0.6 + 0.4 * shadow) + spec * shadow ** 2

    # ---- foam (Unity SimpleFoam), streaked along the current ----
    fpat = 0.0
    for qx_, qy_, w_ in PH:
        fa = tex(FOAM, 9.0, 24.0, qx_, qy_, fo)
        fb = tex(FOAM, 4.0, 11.0, qx_ + 0.37, qy_, fo)
        rafts = tex(FOAM, 30.0, 70.0, qx_ + 13.0, qy_, fo)                     # patchy foam rafts
        fpat = fpat + w_ * (0.55 * fa + 0.45 * fb) * (0.55 + 0.6 * rafts)
    # blending two flow-map phases averages two noise samples and washes out
    # their contrast (-> flat white slabs); restore the variance
    wn = math.sqrt(sum(w_ * w_ for _, _, w_ in PH))
    fm0 = float(fpat.mean())
    fpat = fm0 + (fpat - fm0) / max(wn, 0.5)
    g_i = gorge[idx]
    # debris: foam collar around each floating object + short churned wake
    deb = np.zeros_like(x)
    if DEBRIS is not None and i < len(DEBRIS):
        cur, prv = DEBRIS[i], DEBRIS[max(0, i - 6)]
        for (dx_, dy_, dz_), (px_, py_, _) in zip(cur, prv):
            sel = (np.abs(x - dx_) < 9) & (np.abs(y - dy_) < 9)
            if not sel.any():
                continue
            rr = np.hypot(x[sel] - dx_, y[sel] - dy_)
            mvx, mvy = dx_ - px_, dy_ - py_
            mv = math.hypot(mvx, mvy) + 1e-6
            along = -((x[sel] - dx_) * mvx + (y[sel] - dy_) * mvy) / mv        # distance behind the object
            across = np.abs((x[sel] - dx_) * mvy - (y[sel] - dy_) * mvx) / mv
            collar = np.exp(-np.maximum(rr - 0.6, 0) / 0.45)
            trail = np.exp(-across / (0.4 + 0.12 * np.maximum(along, 0))) * np.exp(-np.maximum(along, 0) / 4.0) * (along > 0)
            deb[sel] = np.maximum(deb[sel], np.maximum(collar, 0.8 * trail))
    cover = np.clip(0.02 + 0.30 * g_i + 0.30 * shallow[idx] * (0.4 + chan[idx]) + 0.05 * chan[idx]
                    + 0.30 * wk_i * (0.6 + 0.4 * chan[idx]) + 0.75 * imp_i + 0.30 * sh_i + 0.40 * deb
                    + 0.35 * np.clip(crest, 0, 1) * (0.2 * chan[idx] + g_i), 0, 0.9)
    foam = sg._smooth((fpat - (1 - cover)) / 0.18) * (0.55 + 0.45 * mf)
    foam_col = np.array([0.88, 0.86, 0.82]) * (0.72 + 0.28 * ndl)[:, None] * shadow
    col = col * (1 - foam[:, None]) + foam_col * foam[:, None]

    # distance haze
    hz = (1 - np.exp(-DIST[idx] / 3000.0))[:, None]
    col = col * (1 - hz) + np.array([0.76, 0.79, 0.82]) * hz

    out = A.copy()
    a_ = soft[idx][:, None]
    out[idx] = A[idx] * (1 - a_) + np.clip(col, 0, 1) * a_

    # spray climbing the walls the flood slams into: at the water's edge,
    # where the current runs into a building, paint churning white water a
    # little way up the wall (animated)
    wm = m > 0.5
    edge = wm & ~np.roll(wm, 1, axis=0)                     # water pixel whose upper neighbour is not water
    imp_px = np.zeros((H, W), np.float32)
    imp_px[idx] = imp_i
    E = np.where(edge, imp_px, 0.0)
    if E.max() > 0.05:
        nz = tex(FOAM, 2.0, 2.0, PX[edge] + 4.0 * tt, PY[edge] * 0.3 + 1.3 * tt, None)
        E[edge] = E[edge] * (0.4 + 0.9 * nz)
        hpx = int(np.clip(np.median(0.9 / (DIST[edge] * PIX_ANG)), 3, 14))
        spray = np.zeros((H, W), np.float32)
        for s_ in range(1, hpx + 1):
            spray = np.maximum(spray, np.roll(E, -s_, axis=0) * (1 - s_ / (hpx + 1)) ** 1.3)
        spray = np.where(wm, 0.0, np.clip(spray * 1.4, 0, 0.85))
        out = out * (1 - spray[..., None]) + np.array([0.86, 0.84, 0.79]) * spray[..., None]
    out = np.clip(out + (Cf - A), 0, 1)              # scan beam back on top
    Image.fromarray((out * 255).astype(np.uint8)).save(f"{args.out}/frame_{i:04d}.png")
    if i % 20 == 0:
        print("frame", i, flush=True)
print("done")
