# Group 01: Autonomous Robot for Delivery of Critical Medicines in ICUs

---

## 1. Authorized Research Title
> "To what extent can an autonomous mobile medicine-delivery robot (simulated in MuJoCo with dynamic obstacle avoidance) reduce ICU nurses' non-patient-facing logistics transit time and optimize labor reallocation, where clinical studies document nurses spending approximately 28% of their shift on supply retrieval?"

### Core Engineering Focus
* Physics and Kinematics: Google DeepMind MuJoCo multi-body physics simulation with unicycle drive, passive casters, and anti-slosh liquid payload dynamics.
* Autonomous Control: Dynamic Window Approach (DWA) local trajectory planning, four-quadrant heading error normalization, and dynamic pedestrian evasion.
* CSBS Technoeconomic Analysis: Clinical workflow model, nursing transit time reduction, dimensionless operational cost parity ratio, and capital payback horizon.

---

## 2. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E006` | `70362400061` | **Khushal Asnani** | Lead Robotics Systems Architect & MuJoCo Physics Modeler | `feat/e006-amr-chassis` |
| `E016` | `70362400041` | **Priyal Kaushal Deputy** | Autonomous Navigation & Obstacle Avoidance Specialist | `feat/e016-navigation-planner` |
| `E054` | `70362400038` | **Ishita Ranjan** | CSBS Healthcare Systems & Time-Motion Workflow Analyst | `feat/e054-csbs-workflow` |
| `E060` | `70362400055` | **Sowmya Satish** | Telemetry, Quality Assurance & Empirical Validation Lead | `feat/e060-validation-qa` |

---

## 3. Foundational Literature and Academic Benchmarks (5 Verified Papers)

Students must study, benchmark against, and cite these 5 authentic peer-reviewed papers. See [docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md](./docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md) for the complete mathematical extraction and gap analysis.

1. **Hospital Logistics AMR Architecture (2026):**
   * *Dei et al.*, "Design and Performance Evaluation of a Modular Mobile Robot for Autonomous Hospital Logistics", *IEEE Transactions on Automation Science and Engineering*, vol. 23, pp. 7748–7763, 2026.
   * DOI: [10.1109/TASE.2026.3674356](https://doi.org/10.1109/TASE.2026.3674356)
   * Focus: Physical modular HOSBOT chassis, doorway clearance bounds (1.20 m), docking repeatability (+/- 15 mm).

2. **Hospital AMR Navigation Benchmarking (2024):**
   * *Rondoni et al.*, "Navigation benchmarking for autonomous mobile robots in hospital environment", *Scientific Reports (Nature Portfolio)*, vol. 14, art. no. 18334, 2024.
   * DOI: [10.1038/s41598-024-69040-z](https://doi.org/10.1038/s41598-024-69040-z)
   * Focus: Standardized multi-tier hospital benchmarking under ISO 13482:2014, path smoothness metrics, pedestrian avoidance.

3. **Stochastic AMR Scheduling with Time Windows (2023):**
   * *Cheng et al.*, "The Multi-Trip Autonomous Mobile Robot Scheduling Problem with Time Windows in a Stochastic Environment at Smart Hospitals", *Applied Sciences*, vol. 13, no. 17, art. no. 9879, 2023.
   * DOI: [10.3390/app13179879](https://doi.org/10.3390/app13179879)
   * Focus: Mixed-integer dispatch optimization, stochastic hallway delay distributions, delivery time windows.

4. **Liquid Anti-Slosh Motion Profiles (2020):**
   * *Terashima et al.*, "Optimal operating-speed-dependent motion profiles to reduce liquid slosh", *Robotics*, vol. 9, no. 1, art. no. 18, 2020.
   * DOI: [10.3390/robotics9010018](https://doi.org/10.3390/robotics9010018)
   * Focus: Centripetal lateral acceleration thresholding ($a_{\text{lat}} \le 0.40\text{ m/s}^2$) and total jerk bound ($\|\mathbf{j}\| \le 1.20\text{ m/s}^3$).

5. **Clinical Time-and-Motion Nursing Baseline (2021):**
   * *Michel et al.*, "How do nurses spend their time? A time and motion analysis of nursing activities in an internal medicine unit", *Journal of Advanced Nursing*, vol. 77, no. 11, pp. 4459–4470, 2021.
   * DOI: [10.1111/jan.14935](https://doi.org/10.1111/jan.14935)
   * Focus: Real-world empirical ground truth documenting 28% shift time spent on non-patient-facing transit (3.36 h/shift).

---

## 4. Directory Structure
```
Group_01_Khushal_Priyal_Ishita_Sowmya/
|-- README.md                             <- Group research charter, literature matrix, and status
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md  <- Complete technical dossier, kinematic proofs, and viva defense
|-- docs/
|   |-- LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md <- Detailed analysis of 5 papers & gap matrix
|   `-- TEAM_ROSTER.json                  <- Commit attribution registry
|-- models/
|   `-- icu_medicine_amr.xml              <- Physical MuJoCo MJCF model
|-- src/
|   `-- icu_amr_controller.py             <- Kinematic simulation loop and telemetry logger
`-- analytics/
    `-- icu_labor_roi.py                  <- CSBS dimensionless technoeconomic model
```

---

## 5. Sprint Onboarding Checklist (Sprint 0)
- [ ] Every team member clones repository locally.
- [ ] Each student creates their assigned feature branch (`feat/<roll_no>-...`).
- [ ] Study assigned research paper in [docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md](./docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md).
- [ ] Execute `python src/icu_amr_controller.py` and confirm clean execution.
- [ ] Update `docs/TEAM_ROSTER.json` with verified GitHub usernames.
- [ ] Submit and merge Sprint 0 Pull Request into `main`.
