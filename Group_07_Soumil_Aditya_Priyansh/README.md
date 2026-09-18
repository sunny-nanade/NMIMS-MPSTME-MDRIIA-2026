# Research Project Group 07: Autonomous Mobile Manipulator for Hospital Clutter Classification and Grasp Planning

## Academic Cohort: Robotics and Business Systems Engineering (PBL Track)

---

## 1. Executive Research Charter

### Primary Research Problem
How can an autonomous mobile manipulator simulated in MuJoCo for clutter classification and grasp planning reduce daily patient-room turnaround time for hospital housekeeping staff from the baseline 10-20 minutes per room?

### Core Investigation Domains
1. **Multi-Body Physics and Manipulation:** Modeling a mobile manipulator base with an articulated arm, parallel gripper, and dynamic multi-object contact friction inside MuJoCo.
2. **Grasp Planning in Dense Clutter:** Algorithmic grasp synthesis, collision-free trajectory planning, and push-to-grasp non-prehensile primitives for complex bedside clutter.
3. **Technoeconomic Workflow Optimization:** Quantifying room turnover acceleration, bed availability expansion, and labor reallocation using strictly dimensionless economic metrics.

---

## 2. Student Engineering Matrix

| Roll No | Name | Technical Role | Branch Responsibility | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- |
| **E050** | **Soumil Patro** | Lead Mobile Base Navigation & SLAM Engineer | `feat/e050-lead-mobile-base-nav` | Holonomic base positioning, obstacle clearance, waypoint tracking |
| **E062** | **Aditya Raju Shah** | Manipulator Arm Kinematics & Vision-Based Grasping Specialist | `feat/e062-manipulator-arm-kine` | 6-DOF IK damping, collision avoidance, gripper contact stability |
| **E066** | **Priyansh Thakkar** | CSBS Hospital Workflow Efficiency & Room Turnover Business Analyst | `feat/e066-csbs-hospital-workfl` | Room turnaround queuing model, infection control parity, dimensionless ROI |

---

## 3. Directory Architecture

```
Group_07_Soumil_Aditya_Priyansh/
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
│   └── hospital_clutter_manipulator.xml           <- MuJoCo MJCF simulation scene with multi-body clutter
├── src/
│   ├── test_env.py                                <- Sprint 0 environment and physics compiler validator
│   └── clutter_manipulator_controller.py          <- Arm trajectory and grasp state machine with student TODOs
└── analytics/
    ├── nosocomial_turnover_economics.py           <- Dimensionless room turnover and labor payback analytics
    ├── generate_paper_figures.py                  <- 300 DPI visualization engine and benchmark dataset generator
    └── clutter_manipulation_benchmark.csv         <- 100-trial experimental benchmark dataset
```

---

## 4. Key Academic & Industry Milestones

- **Milestone 1 (Sprint 0-1):** Multi-body MJCF validation, gripper contact calibration, and kinematics unit tests.
- **Milestone 2 (Sprint 2-3):** Implementation of closed-loop pick-and-place state machine and push-grasp primitives.
- **Milestone 3 (Sprint 4):** 100-trial Monte Carlo benchmark evaluation across sparse, moderate, and dense clutter distributions.
- **Milestone 4 (Sprint 5):** Manuscript compilation following IEEE conference standards and reproducible Git audit defense.
