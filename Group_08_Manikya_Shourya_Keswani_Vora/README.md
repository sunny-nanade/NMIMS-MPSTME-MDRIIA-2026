# MDRIIA_GROUP_08: Autonomous Multirotor UAV for Medical Relief Air-Drop in Flood Operations

---

## 1. Authorized Research Title & Problem Statement

> "To what extent can an autonomous vision-guided multirotor UAV simulated in MuJoCo for payload-range trade-offs optimize last-mile medical relief drop accuracy during NDRF flood operations while establishing fleet utilization payback parity against ground transport?"

### Core Engineering Focus
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body dynamic physics simulation (`models/skyhydro_flood_uav.xml`).
* **Autonomous Control:** Closed-loop Python control architecture with student implementation boundaries (`src/flood_relief_drop_sim.py`).
* **Technoeconomic Evaluation:** Dimensionless CSBS operational economics and return on investment model (`analytics/disaster_relief_logistics.py`).
* **Empirical Validation:** Reproducible benchmark trials and statistical hypothesis testing (`analytics/flood_relief_benchmark.csv`).

---

## 2. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Role | Assigned Git Branch | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `E056` | `70362400045` | **Manikya Rathore** | Lead UAV Aerodynamics, Payload Physics & MuJoCo Modeler | `feat/e056-lead-uav-aerodynamic` | 6-DOF quadrotor aerodynamics, cable-suspended payload pendulum dynamics, rotor thrust-to-weight scaling, and air-drop release mechanics. |
| `E020` | `70362400015` | **Shourya Garg** | Computer Vision, Thermal Survivor Detection & Winch Drop Specialist | `feat/e020-computer-vision-ther` | Vision-based target tracking, circular landing/drop zone identification, downwash compensation, and payload release timing. |
| `E032` | `70362400072` | **Keswani Laksh** | Flight Path Optimization & Wind Gust Disturbance Control Lead | `feat/e032-flight-path-optimiza` | Dryden wind turbulence modeling, payload swing attenuation, LQR attitude stabilization, and flight envelope bounds. |
| `E067` | `70362400020` | **Vora Jash** | CSBS Disaster Logistics, Fleet Economics & Cost-Parity Analyst | `feat/e067-csbs-disaster-logist` | Disaster relief supply chain modeling, payload-range battery trade-offs, NDRF boat replacement ratios, and fleet amortization models. |

---

## 3. Foundational Literature Benchmarks (6 Verified Peer-Reviewed Papers)

The research project is theoretically anchored on six foundational peer-reviewed publications validated against global bibliographic databases.

| # | Author (Year) | Paper Title | Venue / Indexing | Active DOI Link | Primary Extracted Formulation | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Dorling et al. (2017)** | *Vehicle Routing Problems for Drone Delivery* | IEEE Transactions on Systems, Man, and Cybernetics: Systems | [https://doi.org/10.1109/TSMC.2016.2582745](https://doi.org/10.1109/TSMC.2016.2582745) | `Power consumption model $P(m) = (m_{\text{dro...` | Vora Jash (E067) & Manikya Rathore (E056) |
| 2 | **Chowdhury et al. (2017)** | *Drones for disaster response and relief operations: A continuous approximation model* | International Journal of Production Economics | [https://doi.org/10.1016/j.ijpe.2017.03.024](https://doi.org/10.1016/j.ijpe.2017.03.024) | `Fleet demand coverage $D(x,y) = \int \int \rh...` | Vora Jash (E067) |
| 3 | **Zhang et al. (2023)** | *Real-Time Local Obstacle Avoidance and Trajectory Tracking Control of Quadrotor UAVs With Suspended Payload in Complex Environments* | IEEE Access | [https://doi.org/10.1109/ACCESS.2023.3344578](https://doi.org/10.1109/ACCESS.2023.3344578) | `Cable swing dynamics $\ddot{\alpha} + \frac{g...` | Manikya Rathore (E056) & Keswani Laksh (E032) |
| 4 | **Falanga et al. (2017)** | *Vision-based autonomous quadrotor landing on a moving platform* | IEEE International Symposium on Safety, Security and Rescue Robotics (SSRR) | [https://doi.org/10.1109/SSRR.2017.8088164](https://doi.org/10.1109/SSRR.2017.8088164) | `Visual error vector $\mathbf{e}_v = \mathbf{p...` | Shourya Garg (E020) |
| 5 | **Scholten, Fumagalli et al. (2013)** | *Interaction control of an UAV endowed with a manipulator* | IEEE International Conference on Robotics and Automation (ICRA) | [https://doi.org/10.1109/ICRA.2013.6631278](https://doi.org/10.1109/ICRA.2013.6631278) | `Coupled mass matrix $\begin{bmatrix} M_{uu} &...` | Manikya Rathore (E056) & Shourya Garg (E020) |
| 6 | **Kamal et al. (2018)** | *Using crowdsourcing to identify critical affected areas for rapid damage assessment: Hurricane Matthew case study* | International Journal of Disaster Risk Reduction | [https://doi.org/10.1016/j.ijdrr.2018.02.003](https://doi.org/10.1016/j.ijdrr.2018.02.003) | `Isolation index $\Omega = \frac{T_{\text{subm...` | Keswani Laksh (E032) & Vora Jash (E067) |

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
|   `-- skyhydro_flood_uav.xml                                    <- MuJoCo MJCF simulation model
|-- src/
|   |-- test_env.py                                    <- Physics validation & environment tester
|   `-- flood_relief_drop_sim.py                                      <- Autonomous control loop (# TODO student boundaries)
`-- analytics/
    |-- .gitkeep
    |-- disaster_relief_logistics.py                                      <- CSBS dimensionless technoeconomic model
    |-- generate_paper_figures.py                      <- Standalone 300 DPI publication figure generator
    `-- flood_relief_benchmark.csv                                    <- Empirical benchmark trial dataset
```

---

## 5. Pedagogical Boundaries: Guidance vs Student Ownership

To ensure academic rigor and authentic student learning, this repository enforces strict boundaries between scaffolding and student deliverables:

* **Provided by Course Scaffolding:**
  * Validated physical model architecture in MuJoCo MJCF (`models/skyhydro_flood_uav.xml`).
  * Verification toolchain and smoke test script (`src/test_env.py`).
  * Literature foundation, mathematical formulations, and conference paper blueprint (`docs/`).
  * Dimensionless technoeconomic framework (`analytics/disaster_relief_logistics.py`).
* **Student Technical Deliverables (Required for Evaluation):**
  * Implement and tune the control algorithm in `src/flood_relief_drop_sim.py` (filling all marked `# TODO [Student Roll / Name]` blocks).
  * Run physics simulation trials to collect and expand empirical data in `analytics/flood_relief_benchmark.csv`.
  * Re-run `analytics/generate_paper_figures.py` to regenerate publication figures with live experimental telemetry.
  * Author the final 4-page IEEE conference paper in `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend individual Git commits during the oral viva.

---

## 6. Sprint 0 Onboarding & Physics Environment Verification

Verify your local Python and MuJoCo simulation environment:

```powershell
# Step 1: Clone repository and navigate to group directory
git clone <repository_url>
cd <repository_root>/Group_08_Manikya_Shourya_Keswani_Vora

# Step 2: Checkout your individual feature branch
# Example for lead student:
git checkout -b feat/e056-lead-uav-aerodynamic

# Step 3: Run environment smoke test
python src/test_env.py

# Step 4: Verify 300 DPI publication figures
python analytics/generate_paper_figures.py
```
