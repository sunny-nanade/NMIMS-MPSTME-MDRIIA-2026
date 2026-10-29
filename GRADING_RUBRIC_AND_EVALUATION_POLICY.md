# MDRIIA (702CO0E012) Capstone: Grading Rubric & Evaluation Policy
**Modern Day Robotics & Its Industrial Applications · B.Tech CSBS (TCS partnership)**
**SVKM's NMIMS · MPSTME Mumbai · AY 2026–27 Odd Semester · Dr. Sunny Nanade**

> This document replaces the earlier 100-mark, 4-milestone scheme. The capstone is an **ICA component worth 20 marks**.

| Item | Detail |
|---|---|
| **Total Capstone Marks** | **20 Marks** |
| **Submission Due Date** | **Monday, 26-Oct-2026, 23:59 IST** |
| **Studio Showcase, Expo & Viva Voce** | **Saturday, 31-Oct-2026** |
| What you submit | (1) Your group's Technical Dossier as PDF on MS Teams, turned in by **every** member · (2) the filled `.docx` **and** `.pdf` committed to `Group_XX_*/docs/` · (3) your model, controller, business script and `*_real_trials.csv` in your group folder · (4) your LinkedIn video URL in dossier Section 5 |
| Presentation format | **No PPT slides.** Live MuJoCo simulation + CSBS business sensitivity graphs + webcam picture-in-picture of every member |

---

## Component 1: CDIO Robotics Engineering & MuJoCo Physics (10 Marks)
Dossier Sections 1, 2 and 4, checked against your group folder.
| Criterion | Evidence | Marks |
|---|---|---|
| Problem framing | Authorised Aalborg title, verified baseline friction, governing standards decided with clauses, claim verification table (Section 1) | 2 |
| MuJoCo rigid-body model | `models/*.xml` loads; contact friction / `solref` / timestep justified; the mechanism matches the title (Section 2) | 2 |
| Closed-loop control | `src/*.py` controller with an implemented FSM and a stated control law (PID / impedance / DLS-IK), honest script-authorship table (Section 2) | 2 |
| Telemetry & Monte Carlo | 500 Hz logging, N ≥ 30 randomised runs per condition with recorded seeds, tracking RMSE and control effort ∫τ² dt (Section 4) | 2 |
| Statistical validation | Baseline vs proposed, t-test, Cohen's d, 95 % CI, plots that re-generate from `analytics/*_real_trials.csv` (Section 4) | 2 |

## Component 2: CSBS Techno-Economic Business Systems Analysis (5 Marks)
Dossier Section 3 and `analytics/*_roi.py` (or the group's renamed business script).
| Criterion | Evidence | Marks |
|---|---|---|
| Labour reallocation and payback | H_reclaimed and the dimensionless payback horizon P_payback computed by the script from sourced inputs | 1.5 |
| Cost reduction | Normalised Cost Reduction Index NCRI (= 1 − κ), dimensionless, no currency amounts | 1 |
| Queuing model | M/M/1 or M/M/c delay model with stated λ, μ, c and utilisation ρ | 1 |
| Risk | FMEA with at least four failure modes, RPN before and after mitigation, mitigation shown in simulation or code | 1 |
| Sensitivity | Sensitivity graph on the most uncertain input with the break-even value | 0.5 |

## Component 3: Studio Showcase & Viva Voce (5 Marks)
| Criterion | Evidence | Marks |
|---|---|---|
| LinkedIn video (3–4 min) | Live MuJoCo simulation, business graph, every member on webcam picture-in-picture (Section 5) | 1 |
| AI audit and peer review | Three verified AI-error cases; peer review of the two assigned groups (Sections 5.1–5.2) | 1 |
| Live Expo demonstration | Simulation running from a fresh clone, FSM states and one handled failure shown | 1 |
| Individual viva voce | Each member defends their own role, code and the whole project, including the business model | 2 |

---

## Mandatory Individual Turn-in Rule
The work is collaborative, but marks are entered **per student** in the NMIMS Examination Portal.
**Every member must open the MS Teams assignment, attach the group's final PDF dossier, and click "Turn in" individually.**
A student who does not turn in cannot be awarded capstone marks, even if teammates have submitted.

## Integrity Safeguards
1. **Data provenance:** files named `SIMULATED_*`, every `generate_paper_figures.py` and the starter figures in `docs/figures/` contain **generated target numbers** (np.random). Reporting them as experimental results is data fabrication and scores **zero** for the component in which they appear. Results come only from MuJoCo runs of the group's own controller, saved as `analytics/*_real_trials.csv`.
2. **Hard-coded results:** constants typed into a business script as outputs (e.g. a payback period) are not analysis. Every economic number must be computed from sourced inputs or labelled as an assumption and varied in the sensitivity graph.
3. **Evidence authenticity:** every factual claim and citation must be verified at its primary source (dossier Section 1.1). Fabricated citations or DOIs score zero for the component in which they appear.
4. **AI use:** permitted, but must be logged in dossier Section 5.1. Undisclosed AI-generated content is treated as an integrity breach.
5. **Attribution:** individual contributions must match the git history and the dossier (Sections 2.2 and 6), and are defended in the viva.
6. **Zero Currency Rule:** cost comparisons are expressed as dimensionless ratios (κ, NCRI, P_payback), not raw monetary amounts.
7. **Research use:** dossier Section 6 is not marked. Data is used in anonymised education research only for students who gave the optional research consent in the sign-off; the answer has no effect on marks.
