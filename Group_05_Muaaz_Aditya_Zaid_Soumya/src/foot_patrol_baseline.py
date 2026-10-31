"""
Guard foot-patrol baseline (condition guard_baseline) | MDRIIA Group 05 | Owner: E043 Muaaz

A kinematic walker in the SAME MuJoCo scene as the UAVs: it reads the same checkpoint
sites, the same intruder path and the same restricted zone from the model, and its
checkpoint services are scored by the SAME function as the UAV conditions
(patrol_metrics.checkpoint_metrics). It is not a dynamics model of a person: the guard
moves along straight legs at a constant walking speed and pauses at each checkpoint.

ROUTE (documented design, every number in CONFIG below):
  interior  1. Ground floor: the corridor loop patrol_cp0 -> ... -> patrol_cp7, the same
               132 m loop Alpha flies, projected to walking height (eye point
               floor + eye_height_m). Each patrol_cp is serviced on arrival.
            2. Galleries, floors 1..9, in order: from the corridor point in front of the
               lift lobby (patrol_cp7's x-y, which is the gap in the south corridor wall
               that leads to the lifts) the guard walks to the transfer point in front of
               the lift doors, climbs ONE storey by the stair beside the lift core
               (STAIRS), walks back to the gallery and walks the gallery corridor ring
               (same x-y as the ground loop: the gallery corridor sits directly above the
               ground-floor corridor). Walkable observation point of each atrium_cp =
               the gallery-corridor corner nearest to it in plan (the patrol_cp x-y with
               the smallest horizontal distance, about 5.7 m away across the glass
               railing) on that checkpoint's floor; reaching it services that atrium_cp.
            3. After floor 9 the guard takes the lift down to the ground floor (LIFT:
               wait + ride) and starts the next ground loop.
  exterior  The UAV patrol ring (patrol_cp*, the campus boundary wall line offset 3 m
            INWARD, inside the college) projected to the ground: the guard walks the campus
            grounds inside the wall, servicing every patrol_cp.
  ground legs (both scenes): a walking leg must be clear for a body, i.e. rays along the leg
            at knee / waist / eye height, on the centre line and body_half_width_m to each
            side, reach the next point without hitting a collidable geom. A blocked leg (the
            exterior trees planted 2.6 m inside the wall stand 0.4 m outside the ring line) is
            shifted sideways as a whole, in detour_step_m steps up to detour_max_m, to the
            nearest offset whose three sub-legs (step aside, walk parallel, step back) are
            clear, preferring the side toward the ring centre. The checkpoint is still
            serviced on the ring itself. Interior ground legs (the corridor loop) are clear and
            unchanged. Detours are computed once from the model in __init__ (self.ground_vias).

INTRUDER DETECTION (labelled model, not a measurement of a real guard):
  the guard detects the intruder when it is within detect_radius_m of the guard's eye AND
  a ray from the eye to the intruder hits the intruder before any opaque geom
  (translucent geoms -- glass railings, skylight, markers, alpha < 0.5 -- do not block
  the view). Checked at los_check_hz.
"""
import math
import os
import sys

import mujoco
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patrol_metrics import checkpoint_metrics          # noqa: E402  shared with the UAV conditions
from run_telemetry import StepTelemetry                 # noqa: E402

# value, source. Ranges are drawn ONCE per seed (uniform) by draw_guard_params().
# Sources: docs/research/sources_verified.md, section L-24 (guard-patrol baseline parameters).
CONFIG = {
    "walk_speed_mps": ((1.272, 1.462), "Bohannon RW, Age Ageing 1997;26(1):15-19, doi 10.1093/ageing/26.1.15: "
                                       "comfortable gait speed, strata means 1.272-1.462 m/s (adults 20-79). "
                                       "A patrolling guard may walk slower; using comfortable gait is the "
                                       "conservative choice (it favours the guard baseline). Drawn per seed"),
    "stop_mean_s": ((10.0, 60.0), "ASSUMPTION: 10-60 s mean pause per checkpoint (tag scan, look around); no primary "
                                  "source found (sources_verified.md L-24). Drawn per seed"),
    "stop_spread": (0.5, "ASSUMPTION: each pause ~ U[(1 - 0.5) mean, (1 + 0.5) mean], drawn per checkpoint"),
    "eye_height_m": (1.6, "ASSUMPTION: 1.5-1.7 m adult eye height; telemetry z is the eye point"),
    "floor_height_m": (3.6, "models/scene_source/build_nmims_interior.py FLOOR_H (storey height, itself ASSUMED there)"),
    "transfer_xy": ((0.0, -31.0), "in front of the lift doors (y = -32.0 m, lift lobby x in [-6, 6]) in "
                                  "build_nmims_interior.py; a stair beside the lift core is ASSUMED (not modelled)"),
    "stair_vertical_mps": ((0.25, 0.40), "ASSUMPTION: 0.25-0.40 m/s vertical progress climbing stairs, drawn per "
                                         "seed. Anchors (sources_verified.md L-24): stair ascent 0.65 (sd 0.1) m/s "
                                         "slope-wise, Dostan et al., PLoS One 2023, doi 10.1371/journal.pone.0283333; "
                                         "about 0.52 m/s horizontal from 107.4 steps/min x 0.29 m going, Sun et al., "
                                         "Front Public Health 2026, doi 10.3389/fpubh.2025.1725056. Vertical = "
                                         "0.5-0.65 m/s x sin(30-35 deg) = 0.25-0.37 m/s for an ASSUMED 30-35 deg "
                                         "stair pitch (the stair is not modelled)"),
    "lift_wait_s": ((15.0, 60.0), "ASSUMPTION: 15-60 s waiting for a lift, drawn per descent"),
    "lift_speed_mps": (1.5, "ASSUMPTION: 1.0-2.5 m/s mid-rise passenger lift"),
    "detect_radius_m": (15.0, "ASSUMPTION: 10-20 m at which a guard notices a person in an unlit/lit corridor"),
    "los_check_hz": (10.0, "design: line-of-sight test rate"),
    "translucent_alpha": (0.5, "design: geoms with alpha below this do not block the guard's view"),
    "body_half_width_m": (0.3, "ASSUMPTION: 0.25-0.35 m half shoulder width (walking-leg clearance rays)"),
    "leg_ray_heights_m": ((0.2, 0.9, 1.6), "design: knee, waist and eye height above the walking floor"),
    "detour_step_m": (0.25, "design: sideways step tried when a walking leg is blocked"),
    "detour_max_m": (3.0, "design: largest sideways shift tried before giving up (error)"),
    "guards_per_round": (1, "ASSUMPTION: 1-2 guards per round (no primary source, sources_verified.md L-24); "
                            "the simulation walks ONE guard"),
}


def draw_guard_params(rng):
    """Per-seed guard parameters (call with a generator dedicated to the guard)."""
    lo, hi = CONFIG["walk_speed_mps"][0]
    speed = float(rng.uniform(lo, hi))
    lo, hi = CONFIG["stop_mean_s"][0]
    stop = float(rng.uniform(lo, hi))
    lo, hi = CONFIG["stair_vertical_mps"][0]
    stair = float(rng.uniform(lo, hi))
    return {"guard_speed_mps": speed, "guard_stop_mean_s": stop, "stair_vertical_mps": stair}


def _sites(model, prefix):
    out, k = [], 0
    while True:
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"{prefix}{k}")
        if sid < 0:
            return out
        out.append((f"{prefix}{k}", model.site_pos[sid].copy()))
        k += 1


class FootPatrol:
    """Kinematic guard; run() simulates on the physics-step grid of the scene."""

    def __init__(self, model_path, seed, params, intruder_appear_s, rng):
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.seed = seed
        self.rng = rng
        self.p = dict(params)
        self.intruder_appear_s = float(intruder_appear_s)
        self.h = float(self.model.opt.timestep)
        self.eye = CONFIG["eye_height_m"][0]
        ground = _sites(self.model, "patrol_cp")
        gallery = _sites(self.model, "atrium_cp")
        self.visits = {n: [] for n, _ in ground + gallery}
        self.ground = [(n, np.array([p[0], p[1]])) for n, p in ground]
        # observation point of each gallery checkpoint: nearest ground-loop corner, on its floor
        fh = CONFIG["floor_height_m"][0]
        self.floors = {}
        for n, p in gallery:
            j = int(np.argmin([np.linalg.norm(q - p[:2]) for _, q in self.ground]))
            f = int(p[2] // fh)
            self.floors.setdefault(f, {}).setdefault(j, []).append(n)
        self.floor_h = fh
        self._uav_bodies = {b for b in range(self.model.nbody)
                            if (mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, b) or "").startswith("uav_")}
        mujoco.mj_kinematics(self.model, self.data)          # world poses for the leg rays
        n = len(self.ground)
        centre = np.mean([q for _, q in self.ground], axis=0)
        self.ground_vias = {(i, (i + 1) % n): self._ground_path(self.ground[i][1], self.ground[(i + 1) % n][1], centre)
                            for i in range(n)}
        # intruder path (same numeric as the UAV controller reads)
        i = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_NUMERIC, "intruder_path")
        a, k = self.model.numeric_adr[i], self.model.numeric_size[i]
        self.intruder_path = [np.array(q) for q in np.asarray(self.model.numeric_data[a:a + k]).reshape(-1, 2)]
        jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "intruder_root")
        self.iq = self.model.jnt_qposadr[jid]
        self.igeom = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "intruder_geom")
        self.first_detect_s = None

    # ---------------------------------------------------------------- walking legs
    def _blocks(self, g):
        """Collidable geom that is not part of a UAV airframe (same obstacle notion as FR-18)."""
        m = self.model
        if not (m.geom_contype[g] or m.geom_conaffinity[g]):
            return False
        b = m.geom_bodyid[g]
        while b != 0:
            if b in self._uav_bodies:
                return False
            b = m.body_parentid[b]
        return True

    def _ray_clear(self, p, u, length):
        gid = np.zeros(1, dtype=np.int32)
        p, s = np.array(p, dtype=float), 0.0
        while True:
            d = mujoco.mj_ray(self.model, self.data, p, u, None, 1, -1, gid)
            if d < 0 or s + d > length:
                return True
            if self._blocks(int(gid[0])):
                return False
            s += d + 1e-3
            p = p + u * (d + 1e-3)

    def _leg_clear(self, a, b, floor_z=0.0):
        """Body-width clearance of the walking leg a -> b (x-y points) on the floor at floor_z."""
        v = np.array([b[0] - a[0], b[1] - a[1], 0.0])
        L = float(np.linalg.norm(v))
        if L < 1e-6:
            return True
        u = v / L
        nrm = np.array([-u[1], u[0], 0.0])
        w = CONFIG["body_half_width_m"][0]
        return all(self._ray_clear(np.array([a[0], a[1], floor_z + h]) + nrm * dl, u, L)
                   for h in CONFIG["leg_ray_heights_m"][0] for dl in (-w, 0.0, w))

    def _ground_path(self, a, b, centre):
        """Walking points from a to b (b included): [b] when the leg is clear, otherwise the
        smallest sideways shift (toward the ring centre first) whose three sub-legs are clear."""
        if self._leg_clear(a, b):
            return [np.array(b, dtype=float)]
        u = (np.array(b) - np.array(a)) / np.linalg.norm(np.array(b) - np.array(a))
        nrm = np.array([-u[1], u[0]])
        mid = (np.array(a) + np.array(b)) / 2.0
        sides = (1.0, -1.0) if float(nrm @ (centre - mid)) > 0 else (-1.0, 1.0)
        step, top = CONFIG["detour_step_m"][0], CONFIG["detour_max_m"][0]
        for k in range(1, int(round(top / step)) + 1):
            for sd in sides:
                off = nrm * sd * k * step
                a2, b2 = np.array(a) + off, np.array(b) + off
                if self._leg_clear(a, a2) and self._leg_clear(a2, b2) and self._leg_clear(b2, b):
                    return [a2, b2, np.array(b, dtype=float)]
        raise RuntimeError(f"no clear walking leg from {a} to {b} within {top} m sideways")

    # ---------------------------------------------------------------- route plan
    def _segments(self, t_end):
        """Timeline of (t0, t1, p0, p1, state, service names at t1, target) until t_end."""
        segs, t = [], 0.0
        v = self.p["guard_speed_mps"]
        smean, spread = self.p["guard_stop_mean_s"], CONFIG["stop_spread"][0]
        z0 = self.eye
        pos = np.array([*self.ground[0][1], z0])

        def walk(to, services=()):
            nonlocal t, pos
            d = float(np.linalg.norm(to - pos))
            t1 = t + d / v
            segs.append((t, t1, pos.copy(), to.copy(), "WALK", tuple(services)))
            t, pos = t1, to.copy()
            if services:
                pause = smean * float(self.rng.uniform(1 - spread, 1 + spread))
                segs.append((t, t + pause, pos.copy(), pos.copy(), "STOP", ()))
                t += pause

        def walk_ground(i, j):
            """Ground-floor leg i -> j along its planned walking points; services checkpoint j."""
            for via in self.ground_vias[(i, j)][:-1]:
                walk(np.array([via[0], via[1], z0]))
            walk(np.array([*self.ground[j][1], z0]), (self.ground[j][0],))

        def hold(dur, to, state):
            nonlocal t, pos
            segs.append((t, t + dur, pos.copy(), to.copy(), state, ()))
            t, pos = t + dur, to.copy()

        # first service at the start point, t = 0
        segs.append((0.0, 0.0, pos.copy(), pos.copy(), "WALK", (self.ground[0][0],)))
        pause = smean * float(self.rng.uniform(1 - spread, 1 + spread))
        segs.append((0.0, pause, pos.copy(), pos.copy(), "STOP", ()))
        t = pause
        tx, ty = CONFIG["transfer_xy"][0]
        n = len(self.ground)
        landing = self.ground[-1][1]          # interior: corridor point at the lift-lobby opening
        while t < t_end:
            for k in range(1, n):                                # ground loop cp1 .. cp(n-1)
                walk_ground(k - 1, k)
                if t >= t_end:
                    return segs
            if not self.floors:                                  # exterior: close the ring at cp0
                walk_ground(n - 1, 0)
                continue
            for f in sorted(self.floors):
                zf = f * self.floor_h + self.eye
                zprev = pos[2]
                walk(np.array([tx, ty, zprev]))
                hold((zf - zprev) / self.p["stair_vertical_mps"], np.array([tx, ty, zf]), "STAIRS")
                walk(np.array([*landing, zf]))
                obs = self.floors[f]
                for k in list(range(n)):                         # gallery ring, from the landing round
                    walk(np.array([*self.ground[k][1], zf]), obs.get(k, ()))
                walk(np.array([*landing, zf]))
                if t >= t_end:
                    return segs
            walk(np.array([tx, ty, pos[2]]))
            lo, hi = CONFIG["lift_wait_s"][0]
            wait = float(self.rng.uniform(lo, hi))
            hold(wait, pos, "LIFT")
            hold((pos[2] - z0) / CONFIG["lift_speed_mps"][0], np.array([tx, ty, z0]), "LIFT")
            walk(np.array([*landing, z0]))
            walk_ground(n - 1, 0)
        return segs

    # ---------------------------------------------------------------- intruder / LOS
    def _intruder_xy(self, t):
        if t < self.intruder_appear_s:
            return None
        s = (t - self.intruder_appear_s) * 1.35        # same walking pace as the UAV controller's intruder
        for a, b in zip(self.intruder_path, self.intruder_path[1:]):
            L = float(np.linalg.norm(b - a))
            if s <= L:
                return a + (b - a) * s / L
            s -= L
        return self.intruder_path[-1]

    def _sees(self, eye, xy):
        target = np.array([xy[0], xy[1], 0.86])
        vec = target - eye
        dist = float(np.linalg.norm(vec))
        if dist > CONFIG["detect_radius_m"][0]:
            return False
        self.data.qpos[self.iq:self.iq + 3] = target
        self.data.qpos[self.iq + 3:self.iq + 7] = (1, 0, 0, 0)
        mujoco.mj_kinematics(self.model, self.data)
        u = vec / dist
        p = eye.copy()
        gid = np.zeros(1, dtype=np.int32)
        for _ in range(8):                               # look through translucent geoms
            d = mujoco.mj_ray(self.model, self.data, p, u, None, 1, -1, gid)
            if d < 0:
                return False
            g = int(gid[0])
            if g == self.igeom:
                return True
            m = self.model.geom_matid[g]
            alpha = self.model.mat_rgba[m][3] if m >= 0 else self.model.geom_rgba[g][3]
            if alpha >= CONFIG["translucent_alpha"][0]:
                return False
            p = p + u * (d + 1e-3)
        return False

    # ---------------------------------------------------------------- run
    def run(self, duration, telemetry_path=None, run_id=None, condition="guard_baseline"):
        segs = self._segments(duration)
        log = StepTelemetry(telemetry_path, run_id, self.seed, condition) if telemetry_path else None
        nsteps = int(round(duration / self.h))
        los_every = max(1, int(round(1.0 / (CONFIG["los_check_hz"][0] * self.h))))
        k = 0
        for t0, t1, p0, p1, state, services in segs:
            if t1 <= t0 and services:                     # t = 0 service at the start point
                for s in services:
                    self.visits[s].append(t0)
        pending = [(t1, services) for t0, t1, _, _, _, services in segs if services and t1 > t0]
        pi = 0
        for step in range(nsteps):
            t = step * self.h
            while k < len(segs) - 1 and segs[k][1] <= t:
                k += 1
            t0, t1, p0, p1, state, _ = segs[k]
            frac = 0.0 if t1 <= t0 else min(1.0, max(0.0, (t - t0) / (t1 - t0)))
            pos = p0 + (p1 - p0) * frac
            vel = (p1 - p0) / (t1 - t0) if t1 > t0 else np.zeros(3)
            events = []
            while pi < len(pending) and pending[pi][0] <= t + self.h:
                ts, names = pending[pi]
                if ts < duration:
                    for s in names:
                        self.visits[s].append(ts)
                        events.append(f"visit:{s}")
                pi += 1
            if self.first_detect_s is None and step % los_every == 0:
                xy = self._intruder_xy(t)
                if xy is not None and self._sees(pos, xy):
                    self.first_detect_s = t
                    events.append("detect")
            if log is not None:
                log.row("guard", t, pos, vel, p1, fsm_state=state, event=";".join(events))
        if log is not None:
            log.close()
        return self

    def metrics(self):
        m = checkpoint_metrics(self.visits)
        detected = self.first_detect_s is not None
        m.update({
            "detected": int(detected),
            "detection_latency_s": (self.first_detect_s - self.intruder_appear_s) if detected else None,
            "guard_speed_mps": self.p["guard_speed_mps"],
            "guard_stop_mean_s": self.p["guard_stop_mean_s"],
        })
        return m


if __name__ == "__main__":
    import argparse
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import aerial_patrol_swarm as aps
    ap = argparse.ArgumentParser(description="guard foot-patrol baseline, one run")
    ap.add_argument("--scene", default="interior", choices=tuple(aps.SCENES))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--duration", type=float, default=3600.0)
    ap.add_argument("--intruder-appear", type=float, default=100.0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    g = FootPatrol(aps.SCENES[a.scene], a.seed, draw_guard_params(rng), a.intruder_appear, rng).run(a.duration)
    for k, v in g.metrics().items():
        print(f"{k:26s} {v}")
