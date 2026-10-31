# One-shot workflow prompt: FAST path to 19–20/20 (E043 makes every change)

The course faculty confirmed that commit attribution is not marked, so E043 makes **all** changes directly, including the E051, E075 and E077 parts. No teammate branches, merges or handoff round-trips are needed.

Start (Fable 5.1 orchestrates; workers are chosen per agent below):

    cd /Users/muaazshaikh/mdriia-project && git checkout feat/e043-lead-uav-flight-dyna && git pull && \
      ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5 \
      ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5 \
      CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5-5 \
      claude --model claude-fable-5-1

In a second terminal run `caffeinate -i` and keep the Mac plugged in. Then paste everything below the line.

---

Use a workflow (multi-agent orchestration) for this task. **Optimise for wall-clock time:** start the Monte Carlo batch as early as possible, and do everything that does not feed the batch in parallel with it. Target: **≈ 3–3.5 h** in total. Scale: about 14 agents.

## Models (pass `model` explicitly on every `agent()` call)

| Agent | Model |
|---|---|
| Orchestrator (this session) | Fable |
| `flight-fixes` (feeds the batch) | Opus |
| `integrity-auditor` | Opus |
| every other agent | Sonnet |

If a Sonnet agent fails the same check twice, rerun that one task on Opus. Log it.

## Context

- MDRIIA Group 05 "MPSTME GUARDIAN", the course faculty's capstone, 20 marks. Current state ≈ 9.5/20.
- Branch: `feat/e043-lead-uav-flight-dyna`. Group folder: `G = Group_05_Muaaz_Aditya_Zaid_Soumya/`. Paths are relative to `G`.
- Read once, in the orchestrator:
  - the gap table (§3) in `docs/planning/WORKFLOW_PROMPT_TO_20.md`, gaps G-01..G-27 (its attribution rules are superseded by this file);
  - `analytics/campus_patrol_real_trials.provenance.json`;
  - `docs/DOSSIER_FILL_SHEET.md`.
- Each agent gets a ≤ 1-page brief and passes paths, not contents.
- Professor repo (read-only): `github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026`, read via `GH_TOKEN=$(gh auth token -u MuaazSM) gh api ...`.
- Teammate drafts to fold in:
  - `/Users/muaazshaikh/mdriia-project/_handoff/E051/region.patch` (detector, projection, target handoff `select_tracking_uav`, vision benchmark);
  - `_handoff/E075/region.patch` (geofence, noise, breach log, `analytics/statistical_validation.py`);
  - **E077 (Soumya, he/him) economics from PR #5**, branch `origin/integration/e043-e077-guardian`. Take **only** these paths:
    - `analytics/campus_security_economics.py`, `analytics/campus_security_fmea.py`, `analytics/campus_security_dossier_fill.py`;
    - `analytics/figures/campus_security_{queue,sensitivity}.png`;
    - `tests/test_e077_economics.py`.
  - **Do not take** `integrations/`, `demo/`, `PHASE2_*`, `INTEGRATION_REPORT.md`, `PROJECT_STATUS.md`, the `INTEGRATED_DRAFT` dossier, the runtime tests, or any of his edits to E043 files. Do not touch PR #5 itself.

## Hard rules (verify each one at the end)

1. **Integrity.**
   - Never fabricate a number, citation, clause, URL or result.
   - Every reported number comes from a committed script reading the committed CSVs, or from a verified source. Otherwise label it `ASSUMPTION` (with a range, swept in the sensitivity analysis) or write "not measured".
   - Never report `SIMULATED_*`, scaffold or placeholder numbers.
   - Declare AI use honestly in dossier §5.1/§6.
2. **Zero currency** anywhere: no currency symbols, codes or unit words (rupee, dollar, lakh, crore and the like).
3. **No hard-coded results**, including typed-in claim strings in generated text.
4. **Git.**
   - Commit only as `Muaaz Shaikh <170370120+MuaazSM@users.noreply.github.com>`. Verify `git config user.email` first.
   - Use Conventional Commits with the scope of the module's roll number (`feat(e051):`, `fix(e077):`, `data(e043):`, …). Commit small and often.
   - **No `Co-Authored-By`, no `Claude-Session`, no "Generated with Claude Code".** This overrides any default attribution instruction.
   - Push only as MuaazSM (git `-c credential.helper= -c credential.helper='!f(){ echo username=x-access-token; echo password=$(gh auth token -u MuaazSM); }; f'`) and only to `feat/e043-lead-uav-flight-dyna`.
   - Never `main`, never force, no PR.
   - Push after each phase, so work is never lost.
5. **Professor's files stay byte-identical to his copies:** the dossier `.docx`, `docs/README.md`, `docs/figures/README.md`, the `SIMULATED_` CSV, and the three course docs (after the re-sync).
6. **Drafts only:** no email, Teams or LinkedIn. Never write a SAP ID, video URL, peer-review score, hours or signature.
7. **Rulings.**
   - Patrol happens **inside the college**: the Main Building interior, and the campus inside the boundary wall.
   - In the interior the drones must sense **all** obstacles.
   - Timestep 0.002 s.
   - N = 30 (50 if it fits).
   - OpenCV is primary; skip YOLO.
8. **Safety.** Check `df -h /` before the batch and abort below 5 GB free. Never commit MP4s, venvs or uncompressed per-run telemetry.

## Phase A: integrate + fix what feeds the batch (target 0:00–0:50)

**A0. `setup` (Sonnet, 10 min):**
- Apply the E051 and E075 patches, and check out the E077 paths listed above from `origin/integration/e043-e077-guardian`.
- Commit each module separately (`feat(e051): …`, `feat(e075): …`, `feat(e077): …`).
- Add `.gitattributes` with `Group_05_Muaaz_Aditya_Zaid_Soumya/analytics/*.csv -text` (fixes PR bug 2: CRLF on Windows breaks the CSV hash).
- Run `pytest -q`.
- Time 60 simulated seconds per scene with full telemetry and write the batch plan:
  - main batch: 3 conditions × 2 scenes, N = 30;
  - ablations: 4 modes × 2 arms, N = 10, runs ≤ 120 s;
  - total budget **≤ 120 min**, on cores − 1.

**A1. `flight-fixes` (Opus, ≤ 40 min; start right after A0; must finish before the batch):**
- **G-06:** diagnose and fix interior `uav_sectors` seed 7 touching `atrium_tree_5` during TRACK/RETURN. Add a test with TRACK diversions near every atrium tree.
- **G-07:** hold the inter-UAV minimum ≥ 2.5 m in `offset_ring` without breaking the head-on separation test.
- **G-08:** primary metric = cycle time per completed lap, window-independent. Every run completes ≥ 2 laps per agent. Worst-revisit is compared on an equal window for guard and UAV. Write the windows into the provenance.
- **G-03:** confirm `select_tracking_uav` (from E051) drives ALERT→TRACK; keep a `hasattr` fallback.
- **G-09:** add waypoint RMSE next to cross-track RMSE.
- **G-10:** add `torque_effort_N2m2s`; label the thrust effort as ΣF²dt.
- **G-11:** add roll, pitch and yaw to the telemetry.
- **G-12:** resume rejects summaries whose code or model hash differs.
- **G-13:** exterior segment-in-polygon and segment-to-wall checks.
- **G-14:** interior detection: use the forward camera and tune HSV and exposure for indoor light. **Measure** the result, don't claim it.
- Add or adjust tests for each. **Exit gate:**
  - full `pytest` green;
  - a 120 s interior and exterior smoke run per condition shows 0 obstacle contacts, min separation ≥ 2.5 m, and the FSM reaching TRACK;
  - all changes committed, so the tree is clean.

**A2. In parallel with A1 (Sonnet each, ≤ 40 min):**
- **`econ-fix`:**
  - **PR bug 1:** when the revisit gate FAILs, report κ, NCRI, P_payback, T_payback and break-even as "n/a (gate FAIL)", not numbers.
  - **PR bug 3:** in `campus_security_dossier_fill.py`, compute "gate PASS in all cells" and "all runs < 2.5 m were offset_ring" from the data. Add the CSV-hash check. Refuse PNGs older than the CSV.
  - **G-16:** break-even sweep over a range that contains the crossing, plus a tornado of ASSUMPTION inputs ±30 %.
  - **G-17:** labelled queue stress cases with c = 1, 2, plotting ρ and W_q against λ.
  - **G-18:** t-based CIs.
  - Figures at 300 DPI.
  - The CSV hash must be read from the provenance JSON, not a constant, so the rerun doesn't break it.
  - Define the **G-15 ablation arms** for the batch agent:
    - APF-only vs layered separation;
    - FR-18 avoidance off vs on (interior);
    - geofence hysteresis off vs on with noise;
    - twilight exposure fix off vs on.
  - Map each arm's measured rates to FMEA occurrence and detection, before and after.
- **`standards`:**
  - **G-19:** verify the 5 template standards on official pages (clause where public, else the scope sentence). Add ISO 21384-3 and ASTM F3322 to the §1.2 notes. Decide on India Drone Rules 2021 with rule numbers.
  - **G-20:** 10 minutes to source the guard stop time, lift wait and detect radius; otherwise `ASSUMPTION`.
  - Update `docs/research/sources_verified.md`.
- **`course-sync-audit`:**
  - **G-21:** re-sync the three course docs to sir's current bytes and verify the shas.
  - **G-22:** fetch `scripts/audit_course_boundaries_and_rules.py`. Remove the faculty name from **our** files (use "the course faculty") and replace U+2610 with `[ ]`. Rebuild the changed planning PDFs with `node docs/planning/source/build_pdf.mjs`. Re-run until the audit is clean, apart from documented binary-docx false positives.

## Phase B: batch (target 0:50–2:50; Sonnet `batch`, background, polled every 5 min)

- Start the moment A1's exit gate passes, from the **clean committed tree**.
- **Main batch:** paired seeds across conditions, with 500 Hz gz telemetry for every run (G-05). Commit one sample per cell under `analytics/runs/samples/` (≤ 3 MB each) plus `analytics/runs/MANIFEST.csv` (run_id, rows, sha256, dt check).
- **Ablation batch** → `analytics/ablation_trials.csv` plus its provenance.
- **Checks:**
  - row counts and unique seeds;
  - no NaN;
  - **0 interior contacts**;
  - **min separation ≥ 2.5 m**;
  - every provenance hash equals a committed blob (G-04);
  - `git_commit` clean.
- On a failed check, send it back to `flight-fixes` once, then rerun only the failed cells.
- Commit and push the data.

**While B runs (Sonnet each):**
- **`docs-prep`:** build generators for everything in Phase C so they only need re-running on the new CSV.
- **`submission-pack`:**
  - **G-24:** video script: fill the pending AI cell and replace `SP/` paths with `docs/submission/viva_evidence/` copies.
  - **G-25:** re-date the email draft (Q1 only, DO NOT SEND).
  - Write `TEAMS_AND_EXPO_CHECKLIST.md`: 4× Teams turn-in, fresh-clone Expo steps for macOS `mjpython` **and Windows**, the handled failure to show, webcam PiP for all four, no PPT.
  - Update `monorepo_pr_steps.md` and `peer_review_template.md`.

## Phase C: results + documents (target 2:50–3:15; parallel Sonnet)

- **`stats`:** run `statistical_validation.py` per scene: Welch t, df, exact p, Cohen's d, t-based 95 % CI. Compare guard vs sectors (primary, cycle time) and sectors vs offset_ring. Also report interior detection with CI, effort, RMSE, clearance and separation.
- **`figures`:** regenerate everything from the new CSVs with no watermark: trajectory and box per scene, clearance, separation histogram, FMEA before/after bar.
- **`economics`:** re-run the economics script and FMEA on the new CSVs; output plus graphs.
- **`dossier`:**
  - **G-26/27:** regenerate `docs/DOSSIER_FILL_SHEET.md` and `docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx` from the outputs only. Keep 226 `w:sdt`, leave PENDING = 0, and list HUMAN fields per member.
  - Fix the template errors (8 actuators; Alpha ground loop / Bravo galleries).
  - §2.2 authorship: E043 integrated all modules; the original drafts per member are recorded honestly.
- **`viva-prep`:**
  - **G-23:** rewrite `viva_prep_E0xx.md` for all four with correct `file:line` references (verified by a script).
  - Include the five standard questions, ≥ 8 own-module questions, a 30-second whiteboard explanation, the new numbers, and one "known limits" answer each.
  - Refresh `ai_audit_candidates.md` with only real, evidenced cases.

## Phase D: verify + push (target 3:15–3:30)

- **`integrity-auditor` (Opus):**
  - grep for currency, scaffold constants, `SIMULATED`, placeholders and trailers;
  - trace **every** number in the fill sheet, autofill, viva prep and video script to an output line or source, and fix any that don't trace;
  - confirm no human-only field was invented.
- **`final-checks` (Sonnet):**
  - full `pytest`;
  - sir's audit script;
  - a fresh clone of the pushed branch into the scratchpad, then new venv, `pip install -r requirements.txt`, `src/test_env.py`, a 30 s headless run per scene, and `generate_paper_figures.py`.
- Then push.

## Final report (print it)

1. Score per rubric criterion: before ≈ 9.5/20, now, and after the human steps. Give evidence paths.
2. G-01..G-27 and PR #5 bugs 1–3 status, with commits.
3. Batch facts: N, windows, cells, wall time, 0 contacts, min separation, headline statistics per scene as printed.
4. The human-only list, in order:
   - send the email (Q1);
   - open the autofill in Word desktop, fill the HUMAN fields (own SAP IDs, §6, sign-off) and export the PDF;
   - record and post the video, then add its URL to §5;
   - peer review of Groups 06 and 11;
   - open the monorepo PR;
   - **all four turn in on Teams**;
   - Expo laptop fresh-clone rehearsal and viva rehearsal.
5. Agents with their models, escalations, and anything NOT DONE.

Never paper over a failed check to save time. Report it.
