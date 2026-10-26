"""
Scripted expert pilot for SkyHydroDeliveryEnv (baseline + demonstrations).

Per leg (to the warehouse pad, or to the next survivor roof):
  CLIMB    up to a safe cruise height above everything along the route
  TRANSIT  fly over the goal, decelerating smoothly; damp payload swing
  DESCEND  lower until the hanging canister is ~1 m above the roof/pad,
           keeping the canister (not the drone) centred on the marker
  HOOK     when the canister is steady inside the window -> trigger winch
It reads the true state from the env (privileged), so it is a reference
for what a good policy should achieve — and can pre-train the RL policy
(behaviour cloning, see train.py --bc-episodes).
"""
import math
import numpy as np


class ExpertPilot:
    def __init__(self, env):
        self.env = env.unwrapped if hasattr(env, "unwrapped") else env

    def _cruise_alt(self, p, goal):
        e = self.env
        zs = [e.surface_below(p[0] + (goal[0] - p[0]) * u, p[1] + (goal[1] - p[1]) * u) for u in np.linspace(0, 1, 25)]
        return max(zs) + 14.0

    def act(self, obs=None):
        e = self.env
        p, v = e.ctrl.pos(), e.ctrl.vel()
        pl = e._payload()
        plv = (pl - e.prev_payload) / e.control_dt
        goal = e._target_point() - np.array([0, 0, 1.2])            # pad / roof surface point
        dxy = goal[:2] - p[:2]
        dist = float(np.hypot(*dxy))
        sway = pl[:2] - p[:2]                                         # canister offset from the pivot
        sway_v = plv[:2] - v[:2]
        cruise = self._cruise_alt(p, goal)
        # horizontal: approach with a speed that tapers near the goal, plus
        # crane-style anti-sway (move the pivot toward the swinging canister)
        speed = min(8.0, 0.35 * dist)
        if p[2] < cruise - 4.0 and dist > 6.0:
            speed = 0.0                                               # climb before transit
        vh = dxy / (dist + 1e-9) * speed + 1.3 * sway + 0.5 * sway_v
        hook = -1.0
        if dist > 2.0:
            vz = np.clip(0.8 * (cruise - p[2]), -2.5, 3.0)
        else:
            settled = np.hypot(*sway) < 0.5 and np.linalg.norm(sway_v) < 0.6
            want = goal[2] + 1.0                                     # canister ~1 m above the surface
            vz = np.clip(0.6 * (want - pl[2]), -1.5, 1.5) if settled else np.clip(0.5 * (want + 3 - pl[2]), -0.5, 1.0)
            pe = goal[:2] - pl[:2]
            if (settled and np.hypot(*pe) < 1.3 and np.linalg.norm(plv) < 1.0
                    and 0.2 < pl[2] - goal[2] < 2.6):
                hook = 1.0
        a = np.array([vh[0] / e.vh, vh[1] / e.vh, vz / e.vv, hook], dtype=np.float32)
        return np.clip(a, -1, 1)


def run_episode(env, pilot=None, seed=None, max_steps=None, verbose=False):
    pilot = pilot or ExpertPilot(env)
    obs, info = env.reset(seed=seed)
    total, events = 0.0, []
    for t in range(max_steps or env.unwrapped.max_steps):
        obs, r, term, trunc, info = env.step(pilot.act(obs))
        total += r
        if info.get("event"):
            events.append((t, info["event"]))
            if verbose:
                print(f"  step {t:4d}  {info['event']}")
        if term or trunc:
            break
    return total, info, events
