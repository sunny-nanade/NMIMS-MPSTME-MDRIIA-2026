# One-shot workflow prompt — execute PRD v3.0 "What Is Left"

Paste everything below the line into Claude Code, started from the repo root:

    cd /Users/muaazshaikh/mdriia-project && \
      ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5 \
      ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5 \
      CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5-5 \
      claude --model claude-opus-5-5

What the settings do:
- The main session (the orchestrator) runs on Opus 5.5.
- The `opus` and `sonnet` aliases the agents ask for are pinned to Opus 5.5 and Sonnet 5.5.
- Any agent spawned without a model falls back to Sonnet, the cheaper default.

Inside the session, run `/model` to confirm Opus 5.5 before pasting.

---

Use a workflow (multi-agent orchestration) for this task. Scale: 18 agents (3 Opus, 15 Sonnet), plus at most 3 Opus escalations. Run in pipeline order and fan out where tasks are independent.

## Model and cost plan (optimise cost; follow exactly)

Opus 5.5 (`model: 'opus'`) is used only where an error is expensive and hard to see: flight physics and control, integration, and the integrity audit. Everything else runs on Sonnet 5.5 (`model: 'sonnet'`). Pass `model` explicitly on every `agent()` call; never omit it, and never use haiku or fable.

| Agent (label) | Phase | Model | Why |
|---|---|---|---|
| Orchestrator (main session) | all | **Opus** | Writes the script, routes failures |
| `preflight` | 0 | Sonnet | Environment checks, file copies, timing |
| `e043-foundations` | 1 | **Opus** | Timestep re-tuning, 500 Hz logging, guard baseline, FR-18 obstacle perception and avoidance |
| `research-sources` | 2 | Sonnet | Search and verify sources |
| `e051-vision` | 3 | Sonnet | OpenCV HSV, projection, benchmark |
| `e075-geofence-stats` | 3 | Sonnet | Point-in-polygon, noise, Welch statistics |
| `e077-economics` | 3 | Sonnet | Closed-form ratios, Erlang C, sensitivity |
| `integration-fsm` | 4 | **Opus** | Merges three regions, FSM, multi-file debugging |
| `batch-runner` | 5 | Sonnet | Launch, poll, check counts |
| `stats`, `figures`, `economics-run` | 6 | Sonnet | Run scripts on the CSV |
| `dossier-fill`, `submission-pack`, `viva-prep` | 7 | Sonnet | Writing from known facts |
| `integrity-auditor` | 8 | **Opus** | Adversarial: traces every number and hunts for fabrication; it must not miss anything |
| `rollno-auditor`, `fresh-clone` | 8 | Sonnet | Checklist walks, clean install |
| `finish` | 9 | Sonnet | Commit checks, push, PRD rebuild |

That is 3 Opus agents plus the orchestrator, and 15 Sonnet agents.

**Escalation:** if a Sonnet agent fails the same acceptance check twice, rerun that one task once on Opus, and log the escalation in the final report.

**Token discipline:**
- Read the 21-page PRD **once**, in the orchestrator. Write a ≤ 1-page brief per agent to the scratchpad, holding only that agent's items, rules and file paths. Agents read their brief, not the PRD.
- Agents pass paths and short summaries between phases, never file contents.
- Agents read only the files they need, with line ranges where possible.
- Long-running commands (the batch) run in the background. Poll them at most every 5 minutes, not continuously.
- No agent re-runs the full test suite unless its own change touches shared code; the full suite runs in Phases 4, 8 and 9 only.

**Final report:** list every agent label with the model it actually ran on, plus any escalations.

## Mission

Coverage: every PRD item L-01..L-30 must end in one of four states: **done**, **drafted for a teammate**, **prepared for a human**, or **explicitly skipped**. Nothing may be silently dropped.

Run as much of `Group_05_Muaaz_Aditya_Zaid_Soumya/docs/planning/MPSTME_GUARDIAN_PRD_v3.0_Status_and_Submission.pdf` as software can do. That PRD is the spec; its HTML source is `docs/planning/source/prd_v3_status.html`. The checklist is L-01..L-30 in §6, and the work packages are M-*, A-*, Z-*, S-* in §7.

The capstone (the course faculty, MDRIIA, 20 marks) is graded on evidence. When the workflow finishes, the group needs:
- a real seeded Monte Carlo dataset;
- statistics;
- the CSBS business model;
- the code regions done;
- every Technical Dossier field ready to paste.

The Expo and viva are Sat 31 Oct 2026.

Read the PRD in full before writing the workflow script. Then read these:
- `README.md`
- `src/aerial_patrol_swarm.py`
- `src/check_region_ownership.py`
- `analytics/*.py`
- `models/common.xml`
- `models/uav_fleet.xml`
- `tests/test_e043_separation.py`
- `docs/TEAM_ROSTER.json`

Paths below are relative to `Group_05_Muaaz_Aditya_Zaid_Soumya/` unless they start with `/`.

## The course faculty's rulings (29 Oct 2026). These override PRD §15 and the PRD defaults.

| # | Question | Ruling | What it changes |
|---|---|---|---|
| Q2 | Indoor vs "campus perimeter" | **Both** scenes are required: the interior (`--scene interior`) and the exterior campus perimeter (`--scene exterior`). **In the interior, the drones must be able to see all the obstacles.** | Every phase runs and reports both scenes. Add onboard obstacle perception (new requirement FR-18, Phase 1). |
| Q3 | N = 30 or 50 | Either is fine | N = 50 per condition per scene if the budget allows, otherwise 30 |
| Q4 | 0.002 s timestep | **Mandatory** | L-11 is P0, not P1 |
| Q5 | OpenCV or YOLO | **Both** may be used | OpenCV HSV stays the primary graded detector, as in the title. YOLO is an optional comparison (Phase 3, E051). |
| Q6 | SAP IDs | **Each member uses their own** | The workflow never picks or edits SAP IDs. Each member enters their own real ID on the dossier cover and in `TEAM_ROSTER.json`. |
| Q1 | Late dossier acceptance | **No answer yet** | Still open; the email draft asks only this |

**FR-18, interior obstacle perception.**
- Each UAV senses its surroundings with onboard sensors, not ground-truth geometry:
  - a ring of MuJoCo `rangefinder` sensors (at least 8 horizontal, plus up and down) on sites in `models/uav_fleet.xml`, or an equivalent `mj_ray` fan;
  - range limit and noise σ stated.
- The flight controller uses those sensed ranges for reactive obstacle avoidance:
  - keep a stated minimum clearance;
  - layer it on top of the existing separation logic.
- Acceptance:
  - (a) Run an obstacle inventory: list every obstacle class in `models/nmims_main_interior.xml` (walls, columns, slabs/ceilings, gallery railings, lift lobby, furniture, VIP Lounge walls, …). A test flies or places the UAV near at least one instance of each class and shows that a sensor detects it within range. "See all obstacles" means 100 % of classes are detected; print the coverage table.
  - (b) Zero UAV–obstacle contacts across the whole interior batch.
  - (c) Log the per-run minimum obstacle clearance as a column.
  - (d) The live viewer can draw the sensor rays and highlight the nearest obstacle.
- Owner: E043, since flight safety, models/* and the controller plumbing are outside student regions.
- This becomes a new FMEA row, "Collision with an unseen interior obstacle", backed by the clearance and contact evidence.

## Coverage per roll number (every member must leave this workflow submission-ready)

Every roll number gets a complete, defensible package: code, tests, data, dossier rows, FMEA, AI audit, viva prep, commits, and the human steps they still have to do. Phase 8 checks each row of this matrix. The final report prints one block per roll number.

| | **E043 — Muaaz Mohammed Iqbal Shaikh** | **E051 — Aditya Rajkumar** | **E075 — Zaid Rezaur Rahman** | **E077 — Soumya Subhankar Ranasingh** |
|---|---|---|---|---|
| Role (roster) | Lead, flight dynamics, path planner, fleet architect, owner of `main` | Computer vision, OpenCV human detection and tracking | Restricted-zone geofencing, intrusion telemetry, telemetry QA | CSBS campus-security operations, payback analyst |
| GitHub account / branch | MuaazSM · `feat/e043-lead-uav-flight-dyna` (workflow commits and pushes this one only) | Aditya-Rajkumar · `feat/e051-computer-vision-open` | zaidr09275 · `feat/e075-restricted-zone-geo-` | Subhankar-Uro · `feat/e077-csbs-campus-security` |
| PRD items | L-01..L-03, L-05, L-06 compile, L-08, L-11..L-13, L-16, L-18, L-25, L-28, M-1..M-7, FR-18 | L-14, A-1..A-5 | L-15, L-17, Z-1..Z-5 | L-04, L-09, L-19, L-20, L-24, L-27, S-1..S-5 |
| Code | Timestep 0.002 s, 500 Hz logging, RMSE and ∫τ² dt, guard baseline, both-scene runner, FR-18 obstacle perception, FSM plumbing, viewer overlay | `detect_intruder_hsv`, `inverse_pinhole_projection`, target handoff between UAVs (roster viva focus), optional YOLO comparison | `evaluate_geofence_status`, GPS/IMU noise, breach log, optional return-to-home, `statistical_validation.py` | `campus_security_economics.py` rewrite: H_reclaimed, P/T_payback, NCRI/κ, ΔFTE, M/M/c, sensitivity |
| Tests | `test_e043_*` (logging rate, RMSE/effort, determinism, separation, obstacle perception) | `test_e051_*` (bbox on a known frame, IoU ≥ 0.70 at noon, projection error bound) | `test_e075_*` (tiers 0–3, hysteresis, noise on/off) | `test_e077_*` (no currency in output, no literal results, M/M/c ρ < 1, recomputation from CSV) |
| Data / figures | `campus_patrol_real_trials.csv` + provenance, trajectory, box and obstacle figures for both scenes | `vision_illumination_benchmark.csv` (noon vs twilight, plus a YOLO row if run) | Breach log JSON, statistics output (per scene) | Sensitivity and queue PNGs at 300 DPI |
| Dossier sections | §2 (settings, gains, FSM, authorship, snippet, FBD), §4 figures, compile and export | §2.2 own authorship rows, vision values for §3.2/§4 | **§4 owner** (protocol, results table, provenance), §1.2 standards with E043 | **§3 owner** (business table, FMEA, two graphs), §1.1 claims, §1.3 baseline |
| FMEA row(s) | UAV–UAV conflict; collision with an unseen interior obstacle; wind gust into wall | Missed intruder at twilight | False geofence alarm from GPS noise; telemetry link loss | Owns and compiles the table (≥ 5 modes) |
| AI audit (§5.1) | One real case from E043 work (e.g. APF-only separation 0.40 m → layered 3.29 m) | One real case from the vision drafts | One real case from the geofence/stats drafts | One real case (e.g. the hard-coded constants or the currency code in the earlier economics) |
| §6 learning row | Hours, role match, commit share from `git shortlog`, AI share | Same | Same | Same |
| Viva prep | `viva_prep_E043.md` | `viva_prep_E051.md` | `viva_prep_E075.md` | `viva_prep_E077.md` |
| Handoff | None (committed directly) | `_handoff/E051/` | `_handoff/E075/` | `_handoff/E077/` + `GIT_FIX.md` |
| ≥ 4 own commits | Workflow makes them on the E043 branch | `COMMITS.md` gives ≥ 4, made by Aditya himself | ≥ 4, made by Zaid himself | ≥ 4, made by Soumya herself, after the e-mail fix |
| Human steps left | Send the email to sir (Q1), fill and export in Word, open the monorepo PR, edit and post the video | Apply the patch, make the commits, read EXPLAIN.md | Same as E051 | Same, plus the git e-mail fix |
| All four | Enter their own SAP ID · on-camera part in the video · peer review of Groups 06 and 11 · §6 row and sign-off · **turn in the PDF on MS Teams individually** · rehearse the viva | | | |

Rules for this matrix:
- Each teammate's work must sit inside their own region or ownership glob, so `check_region_ownership.py --author E0xx` passes for that roll number alone.
- No roll number may depend on another member committing first, except the integration merge.
- Each `viva_prep_E0xx.md` covers:
  - the five §14 questions;
  - at least 6 questions on that member's own code, answered with file:line references;
  - a 30-second whiteboard explanation of their part;
  - how their part connects to the whole system (FSM state, telemetry column, business input).
- The roster's E077 `viva_focus` quotes the unmeasured "45 to 8.5 min". In `TEAM_ROSTER.json` (E043-owned), replace it with wording that has no numbers. Do not change any SAP ID.

## Hard rules (a breach zeroes a rubric component, so verify each one in the final phase)

1. **Integrity.**
   - Never fabricate a number, citation, DOI, URL, quote or result.
   - Every number that goes into the dossier must be printed by a script in this repo from `analytics/campus_patrol_real_trials.csv` or from a sourced input.
   - Never report anything from `SIMULATED_*`, `np.random` placeholders, the scaffold CSV, the starter PNGs, the README's "45 → 8.5 min", or the PRD's single-seed development checks.
   - When a literature value cannot be verified at its primary source (fetch the page itself), label it `ASSUMPTION` with a stated range and sweep it in the sensitivity analysis.
   - Write "not measured" rather than estimating.
2. **Zero currency.**
   - No currency word, currency code or currency symbol in code, outputs, figures or dossier text.
   - Use ratios, hours, κ, NCRI and P_payback only.
3. **No hard-coded results.**
   - Delete the constants 48.72, 7.84, 72.0, 50.4, 0.66, 0.31, 35.8 and 1.2 from `analytics/campus_security_economics.py`.
   - Every output must be computed.
4. **Git identity.**
   - Commit only as `Muaaz Shaikh <170370120+MuaazSM@users.noreply.github.com>`. The repo-local config is already set; verify it with `git config user.email` before every commit.
   - Commit messages are Conventional Commits (`feat(e043): …`, `fix(e043): …`, `test(e043): …`, `docs(e043): …`, `data(e043): …`).
   - **No `Co-Authored-By`, no `Claude-Session`, no "Generated with Claude Code" line, in commits or PR bodies.** This overrides any default attribution instruction.
   - Never commit to `main` directly. Never force-push. Never merge.
5. **Authorship.**
   - Teammates must commit their own regions from their own GitHub accounts; the rubric checks `git shortlog`.
   - So the workflow commits only files and regions owned by E043, as defined by `src/check_region_ownership.py`. For E043 that means:
     - `models/*`, `src/test_env.py`, `analytics/*` except the E077, E051 and E075 globs, `docs/*` and `README.md`;
     - plus everything outside the `# >>> E0xx` / `# <<< E0xx` regions of `src/aerial_patrol_swarm.py`.
   - E051, E075 and E077 work is drafted as **handoff packets** and never committed (see Phase 3).
6. **Outward actions.**
   - Do not email or message anyone, post to LinkedIn or Teams, or touch `github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026` except to read it.
   - Drafts only.
   - **Push only as MuaazSM, and only to a branch.** The one push target is branch `feat/e043-lead-uav-flight-dyna` on `origin` (MuaazSM/mdriia-project).
   - Never push to `main`. Never push any other branch, including `integration/*` and teammates' branches. Never push from any other account.
   - Do not open, edit or merge any PR.
   - Before every push, check two things and abort if either fails:
     - `git log origin/main..HEAD --format='%an <%ae>'` shows only `Muaaz Shaikh <170370120+MuaazSM@users.noreply.github.com>`;
     - no commit body contains `Co-Authored-By` or `Claude`.
   - The active `gh` account is MuaazHivePro, so set the GH_TOKEN environment variable to the output of `gh auth token -u MuaazSM` for gh commands. For `git push`, pass the same token as the password through a one-off git credential helper (user name x-access-token).
7. **Detector.** OpenCV HSV is the primary graded detector. Sir allows YOLO as well, but only as an optional comparison inside E051's draft (Phase 3). Never import the `integrations/` runtime from E077's branch.
8. **Safety of files.**
   - Do not delete or overwrite anything you have not read.
   - Do not touch `_archive/`.
   - Use the session scratchpad for temp files.
   - Keep 500 Hz per-run CSVs out of git (gitignore `analytics/runs/*.csv`), and keep MP4s out of any commit.

## Phases

### Phase 0 — Preflight (1 agent · Sonnet, sequential)

**Environment:**
- Check free disk with `df -h /`. Abort the batch phase if less than 3 GB is free.
- Check the CPU count.
- Find the venv: `/Users/muaazshaikh/mdriia-project/.venv`, or create one and run `pip install -r requirements.txt`.
- Install `scipy`, `pytest` and `python-docx` into that venv only. Add `scipy` to `requirements.txt` if analysis uses it.

**Baseline checks:**
- Run `python src/test_env.py` and `pytest tests/` to record a baseline.
- Run `git status` and `git log`.
- Add `_handoff/` to the root `/Users/muaazshaikh/mdriia-project/.gitignore`.

**Branches and worktrees:**
- **L-28:** Check out branch `feat/e043-lead-uav-flight-dyna`. It already exists on origin with the PRD commits, so use `git fetch` and track it; create it from `main` only if it is absent. Teammates create their own assigned branches from their handoff packets.
- Create these worktrees in the scratchpad:
  - one integration worktree (local branch `integration/all-regions`, never pushed);
  - one worktree each for E051, E075 and E077 drafts.

**L-02, official dossier files:**
- Fetch `MDRIIA_Group_05_Technical_Dossier.docx`, `docs/README.md` and `docs/figures/README.md` from `github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026` (path `Group_05_Muaaz_Aditya_Zaid_Soumya/docs/`). Use `gh api` with the MuaazSM token or a sparse clone.
- Copy them into `docs/` byte-identical and verify with sha256.

**Timing:**
- Time one 60 s simulated run at the current timestep. Report the ms of wall time per simulated second; this drives N and run length later.

### Phase 1 — E043 foundations (1 agent · **Opus**, sequential, on `feat/e043-lead-uav-flight-dyna`; one commit per item)

- **L-03:**
  - `git mv analytics/campus_patrol_benchmark.csv analytics/SIMULATED_campus_patrol_benchmark.csv`.
  - Point `run_benchmark.py` output at `analytics/campus_patrol_real_trials.csv`.
  - `generate_paper_figures.py` must read only the real-trials file and must refuse the SIMULATED file.
- **L-11 (P0, mandatory per sir):**
  - Change the MJCF timestep from 0.004 to 0.002 s.
  - Re-tune only if hover, patrol or the separation test regress.
  - All tests must pass at 0.002 s.
  - Write a 4–6 sentence justification for friction `1.0 0.01 0.005` and solref `0.004 1`, with the physical reasoning and the MuJoCo docs reference. This goes into the fill sheet.
- **L-12:**
  - 500 Hz per-run telemetry: log every physics step (row interval exactly 0.002 s; assert it in a test).
  - Columns: `t, run_id, seed, condition, uav, pos xyz, vel xyz, ref xyz, err xyz, actuator forces ×8, fsm_state, event`.
  - Write one CSV per run to `analytics/runs/` (gitignored), not one row per outer loop.
- **L-13:** Add per-run tracking RMSE (vs the reference path) and control effort ∫τ² dt over the 8 rotor actuators to the runner summary row.
- **Baseline condition:** Model the PRD §9 primary baseline in E043-owned code: a static-guard foot patrol, i.e. a kinematic walker in the same scene on the same 132 m ground loop plus galleries.
  - Walking speed and stop durations are randomised per seed from the distribution defined in §9.
  - Parameters come from a verified source or are labelled `ASSUMPTION`.
  - Its cycle-time and revisit metrics use the same code path as the UAV condition.
- **Runner:** `run_benchmark.py` supports conditions `guard_baseline`, `uav_sectors` and `uav_offset_ring`. It randomises mean wind, gust σ, intruder appearance time and dock jitter (ranges stated in a config dict), records one seed per run, and writes a provenance JSON (seeds, git hash, model hash, versions, timestep, N, duration).
- **Both scenes:** the runner takes `--scene interior|exterior`.
  - The exterior guard baseline walks the campus perimeter route.
  - Interior and exterior each get their own conditions and their own summary rows (add a `scene` column).
- **FR-18:** implement interior obstacle perception and sensed-range avoidance as specified in the rulings above. Add the `min_obstacle_clearance_m` and `obstacle_contacts` columns. Add `tests/test_e043_obstacle_perception.py` covering the class-coverage inventory and zero contacts on a short interior run. Commit it separately.
- Add tests for the logging rate, the RMSE and effort columns, and runner determinism (same seed gives the same summary).
- **NFR-06:** Untrack the two MP4s, keeping the files on disk:

  ```
  git rm --cached docs/figures/exterior/patrol_2x2.mp4 docs/figures/interior/patrol_2x2_interior.mp4
  ```

  Then add `*.mp4` to the group `.gitignore`.

### Phase 2 — Research (1 agent · Sonnet, parallel with Phase 1)

Use WebSearch and WebFetch. Every row records: source type, full reference, URL or DOI, the exact supporting sentence, and a verdict (Verified / Corrected / Delete).

- **L-09 claims:** "72 % latency cut", "11-month CapEx recovery", "90-s verification", "45 → 8.5 min".
- **L-23 standards:** ISO 10218, ISO 3691-4, ANSI/RIA R15.06, IEC 60601-1, India Drone Rules 2021, ISO 21384, ASTM F3322. For each: Yes/No, clause, one-line reason.
- **L-24 baseline:** a guard-patrol baseline (walking speed, rounds per shift, shift pattern) with its primary source.

Output: `docs/research/sources_verified.md`. Unverifiable means `ASSUMPTION`, never invented.

### Phase 3 — Teammate region drafts (3 agents · Sonnet, in parallel, each in its own worktree; never committed)

**E051 (L-14, A-1..A-4):**
- `detect_intruder_hsv` (HSV → morphology → contours → largest bbox; returns detected, bbox, latency_ms).
- `inverse_pinhole_projection` (f = 450 px, 640 × 480).
- IoU against the MuJoCo segmentation ground truth, and latency, at noon vs twilight lighting → `analytics/vision_illumination_benchmark.csv` (real measurements).
- `tests/test_e051_*.py`.
- **Optional YOLO comparison (allowed by sir):** attempt it only if `df -h /` shows at least 6 GB free.
  - Install CPU-only `torch` plus `ultralytics` into a **separate** venv, never into `requirements.txt`.
  - Run a pretrained YOLO person detector on the same frames, and add its IoU and latency rows to `vision_illumination_benchmark.csv` with a `detector` column.
  - Note the AGPL-3.0 licence in `EXPLAIN.md`.
  - If install or space fails, skip it and say so. OpenCV results must not depend on it.

**E075 (L-15, Z-1..Z-4, L-17):**
- `evaluate_geofence_status` (ray-casting point-in-polygon on the VIP Lounge polygon from the scene, tiers 0–3 with hysteresis).
- GPS/IMU noise injection with a stated σ, and a JSON breach log.
- Optionally, return-to-home after at least 2.5 s of telemetry loss.
- `tests/test_e075_*.py`.
- `analytics/statistical_validation.py`: Welch two-sided t, df, exact p, Cohen's d, 95 % CI of the difference, all read from the real-trials CSV. Add an ownership glob for it → E075 in the E043-owned `check_region_ownership.py`.

**E077 (L-04, L-19, L-20, S-1..S-4):**
- Rewrite `analytics/campus_security_economics.py`:
  - inputs come only from the real-trials CSV plus a `SOURCES` dict, each entry carrying a provenance string or `ASSUMPTION`;
  - compute H_reclaimed, P_payback, T_payback, NCRI/κ, ΔFTE, and M/M/c (λ, μ, c, ρ, W_q via Erlang C);
  - sensitivity ±30 % on the most uncertain input, with the break-even marked;
  - write the sensitivity and queue PNGs at 300 DPI.
- FMEA with at least 5 modes, RPN before and after. Each mitigation points to code or a run (the separation test, vision benchmark, geofence log, collision counter).
- No currency anywhere.

Each draft must:
- pass `python src/check_region_ownership.py --author E0xx --base main`;
- pass its own tests.

**Handoff packets** go to `/Users/muaazshaikh/mdriia-project/_handoff/<E0xx>/` (gitignored). Each contains:
- `region.patch`, which applies cleanly on `main`;
- `COMMITS.md`: at least 4 suggested conventional commits, splitting the patch into logical steps, for the member to make from their own account on their assigned branch (`feat/e051-computer-vision-open`, `feat/e075-restricted-zone-geo-`, `feat/e077-csbs-campus-security`);
- `EXPLAIN.md`: a line-by-line walkthrough so they can defend it at the viva;
- `AI_DISCLOSURE.md`: what was AI-drafted, for dossier §5.1 and §6.

E077's packet also gets `GIT_FIX.md` (L-27, S-5). It covers:
- setting the correct commit e-mail, since 8 of 10 commits on her runtime branch use `@mgail.com`;
- re-authoring those commits safely on her own branch, with exact commands;
- parking `feat/e077-guardian-live-surveillance-upgrade` and moving the economics work to `feat/e077-csbs-campus-security`.

It only writes instructions. It does not rewrite her branch.

### Phase 4 — Integration (1 agent · **Opus**, in the integration worktree)

- Apply all three patches on top of the Phase 1 branch.
- Keep FR-18 obstacle avoidance active in every interior condition, and the FSM must never disable it.
- **L-16:** Wire the surveillance FSM: PATROL → DETECT → VERIFY → ALERT(0–3) → TRACK → RETURN_TO_PATROL.
  - The FSM plumbing is E043's code; port it back to the E043 branch as a separate commit. Only the calls into the E051/E075 regions stay integration-only.
  - Log the state on every row.
  - **FR-17 overlay:** show the state as a text overlay in `src/view_live.py`.
  - Show the head-on conflict as the handled failure.
- All tests and the ownership gate must pass.
- **Fallback (PRD §9):** if integration fails, run the batch with detection disabled and record detection latency as "not measured".

### Phase 5 — Monte Carlo batch, L-05 (1 agent · Sonnet; long-running Bash in the background, polled)

- Choose N and run duration from the Phase 0 timing and a **wall-clock budget of 150 min**:
  - **conditions × scenes**: `guard_baseline`, `uav_sectors` and `uav_offset_ring`, each in `interior` and `exterior` (6 cells);
  - N = 50 per cell if it fits, otherwise N = 30. Both are acceptable to sir. Use the same N in every cell;
  - if 6 cells do not fit even at N = 30, run guard vs sectors in both scenes first (4 cells), add offset_ring after, and report what ran;
  - each run must cover at least 2 full ground laps;
  - state the choice and the reason in the provenance JSON.
- Parallelise across CPU cores − 1.
- Run from the integration worktree, and record its git tree hash.
- Output `analytics/campus_patrol_real_trials.csv` plus `analytics/campus_patrol_real_trials.provenance.json`.
- Check the result:
  - row counts equal N × cells;
  - zero interior obstacle contacts; if any occur, report them, do not hide them;
  - no NaNs;
  - seeds are unique.

### Phase 6 — Analysis (3 agents · Sonnet, parallel)

- **Statistics:** run `statistical_validation.py` **per scene**.
  - Primary: guard baseline vs UAV sectors on patrol cycle time / worst revisit.
  - Secondary: sectors vs offset_ring.
  - Also report the interior minimum obstacle clearance (mean, 95 % CI) and the contact count.
  - Save the printed output verbatim.
- **L-18 figures:** regenerate the figures from the real CSV with no watermark:
  - trajectory and box plot for each scene;
  - one interior obstacle-clearance figure (sensor-ray snapshot or clearance histogram). Delete the starter PNGs only after the new ones exist.
- **Economics:** run the rewritten economics script on the real CSV and save its output and graphs. They are E077-owned, so they go in the E077 handoff packet; copy them into the dossier fill sheet.

### Phase 7 — Documents (3 agents · Sonnet, parallel)

**Dossier fill sheet:** `docs/DOSSIER_FILL_SHEET.md`.
- Map every field of the template (PRD §8) to its exact value and source (script plus output line, or reference).
- Correct the template's errors: 8 actuators, not "9 (2×4+1)"; patrol is Alpha on the ground loop and Bravo on the galleries, not NE/SW sectors.
- Include:
  - §2.1 gains table with units;
  - §2.2 authorship table generated from `git log`;
  - §2.3 code snippet of at most 25 lines with line numbers;
  - §2.4 hover FBD worked example (1.35 × 9.81 = 13.24 N → 3.31 N per rotor; T/W = 30 / 13.24 = 2.27);
  - §4 protocol and results tables;
  - §4 provenance boxes, ticked only where true.

**Autofill draft (optional):**
- If python-docx can fill the template's content controls without removing any `w:sdt` element (count them before and after; the counts must be equal), write `docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx`.
- Never modify the original `.docx`.
- The final fill and PDF export are done by a human in Word desktop.

**Viva and admin pack** in `docs/submission/` (E043-owned docs):
- `email_to_sir_DRAFT.md`: thanks sir for the rulings on Q2–Q6 and confirms how we applied them (both scenes, interior obstacle perception, timestep 0.002 s, OpenCV plus optional YOLO, own SAP IDs). It asks only Q1: will the late dossier be accepted, and by when (proposed: Saturday morning before the Expo)? **Do not send it.**
- `video_script_and_shotlist.md`: 3:00–4:00, live sim, business graph, all four on webcam PiP, per Showcase Guide §7.
- `peer_review_template.md`: Groups 06 and 11; humans watch the videos and fill it.
- `ai_audit_candidates.md`: only real AI errors evidenced in this repo or session history, each with proof; for example, the APF-only separation test reached 0.40 m (contact) before the layered fix brought it to 3.29 m, and the template's "9 actuators".
- **L-10:** in the fill sheet, an honest §5.1/§6 AI-use declaration for E043 covering the scene, controller, documents and this workflow, plus the share of AI-drafted work for each member, taken from the handoff `AI_DISCLOSURE.md` files.
- `viva_prep_<E0xx>.md` for each member: the five §14 questions plus questions on their own code, answered with references to files and lines.
- **L-26 (ruling: each member uses their own):** `sap_id_checklist.md`, a one-line instruction per member to enter their own real SAP ID on the dossier cover and in `TEAM_ROSTER.json`. Do not write or change any SAP ID yourself.

### Phase 8 — Adversarial verification (3 agents in parallel: integrity auditor on **Opus**, the other two on Sonnet; all three must pass before Phase 9)

**Roll-number auditor:** walk the coverage matrix row by row for each of E043, E051, E075 and E077.
- Every cell must have an artifact that exists at its stated path.
- Every handoff patch must apply cleanly on `main`, pass that member's tests, and pass the ownership gate for that roll number alone.
- Each `COMMITS.md` must give at least 4 commits.
- Report any gap and fix it before Phase 9.

**Integrity auditor:**
- Grep the deliverables (case-insensitive) for currency words, currency codes and currency symbols, for the deleted constants, and for any SIMULATED or placeholder use.
- Trace every number in `DOSSIER_FILL_SHEET.md` back to a script output line or a verified source. List any number that cannot be traced and fix it.
- Confirm no MP4s, venvs or per-run CSVs are staged.

**Fresh-clone tester:**
- Clone the E043 branch into the scratchpad.
- Create a new venv and run `pip install -r requirements.txt`.
- Run `src/test_env.py` and `pytest`, then a 30 s headless run **in each scene**, then `generate_paper_figures.py`.
- Fix anything missing (NFR-01, L-25).

### Phase 9 — Finish (1 agent · Sonnet)

- Make sure the E043 branch has at least 4 clean conventional commits, all authored by MuaazSM with no trailers. Verify with `git log --format='%an <%ae>%n%B'`.
- Push `feat/e043-lead-uav-flight-dyna` to origin as MuaazSM after the author check in rule 6. Use `git push origin feat/e043-lead-uav-flight-dyna`; never `--force` and never `main`. No PR.
- Update the PRD statuses: copy `prd_v3_status.html` to `prd_v3_1_status.html` with each L-item's new status. Replace §15 with sir's rulings, add FR-18, and update §9 to both scenes. Rebuild with:

  ```
  node docs/planning/source/build_pdf.mjs docs/planning/source/prd_v3_1_status.html docs/planning/MPSTME_GUARDIAN_PRD_v3.1_Status.pdf "PRD v3.1 · Status"
  ```

  Then check the pages visually with pdftoppm.
- **L-08, monorepo PR preparation (do not open the PR):**
  - Build `scratchpad/monorepo_export/Group_05_Muaaz_Aditya_Zaid_Soumya/` from the E043 branch, excluding MP4s, venvs, `analytics/runs/*.csv`, `_handoff/` and `_archive/`.
  - Diff it against the monorepo's current Group_05 folder. Flag any file sir's template has that we lack, and any file over 5 MB.
  - Write `docs/submission/monorepo_pr_steps.md` with the exact fork, branch, copy and PR commands, to run only after teammates' branches are merged and the dossier PDF exists.
- **L-29** (PRD/Implementation Plan v2.1 for the interior scene) is optional: skip it and list it as skipped.

## Final report (print it; do not create other files for it)

1. **One block per roll number (E043, E051, E075, E077)**, following the coverage matrix:
   - each row marked done / drafted / human-only / blocked, with evidence (path or commit hash);
   - the result of `check_region_ownership.py --author E0xx` for that roll number;
   - the ordered to-do list that member still has.

   Then a table of L-01..L-30 with the same statuses.
2. The FR-18 obstacle-class coverage table and interior contact count. Batch facts: N, duration, cells (condition × scene) and wall time, plus the headline statistics as printed by the script (t, df, p, d, CI).
3. What each teammate must do, in order (apply the patch, make their 4 commits, read EXPLAIN.md).
4. The human-only list:
   - L-01: send the email;
   - L-06: Word fill and PDF export;
   - L-07: four Teams turn-ins;
   - L-08: the monorepo PR;
   - L-21: video;
   - L-22: peer review;
   - L-26: each member enters their own SAP ID;
   - Q1: get sir's answer on late acceptance;
   - L-27: Soumya's git e-mail fix;
   - L-30: viva rehearsal.
5. Every assumption made, and every rule check result from Phase 8.

If a phase fails, do not paper over it. Report it, apply the PRD's fallback, and continue with the phases that do not depend on it.
