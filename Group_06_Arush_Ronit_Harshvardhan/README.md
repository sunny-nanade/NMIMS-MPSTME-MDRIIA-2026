# Group 06: Group_06_Arush_Ronit_Harshvardhan
**Course:** Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS)  
**Domain Track:** Solar Panel Cleaning  

---

## 🎯 Authorized Research Title
> **"How can an autonomous crawler cleaning robot simulated in MuJoCo recover soiling-induced energy losses (15-18% monthly) on inclined commercial rooftop solar arrays while reducing cleaning cycle operational expenditure compared to manual labor?"**

### Pedagogical & Scientific Objectives
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body physics simulation.
* **Autonomous Control:** Closed-loop Python PID / obstacle avoidance state machine.
* **CSBS Business Model:** Technoeconomic evaluation based on dimensionless operational metrics, labor reallocation, and payback parity.

---

## 👥 Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E048` | `70362400013` | **Arush Ashish Patil** | Lead Tracked Crawler Chassis & MuJoCo Adhesion Modeler | `feat/e048-lead-tracked-crawler` |
| `E052` | `70362400001` | **Ronit Rajput** | Waterless Rotary Brush Actuation & Cleaning Efficiency Engineer | `feat/e052-waterless-rotary-bru` |
| `E058` | `70362400031` | **Harshvardhan Sahi** | CSBS Photovoltaic Degradation & CapEx/OpEx Payback Analyst | `feat/e058-csbs-photovoltaic-de` |


---

## 📁 Directory Structure
```
Group_06_Arush_Ronit_Harshvardhan/
├── README.md               <- Group research charter and milestone status
├── docs/
│   └── TEAM_ROSTER.json    <- Machine-readable commit attribution registry
├── src/
│   └── test_env.py         <- Local toolchain and MuJoCo verification script
├── models/                 <- MuJoCo MJCF XML models and textures
└── analytics/              <- CSV telemetry data and CSBS business ROI calculations
```

---

## 📅 Sprint Onboarding Checklist (Sprint 0)
- [ ] Every team member clones repository locally.
- [ ] Each student creates their assigned branch (`feat/<roll_no>-...`).
- [ ] Execute `python src/test_env.py` and confirm all checks pass.
- [ ] Update `docs/TEAM_ROSTER.json` with actual GitHub usernames.
- [ ] Submit and merge Sprint 0 Pull Request into `main`.
