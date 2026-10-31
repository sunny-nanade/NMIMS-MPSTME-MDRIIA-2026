# AI-audit candidates for the dossier sections 5.1 and 6 and for viva question 5

Purpose: the cases where an AI assistant (or an AI-drafted file) was wrong, each with proof you can open. Rule used: a case is listed only if there is a commit, a saved test or script output, or a file and line that shows the error. Authorship is stated separately, because git records Muaaz as the author of every commit on the E043 branch and cannot tell AI-drafted text from hand-written text; the statement that a file was AI-drafted comes from the AI-use declaration (dossier sections 5.1 and 6; the per-member disclosures are saved as `docs/submission/viva_evidence/E051_AI_DISCLOSURE.md`, `E075_AI_DISCLOSURE.md` and `E077_AI_DISCLOSURE.md`), not from git. Saved outputs are in `docs/submission/viva_evidence/` (EV) and were regenerated on this tree on 31 Oct 2026. Evidence that exists only as a commit message or a recorded output is labelled as such. Run `python docs/submission/viva_refs_check.py` to check every line reference in this file.

## Summary: cases per member

| Member | Case | Proof | Attribution status |
|---|---|---|---|
| E043 Muaaz | E043-A ownership gate matched nothing | commit 40a811f; EV `viva_gate_old_vs_fixed.txt` | the original gate is in the initial commit c3fdea7; AI drafting is covered by the declaration, git cannot show it |
| E043 Muaaz | E043-B APF alone does not hold 2.5 m | `tests/test_e043_separation.py:116`; EV `viva_sep_current.txt` | the 2.5 m guarantee is the course guide's wording in the scaffold docstring; AI implemented it as written |
| E043 Muaaz | E043-C solref "silently clamped" claim is wrong | EV `viva_contact_solref_mix.txt` | AI-drafted document; found during viva preparation; corrected in the file |
| E043 Muaaz | E043-D shared waypoint arrays put Bravo's layer on Alpha's route | commit 6602371; test at `tests/test_e043_separation.py:129` | AI-drafted controller (declaration); commit message states the cause |
| E043 Muaaz | E043-E eight horizontal beams let a thin trunk through | commit 4034619; test at `tests/test_e043_obstacle_perception.py:250` | AI-drafted controller (declaration); numbers from the commit message |
| E043 Muaaz | E043-F separation governor lost its back-off next to a wall | commit 63c2178; `analytics/ablation_trials.csv:20` | AI-drafted controller (declaration) |
| E043 Muaaz | E043-G exterior patrol layer 20 m sat 0.8 m above a 19.2 m roof | commits 626b71f (fix) and 8085b85 (test) | AI-drafted scene generator and controller (declaration); cause read from the recorded contact bodies and times in the commit message |
| E051 Aditya | E051-A saturation floor too loose | EV `viva_e051_satfrac_repro.txt` (reproduced) | stated by the AI in the E051 disclosure |
| E051 Aditya | E051-B detector blind at twilight, then fixed by a gain that re-exposes the lounge floor | `analytics/vision_illumination_summary.txt`; EV `viva_e051_twilight_failing_frames.txt` | measured weakness of an AI-drafted detector; the cause of the remaining misses is read from frame numbers |
| E075 Zaid | E075-A exit-margin-only hysteresis barely cut false alarms | EV `viva_e075_exit_margin_only_repro.txt` (reproduced) | stated by the AI in the E075 disclosure |
| E075 Zaid | E075-B first statistics compared window-dependent maxima | `git show 32f16c9^` (default metric); commit 32f16c9 | AI-drafted script (declaration); shown by git |
| E077 Soumya | E077-A tests failed on the AI's own text | recorded pytest output in the E077 disclosure | stated by the AI; not re-runnable |
| E077 Soumya | E077-B old economics file computed from typed-in constants | `git show main:...campus_security_economics.py`; EV `viva_e077_old_economics_main.txt` | initial-commit file; authorship not recorded; the replacement is AI-drafted (declaration) |
| E077 Soumya | E077-C FMEA loader written against a guessed ablation schema | commit 727a1bf (diff) | AI-drafted script (declaration); shown by the diff |

Resolved defect: the interim main batch at commit 63c2178 had exterior uav_offset_ring obstacle contacts in 5 of 30 runs (seeds 7, 13, 19, 21, 22) and one run with 0 Alpha laps. It was diagnosed (Alpha against the 19.2 m roof of `bldg_791070237_0` at about 92 s) and fixed by raising the exterior layer to 22 m (commit 626b71f), tested by commit 8085b85, and the rerun batch has 0 obstacle contacts in all 120 UAV runs (`docs/submission/viva_evidence/viva_batch_validation.txt`, `analytics/campus_security_economics_output.txt` section DATA QUALITY). Case E043-G below.

Not AI errors:
- The dossier template says "9 actuators (2 x 4 rotors + 1)". It is the faculty template. Commit 6a4dab5 says the .docx was copied unmodified from the course monorepo, so no group agent wrote the sentence. The model has 8 rotor actuators (nu = 8 in both scenes, EV `viva_hover_numbers.txt`; the actuator block of `models/uav_fleet.xml`, `docs/DOSSIER_FILL_SHEET.md` records the correction, which is made in the draft only).
- Scope or specification changes, not wrong AI output: the exterior ring 3 m outside the boundary wall (moved inside by commit 8803f8d after the faculty ruling that all patrolling is inside the college; proof `tests/test_e043_exterior_route_inside_campus.py:67` `test_every_checkpoint_inside_the_boundary_wall`); the "45 -> 8.5 min" scaffold text (`docs/research/sources_verified.md`, verdict Delete: course scaffold text with no source).

---------------------------------------------------------------------------------------------

## E043-A: the region-ownership gate matched nothing

- Claim: `src/check_region_ownership.py` is meant to stop one member editing another member's lines in the shared file.
- What was wrong: git reports repository-root paths (Group_05_.../src/...) while the ownership globs and the region filename assumed group-folder paths, so no glob matched and no region was found; every change was attributed to E043; and the per-line diff of `src/aerial_patrol_swarm.py` came back empty because of a cwd-relative pathspec.
- Proof 1: fix commit 40a811f, whose message states both causes ("no FILE_OWNERS glob and not the region file ever matched ... the per-line diff ... came back empty").
- Proof 2 (EV `viva_gate_old_vs_fixed.txt`, from the group folder with author E051 against main): the old gate (parent of 40a811f) printed "[BLOCKED] 48 change(s)", all whole files, with `src/aerial_patrol_swarm.py` as one whole-file line; the fixed gate printed per-line entries for that file (22 shown, "... and 653 more", 713 violations in total). With author E043 the fixed gate prints "[OK] all 48 changed file(s) are within E043's ownership."
- Reproduce: `git show 40a811f^:Group_05_Muaaz_Aditya_Zaid_Soumya/src/check_region_ownership.py > <scratch>/old_gate.py`, then run it and the current file from the group folder with the same arguments.
- What to say: the AI-written checker looked correct and printed OK for the author who owned everything; it only failed when asked to separate authors. I found out by running it for a teammate's patch and getting nothing per line.

## E043-B: APF alone does not keep the UAVs 2.5 m apart

- Claim in the scaffold: the docstring of `compute_apf_separation` (src/aerial_patrol_swarm.py:360-366) says to "guarantee minimum separation distance d >= 2.5 m".
- What was wrong: in a head-on pass at 6 m/s each, the guide's APF alone lets the centres come within the airframe span. Code comment at src/aerial_patrol_swarm.py:161-168 (`K_REP` block) records it.
- Proof: `test_apf_alone_does_not_hold_separation` (tests/test_e043_separation.py:116) asserts APF alone breaks d >= 2.5 m; `test_layered_separation_holds_and_pair_passes` (tests/test_e043_separation.py:121) asserts the layered version holds 2.5 m, the pair passes and 0 UAV-UAV contacts. Current output of `python tests/test_e043_separation.py` (EV `viva_sep_current.txt`): APF only 0.43 m CONTACT, layered 7.12 m, pair passed True (exterior ring east leg, 60 m span, 6 m/s each).
- The brief's earlier figures (0.40 m, then 0.42 m and 3.29 m from older code) are not current; quote the saved output.
- Attribution: the 2.5 m guarantee is the course guide's text carried in the scaffold. The AI implemented it as written; the error caught was the assumption, by measurement. Say "the specification was wrong and I proved it".
- Limit: layered separation is proved in this head-on test and by min_inter_uav_m of at least 3.053 m in all 120 UAV runs of the batch with 0 UAV-UAV contacts (EV `viva_batch_validation.txt`). The separation ablation is interior only: APF only gave min_inter_uav_m 2.158 m mean, 6 of 10 runs below 2.5 m and 16 contacts; layered gave 4.157 m, 0 of 10 and 0 (EV `viva_ablation_summary.txt`).

## E043-C: "silently clamped" claim in the contact-parameter justification

- Claim (in the file before correction): `docs/research/mjcf_parameter_justification.md` said solref 0.004 s equals exactly 2 x the 0.002 s timestep, so the leg contact is "used as written", whereas at the earlier 0.004 s timestep MuJoCo "silently clamped it".
- What is wrong: a leg-on-surface contact does not use 0.004. MuJoCo mixes the two geoms' solref (equal solmix): leg 0.004 with the building or ground default 0.02 gives 0.012. That is above 2 x timestep at both 0.002 s (0.004) and 0.004 s (0.008), so no clamp acted on these contacts at either timestep. The quoted rule (time constant at least 2 x timestep, refsafe) is real MuJoCo behaviour, but the document applied it to the wrong number.
- Proof: EV `viva_contact_solref_mix.txt`, for example "contact ('alpha_leg0', 'nmims_main_collision') geom solref [0.004, 1.0] / [0.02, 1.0] ... contact solref used [0.012, 1.0]" in the exterior scene and "('ground', 'alpha_leg0') ... [0.012, 1.0]" in the interior scene. Companion EV `viva_contact_halved.txt`: leg solref 0.002 gives deepest contact 2.124 mm against 2.416 mm shipped.
- Status: corrected in the file (it now says the contact uses 0.012 s and that no clamp acted at either timestep). The earlier wording survives only in git history. One sentence in that file still quotes an older head-on result (3.29 m); the current figure is 7.12 m (E043-B).
- What to say: the AI wrote a confident explanation of the contact parameter from the manual; I checked it by printing the contact's solref and it was wrong.

## E043-D: the altitude layer was added to the wrong UAV

- Claim: Bravo flies 4 m above Alpha in the exterior so the pair is separated by altitude.
- What was wrong: the two routes shared point arrays (in offset_ring both UAVs held the same loop objects; an out-and-back route holds each inner point twice), so an in-place addition of Bravo's layer also raised Alpha's points; in the exterior offset_ring both UAVs flew at 24 m, and a TRACK / RETURN_TO_PATROL encounter reached 2.35 m in main batch run exterior_uav_offset_ring_s4.
- Proof: commit 6602371 (its message states the cause and the 2.35 m run); the regression test `test_altitude_layer_is_per_uav_in_every_policy` at tests/test_e043_separation.py:129 checks that every waypoint of each UAV sits at the ring altitude plus its own layer, exactly once, and that no route shares arrays; the explanation sits in the comment inside `_build_routes` (src/aerial_patrol_swarm.py:296-333). Current routes: Alpha exterior at 22.0 m, Bravo at 26.0 m (read by building the controller for both policies; the interior routes are at 2.4 m for both UAVs, except Bravo's sectors atrium sweep, 5.4 to 34.2 m).
- Limit: the batch run that found it (s4) is not in the committed data any more (the batch was re-run); the 2.35 m figure rests on the commit message. The next batch after this fix showed the roof contacts of case E043-G; that defect is fixed and the rerun batch has 0 contacts, so the exterior offset_ring may be described as clean in that sense.

## E043-E: eight horizontal beams let a thin trunk through

- Claim: the FR-18 range ring senses all obstacles.
- What was wrong: the 8 horizontal beams at 45 degrees left 0.77 m gaps at 1 m range; forced TRACK diversions past the six atrium trees touched a 0.24 m trunk in 92 of 300 cases.
- Proof: commit 4034619 (message gives 92 of 300 before and 0 of 300 after); the fix is the levelled 120-beam planar scan (`N_SCAN` at src/aerial_patrol_swarm.py:184) plus the swept-tube layer (`_avoid_obstacles`, src/aerial_patrol_swarm.py:481-537); the every-tree test is `test_track_diversions_past_every_atrium_tree_have_no_contacts` at tests/test_e043_obstacle_perception.py:250.
- Limit: the 92-of-300 figure comes from the commit message; the old code is only in git history. The FR-18 ablation in the batch shows 0 contacts in both arms (EV `viva_ablation_summary.txt`), so the batch itself does not demonstrate FR-18; the tests do.

## E043-F: the separation governor lost its back-off next to a wall

- What was wrong: when a UAV's FR-18 layer cancelled its back-off beside a wall, its measured speed toward the other UAV exceeded its half of the closing allowance and the pair closed to 2.43 m in the interior offset_ring separation ablation, seed 9 (production arm).
- Proof: commit 63c2178 (message: 2.43 m before, 2.79 m after); the rule is the shortfall block (variable `v_other`, src/aerial_patrol_swarm.py:676-684); the committed ablation row for that run is analytics/ablation_trials.csv:20 (interior_uav_offset_ring_s9_abl_separation_on, min_inter_uav_m 2.7903).
- Limit: the 2.43 m figure is from the commit message; the committed CSV only has the fixed run.

## E043-G: the exterior patrol layer was too low for one roof

- Claim: the exterior layer at 20 m (Bravo 24 m) clears the campus, and avoidance plus separation keep the UAVs off every obstacle.
- What was wrong: at 20 m Alpha sat 0.8 m above the 19.2 m roof of `bldg_791070237_0`, whose south edge is 1.6 m north of leg `patrol_cp6 -> cp7`. Catching up on Bravo 4 m above, the separation governor pushed Alpha down and sidestepped it right (north) into the roof edge: every exterior offset_ring contact of the interim batch (seeds 7, 13, 19, 21, 22) is Alpha against that building at about 92 s, contact z 18.98 to 19.2 m; seed 7 was left resting on the roof with 0 laps (message of commit 626b71f). The roof height is from mesh vertices; 20.9 m is the geom bounding box.
- Proof: commit 626b71f (message and the comment at models/scene_source/build_nmims_scene.py:59-64) raises `ROUTE_ALT` to 22 m; test `test_every_route_leg_clears_every_roof_within_sidestep_reach` (tests/test_e043_exterior_route_inside_campus.py:232, commit 8085b85) prints a smallest clearance of 2.80 m at 22 m (`python -m pytest -s tests/test_e043_exterior_route_inside_campus.py`), so 2 m lower, at the old 20 m layer, it was 2.80 - 2.0 = 0.80 m, below the 0.95 m margin, and the test fails there; the rerun batch has 0 obstacle contacts in all 120 UAV runs (EV `viva_batch_validation.txt`).
- Limit: the interim batch's telemetry is not committed, so the diagnosis rests on the commit message; the fix moves every exterior number (do not quote any exterior figure from before commit 8085b85).

## E051-A: the saturation floor was too loose

- Source: `docs/submission/viva_evidence/E051_AI_DISCLOSURE.md` ("One real AI error from this drafting").
- What was wrong: S_min = 0.66 x 226 = 149 let the terracotta VIP Lounge carpet (RGB 186, 91, 66; HSV 6, 165, 186) merge with the intruder blob; detector boxes as large as (160, 62, 640, 475) against ground truth (288, 62, 352, 249). Fixed to 0.75 x 226 = 169 (`HSV_SAT_FRAC` at src/aerial_patrol_swarm.py:795, used by `_hsv_bands` at src/aerial_patrol_swarm.py:816-826).
- Proof (reproduced on this tree on the same 58 interior noon frames, nothing written; EV `viva_e051_satfrac_repro.txt`): HSV_SAT_FRAC 0.66 gives mean IoU 0.874, hit rate 0.862, worst frame IoU 0.000; 0.75 gives mean IoU 0.985, hit rate 1.000, worst frame IoU 0.939. These equal the disclosed figures.
- Limits: the threshold was tuned on the frames the benchmark reports (in-sample). Smaller recorded AI error: a hand-over test that could not fail because the seeing UAV was also the closer one; rewritten before the packet (the test at tests/test_e051_vision.py:205 now places the seeing UAV farther away).

## E051-B: blind at twilight, then the gain brought the lounge floor back

- What was wrong: with the fixed V floor of 40 the detector found nothing at 0.15 x light in the interior (hit rate 0.000, detection rate 0.000) and little outdoors (exterior twilight hit rate 0.230). A value-channel gain (`AE_TARGET_V` and `detect_intruder_hsv`, src/aerial_patrol_swarm.py:839-844) fixed detection (interior twilight detection rate 1.000; exterior hit rate 0.990).
- Proof: `analytics/vision_illumination_summary.txt` section AUTO-EXPOSURE ABLATION (gain off) against the production table above it; commit 616c2e6; the batch ablation twilight off arm detected 0 of 10 runs and the on arm 6 of 10 (EV `viva_ablation_summary.txt`).
- Remaining error: the production interior twilight hit rate is 0.862, not 1.000: 8 of 58 frames have IoU below 0.5, frames 55 to 63, the VIP Lounge stretch of E051-A (EV `viva_e051_twilight_failing_frames.txt`). That the cause is the same floor confusion is a reading of the frame numbers; the pixels were not inspected. The summary's brightness sweep shows the same 0.862 at every scale from 0.70 to 0.10.

## E075-A: exit margin alone barely reduced false alarms

- Source: `docs/submission/viva_evidence/E075_AI_DISCLOSURE.md`.
- What was wrong: the first hysteresis design was an exit margin only; the AI expected it to cut false alarms.
- Proof (reproduced on this tree by setting `GEOFENCE_CONFIRM_N` to 1, which turns the tier-3 dwell off, in the unmodified demo with --no-write; EV `viva_e075_exit_margin_only_repro.txt`; the production table is EV `viva_e075_full_hysteresis.txt`): false tier-3 alarms over 100 seeds, noise on. Skirt path: interior 1948 (hysteresis off), 1650 (exit margin only), 1 (production); exterior 1804, 1549, 1. Crossing path: interior 632, 417, 3; exterior 603, 408, 5.
- Fix and cost: the tier-3 dwell of 5 consecutive inside readings (`GEOFENCE_CONFIRM_N` at src/aerial_patrol_swarm.py:951, applied in `evaluate_geofence_status`, src/aerial_patrol_swarm.py:1037-1083, dwell lines 1064-1065). Cost: 4 more readings before a true breach is tier 3 (0.4 s at 10 Hz). No test failed; the error was found by reading the demo table.
- Limit: in full flights the hysteresis lowers false breach events from 7.6 to 0.1 per run but spurious tier escalations only from 12.8 to 4.0 per run (EV `viva_ablation_summary.txt`).

## E075-B: the first statistics compared window-dependent maxima

- What was wrong: the first statistics script's default metric was worst_revisit_ground_s, the longest gap inside each run's own window (guard 5000 s interior and 1800 s exterior, UAV 500 s at that time). A maximum over a long window is not comparable with a maximum over a short one, so a very small p value for it said little.
- Proof: `git show 32f16c9^:Group_05_Muaaz_Aditya_Zaid_Soumya/analytics/statistical_validation.py` (line 178: `--metric` default worst_revisit_ground_s; PRIMARY pair on that metric); commit 32f16c9 replaced the primary metric with cycle_time_s (mean time per completed ground lap, window-independent), added the equal 300 s window and now prints the old metric as "Context only (window-dependent, never a cross-condition comparison)" in `analytics/statistical_validation_output.txt`.
- Limit: the guard's equal-window worst revisit is right-censored at the 300 s window (30 of 30 guard runs per scene had no revisit inside it, `analytics/statistical_validation_output.txt`), so no t-test, d or CI is computed on that metric for any pair; it is reported descriptively and cycle_time_s stays the primary metric.

## E077-A: the tests failed on the AI's own text

- Source: `docs/submission/viva_evidence/E077_AI_DISCLOSURE.md`; the recorded output is two failing assertions, then all tests passing (35 in the file at that time; the file now has 30 tests after later rewrites):
  - a no-money test scanned this module's own source for forbidden words and matched the file that enforces it (the AI had put the forbidden word into two test names and a comment);
  - a numeric-literal scan flagged the number 78 used six times as a print width (`numeric literals outside the input tables ... [78]`).
- Near miss: the first capex range ended at 1.2, one of the eight deleted constants; changed to 1.1.
- Limit: the failing versions no longer exist, so this case rests on the recorded output in the disclosure, not on a re-run. State that.

## E077-B: the old economics file was computed from typed-in constants

- File: `analytics/campus_security_economics.py` on main (`git show main:Group_05_Muaaz_Aditya_Zaid_Soumya/analytics/campus_security_economics.py`; saved in EV `viva_e077_old_economics_main.txt`). Lines 13-14: t_guard_patrol_min = 48.72, t_dual_uav_patrol_min = 7.84; lines 21-22: 72.0, 50.4; line 28: c_hybrid = 0.66; line 31: k_capex_normalized = 0.31; lines 36-37: 35.8, 1.2. Its header claims a dimensionless formulation, yet the printed "results" are arithmetic on these constants.
- Proof the replacement is clean: it reads the hashed CSV and exits without it (`test_csv_is_the_recorded_real_trials_file` at tests/test_e077_economics.py:102 and `test_provenance_hash_check_fails_loudly` at tests/test_e077_economics.py:111); every input is sourced or a labelled ASSUMPTION range (`test_every_input_is_sourced_or_a_labelled_assumption_range` at tests/test_e077_economics.py:139). The numbers are in `analytics/campus_security_economics_output.txt`.
- Attribution: this file is in the initial commit; git does not show who or what wrote it. Say "scaffold-era file with typed-in results; replaced". Claim AI authorship only if your own record says so.

## E077-C: the FMEA loader was written against a guessed schema

- What was wrong: the FMEA loader (commit fe31560) was written before the ablation CSV existed and guessed its names: modes obstacle_avoidance, geofence_hysteresis, twilight_exposure and a column spurious_escalations. The runner writes fr18, geofence, twilight and geofence_spurious_breaches, so on the real file the loader would have exited with "unknown mode". A first failure metric for the geofence row, spurious tier escalations, is non-zero in every run of both arms (minimum 7 off and 2 on in EV `viva_ablation_summary.txt`), so it gave 10 of 10 failing runs in both arms and an identical RPN.
- Proof: commit 727a1bf (`git show 727a1bf -- Group_05_Muaaz_Aditya_Zaid_Soumya/analytics/campus_security_fmea.py` lists every renamed mode and the new `GEOFENCE_COLUMNS`, analytics/campus_security_fmea.py:153); `ABLATION_MODES` (analytics/campus_security_fmea.py:171-186) now matches the runner; the residual escalations are printed next to the row by `geofence_residual` (analytics/campus_security_fmea.py:303-313) and appear in `analytics/campus_security_economics_output.txt` ("spurious tier escalations 12.8 -> 4.0").
- Limit: the discovery came when the figure script failed against the real CSV ("unknown mode"), reported by the agent that ran it; the diff is the durable evidence.

## E077 branch note (a defect, not claimed as an AI error)

The remote branch `origin/feat/e077-guardian-live-surveillance-upgrade` contains files with a currency field set to a three-letter code: integrations/guardian_runtime/configs/economics.example.json (line 2) and integrations/guardian_runtime/evidence/final/economics_assumptions.json (lines 3 and 40), found with `git grep -n -i -w` on that ref. The project rule is no monetary unit anywhere. That runtime is not imported by this project and must not be copied into the submission. Who or what wrote it is not recorded; do not call it an AI error unless the member confirms.

## How to use these in the viva

- E043: lead with E043-D (commit 6602371 and its test), then E043-A (commit 40a811f) or E043-C (you found it by checking the manual claim against a printed value). Add E043-G (the roof contact, found by a batch check and fixed) as the second story: it shows the batch check doing its job.
- E051: E051-A with the reproduced 0.874 -> 0.985 and the in-sample caveat; E051-B for the twilight story and the 8 remaining frames.
- E075: E075-A with 1948 -> 1650 -> 1 and the 0.4 s trade-off; E075-B if asked about the statistics.
- E077: E077-C for a shown-by-diff case, E077-B for the numbers the old file typed in, E077-A with its not-re-runnable limit.
- Do not present any case as proof that the AI is unreliable in general; present it as "this is how we caught it".
