# MDRIIA Group 10: 7-DOF Surgical Robotic Manipulator with Physiological Tremor Compensation
**Course:** Modern Day Robotics and Its Industrial Applications (MDRIIA - Course Code: 702CO0E012)  
**Academic Term:** Academic Year 2026–2027 | Semester VI (B.Tech CSBS)  
**Institution:** SVKM's NMIMS MPSTME, Mumbai  

---

## 1. Authorized Research Title & Problem Statement

> "How can a 7-DOF surgical manipulator simulated in MuJoCo implement inverse kinematics Jacobian damping and low-pass tremor filtering to achieve sub-0.5 mm needle placement accuracy under simulated physiological surgeon hand tremor?"

### Core Engineering Focus
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body dynamic physics simulation (`models/surgical_7dof_robot.xml`).
* **Autonomous Control:** Closed-loop Python control architecture with student implementation boundaries (`src/surgical_tremor_controller.py`).
* **Technoeconomic Evaluation:** Dimensionless CSBS operational economics and return on investment model (`analytics/surgical_or_economics.py`).
* **Empirical Validation:** Reproducible benchmark trials and statistical hypothesis testing (`analytics/surgical_precision_benchmark.csv`).

---

> [!NOTE]
> ### The Devil's Advocate: Reality Check & Theoretical Roast
> *"Filtering out physiological surgeon tremor down to 5 micrometers with high-frequency Kalman filters, while the entire surgical suite is vibrating because someone in the adjacent hallway is rolling a 200 kg autoclave cart across the tile seams."*

---

## 2. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Role | Assigned Git Branch | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `E071` | `70362400034` | **Soumya Singh** | Lead Surgical Kinematics, Damped Least Squares IK & MuJoCo Modeler | `feat/e071-lead-surgical-kinema` | 7-DOF redundant manipulator kinematics, Damped Least Squares (DLS) Jacobian pseudo-inverse, singularity robustness, and joint velocity bounds. |
| `E033` | `70362400028` | **Harshal Khandekar** | Digital Signal Processing, Tremor Modeling & Kalman Filtering Lead | `feat/e033-digital-signal-proce` | Physiological surgeon tremor modeling (8-12 Hz Gaussian bandpass noise), discrete Butterworth/Kalman filter implementation, and phase lag minimization. |

### Student Engineering Commendation & Acknowledgments
SVKM's NMIMS MPSTME conveys sincere appreciation and heartfelt gratitude to **Soumya Singh (E071)** and **Harshal Khandekar (E033)** for their disciplined commitment, late-night debugging, and technical craftsmanship throughout Semester VI. Your rigorous work in DeepMind MuJoCo physics modeling, closed-loop telemetry instrumentation, and Computer Science & Business Systems (CSBS) technoeconomic modeling exemplifies the highest standards of undergraduate engineering inquiry.

> *"Scientists discover the world that exists; engineers create the world that never was."*  
> — **Theodore von Kármán**

> *"There is no substitute for hard work. Genius is one percent inspiration and ninety-nine percent perspiration."*  
> — **Thomas A. Edison**

---

## 3. Foundational Literature Benchmarks (Strict 2 Seminal : 4 Recent Ratio)

The research project is theoretically anchored on six foundational peer-reviewed publications validated against global bibliographic databases.

| # | Author (Year) | Type | Paper Title | Venue / Indexing | Active DOI Link | Primary Extracted Formulation | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Yang et al. (2015)** | Recent | *Manipulator Design and Operation of a Six-Degree-of-Freedom Handheld Tremor-Canceling Microsurgical Instrument* | IEEE/ASME Transactions on Mechatronics | [https://doi.org/10.1109/TMECH.2014.2320858](https://doi.org/10.1109/TMECH.2014.2320858) | `Tremor attenuation ratio $\Gamma = 20 \log_{1...` | Soumya Singh (E071) & Harshal Khandekar (E033) |
| 2 | **Taylor & Stoianovici (2003)** | Recent | *Medical robotics in computer-integrated surgery* | IEEE Transactions on Robotics and Automation | [https://doi.org/10.1109/TRA.2003.817058](https://doi.org/10.1109/TRA.2003.817058) | `Safety boundary virtual fixture $F_{\text{fix...` | Soumya Singh (E071) |
| 3 | **Chiaverini (1997)** | Seminal | *Singularity-robust task-priority redundancy resolution for real-time kinematic control of robot manipulators* | IEEE Transactions on Robotics and Automation | [https://doi.org/10.1109/70.585902](https://doi.org/10.1109/70.585902) | `Damped pseudo-inverse $J^* = J^T (J J^T + \la...` | Soumya Singh (E071) & Harshal Khandekar (E033) |
| 4 | **Riviere & Thakor (1998)** | Seminal | *Adaptive cancelling of physiological tremor for improved precision in microsurgery* | IEEE Transactions on Biomedical Engineering | [https://doi.org/10.1109/10.686791](https://doi.org/10.1109/10.686791) | `Tremor signal model $x_k = \sum_{i=1}^M \left...` | Harshal Khandekar (E033) |
| 5 | **Childers & Maggard-Gibbons (2018)** | Recent | *Understanding Costs of Care in the Operating Room* | JAMA Surgery | [https://doi.org/10.1001/jamasurg.2017.6233](https://doi.org/10.1001/jamasurg.2017.6233) | `OR cost rate $C_{\text{OR}} = \text{BaseRate}...` | Soumya Singh (E071) & Harshal Khandekar (E033) |
| 6 | **Riviere et al. (2003)** | Recent | *Toward active tremor canceling in handheld microsurgical instruments* | IEEE Transactions on Robotics and Automation | [https://doi.org/10.1109/TRA.2003.817506](https://doi.org/10.1109/TRA.2003.817506) | `Transfer function $H(s) = \frac{s^2 + 2\zeta_...` | Harshal Khandekar (E033) & Soumya Singh (E071) |

For the exhaustive literature analysis, mathematical derivations, and viva defense questions, refer to:
* [`docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md`](docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md)
* [`docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md`](docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md)

---

## 4. Project Demonstration & Academic Showcase (LinkedIn)

[![Watch Video Demonstration on LinkedIn](docs/figures/video_poster.png)](https://www.linkedin.com/)

* **Video Demonstration:** [Watch 60-Second Walkthrough on LinkedIn](https://www.linkedin.com/) *(Click thumbnail above to open LinkedIn post)*
* **Student Presenters:** **Soumya Singh** (E071), **Harshal Khandekar** (E033)
* **Academic Institutional Tags:** SVKM's NMIMS MPSTME | Academic Directorate | Industry 4.0 Robotics
* **Submission Protocol:** Record a 60–90 second demonstration of your MuJoCo simulation and telemetry. Publish on LinkedIn tagging MPSTME, Dean, and Course Faculty. Insert your live post URL in `docs/TEAM_ROSTER.json` under `"linkedin_url"`, and submit a pull request to update this project dossier and the cohort dashboard.

---

## 5. Repository Directory Architecture

```
.
|-- README.md                                          <- Front-page research charter, student roster & literature
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md               <- Comprehensive technical engineering guide
|-- docs/
|   |-- TEAM_ROSTER.json                               <- Machine-readable team configuration
|   |-- LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md   <- Exhaustive literature dossier (6 verified papers)
|   |-- RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md         <- 4-page IEEE conference manuscript blueprint
|   `-- figures/
|       |-- figure1_system_architecture.png            <- 300 DPI system architecture diagram
|       |-- figure2_kinematic_telemetry.png            <- 300 DPI kinematics and simulation telemetry
|       `-- figure3_comparative_performance.png        <- 300 DPI comparative benchmark visualization
|-- models/
|   |-- .gitkeep
|   `-- surgical_7dof_robot.xml                                    <- MuJoCo MJCF simulation model
|-- src/
|   |-- test_env.py                                    <- Physics validation & environment tester
|   `-- surgical_tremor_controller.py                                      <- Autonomous control loop (# TODO student boundaries)
`-- analytics/
    |-- .gitkeep
    |-- surgical_or_economics.py                                      <- CSBS dimensionless technoeconomic model
    |-- generate_paper_figures.py                      <- Standalone 300 DPI publication figure generator
    `-- surgical_precision_benchmark.csv                                    <- Empirical benchmark trial dataset
```

---

## 5. Pedagogical Boundaries: Guidance vs Student Ownership

To ensure academic rigor and authentic student learning, this repository enforces strict boundaries between scaffolding and student deliverables:

* **Provided by Course Scaffolding:**
  * Validated physical model architecture in MuJoCo MJCF (`models/surgical_7dof_robot.xml`).
  * Verification toolchain and smoke test script (`src/test_env.py`).
  * Literature foundation, mathematical formulations, and conference paper blueprint (`docs/`).
  * Dimensionless technoeconomic framework (`analytics/surgical_or_economics.py`).
* **Student Technical Deliverables (Required for Evaluation):**
  * Implement and tune the control algorithm in `src/surgical_tremor_controller.py` (filling all marked `# TODO [Student Roll / Name]` blocks).
  * Run physics simulation trials to collect and expand empirical data in `analytics/surgical_precision_benchmark.csv`.
  * Re-run `analytics/generate_paper_figures.py` to regenerate publication figures with live experimental telemetry.
  * Author the final 4-page IEEE conference paper in `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend individual Git commits during the oral viva.

---

## 6. Sprint 0 Onboarding & Physics Environment Verification

Verify your local Python and MuJoCo simulation environment:

```powershell
# Step 1: Clone repository and navigate to group directory
git clone <repository_url>
cd <repository_root>/Group_10_Soumya_Harshal_Arham_Aneesh

# Step 2: Checkout your individual feature branch
# Example for lead student:
git checkout -b feat/e071-lead-surgical-kinema

# Step 3: Run environment smoke test
python src/test_env.py

# Step 4: Verify 300 DPI publication figures
python analytics/generate_paper_figures.py
```
