# Group 10: Group_10_Soumya_Harshal_Arham_Aneesh
**Course:** Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS)  
**Domain Track:** Intelligent robotics assistant for precision surgical task  

---

## 🎯 Authorized Research Title
> **"How can a 7-DOF surgical manipulator simulated in MuJoCo implement inverse kinematics Jacobian damping and low-pass tremor filtering to achieve sub-0.5 mm needle placement accuracy under simulated physiological surgeon hand tremor?"**

### Pedagogical & Scientific Objectives
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body physics simulation.
* **Autonomous Control:** Closed-loop Python PID / obstacle avoidance state machine.
* **CSBS Business Model:** Technoeconomic evaluation based on dimensionless operational metrics, labor reallocation, and payback parity.

---

## 👥 Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E071` | `70362400085` | **Soumya Singh** | Lead Surgical Kinematics, Damped Least Squares IK & MuJoCo Modeler | `feat/e071-lead-surgical-kinema` |
| `E033` | `70362400064` | **Harshal Khandekar** | Digital Signal Processing, Tremor Modeling & Kalman Filtering Lead | `feat/e033-digital-signal-proce` |
| `E069` | `70362300012` | **Arham Khan** | End-Effector Precision Telemetry & Sub-Millimeter Calibration Specialist | `feat/e069-end-effector-precisi` |
| `E076` | `70362300030` | **Aneesh Kumar** | CSBS Surgical Clinical Economics & OR Utilization Business Analyst | `feat/e076-csbs-surgical-clinic` |


---

## 📁 Directory Structure
```
Group_10_Soumya_Harshal_Arham_Aneesh/
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
