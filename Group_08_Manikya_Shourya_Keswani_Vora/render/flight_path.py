"""
Motion script for skyrender: one line per video frame with a pose
(x y z qw qx qy qz) for EVERY mocap body in the scene, in model order:

  uav_chassis   roof-scanning flight: hover over each drop roof, fly to the
                nearest unscanned one (minimum-jerk legs, tilts into its
                acceleration like a real quadrotor, capped at 25 deg)
  scan_gimbal   level camera gimbal following the drone
  helicopter    steady banked circuit over the valley
  debris_*      floating flood debris carried by the computed flow field
                (environment/flowfield.py): drifts with the current, bends
                around buildings, logs/cars turn to align with the flow,
                everything bobs and rolls on the surface, tumbles harder in
                the torrent; pieces that wash out of the valley re-enter at
                the top of the gorge.

Scripted visualisation motion — not the project's flight controller
(that is rl/flight_controller.py + the RL policy).

Usage: python render/flight_path.py out.txt [scene.xml]
"""
import math
import os
import random
import re
import sys

import numpy as np

ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "environment")
sys.path.insert(0, ENV)
import scene_generator as sg   # noqa: E402
import flowfield               # noqa: E402

FPS = 24.0
HOVER_S = 0.8
MAX_TILT = math.radians(25.0)


def qmul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return (w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2)


def axis_q(ax, ang):
    s = math.sin(ang / 2)
    return (math.cos(ang / 2), ax[0] * s, ax[1] * s, ax[2] * s)


def ypr_q(yaw, pitch, roll):
    return qmul(qmul(axis_q((0, 0, 1), yaw), axis_q((0, 1, 0), pitch)), axis_q((1, 0, 0), roll))


def mocap_order(xml_path):
    txt = open(xml_path).read()
    return re.findall(r'<body name="([^"]+)"[^>]*mocap="true"', txt)


def drone_track(layout):
    wps = [np.array(w, float) for w in sg.flight_waypoints(layout)]
    route = [min(wps, key=lambda p: p[1])]
    rest = [p for p in wps if p is not route[0]]
    while rest:
        nxt = min(rest, key=lambda p: np.linalg.norm(p - route[-1]))
        route.append(nxt); rest = [p for p in rest if p is not nxt]
    pts = []
    def hold(p, secs):
        for _ in range(int(round(secs * FPS))):
            pts.append(p.copy())
    hold(route[0], HOVER_S)
    for a, b in zip(route[:-1], route[1:]):
        D = np.linalg.norm(b - a)
        n = int(round(max(2.0, 0.62 * math.sqrt(D)) * FPS))
        for i in range(1, n + 1):
            u = i / n
            e = u * u * u * (u * (6 * u - 15) + 10)
            pts.append(a + (b - a) * e)
        hold(b, HOVER_S)
    P = np.array(pts)
    acc = np.gradient(np.gradient(P, 1 / FPS, axis=0), 1 / FPS, axis=0)
    Q = []
    for a in acc:
        zb = np.array([a[0], a[1], 9.81]); zb /= np.linalg.norm(zb)
        ang = min(math.acos(np.clip(zb[2], -1, 1)), MAX_TILT)
        ax = np.cross([0, 0, 1.0], zb); nrm = np.linalg.norm(ax)
        Q.append((1, 0, 0, 0) if nrm < 1e-9 else axis_q(ax / nrm, ang))
    return P, Q, wps[0][2]


class DebrisSim:
    ELONGATED = {"log", "tree", "plank", "branch", "car", "sheet", "mattress"}

    def __init__(self, terrain, layout, flow, seed=1):
        self.t, self.flow = terrain, flowfield.Flow(flow)
        self.items = sg.debris_items(seed)
        self.rng = random.Random(seed + 4040)
        fl = flow["fluid"] & (flow["wake"] < 0.95)
        L, res = float(flow["L"]), float(flow["res"])
        cells = np.argwhere(fl)
        self.cells_xy = np.stack([cells[:, 1] * res - L, cells[:, 0] * res - L], 1)
        self.fluid = flow["fluid"]; self.L, self.res = L, res
        self.top = self.cells_xy[self.cells_xy[:, 1] > 92]
        n = len(self.items)
        start = self.cells_xy[[self.rng.randrange(len(self.cells_xy)) for _ in range(n)]]
        self.p = start + np.array([[self.rng.uniform(-0.4, 0.4), self.rng.uniform(-0.4, 0.4)] for _ in range(n)])
        self.yaw = np.array([self.rng.uniform(0, 6.28) for _ in range(n)])
        self.spin = np.array([self.rng.uniform(-0.6, 0.6) for _ in range(n)])
        self.ph = np.array([self.rng.uniform(0, 6.28) for _ in range(n)])
        self.slow = np.zeros(n)

    def is_fluid(self, x, y):
        i = int(round((y + self.L) / self.res)); j = int(round((x + self.L) / self.res))
        return 0 <= i < self.fluid.shape[0] and 0 <= j < self.fluid.shape[1] and bool(self.fluid[i, j])

    def surface(self, x, y):
        return float(self.t.water_at(x, y))

    def step(self, dt, time):
        poses = []
        for k, (i, kind, u) in enumerate(self.items):
            x, y = self.p[k]
            for _ in range(3):
                vx, vy = self.flow.velocity(x, y)
                vx, vy = 0.88 * vx, 0.88 * vy
                nx_, ny_ = x + vx * dt / 3, y + vy * dt / 3
                if self.is_fluid(nx_, ny_):
                    x, y = nx_, ny_
                elif self.is_fluid(nx_, y):
                    x = nx_
                elif self.is_fluid(x, ny_):
                    y = ny_
            spd = math.hypot(*self.flow.velocity(x, y))
            self.slow[k] = self.slow[k] + dt if spd < 0.15 else 0.0
            if y < -self.L + 8 or abs(x) > self.L - 4 or self.slow[k] > 4.0:
                x, y = self.top[self.rng.randrange(len(self.top))]
                self.slow[k] = 0.0
            self.p[k] = (x, y)
            # orientation: elongated pieces swing round to lie along the current
            if kind in self.ELONGATED and spd > 0.2:
                vx, vy = self.flow.velocity(x, y)
                target = math.atan2(vy, vx)
                d = (target - self.yaw[k] + math.pi) % (2 * math.pi) - math.pi
                self.yaw[k] += d * min(1.0, 0.8 * dt) + 0.15 * self.spin[k] * dt
            else:
                self.yaw[k] += self.spin[k] * dt * (1 + 0.1 * spd)
            rough = min(1.0, spd / 14.0)
            ph = self.ph[k]
            roll = (0.06 + 0.25 * rough) * math.sin(1.7 * time + ph)
            pitch = (0.05 + 0.2 * rough) * math.sin(2.3 * time + 1.3 * ph)
            z = self.surface(x, y) + (0.05 + 0.15 * rough) * math.sin(2.1 * time + 0.7 * ph)
            poses.append((x, y, z, ypr_q(self.yaw[k], pitch, roll)))
        return poses


def build(seed=1, out="path.txt", xml=None):
    xml = xml or os.path.join(ENV, "scene_flood.xml")
    order = mocap_order(xml)
    terrain = sg.build_terrain(seed)
    layout = sg.generate_layout(n_houses=5, seed=seed, terrain=terrain)
    flow = flowfield.load_or_compute(terrain, layout, os.path.join(ENV, "assets", "flowfield.npz"))
    P, Q, alt = drone_track(layout)
    nfr = len(P)
    (hcx, hcy), hr, hz, period = sg.helicopter_orbit()
    v = 2 * math.pi * hr / period
    bank = math.atan(v * v / (hr * 9.81))
    th0 = math.radians(200)
    deb = DebrisSim(terrain, layout, flow, seed)
    for _ in range(int(6 * FPS)):                  # let the debris spread along the current first
        deb.step(1 / FPS, 0.0)
    debris_index = {f"debris_{i}": k for k, (i, _, _) in enumerate(deb.items)}
    with open(out, "w") as f:
        for i in range(nfr):
            t = i / FPS
            dposes = deb.step(1 / FPS, t)
            groups = []
            for name in order:
                if name == "uav_chassis":
                    p, q = P[i], Q[i]
                elif name == "scan_gimbal":
                    p, q = P[i], (1, 0, 0, 0)
                elif name == "helicopter":
                    th = th0 + 2 * math.pi * t / period
                    p = (hcx + hr * math.cos(th), hcy + hr * math.sin(th), hz + 1.5 * math.sin(t * 0.9))
                    q = qmul(qmul(axis_q((0, 0, 1), th + math.pi / 2), axis_q((0, 1, 0), math.radians(6))),
                             axis_q((1, 0, 0), -bank))
                elif name in debris_index:
                    x, y, z, q = dposes[debris_index[name]]
                    p = (x, y, z)
                else:
                    p, q = (0, 0, -100), (1, 0, 0, 0)
                groups.append(f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f} {q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}")
            f.write(" ".join(groups) + "\n")
    print(f"wrote {out}: {nfr} frames ({nfr / FPS:.1f} s), {len(order)} mocap bodies "
          f"({len(debris_index)} debris), drone altitude {alt:.1f} m")


if __name__ == "__main__":
    build(out=sys.argv[1] if len(sys.argv) > 1 else "path.txt", xml=sys.argv[2] if len(sys.argv) > 2 else None)
