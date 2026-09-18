# Group 03: Group_03_Kashish_Vaishnavi_Daneeka
**Course:** Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS)  
**Domain Track:** Autonomous ambulance robot for medical emergencies  

---

## 🎯 Authorized Research Title
> **"Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation?"**

### Pedagogical & Scientific Objectives
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body physics simulation.
* **Autonomous Control:** Closed-loop Python PID / obstacle avoidance state machine.
* **CSBS Business Model:** Technoeconomic evaluation based on dimensionless operational metrics, labor reallocation, and payback parity.

---

## 👥 Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E026` | `70362400060` | **Kashish Praveen Jain** | Lead Autonomous Navigation & Traffic Congestion Modeling Specialist | `feat/e026-lead-autonomous-navi` |
| `E046` | `70362400074` | **Vaishnavi Parashar** | MuJoCo Dynamic Chassis Modeler & Path Optimization Engineer | `feat/e046-mujoco-dynamic-chass` |
| `E057` | `70362400081` | **Daneeka Abhijeet Roy** | Emergency Medical Logistics & Cost-Effectiveness Business Analyst | `feat/e057-emergency-medical-lo` |


---

## 📁 Directory Structure
```
Group_03_Kashish_Vaishnavi_Daneeka/
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
