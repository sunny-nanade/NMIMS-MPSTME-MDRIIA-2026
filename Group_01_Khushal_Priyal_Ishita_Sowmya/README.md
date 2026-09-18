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

## 3. Directory Structure
```
Group_01_Khushal_Priyal_Ishita_Sowmya/
|-- README.md                             <- Group research charter and milestone status
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md  <- Complete technical dossier, verified literature, and viva defense
|-- docs/
|   `-- TEAM_ROSTER.json                  <- Commit attribution registry
|-- models/
|   `-- icu_medicine_amr.xml              <- Physical MuJoCo MJCF model
|-- src/
|   `-- icu_amr_controller.py             <- Kinematic simulation loop and telemetry logger
`-- analytics/
    `-- icu_labor_roi.py                  <- CSBS dimensionless technoeconomic model
```

---

## 4. Sprint Onboarding Checklist (Sprint 0)
- [ ] Every team member clones repository locally.
- [ ] Each student creates their assigned feature branch (`feat/<roll_no>-...`).
- [ ] Execute `python src/icu_amr_controller.py` and confirm clean execution.
- [ ] Update `docs/TEAM_ROSTER.json` with verified GitHub usernames.
- [ ] Submit and merge Sprint 0 Pull Request into `main`.

