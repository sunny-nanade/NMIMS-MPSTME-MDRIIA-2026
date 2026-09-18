# Research Project Group 10: 7-DOF Surgical Manipulator with Damped Least Squares IK and Physiological Tremor Filtering

## Academic Cohort: Robotics and Business Systems Engineering (PBL Track)

---

## 1. Executive Research Charter

### Primary Research Problem
How can a 7-DOF surgical manipulator simulated in MuJoCo implement inverse kinematics Jacobian damping and low-pass tremor filtering to achieve sub-0.5 mm needle placement accuracy under simulated physiological surgeon hand tremor?

### Core Investigation Domains
1. **Redundant Manipulator Kinematics & Singularity Avoidance:** Implementing a 7-DOF articulated kinematic chain in MuJoCo utilizing Damped Least Squares (Levenberg-Marquardt) to prevent extreme joint velocities near kinematic singularities.
2. **Digital Signal Processing for Physiological Tremor Suppression:** Characterizing 8-12 Hz hand tremor signals, designing low-latency discrete-time filtering (<25 ms phase lag), and executing real-time trajectory smoothing.
3. **Sub-Millimeter Surgical Precision & Healthcare Economics:** Quantifying needle placement Root Mean Square Error (RMSE), operating room turnaround efficiency, and complication reduction using dimensionless economic metrics.

---

## 2. Student Engineering Matrix

| Roll No | Name | Technical Role | Branch Responsibility | Core Viva Defense Area |
| :--- | :--- | :--- | :--- | :--- |
| **E071** | **Soumya Singh** | Lead Surgical Kinematics & Damped Least Squares IK Modeler | `feat/e071-lead-surgical-kinema` | 7-DOF redundant Jacobian, DLS damping factor, null-space projection |
| **E033** | **Harshal Khandekar** | DSP Tremor Modeling & Discrete-Time Filtering Lead | `feat/e033-digital-signal-proce` | 8-12 Hz bandpass characterization, phase lag compensation, filter stability |
| **E069** | **Arham Khan** | End-Effector Precision Telemetry & Sub-Millimeter Calibration | `feat/e069-end-effector-precisi` | Needle tip target registration, contact mechanics, sub-0.5 mm verification |
| **E076** | **Aneesh Kumar** | CSBS Surgical Clinical Economics & OR Utilization Analyst | `feat/e076-csbs-surgical-clinic` | OR time cost parity, procedure revision avoidance, capital amortization |

---

## 3. Directory Architecture

```
Group_10_Soumya_Harshal_Arham_Aneesh/
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
│   └── surgical_7dof_robot.xml                    <- MuJoCo MJCF 7-DOF surgical arm with needle end-effector
├── src/
│   ├── test_env.py                                <- Sprint 0 environment and physics compiler validator
│   └── surgical_tremor_controller.py              <- 7-DOF kinematics, tremor injection, and filtering state machine
└── analytics/
    ├── surgical_or_economics.py                   <- CSBS operating room economics and procedure payback model
    ├── generate_paper_figures.py                  <- 300 DPI visualization engine and benchmark dataset generator
    └── surgical_precision_benchmark.csv           <- 100-trial experimental benchmark dataset
```

---

## 4. Key Academic & Industry Milestones

- **Milestone 1 (Sprint 0-1):** 7-DOF MJCF validation, joint limit verification, and zero-gravity forward kinematics tests.
- **Milestone 2 (Sprint 2-3):** Implementation of Damped Least Squares IK, 8-12 Hz tremor injection, and low-pass filtering.
- **Milestone 3 (Sprint 4):** 100-trial Monte Carlo benchmark evaluating sub-0.5 mm needle accuracy across filter configurations.
- **Milestone 4 (Sprint 5):** Manuscript compilation following IEEE conference standards and reproducible Git audit defense.
