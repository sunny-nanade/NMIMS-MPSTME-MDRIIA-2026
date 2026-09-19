# MDRIIA Group 03: Autonomous Last-Mile Ground AED Delivery Robot for Sudden Cardiac Arrest
**Course:** Modern Day Robotics and Its Industrial Applications (MDRIIA - Course Code: 702CO0E012)  
**Academic Term:** Academic Year 2026–2027 | Semester VI (B.Tech CSBS)  
**Institution:** SVKM's NMIMS MPSTME, Mumbai  

---

## 1. Authorized Research Title & Problem Statement

> "Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation?"

### Core Engineering Focus
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body dynamic physics simulation (`models/aed_delivery_amr.xml`).
* **Autonomous Control:** Closed-loop Python control architecture with student implementation boundaries (`src/aed_navigation_controller.py`).
* **Technoeconomic Evaluation:** Dimensionless CSBS operational economics and return on investment model (`analytics/cardiac_survival_economics.py`).
* **Empirical Validation:** Reproducible benchmark trials and statistical hypothesis testing (`analytics/aed_delivery_benchmark.csv`).

---

## 2. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Role | Assigned Git Branch | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `E026` | `70362400060` | **Kashish Praveen Jain** | Lead Autonomous Navigation & Traffic Congestion Modeling Specialist | `feat/e026-lead-autonomous-navi` | Sidewalk navigation dynamics, pedestrian crowd evasion, dynamic routing through urban choke points, and arrival latency budgets. |
| `E046` | `70362400074` | **Vaishnavi Parashar** | MuJoCo Dynamic Chassis Modeler & Path Optimization Engineer | `feat/e046-mujoco-dynamic-chass` | Four-wheel independent suspension, curb-climbing dynamics, shock isolation for biphasic AED pads, and contact friction stability. |
| `E057` | `70362400081` | **Daneeka Abhijeet Roy** | Emergency Medical Logistics & Cost-Effectiveness Business Analyst | `feat/e057-emergency-medical-lo` | Cardiac arrest survival decay modeling (7-10%/min), time-to-first-shock reduction, EMS fleet offloading ratios, and payback parity. |


### Student Engineering Commendation & Acknowledgments
SVKM's NMIMS MPSTME conveys sincere appreciation and heartfelt gratitude to **Kashish Praveen Jain (E026)**, **Vaishnavi Parashar (E046)**, and **Daneeka Abhijeet Roy (E057)** for their disciplined commitment, late-night debugging, and technical craftsmanship throughout Semester VI. Your rigorous work in DeepMind MuJoCo physics modeling, closed-loop telemetry instrumentation, and Computer Science & Business Systems (CSBS) technoeconomic modeling exemplifies the highest standards of undergraduate engineering inquiry.

> *"Scientists discover the world that exists; engineers create the world that never was."*  
> — **Theodore von Kármán**

> *"There is no substitute for hard work. Genius is one percent inspiration and ninety-nine percent perspiration."*  
> — **Thomas A. Edison**

---

## 3. Foundational Literature Benchmarks (Strict 2 Seminal : 4 Recent Ratio)

The research project is theoretically anchored on six foundational peer-reviewed publications validated against global bibliographic databases.

| # | Author (Year) | Type | Paper Title | Venue / Indexing | Active DOI Link | Primary Extracted Formulation | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Schierbeck et al. (2023)** | Recent | *Drone delivery of automated external defibrillators compared with ambulance arrival in out-of-hospital cardiac arrest* | The Lancet Digital Health | [https://doi.org/10.1016/S2589-7500(23)00161-9](https://doi.org/10.1016/S2589-7500(23)00161-9) | `Median time savings $\Delta t = 1\text{ min }...` | Daneeka Abhijeet Roy (E057) |
| 2 | **Tsao et al. (2023)** | Recent | *Heart Disease and Stroke Statistics-2023 Update: A Report From the American Heart Association* | Circulation | [https://doi.org/10.1161/CIR.0000000000001123](https://doi.org/10.1161/CIR.0000000000001123) | `Resuscitation decay rate $\frac{dS}{dt} = -k ...` | Daneeka Abhijeet Roy (E057) & Kashish Praveen Jain (E026) |
| 3 | **Naess et al. (2024)** | Recent | *Using machine learning to assess the extent of busy ambulance delays* | PLOS ONE | [https://doi.org/10.1371/journal.pone.0296308](https://doi.org/10.1371/journal.pone.0296308) | `Urban delay distribution $P(t_{\text{EMS}} > ...` | Kashish Praveen Jain (E026) |
| 4 | **Weinberg et al. (2023)** | Recent | *Sharing the Sidewalk: Observing Delivery Robot Interactions with Pedestrians* | Multimodal Technologies and Interaction | [https://doi.org/10.3390/mti7050053](https://doi.org/10.3390/mti7050053) | `Comfort lateral separation $d_{\text{sep}} \g...` | Kashish Praveen Jain (E026) & Vaishnavi Parashar (E046) |
| 5 | **Larsen et al. (1993)** | Seminal | *Predicting survival from out-of-hospital cardiac arrest: A graphic model* | Annals of Emergency Medicine | [https://doi.org/10.1016/s0196-0644(05)81302-2](https://doi.org/10.1016/s0196-0644(05)81302-2) | `Survival model: $S(t_{\text{cpr}}, t_{\text{d...` | Vaishnavi Parashar (E046) & Daneeka Abhijeet Roy (E057) |
| 6 | **Tripathi et al. (2020)** | Seminal | *Circadian variation of in-hospital cardiac arrest* | Resuscitation | [https://doi.org/10.1016/j.resuscitation.2020.08.014](https://doi.org/10.1016/j.resuscitation.2020.08.014) | `Adjusted survival odds ratio $\text{OR} = \ex...` | Vaishnavi Parashar (E046) & Kashish Praveen Jain (E026) |

For the exhaustive literature analysis, mathematical derivations, and viva defense questions, refer to:
* [`docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md`](docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md)
* [`docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md`](docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md)

---

## 4. Repository Directory Architecture

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
|   `-- aed_delivery_amr.xml                                    <- MuJoCo MJCF simulation model
|-- src/
|   |-- test_env.py                                    <- Physics validation & environment tester
|   `-- aed_navigation_controller.py                                      <- Autonomous control loop (# TODO student boundaries)
`-- analytics/
    |-- .gitkeep
    |-- cardiac_survival_economics.py                                      <- CSBS dimensionless technoeconomic model
    |-- generate_paper_figures.py                      <- Standalone 300 DPI publication figure generator
    `-- aed_delivery_benchmark.csv                                    <- Empirical benchmark trial dataset
```

---

## 5. Pedagogical Boundaries: Guidance vs Student Ownership

To ensure academic rigor and authentic student learning, this repository enforces strict boundaries between scaffolding and student deliverables:

* **Provided by Course Scaffolding:**
  * Validated physical model architecture in MuJoCo MJCF (`models/aed_delivery_amr.xml`).
  * Verification toolchain and smoke test script (`src/test_env.py`).
  * Literature foundation, mathematical formulations, and conference paper blueprint (`docs/`).
  * Dimensionless technoeconomic framework (`analytics/cardiac_survival_economics.py`).
* **Student Technical Deliverables (Required for Evaluation):**
  * Implement and tune the control algorithm in `src/aed_navigation_controller.py` (filling all marked `# TODO [Student Roll / Name]` blocks).
  * Run physics simulation trials to collect and expand empirical data in `analytics/aed_delivery_benchmark.csv`.
  * Re-run `analytics/generate_paper_figures.py` to regenerate publication figures with live experimental telemetry.
  * Author the final 4-page IEEE conference paper in `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend individual Git commits during the oral viva.

---

## 6. Sprint 0 Onboarding & Physics Environment Verification

Verify your local Python and MuJoCo simulation environment:

```powershell
# Step 1: Clone repository and navigate to group directory
git clone <repository_url>
cd <repository_root>/Group_03_Kashish_Vaishnavi_Daneeka

# Step 2: Checkout your individual feature branch
# Example for lead student:
git checkout -b feat/e026-lead-autonomous-navi

# Step 3: Run environment smoke test
python src/test_env.py

# Step 4: Verify 300 DPI publication figures
python analytics/generate_paper_figures.py
```
