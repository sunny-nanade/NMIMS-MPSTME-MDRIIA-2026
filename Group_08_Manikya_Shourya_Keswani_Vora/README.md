# MDRIIA Group 08 · SkyHydro: Vision-Guided Multirotor UAV for Last-Mile Flood Relief Delivery

**Course:** Modern Day Robotics and Its Industrial Applications (MDRIIA, 702CO0E012) · B.Tech CSBS · SVKM's NMIMS MPSTME · AY 2026–27
**Team:** Manikya Rathore (E056) · Shourya Garg (E020) · Keswani Laksh (E032) · Vora Jash (E067)

> *To what extent can an autonomous vision-guided multirotor UAV simulated in MuJoCo for payload-range trade-offs optimize last-mile medical relief drop accuracy during NDRF flood operations while establishing fleet utilization payback parity against ground transport?*

The technical dossier is in [`docs/MDRIIA_Group_08_Technical_Dossier.pdf`](docs/).

## What is in this folder

| Path | What it is | Dossier |
|---|---|---|
| `models/skyhydro_flood_uav.xml` | MJCF drop-trial model: official airframe and masses, 4 rotor motors on their own sites (differential thrust + drag torque), 2-DOF cable pendulum + winch, releasable canister, rooftop target. Timestep 0.002 s (500 Hz), RK4. | §2 |
| `src/flood_relief_drop_sim.py` | Closed-loop controller: FSM `TAKEOFF → CRUISE → APPROACH_DROP_ZONE → HOVER → WINCH_LOWER → RELEASE → WINCH_UP → RETURN_TO_BASE` (+ `ABORT`), cascaded PID + geometric attitude control, wind/gust model, Monte Carlo runner, 500 Hz logger, viewer | §2, §4 |
| `analytics/flood_relief_real_trials.csv` | **Our results**: 240 MuJoCo runs (2 controllers × 4 crosswinds × 30 runs), one row per run with its seed | §4 |
| `analytics/telemetry/*.csv.gz` | 500 Hz logs (time, FSM state, pose, reference, velocity, canister, swing, cable length, wind, 4 rotor thrusts, power) | §4 |
| `analytics/analyze_trials.py` | Welch t-test, Cohen's d, 95 % CI, CEP, success rates → `trial_stats.json`, `docs/figures/fig_boxplot.png`, `fig_trajectory.png` | §4 |
| `analytics/disaster_relief_logistics.py` | CSBS model (dimensionless): H_reclaimed, κ / NCRI, P_payback, M/M/c queue, FMEA, ±30 % tornado + break-even → `business_results.json`, `fig_business_*.png` | §3 |
| `environment/`, `rl/`, `simulate.py` | Full 3D flood valley (terrain, two towns, survivors, animated flood water, debris, helicopter) and the RL pilot (PPO, Stable-Baselines3, curriculum stages 1–3) | expo demo |
| `results/stage1-3/` | Trained RL pilots (`model.zip`) + `training_summary.json` + `replay.json` | expo demo |
| `analytics/evaluate_rl_pilot.py`, `rl_pilot_real_trials.csv` | Stage-3 RL pilot vs scripted expert, 30 full missions each (same seeds): RL 30/30, 150 s vs 309 s | expo demo |
| `analytics/SIMULATED_*`, `generate_paper_figures.py`, `docs/figures/figure*.png` | Course starter files with **generated target numbers**. Not used for any result. | — |

## Run it (fresh clone)

```bash
# Windows: setup_windows.bat     Linux/macOS: ./setup_linux.sh      (venv, CUDA PyTorch, deps, builds the valley, tests)
pip install -r requirements.txt            # if you set up the environment yourself

# 1. the drop-trial model loads
python -c "import mujoco; mujoco.MjModel.from_xml_path('models/skyhydro_flood_uav.xml')"

# 2. watch one drop (FSM state shown in the viewer: text overlay + status-light colour)
python src/flood_relief_drop_sim.py --view                                # proposed controller, 10 m/s crosswind
python src/flood_relief_drop_sim.py --view --controller baseline --wind 15   # baseline misses
python src/flood_relief_drop_sim.py --view --battery-soc 0.3              # handled failure: battery-reserve ABORT

# 3. Monte Carlo trials -> statistics -> business model (re-creates every number in the dossier)
python src/flood_relief_drop_sim.py --trials 30                           # 240 runs, ~15-60 min depending on CPU
python analytics/analyze_trials.py
python analytics/disaster_relief_logistics.py

# 4. re-create the 500 Hz log of any run from its seed
python src/flood_relief_drop_sim.py --trials 30 --replay-run 137 --telemetry run137.csv

# 5. full valley + trained RL pilot (expo)
python analytics/evaluate_rl_pilot.py --episodes 30   # RL vs expert, 60 missions (~25-60 min)
sim.bat            # or: python simulate.py          (survey scan, then the trained pilot supplies the houses)
sim.bat --replay   # replay the recorded test missions from results/
train.bat          # retrain stages 1 -> 3 on the GPU (results saved to results/ automatically)
```

## Data provenance

Every number in dossier §4 comes from `analytics/flood_relief_real_trials.csv`, produced by `src/flood_relief_drop_sim.py` running MuJoCo. Every economic input in §3 is either computed from those trials or is a labelled assumption that is varied in the sensitivity graph. Nothing is taken from the `SIMULATED_*` starter files.

## Honest limits

* Wind is a quadratic-drag force with first-order Gauss–Markov gusts (Dryden-like), not CFD; rotor downwash on the canister is not modelled.
* "Vision" is a simulated downward-camera measurement of the canister relative to the marker (5 cm noise, 30 Hz). There is no image-processing model.
* In the valley demo, the survey scan is a scripted flight that reads each house's survivor count from the scene; the RL pilot learned the pickup and delivery runs, not the scan.
* Cost figures are ratios to one boat-hour; most inputs are assumptions (see `ASSUME` in the business script) and are varied ±30 %.
