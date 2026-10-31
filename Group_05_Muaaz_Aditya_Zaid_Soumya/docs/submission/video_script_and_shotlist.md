# LinkedIn video: 3:30 script and shot list (Guide limit 3:00-4:00)

Rules from the Showcase Guide (section 7, read from `MDRIIA_LinkedIn_and_GitHub_Showcase_Guide.pdf` in the course monorepo root on 30 Oct 2026): 3 to 4 minutes, no PPT slides, live software only (MuJoCo viewer, result plots, business graph), every member appears on a webcam picture-in-picture and every member speaks, a Teams/Zoom/Meet screen-and-webcam recording is fine, upload natively to LinkedIn (no YouTube link), one post per group, tag the teammates, MPSTME and the course faculty, link the monorepo folder. Privacy: no SAP IDs, no phone numbers, no personal data of anyone outside the team. No currency amounts anywhere: ratios only.

Number status: the figures in the table and post below are the record of the Part 1 batch and are due to be re-filled from the final `VIDEO_NUMBERS.md` after the last benchmark run (`python docs/submission/print_video_numbers.py`). Do not record until the numbers on this page equal the numbers in that file; if they differ, the file wins.

Number rule: every number said on camera is copied from `docs/submission/VIDEO_NUMBERS.md` (which copies `video_numbers_output.txt`, produced by `python docs/submission/print_video_numbers.py`). A number read off the live viewer overlay is read from the screen, not from this page. If the screen differs from this sheet, say the screen value and fix the sheet afterwards.

Speakers (from `docs/TEAM_ROSTER.json`): **E043 Muaaz** = lead, flight dynamics and integration; **E051 Aditya** = computer vision and OpenCV detection; **E075 Zaid** = geofence, alerts and statistics; **E077 Soumya** = economics and FMEA. All four on webcam PiP throughout, including when someone else is speaking.

Shot numbers follow `docs/submission/video_shots.sh` (run `bash docs/submission/video_shots.sh <n>` from the group folder; on macOS it uses `mjpython`). Shot 1 = interior live (`view_live.py --scene interior --rays --seed 4 --appear 20`), Shot 2 = campus inside the wall (`--scene exterior --seed 4 --appear 20`; cut before 61.9 s sim time, when Alpha starts opening false-alarm incidents), Shot 3b = head-on failure without the governor (`--demo headon --apf-only`), Shot 3 = head-on handled (`--demo headon --rays`), Shot 4 = business graphs in Preview.

Hardware facts used in the lines, verified in the repo: MJCF models in `models/` (`uav_fleet.xml` plus the scene files), timestep 0.002 s in both scene files, two quadrotors with 4 rotors each = 8 rotors (`uav_fleet.xml`, `alpha_m0..3`, `bravo_m0..3`; 7.5 N maximum per rotor), controller in `src/aerial_patrol_swarm.py`: cascaded position P, velocity PI, attitude PD, then a rotor mixer, with layered separation (altitude layers, potential fields, distance governor) between the two UAVs.

## Timed script (3:30 = 210 s)

| Time | Speaker | Line to say | On-screen asset |
| :--- | :--- | :--- | :--- |
| 0:00-0:15 | E043 Muaaz | "To what extent can a collaborative dual-UAV surveillance system, simulated in MuJoCo, optimize campus perimeter patrol cycle time and OpenCV human detection latency compared with static security guard patrols? We are Group 5, and we will show you the answer running live." | Webcam full screen, then PiP over the title card on `docs/figures/video_poster.png` |
| 0:15-0:40 | E043 Muaaz | "The baseline is a guard on foot. We model the guard walking at a comfortable speed of 1.272 to 1.462 metres per second, from Bohannon, Age and Ageing 1997, drawn per seed, with pauses. That is the conservative choice, it favours the guard. All our flying is inside the college." | Webcam PiP over `docs/figures/trajectory_interior.png`, then `trajectory_exterior.png` |
| 0:40-1:00 | E043 Muaaz | "The physics is a MuJoCo MJCF model: two quadrotors, four rotors each, so eight rotors, with a timestep of 0.002 seconds, which is 500 hertz. The controller is cascaded: a position loop, a velocity PI loop and an attitude PD loop, then a mixer to rotor thrust. Separation between the two UAVs is layered on top of that." | Viewer, `models/uav_fleet.xml` actuator block in the editor, then `src/aerial_patrol_swarm.py` gains block |
| 1:00-1:20 | E051 Aditya | "Interior first, inside the Main Building. Each UAV has a range ring that avoids every obstacle it senses. My OpenCV detector looks down, finds the intruder by colour, and verifies it over consecutive frames before the state machine moves on." | Shot 1: `view_live.py --scene interior --rays --seed 4 --appear 20`, overlay in frame (Alpha and Bravo FSM state) |
| 1:20-1:35 | E075 Zaid | "Now the campus scene. Watch the overlay step through PATROL, DETECT, VERIFY, ALERT, TRACK and RETURN. The geofence decides the alert tier, the better-placed UAV tracks the intruder, then it returns to patrol." | Shot 2: `view_live.py --scene exterior --seed 4 --appear 20` (cut before 60.2 s), overlay states highlighted |
| 1:35-1:55 | E043 Muaaz | "Here is a failure we handled. With potential fields alone, two UAVs meeting head-on touch: the minimum centre distance on the overlay is [read it from the screen]. With layered separation and the distance governor, the same encounter passes at [read it from the screen]." | Shot 3b (`--demo headon --apf-only`) then Shot 3 (`--demo headon --rays`), overlay minimum distance in frame |
| 1:55-2:30 | E075 Zaid | "Results: 30 seeded runs in each of 6 cells. Interior cycle time: guard 2460.4638 seconds, our sectors policy 56.8981 seconds, a ratio of 43.2434. Welch t is 22.1926 on 29.001 degrees of freedom, p is 9.60822 times ten to the minus 20, Cohen's d is 5.7301, and the 95 percent interval of the difference is 2182.0578 to 2625.0736 seconds. Exterior: 532.9093 against 71.0988 seconds, t 17.8531, d 4.6097. Tracking RMSE for sectors is 0.4878 metres inside and 0.2726 outside." | `docs/figures/revisit_boxplot_interior.png`, then `revisit_boxplot_exterior.png` (these show worst ground revisit; cycle-time numbers are in `video_numbers_output.txt`, open it beside the plot) |
| 2:30-2:55 | E077 Soumya | "The business case uses ratios only, no currency. Every economic input is either sourced or an assumed range that we sweep. Using the assumed ranges: kappa is 0.185 against a target of 0.25, so the target is met; NCRI is 0.815; the payback ratio is 0.304, below 1, so in the base case the fleet pays for itself inside its assumed service life, in about 12.8 months; but the envelope over all assumption corners runs from 0.041 to 5.042, so in the worst corners it would not. The queue model says both guard and UAV systems are almost never busy at the assumed incident rate, so response time, not congestion, is what differs. The highest FMEA risk is a missed intruder indoors, RPN 432 for the guard falling to 288 with the UAVs, the same limit as the detection result." | Business graph: `video_assets/campus_security_sensitivity.png`, then `video_assets/campus_security_queue.png` |
| 2:55-3:20 | E051 Aditya and E075 Zaid | E051: "Limits, honestly. Interior detection is 11 of 30 for the guard and 11 of 30 for our sectors policy, so we do not claim an interior detection improvement; outside it is 30 of 30 with a mean latency of 18.6190 seconds against 281.0518 seconds, and the run windows differ." E075: "Safety: 0 contacts in 59 of 60 interior UAV runs; one contact found and being fixed, in interior sectors seed 7. The offset-ring policy came within 1.6339 metres of the other UAV, so it does not meet a 2.5 metre separation. UAV-to-UAV contacts were 0. This is simulation only." | Webcam PiP over `video_numbers_output.txt` sections 2 and 3, then `docs/figures/interior_obstacle_clearance.png` |
| 3:20-3:30 | E043 Muaaz (all four wave) | "Code, data and the model are in our group folder in the course repository, linked in the post. Thank you." | Four webcams, repo link text on screen: `github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026`, folder `Group_05_Muaaz_Aditya_Zaid_Soumya` |

Each member speaks at least once above. The Guide's "what I built, what I learned, one thing AI got wrong" round fits inside the 4:00 limit using the 30 s of slack before the close (3:30 to 4:00), about 7 s per member, in their own words. One evidenced case per member, each with a file you can open on screen (all in `docs/submission/viva_evidence/` unless a commit is named; full write-ups in `docs/submission/ai_audit_candidates.md`):

| Member | One thing AI got wrong (say it in your own words) | Proof to show |
| :--- | :--- | :--- |
| E043 Muaaz | The AI-written region-ownership checker printed OK because its path patterns never matched anything, so it could not tell one member's lines from another's. I found it when it returned nothing per line for a teammate's patch. | commit `40a811f`; `viva_gate_old_vs_fixed.txt` |
| E051 Aditya | The AI's first colour-saturation floor for the detector was too loose, and the detector merged the intruder with similarly coloured floor pixels in some frames. We measured the two saturations and raised the floor. Caveat: tuned on the same frames it is reported on. | `viva_e051_satfrac_repro.txt`; `E051_AI_DISCLOSURE.md` |
| E075 Zaid | The AI expected an exit margin alone to stop geofence false alarms. Measured over 100 seeds, it barely did; adding a tier-3 dwell of 5 consecutive inside readings is what fixed it, at the cost of 0.4 s. | `viva_e075_exit_margin_only_repro.txt`; `E075_AI_DISCLOSURE.md` |
| E077 Soumya | The AI's own economics tests failed on its own text, and the old economics file we replaced was arithmetic on typed-in constants, not on our results. The replacement refuses to run without the real trials file. | `E077_AI_DISCLOSURE.md` (recorded pytest output; the failing versions no longer exist, so say it rests on that record); `viva_e077_old_economics_main.txt` |

Honesty limits to keep: git records Muaaz as author of every commit, so say "AI-drafted" only for what the AI-use declaration lists; the E077 failing-test case cannot be re-run; do not present any case as proof that AI is unreliable in general, present it as how we caught it.

## Before you record

- [ ] Record on the merged tree (E043 plus the E051, E075 and E077 patches), otherwise DETECT, VERIFY, ALERT and TRACK will not appear.
- [ ] Run each shot command once off-camera and read the overlay yourself: the FSM overlay was checked through terminal output, not by screenshot.
- [ ] Exterior detection can show a false alarm on the red cab geoms; if one appears, say it is real detector behaviour.
- [ ] Open in tabs: the two boxplots, `video_numbers_output.txt`, the E077 graphs, `docs/figures/trajectory_*.png`. Copies of the existing figures are in `docs/submission/video_assets/`.
- [ ] Close mail and messages: nothing with SAP IDs or phone numbers on screen.

## LinkedIn post

**Post text** (filled from the Guide's template; numbers from `VIDEO_NUMBERS.md`):

> Simulated guard cycle time 2460.4638 s vs 56.8981 s for our dual-UAV sectors policy inside the Main Building (ratio 43.2434, N = 30 seeded runs per cell, Welch p = 9.60822e-20).
>
> Our MDRIIA capstone team (B.Tech CSBS, SVKM's NMIMS MPSTME) asked: "To what extent can a collaborative dual-UAV surveillance system simulated in MuJoCo optimize campus perimeter patrol cycle time and OpenCV human detection latency compared to static security guard patrols?"
>
> We modelled two quadrotors (8 rotors) in DeepMind MuJoCo at a 0.002 s timestep with a cascaded position, velocity and attitude controller plus layered separation, and ran 30 Monte Carlo trials in each of 6 cells: cycle time in the interior scene 2460.4638 s for the guard against 56.8981 s for sectors, tracking RMSE 0.4878 m. Business case: kappa 0.185 (target 0.25 met), NCRI 0.815 and payback ratio 0.304 (interior sectors, assumed cost ranges, ratios only).
>
> What we learned, honestly: interior detection did not improve (11 of 30 for both guard and sectors), 0 contacts in 59 of 60 interior UAV runs with one contact found and being fixed, and the offset-ring policy came within 1.6339 m of the other UAV. Simulation only. One thing AI got wrong: the AI-written checker that was meant to stop one member editing another's lines printed OK because its path patterns matched nothing; we caught it when it returned nothing for a teammate's patch.
>
> Code: https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026/tree/main/Group_05_Muaaz_Aditya_Zaid_Soumya [PR LINK PLACEHOLDER: not opened yet; fill in the pull request URL from `monorepo_pr_steps.md` step 4 once it exists, or delete this bracket]
> Team: Muaaz Shaikh, Aditya Rajkumar, Zaid Rezaur Rahman, Soumya Subhankar Ranasingh. Guided by [the course faculty: type the name when posting].

**Tags** (use the LinkedIn mention picker, not typed text): Muaaz Mohammed Iqbal Shaikh, Aditya Rajkumar, Zaid Rezaur Rahman, Soumya Subhankar Ranasingh, MPSTME Mumbai, SVKM's NMIMS, the course faculty (pick the name in the mention picker). Link the monorepo folder as above.

**Hashtags** (carried over from the Guide's post template as read on 30 Oct 2026): #Robotics #MuJoCo #CSBS #TCS #MPSTME #NMIMS

HUMAN check: the Showcase Guide PDF is not in this working tree, so these six could not be re-checked against it in the last pass. Open `MDRIIA_LinkedIn_and_GitHub_Showcase_Guide.pdf` (section 7, post template) and make the hashtag line match it exactly before posting; if the Guide does not list #TCS, drop it.

Do not post until the LinkedIn URL can go into dossier Section 5 and `docs/TEAM_ROSTER.json` (`linkedin_url`). No currency, no SAP IDs, no phone numbers in the post or on screen.
