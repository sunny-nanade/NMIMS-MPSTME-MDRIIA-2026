"""
simulate.py — open the SkyHydro flood-relief environment in MuJoCo's
interactive 3D viewer and watch (or fly) the mission live.

  python simulate.py                                   # the TRAINED pilot from results/ flies the mission
                                                       # (scripted expert if nothing is trained yet)
  python simulate.py --replay                          # replay the trained pilot's recorded test flights
  python simulate.py --policy expert                   # scripted expert pilot
  python simulate.py --policy runs/ppo_stage3/best_model.zip   # any model file
  python simulate.py --policy manual                   # fly it yourself (keys below)
  python simulate.py --policy hover                    # just hover, explore the scene
  python simulate.py --light                           # fast training scene instead of the full-detail one
  python simulate.py --free-cam                        # start from the cinematic video's overview camera

The flood water is animated live (environment/live_water.py) with the same
look as the cinematic video: muddy current, foam streaks, the white torrent
down the gorge, foam piling against walls and wakes behind buildings.

Manual keys (viewer window focused):
  I / K  forward / back (+y / -y)     J / L  left / right (-x / +x)
  U / O  up / down                    H      winch hook (pick up / release)
  (the viewer's own mouse controls still work: rotate / zoom / pan / double-click to track)

macOS: run with `mjpython simulate.py ...` (MuJoCo's passive viewer needs it).
"""
import argparse
import math
import os
import time

import numpy as np
import mujoco
import mujoco.viewer

from rl import STAGES
from rl.skyhydro_env import SkyHydroDeliveryEnv
from rl.expert import ExpertPilot

ROOT = os.path.dirname(os.path.abspath(__file__))
SPIN = {"heli_main_rotor": 17.0, "heli_tail_rotor": 50.0,
        "uav_prop1": 33.0, "uav_prop2": -33.0, "uav_prop3": 33.0, "uav_prop4": -33.0}


class SceneAnimator:
    """Keeps the 'live' extras moving while physics runs: the rescue
    helicopter circling the valley (rotors spinning), the drone's
    propellers, the level camera gimbal + scan beam under the drone, and the
    flood debris (logs, uprooted trees, barrels, cars...) drifting with the
    computed current (environment/flowfield.py) around the buildings."""

    def __init__(self, env):
        m = env.model
        self.env = env
        bid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)
        self.heli = int(m.body_mocapid[bid("helicopter")]) if bid("helicopter") >= 0 else -1
        self.gimbal = int(m.body_mocapid[bid("scan_gimbal")]) if bid("scan_gimbal") >= 0 else -1
        self.spin = []
        for name, rate in SPIN.items():
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, name)
            if j >= 0:
                self.spin.append((int(m.jnt_qposadr[j]), int(m.jnt_dofadr[j]), rate))
        with open(os.path.join(os.path.dirname(env.xml_path), "scene_manifest.json")) as f:
            import json
            man = json.load(f)
        # helicopter orbit (same circuit as the cinematic video)
        orb = man.get("helicopter_orbit", {"center": [0, 8], "radius": 46.0, "altitude": 50.0, "period": 22.0})
        self.c = np.array(orb["center"], float)
        self.r, self.z, self.period = orb["radius"], orb["altitude"], orb["period"]
        self.debris, self.deb_t = None, 0.0
        try:
            self._init_debris(env, m, bid)
        except Exception as exc:                     # scenery only — never stop the sim for it
            print("debris animation off:", exc)

    def _init_debris(self, env, m, bid):
        ids = [(int(m.body_mocapid[bid(f"debris_{i}")]), i) for i in range(200) if bid(f"debris_{i}") >= 0]
        npz = os.path.join(os.path.dirname(env.xml_path), "assets", "flowfield.npz")
        if not ids or not os.path.exists(npz):
            return
        import sys
        sys.path.insert(0, os.path.join(ROOT, "render"))
        from flight_path import DebrisSim          # also puts environment/ on the path
        import flowfield

        class _Water:                                 # water-surface lookup from the env's grids
            water_at = staticmethod(lambda x, y: env._grid_at(env.water, x, y))
        flow = flowfield.load_or_compute(None, None, npz)
        self.debris = DebrisSim(_Water(), None, flow, seed=1)
        self.deb_ids = {i: mid for mid, i in ids}
        for _ in range(int(6 * 24)):                  # spread the debris along the current
            self.debris.step(1 / 24, 0.0)

    def __call__(self, env):
        d, t = env.data, env.data.time
        for qa, da, rate in self.spin:
            d.qpos[qa] = rate * t
            d.qvel[da] = rate
        if self.heli >= 0:
            th = 2 * math.pi * t / self.period
            d.mocap_pos[self.heli] = [self.c[0] + self.r * math.cos(th), self.c[1] + self.r * math.sin(th),
                                      self.z + 1.5 * math.sin(0.9 * t)]
            yaw = th + math.pi / 2
            bank = math.atan((2 * math.pi * self.r / self.period) ** 2 / (self.r * 9.81))
            cy, sy, cr, sr = math.cos(yaw / 2), math.sin(yaw / 2), math.cos(-bank / 2), math.sin(-bank / 2)
            d.mocap_quat[self.heli] = [cy * cr, cy * sr, sy * sr, sy * cr]   # yaw then roll
        if self.gimbal >= 0:
            d.mocap_pos[self.gimbal] = env.ctrl.pos()
            d.mocap_quat[self.gimbal] = [1, 0, 0, 0]
        if self.debris is not None and (t - self.deb_t >= 1 / 30 or t < self.deb_t):
            dt = min(max(t - self.deb_t, 0.0), 0.1) if t >= self.deb_t else 1 / 30
            self.deb_t = t
            for (i, _, _), (x, y, z, q) in zip(self.debris.items, self.debris.step(dt, t)):
                mid = self.deb_ids.get(i)
                if mid is not None:
                    d.mocap_pos[mid] = [x, y, z]
                    d.mocap_quat[mid] = q


class Manual:
    KEYS = {73: (0, 1, 0), 75: (0, -1, 0), 74: (-1, 0, 0), 76: (1, 0, 0), 85: (0, 0, 1), 79: (0, 0, -1)}  # I K J L U O

    def __init__(self):
        self.cmd = np.zeros(3)
        self.hook = False

    def key(self, keycode):
        if keycode in self.KEYS:
            self.cmd = np.clip(self.cmd + 0.25 * np.array(self.KEYS[keycode]), -1, 1)
        elif keycode == 72:          # H
            self.hook = True
        elif keycode == 32:          # space: stop
            self.cmd[:] = 0

    def act(self, obs):
        a = np.array([*self.cmd, 1.0 if self.hook else -1.0], np.float32)
        self.hook = False
        return a


def replay(args):
    """Play a recorded flight (rl/record.py JSON) in the full 3D scene — no model or torch needed."""
    import json
    doc = json.load(open(args.replay))
    xml = os.path.join(ROOT, "environment", "scene_flood_dynamic.xml")
    env = SkyHydroDeliveryEnv(xml_path=xml, physics_dt=0.004, **STAGES[doc.get("stage", 3)])
    env.reset(seed=0)
    m, d = env.model, env.data
    q_root = int(m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "uav_root_joint")])
    qc = env.cable_q
    fps = float(doc.get("fps", 30))
    print(f"replay: {doc.get('policy')}  stage {doc.get('stage')}  {len(doc['episodes'])} episode(s)  "
          f"success {doc['summary']['success_rate']:.0%}")
    anim = SceneAnimator(env)
    water = None
    if not args.static_water:
        try:
            import sys
            sys.path.insert(0, os.path.join(ROOT, "environment"))
            from live_water import LiveWater
            water = LiveWater(m, os.path.dirname(xml)); water = water if water.ok else None
        except Exception as exc:
            print("live water off:", exc)
    with mujoco.viewer.launch_passive(m, d) as viewer:
        viewer.cam.distance, viewer.cam.elevation, viewer.cam.azimuth = 70.0, -28.0, 110.0
        if args.free_cam:
            viewer.cam.lookat[:] = m.stat.center
            viewer.cam.distance, viewer.cam.elevation, viewer.cam.azimuth = 1.5 * m.stat.extent, -36.0, 106.0
        def beam(on):
            with viewer.lock():
                viewer.opt.geomgroup[4] = 1 if on else 0

        pace = {"wall": time.time(), "sim": 0.0}

        def tick(e):                            # animation + viewer refresh during the live survey flight
            anim(e)
            if e.data.time - pace["sim"] >= 1 / 60:
                if water is not None:
                    water.update(viewer, e.data.time)
                if not args.free_cam:
                    viewer.cam.lookat[:] = e.ctrl.pos()
                viewer.sync()
                lag = (e.data.time - pace["sim"]) / args.speed - (time.time() - pace["wall"])
                if lag > 0:
                    time.sleep(lag)
                pace["wall"], pace["sim"] = time.time(), e.data.time

        while viewer.is_running():
            for ep in doc["episodes"]:
                print(f"--- episode {ep['episode']}: {ep['result']}, delivered {ep['delivered']}/{ep['targets']}, "
                      f"return {ep['return']}")
                t0 = 0.0
                if not args.no_scan:            # survey flight first, from where the recorded flight starts
                    mujoco.mj_resetData(m, d)
                    fr0 = ep["frames"][0]
                    d.qpos[q_root:q_root + 7] = fr0[:7]
                    mujoco.mj_forward(m, d)
                    env.carrying = False; env._set_payload_visible(False)
                    pace["wall"], pace["sim"] = time.time(), d.time
                    from rl.scan import Survey
                    Survey(env, tick, beam).run(alive=viewer.is_running, return_to=fr0[:3])
                    print("[replay] recorded pilot flight starts")
                    t0 = d.time
                events = list(ep["events"])
                t_wall = time.time()
                for k, fr in enumerate(ep["frames"]):
                    if not viewer.is_running():
                        break
                    t = k / fps
                    d.qpos[q_root:q_root + 7] = fr[:7]
                    d.qpos[qc[0]], d.qpos[qc[1]] = fr[7], fr[8]
                    env.carrying = bool(fr[9]); env._set_payload_visible(env.carrying)
                    d.time = t0 + t
                    anim(env)
                    mujoco.mj_forward(m, d)
                    while events and events[0]["t"] <= t:
                        e = events.pop(0)
                        print(f"[t={e['t']:6.1f}s] {e['event']:>18}   delivered {e['delivered']}/{e['of']}")
                    if water is not None:
                        water.update(viewer, t0 + t)
                    if not args.free_cam:
                        viewer.cam.lookat[:] = fr[:3]
                    viewer.sync()
                    lag = t / args.speed - (time.time() - t_wall)
                    if lag > 0:
                        time.sleep(lag)
                t_end = time.time()
                while viewer.is_running() and time.time() - t_end < 2:
                    viewer.sync(); time.sleep(0.05)
    env.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="auto",
                    help="auto (trained pilot from results/, else expert) | trained | expert | manual | hover | random | path/to/model.zip")
    ap.add_argument("--light", action="store_true", help="use the fast training scene")
    ap.add_argument("--stage", type=int, choices=[1, 2, 3], default=None,
                    help="mission size (default: the trained pilot's stage, 3 for the expert)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--speed", type=float, default=1.0, help="playback speed (2 = twice real time)")
    ap.add_argument("--no-scan", action="store_true", help="skip the survey/scan flight before the deliveries")
    ap.add_argument("--static-water", action="store_true", help="don't animate the flood water (saves a little CPU)")
    ap.add_argument("--free-cam", action="store_true", help="start with the video's overview camera instead of following the drone")
    ap.add_argument("--device", default="auto", help="device for a trained policy: auto | cuda | cpu")
    ap.add_argument("--replay", nargs="?", const="auto", default=None,
                    help="replay recorded test flights: no value = the latest trained pilot's results/stage<k>/replay.json")
    args = ap.parse_args()
    from rl import results
    if args.replay:
        if args.replay == "auto":
            e = results.best_entry(args.stage)
            if not e or not os.path.exists(e["replay"]):
                raise SystemExit("no recorded flights in results/ yet — train first:  python train_all.py")
            args.replay = e["replay"]
        return replay(args)

    if args.policy in ("auto", "trained"):
        e = results.best_entry(args.stage)
        if e:
            args.policy = e["model"]
            args.stage = args.stage or e["stage"]
            t = e.get("test") or {}
            print(f"trained pilot: results/stage{e['stage']}/model.zip  ({e.get('algo')}, {e.get('timesteps') or 0:,} steps, "
                  f"trained on {e.get('trained_on')}; test success {t.get('success_rate', float('nan')):.0%})")
        elif args.policy == "trained":
            raise SystemExit("no trained pilot in results/ yet — train first:  python train_all.py")
        else:
            print("no trained pilot in results/ yet -> the scripted expert flies (train with: python train_all.py)")
            args.policy = "expert"
    args.stage = args.stage or 3

    xml = os.path.join(ROOT, "environment", "scene_train.xml" if args.light else "scene_flood_dynamic.xml")
    stage = dict(STAGES[args.stage])
    stage["max_steps"] = 100000 if args.policy in ("manual", "hover") else stage["max_steps"]
    env = SkyHydroDeliveryEnv(xml_path=xml, physics_dt=0.004, **stage)
    obs, info = env.reset(seed=args.seed)

    manual = None
    if args.policy == "expert":
        pilot = ExpertPilot(env); policy = pilot.act
    elif args.policy == "manual":
        manual = Manual(); policy = manual.act
    elif args.policy == "hover":
        policy = lambda o: np.array([0, 0, 0, -1], np.float32)
    elif args.policy == "random":
        policy = lambda o: env.action_space.sample()
    else:
        from stable_baselines3 import PPO, SAC
        from rl.train import pick_device
        dev = pick_device(args.device)
        print(f"pilot network running on {dev}; mission stage {args.stage}")
        try:
            model = PPO.load(args.policy, device=dev)
        except Exception:
            model = SAC.load(args.policy, device=dev)
        policy = lambda o: model.predict(o, deterministic=True)[0]

    anim = SceneAnimator(env)
    water = None
    if not args.light and not args.static_water:
        try:                                   # animated video-style flood water (environment/live_water.py)
            import sys
            sys.path.insert(0, os.path.join(ROOT, "environment"))
            from live_water import LiveWater
            water = LiveWater(env.model, os.path.dirname(env.xml_path))
            water = water if water.ok else None
        except Exception as exc:               # scenery only — never stop the sim for it
            print("live water off:", exc)
    with mujoco.viewer.launch_passive(env.model, env.data, key_callback=manual.key if manual else None) as viewer:
        viewer.cam.distance, viewer.cam.elevation, viewer.cam.azimuth = 70.0, -28.0, 110.0
        state = {"wall": time.time(), "sim": env.data.time}
        follow = {"on": not args.free_cam}
        if args.free_cam:                       # same framing as the cinematic video
            viewer.cam.lookat[:] = env.model.stat.center
            viewer.cam.distance, viewer.cam.elevation, viewer.cam.azimuth = 1.5 * env.model.stat.extent, -36.0, 106.0

        def substep(e):
            anim(e)
            # keep playback near real time and refresh the window ~60 Hz
            if e.data.time - state["sim"] >= 1 / 60:
                if water is not None:
                    water.update(viewer, e.data.time)
                if follow["on"]:
                    viewer.cam.lookat[:] = e.ctrl.pos()
                viewer.sync()
                lag = (e.data.time - state["sim"]) / args.speed - (time.time() - state["wall"])
                if lag > 0:
                    time.sleep(lag)
                state["wall"], state["sim"] = time.time(), e.data.time

        env.substep_callback = substep

        def beam(on):                           # blue scan beam under the drone (geom group 4)
            with viewer.lock():
                viewer.opt.geomgroup[4] = 1 if on else 0

        def survey():
            if args.no_scan or args.policy in ("manual", "hover"):
                return obs
            from rl.scan import Survey
            sv = Survey(env, substep, beam)
            found = sv.run(alive=viewer.is_running)
            print(f"[t={env.data.time:6.1f}s] pilot takes over: supply {len(found)} houses")
            return sv.hand_over(found)

        obs = survey()
        R = 0.0
        while viewer.is_running():
            obs, r, term, trunc, info = env.step(policy(obs))
            R += r
            if info.get("event"):
                print(f"[t={env.data.time:6.1f}s] {info['event']:>18}   delivered {info['delivered']}/{info['n_targets']}   "
                      f"return {R:.1f}")
            if term or trunc:
                print(f"episode over ({info.get('event') or 'time limit'}) — restarting in 3 s")
                t_end = time.time()
                while viewer.is_running() and time.time() - t_end < 3:
                    if water is not None:
                        water.update(viewer, env.data.time + time.time() - t_end)
                    viewer.sync(); time.sleep(0.05)
                obs, info = env.reset(); R = 0.0
                state["sim"] = env.data.time
                obs = survey()
    env.close()


if __name__ == "__main__":
    main()
