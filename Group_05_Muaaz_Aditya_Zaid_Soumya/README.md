# Collaborative Dual-UAV Autonomous Surveillance System for Campus Perimeter Security

## Project Charter and Research Scaffolding
**Group ID:** MDRIIA Group 05  
**Project Track:** Modern Day Robotics and Industrial Applications  

---

## 1. Problem Statement and Interrogative Research Question

Institutional campus physical security frequently relies on manual security guard foot patrols that require 45 to 60 minutes per sweep and static closed-circuit television (CCTV) cameras that leave more than 35% of blind-spot zones unmonitored. This temporal latency and spatial occlusion expose physical boundaries to undetected intrusions. Autonomous aerial robotic swarms offer a high-speed, flexible surveillance alternative. However, collaborative multi-UAV perimeter patrol introduces complex engineering challenges in 6-DOF flight dynamics, inter-UAV collision avoidance, downward camera target detection under varied illumination, and real-time geofencing.

### Aalborg Interrogative Research Title
> **"To what extent can a collaborative dual-UAV surveillance system simulated in MuJoCo optimize campus perimeter patrol cycle time and OpenCV human detection latency compared to static security guard patrols?"**

---

## 2. Research Hypotheses and Engineering Scope

### Scientific Hypotheses
* **Null Hypothesis (H0):** A collaborative dual-UAV surveillance system simulated in MuJoCo achieves no statistically significant reduction in perimeter patrol sweep cycle time (min) or human intrusion detection latency (s) compared to conventional manual guard patrols (p >= 0.05).
* **Alternative Hypothesis (H1):** A collaborative dual-UAV surveillance system in MuJoCo reduces perimeter patrol cycle time by > 75%, maintains inter-UAV separation >= 2.5 m using Artificial Potential Fields (APF), and achieves real-time OpenCV human detection latency < 50 ms across illumination levels down to 5 lx, significantly outperforming foot-patrol baselines (p < 0.001).

---

## 3. Foundational Literature Benchmarks

The research foundation for this project is established upon five peer-reviewed publications:

1. **Guerrero-Bonilla & Dimarogonas (2021)** - *IEEE Robotics and Automation Letters*  
   *Title:* Perimeter surveillance based on set-invariance  
   *DOI:* [10.1109/LRA.2020.3028055](https://doi.org/10.1109/LRA.2020.3028055)  
   *Key Baseline:* Establishes set-invariance control laws for multi-robot perimeter coverage and intruder interception.

2. **Javaid, Saeed, Qadir, Fahim, He, Song, & Bilal (2023)** - *IEEE Transactions on Intelligent Transportation Systems*  
   *Title:* Communication and Control in Collaborative UAVs: Recent Advances and Future Trends  
   *DOI:* [10.1109/TITS.2023.3248841](https://doi.org/10.1109/TITS.2023.3248841)  
   *Key Baseline:* Surveys decentralized coordination, dynamic flight control, and communication constraints for multi-UAV swarms.

3. **Wu, Zhang, Sun, Li, Gao, & Han (2024)** - *IEEE Transactions on Vehicular Technology*  
   *Title:* Multi-UAV Collaborative Dynamic Task Allocation Method Based on ISOM and Attention Mechanism  
   *DOI:* [10.1109/TVT.2023.3341878](https://doi.org/10.1109/TVT.2023.3341878)  
   *Key Baseline:* Models dynamic task allocation and spatial sector partitioning for cooperative aerial surveillance.

4. **Cabreira, Brisolara, & Ferreira (2019)** - *Drones*  
   *Title:* Survey on Coverage Path Planning with Unmanned Aerial Vehicles  
   *DOI:* [10.3390/drones3010004](https://doi.org/10.3390/drones3010004)  
   *Key Baseline:* Evaluates optimal aerial coverage path planning algorithms across complex geometric boundaries.

5. **Mittal, Singh, & Sharma (2020)** - *Image and Vision Computing*  
   *Title:* Deep learning-based object detection in low-altitude UAV datasets: A survey  
   *DOI:* [10.1016/j.imavis.2020.104046](https://doi.org/10.1016/j.imavis.2020.104046)  
   *Key Baseline:* Analyzes aerial object detection throughput, small-target resolution, and lighting variation challenges.

---

## 4. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Assigned Engineering Role | Git Feature Branch | Individual Deliverable Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **E043** | `70362400058` | Muaaz Mohammed Iqbal Shaikh | Lead UAV Flight Dynamics, Path Planner & Coordinated Fleet Architect | `feat/e043-lead-uav-flight-dyna` | 6-DOF Newton-Euler dynamics, cascaded PID attitude/position control, APF separation |
| **E051** | `70362400040` | Aditya Rajkumar | Computer Vision, OpenCV Human Detection & Tracking Specialist | `feat/e051-computer-vision-open` | MuJoCo camera rendering, OpenCV HSV/contour extraction, inverse pinhole ground projection |
| **E075** | `70362300055` | Zaid Rezaur Rahman | Restricted-Zone Geo-Fencing & Intrusion Telemetry Lead | `feat/e075-restricted-zone-geo-` | 3D polygonal geofencing, 4-tier alert state machine, JSON/CSV telemetry streaming |
| **E077** | `70362300043` | Soumya Subhankar Ranasingh | CSBS Campus Security Operations & OpEx Payback Analyst | `feat/e077-csbs-campus-security` | Time-motion patrol model, security labor reallocation matrix, dimensionless OpEx payback |

---

## 5. Repository Directory Architecture

```
Group_05_Muaaz_Aditya_Zaid_Soumya/
|-- README.md                                  <- Project charter, literature, and student matrix
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md       <- Flight dynamics, vision equations, viva prep
|-- docs/
|   |-- TEAM_ROSTER.json                       <- Machine-readable member identity schema
|   |-- LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md <- Detailed analysis of 5 verified papers
|   |-- RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md <- IEEE/ACM 4-page conference template
|   `-- figures/
|       |-- figure1_system_architecture.png    <- High-res system block diagram
|       |-- figure2_kinematic_telemetry.png    <- High-res flight path & inter-UAV separation
|       `-- figure3_comparative_performance.png <- High-res patrol cycle time & vision latency
|-- models/
|   `-- campus_perimeter_patrol.xml            <- MuJoCo MJCF dual-UAV environment with cameras
|-- src/
|   |-- aerial_patrol_swarm.py                 <- Swarm patrol controller with student TODO blocks
|   `-- test_env.py                            <- Toolchain verification and test step script
`-- analytics/
    |-- campus_security_economics.py           <- CSBS security operations & OpEx payback analysis
    |-- generate_paper_figures.py              <- Automation script generating publication figures
    `-- campus_patrol_benchmark.csv            <- N=80 trial simulation dataset
```

---

## 6. Pedagogical Boundaries: Guidance vs Student Ownership

1. **Provided Scaffolding:**
   * 6-DOF quadrotor equations of motion and cascaded PID control architecture.
   * Curated literature review of 5 verified papers with active DOIs.
   * Baseline dual-UAV MuJoCo MJCF model with campus perimeter boundaries and target avatar.
   * 4-page conference manuscript blueprint and figure rendering scripts.

2. **Mandatory Student Contributions (Students Must Implement and Commit):**
   * Students must implement their respective `# TODO` blocks in `src/aerial_patrol_swarm.py`.
   * Students must tune PID gains ($K_p, K_i, K_d$) for stable flight under dynamic cross-winds.
   * Students must execute Monte Carlo simulation runs ($N \ge 80$), log actual flight and vision telemetry, and update `analytics/campus_patrol_benchmark.csv`.
   * Students must complete the full text of `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend it in oral vivas.
