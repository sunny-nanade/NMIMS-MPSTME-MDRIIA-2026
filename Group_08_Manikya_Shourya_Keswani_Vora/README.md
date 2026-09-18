# Research Project Group 08: Autonomous Vision-Guided Multirotor UAV for Flood Disaster Emergency Supply Delivery

## Academic Cohort: Robotics and Business Systems Engineering (PBL Track)

---

## 1. Executive Research Charter

### Primary Research Problem
To what extent can an autonomous vision-guided multirotor UAV simulated in MuJoCo for payload-range trade-offs optimize last-mile medical relief drop accuracy during flood disaster relief operations while establishing fleet utilization payback parity against conventional boat and ground transport?

### Core Investigation Domains
1. **Multirotor Flight Dynamics & Slung-Load Physics:** Simulating 6-DOF aerial vehicle aerodynamics coupled with cable-suspended emergency medical kits under turbulent crosswind gusts.
2. **Vision-Guided Precision Winch Delivery:** Real-time visual servoing, downward fiducial marker tracking, and active swing-damping winch release mechanisms.
3. **Disaster Logistics & Cost-Parity Modeling:** Formulating emergency supply chain routing, response latency reduction in inundated zones, and dimensionless fleet amortization.

---

## 2. Student Engineering Matrix

| Roll No | Name | Technical Role | Branch Responsibility | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- |
| **E056** | **Manikya Rathore** | Lead UAV Aerodynamics, Payload Physics & MuJoCo Modeler | `feat/e056-lead-uav-aerodynamic` | Multirotor thrust dynamics, slung-load pendulum physics, cable tension |
| **E020** | **Shourya Garg** | Vision Target Detection & Winch Drop Specialist | `feat/e020-computer-vision-ther` | Visual targeting, altitude estimation, winch brake triggering |
| **E032** | **Keswani Laksh** | Flight Path Optimization & Wind Gust Disturbance Control Lead | `feat/e032-flight-path-optimiza` | Waypoint navigation, L1 adaptive guidance, Dryden gust rejection |
| **E067** | **Vora Jash** | CSBS Disaster Logistics, Fleet Economics & Cost-Parity Analyst | `feat/e067-csbs-disaster-logist` | Queue-based relief delivery, payload-range energy trade-off, payback parity |

---

## 3. Directory Architecture

```
Group_08_Manikya_Shourya_Keswani_Vora/
├── README.md                                      <- Master project engineering charter
├── RESEARCH_AND_IMPLEMENTATION_GUIDE.md           <- In-depth technical specifications and student boundaries
├── docs/
│   ├── TEAM_ROSTER.json                           <- Machine-readable Git attribution schema
│   ├── LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md <- Exhaustive review of 5 peer-reviewed benchmark papers
│   ├── RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md     <- 4-page IEEE conference publication template
│   └── figures/                                   <- High-resolution publication diagrams (300 DPI)
│       ├── figure1_system_architecture.png
│       ├── figure2_kinematic_telemetry.png
│       └── figure3_comparative_performance.png
├── models/
│   └── skyhydro_flood_uav.xml                     <- MuJoCo MJCF quadrotor model with cable-suspended payload
├── src/
│   ├── test_env.py                                <- Sprint 0 environment and physics compiler validator
│   └── flood_relief_drop_sim.py                   <- Quadrotor flight control and winch drop state machine
└── analytics/
    ├── disaster_relief_logistics.py               <- CSBS fleet routing, response latency, and cost-parity model
    ├── generate_paper_figures.py                  <- 300 DPI visualization engine and benchmark dataset generator
    └── flood_relief_benchmark.csv                 <- 100-trial experimental benchmark dataset
```

---

## 4. Key Academic & Industry Milestones

- **Milestone 1 (Sprint 0-1):** Quadrotor MJCF validation, cable stiffness tuning, and aerodynamic drag verification.
- **Milestone 2 (Sprint 2-3):** Implementation of attitude PID, winch deployment logic, and visual target descent.
- **Milestone 3 (Sprint 4):** 100-trial Monte Carlo benchmark evaluation across calm, moderate, and severe crosswind conditions.
- **Milestone 4 (Sprint 5):** Manuscript compilation following IEEE conference standards and reproducible Git audit defense.
