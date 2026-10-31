# Merge notes: feat/e043-overnight-full-marks into feat/e043-lead-uav-flight-dyna

Nothing here has been merged. The Part 1 branch and the main checkout were not touched. Merging needs the user's approval.

## Status in one paragraph

All five steps are done and committed. The 180-run main batch and the 80-run ablations were rerun on the current model (exterior patrol layer 22 m, Bravo 26 m). Stats, economics, FMEA, figures, fill sheet, autofill draft, viva evidence and prep, README, VIDEO_VS_FINAL_NUMBERS.md and the video shot-2 timeline were regenerated from them. An Opus integrity audit of the diff since b8f9a92 found four problems (a t-CI still printed on the equal-window revisit in the economics output, stale gate wording, citations pointing at this file, a doubled unit) and fixed them; it then passed all nine checks.

## State of the branches

- Part 1 branch `feat/e043-lead-uav-flight-dyna` on origin: `b712d28b11d2e2b74af2006f6bca94bf7092282b`.
- `git merge-base --is-ancestor origin/feat/e043-lead-uav-flight-dyna HEAD` exits 0 on the overnight branch, so the merge is a fast-forward as long as the Part 1 branch has not moved.
- If `git rev-parse origin/feat/e043-lead-uav-flight-dyna` prints anything else, stop and use the no-fast-forward route.
- Diff `origin/feat/e043-lead-uav-flight-dyna..HEAD` (before this note): 126 files changed, 19060 insertions, 9113 deletions. Files by top folder: docs 77, analytics 31, tests 9, src 4, models 2, README.md 1, RESEARCH_AND_IMPLEMENTATION_GUIDE.md 1, .gitignore 1.

## What changed since b8f9a92

1. 87b6585 fix(e075): the guard equal-window worst revisit is reported as ">= 300 s (right-censored)" with censored counts per cell; no t-test, d or CI on it anywhere (c42c044 removed the last CI, in the economics output). The economics gate passes only if every UAV worst revisit is below the window and prints that reasoning. Cycle time stays the primary metric.
2. 626b71f and 8085b85 fix/test(e043): the interim 63c2178 batch had exterior offset_ring obstacle contacts, confirmed as Alpha against bldg_791070237_0 (roof 19.2 m from mesh vertices; 20.9 m was the geom bounding box), pushed down and north by the separation governor while catching up on Bravo. Fix: exterior ROUTE_ALT 20 m to 22 m (Bravo 26 m). The new test checks every exterior leg of both UAVs in both policies against every collidable building footprint in the compiled model, with the FR-18 margin read from the controller constants.
3. 1071ab6 to 617572e: new main batch (provenance git_commit 8085b85, csv sha256 1ecc25f0...), new ablations (git_commit dad31cb), and every output and document regenerated from them.

## Results of the new batch (analytics/statistical_validation_output.txt, analytics/campus_security_economics_output.txt, docs/dossier_fill_facts_output.txt)

| Cell | Obstacle contacts | Min inter-UAV separation | Equal-window revisit censored | UAV worst revisit max | Gate |
|---|---|---|---|---|---|
| interior guard_baseline | n/a | n/a | 30 of 30 | n/a | n/a |
| interior uav_sectors | 0 | 5.6041 m | 0 of 30 | 108.65 s | PASS |
| interior uav_offset_ring | 0 | 3.0525 m | 0 of 30 | 74.23 s | PASS |
| exterior guard_baseline | n/a | n/a | 30 of 30 | n/a | n/a |
| exterior uav_sectors | 0 | 9.2803 m | 0 of 30 | 133.63 s | PASS |
| exterior uav_offset_ring | 0 | 4.0002 m | 0 of 30 | 126.34 s | PASS |

UAV-UAV contacts 0 in all 120 UAV runs. Every ground-loop UAV did at least 3 laps, except the known interior uav_sectors Bravo gallery spiral (0 ground laps; it flies the atrium galleries). Ablations: separation off has 6 of 10 runs below 2.5 m and 16 UAV-UAV contacts; separation on has 0 and 0. FR-18 and geofence arms show no difference at 90 s.

## Checks

| Check | Result |
|---|---|
| Provenance, main batch and ablations | csv_sha256 equals the committed bytes; code and model hashes equal the HEAD blobs; git_commit not dirty |
| Telemetry manifest | 180 runs, dt_check OK for all 180 |
| Full pytest in the group folder | 112 passed, 1 skipped |
| viva_refs_check.py | 288 verified, 0 failed |
| Opus integrity audit, diff since b8f9a92 | 4 findings fixed (c42c044, 9da5bd1, 89fa543, 617572e); then all 9 checks pass |
| Faculty audit script on a fresh clone | 805 hits, all inside compressed or minified files (telemetry .gz samples, .docx zips including the professor's own template, mermaid.min.js). The autofill draft's text has no currency, no placeholder status words and no emoji |
| Fresh clone, clean venv, src/test_env.py | passed |
| Fresh clone 30 s smoke, uav_offset_ring | interior: 0 obstacle contacts, 0 UAV-UAV, min separation 10.8451 m; exterior: 0, 0, 29.8354 m |
| Professor's files and Part 1 VIDEO_NUMBERS.md / video_numbers_output.txt | byte-identical to b8f9a92 |
| Commit authors since b8f9a92 | all MuaazSM noreply, no trailers |

## Known limitations and things to re-check before submission

- Interior detection is not improved (G-14 partial); exterior false alarms from the red tempo cabs remain (shot 2 is cut at 60.2 s for that reason).
- Wall containment: the exterior flown track leaves the wall polygon in 0.00 to 12.80 % of samples per run, at most 6.66 m outside (docs/submission/viva_evidence/inside_wall_check.txt). Not traced; no cause claimed.
- Commit counts in the fill sheet and docs/dossier_fill_facts_output.txt are recomputed from git and go stale with every new commit; regenerate both just before submission.
- The roof test does not cover the takeoff-to-route transit leg.
- The FR-18 ablation shows no difference (0 vs 0) at 90 s.

## Merge commands (push as MuaazSM)

Fast-forward, only if `git rev-parse origin/feat/e043-lead-uav-flight-dyna` is still b712d28b11d2e2b74af2006f6bca94bf7092282b:

```
git fetch origin
git switch feat/e043-lead-uav-flight-dyna
git merge --ff-only origin/feat/e043-overnight-full-marks
git -c credential.helper= -c credential.helper='!f(){ echo username=x-access-token; echo password=$(gh auth token -u MuaazSM); }; f' push origin feat/e043-lead-uav-flight-dyna
```

No-fast-forward route if Part 1 moved:

```
git fetch origin
git switch feat/e043-lead-uav-flight-dyna
git merge --no-ff origin/feat/e043-overnight-full-marks -m "merge(e043): overnight censored revisit and exterior roof fix"
git -c credential.helper= -c credential.helper='!f(){ echo username=x-access-token; echo password=$(gh auth token -u MuaazSM); }; f' push origin feat/e043-lead-uav-flight-dyna
```
