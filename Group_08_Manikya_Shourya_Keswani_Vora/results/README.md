# results/ — trained RL pilots (from the lab PC run)

Copy the lab PC's `results` folder here before committing, so it contains:

```
results/registry.json
results/stage1/  model.zip  training_summary.json  replay.json
results/stage2/  model.zip  training_summary.json  replay.json
results/stage3/  model.zip  training_summary.json  replay.json
```

`python simulate.py` reads `registry.json` and lets the stage-3 pilot fly the full mission;
`python simulate.py --replay` plays the recorded test missions (no PyTorch needed).
Training (PPO, RTX 3090, CPU envs): stage 1 = 1 M steps / 57 min, stage 2 = 2 M / 163 min, stage 3 = 3 M / 103 min.
Stages 1-2 never completed a test mission (0/3 each); the pilot learned the task in stage 3.

Evaluation of the stage-3 pilot (`python analytics/evaluate_rl_pilot.py --episodes 30`,
`analytics/rl_pilot_real_trials.csv`, same seeds for both pilots, full 4-house mission):

| pilot | missions completed | mission time (s) | mean / max canister swing (deg) |
|---|---|---|---|
| RL (stage 3) | 30 / 30 | 150.2 ± 4.4 | 8.9 / 39.9 |
| scripted expert | 30 / 30 | 309.0 ± 9.6 | 2.3 / 50.2 |

Welch t-test on mission time: t = -82.8, p = 6.9e-47. The RL pilot is ~2x faster; the expert keeps
the canister steadier on average.
