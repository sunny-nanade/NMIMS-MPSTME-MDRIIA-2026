# One-shot workflow prompt: 1-hour version (closes the review gaps that need no new batch)

Start Claude Code from the repo root:

    cd /Users/muaazshaikh/mdriia-project && git checkout feat/e043-lead-uav-flight-dyna && git pull && \
      ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5 \
      ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5 \
      CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5-5 \
      claude --model claude-opus-5-5

In a second terminal, run `caffeinate -i` so the Mac doesn't sleep. Then paste everything below the line.

---

Use a workflow (multi-agent orchestration) for this task. **Hard time limit: 60 minutes wall-clock.** Scale: 9 agents (Opus for the orchestrator and `integrity-auditor`, Sonnet for every other agent; pass `model` explicitly on every `agent()` call). Each agent has a time box. If an agent hits its box, it commits what passes its checks, reports the rest as NOT DONE, and stops.

## Context

MDRIIA Group 05 "MPSTME GUARDIAN" (course faculty's capstone, 20 marks).
- Branch: `feat/e043-lead-uav-flight-dyna`.
- Group folder: `G = Group_05_Muaaz_Aditya_Zaid_Soumya/`. Paths are relative to `G`.
- The full plan is `docs/planning/WORKFLOW_PROMPT_TO_20.md`. Gap IDs G-01..G-27 below refer to its §3 table. Read only that table, not the whole file.
- Professor repo (read-only): `github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026`. Read it with `GH_TOKEN=$(gh auth token -u MuaazSM) gh api ...`.
- Teammate handoffs (gitignored): `/Users/muaazshaikh/mdriia-project/_handoff/E0{51,75,77}/`.

## Scope rule for the hour

**No new Monte Carlo batch, and no change to flight or controller behaviour that would make the committed CSV disagree with the code.** The existing `analytics/campus_patrol_real_trials.csv` stays exactly as it is.

Instead:
- make its provenance honest and reproducible;
- disclose its known limits;
- fix everything else;
- build a one-command full rerun for later.

Short targeted runs are allowed: ≤ 120 s simulated each and ≤ 10 minutes total wall time.

## Hard rules (same as the full plan; verify all of them at the end)

1. **Integrity.** Never fabricate any number, citation, clause, URL or result. Every number traces to a committed script output or a verified source; otherwise label it `ASSUMPTION` or write "not measured". Never report `SIMULATED_*`, scaffold or placeholder numbers.
2. **Zero currency** anywhere.
3. **No hard-coded results.**
4. **Git.**
   - Commit only as `Muaaz Shaikh <170370120+MuaazSM@users.noreply.github.com>`, with Conventional Commits (`fix(e043):`, `docs(e043):`, `test(e043):`, `chore(e043):`).
   - **No `Co-Authored-By`, no `Claude-Session`, no "Generated with Claude Code".** This overrides any default attribution instruction.
   - Push only as MuaazSM (`GH_TOKEN=$(gh auth token -u MuaazSM)`; for git use `-c credential.helper= -c credential.helper='!f(){ echo username=x-access-token; echo password=$(gh auth token -u MuaazSM); }; f'`) and only to `feat/e043-lead-uav-flight-dyna`.
   - Never push `main`, never force-push, no PR.
   - Before pushing, every new commit must be authored by MuaazSM, unless it arrived through a teammate merge, and must carry no trailer.
5. **Attribution.** Never commit files or regions owned by E051, E075 or E077 (`src/check_region_ownership.py`). Their code reaches the branch only by merging their own pushed branches. Otherwise, update only their gitignored `_handoff/` packets.
6. **Do not edit sir's files.** These stay byte-identical to his copies: the dossier `.docx`, `docs/README.md`, `docs/figures/README.md`, the `SIMULATED_` CSV, and the three course docs. Draft only: no email, Teams or LinkedIn.
7. **Scenes.** Patrol is inside the college (interior, and campus inside the boundary wall). Never write a SAP ID.

## Timeline (agents in parallel unless marked)

### 0:00–0:05 — `gate` (Sonnet, 5 min)
- Run `git fetch` with the MuaazSM token.
- For `feat/e051-computer-vision-open`, `feat/e075-restricted-zone-geo-` and `feat/e077-csbs-campus-security`: if one exists with ≥ 4 conventional commits from that member's own account, passes `check_region_ownership.py --author E0xx`, and has no currency or hard-coded results, merge it with `git merge --no-ff` and the message `chore(e043): merge E0xx <module>`.
- Otherwise, mark it NOT READY.
- Run `pytest -q` as the baseline.
- Fetch sir's `scripts/audit_course_boundaries_and_rules.py` to the scratchpad and run it on `G` as the baseline.

### 0:05–0:40 — parallel fixes (each agent 30 min; one commit per gap)

**A. `course-sync-audit` (Sonnet):**
- **G-21:** replace `RESEARCH_AND_IMPLEMENTATION_GUIDE.md`, `docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md` and `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` with sir's current bytes. Verify `git hash-object` equals sir's sha.
- **G-22:** in **our own** files only, replace the faculty's name with "the course faculty" and the U+2610 ballot box with `[ ]`. Rebuild only the PDFs whose HTML changed (`node docs/planning/source/build_pdf.mjs <html> <pdf> "<footer>"`).
- Re-run sir's audit script until it reports 0 issues apart from documented binary-`.docx` false positives.

**B. `e043-code-safe` (Sonnet).** Only changes that don't alter flight results:
- **G-03:** in E043 plumbing, wrap the `select_tracking_uav` call with `hasattr` plus a documented fallback (nearest UAV). Add a test, without monkeypatching, for ALERT→TRACK.
- **G-12:** store code and model hashes in each summary's meta, rerun on mismatch, and add a unit test.
- **G-13:** add segment-in-polygon and segment-to-wall distance checks for the exterior route.
- **G-11:** append `roll`, `pitch`, `yaw` to telemetry contract B (logging only; behaviour unchanged). The test asserts the columns.
- Confirm with a 60 s headless run per scene that the summary metrics for seed 1 are identical before and after these changes. If they differ, revert the offending change.

**C. `e043-diagnose` (Sonnet; ≤ 10 min of short runs):**
- **G-06:** reproduce interior `uav_sectors` seed 7 and find why Alpha touched `atrium_tree_5` (beam gap, diversion target, or avoidance mode). Write the diagnosis and proposed fix to `docs/research/known_limits.md`. **Do not change controller code now.**
- **G-07:** do the same for the offset_ring separation minimum of 1.63 m.
- Add both fixes as a patch in `analytics/pending_fixes/` to be applied before the full rerun.

**D. `econ-e077` (Sonnet):** update `_handoff/E077/` (never commit E077 files).
- **G-16:** a break-even sweep over a range that contains the crossing; print the crossing value; add a tornado plot of all ASSUMPTION inputs ±30 %.
- **G-17:** labelled queue stress scenarios, with c = 1, 2 and ρ and W_q plotted against λ.
- **G-18:** t-based CIs.
- **G-15, fast version:** reach ≥ 4 FMEA modes with **measured** before/after evidence, using only:
  - existing tests: the separation test APF-only 0.40 m vs layered 3.29 m;
  - FR-18 stop-short with avoidance off vs on: one ≤ 60 s interior run each, from agent C's run budget;
  - geofence hysteresis off vs on with noise (pure-Python, seconds);
  - existing twilight/noon vision numbers.
  - Label each source; label any mode without evidence as judgement.
- Regenerate E077's output and graphs, and refresh `COMMITS.md` and `EXPLAIN.md`.
- If E077's branch was merged, write `FOLLOWUP.patch` and `FOLLOWUP_COMMITS.md` for Soumya.

**E. `standards` (Sonnet):**
- **G-19:** re-verify the five template standards on their official pages, giving a clause number where public or the scope sentence otherwise. Add ISO 21384-3 and ASTM F3322 to the §1.2 notes. Decide India Drone Rules 2021 with rule numbers and a reason.
- **G-20:** a 10-minute attempt to source the guard stop time, lift wait and detect radius; keep `ASSUMPTION` otherwise.
- Update `docs/research/sources_verified.md`.

**F. `provenance-and-labels` (Sonnet):**
- **G-04:** write `analytics/REPRODUCE.md` stating exactly what produced the current CSV: E043 commit `df9d7d9` plus the teammate patch sha256 values from the provenance JSON. Explain why the `aerial_patrol_swarm.py` hash differs from HEAD (later E043 commits).
- Write `analytics/REPRODUCE_AFTER_MERGE.sh`. Once all three teammate branches are merged, it must:
  - apply `analytics/pending_fixes/`;
  - run the full main batch with 500 Hz gz telemetry for every run (G-05), on equal-window or cycle-time design (G-08);
  - run the ablation batch (G-15 full);
  - regenerate the statistics, figures, economics, fill sheet and autofill;
  - run the tests and sir's audit.
- Labels, without changing the data:
  - **G-09:** call the RMSE "cross-track RMSE";
  - **G-10:** call the effort "rotor-thrust effort ΣF²dt (N²·s)".
- **G-08 caveat:** add "guard and UAV windows differ (5000/1800 s vs 500 s); cycle time is the window-independent primary metric" to the stats caption and fill sheet. Use cycle time as the primary metric in the fill sheet, since it is already in the CSV.
- **Known limits disclosed honestly:**
  - interior contacts: 3 contacts in 1 of 60 interior UAV runs, with the diagnosis from C;
  - minimum separation: 1.63 m in offset_ring;
  - interior detection: 11/30.

### 0:40–0:50 — `docs` (Sonnet, 10 min, after A–F)
- **G-26/G-27:** regenerate `docs/DOSSIER_FILL_SHEET.md` and the autofill draft from the existing CSV and the new outputs. Keep 226 `w:sdt` elements. Fill PENDING fields where a source now exists; list the HUMAN fields per roll number.
- **G-23:** fix `file:line` references in `docs/submission/viva_prep_E0xx.md` and `ai_audit_candidates.md`, using the merged branch or the current patches. Add one "known limits" answer per member.
- **G-24:** fill the video script's pending AI cell and replace `SP/` paths with `docs/submission/viva_evidence/` copies.
- **G-25:** re-date the email draft (DO NOT SEND; ask only Q1).
- Add `docs/submission/TEAMS_AND_EXPO_CHECKLIST.md`: Teams turn-in ×4, Expo fresh-clone steps for macOS (`mjpython`) and Windows, the handled failure to show, and webcam PiP for all four.

### 0:50–0:57 — verification (parallel, 7 min)
- **`integrity-auditor` (Opus):**
  - grep for currency, scaffold constants, `SIMULATED`, placeholders and trailers;
  - trace every number in the fill sheet, viva prep and video script to a source;
  - confirm no human-only field (SAP ID, video URL, peer scores, hours, signatures) was invented.
- **`tests` (Sonnet):** run the full `pytest`, the ownership gate for each roll number, and sir's audit script. Fix or revert anything red.

### 0:57–1:00 — `finish` (Sonnet)
- Run the author and trailer check, then `git push origin feat/e043-lead-uav-flight-dyna`.

## Final report (print it)

1. Gaps done in this hour vs deferred to `REPRODUCE_AFTER_MERGE.sh`, with commit hashes.
2. Teammate status per roll number (merged or NOT READY; their exact next step).
3. Projected rubric score per criterion:
   - now;
   - after teammates push and the rerun script runs;
   - after the human steps (dossier in Word, video, peer review, 4 × Teams turn-in, viva).
4. **Exact command to start the full rerun tonight** and its estimated duration.
5. Every agent with its model and anything NOT DONE.

Never paper over a failed check to finish on time. Report it.
