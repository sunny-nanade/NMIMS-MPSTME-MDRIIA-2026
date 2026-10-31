# Viva prep: E075 (Zaid) - geofence tiers, hysteresis, noise, breach log, statistics script

How to read this file. Every number is copied from a file named next to it, or from a script output saved in `docs/submission/viva_evidence/` (EV; regenerated on this tree on 31 Oct 2026). Where nothing was measured it says "not measured". Line numbers are for `src/aerial_patrol_swarm.py` (the E075 region, lines 943-1134), `analytics/` and `tests/` as committed on branch feat/e043-overnight-full-marks at the commit that contains this file; `python docs/submission/viva_refs_check.py` checks every reference.

AI-use statement you must say honestly (`docs/submission/viva_evidence/E075_AI_DISCLOSURE.md`): the geofence functions, the noise demo, the statistics script, the 20 tests, the breach logs and the packet files were drafted by an AI assistant under the lead's instructions, about 100 percent of the code. Git records the lead as author of the commits, so it cannot show who wrote what. You must derive the tier rule, the ray-casting test and the Welch formulas on paper, and re-run the demo, the tests and the statistics script yourself.

---------------------------------------------------------------------------------------------

## Part 1. The five standard viva questions, answered for E075

### Q1. Why that solref and friction, and what if you halved them? (E043's parameter; know the answer)

- Timestep 0.002 s (models/campus_perimeter_patrol.xml:19); friction "1.0 0.01 0.005", condim 3 (models/common.xml:66); the quad class solref "0.004 1" (models/common.xml:72). 1.0 is MuJoCo's default sliding friction; damping ratio 1 is critical damping (`docs/research/mjcf_parameter_justification.md`).
- Measured (EV `viva_contact_solref_mix.txt`, `viva_contact_halved.txt`; one 2 s rest on the dock, not a dossier result): leg-on-surface contacts use the averaged solref 0.012. Halving the leg value moves the deepest penetration from 2.416 mm to 2.124 mm; friction 0.5 or 0.1 gives 0.000 mm drift at rest. Nothing in a patrol metric responds. Landing with lateral speed was not measured, and no batch was re-run with other contact values.
- Your link: the geofence works on the horizontal footprint only (z is ignored, docstring of `evaluate_geofence_status`, src/aerial_patrol_swarm.py:1037-1051), so contact parameters never enter it. The justification file's old "silently clamped" claim was wrong and has been corrected (case E043-C in `ai_audit_candidates.md`).

### Q2. Show one FSM transition live and its line of code.

Your transition is VERIFY -> ALERT_k. Live: `mjpython src/view_live.py --scene exterior --appear 25 --rays`; the overlay shows ALERT_2 for one tick between VERIFY and TRACK. Saved headless timeline of the same controller (EV `viva_fsm_timeline.txt`, exterior, seed 4, intruder at 25 s, 10 Hz): bravo DETECT 29.10 s, VERIFY 29.21 s, ALERT_2 29.31 s, TRACK 29.41 s; the incident record says tier 2 at alert and maximum tier 3 during TRACK.
- The line: `evaluate_geofence_status` is called at src/aerial_patrol_swarm.py:1418 when VERIFY_K consistent hits are reached, and `surv_state` becomes ALERT_<tier> at src/aerial_patrol_swarm.py:1422-1423. Your function is `evaluate_geofence_status` at src/aerial_patrol_swarm.py:1037-1083; the tier from distance is `_geofence_tier_of` at src/aerial_patrol_swarm.py:1016-1023.
- During TRACK the FSM calls it again each vision tick (src/aerial_patrol_swarm.py:1443-1447) and logs a tier escalation as an event `alert:<tier>`.
- Consequence to explain: tier 3 needs 5 consecutive inside readings (`GEOFENCE_CONFIRM_N`, src/aerial_patrol_swarm.py:951, applied at src/aerial_patrol_swarm.py:1064-1065). The FSM feeds one reading at verification and one per TRACK vision tick; at the batch vision rate of 10 Hz (provenance vision_hz 10.0) that is about 0.5 s, so a breach shows as tier 2 first and as tier 3 a few ticks later, exactly what the timeline above shows. The delay in the full dataset was not measured.
- Tests: tests/test_e075_geofence_stats.py:58 `test_tiers_on_known_points`; tests/test_e075_geofence_stats.py:106 `test_tier3_dwell_rejects_a_single_inside_reading`; tests/test_e043_surveillance_fsm.py:63 `test_full_cycle_and_incident_record`.

### Q3. Which input moves payback the most, and where does its value come from?

(E077's model; you must be able to state it.) Source: `analytics/campus_security_economics_output.txt`, section TORNADO. P_payback at -30 % and +30 % of each assumed input, interior uav_offset_ring (base 0.301): replacement_fraction 0.469 and 0.221, capex_ratio 0.198 and 0.418, service_life_years 0.430 and 0.231; every other input moves P by 0.04 or less. Over the whole assumed range capex_ratio (0.2 to 1.1) is the most uncertain. Both leading inputs are ASSUMPTION ranges with the midpoint as base case (no primary source, `docs/research/sources_verified.md`). Sourced: 8 h shift (OSH Code 2020 s.25(1)(a)), 400 battery cycles (DJI Matrice 350 RTK page), 2080 h per FTE and kappa target 0.25 (course Standards Manual section 3). Payback 12.6 to 12.9 months, conditional on those ranges.
Your link: the FMEA row "false geofence alarm" takes its occurrence from the geofence ablation (analytics/ablation_trials.csv, mode geofence, 10 seeds per arm, interior, position noise on). Source `analytics/campus_security_economics_output.txt`: before (hysteresis off) O = 10 (10/10 runs with a spurious breach event, 95 % Clopper-Pearson 0.69 to 1.00), after O = 6 (1/10, 0.00 to 0.45); RPN 400 to 24; Fisher exact p = 0.000119. Residual: spurious tier escalations 12.8 to 4.0 per run and spurious breach events 7.6 to 0.1 per run, so the hysteresis lowers false escalations but does not remove them.

### Q4. Why Welch's t-test, and what does Cohen's d mean? (this is your script)

- Why Welch: very unequal spread. cycle_time_s interior guard sd 593.2051, uav_sectors sd 5.9314; exterior 141.6419 and 8.2237 (`analytics/statistical_validation_output.txt`). Pooled-variance Student t assumes equal variance. Welch uses se = sqrt(sA^2/nA + sB^2/nB) (`welch`, analytics/statistical_validation.py:137-157), t = diff / se, Welch-Satterthwaite df, two-sided p from `stats.t.sf`, 95 % CI = diff plus or minus t_crit x se; Cohen's d = diff / sqrt(((nA-1) sA^2 + (nB-1) sB^2) / (nA+nB-2)).
- Results, primary pair guard_baseline vs uav_sectors, cycle_time_s, n = 30 each, 180 rows, alpha 0.05 (same output file): interior mean difference 2403.0552 s, se 108.3093, t = 22.1870, df 29.006, p = 9.629081e-20, d = 5.7286, CI [2181.5396, 2624.5707]. Exterior mean difference 461.0857 s, t = 17.8000, df 29.196, p = 3.223302e-17, d = 4.5959, CI [408.1221, 514.0494].
- Secondary pair uav_sectors vs uav_offset_ring, cycle time: interior t = 16.7696, p = 5.897519e-19, d = 4.3299, CI [17.0921, 21.7887]; exterior t = 19.0906, p = 8.086426e-26, d = 4.9292, CI [32.4368, 40.0472]. The equal-window worst revisit is not tested (right-censored guard; see the caveats and `censored_lines`).
- Detection intervals (same file): interior guard 11/30 (Wilson [0.2187, 0.5449]), uav_sectors 10/30 ([0.1923, 0.5122]), uav_offset_ring 13/30 ([0.2738, 0.6080]); exterior 30/30 in each ([0.8865, 1.0000]).
- Caveats you must volunteer: the script treats runs as independent draws, the seeds are shared across conditions, so a paired analysis is a valid alternative and was not run (not measured); the guard windows (5000 s interior, 1800 s exterior) differ from the UAV window (300 s), so the guard's equal-window worst revisit is right-censored (>= 300 s, 30 of 30 runs had no revisit inside the window) and no t-test is run on it; every UAV cell now has 0 obstacle contacts (the exterior layer was raised to 22 m after an interim batch with roof contacts, see viva_prep_E043.md Part 0), so the exterior numbers are not comparable with earlier exterior figures; the runs are simulation.
- The script's safety gate: `load_validated` (analytics/statistical_validation.py:78-111) refuses a CSV without a provenance record, a SIMULATED_ file, a hash that differs from the provenance csv_sha256, or missing columns; test `test_refuses_simulated_and_unprovenanced_input` at tests/test_e075_geofence_stats.py:274; Welch checked against scipy by `test_welch_matches_scipy_reference` at tests/test_e075_geofence_stats.py:231.

### Q5. What did the AI get wrong, and how did you prove it?

Case E075-A (disclosed, reproduced today): the first hysteresis was an exit margin only (a tier is left only 2.0 m past its threshold). The AI expected it to cut false alarms; the demo showed it barely did. I reproduced the exit-margin-only numbers by setting `GEOFENCE_CONFIRM_N` = 1 (dwell off) and running the unmodified demo with `--no-write` (EV `viva_e075_exit_margin_only_repro.txt`, script `viva_e075_exit_margin_only_repro.py`); the full-hysteresis table is EV `viva_e075_full_hysteresis.txt` (same script with VIVA_FULL_HYSTERESIS=1). False tier-3 alarms over 100 seeds, noise on:
- Skirt path, interior: 1948 (hysteresis off), 1650 (exit margin only), 1 (exit margin plus dwell). Exterior: 1804, 1549, 1.
- Crossing path, interior: 632, 417, 3. Exterior: 603, 408, 5.
- Why: an exit margin only suppresses re-entry after a first false entry; it does nothing about the first noisy reading that crosses the line. Fix: the tier-3 dwell (5 consecutive inside readings, tier 2 shown meanwhile). No test failed; the error was found by reading the demo table. Cost: 4 extra readings before a real breach is reported as tier 3 (0.4 s at the demo's 10 Hz); a safety trade-off you must be able to argue.
Case E075-B (found by reading the output): the first statistics script compared worst_revisit_ground_s across conditions with different run windows (its default metric, `git show 32f16c9^:Group_05_Muaaz_Aditya_Zaid_Soumya/analytics/statistical_validation.py`, line 178). A maximum over a 5000 s window is not comparable with a maximum over a 300 s window. Commit 32f16c9 replaced the primary metric with cycle_time_s (mean time per completed ground lap, window-independent) and added the equal 300 s window; the old metric is now printed "context only" (`analytics/statistical_validation_output.txt`).

---------------------------------------------------------------------------------------------

## Part 2. Questions on your own code (answers with file:line)

1. What are the four tiers and where are the thresholds? `_geofence_tier_of` (src/aerial_patrol_swarm.py:1016-1023): d <= 0 gives tier 3 (inside); d <= `GEOFENCE_BUFFER_M` 5.0 gives tier 2 (src/aerial_patrol_swarm.py:948, guide value); d <= `GEOFENCE_ADVISORY_M` 15.0 gives tier 1 (src/aerial_patrol_swarm.py:949, ASSUMPTION range 10 to 25 m); else tier 0. Status strings `GEOFENCE_STATUS` (src/aerial_patrol_swarm.py:955-960).
2. How is "inside the zone" decided? Even-odd ray casting `_point_in_polygon` (src/aerial_patrol_swarm.py:980-991): count crossings of a +x ray; an edge counts if it straddles the ray's y (line 987) and the crossing is to the right (line 989). Test on a non-convex polygon: `test_ray_casting_on_a_non_convex_polygon` at tests/test_e075_geofence_stats.py:80.
3. How is the distance computed? `_dist_to_polygon_edges` (src/aerial_patrol_swarm.py:994-1005) projects the point onto each edge segment and clamps the parameter to [0, 1]; `geofence_signed_distance` (src/aerial_patrol_swarm.py:1007-1014) is negative or zero inside, positive outside.
4. Where does the polygon come from? The scene geom `substation_zone`, read by `_geofence_polygon` (src/aerial_patrol_swarm.py:962-977; any yaw is handled through the geom matrix); test `test_polygon_comes_from_scene_geom_and_none_is_clear` at tests/test_e075_geofence_stats.py:69. Interior zone: the VIP Lounge box x -21.4 to -14.0, y -3.8 to 15.4 (models/nmims_main_interior.xml:714). Exterior zone: x -30 to -12, y 24.5 to 32.5 (models/nmims_main_campus.xml:210), whose location the scene file marks ASSUMED (models/nmims_main_campus.xml:209).
5. Explain the hysteresis. In `evaluate_geofence_status` (src/aerial_patrol_swarm.py:1061-1068): the dwell counter `_geofence_streak` counts consecutive raw tier 3 readings (line 1064); until it reaches `GEOFENCE_CONFIRM_N` 5 the candidate is tier 2 (line 1065); a tier rises at once but falls only when the point is `GEOFENCE_EXIT_MARGIN_M` 2.0 m (src/aerial_patrol_swarm.py:950) beyond the threshold that entered it (line 1068). Tests: tests/test_e075_geofence_stats.py:87 `test_hysteresis_does_not_flap_on_a_boundary_hugging_path`; tests/test_e075_geofence_stats.py:99 `test_exit_margin_leaves_the_tier_only_past_the_margin`; tests/test_e075_geofence_stats.py:106 `test_tier3_dwell_rejects_a_single_inside_reading`; tests/test_e075_geofence_stats.py:116 `test_hysteresis_cuts_false_breaches_under_noise`.
6. How is noise injected and why a separate random stream? `inject_position_noise` (src/aerial_patrol_swarm.py:1089-1101): zero-mean Gaussian on x and y, sigma 1.5 m per axis (`GEOFENCE_NOISE_SIGMA_M`, src/aerial_patrol_swarm.py:953, ASSUMPTION range 0.5 to 3.0 m, not sourced); its own stream `default_rng([seed, 75])` (`reseed_geofence_noise`, src/aerial_patrol_swarm.py:1085-1087) so noise never changes the gust generator; test `test_noise_does_not_touch_the_gust_rng` at tests/test_e075_geofence_stats.py:149.
7. What is the breach log? `write_geofence_breach_log` (src/aerial_patrol_swarm.py:1103-1113) writes analytics/geofence_breach_log_<scene>.json with every tier change (timestamp, position, tier, status, escalate or de-escalate, noisy flag; built by `geofence_events` at src/aerial_patrol_swarm.py:1073-1081); schema test `test_breach_log_schema` at tests/test_e075_geofence_stats.py:159. The demo writes seed-0 events of every setting.
8. Return-to-home? `telemetry_link_ok` (src/aerial_patrol_swarm.py:1115-1121) and `return_to_home_required` (src/aerial_patrol_swarm.py:1123-1131): true once the link has been down at least `GEOFENCE_RTH_LOSS_S` 2.5 s (src/aerial_patrol_swarm.py:954, from the course brief). It is optional and is NOT called by the FSM (a grep finds only the definition), so link loss is not exercised in the dataset; the FMEA has no such row. Test `test_return_to_home_after_2_5_s_of_loss` at tests/test_e075_geofence_stats.py:182.
9. How does the statistics script protect against fake data? `load_validated` (analytics/statistical_validation.py:78-111): file must exist with a provenance record containing not_applicable, no SIMULATED_ text, csv_sha256 equal to the file hash, required columns, known scene and condition; refusal is exit code 2. Test `test_refuses_simulated_and_unprovenanced_input` at tests/test_e075_geofence_stats.py:274.
10. What does the script report beyond the t test? Detection with Wilson and exact intervals (`wilson_ci` analytics/statistical_validation.py:170-179, `exact_ci` analytics/statistical_validation.py:182-188; test `test_detection_intervals_match_scipy` at tests/test_e075_geofence_stats.py:306), mean CIs with t (`mean_ci`, analytics/statistical_validation.py:160-167), effort, tracking, clearance, separation and lap lines per cell. Interior clearance (output file): uav_sectors mean 0.8606 m (min 0.4379), uav_offset_ring 0.7972 m (min 0.3651), 0 contacts in both.
11. Why N = 30 and what are the windows? N = 30 per cell is the faculty ruling; windows are printed in the output header: guard 5000 s interior and 1800 s exterior, UAV 300 s, equal window 300 s (`windows_text`, analytics/statistical_validation.py:191-199).

## Part 3. The 30-second whiteboard

Draw the zone as a rectangle with two rings around it: 5 m (tier 2) and 15 m (tier 1). Write: distance d to the edge, negative inside. d <= 0 tier 3, <= 5 tier 2, <= 15 tier 1, else 0. Then draw a noisy path skirting 1.5 m outside: "single noisy readings cross the line, so tier 3 needs 5 consecutive inside readings, and a tier is left only 2 m past its threshold. In the demo that took false alarms on the skirt path from 1948 to 1 per 100 runs in the interior, at the price of about 0.4 s delay at 10 Hz. In the full flights it is still not zero: spurious tier escalations 12.8 down to 4.0 per run."

## Part 4. How your part connects to the system

- FSM state: your tier is the number in ALERT_<tier> (src/aerial_patrol_swarm.py:1418, src/aerial_patrol_swarm.py:1422) and in escalation events during TRACK (src/aerial_patrol_swarm.py:1443-1447); `_close_incident` resets your state with `evaluate_geofence_status` (None) at src/aerial_patrol_swarm.py:1371.
- Telemetry: the tier appears in the fsm_state text (ALERT_0 to ALERT_3) and event (alert:<k>) of the per-step telemetry; there is no CSV column for the tier in the main results file.
- Business input: the ablation behind the FMEA row "false geofence alarm" (analytics/run_ablations.py runs it with the hysteresis flag at src/aerial_patrol_swarm.py:53-54); the statistics script produces the t, df, p, d and CI quoted in the dossier.

## Part 5. Numbers you must know (verbatim, with source)

Noise demo (EV `viva_e075_full_hysteresis.txt`; sigma 1.5 m per axis ASSUMPTION; walker 1.35 m/s; 10 Hz; 100 seeds per cell; dwell 5 readings; exit margin 2.0 m). Zone corners as printed: interior (-21.40, -3.80) to (-14.00, 15.40); exterior (-30.00, 24.50) to (-12.00, 32.50).

| scene | path | noise | hysteresis | false alarms | per run | tier changes/run |
|---|---|---|---|---|---|---|
| interior | crossing | on | off | 632 | 6.320 | 75.52 |
| interior | crossing | on | on | 3 | 0.030 | 22.60 |
| interior | skirt | on | off | 1948 | 19.480 | 60.32 |
| interior | skirt | on | on | 1 | 0.010 | 4.17 |
| exterior | crossing | on | off | 603 | 6.030 | 76.95 |
| exterior | crossing | on | on | 5 | 0.050 | 22.44 |
| exterior | skirt | on | off | 1804 | 18.040 | 56.44 |
| exterior | skirt | on | on | 1 | 0.010 | 4.25 |

With noise off, false alarms are 0 in every setting. Design choices that are NOT measurements: tier 1 band 15 m (10 to 25), exit margin 2.0 m, dwell 5 readings, noise sigma 1.5 m (0.5 to 3.0), demo sampling 10 Hz, skirt offset 1.5 m. The 5 m tier-2 buffer and the 2.5 s link-loss limit come from the project brief.

Flights (EV `viva_ablation_summary.txt`, mode geofence, off vs on, 10 seeds each, interior, 90 s, noise on): escalations 30.1 vs 6.9 per run; spurious escalations 12.8 vs 4.0; breach-log events 16.0 vs 1.2; spurious breach events 7.6 vs 0.1.

Statistics (`analytics/statistical_validation_output.txt`): see Q4. Cell means of cycle_time_s: interior guard 2460.4638, uav_sectors 57.4086, uav_offset_ring 37.9682; exterior 532.9093, 71.8236, 35.5816. Equal-window worst revisit (descriptive, right-censored guard, no test): interior sectors 68.1647, offset_ring 53.8402; exterior 113.1541, 113.2678.

Tests: `python -m pytest tests/test_e075_geofence_stats.py -q` gave 20 passed; the whole suite gave 112 passed, 1 skipped (EV `viva_pytest_summary.txt`).

Known limits, one answer to give when asked "where does the geofence fail": the 1.5 m noise is an assumed value, not a measured GPS or vision error, and the demo is scripted walker paths, so the 1-in-100 figure is a model result, not a field result; in flights the hysteresis lowers but does not remove false alerts (spurious tier escalations 4.0 per run remain, 1 of 10 runs still has a spurious breach event); the dwell delays a real breach by 4 readings (0.4 s at 10 Hz); the exterior zone location is ASSUMED in the scene file; the return-to-home functions exist and are tested but the FSM never calls them, so link loss is not part of any measured result; the ablation is interior only, so the exterior FMEA geofence row reads "not measured".

## Part 6. Commands to re-run before the viva

- `python analytics/geofence_noise_demo.py --no-write` (add --seeds 100 for the full table; without --no-write it rewrites the two committed breach logs) and `python -m pytest tests/test_e075_geofence_stats.py -q`.
- `python analytics/statistical_validation.py` reads analytics/campus_patrol_real_trials.csv and its provenance JSON and rewrites analytics/statistical_validation_output.txt; use `--help` for a scratch output path before running it on a clean checkout.
- `python docs/submission/viva_evidence/viva_e075_exit_margin_only_repro.py` (exit margin only) and the same command with VIVA_FULL_HYSTERESIS=1 (production).
