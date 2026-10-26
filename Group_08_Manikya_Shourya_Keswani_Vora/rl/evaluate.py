"""
Evaluate a trained SkyHydro pilot (or the scripted expert / random baseline)
and optionally record a video.

  python -m rl.evaluate --model runs/ppo_stage3/best_model.zip --stage 3 --episodes 20
  python -m rl.evaluate --model expert --stage 3 --episodes 5
  python -m rl.evaluate --model runs/ppo_stage1/best_model.zip --stage 1 --video eval.mp4
    (headless video: set MUJOCO_GL=egl  [Linux]  before running)
"""
import argparse
from collections import Counter

import numpy as np

from rl import STAGES
from rl.skyhydro_env import SkyHydroDeliveryEnv
from rl.expert import ExpertPilot


def load_policy(spec, env, device="auto"):
    if spec == "expert":
        pilot = ExpertPilot(env)
        return lambda obs: pilot.act(obs)
    if spec == "random":
        return lambda obs: env.action_space.sample()
    from stable_baselines3 import PPO, SAC
    from rl.train import pick_device
    device = pick_device(device)
    try:
        model = PPO.load(spec, device=device)
    except Exception:
        model = SAC.load(spec, device=device)
    return lambda obs: model.predict(obs, deterministic=True)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="expert", help="path to .zip, or 'expert' / 'random'")
    ap.add_argument("--stage", type=int, choices=[1, 2, 3], default=3)
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--xml", default=None)
    ap.add_argument("--video", default=None, help="write an mp4 of the first episode")
    ap.add_argument("--device", default="auto", help="auto | cuda | cpu")
    args = ap.parse_args()

    env = SkyHydroDeliveryEnv(xml_path=args.xml, render_mode="rgb_array" if args.video else None, **STAGES[args.stage])
    policy = load_policy(args.model, env, args.device)
    rets, deliv, succ, steps, ends = [], [], 0, [], Counter()
    frames = []
    for ep in range(args.episodes):
        obs, info = env.reset(seed=args.seed + ep)
        R = 0.0
        while True:
            obs, r, term, trunc, info = env.step(policy(obs))
            R += r
            if args.video and ep == 0 and env.steps % 2 == 0:
                frames.append(env.render())
            if term or trunc:
                break
        ok = info.get("event") == "mission_complete"
        succ += ok
        rets.append(R); deliv.append(info["delivered"] / info["n_targets"]); steps.append(info["steps"])
        ends[info.get("event") or "time_limit"] += 1
        print(f"episode {ep:3d}: return {R:8.1f}  delivered {info['delivered']}/{info['n_targets']}  "
              f"steps {info['steps']:5d}  end={info.get('event') or 'time_limit'}")
    print("\n=== summary ===")
    print(f"policy: {args.model}   stage {args.stage}   episodes {args.episodes}")
    print(f"mission success rate : {succ / args.episodes:.0%}")
    print(f"deliveries completed : {np.mean(deliv):.0%} of targets on average")
    print(f"mean return          : {np.mean(rets):.1f} ± {np.std(rets):.1f}")
    print(f"mean episode length  : {np.mean(steps) * env.control_dt:.0f} s simulated")
    print(f"episode endings      : {dict(ends)}")
    if args.video and frames:
        import imageio
        imageio.mimsave(args.video, frames, fps=10)      # one frame per 0.2 s simulated -> 2x speed
        print("video ->", args.video)
    env.close()


if __name__ == "__main__":
    main()
