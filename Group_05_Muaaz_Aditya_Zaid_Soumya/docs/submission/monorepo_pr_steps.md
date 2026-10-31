# Monorepo pull request steps (L-08)

Status: prepared, not run. Nothing below has opened a pull request or pushed to the course monorepo. Do NOT run steps 1 to 4 until all three conditions hold:
1. [ ] The final E043, E051, E075 and E077 work is committed on one branch ("the merged branch"). Merging into it is the team's decision; the course faculty confirmed that commit attribution is not marked, so the work was done on one branch rather than four.
2. [ ] The dossier PDF exists: `docs/MDRIIA_Group_05_Technical_Dossier.docx` filled in Word desktop (not Google Docs) and exported to `docs/MDRIIA_Group_05_Technical_Dossier.pdf` (original names, Guide section 2).
3. [ ] The LinkedIn post is live and its URL is in the dossier Section 5 and in `docs/TEAM_ROSTER.json` (`linkedin_url`) (a HUMAN field), or the team has decided to submit with the video link marked as not yet posted.

Target repository: `https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026`. `main` is protected: no direct commits, work goes through a branch and a pull request (monorepo README, "Student Git Submission & Branching Hygiene"). The pull request is opened from one member's fork; dossier Section 6 asks for each member's commit share, which each member reads for themselves from `git shortlog -sn -- Group_05_*/` and states honestly, without claiming commits they did not make.

Rules for every step: author identity is the person running the step's own; Conventional Commits; no AI attribution in any commit message, PR title or PR body; no force-push; no videos, virtual environments or large binaries (Guide section 4); the pull request touches only `Group_05_Muaaz_Aditya_Zaid_Soumya/`.

## Dry run: repeat it on the merged branch

An earlier dry run (30 Oct 2026, before the final merge) built the export with `git archive` of the group folder only and compared it with the monorepo's current `Group_05_Muaaz_Aditya_Zaid_Soumya/` through a read-only GitHub API listing. Its counts are out of date and are not reproduced here: repeat the check on the merged branch and write down what you see. What to check and what was found structurally:
- [ ] Export holds no MP4, no virtual environment, no `analytics/runs/` per-run telemetry, no `_handoff/`, no `_archive/`. `git archive` leaves untracked files out by itself, so the two patrol MP4s (not tracked) stay out.
- [ ] No file over 5 MB (the sizes check in step 2 prints nothing). Record the folder size from `du -sh`: ______
- [ ] FLAG, files the course template has that we lack: `docs/figures/figure1_system_architecture.png`, `docs/figures/figure2_kinematic_telemetry.png`, `docs/figures/figure3_comparative_performance.png`. These starter figures are placeholders (np.random targets) and must never be reported. We replaced them with figures regenerated from the real-trials CSV (`revisit_boxplot_*.png`, `trajectory_*.png`, `interior_obstacle_clearance.png`). Because the copy in step 2 does not delete, the three starter PNGs stay in the PR branch unless you remove them. The safe default is to remove them so no starter figure ships; if in doubt ask the course faculty.
- [ ] FLAG, working drafts in our export that may not belong in a course submission: `docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx`, `docs/DOSSIER_FILL_SHEET.md`, `docs/submission/email_to_sir_DRAFT.md`, `docs/submission/viva_prep_*.md`, and the planning folder. Decide before step 2 and delete from the clone if you do not want them shipped (optional lines are in step 2). `docs/submission/viva_evidence/` holds the saved outputs the viva answers point to: ship it if the viva notes ship.
- [ ] Everything in `docs/planning/` (PRDs, PDFs, HTML sources, `mermaid.min.js`) is allowed inside the group folder but is not required by the template.

## 1. Fork and clone

Placeholders in angle brackets are filled by the person running the step. E043 (Muaaz) owns L-08; the branch name follows the monorepo pattern `feat/<roll-no>-<task-name>`.

```bash
gh repo fork https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026 --clone=false
git clone https://github.com/<your-github-user>/NMIMS-MPSTME-MDRIIA-2026.git monorepo-fork
cd monorepo-fork
git remote add upstream https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026.git
git fetch upstream
git checkout -b feat/e043-group-05-dual-uav-patrol upstream/main
```

## 2. Copy the group folder from the merged branch

Use `git archive` from the project repository, on the merged branch, so only committed files are copied (no MP4s, venvs, telemetry, handoff packets or caches can slip in). Run this from the project repository root, with the merged branch checked out:

```bash
git archive HEAD Group_05_Muaaz_Aditya_Zaid_Soumya | tar -x -C <path-to>/monorepo-fork
```

Optional, only if you decided in the dry-run section to leave drafts out (run inside `monorepo-fork/Group_05_Muaaz_Aditya_Zaid_Soumya`):

```bash
rm -f docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx docs/DOSSIER_FILL_SHEET.md docs/submission/email_to_sir_DRAFT.md
git rm -q --ignore-unmatch docs/figures/figure1_system_architecture.png docs/figures/figure2_kinematic_telemetry.png docs/figures/figure3_comparative_performance.png
```

Then check, from the clone root, that nothing excluded slipped in and nothing is oversized:

```bash
find Group_05_Muaaz_Aditya_Zaid_Soumya \( -name '*.mp4' -o -name '.venv' -o -name '_handoff' -o -name '_archive' -o -path '*analytics/runs/*' \) | head
find Group_05_Muaaz_Aditya_Zaid_Soumya -type f -size +5M
du -sh Group_05_Muaaz_Aditya_Zaid_Soumya
git status --short | head -50
git status --short | grep -v 'Group_05_Muaaz_Aditya_Zaid_Soumya/' | head
```

The first two commands and the last one must print nothing. `git status` must list paths only under `Group_05_Muaaz_Aditya_Zaid_Soumya/`.

## 3. Verify from the clean copy

```bash
cd Group_05_Muaaz_Aditya_Zaid_Soumya
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/test_env.py
python -m pytest tests/
deactivate && rm -rf .venv
cd ..
```

(The `.venv` is deleted again so it is not committed. The Expo needs this same fresh-clone run on the laptop: Guide section 12.)

Record the results of this run on the merged branch (copy from your own terminal, do not carry over any earlier count):
- [ ] `python src/test_env.py`: ______
- [ ] `python -m pytest tests/`: ______ passed, ______ failed, ______ skipped
- [ ] 30 s runs in both scenes finish, figures regenerate: ______
- [ ] If any check fails, stop and fix it on the merged branch; do not open the pull request around a failing check.

The Expo needs this same fresh-clone run on the laptop (Guide section 12); the macOS and Windows steps are in `TEAMS_AND_EXPO_CHECKLIST.md`.

## 4. Commit, push, open the pull request

```bash
git add Group_05_Muaaz_Aditya_Zaid_Soumya
git commit -m "feat(group-05): add dual-UAV campus patrol model, controller, trials and dossier"
git push -u origin feat/e043-group-05-dual-uav-patrol
gh pr create --repo github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026 --base main \
  --title "Group 05: MPSTME GUARDIAN, dual-UAV campus patrol (MuJoCo)" \
  --body-file pr_body.md
```

`pr_body.md` (draft, plain text, no AI attribution line of any kind):

```
Group 05 (Muaaz, Aditya, Zaid, Soumya), MDRIIA 702CO0E012.

What this adds, all inside Group_05_Muaaz_Aditya_Zaid_Soumya/:
- models/: MuJoCo model, two scenes (interior of the Main Building; the campus compound inside the boundary wall)
- src/: dual-UAV controller, FR-18 obstacle sensing, surveillance state machine, viewer
- analytics/: benchmark runner, real-trial CSV with provenance, statistics, economics
- docs/: filled technical dossier (.docx and .pdf), figures, research notes

Results: N = 30 seeded runs in each of 6 cells at timestep 0.002 s; the CSV and its provenance record are in analytics/. All patrolling is inside the college (Main Building interior; campus inside the boundary wall). OpenCV is the primary detector.
Run: pip install -r requirements.txt, then see README.md section 5.5.
```

Add result numbers to the body only if they are copied from the final statistics output; otherwise leave it as written.

## 5. After the PR

- [ ] Each member checks `git shortlog -sn -- Group_05_*/` on the PR branch and enters their own commit share in dossier Section 6 (fill honestly).
- [ ] Paste the pull request URL into the LinkedIn post's placeholder in `video_script_and_shotlist.md` before posting.
- [ ] Each of the four members attaches the final PDF on MS Teams and clicks "Turn in" themselves (Guide section 3); one member's submission does not count for the others. Tick list: `TEAMS_AND_EXPO_CHECKLIST.md`.
- [ ] Do not push anything to the fork after the PR is open unless asked by the course faculty.
