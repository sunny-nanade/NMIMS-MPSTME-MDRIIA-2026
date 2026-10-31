# Tonight: Part 1 = video-ready in 50 min · Part 2 = overnight run to full marks

Start once and use the same session for both parts:

    cd /Users/muaazshaikh/mdriia-project && git checkout feat/e043-lead-uav-flight-dyna && git pull && \
      ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5 \
      ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5 \
      CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5-5 \
      claude --model claude-fable-5-1

In a second terminal: `caffeinate -i` (Mac plugged in).

---

## PART 1: paste this now (hard stop 22:40)

Use a workflow (multi-agent orchestration). **Hard deadline: everything committed and pushed within 50 minutes.** We record the LinkedIn video at 22:45. Use the existing trial data: **no new Monte Carlo batch in Part 1.** Models: you, the orchestrator, on Fable; `demo-finder` on Opus; every other agent on Sonnet (pass `model` explicitly). About 5 agents. When an agent hits its time box, it commits what passes and reports the rest.

**Context**
- MDRIIA Group 05 "MPSTME GUARDIAN".
- Branch: `feat/e043-lead-uav-flight-dyna`. Group folder: `G = Group_05_Muaaz_Aditya_Zaid_Soumya/`.
- The course faculty does not mark commit attribution, so E043 makes every change.
- Existing data: `analytics/campus_patrol_real_trials.csv`, 30 runs per cell, 6 cells, dt 0.002 s. Its provenance JSON says it came from E043 commit `df9d7d9` plus the E051/E075/E077 draft patches.

**Rules**
- Commit only as `Muaaz Shaikh <170370120+MuaazSM@users.noreply.github.com>`, with Conventional Commits whose scope is the module's roll number. **No `Co-Authored-By`, no `Claude-Session`, no "Generated with Claude Code".**
- Push only as MuaazSM (git `-c credential.helper= -c credential.helper='!f(){ echo username=x-access-token; echo password=$(gh auth token -u MuaazSM); }; f'`) and only to this branch. Never `main`, never force, no PR.
- Never fabricate a number. Every number spoken in the video must come from a script output on the committed CSV.
- Zero currency.
- **Never claim "zero obstacle contacts".** Interior `uav_sectors` seed 7 had 3 contacts. Say "0 contacts in 59 of 60 interior UAV runs; one contact found and being fixed".
- Never claim separation ≥ 2.5 m in `offset_ring`: its minimum was 1.63 m.
- Patrol is inside the college. Never commit MP4s.

**A. `integrate` (Sonnet, 20 min).** Start immediately.
- Apply `/Users/muaazshaikh/mdriia-project/_handoff/E051/region.patch` and `_handoff/E075/region.patch`.
- From `origin/integration/e043-e077-guardian` take **only**:
  - `analytics/campus_security_economics.py`, `campus_security_fmea.py`, `campus_security_dossier_fill.py`;
  - `analytics/figures/campus_security_{queue,sensitivity}.png`;
  - `tests/test_e077_economics.py`.
- Fix PR #5's bugs:
  - **(1)** when the revisit gate FAILs, report κ, NCRI and payback as "n/a (gate FAIL)";
  - **(2)** add `.gitattributes` with `Group_05_Muaaz_Aditya_Zaid_Soumya/analytics/*.csv -text`;
  - **(3)** compute the typed-in claim strings in `campus_security_dossier_fill.py` from the data;
  - figures at 300 DPI.
- Make sure `select_tracking_uav` exists, from E051, with a `hasattr` fallback.
- Run `pytest -q` until green, re-running only the touched test files.
- One commit per module: `feat(e051)`, `feat(e075)`, `feat(e077)`, `fix(e077)`, `chore(e043)`. Push.

**B. `video-kit` (Sonnet, 35 min, in parallel with A).**
- Run the statistics on the committed CSV (E075's `statistical_validation.py` from the patch, or stdlib if A isn't done). Write `docs/submission/VIDEO_NUMBERS.md`, which may use only printed outputs. It holds:
  - the headline guard vs `uav_sectors` cycle time per scene (means, Welch t, df, p, Cohen's d, 95 % CI);
  - detection results with their honest caveats (interior 11/30, the same as the guard);
  - min clearance and separation, stated honestly;
  - the economics headline (κ, NCRI, P_payback, the M/M/c line), from the E077 script output.
- Rewrite `docs/submission/video_script_and_shotlist.md` as a **3:30 script, timed per line**:
  - who speaks each line (all four on webcam PiP), and the on-screen asset for each shot;
  - no PPT slides; the showcase guide requires a live sim and a business graph;
  - the hook (the authorised title as a question), the problem and baseline, the physics (MJCF, 0.002 s, 8 rotors, control law), the live interior and campus FSM, the handled failure (head-on conflict resolved), the results numbers, the business graph, limits, and a close with the repo link;
  - a LinkedIn post text with the tags list (teammates, MPSTME, the course faculty, monorepo folder link) and hashtags from the showcase guide (fetch it from sir's repo).
- Copy the existing result figures plus the business graphs into `docs/submission/video_assets/` (PNG only).

**C. `demo-finder` (Opus, 30 min; start once A has applied the patches).**
- Find, by short headless runs, **exact commands** that show the FSM going PATROL→DETECT→VERIFY→ALERT→TRACK→RETURN **within the first 60–90 s**, in the interior and in the campus scene. Use `src/view_live.py` flags for seed, scene and `--rays`.
- Find the command for the head-on conflict as the handled failure.
- Write `docs/submission/video_shots.sh` (macOS: `mjpython src/view_live.py ...`), with a numbered menu of the shots:
  1. interior FSM + sensor rays;
  2. campus inside the wall;
  3. head-on failure handled;
  4. the business graph opened in Preview.
- Also render backup clips with `src/render_scene_media.py` to `docs/figures/video_backup/`, gitignored, never committed, in case the live viewer stutters while recording.
- Test every command once. Commit the script and push.

**D. 22:35: `wrap` (Sonnet).**
- Run the full `pytest`.
- Run the trailer and author check.
- Push.
- Print:
  - the exact shot commands;
  - the path of `VIDEO_NUMBERS.md` and the script;
  - anything not done.

---

## PART 2: paste this after recording (about 23:45; about 1.5–2 h; separate branch, Part 1 untouched)

Use a workflow (multi-agent orchestration). Execute `Group_05_Muaaz_Aditya_Zaid_Soumya/docs/planning/WORKFLOW_PROMPT_FAST_20.md` with the overrides below. **Overrides win over FAST_20 wherever they differ.**

### Isolation (do this first; never break it)
- **Do not modify, commit to, reset, rebase or push `feat/e043-lead-uav-flight-dyna`.** Do not change the files in `/Users/muaazshaikh/mdriia-project` (the main checkout). The video was recorded from it and it must stay exactly as Part 1 left it.
- Create a new branch and a separate worktree from the current tip of the Part 1 branch:

  ```
  cd /Users/muaazshaikh/mdriia-project
  git fetch origin
  git worktree add -b feat/e043-overnight-full-marks /Users/muaazshaikh/mdriia-overnight origin/feat/e043-lead-uav-flight-dyna
  ```

- Do **all** work, runs, commits and tests inside `/Users/muaazshaikh/mdriia-overnight` only. The group folder there is `/Users/muaazshaikh/mdriia-overnight/Group_05_Muaaz_Aditya_Zaid_Soumya` (call it `G`).
- Use the existing venv by absolute path, `/Users/muaazshaikh/mdriia-project/.venv/bin/python` (and `mjpython`). Never pip-install into it; install anything new into a scratchpad venv.
- Run outputs (`analytics/runs/`, backup clips) go only inside the worktree.
- **Push only `feat/e043-overnight-full-marks`**, as MuaazSM:

  ```
  git -c credential.helper= -c credential.helper='!f(){ echo username=x-access-token; echo password=$(gh auth token -u MuaazSM); }; f' push -u origin feat/e043-overnight-full-marks
  ```

  Never `main`, never the Part 1 branch, never force, **no PR and no merge**. The user decides tomorrow whether to merge it into the Part 1 branch.
- At the very end, prove isolation and print the result:
  - `git -C /Users/muaazshaikh/mdriia-project status --short` shows nothing new from this run;
  - `git rev-parse origin/feat/e043-lead-uav-flight-dyna` is unchanged from its value at the start.

### Skip (Part 1 did these): verify them instead
- Integration of E051/E075/E077 and PR #5 bugs 1 and 2. Check that `.gitattributes` has the CSV `-text` rule and that "n/a (gate FAIL)" exists in the economics script and its tests.

### Finish what Part 1 left open (econ agent)
- **PR #5 bug 3, remaining part:** `analytics/campus_security_dossier_fill.py` must verify the CSV sha256 against the provenance JSON, and must refuse to embed `campus_security_*.png` older than the CSV.
- **CSV hash source:** `analytics/campus_security_economics.py` (and any other script) must read the expected CSV sha256 from `analytics/campus_patrol_real_trials.provenance.json`, not from a constant. Otherwise the rerun breaks it.
- **Stale FMEA text:** the economics/FMEA output still says "pending E051 merge" / "pending E075 merge" for the twilight and geofence rows. Replace that with measured ablation results (G-15). Never say "pending".

### Speed overrides
- UAV run duration **300 s** in both scenes (≥ 4 laps; cycle time is the window-independent primary metric). Guard runs keep their durations (< 20 s wall each).
- Worst-revisit equal-window comparison: compute the guard's metric over the same 300 s window from its 500 Hz telemetry. No extra guard runs.
- Ablations: 4 modes × 2 arms × N = 10, 90 s runs.
- Start the batch on cores − 1 the moment `flight-fixes` passes its gate. Build the documents, figures and viva generators while it runs.
- Target total ≤ 100 min.

### Keep from FAST_20
- **A1 `flight-fixes` (Opus):** G-06 atrium contact, G-07 separation, G-08, G-09..G-14.
- **A2:** economics G-15..G-18 with ablation arms; standards G-19/G-20; course sync and audit G-21/G-22.
- **Phase B:** main batch with 500 Hz gz telemetry for every run, plus ablations.
- **Phase C:** statistics, figures, economics, dossier fill sheet and autofill, viva prep.
- **Phase D:** integrity audit (Opus), tests, sir's audit, fresh clone **of the new branch**, push of the new branch.

### Also
- Leave the LinkedIn video URL in §5 as a HUMAN field.
- Write `docs/submission/VIDEO_VS_FINAL_NUMBERS.md`. Show every number spoken in the video (from the Part 1 `VIDEO_NUMBERS.md`) next to its new value, with the reason for each change: the fixes and the 300 s window. The video used the first batch and the dossier uses this rerun; both are honest, and the dossier is authoritative.
- Write `docs/submission/MERGE_TOMORROW.md` with:
  - the diff summary `feat/e043-lead-uav-flight-dyna..feat/e043-overnight-full-marks`;
  - which checks passed;
  - the exact commands to fast-forward or merge it into the Part 1 branch if the user approves.
- **Same rules as FAST_20:** MuaazSM only, no Claude trailers, no fabrication, zero currency, never invent human-only fields.

### Final report
- Give FAST_20's final report, plus:
  - the isolation proof;
  - the new branch name and head sha;
  - the human list for Saturday morning: merge decision, Word dossier, PDF, 4× Teams turn-in, monorepo PR, email, Expo rehearsal.
