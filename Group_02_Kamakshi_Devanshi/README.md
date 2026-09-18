# MDRIIA_GROUP_02: AI Companion Robot for Remote Elderly Supervision and Fall Emergency Response

---

## 1. Authorized Research Title & Problem Statement

> "How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?"

### Core Engineering Focus
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body dynamic physics simulation (`models/elderly_companion_base.xml`).
* **Autonomous Control:** Closed-loop Python control architecture with student implementation boundaries (`src/fall_detection_kinematics.py`).
* **Technoeconomic Evaluation:** Dimensionless CSBS operational economics and return on investment model (`analytics/geriatric_care_economics.py`).
* **Empirical Validation:** Reproducible benchmark trials and statistical hypothesis testing (`analytics/fall_triage_benchmark.csv`).

---

## 2. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Role | Assigned Git Branch | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `E007` | `70362400022` | **Kamakshi Bahuguna** | Computer Vision, Pose Kinematics & Edge Inference Specialist | `feat/e007-vision-pose-kinematics` | MediaPipe skeletal landmark tracking, bounding-box aspect ratio inversion, vertical centroid velocity thresholding, and confusion matrix validation. |
| `B029` | `70362400037` | **Devanshi Sachin Kambli** | MuJoCo Physics, Domestic Navigation & Healthcare Economics Lead | `feat/b029-mujoco-physics-navigation` | Differential mobile base physics, pan-tilt mast observation angles, post-fall approach trajectory, and 'long lie' clinical cost model. |

---

## 3. Foundational Literature Benchmarks (6 Verified Peer-Reviewed Papers)

The research project is theoretically anchored on six foundational peer-reviewed publications validated against global bibliographic databases.

| # | Author (Year) | Paper Title | Venue / Indexing | Active DOI Link | Primary Extracted Formulation | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Wang & Deng (2024)** | *Enhancing elderly care: Efficient and reliable real-time fall detection algorithm* | Digital Health | [https://doi.org/10.1177/20552076241233690](https://doi.org/10.1177/20552076241233690) | `Aspect ratio $AR = \frac{w_b}{h_b}$; vertical...` | Kamakshi Bahuguna (E007) |
| 2 | **Kothari & Chakurkar (2025)** | *Towards safer environments: A YOLO and MediaPipe-based human fall detection system* | MethodsX | [https://doi.org/10.1016/j.mex.2025.103623](https://doi.org/10.1016/j.mex.2025.103623) | `Keypoint angle $\theta = \arccos\left(\frac{\...` | Kamakshi Bahuguna (E007) |
| 3 | **Romero-Garces et al. (2022)** | *CLARA: Building a Socially Assistive Robot to Interact with Elderly People* | Designs | [https://doi.org/10.3390/designs6060125](https://doi.org/10.3390/designs6060125) | `Mast center-of-mass height $h_{\text{mast}} \...` | Devanshi Sachin Kambli (B029) |
| 4 | **Ding & Wang (2020)** | *A WiFi-Based Smart Home Fall Detection System Using Recurrent Neural Network* | IEEE Transactions on Consumer Electronics | [https://doi.org/10.1109/TCE.2020.3021398](https://doi.org/10.1109/TCE.2020.3021398) | `CSI phase difference $\Delta \phi = \arg(H_i)...` | Devanshi Sachin Kambli (B029) |
| 5 | **Kubitza et al. (2022)** | *Therapy options for those affected by a long lie after a fall: a scoping review* | BMC Geriatrics | [https://doi.org/10.1186/s12877-022-03258-2](https://doi.org/10.1186/s12877-022-03258-2) | `Hospital stay duration $D_{\text{stay}} = 18....` | Devanshi Sachin Kambli (B029) |
| 6 | **Chen et al. (2021)** | *Vision-Based Elderly Fall Detection Algorithm for Mobile Robot* | IEEE International Conference on Electronics Technology (ICET) | [https://doi.org/10.1109/ICET51757.2021.9450950](https://doi.org/10.1109/ICET51757.2021.9450950) | `Major-to-minor axis ratio $\lambda = \frac{a}...` | Kamakshi Bahuguna (E007) & Devanshi Sachin Kambli (B029) |

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
|   `-- elderly_companion_base.xml                                    <- MuJoCo MJCF simulation model
|-- src/
|   |-- test_env.py                                    <- Physics validation & environment tester
|   `-- fall_detection_kinematics.py                                      <- Autonomous control loop (# TODO student boundaries)
`-- analytics/
    |-- .gitkeep
    |-- geriatric_care_economics.py                                      <- CSBS dimensionless technoeconomic model
    |-- generate_paper_figures.py                      <- Standalone 300 DPI publication figure generator
    `-- fall_triage_benchmark.csv                                    <- Empirical benchmark trial dataset
```

---

## 5. Pedagogical Boundaries: Guidance vs Student Ownership

To ensure academic rigor and authentic student learning, this repository enforces strict boundaries between scaffolding and student deliverables:

* **Provided by Course Scaffolding:**
  * Validated physical model architecture in MuJoCo MJCF (`models/elderly_companion_base.xml`).
  * Verification toolchain and smoke test script (`src/test_env.py`).
  * Literature foundation, mathematical formulations, and conference paper blueprint (`docs/`).
  * Dimensionless technoeconomic framework (`analytics/geriatric_care_economics.py`).
* **Student Technical Deliverables (Required for Evaluation):**
  * Implement and tune the control algorithm in `src/fall_detection_kinematics.py` (filling all marked `# TODO [Student Roll / Name]` blocks).
  * Run physics simulation trials to collect and expand empirical data in `analytics/fall_triage_benchmark.csv`.
  * Re-run `analytics/generate_paper_figures.py` to regenerate publication figures with live experimental telemetry.
  * Author the final 4-page IEEE conference paper in `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend individual Git commits during the oral viva.

---

## 6. Sprint 0 Onboarding & Physics Environment Verification

Verify your local Python and MuJoCo simulation environment:

```powershell
# Step 1: Clone repository and navigate to group directory
git clone <repository_url>
cd <repository_root>/Group_02_Kamakshi_Devanshi

# Step 2: Checkout your individual feature branch
# Example for lead student:
git checkout -b feat/e007-vision-pose-kinematics

# Step 3: Run environment smoke test
python src/test_env.py

# Step 4: Verify 300 DPI publication figures
python analytics/generate_paper_figures.py
```
