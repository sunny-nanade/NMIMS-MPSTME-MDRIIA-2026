"""
Survey (scan) phase flown before the deliveries, for simulate.py.

The drone flies the survey route at the survey altitude, hovers over each
mission house with the blue scan beam on, and reports what the scan finds:
how many survivors are on the roof, or that the house is already evacuated.
Only houses where survivors were detected go on the delivery list. Then it
returns to where it started, and the trained RL pilot (or the expert) flies
the supply runs.

The survey is a scripted waypoint flight through the same flight controller
(rl/flight_controller.py) — it is not part of what the RL pilot learned. The
"detection" reads each house's survivor count from the scene (ground truth);
there is no camera-image recognition model.
"""
import math

import numpy as np
import mujoco

HOVER_S = 2.0          # time spent scanning each roof
VMAX_H = 8.0           # m/s
VMAX_V = 3.0


class Survey:
    def __init__(self, env, tick, beam=None, log=print):
        """tick(env) is called after every physics step (animation, viewer sync, pacing).
        beam(on: bool) switches the scan beam on/off in the viewer."""
        self.env, self.tick, self.beam, self.log = env, tick, beam or (lambda on: None), log
        self.alt = float(env.man.get("survey_altitude", 30.0))

    def _step(self, v_cmd):
        e = self.env
        for _ in range(e.n_sub):
            e.ctrl.apply(np.asarray(v_cmd, float))
            mujoco.mj_step(e.model, e.data)
            self.tick(e)

    def _fly_to(self, goal, tol=1.2, max_s=90.0, alive=lambda: True):
        """Climb to the goal altitude first if needed, then fly over it and settle."""
        e = self.env
        t0 = e.data.time
        while alive() and e.data.time - t0 < max_s:
            p, v = e.ctrl.pos(), e.ctrl.vel()
            d = goal[:2] - p[:2]
            dist = float(np.hypot(*d))
            vz = float(np.clip(0.8 * (goal[2] - p[2]), -VMAX_V, VMAX_V))
            if p[2] < goal[2] - 3.0 and dist > 5.0:
                vh = np.zeros(2)                                  # climb clear of the roofs before moving
            else:
                vh = d / (dist + 1e-9) * min(VMAX_H, 0.45 * dist)
            if dist < tol and abs(goal[2] - p[2]) < 1.0 and np.linalg.norm(v) < 0.6:
                return True
            self._step([vh[0], vh[1], vz])
        return False

    def _hold(self, secs, alive):
        e = self.env
        t0 = e.data.time
        while alive() and e.data.time - t0 < secs:
            self._step([0.0, 0.0, 0.0])

    def run(self, alive=lambda: True, return_to=None):
        e = self.env
        start = e.ctrl.pos().copy() if return_to is None else np.asarray(return_to, float)
        houses = list(e.man["houses"])
        route, p = [], e.ctrl.pos()
        while houses:                                            # nearest-neighbour survey route
            h = min(houses, key=lambda h: math.hypot(h["x"] - p[0], h["y"] - p[1]))
            route.append(h); houses.remove(h); p = np.array([h["x"], h["y"], self.alt])
        self.log(f"[scan] survey of {len(route)} houses at {self.alt:.0f} m")
        found = []
        self.beam(True)
        for h in route:
            if not alive():
                break
            self._fly_to(np.array([h["x"], h["y"], self.alt]), alive=alive)
            self._hold(HOVER_S, alive)
            n = int(h.get("survivors", 0))
            if n > 0:
                found.append(h["id"])
                self.log(f"[scan] {h['id']}: {n} survivor{'s' if n > 1 else ''} detected on the roof -> added to delivery list")
            else:
                self.log(f"[scan] {h['id']}: no survivors (evacuated) -> skipped")
        self.beam(False)
        self.log(f"[scan] done: {len(found)} houses need supplies -> returning to start, handing over to the pilot")
        self._fly_to(start, tol=0.5, alive=alive)
        self._hold(1.0, alive)
        return found

    def hand_over(self, found):
        """Reset the episode bookkeeping so the pilot starts its mission from here."""
        e = self.env
        e.remaining = [h for h in e.remaining if h["id"] in found]
        e.n_targets = max(1, len(e.remaining))
        e.steps, e.delivered, e.carrying, e.current_house = 0, 0, False, None
        e.prev_payload = e._payload()
        e.prev_dist = float(np.linalg.norm(e._payload() - e._target_point()))
        return e._obs()
