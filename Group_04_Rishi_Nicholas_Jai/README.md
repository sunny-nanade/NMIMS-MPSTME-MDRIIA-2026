# Multi-Arm Robotic Gripper for Non-Cooperative Space Debris Capture in LEO

## Project Charter and Research Scaffolding
**Group ID:** MDRIIA Group 04  
**Project Track:** Modern Day Robotics and Industrial Applications  

---

## 1. Problem Statement and Interrogative Research Question

The proliferation of orbital debris in Low Earth Orbit (LEO) poses an escalating threat to commercial satellite constellations and crewed space missions. Active Debris Removal (ADR) requires an autonomous servicer spacecraft to synchronize with and capture non-cooperative, tumbling orbital targets without prior mechanical mating fixtures. Conventional rigid position-controlled robotic manipulators impart severe collision impulses upon initial contact, often rebounding the target into unpredictable trajectories or inducing critical base attitude instabilities on the free-floating servicer bus.

### Aalborg Interrogative Research Title
> **"How can a multi-arm robotic gripper mechanism simulated in MuJoCo utilize impedance contact control to synchronize with and capture tumbling non-cooperative orbital debris in LEO while mitigating collision impulse and momentum transfer?"**

---

## 2. Research Hypotheses and Engineering Scope

### Scientific Hypotheses
* **Null Hypothesis (H0):** A multi-arm robotic gripper utilizing Cartesian impedance control achieves no statistically significant reduction in peak contact impulse (N) and no improvement in capture success rate (%) compared to conventional rigid proportional-derivative (PD) grasping during non-cooperative tumbling target capture (p >= 0.05).
* **Alternative Hypothesis (H1):** A multi-arm robotic gripper utilizing Cartesian operational space impedance contact control in MuJoCo reduces peak contact impulse by > 50%, suppresses servicer base attitude disturbance below 3.5 degrees, and achieves a capture success rate > 90% across debris tumble velocities up to 15 deg/s (p < 0.001).

---

## 3. Foundational Literature Benchmarks

The research foundation for this project is established upon five peer-reviewed publications:

1. **Yan, Xu, Hu, & Liang (2020)** - *Acta Astronautica*  
   *Title:* Multi-objective configuration optimization for coordinated capture of dual-arm space robot  
   *DOI:* [10.1016/j.actaastro.2019.11.002](https://doi.org/10.1016/j.actaastro.2019.11.002)  
   *Key Baseline:* Establishes dual-arm coordinated kinematics and base disturbance minimization for space manipulators.

2. **Rybus, Wojtunik, & Basmadji (2022)** - *Acta Astronautica*  
   *Title:* Optimal collision-free path planning of a free-floating space robot using spline-based trajectories  
   *DOI:* [10.1016/j.actaastro.2021.10.012](https://doi.org/10.1016/j.actaastro.2021.10.012)  
   *Key Baseline:* Models base reaction displacement of free-floating space robots and collision-free approach trajectory generation.

3. **Han, Huang, Liu, & Yang (2020)** - *Acta Astronautica*  
   *Title:* Combined spacecraft stabilization control after multiple impacts during the capture of a tumbling target by a space robot  
   *DOI:* [10.1016/j.actaastro.2020.05.035](https://doi.org/10.1016/j.actaastro.2020.05.035)  
   *Key Baseline:* Investigates post-impact dynamic coupling and stabilization of tumbling target-spacecraft coupled systems.

4. **Wang, Shi, & Katupitiya (2021)** - *Aerospace Science and Technology*  
   *Title:* A Strategy to Decelerate and Capture a Spinning Object by a Dual-Arm Space Robot  
   *DOI:* [10.1016/j.ast.2021.106682](https://doi.org/10.1016/j.ast.2021.106682)  
   *Key Baseline:* Supplies multi-phase deceleration and synchronization contact strategies for spinning targets.

5. **Tao, Zhang, Chu, Zhou, & Zhao (2021)** - *IEEE Access*  
   *Title:* Impedance-Sliding Mode Control with Force Constraints for Space Robots Capturing Non-Cooperative Objects  
   *DOI:* [10.1109/ACCESS.2021.3129835](https://doi.org/10.1109/ACCESS.2021.3129835)  
   *Key Baseline:* Formulates operational space impedance control with contact force bounds to eliminate contact rebound.

---

## 4. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Assigned Engineering Role | Git Feature Branch | Individual Deliverable Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **E034** | `70362400032` | Rishi Vinod Koli | Lead Orbital Dynamics & MuJoCo Multi-Body Physics Architect | `feat/e034-lead-orbital-dynamic` | Microgravity MJCF modeling, freejoint servicer base, tumbling target dynamics |
| **E035** | `70362400029` | Nicholas Lewis | Impedance Contact Control & Robotic Kinematics Engineer | `feat/e035-impedance-contact-co` | Cartesian impedance control law, phase synchronization, contact force absorption |
| **E036** | `70362400014` | Jai Maini | CSBS Commercial Space Economics & Satellite De-Orbiting Business Analyst | `feat/e036-csbs-commercial-spac` | Multi-target ADR cost recovery ratio, constellation asset preservation, FCC/ESA compliance |

---

## 5. Repository Directory Architecture

```
Group_04_Rishi_Nicholas_Jai/
|-- README.md                                  <- Project charter, literature, and student matrix
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md       <- Orbital equations, impedance laws, viva prep
|-- docs/
|   |-- TEAM_ROSTER.json                       <- Machine-readable member identity schema
|   |-- LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md <- Detailed analysis of 5 verified papers
|   |-- RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md <- IEEE/ACM 4-page conference template
|   `-- figures/
|       |-- figure1_system_architecture.png    <- High-res system block diagram
|       |-- figure2_kinematic_telemetry.png    <- High-res contact force and impulse plot
|       `-- figure3_comparative_performance.png <- High-res capture success rate vs tumble rate
|-- models/
|   `-- space_debris_gripper.xml               <- MuJoCo MJCF zero-G model with dual arms & target
|-- src/
|   |-- debris_capture_controller.py           <- Impedance control script with student TODO blocks
|   `-- test_env.py                            <- Toolchain verification and test step script
`-- analytics/
    |-- constellation_economics.py             <- Commercial space economics & risk mitigation
    |-- generate_paper_figures.py              <- Automation script generating publication figures
    `-- space_debris_capture_benchmark.csv     <- N=80 trial simulation dataset
```

---

## 6. Pedagogical Boundaries: Guidance vs Student Ownership

1. **Provided Scaffolding:**
   * Hill-Clohessy-Wiltshire orbital relative equations and Cartesian impedance formulation.
   * Curated literature dossier with verified DOIs and benchmark parameters.
   * Baseline microgravity MuJoCo MJCF model skeleton with dual 3-DOF arms.
   * 4-page conference manuscript blueprint and figure generation scripts.

2. **Mandatory Student Contributions (Students Must Implement and Commit):**
   * Students must implement their respective `# TODO` blocks in `src/debris_capture_controller.py`.
   * Students must tune virtual inertia ($M_d$), damping ($D_d$), and stiffness ($K_d$) parameters to achieve critical contact damping.
   * Students must execute Monte Carlo simulation runs ($N \ge 80$), record actual physical contact telemetry, and update `analytics/space_debris_capture_benchmark.csv`.
   * Students must draft and complete the full text of `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend it in oral vivas.
