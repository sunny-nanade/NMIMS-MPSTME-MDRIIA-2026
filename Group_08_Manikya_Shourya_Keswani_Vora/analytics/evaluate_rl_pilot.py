"""
Group 08 SkyHydro: evaluate the trained RL pilot (results/stage3/model.zip) on the full
valley mission against the scripted expert, same seeds for both.

  python analytics/evaluate_rl_pilot.py --episodes 30
  -> analytics/rl_pilot_real_trials.csv  (one row per mission, seed recorded)

Mission = stage 3: start anywhere over the valley, supply every house with survivors
(pick up at the hilltop warehouse, winch-drop on each roof). Physics as in training
(scene_train.xml, 0.004 s RK4, agent acts every 0.1 s).
"""
import argparse
import csv
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def run(args):
    pilot, seed, model_path = args
    from rl import STAGES
    from rl.skyhydro_env import SkyHydroDeliveryEnv
    env = SkyHydroDeliveryEnv(**STAGES[3])
    if pilot == "rl":
        from stable_baselines3 import PPO
        model = PPO.load(model_path, device="cpu")
        act = lambda o: model.predict(o, deterministic=True)[0]
    else:
        from rl.expert import ExpertPilot
        ex = ExpertPilot(env)
        act = ex.act
    obs, info = env.reset(seed=seed)
    R, swing, path = 0.0, [], 0.0
    p_prev = env.ctrl.pos()
    t_first = None
    while True:
        obs, r, term, trunc, info = env.step(act(obs))
        R += r
        swing.append(math.degrees(env._swing()))
        p = env.ctrl.pos(); path += float(np.linalg.norm(p - p_prev)); p_prev = p
        if info.get("event") == "delivered" and t_first is None:
            t_first = env.data.time
        if term or trunc:
            break
    end = info.get("event") or "time_limit"
    return dict(pilot=pilot, seed=seed, result=end, success=int(end == "mission_complete"),
                delivered=info["delivered"], targets=info["n_targets"], return_=round(R, 2),
                mission_time_s=round(env.data.time, 2), time_first_delivery_s=round(t_first, 2) if t_first else "",
                path_length_m=round(path, 1), mean_swing_deg=round(float(np.mean(swing)), 3),
                max_swing_deg=round(float(np.max(swing)), 3), steps=info["steps"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=30)
    ap.add_argument("--seed", type=int, default=5000)
    ap.add_argument("--model", default=os.path.join(ROOT, "results", "stage3", "model.zip"))
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default=os.path.join(HERE, "rl_pilot_real_trials.csv"))
    a = ap.parse_args()
    jobs = [(p, a.seed + k, a.model) for p in ("rl", "expert") for k in range(a.episodes)]
    t0 = time.time()
    rows = []
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(run, jobs):
            rows.append(r)
            print(f"{r['pilot']:6s} seed {r['seed']}  {r['result']:<18} {r['delivered']}/{r['targets']}  "
                  f"{r['mission_time_s']:6.1f} s  return {r['return_']}", flush=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    from scipy import stats
    for p in ("rl", "expert"):
        R = [r for r in rows if r["pilot"] == p]
        ok = [r for r in R if r["success"]]
        print(f"{p}: success {len(ok)}/{len(R)}, delivered {np.mean([r['delivered']/r['targets'] for r in R]):.1%}, "
              f"mission time (successful) {np.mean([r['mission_time_s'] for r in ok]) if ok else float('nan'):.1f} s")
    a_ = [r["mission_time_s"] for r in rows if r["pilot"] == "rl" and r["success"]]
    b_ = [r["mission_time_s"] for r in rows if r["pilot"] == "expert" and r["success"]]
    if len(a_) > 2 and len(b_) > 2:
        t = stats.ttest_ind(a_, b_, equal_var=False)
        print(f"mission time RL vs expert (successful missions): Welch t = {t.statistic:.2f}, p = {t.pvalue:.2e}")
    print(f"{len(rows)} missions in {time.time() - t0:.0f} s -> {a.out}")


if __name__ == "__main__":
    main()
