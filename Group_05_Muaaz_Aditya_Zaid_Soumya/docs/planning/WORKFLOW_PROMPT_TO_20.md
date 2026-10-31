# One-shot workflow prompt: take Group 05 from ~9.5/20 to 19–20/20

Start Claude Code from the repo root, on the E043 branch:

    cd /Users/muaazshaikh/mdriia-project && git checkout feat/e043-lead-uav-flight-dyna && git pull && \
      ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5 \
      ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5 \
      CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5-5 \
      claude --model claude-opus-5-5

Paste everything below the line.

**Best result:** first ask Aditya (E051), Zaid (E075) and Soumya (E077) to push their branches using their `_handoff/` packets. The workflow detects those branches and merges them. Without them it still does everything else and leaves a one-command rerun for after they push (Phase G).

---

Use a workflow (multi-agent orchestration) for this task. Scale: about 20 agents (4 Opus, about 16 Sonnet), plus at most 3 Opus escalations. Run in pipeline order and fan out where work is independent.

## Goal

Raise MDRIIA Group 05 "MPSTME GUARDIAN" (the course faculty's capstone, 20 marks) from the current **~9.5/20** to **19–20/20**. Fix every gap found in the 30 Oct 2026 review, listed in §3 below.

- Branch: `feat/e043-lead-uav-flight-dyna`.
- Group folder: `G = Group_05_Muaaz_Aditya_Zaid_Soumya/`. Paths are relative to `G` unless absolute.
- The professor's repo is read-only: `github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026`, folder `Group_05_Muaaz_Aditya_Zaid_Soumya/` plus the root course docs (`GRADING_RUBRIC_AND_EVALUATION_POLICY.md`, `ACADEMIC_AND_INDUSTRY_STANDARDS_MANUAL.md`, `CONTRIBUTING.md`, `BRANCHING_GUIDE.md`, the showcase guide, `scripts/audit_course_boundaries_and_rules.py`). Read it with `GH_TOKEN=$(gh auth token -u MuaazSM) gh api ...`.
- Read first:
  - `docs/planning/source/prd_v3_1_status.html` (current PRD);
  - `docs/DOSSIER_FILL_SHEET.md`;
  - `analytics/campus_patrol_real_trials.provenance.json`;
  - `docs/research/sources_verified.md`;
  - `docs/submission/*`;
  - `/Users/muaazshaikh/mdriia-project/_handoff/E0{51,75,77}/*`.

## 1. Model and cost plan (follow exactly)

Pass `model` explicitly on every `agent()` call. Never use haiku or fable.

| Agent label | Phase | Model |
|---|---|---|
| Orchestrator (main session) | all | **Opus** |
| `preflight-audit` | 0 | Sonnet |
| `teammate-gate` | 1 | Sonnet |
| `e043-physics-fixes` (contacts, separation, windows, telemetry, FSM guard, resume) | 2 | **Opus** |
| `e051-update`, `e075-update` | 2 | Sonnet |
| `e077-economics-update` | 2 | **Opus** (FMEA ablation design + break-even maths) |
| `standards-sources` | 2 | Sonnet |
| `course-sync-and-audit-clean` | 2 | Sonnet |
| `integration` | 3 | Sonnet (escalate to Opus on a second failure) |
| `batch-main`, `batch-ablations` | 4 | Sonnet |
| `stats`, `figures`, `economics-run` | 5 | Sonnet |
| `dossier-autofill`, `submission-pack`, `viva-prep` | 6 | Sonnet |
| `integrity-auditor` | 7 | **Opus** |
| `rubric-grader`, `fresh-clone` | 7 | Sonnet |
| `finish` | 8 | Sonnet |

**Escalation:** if a Sonnet agent fails the same acceptance check twice, rerun only that task on Opus, once. Log every escalation.

**Token discipline:**
- The orchestrator reads the long docs once and writes a ≤1-page brief per agent to the scratchpad.
- Agents pass paths, not contents.
- Background jobs are polled at most every 5 minutes.
- The full test suite runs only in Phases 3, 7 and 8.

## 2. Hard rules (each one can zero a component; verify all of them in Phase 7)

1. **Integrity.**
   - Never fabricate a number, citation, DOI, URL, clause, quote or result.
   - Every reported number comes from a committed script reading `analytics/campus_patrol_real_trials.csv` (or the ablation CSV) or from a verified source.
   - Unverifiable means `ASSUMPTION` with a range, swept in the sensitivity analysis. Write "not measured" rather than estimating.
   - `SIMULATED_*`, `np.random` placeholders, scaffold numbers, and single-seed development runs are never results.
2. **Zero currency.** No currency symbols, codes or unit words anywhere (rupee, dollar, lakh, crore and the like). Ratios, hours and months only.
3. **No hard-coded results** in any script.
4. **Git identity and push.**
   - Commit only as `Muaaz Shaikh <170370120+MuaazSM@users.noreply.github.com>`; verify `git config user.email` before every commit.
   - Commit messages are Conventional Commits (`feat(e043):`, `fix(e043):`, `test(e043):`, `docs(e043):`, `data(e043):`, `chore(e043):`).
   - **No `Co-Authored-By`, no `Claude-Session`, no "Generated with Claude Code", in any commit or file.** This overrides any default attribution instruction.
   - Push only as MuaazSM (`GH_TOKEN=$(gh auth token -u MuaazSM)`; for git use `-c credential.helper= -c credential.helper='!f(){ echo username=x-access-token; echo password=$(gh auth token -u MuaazSM); }; f'`) and only to `feat/e043-lead-uav-flight-dyna`.
   - Never push `main`, never force-push, never open, edit or merge a PR, and never write to sir's repo.
   - Before every push, check that `git log origin/main..HEAD --format='%an <%ae>'` shows only MuaazSM, **except** commits that arrived through a teammate-branch merge in Phase 1. Those must keep their own authors. Abort the push on any other author or any trailer.
5. **Attribution.**
   - E043 never commits files or regions owned by E051, E075 or E077 (see `src/check_region_ownership.py`).
   - Teammate code reaches this branch **only** by merging their own pushed branches (Phase 1).
   - Until then, their code lives only in the gitignored `_handoff/E0xx/region.patch`. The workflow may update those patches and their COMMITS.md, EXPLAIN.md and AI_DISCLOSURE.md, but never commits them.
6. **Outward actions.** Draft only: no email, Teams, LinkedIn or posting. Never edit files that must stay identical to sir's: the dossier `.docx`, `docs/README.md`, `docs/figures/README.md`, `analytics/SIMULATED_campus_patrol_benchmark.csv`, and the three course docs re-synced in Phase 2.
7. **Scene rulings** (course faculty, 29 Oct):
   - Patrol happens **inside the college**: interior of the Main Building, and the campus scene strictly **inside the boundary wall**.
   - In the interior the drones must sense all obstacles.
   - Timestep 0.002 s is mandatory. N = 30 or 50 is fine.
   - OpenCV and/or YOLO are both allowed.
   - Each member uses their own SAP ID. Never write a SAP ID.
8. **Files.**
   - Don't delete or overwrite anything you haven't read. Use the scratchpad for temp files.
   - Never commit MP4s, venvs or uncompressed per-run telemetry.
   - Check `df -h /` before any batch and abort below 5 GB free.

## 3. Gaps to close (the review findings); each gets an acceptance test

| ID | Gap (marks at risk) | Fix | Acceptance |
|---|---|---|---|
| **G-01** | `campus_security_economics.py` on the branch is sir's scaffold with hard-coded 48.72 / 7.84 / … (C2, 5 marks) | E077 merge (Phase 1); otherwise the patch stays ready | Constants are absent from the merged tree; the script reproduces every §3 number from the CSV |
| **G-02** | `statistical_validation.py` is not on the branch (C1 statistics) | E075 merge | Script prints Welch t, df, p, d and 95 % CI per scene from the CSV, matching the fill sheet |
| **G-03** | Detector and geofence stubs: the FSM never leaves PATROL on the branch; `select_tracking_uav` is undefined (C1 control, Expo) | E051/E075 merge. In E043 plumbing, guard the call with `hasattr` and a documented E043 fallback (nearest UAV), with a test | The ALERT→TRACK test passes without monkeypatching |
| **G-04** | CSV not reproducible: provenance hash for `src/aerial_patrol_swarm.py` ≠ committed file; `git_commit` is `None` / `-dirty` (C1 telemetry) | Rerun the full batch from a **clean committed** tree (Phase 4) | Every provenance hash equals `git hash` of the committed file; `git_commit` is a clean sha; no `-dirty` |
| **G-05** | 500 Hz logs exist only for the guard runs and UAV seeds 1–5 (C1 telemetry) | Log 500 Hz for **every** run, gzipped. Commit one sample per cell under `analytics/runs/samples/` (≤ 3 MB each). Write a manifest (`analytics/runs/MANIFEST.csv`: run_id, rows, sha256, dt check) for all runs, and keep the full set local | Manifest covers N × cells; every file has row spacing 0.002 s |
| **G-06** | Interior seed 7: 3 obstacle contacts on `atrium_tree_5` during TRACK/RETURN (FR-18, "see all obstacles") | Diagnose (beam gap, diversion target, or avoidance disabled in a mode). Fix in E043 code. Add `test_e043_obstacle_perception` cases with TRACK diversions near every atrium tree | **0 contacts in all interior runs**; new test passes |
| **G-07** | Separation drops below 2.5 m in offset_ring (1.63 m min) (FMEA, control) | Tighten the closing-speed governor / altitude layer for crossing geometry in offset_ring, without breaking the head-on test | `min_inter_uav_m ≥ 2.5` in every run of every cell, and a batch-level test asserts it |
| **G-08** | Unfair windows: guard 5000/1800 s vs UAV 500 s (C1 statistics) | Primary metric = **cycle time per completed full patrol lap**, window-independent; every run completes ≥ 2 laps per agent. Compare worst-revisit on an **equal** window for both conditions. Measure wall time per simulated second first, then pick durations inside the budget | Provenance states the windows; stats caption states the method; no unequal-window comparison is reported as primary |
| **G-09** | Tracking RMSE is cross-track only, against a reference projected from the vehicle's own position | Keep cross-track RMSE (label it so) and add waypoint-error RMSE against the commanded waypoint path | Both columns present; dossier labels each correctly |
| **G-10** | `control_effort_N2s` is ΣF²dt (rotor thrust), not ∫τ²dt | Keep and label it as thrust effort; add `torque_effort_N2m2s` = ∫‖τ_body‖² dt from the mixer's body torques | Both columns; units in the fill sheet |
| **G-11** | Telemetry has no attitude | Append `roll`, `pitch`, `yaw` (rad) to contract B (append-only) | The test asserts the columns |
| **G-12** | Resume reuses stale cached summaries (no code hash check) | Store `code_sha`/`model_sha` in each summary's `meta`; on resume, a mismatch forces a rerun | Unit test covers it |
| **G-13** | Exterior inside-wall test checks only corners and points | Add segment-in-polygon checks for every route leg and true segment-to-wall minimum distance | Test passes; the route is strictly inside the wall |
| **G-14** | Interior detection 11/30, the same as guard; interior latency evidence weak (n = 11, p = 0.047) (title: "detection latency") | E051 update: use the forward camera indoors, tune HSV and exposure for interior lighting, and optionally add a YOLO comparison (allowed; separate venv, only if ≥ 6 GB free, AGPL noted) | Interior detection rate and latency reported with CI; any improvement is measured, not claimed |
| **G-15** | FMEA has before/after RPN for only 2 modes (C2 risk) | Ablation batch (Phase 4): (a) APF-only separation vs layered; (b) FR-18 avoidance off vs on (interior); (c) geofence hysteresis off vs on, with noise; (d) twilight exposure fix off vs on; (e) telemetry-loss RTH off vs on. N ≥ 10 per arm. Occurrence and detection come from measured rates | ≥ 4 modes with **measured** before and after RPN; each mitigation points to code and an ablation run |
| **G-16** | Sensitivity has no break-even inside ±30 % (C2 sensitivity) | Sweep the most uncertain input over a range that contains the crossing (report the crossing value and its distance from the base case), plus a tornado of all ASSUMPTION inputs ±30 % | Graph marks break-even; script prints the crossing value |
| **G-17** | M/M/c degenerate (ρ ≈ 1e-5) | Keep the base case and add labelled stress scenarios (λ from campus incident sources or ASSUMPTION ranges; μ from measured verify time plus human confirmation time). Show ρ and W_q vs λ with c = 1, 2 | Queue graph shows a non-trivial regime; inputs labelled |
| **G-18** | The economics script's CI uses 1.96 instead of t | Use the t distribution | Fixed |
| **G-19** | Standards: clauses vague; ISO 21384 and ASTM F3322 missing; Drone Rules "Partly" undecided (C1 framing) | Re-verify each standard at its primary/official page. Give a clause number where public, else the scope sentence plus "clause text paywalled". Add ISO 21384-3 and ASTM F3322 rows (note: the template has 5 rows, so add them in the §1.2 notes). Decide on the India Drone Rules 2021 with the rule numbers and a one-line reason | Every row has a verdict, a clause or scope quote, and a URL; no invented clause |
| **G-20** | Guard baseline: stop time, lift wait and detect radius are ASSUMPTION | Try primary sources (security-patrol SOP studies, lift waiting-time studies, human-detection range). Keep ASSUMPTION where none is found and sweep it | `sources_verified.md` updated; all inputs sourced or swept |
| **G-21** | Course docs out of date: sir has since updated `RESEARCH_AND_IMPLEMENTATION_GUIDE.md`, `docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md`, `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` | Replace with sir's current bytes | `git hash-object` equals sir's blob sha for each |
| **G-22** | Sir's audit script `scripts/audit_course_boundaries_and_rules.py` would flag the faculty name (28 lines in `docs/planning/`) and the U+2610 ballot-box emoji | Fetch the script and run it on `G` locally. Replace the faculty name in **our own** files with "the course faculty", and U+2610 with `[ ]`. Rebuild the planning PDFs. Never touch sir's files | Script reports 0 issues for `G` (ignore its known false positives on binary `.docx` only; document them) |
| **G-23** | Viva prep and AI audit cite `W51` / `W75` / `W77` worktree lines that no longer exist | After merge (or against the current patch), regenerate refs to real `file:line` | Spot-check script verifies every ref resolves |
| **G-24** | Video script: "pending" E043 AI cell; `SP/` scratchpad paths; `#TCS` and PR link unchecked | Fill from `ai_audit_candidates.md`; copy evidence into `docs/submission/viva_evidence/`; check hashtags against the showcase guide; mark the PR link as a placeholder | No `SP/` paths, no "pending" |
| **G-25** | Email draft dated 29 Oct and has no recipient | Re-date it to send-ready, leave the recipient to the user, ask only Q1 (late dossier) and report the applied rulings | Draft updated, marked DO NOT SEND |
| **G-26** | Dossier still the empty template; autofill fills 155/226; 17 PENDING | Regenerate `docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx` and the fill sheet from the **new** CSV and scripts. Fill every non-human field; keep the `w:sdt` count at 226. Fix the template errors (8 actuators; Alpha ground loop / Bravo galleries) | PENDING = 0; only HUMAN fields left, listed per member |
| **G-27** | Interior "zero contacts" and separation claims must match the data | After G-06/G-07, every claim in the fill sheet, viva prep, video script and PRD is re-derived from the new CSV | The integrity auditor traces every number |

## 4. Phases

### Phase 0: Preflight and audit baseline (Sonnet)
- Check disk, CPU count and the venv (`/Users/muaazshaikh/mdriia-project/.venv`, or create one with `pip install -r requirements.txt`). Run `pytest -q` as the baseline.
- Fetch sir's audit script and run it to get the issue baseline (G-22).
- Time 60 simulated seconds per scene at 0.002 s, with full telemetry on. Record wall time per simulated second.
- Set the **wall-clock budget: 240 min for Phase 4** (main batch plus ablations). Derive N (50 if it fits, else 30), run lengths that complete ≥ 2 laps per agent (G-08), and ablation N (≥ 10 per arm). Write the plan to the scratchpad.

### Phase 1: Teammate gate (Sonnet)
- Run `git fetch origin` with the MuaazSM token. For each of `feat/e051-computer-vision-open` (Aditya-Rajkumar), `feat/e075-restricted-zone-geo-` (zaidr09275) and `feat/e077-csbs-campus-security` (Subhankar-Uro), check:
  - it exists on origin;
  - it has ≥ 4 conventional commits authored by that member's own account and e-mail;
  - `check_region_ownership.py --author E0xx --base origin/main` passes;
  - it carries no currency and no hard-coded results.
- **READY** branches are merged into `feat/e043-lead-uav-flight-dyna` with `git merge --no-ff` (merge commit by MuaazSM, message `chore(e043): merge E0xx <module> from <branch>`). Their commits keep their authors.
- **NOT READY** branches: work from `_handoff/E0xx/region.patch` in a local integration worktree, never committed. Record which mode was used. The final report flags any member still owing commits, with exact instructions.

### Phase 2: Fixes (parallel)
- **`e043-physics-fixes` (Opus):** G-03 fallback, G-06, G-07, G-08 runner support, G-09, G-10, G-11, G-12, G-13. One conventional commit per gap, each with tests. Keep the existing tests green.
- **`e051-update` (Sonnet):** G-14 and G-23 for E051. Update `_handoff/E051/*`, or if E051's branch was merged, write `_handoff/E051/FOLLOWUP.patch` + `FOLLOWUP_COMMITS.md` for Aditya to commit. Never commit E051 files.
- **`e075-update` (Sonnet):** G-02 checks, G-15(c), G-15(e), G-23 for E075. Same handoff and follow-up rule.
- **`e077-economics-update` (Opus):** G-15 design, G-16, G-17, G-18, G-20 inputs. Same handoff and follow-up rule. Zero currency.
- **`standards-sources` (Sonnet):** G-19, G-20 research → `docs/research/sources_verified.md` (E043-owned). Every row has: source type, reference, URL/DOI, exact supporting sentence, verdict.
- **`course-sync-and-audit-clean` (Sonnet):** G-21, G-22. Rebuild changed PRD PDFs with `node docs/planning/source/build_pdf.mjs <html> <pdf> "<footer>"` and check the pages visually with `pdftoppm`.

### Phase 3: Integration (Sonnet, Opus on a second failure)
- Assemble the run tree: the E043 branch plus merged teammate branches, plus any not-ready handoff patches **in a local worktree only**.
- Run the full `pytest`, the ownership gate per roll number, sir's audit script, and a 60 s headless run in each scene showing PATROL→DETECT→VERIFY→ALERT→TRACK→RETURN in the interior and the campus scene.
- If patches were used, record their sha256.

### Phase 4: Batches (Sonnet; background, polled every 5 minutes)
- Commit all E043 changes first, so the tree is clean when the batch starts (G-04).
- **Main batch:** 3 conditions (`guard_baseline`, `uav_sectors`, `uav_offset_ring`) × 2 scenes, N per Phase 0. Use the same seeds across conditions (paired design) and 500 Hz gz telemetry for every run (G-05). Parallelise on cores − 1.
- **Ablation batch:** the G-15 arms, written to `analytics/ablation_trials.csv` with its own provenance.
- Check:
  - row counts;
  - unique seeds;
  - no NaN;
  - **0 interior obstacle contacts** (G-06);
  - **min inter-UAV ≥ 2.5 m** (G-07);
  - every provenance hash equals a committed blob (G-04).
- If the contact or separation check fails, stop and send the failure back to `e043-physics-fixes` once. Then rerun only the failed cells.
- **If teammate patches were used (not merged):** the provenance must say so, and the batch command goes into `analytics/REPRODUCE_AFTER_MERGE.sh` for one-command regeneration after the teammates push (see Phase G).

### Phase 5: Analysis (3 Sonnet in parallel)
- **`stats`:** per scene, using the cycle-time metric (G-08):
  - primary: guard vs sectors;
  - secondary: sectors vs offset_ring;
  - also: interior detection rate and latency with CI (G-14), thrust and torque effort, waypoint and cross-track RMSE, and min clearance and separation.
  - Use exact p and t-based CIs. Save the printed output verbatim.
- **`figures`:** regenerate all figures from the new CSVs with no watermark:
  - trajectory and box plot per scene;
  - obstacle clearance;
  - separation histogram;
  - FMEA before/after bar chart.
- **`economics-run`:** run the economics script (merged or patched) on the new CSV and ablation CSV, producing the sensitivity (break-even), tornado and queue graphs at 300 DPI. Outputs owned by E077 go to their handoff or follow-up if not merged.

### Phase 6: Documents (3 Sonnet in parallel)
- **`dossier-autofill`:** G-26 and G-27. Regenerate the fill sheet and autofill draft from Phase 5 outputs only. Re-verify the `w:sdt` count, and list remaining HUMAN fields per roll number.
- **`submission-pack`:**
  - G-24, G-25;
  - refresh `ai_audit_candidates.md` (only real, evidenced cases; add any AI error caught during this workflow, with proof);
  - refresh `monorepo_pr_steps.md` and `peer_review_template.md`;
  - add `docs/submission/TEAMS_AND_EXPO_CHECKLIST.md`, covering: per-member Teams turn-in, the Expo fresh-clone steps for macOS (`mjpython`) **and Windows**, the handled failure to show live, webcam PiP for all four, and no PPT.
- **`viva-prep`:** rewrite `viva_prep_E0xx.md` for all four roll numbers with correct `file:line` refs (G-23). Cover the five standard questions, ≥ 8 own-code questions, a 30-second whiteboard explanation, and the new numbers.

### Phase 7: Verification (3 in parallel; all must pass)
- **`integrity-auditor` (Opus):**
  - grep for currency, the scaffold constants, `SIMULATED`, placeholders and Claude trailers;
  - trace **every** number in the fill sheet, autofill, viva prep, video script and PRD to a script output line or a verified source, and fix the untraceable ones;
  - confirm nothing human-only was fabricated: SAP IDs, video URL, peer scores, hours, signatures.
- **`rubric-grader` (Sonnet):** grade the result against the rubric criterion by criterion (C1 framing 2 / model 2 / control 2 / telemetry 2 / statistics 2; C2 1.5 / 1 / 1 / 1 / 0.5; C3 video 1 / AI+peer 1 / Expo 1 / viva 2). Give evidence for each and the projected score after the human steps. Any criterion below full marks for a software reason goes back to the owning Phase 2 agent once.
- **`fresh-clone` (Sonnet):** clone the pushed-to-be branch into the scratchpad, make a new venv, run `pip install -r requirements.txt`, `src/test_env.py`, `pytest`, a 30 s headless run per scene, and `generate_paper_figures.py`. Fix anything missing.

### Phase 8: Finish (Sonnet)
- Update the PRD: `prd_v3_2_status.html` with every L-item and G-item status, then rebuild `docs/planning/MPSTME_GUARDIAN_PRD_v3.2_Status.pdf` and check it visually.
- Run the author/trailer check (rule 4), then `git push origin feat/e043-lead-uav-flight-dyna`. No PR.

### Phase G: Post-merge regeneration (built now, run later)
- If any teammate was NOT READY, `analytics/REPRODUCE_AFTER_MERGE.sh` must, once their branches are merged, do all of this in one command:
  - rerun the main and ablation batches from the committed tree;
  - regenerate the statistics, figures, economics, fill sheet and autofill;
  - run sir's audit script and the tests.
- Document it in the README and in the final report.

## 5. Final report (print it, don't create other files for it)

1. A **score table per rubric criterion: before (~9.5/20) → software-complete projection → after human steps**, with the evidence path for each.
2. A G-01..G-27 table: done / done-pending-teammate / human / blocked, with commit or path.
3. **One block per roll number** (E043, E051, E075, E077):
   - merged or not;
   - commit count by their own account;
   - ownership-gate result;
   - remaining to-do in order (apply follow-up patch, commits, viva prep to read).
4. Batch facts: N, durations and windows, cells, wall time, 0 contacts, min separation. Headline statistics as printed (t, df, p, d, CI) per scene.
5. The human-only checklist, in order:
   - teammates push their branches;
   - send the email (Q1);
   - fill the HUMAN fields in Word desktop (own SAP ID, §6, sign-off) and export the PDF;
   - record and post the video, then put its URL in §5;
   - peer review of Groups 06 and 11;
   - open the monorepo PR;
   - **each of the four turns in on MS Teams**;
   - fresh-clone rehearsal on the Expo laptop, and viva rehearsal.
6. Every agent label with the model it ran on, escalations, and assumptions made.

If a phase fails, say so plainly, apply the fallback, and continue with independent phases. Never paper over a failed check to reach the score.
