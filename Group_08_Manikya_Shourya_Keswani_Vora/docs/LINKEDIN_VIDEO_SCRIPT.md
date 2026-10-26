# LinkedIn video script (3:00–4:00, no slides) — Group 08 SkyHydro

Record on Teams/Zoom/Meet with screen share + every member's webcam on. Upload natively on LinkedIn,
tag all 4 members, MPSTME and Dr. Sunny Nanade, link the repo folder. No SAP IDs, no phone numbers.
Numbers below are from `analytics/trial_stats.json` and `analytics/business_results.json`.

| Time | Who | On screen | Say (roughly) |
|---|---|---|---|
| 0:00–0:20 | Manikya | webcam | "Floods affect about 3.2 crore people in India every year on average (CWC, 1953–2016). Urgent medicines often wait for a boat. We asked: can a vision-guided UAV drop them accurately in crosswind, and does a small fleet pay back against boats?" |
| 0:20–1:00 | Manikya | `python simulate.py` (valley) + webcam | flooded valley, survey scan with the blue beam, the trained RL pilot picks up at the warehouse and delivers to a roof. Say: "our PPO pilot completed 30/30 full missions, twice as fast as our scripted expert (150 s vs 309 s)" |
| 1:00–1:40 | Shourya + Keswani | `python src/flood_relief_drop_sim.py --view --wind 10` then `--controller baseline --wind 15` | point at the FSM text / light: TAKEOFF → CRUISE → APPROACH → HOVER → WINCH_LOWER → RELEASE; show the baseline missing into the water; show `--battery-soc 0.3` ABORT (handled failure) |
| 1:40–2:20 | Keswani | `docs/figures/fig_boxplot.png`, `fig_trajectory.png` | "240 MuJoCo runs, 500 Hz logs. Radial drop error 2.82 m baseline vs 0.31 m proposed, Welch t = 7.35, p = 4e-11, Cohen's d = 0.98. Unsafe drops 34 % → 0.8 %; at 15 m/s light canisters are aborted, not dropped blind." |
| 2:20–3:00 | Jash | `fig_business_sensitivity.png`, `fig_business_queue.png`, `fig_business_tornado.png` | "Costs as ratios to one boat-hour: κ = 0.036, NCRI = 0.96, P_payback = 0.08; M/M/2 wait 23 min vs 155 min for 4 boats. Most uncertain input is UAV CapEx — payback breaks even at 3,644 boat-hours per UAV. Top FMEA risk: swing in crosswind, RPN 280 → 48." |
| 3:00–3:45 | all four | webcams | each: what I built, what I learned, one thing AI got wrong (see dossier §5.1: OOM workers, GPU speed claim, unstable centring loop) |

## Post text

Flood relief drop error cut from 2.8 m to 0.3 m in 240 MuJoCo trials.
Our MDRIIA capstone team (B.Tech CSBS, SVKM's NMIMS MPSTME) asked: "To what extent can an autonomous vision-guided multirotor UAV simulated in MuJoCo for payload-range trade-offs optimize last-mile medical relief drop accuracy during NDRF flood operations while establishing fleet utilization payback parity against ground transport?"
We modelled a winch quadrotor in DeepMind MuJoCo with a cascaded-PID + vision-guided release controller and ran 240 Monte Carlo trials across 0–15 m/s crosswinds: drop error 2.82 → 0.31 m (Welch p < 0.001), path RMSE 0.70 m. Business case: P_payback 0.08, NCRI 0.96 (assumption-based, sensitivity in the repo).
What we learned: AI sped us up but got things wrong — it claimed GPU training would be faster; MuJoCo on the CPU was the real bottleneck.
Code: https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026/tree/main/Group_08_Manikya_Shourya_Keswani_Vora   Team: @… @… @…   Guided by @Sunny Nanade
#Robotics #MuJoCo #CSBS #TCS #MPSTME #NMIMS
