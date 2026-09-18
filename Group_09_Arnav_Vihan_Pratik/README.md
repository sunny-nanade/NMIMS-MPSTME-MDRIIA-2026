# Group 09: Group_09_Arnav_Vihan_Pratik
**Course:** Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS)  
**Domain Track:** UGV for defence and hazardous applications  

---

## 🎯 Authorized Research Title
> **"How can an autonomous ground vehicle utilizing simulated LiDAR rangefinders and traversability cost-mapping in MuJoCo navigate unknown unstructured hazardous terrain while reducing teleoperation cognitive workload and communication latency?"**

### Pedagogical & Scientific Objectives
* **Physics & Kinematics:** Google DeepMind MuJoCo multi-body physics simulation.
* **Autonomous Control:** Closed-loop Python PID / obstacle avoidance state machine.
* **CSBS Business Model:** Technoeconomic evaluation based on dimensionless operational metrics, labor reallocation, and payback parity.

---

## 👥 Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E064` | `70362400067` | **Arnav Saurabh Surve** | Lead UGV Skid-Steer Dynamics & MuJoCo Terrain Modeler | `feat/e064-lead-ugv-skid-steer-` |
| `E070` | `70362400086` | **Vihan Shripad Joshi** | LiDAR Perception, 3D Elevation Mapping & Obstacle Segmentation Lead | `feat/e070-lidar-perception-3d-` |
| `E073` | `70362300032` | **Pratik Mangesh Gaikwad** | CSBS Hazardous Operations Safety & Teleoperation Latency Analyst | `feat/e073-csbs-hazardous-opera` |


---

## 📁 Directory Structure
```
Group_09_Arnav_Vihan_Pratik/
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
