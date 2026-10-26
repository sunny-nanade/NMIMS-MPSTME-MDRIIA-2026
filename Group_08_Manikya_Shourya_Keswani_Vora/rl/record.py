"""
Record what a trained pilot does into a JSON file, so it can be replayed
later in the 3D viewer WITHOUT the model, PyTorch or retraining:

  python -m rl.record --model runs/ppo_stage3/best_model.zip --stage 3 --episodes 3
      -> runs/ppo_stage3/replay.json
  python simulate.py --replay runs/ppo_stage3/replay.json

The JSON holds, per episode: the flight (drone position + orientation, cable
swing, whether the canister is on the hook) sampled 30x per simulated second,
every event (pickup / delivered / crash ...) with its time, the reward and
the result. It is plain JSON, so it can also go into the report / plots.
"""
import argparse
import datetime
import json
import os

import numpy as np
import mujoco

from rl import STAGES
from rl.skyhydro_env import SkyHydroDeliveryEnv

FPS = 30


def record(make_policy, policy_name, stage=3, episodes=1, seed=12345, xml=None, out=None, extra=None):
    env = SkyHydroDeliveryEnv(xml_path=xml, **STAGES[stage])
    policy = make_policy(env)                         # make_policy(env) -> callable(obs) -> action
    m = env.model
    jq = lambda n: int(m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)])
    q_root, q_cable = jq("uav_root_joint"), env.cable_q
    eps = []
    for ep in range(episodes):
        obs, info = env.reset(seed=seed + ep)
        frames, events, nxt = [], [], [0.0]

        def grab(e):
            if e.data.time + 1e-9 >= nxt[0]:
                nxt[0] += 1.0 / FPS
                q = e.data.qpos
                frames.append([round(float(v), 4) for v in (*q[q_root:q_root + 7], q[q_cable[0]], q[q_cable[1]])]
                              + [1 if e.carrying else 0])
        env.substep_callback = grab
        grab(env)
        R = 0.0
        while True:
            obs, r, term, trunc, info = env.step(policy(obs))
            R += r
            if info.get("event"):
                events.append({"t": round(float(env.data.time), 2), "event": info["event"],
                               "delivered": info["delivered"], "of": info["n_targets"]})
            if term or trunc:
                break
        end = info.get("event") or "time_limit"
        eps.append({"episode": ep, "seed": seed + ep, "result": end, "success": end == "mission_complete",
                    "delivered": info["delivered"], "targets": info["n_targets"], "return": round(R, 2),
                    "duration_s": round(float(env.data.time), 2), "events": events, "frames": frames})
        print(f"episode {ep}: {end:>18}  delivered {info['delivered']}/{info['n_targets']}  return {R:7.1f}  "
              f"{env.data.time:5.0f} s  ({len(frames)} frames)")
    env.close()
    doc = {
        "format": "skyhydro-replay-v1",
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "policy": policy_name, "stage": stage, "fps": FPS,
        "frame_fields": ["x", "y", "z", "qw", "qx", "qy", "qz", "cable_pitch", "cable_roll", "carrying"],
        "summary": {"episodes": len(eps), "success_rate": sum(e["success"] for e in eps) / len(eps),
                    "mean_return": round(float(np.mean([e["return"] for e in eps])), 2),
                    "mean_delivered_fraction": round(float(np.mean([e["delivered"] / e["targets"] for e in eps])), 3)},
        **(extra or {}),
        "episodes": eps,
    }
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f:
            json.dump(doc, f, separators=(",", ":"))
        print(f"replay -> {out}   (watch it: python simulate.py --replay {out})")
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="path to a trained .zip, or 'expert'")
    ap.add_argument("--stage", type=int, choices=[1, 2, 3], default=3)
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--xml", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default=None, help="default: replay.json next to the model")
    args = ap.parse_args()
    from rl.evaluate import load_policy
    out = args.out or (os.path.join(os.path.dirname(os.path.abspath(args.model)), "replay.json")
                       if args.model != "expert" else "runs/expert_replay.json")
    record(lambda env: load_policy(args.model, env, args.device), args.model, args.stage, args.episodes, args.seed, args.xml, out)


if __name__ == "__main__":
    main()
