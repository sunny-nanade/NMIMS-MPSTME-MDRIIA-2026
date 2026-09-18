# Research Project Group 09: Autonomous Hazardous Terrain UGV with LiDAR Traversability Cost-Mapping

## Academic Cohort: Robotics and Business Systems Engineering (PBL Track)

---

## 1. Executive Research Charter

### Primary Research Problem
How can an autonomous ground vehicle utilizing simulated LiDAR rangefinders and traversability cost-mapping in MuJoCo navigate unknown unstructured hazardous terrain while reducing teleoperation cognitive workload and communication latency?

### Core Investigation Domains
1. **Skid-Steer Multi-Body Physics & Terrain Dynamics:** Simulating 4-wheel/tracked vehicle mobility across uneven rubble, sharp grade transitions, and varying friction interfaces inside MuJoCo.
2. **LiDAR Elevation Mapping & Traversability Estimation:** Real-time geometric ground filtering, slope and step-height extraction, and 2.5D traversability cost-grid generation.
3. **Shared Autonomy & Human-in-the-Loop Operations:** Quantifying operator cognitive workload reduction (NASA-TLX metrics) and teleoperation performance degradation under variable network communication latency.

---

## 2. Student Engineering Matrix

| Roll No | Name | Technical Role | Branch Responsibility | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- |
| **E064** | **Arnav Saurabh Surve** | Lead UGV Skid-Steer Dynamics & MuJoCo Terrain Modeler | `feat/e064-lead-ugv-skid-steer-` | Skid-steer contact dynamics, wheel slippage, pitch/roll stability |
| **E070** | **Vihan Shripad Joshi** | LiDAR Perception, 3D Elevation Mapping & Obstacle Segmentation Lead | `feat/e070-lidar-perception-3d-` | Raycast processing, 2.5D elevation grid, traversability cost metrics |
| **E073** | **Pratik Mangesh Gaikwad** | CSBS Hazardous Operations Safety & Teleoperation Latency Analyst | `feat/e073-csbs-hazardous-opera` | Shared autonomy supervisory control, latency injection, NASA-TLX economics |

---

## 3. Directory Architecture

```
Group_09_Arnav_Vihan_Pratik/
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
│   └── hazardous_terrain_ugv.xml                  <- MuJoCo MJCF UGV simulation with uneven rubble terrain
├── src/
│   ├── test_env.py                                <- Sprint 0 environment and physics compiler validator
│   └── rough_terrain_recon_controller.py          <- UGV navigation, LiDAR mapping, and shared autonomy loop
└── analytics/
    ├── hazardous_recon_economics.py               <- CSBS industrial safety, cognitive workload & cost parity
    ├── generate_paper_figures.py                  <- 300 DPI visualization engine and benchmark dataset generator
    └── ugv_traversability_benchmark.csv           <- 100-trial experimental benchmark dataset
```

---

## 4. Key Academic & Industry Milestones

- **Milestone 1 (Sprint 0-1):** UGV chassis and multi-body terrain MJCF validation, wheel friction calibration, and kinematic unit tests.
- **Milestone 2 (Sprint 2-3):** Implementation of LiDAR rangefinder raycasting, local 2.5D elevation mapping, and cost-grid generation.
- **Milestone 3 (Sprint 4):** 100-trial Monte Carlo benchmark evaluation across benign, moderate, and extreme terrain roughness.
- **Milestone 4 (Sprint 5):** Manuscript compilation following IEEE conference standards and reproducible Git audit defense.
