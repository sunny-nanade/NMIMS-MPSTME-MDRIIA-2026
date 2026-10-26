"""
train_all.py — train the RL pilot through the whole curriculum on the GPU,
one command. Each stage starts from the previous stage's pilot, and every
stage's result is saved automatically to results/stage<k>/ (model.zip,
training_summary.json, replay.json) + results/registry.json.

  python train_all.py                    # stages 1 -> 2 -> 3 (full run)
  python train_all.py --stages 2 3       # resume from stage 2 (uses results/stage1)
  python train_all.py --quick            # ~5 min pipeline check (tiny budgets, not a real pilot)
  python train_all.py --scale 2          # 2x the timesteps of every stage

Then:  python simulate.py               (the trained pilot flies the mission)
       python simulate.py --replay      (replay the recorded test flights)
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))

#            timesteps   extra args
PLAN = {1: (1_000_000, ["--bc-episodes", "40"]),
        2: (2_000_000, ["--init", "auto"]),
        3: (3_000_000, ["--init", "auto"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", type=int, nargs="+", default=[1, 2, 3], choices=[1, 2, 3])
    ap.add_argument("--algo", choices=["ppo", "sac"], default="ppo")
    ap.add_argument("--scale", type=float, default=1.0, help="multiply every stage's timesteps")
    ap.add_argument("--n-envs", type=int, default=None)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--quick", action="store_true", help="tiny budgets to check the whole pipeline end to end")
    args = ap.parse_args()

    t_all = time.time()
    for st in sorted(args.stages):
        steps, extra = PLAN[st]
        steps = int(steps * args.scale)
        if args.quick:
            steps, extra = 20_000, (["--bc-episodes", "3"] if st == 1 else extra)
        cmd = [sys.executable, "-m", "rl.train", "--algo", args.algo, "--stage", str(st),
               "--timesteps", str(steps), "--device", args.device, *extra]
        if args.n_envs:
            cmd += ["--n-envs", str(args.n_envs)]
        print(f"\n======== stage {st}: {steps:,} steps ========\n$ {' '.join(cmd)}", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            sys.exit(f"stage {st} failed (exit {r.returncode}) — fix it and resume with: python train_all.py --stages "
                     + " ".join(str(s) for s in sorted(args.stages) if s >= st))
        print(f"stage {st} done in {(time.time() - t0) / 60:.1f} min -> results/stage{st}/", flush=True)
    print(f"\nall done in {(time.time() - t_all) / 60:.1f} min.  Results: results/registry.json\n"
          f"watch the trained pilot:   python simulate.py\n"
          f"replay the test flights:   python simulate.py --replay")


if __name__ == "__main__":
    main()
