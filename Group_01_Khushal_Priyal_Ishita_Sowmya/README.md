# Group 01: Group_01_Khushal_Priyal_Ishita_Sowmya
**Course:** Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS)  
**Domain Track:** Autonomous robot for delivery of critical medicines for ICUs  

---

## 🎯 Authorized Research Title
> **"To what extent can an autonomous mobile medicine-delivery robot (simulated in MuJoCo with dynamic obstacle avoidance) reduce ICU nurses' non-patient-facing logistics transit time and optimize labor reallocation, where clinical studies document nurses spending approximately 28% of their shift on supply retrieval?"**

### Pedagogical & Scientific Objectives
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body physics simulation.
* **Autonomous Control:** Closed-loop Python PID / obstacle avoidance state machine.
* **CSBS Business Model:** Technoeconomic evaluation based on dimensionless operational metrics, labor reallocation, and payback parity.

---

## 👥 Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E006` | `70362400061` | **Khushal Asnani** | Lead Robotics Systems Architect & MuJoCo Physics Modeler | `feat/e006-lead-robotics-system` |
| `E016` | `70362400041` | **Priyal Kaushal Deputy** | Autonomous Navigation, SLAM & Dynamic Collision Avoidance Specialist | `feat/e016-autonomous-navigatio` |
| `E054` | `70362400039` | **Ishita Ranjan** | CSBS Clinical Workflow & Time-Motion ROI Business Analyst | `feat/e054-csbs-clinical-workfl` |
| `E060` | `70362400055` | **Sowmya Satish** | Sensor Telemetry, Quality Assurance & Empirical Validation Lead | `feat/e060-sensor-telemetry-qua` |


---

## 📁 Directory Structure
```
Group_01_Khushal_Priyal_Ishita_Sowmya/
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
