# Capstone requirements: where each one lives in this repository

Course: Modern Day Robotics and Its Industrial Applications (MDRIIA, 702CO0E012), capstone ICA of 20 marks
(Component 1 CDIO Robotics and MuJoCo Physics 10, Component 2 CSBS Techno-Economics 5, Component 3 Showcase and Viva 5).
Source documents: the course repository's `README.md`, `GRADING_RUBRIC_AND_EVALUATION_POLICY.md`,
`ACADEMIC_AND_INDUSTRY_STANDARDS_MANUAL.md`, the Group 03 folder, the Technical Dossier template and the LinkedIn and
GitHub Showcase Guide. All numbers quoted from this repository's own runs are in
[`CAPSTONE_RESULTS.md`](CAPSTONE_RESULTS.md), which `scripts/make_capstone_doc.py` regenerates from `analytics/`.

## One command per deliverable

```bash
pip install -e ".[dev,viz,geo]"
python experiments/09_capstone_monte_carlo.py --n 50   # 750 MuJoCo episodes at 500 Hz -> analytics/aed_delivery_real_trials.csv
python analytics/aed_delivery_roi.py                   # business model, queue, FMEA, sensitivity -> analytics/*.csv, docs/figures/business_*.png
python analytics/standards_check.py                    # braking test + clause checks -> analytics/standards_check.csv
python scripts/make_capstone_doc.py                    # docs/CAPSTONE_RESULTS.md from the files above
python scripts/export_nmims.py --out dist/nmims        # builds Group_03_Kashish_Vaishnavi/ in the course layout
python scripts/fill_dossier.py --template <dossier.docx> --out <filled.docx> --pdf   # fills every field the repo can answer
```

## Rubric criterion to evidence

| Rubric criterion (marks) | Evidence in this repository |
|---|---|
| Problem framing (2): authorised title, verified baseline friction, standards with clauses, claim table | Title verbatim in `README.md` and the exported roster. Claim verification in `docs/CLAIM_VERIFICATION.md`; standards in `docs/STANDARDS_COMPLIANCE.md` (generated from `analytics/standards_check.csv`); baseline friction: ambulance response distribution from Naess et al. (`docs/CLINICAL_MODEL.md`) |
| MuJoCo rigid-body model (2) | `src/aedrover/sim/vehicle_mjcf.py` and `world.py` generate the MJCF; timestep 0.002 s; tyre `solref` 0.03 s / 1.0 (about 200 kN/m, validated by `experiments/01_validate_suspension.py`); friction 1.0 / 0.005 / 0.0001; exported as `models/aed_delivery_amr.xml` and compiled by the export audit |
| Closed-loop control (2): implemented FSM, stated control law | `src/aedrover/capstone/fsm.py`: DISPATCH, ROAD_CRUISE, CURB_SIDEWALK, ARRIVE, AED_HANDOVER supervising a dynamic-window planner (potential-field family) plus the speed-and-separation safety filter. Every transition is logged with a reason |
| Telemetry and Monte Carlo (2): 500 Hz, N >= 30 per condition, seeds, RMSE, control effort | `src/aedrover/capstone/telemetry.py` records one row per 0.002 s physics step (measured rate 500.0 Hz in every run). 50 runs per condition and controller, five conditions, seed column in every row. Tracking RMSE = sqrt(mean e_y^2), effort = sum of torque^2 times dt over the six actuators |
| Statistical validation (2): baseline vs proposed, t-test, Cohen's d, 95 % CI, plots that regenerate | `statistics_table()` in `capstone/monte_carlo.py` (Welch, exact p, d with CI, difference CI) writes `analytics/capstone_statistics.csv`; figures are redrawn from the CSV by `experiments/09_capstone_monte_carlo.py --from-csv` |
| Labour reallocation and payback (1.5) | `capstone/business.py`: `H_reclaimed`, `T_payback` (months) and `P_payback`, all computed; inputs tabulated with unit and source in `analytics/roi_inputs.csv` |
| Cost reduction (1): NCRI = 1 - kappa | same module; NCRI and kappa in `analytics/roi_results.json` |
| Queuing model (1): M/M/1 or M/M/c with lambda, mu, c, rho | Erlang C in `business.py` (M/M/1 is the c = 1 case, tested against the closed form); graph `docs/figures/business_queue.png` |
| Risk (1): FMEA, at least 4 modes, RPN before and after, mitigation shown in simulation or code | `analytics/fmea.csv`: five modes; the occurrence score comes from the measured failure rate of the unmitigated vs mitigated controller in the Monte Carlo, so the post-mitigation RPN is backed by the simulation |
| Sensitivity (0.5): graph with break-even | `docs/figures/business_sensitivity.png` and `analytics/roi_sensitivity.csv`, `roi_tornado.csv`; break-even values in `roi_results.json` |
| Live Expo demo (1): runs from a fresh clone | `pip install -r requirements.txt` then `python src/test_env.py`; `python scripts/live_cinematic.py --drone` for the viewer |

## What the numbers say (read this before the viva)

* **Vehicle and speeds are the course guide's.** The proposed controller runs on `VehicleParams.course()`: 26 kg sprung and
  2.25 kg unsprung per corner, k_s 4500 N/m, c_s 350 N s/m (zeta 1.02, omega_n 26.3 rad/s), payload isolator 2200 N/m and
  180 N s/m, tyre friction 1.1, radial tyre stiffness 30 kN/m (measured 30.0), ROAD_CRUISE 3.5 m/s and CURB_SIDEWALK
  at least 1.2 m/s. The repository's own co-designed chassis is kept as a separate arm (`proposed_codesigned`); at the
  guide's soft tyre it adds little.
* **The labour lens does not close.** With the placeholder inputs one hub sees under one suspected cardiac arrest a
  day, so the ALS-ambulance hours the pods free (about 0.85 vehicle-hours a day over a 50 km^2 zone) are far below what
  77 pods cost to run: kappa is about 283, NCRI is negative and there is no payback. The model reports this instead of
  tuning inputs to meet kappa <= 0.25; cost parity would need an incidence about 700 times the assumed one. The health
  lens sits beside it (about +2.4 percentage points of expected survival under parallel dispatch, about 130 QALY a year
  over the zone, 13 QALY per ALS vehicle-year of cost), because the clinical argument, not the labour saving, is the
  reason to deploy.
* **Radius matters more than speed.** The proposed controller averages about 2.1 m/s over successful runs, so at a 500 m
  response radius (route factor 1.54) the pod's time to first shock is about 9.7 min against 11.0 min for the median
  urban ambulance. The course's 1.5 km radius is a sweep, not the baseline.
* **Failed runs have no transit time.** Statistics on TTFS, RMSE and effort use successful runs only; the success rate
  and its Wilson interval are reported separately (`analytics/capstone_success_rates.csv`). In the protocol conditions
  the baseline reaches the goal in 68 of 150 runs and the proposed controller in 115, so read both. The proposed
  controller tracks the centreline worse (about 0.8 m against 0.02 m; it leaves the line to avoid pedestrians) and uses
  more control effort; that is a cost of avoidance, not an error. The lane-splitting condition is the hard one: 36 % of
  proposed runs reach the goal.
* **Payload shock is the weakest result.** At 3.5 m/s the naive controller exceeds 3 g in 28 % of runs (64 % on kerbs);
  the proposed controller cuts that to 8 % (16 % on kerbs), but 92 % of its runs stay within 3 g and the worst is 4.62 g, so
  the budget is still recorded as a DEVIATION. Wheel slip on a wet kerb is only marginally mitigated (78 % of slippery
  runs fail against 84 %, occurrence score unchanged); the FMEA keeps that residual risk instead of scoring it away.
* **Standards deviations are deliberate and recorded:** the safety filter models a 100 ms reaction time against the 50 ms
  the course manual cites for ISO 3691-4, caps pedestrian-zone speed at 1.4 m/s against 0.8 m/s (the README ablation shows
  the 0.8 m/s cap cuts delivery), and the median minimum clearance is 0.25 m against the 0.50 m bubble. See
  `analytics/standards_check.csv`.
## Items only the students can complete (not filled, on purpose)

These are personal attestations or external facts; filling them on someone's behalf would be false.

1. Dossier 2.2 script authorship and Section 6 individual learning record (hours, commit share, AI share).
2. Dossier Section 5: the LinkedIn URL, video length, the webcam and live-simulation confirmations, the three-case AI
   audit log (evidence candidates in `docs/AI_AUDIT_CANDIDATES.md`) and the two peer reviews.
3. The sign-off: each member's three answers, signature and optional research consent.
4. Recording and posting the 3 to 4 minute video, and every member's own turn-in of the PDF on MS Teams.
5. A hand-drawn free-body diagram for dossier 2.4 (the worked equation is filled; the sketch is not).
6. Feature branches and at least four conventional commits per member from their own accounts
   (`ACADEMIC_AND_INDUSTRY_STANDARDS_MANUAL.md`, section 5); the export never stages or commits.
