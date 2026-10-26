"""
live_water.py — the cinematic flood water, live in MuJoCo's interactive viewer.

MuJoCo's viewer has no custom shaders, so on its own it draws the flood as a
flat, single-coloured sheet. The cinematic video gets its look from
render/water_shader.py (an offline per-pixel shader). This module bakes the
SAME water model into an animated texture on the water heightfield, so the
live simulation looks like the video:

  * turbid, silt-brown body colour (lighter over the shallows), drifting
    sediment plumes
  * wave trains + Unity WaterBump / SmallWaves ripples, all advected along the
    solved flood current (environment/flowfield.py) so they bend around the
    buildings; lit by the scene's sun, with sun glints and sky sheen
  * Unity SimpleFoam whitewater streaked along the current: the white torrent
    pouring down the gorge, wave-crest foam in the channel, foam piling up
    against upstream walls, wakes trailing behind every building

The animation is a seamless loop (LOOP_S seconds, FPS frames/s): every wave
train and both flow-map phases are periodic over the loop. Frames are baked
once (in parallel, ~10-60 s) and cached as JPEGs in assets/water_anim.pkl;
assets/water_tex.png (frame 0) is the static texture the XML loads, so even a
plain `python -m mujoco.viewer` shows proper water.

At run time `LiveWater(model).update(viewer, sim_time)` copies the current
frame into model.tex_data and calls viewer.update_texture().

Build / rebuild the cache:
    python live_water.py                      # in environment/, after scene_generator.py
    python live_water.py --res 2048           # sharper (more RAM/disk, slower bake)
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import pickle
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

ANIM_FILE = "water_anim.pkl"
TEX_FILE = "water_tex.png"
LOOP_S = 4.0                 # seamless loop length (s)
FPS = 20                     # texture frames per second
FM_T = 1.0                   # flow-map cycle (s) — LOOP_S must be a multiple
VERSION = 4

# MuJoCo multiplies the texture by the scene lighting (headlight + sun + sky
# fill on a flat, upward surface). The baked colours are the final on-screen
# colours of the video, divided by this factor (measured with a probe render).
LIGHT_GAIN = 1.33

# viewing direction used for the (view-dependent) glints and sheen: the
# default overview camera (azimuth 106°, elevation −36°)
_az, _el = math.radians(106.0), math.radians(-36.0)
VIEW = -np.array([math.cos(_el) * math.cos(_az), math.cos(_el) * math.sin(_az), math.sin(_el)])
SUN = np.array([-0.35, -0.45, 0.82]); SUN /= np.linalg.norm(SUN)   # direction to the sun (matches the XML light)


# ---------------------------------------------------------------- static fields
def _tex_grid(res):
    import scene_generator as sg
    D = sg.DOMAIN_HALF
    c = (np.arange(res) + 0.5) / res
    xs = -D + 2 * D * c
    ys = D - 2 * D * c                       # texture row 0 = +y (image convention, like terrain_tex.png)
    return xs, ys


def compute_static(env_dir, res):
    """Per-texel world position + every flow/terrain field the shader needs,
    restricted to the band of columns that can ever be wet."""
    import scene_generator as sg
    import flowfield
    from scipy.ndimage import map_coordinates

    man = json.load(open(os.path.join(env_dir, "scene_manifest.json")))
    seed = int(man.get("seed", 1))
    terrain = sg.build_terrain(seed)
    flow_path = os.path.join(env_dir, "assets", "flowfield.npz")
    if os.path.exists(flow_path):
        FLOW = flowfield.Flow(flowfield.load_or_compute(None, None, flow_path))
    else:
        layout = sg.generate_layout(n_houses=len(man["houses"]), seed=seed, terrain=terrain)
        FLOW = flowfield.Flow(flowfield.load_or_compute(terrain, layout, flow_path))

    D, G = sg.DOMAIN_HALF, sg.GRID

    def gs(grid, px, py):
        gi = (px + D) / (2 * D) * (G - 1)
        gj = (D - py) / (2 * D) * (G - 1)
        return map_coordinates(grid, [gj, gi], order=1, mode="nearest")

    xs, ys = _tex_grid(res)
    # columns where water can show (water above ground anywhere along y), with margin
    wet = terrain.water > terrain.heights - 0.3
    colwet = wet.any(axis=0)
    gx = np.linspace(-D, D, G)
    xmin, xmax = gx[colwet].min() - 3, gx[colwet].max() + 3
    c0 = int(np.searchsorted(xs, xmin)); c1 = int(np.searchsorted(xs, xmax))
    PX, PY = np.meshgrid(xs[c0:c1], ys)
    PZ = gs(terrain.water, PX, PY)
    depth = PZ - gs(terrain.heights, PX, PY)
    N = PX - sg.centerline(PY)
    wgy, wgx = np.gradient(terrain.water, 2 * D / (G - 1))
    gorge = sg._smooth(gs(np.hypot(wgx, wgy), PX, PY) / 0.10)
    chan = sg._smooth((-N - 1.0) / 5.0)
    shallow = sg._smooth((1.0 - depth) / 0.8)
    UX, UY = FLOW.sample("ux", PX, PY), FLOW.sample("uy", PX, PY)
    speed = FLOW.sample("speed", PX, PY)
    IMPACT = FLOW.sample("impact", PX, PY)
    SHEAR = FLOW.sample("shear", PX, PY)
    wake = FLOW.sample("wake", PX, PY)
    turb = np.clip(0.30 + 0.55 * chan + 1.0 * gorge + 0.45 * shallow, 0.25, 1.6) + 0.5 * wake + 0.9 * IMPACT + 0.35 * SHEAR
    # only shade texels where water can actually be seen (water above the ground)
    mask = PZ > gs(terrain.heights, PX, PY) - 0.4
    f32 = lambda a: np.ascontiguousarray(a[mask], np.float32)
    return dict(res=res, c0=c0, c1=c1, mask=mask, PX=f32(PX), PY=f32(PY), depth=f32(depth), gorge=f32(gorge),
                chan=f32(chan), shallow=f32(shallow), VX=f32(UX * speed), VY=f32(UY * speed),
                IMPACT=f32(IMPACT), SHEAR=f32(SHEAR), wake=f32(wake), turb=f32(turb),
                texel=2 * D / res)


# ---------------------------------------------------------------- textures
_T = {}


def _load_textures():
    if _T:
        return _T
    from scipy.ndimage import gaussian_filter
    unity = os.path.join(HERE, "assets", "water_unity")

    def gray(name):
        return np.asarray(Image.open(os.path.join(unity, name)).convert("L"), np.float32) / 255.0

    def grad_maps(h):
        gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
        gy = -(np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2
        s = np.sqrt((gx ** 2 + gy ** 2).mean())
        return gx / s, gy / s

    bump = gaussian_filter(gray("WaterBump.jpg"), 0.8, mode="wrap")
    _T["BGX"], _T["BGY"] = grad_maps(bump)
    swell = gaussian_filter(gray("SmallWaves.png"), 0.6, mode="wrap")
    _T["SGX"], _T["SGY"] = grad_maps(swell)
    foam = gray("SimpleFoam.png")
    _T["FOAM"] = (foam - foam.min()) / (foam.max() - foam.min())
    _T["MIPS"] = {}
    return _T


def _tex(name, tile_x, tile_y, xs, ys, foot):
    """Tiling bilinear lookup, pre-filtered to the texel footprint (no aliasing)."""
    from scipy.ndimage import map_coordinates, gaussian_filter
    T = _load_textures()
    m = T[name]
    n = m.shape[0]
    texels = foot * n / min(tile_x, tile_y)
    lev = int(np.clip(round(math.log2(max(texels, 1e-6)) + 1.0), 0, 7))
    key = (name, lev)
    if key not in T["MIPS"]:
        T["MIPS"][key] = m if lev == 0 else gaussian_filter(m, 2.0 ** (lev - 1), mode="wrap")
    return map_coordinates(T["MIPS"][key], [-ys / tile_y * n, xs / tile_x * n], order=1, mode="grid-wrap")


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _waves():
    """Directional wave trains (relative to the current, which runs toward −y),
    with frequencies snapped so every train repeats exactly over LOOP_S."""
    rng = np.random.default_rng(7)
    out = []
    lams = np.exp(rng.uniform(np.log(1.1), np.log(11.0), 16))
    for j, lam in enumerate(sorted(lams)):
        k = 2 * math.pi / lam
        a = max(-1.13, min(1.13, math.radians(rng.normal(0, 32))))
        kd = np.array([math.sin(a), -math.cos(a)])
        w = k * math.sqrt(9.81 / k)
        w = max(1, round(w * LOOP_S / (2 * math.pi))) * 2 * math.pi / LOOP_S      # periodic over the loop
        slope = (0.075 if lam < 4 else 0.05) * rng.uniform(0.7, 1.3)
        out.append((k, kd, w, slope, j % 5 == 2, rng.uniform(0, 6.28)))
    return out


def _fm_phase(tt, shift):
    f = (tt / FM_T + shift) % 1.0
    cycle = int(math.floor(tt / FM_T + shift)) % int(round(LOOP_S / FM_T))      # periodic offsets
    r = np.random.default_rng(cycle * 7919 + int(shift * 13) + 1000)
    return f * FM_T, 1.0 - abs(2.0 * f - 1.0), r.uniform(0, 40, 2)


def shade_frame(S, tt):
    """Final water colour (n_wet_texels x 3, float 0..1, on-screen) at time tt —
    the same model as render/water_shader.py, evaluated in texture space."""
    x, y = S["PX"], S["PY"]
    fo = S["texel"]
    tb, g_i, ch, sh_ = S["turb"], S["gorge"], S["chan"], S["shallow"]
    vx, vy = S["VX"], S["VY"]
    imp, shr, wk = S["IMPACT"], S["SHEAR"], S["wake"]
    sx = np.zeros_like(x); sy = np.zeros_like(x); hgt = np.zeros_like(x)
    PH = []
    for shift in (0.0, 0.5):
        tau, wg, off = _fm_phase(tt, shift)
        qx, qy = x - vx * tau + off[0], y - vy * tau + off[1]
        PH.append((qx, qy, wg))
        for k, kd, w, slope, stationary, ph in S["WAVES"]:
            if stationary:
                continue
            phase = k * (kd[0] * qx + kd[1] * qy) - w * tt + ph
            amp = slope * tb * wg
            c = np.cos(phase)
            sx += amp * kd[0] * c; sy += amp * kd[1] * c; hgt += amp / k * np.sin(phase)
        det = 0.045 * (0.6 + 0.6 * tb)
        sx += wg * (det * (_tex("BGX", 5.0, 7.5, qx, qy, fo) + 0.8 * _tex("BGX", 1.9, 2.6, qx + 0.7, qy, fo))
                    + 0.05 * tb * _tex("SGX", 16.0, 22.0, qx, qy, fo))
        sy += wg * (det * (_tex("BGY", 5.0, 7.5, qx, qy, fo) + 0.8 * _tex("BGY", 1.9, 2.6, qx + 0.7, qy, fo))
                    + 0.05 * tb * _tex("SGY", 16.0, 22.0, qx, qy, fo))
    for k, kd, w, slope, stationary, ph in S["WAVES"]:          # standing waves (torrent, wall pile-up)
        if not stationary:
            continue
        phase = k * (kd[0] * x + kd[1] * y) + ph + 0.35 * math.sin(2 * math.pi * tt / LOOP_S)
        jump = 4.0 * g_i * (1.0 - g_i)                                       # foot of the torrent
        amp = slope * tb * (0.3 + 0.9 * (g_i + 0.5 * ch) + 1.5 * imp + 1.2 * jump)
        c = np.cos(phase)
        sx += amp * kd[0] * c; sy += amp * kd[1] * c; hgt += amp / k * np.sin(phase)
    churn = 1.4 * imp + 0.7 * wk + 0.4 * shr                    # boiling water at walls and in wakes
    ct = 2 * math.pi * tt / LOOP_S
    sx += 0.09 * churn * _tex("BGX", 1.4, 1.4, x + 3.0 * math.cos(ct), y - 3.0 * math.sin(ct), fo)
    sy += 0.09 * churn * _tex("BGY", 1.4, 1.4, x - 3.0 * math.sin(ct), y + 3.0 * math.cos(ct), fo)

    nz = 1.0 / np.sqrt(sx * sx + sy * sy + 1.0)
    nxx, nyy = -sx * nz, -sy * nz
    V = VIEW
    ndv = np.clip(nxx * V[0] + nyy * V[1] + nz * V[2], 0.02, 1)
    F = 0.02 + 0.98 * (1 - ndv) ** 5
    rz = 2 * ndv * nz - V[2]
    sky = np.array([0.82, 0.84, 0.86]) + (np.array([0.60, 0.66, 0.74]) - np.array([0.82, 0.84, 0.86])) * np.clip(rz, 0, 1)[..., None] ** 0.6
    hill = np.array([0.20, 0.27, 0.19])            # mix of forested valley walls and town in the reflection
    env = 0.55 * sky + 0.45 * hill

    sed = sum(w_ * _tex("FOAM", 60.0, 90.0, qx_ * 0.5, qy_, fo) for qx_, qy_, w_ in PH)
    sed = sed.mean() + (sed - sed.mean()) / max(math.sqrt(sum(w_ * w_ for _, _, w_ in PH)), 0.5)
    shl = sh_[..., None]
    body = np.array([0.36, 0.29, 0.21]) * (1 - shl) + np.array([0.47, 0.40, 0.31]) * shl
    body = body * (0.86 + 0.24 * sed[..., None])
    ndl = np.clip(nxx * SUN[0] + nyy * SUN[1] + nz * SUN[2], 0, 1)
    crest = np.clip(hgt / (0.05 + 0.08 * tb), -1, 1)
    diffuse = body * (0.36 + 0.62 * ndl + 0.18 * nz)[..., None] * 0.92 \
        + np.array([0.05, 0.04, 0.025]) * np.clip(crest, 0, 1)[..., None]
    hx, hy, hz = SUN + V
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    ndh = np.clip((nxx * hx + nyy * hy + nz * hz) / hn, 0, 1)
    spec = (0.45 * ndh ** 300 + 0.06 * ndh ** 30)[..., None] * np.array([1.0, 0.98, 0.94])
    calm = (1 - ch) * (1 - g_i)
    Fv = np.clip(F * 3.0 + 0.06 + 0.08 * calm, 0, 1)[..., None]
    col = diffuse * (1 - Fv) + env * Fv + spec

    # foam (Unity SimpleFoam) streaked along the current
    fpat = 0.0
    for qx_, qy_, w_ in PH:
        fa = _tex("FOAM", 9.0, 24.0, qx_, qy_, fo)
        fb = _tex("FOAM", 4.0, 11.0, qx_ + 0.37, qy_, fo)
        rafts = _tex("FOAM", 30.0, 70.0, qx_ + 13.0, qy_, fo)
        fc = _tex("FOAM", 16.0, 26.0, qx_ * 0.8 + 5.0, qy_, fo)              # coarse churn in the torrent
        fpat = fpat + w_ * ((0.55 * fa + 0.45 * fb) * (0.55 + 0.6 * rafts) * (1 - 0.55 * g_i) + 0.55 * g_i * fc)
    wn = math.sqrt(sum(w_ * w_ for _, _, w_ in PH))
    fm0 = float(fpat.mean())
    fpat = fm0 + (fpat - fm0) / max(wn, 0.5)
    cover = np.clip(0.02 + 0.27 * g_i + 0.30 * sh_ * (0.4 + ch) + 0.05 * ch
                    + 0.30 * wk * (0.6 + 0.4 * ch) + 0.75 * imp + 0.30 * shr
                    + 0.35 * np.clip(crest, 0, 1) * (0.2 * ch + g_i), 0, 0.9)
    foam = _smooth((fpat - (1 - cover)) / 0.18)
    foam_col = np.array([0.88, 0.86, 0.82]) * (0.74 + 0.26 * ndl)[..., None]
    col = col * (1 - foam[..., None]) + foam_col * foam[..., None]
    return np.clip(col, 0, 1)


def _encode(col, mask, quality=90):
    band = np.empty(mask.shape + (3,), np.float32)
    band[:] = np.median(col, axis=0)                  # dry texels (never visible): plain water colour
    band[mask] = col
    img = np.clip(band / LIGHT_GAIN * 255.0 + 0.5, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=quality, subsampling=0)
    return buf.getvalue()


# ---------------------------------------------------------------- parallel bake
_S = None


def _worker_init(static_path):
    global _S
    d = np.load(static_path)
    _S = {k: (d[k].item() if d[k].ndim == 0 else d[k]) for k in d.files}
    _S["WAVES"] = _waves()
    _load_textures()


def _worker_frames(idx):
    nf = int(round(LOOP_S * FPS))
    return [(i, _encode(shade_frame(_S, i / FPS), _S["mask"])) for i in idx if i < nf]


def build(env_dir=HERE, res=1536, workers=None, verbose=True):
    """Bake the animated water loop + the static texture into env_dir/assets."""
    t0 = time.time()
    assets = os.path.join(env_dir, "assets")
    S = compute_static(env_dir, res)
    static_path = os.path.join(assets, "_water_static.npz")
    np.savez(static_path, **S)
    nf = int(round(LOOP_S * FPS))
    workers = workers or max(1, min(8, nf, (os.cpu_count() or 2) - 1))     # ~1 GB RAM per worker
    if verbose:
        print(f"live water: baking {nf} frames, {res}x{res} texture (band {S['c1'] - S['c0']} cols), {workers} workers ...", flush=True)
    frames = [None] * nf
    chunks = [list(range(w, nf, workers)) for w in range(workers)]
    # one maths thread per worker process (otherwise every worker opens a thread +
    # memory pool per CPU core and the machine runs out of RAM)
    for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    while workers > 1:
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor
        from concurrent.futures.process import BrokenProcessPool
        ctx = mp.get_context("spawn")             # same on Windows / macOS / Linux
        # spawned workers must be able to import this module whoever called build()
        os.environ["PYTHONPATH"] = HERE + os.pathsep + os.environ.get("PYTHONPATH", "")
        chunks = [list(range(w, nf, workers)) for w in range(workers)]
        try:
            with ProcessPoolExecutor(workers, mp_context=ctx, initializer=_worker_init, initargs=(static_path,)) as ex:
                for res_ in ex.map(_worker_frames, chunks):
                    for i, b in res_:
                        frames[i] = b
            break
        except BrokenProcessPool:
            workers //= 2
            print(f"live water: a worker ran out of memory, retrying with {workers} workers ...", flush=True)
    if workers <= 1:
        _worker_init(static_path)
        for i, b in _worker_frames(range(nf)):
            frames[i] = b
    os.remove(static_path)
    # static texture (frame 0) for the XML: full domain, the band pasted in
    band0 = np.asarray(Image.open(io.BytesIO(frames[0])).convert("RGB"))
    full = np.empty((res, res, 3), np.uint8)
    full[:] = band0[:, :1].mean(axis=(0, 1)).astype(np.uint8)
    full[:, S["c0"]:S["c1"]] = band0
    Image.fromarray(full).save(os.path.join(assets, TEX_FILE))
    with open(os.path.join(assets, ANIM_FILE), "wb") as f:
        pickle.dump(dict(version=VERSION, res=res, c0=S["c0"], c1=S["c1"], fps=FPS, loop=LOOP_S, frames=frames), f)
    if verbose:
        mb = sum(len(b) for b in frames) / 1e6
        print(f"live water: done in {time.time() - t0:.0f} s -> assets/{ANIM_FILE} ({mb:.0f} MB), assets/{TEX_FILE}", flush=True)


# ---------------------------------------------------------------- runtime
class LiveWater:
    """Streams the baked water loop into the model's water texture."""

    def __init__(self, model, env_dir=HERE, tex_name="water_tex", rate=None):
        import mujoco
        self.ok = False
        self.texid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_TEXTURE, tex_name)
        path = os.path.join(env_dir, "assets", ANIM_FILE)
        if self.texid < 0:
            print("live water: scene has no water texture (regenerate it with scene_generator.py) — static water")
            return
        if not os.path.exists(path):
            print("live water: no animation cache yet, baking it now (one-time) ...")
            build(env_dir)
        with open(path, "rb") as f:
            A = pickle.load(f)
        W, H = int(model.tex_width[self.texid]), int(model.tex_height[self.texid])
        nch = int(model.tex_nchannel[self.texid])
        if A.get("version") != VERSION or A["res"] != W or H != W:
            print(f"live water: cache doesn't match the scene texture ({A['res']} vs {W}x{H}) — run environment/live_water.py; static water")
            return
        adr = int(model.tex_adr[self.texid])
        self.tex = model.tex_data[adr:adr + W * H * nch].reshape(H, W, nch)
        self.nch = nch
        self.c0, self.c1 = A["c0"], A["c1"]
        self.frames, self.fps = A["frames"], float(A["fps"])
        self.cache = {}
        self.last = -1
        self.ok = True

    def _frame(self, i):
        f = self.cache.get(i)
        if f is None:
            f = np.asarray(Image.open(io.BytesIO(self.frames[i])).convert("RGB"))
            if len(self.cache) < len(self.frames):        # decoded loop stays in RAM (~ band x res x 3 x frames)
                self.cache[i] = f
        return f

    def update(self, viewer, t):
        """Call every render tick with the simulation time; uploads only when the frame changes."""
        if not self.ok:
            return False
        i = int(t * self.fps) % len(self.frames)
        if i == self.last:
            return False
        self.last = i
        self.tex[:, self.c0:self.c1, :3] = self._frame(i)
        if viewer is not None:
            viewer.update_texture(self.texid)
        return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Bake the live flood-water animation for the MuJoCo viewer.")
    ap.add_argument("--res", type=int, default=1536, help="water texture resolution over the 240 m domain")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    build(HERE, a.res, a.workers)
