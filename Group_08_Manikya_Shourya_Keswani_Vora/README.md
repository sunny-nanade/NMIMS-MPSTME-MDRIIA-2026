# Group 08: Group_08_Manikya_Shourya_Keswani_Vora
**Course:** Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS)  
**Domain Track:** UAV for emergency supply delivery in floods (SkyHydro)  

---

## 🎯 Authorized Research Title
> **"To what extent can an autonomous vision-guided multirotor UAV simulated in MuJoCo for payload-range trade-offs optimize last-mile medical relief drop accuracy during NDRF flood operations while establishing fleet utilization payback parity against ground transport?"**

### Pedagogical & Scientific Objectives
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body physics simulation.
* **Autonomous Control:** Closed-loop Python PID / obstacle avoidance state machine.
* **CSBS Business Model:** Technoeconomic evaluation based on dimensionless operational metrics, labor reallocation, and payback parity.

---

## 👥 Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E056` | `70362400057` | **Manikya Rathore** | Lead UAV Aerodynamics, Payload Physics & MuJoCo Modeler | `feat/e056-lead-uav-aerodynamic` |
| `E020` | `70362400047` | **Shourya Garg** | Computer Vision, Thermal Survivor Detection & Winch Drop Specialist | `feat/e020-computer-vision-ther` |
| `E032` | `70362400048` | **Keswani Laksh** | Flight Path Optimization & Wind Gust Disturbance Control Lead | `feat/e032-flight-path-optimiza` |
| `E067` | `70362400015` | **Vora Jash** | CSBS Disaster Logistics, Fleet Economics & Cost-Parity Analyst | `feat/e067-csbs-disaster-logist` |


---

## 📁 Directory Structure
```
Group_08_Manikya_Shourya_Keswani_Vora/
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
