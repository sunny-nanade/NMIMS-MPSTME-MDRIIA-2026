# MS Teams turn-in and Expo checklist (Group 05)

Status: working checklist, nothing here has been done yet. Tick boxes yourself. Section numbers refer to `MDRIIA_LinkedIn_and_GitHub_Showcase_Guide.pdf` (the Guide); if a step here disagrees with the Guide, the Guide wins and this file should be corrected.

"The merged branch" below means the branch that carries the final E043, E051, E075 and E077 work after the team decides to merge it. That merge is a decision for the team, not something done by this checklist. Replace `<merged-branch>` and `<repo-url>` with the real names once it exists.

Never write in this checklist, the dossier or on screen: SAP IDs in public places, the LinkedIn video URL guessed in advance (it is a HUMAN field, Section 5 of the dossier), peer-review scores for anyone else, signatures or hours you did not log.

## A. MS Teams turn-in: four separate turn-ins (one per member)

One member's turn-in does not count for the others (Guide section 3). Each of the four members does the whole list from their own Teams account.

| Member | Roll no. | Attached the final PDF | Clicked "Turn in" |
| :--- | :--- | :---: | :---: |
| Muaaz Shaikh | E043 | [ ] | [ ] |
| Aditya Rajkumar | E051 | [ ] | [ ] |
| Zaid Rezaur Rahman | E075 | [ ] | [ ] |
| Soumya Subhankar Ranasingh | E077 | [ ] | [ ] |

Before anyone turns in:
- [ ] The dossier was filled in Word desktop (not Google Docs) from `docs/MDRIIA_Group_05_Technical_Dossier.docx` and exported to `docs/MDRIIA_Group_05_Technical_Dossier.pdf`, keeping the original file names (Guide section 2). The faculty's blank `.docx` itself is never edited in the repository.
- [ ] Each member has typed their own real SAP ID on the cover and in `docs/TEAM_ROSTER.json`. Nobody types another member's ID.
- [ ] Section 5 of the dossier holds the LinkedIn post URL once the post is live (the video URL is a HUMAN field), and Section 5.2 holds each member's own peer review (`docs/submission/peer_review_template.md` is the working sheet; copy your own scores in yourself, never a teammate's).
- [ ] Section 6 (commit share, AI-use) is filled honestly by each member from `git shortlog -sn -- Group_05_*/` and `docs/submission/ai_audit_candidates.md`.
- [ ] The PDF attached is the same file for all four members (compare file size and open it once more after downloading it back from Teams).
- [ ] After "Turn in", each member checks that Teams shows the status as turned in, and notes the time in the group chat.

If the late-dossier question is still open, the draft is `docs/submission/email_to_sir_DRAFT.md` (marked DO NOT SEND, recipient left for Muaaz). Send it only by hand.

## B. Fresh-clone check, the same steps the Expo needs (Guide section 12)

Do this on the laptop that will be used at the Expo, in a folder that has never held the project, and do not copy the old `.venv` over. The point is to prove the repository alone is enough.

### B1. macOS (viewer runs under `mjpython`)

```bash
git clone <repo-url> expo-check
cd expo-check
git checkout <merged-branch>          # or the monorepo's main after the pull request is merged
cd Group_05_Muaaz_Aditya_Zaid_Soumya
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/test_env.py
python -m pytest tests/
mjpython src/view_live.py --scene interior --rays --seed 4 --appear 20
mjpython src/view_live.py --scene exterior --seed 4 --appear 20
mjpython src/view_live.py --demo headon --apf-only
mjpython src/view_live.py --demo headon --rays
```

### B2. Windows (plain `python`; there is no `mjpython`)

```bat
git clone <repo-url> expo-check
cd expo-check
git checkout <merged-branch>
cd Group_05_Muaaz_Aditya_Zaid_Soumya
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\test_env.py
python -m pytest tests\
python src\view_live.py --scene interior --rays --seed 4 --appear 20
python src\view_live.py --scene exterior --seed 4 --appear 20
python src\view_live.py --demo headon --apf-only
python src\view_live.py --demo headon --rays
```

Tick after each platform you actually ran (do not tick one for the other):
- [ ] macOS: clone, install, `src/test_env.py` and `pytest tests/` finished without failure; write down the pass count you saw: ______
- [ ] Windows: the same; pass count you saw: ______
- [ ] All four viewer commands open a window on that laptop. If the overlay says "Vision off", the off-screen renderer did not start next to the viewer: say so, and use `docs/submission/video_shots.sh` or the backup clips it names, never a mock-up.
- [ ] Any failure is written down in the group chat and fixed in the repository, not worked around on one laptop.
- [ ] Delete `expo-check/.venv` when done, and never commit it. Never commit MP4 files either.

## C. What to show at the Expo

1. The live viewer, not slides: no PPT at the Expo. Show the MuJoCo viewer, the result figures in `docs/figures/` and the business graphs in `analytics/figures/` (or the copies in `docs/submission/video_assets/`).
2. The handled failure: first `--demo headon --apf-only` (potential fields alone: the two UAVs touch), then `--demo headon --rays` (layered separation and the distance governor: the same encounter passes). Read the minimum centre distance off the on-screen overlay, not off a sheet.
3. Interior first (all obstacles sensed, FR-18 rays on), then the campus inside the wall. In the exterior shot, cut before Alpha starts opening false-alarm incidents (see the CUT note printed by `video_shots.sh 2`), or say plainly that a false alarm is real detector behaviour.
4. Every number said aloud is read from the final `VIDEO_NUMBERS.md` or from the screen. No currency amounts: ratios only. If the screen differs from a sheet, say the screen value.
5. State the limits unprompted: simulation only; where the data does not support an improvement claim, say so.

## D. Webcam picture-in-picture for all four members

- [ ] Each of the four members has a working webcam on the day and has tested it with the screen recording tool at least once.
- [ ] The recording or live Teams/Zoom/Meet session shows all four webcams in picture-in-picture for the whole demo, including while someone else is speaking.
- [ ] Every member speaks at least once. Speaking order and lines are in `docs/submission/video_script_and_shotlist.md`.
- [ ] Mail, chat and the browser bookmarks bar are closed or cleared: no SAP IDs, no phone numbers on screen.
- [ ] No slides: nothing is shared in PowerPoint, Keynote or Google Slides.

## E. Last look before leaving for the Expo

- [ ] Phone and laptop charged; charger and a second display cable packed.
- [ ] A copy of the final PDF and a clone of the repository on the laptop, working offline.
- [ ] Everyone knows which of them runs which viewer command and who answers for which part (the four `docs/submission/viva_prep_E0xx.md` files).
