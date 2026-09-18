# Autonomous Tracked Crawler Cleaning Robot for Inclined Photovoltaic Solar Arrays

## Project Charter and Research Scaffolding
**Group ID:** MDRIIA Group 06  
**Project Track:** Modern Day Robotics and Industrial Applications  

---

## 1. Problem Statement and Interrogative Research Question

Atmospheric particulate accumulation and dust cementation on commercial rooftop photovoltaic (PV) installations degrade monthly power generation by 15% to 18% in high-pollution urban and industrial environments. Conventional manual wet cleaning relies on contracted human labor, presenting severe occupational slip-and-fall hazards on inclined roofs (10 to 30 degrees tilt) and consuming 3.5 to 5.0 liters of treated water per square meter. Water-free autonomous tracked crawler robots offer an environmentally sustainable alternative. However, continuous operation on inclined, low-friction borosilicate glass panels introduces critical dynamic challenges: maintaining tread adhesion without downhill slip, suppressing mechanical vibration to prevent solar cell micro-cracking, and executing comprehensive boustrophedon cleaning coverage.

### Aalborg Interrogative Research Title
> **"How can an autonomous crawler cleaning robot simulated in MuJoCo recover soiling-induced energy losses (15-18% monthly) on inclined commercial rooftop solar arrays while reducing cleaning cycle operational expenditure compared to manual labor?"**

---

## 2. Research Hypotheses and Engineering Scope

### Scientific Hypotheses
* **Null Hypothesis (H0):** An autonomous crawler cleaning robot traversing an inclined PV array (20-degree tilt) in MuJoCo exhibits significant downward slip (slip ratio > 15%), cannot achieve full surface coverage, and fails to yield a statistically significant reduction in cleaning cycle operational expenditure compared to manual labor (p >= 0.05).
* **Alternative Hypothesis (H1):** An autonomous crawler cleaning robot utilizing high-friction EPDM tracks and slope-compensating velocity control achieves stable adhesion (slip ratio < 3.5%), executes 100% boustrophedon cleaning coverage, maintains vibration deflections below 1.0 mm (ISO/IEC compliance), recovers > 95% of soiling-induced power attenuation, and achieves a positive dimensionless economic payback in under 12 months (p < 0.001).

---

## 3. Foundational Literature Benchmarks

The research foundation for this project is established upon five peer-reviewed publications:

1. **Figgis, Bermudez, & Garcia (2023)** - *Solar Energy*  
   *Title:* PV module vibration by robotic cleaning  
   *DOI:* [10.1016/j.solener.2022.12.049](https://doi.org/10.1016/j.solener.2022.12.049)  
   *Key Baseline:* Establishes that robotic brush excitation (~7 Hz) causes module deflections < 1.0 mm, confirming mechanical safety against cell cracking.

2. **Song, Liu, & Yang (2021)** - *Applied Energy*  
   *Title:* Air pollution and soiling implications for solar photovoltaic power generation: A comprehensive review  
   *DOI:* [10.1016/j.apenergy.2021.117247](https://doi.org/10.1016/j.apenergy.2021.117247)  
   *Key Baseline:* Synthesizes dust deposition mechanics and quantifies regional soiling rates causing 15% to 18% monthly energy losses.

3. **Al-Housani, Bicer, & Koc (2023)** - *Solar Energy*  
   *Title:* Effect of cleaning Robot's moving shadow on PV string  
   *DOI:* [10.1016/j.solener.2023.03.003](https://doi.org/10.1016/j.solener.2023.03.003)  
   *Key Baseline:* Models transient shading effects of cleaning robots during active daylight maintenance.

4. **Al-Neama, Farah, & Al-Habaibeh (2022)** - *Solar Energy*  
   *Title:* An infrared based dust mitigation system operated by the robotic arm for performance improvement of the solar panel  
   *DOI:* [10.1016/j.solener.2022.08.064](https://doi.org/10.1016/j.solener.2022.08.064)  
   *Key Baseline:* Demonstrates dust removal efficiency metrics and electrical performance restoration.

5. **Wang et al. (2022)** - *IEEE Transactions on Systems, Man, and Cybernetics: Systems*  
   *Title:* A Hybrid Cleaning Scheduling Framework for Operations and Maintenance of Photovoltaic Systems  
   *DOI:* [10.1109/TSMC.2021.3131031](https://doi.org/10.1109/TSMC.2021.3131031)  
   *Key Baseline:* Supplies mathematical optimization formulations linking cleaning frequency to Levelized Cost of Energy (LCOE).

---

## 4. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Assigned Engineering Role | Git Feature Branch | Individual Deliverable Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **E048** | `70362400013` | Arush Ashish Patil | Lead Tracked Crawler Chassis & MuJoCo Adhesion Modeler | `feat/e048-lead-tracked-crawler` | Tracked chassis kinematics, Coulomb-Contensou friction calibration, edge-fall detection |
| **E052** | `70362400001` | Ronit Rajput | Waterless Rotary Brush Actuation & Cleaning Efficiency Engineer | `feat/e052-waterless-rotary-bru` | High-speed cylindrical brush actuation, boustrophedon path planning, anti-slip control |
| **E058** | `70362400031` | Harshvardhan Sahi | CSBS Photovoltaic Degradation & CapEx/OpEx Payback Analyst | `feat/e058-csbs-photovoltaic-de` | Mumbai particulate soiling kinetics, power recovery telemetry, dimensionless LCOE model |

---

## 5. Repository Directory Architecture

```
Group_06_Arush_Ronit_Harshvardhan/
|-- README.md                                  <- Project charter, literature, and student matrix
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md       <- Friction laws, brush dynamics, viva prep
|-- docs/
|   |-- TEAM_ROSTER.json                       <- Machine-readable member identity schema
|   |-- LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md <- Detailed analysis of 5 verified papers
|   |-- RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md <- IEEE/ACM 4-page conference template
|   `-- figures/
|       |-- figure1_system_architecture.png    <- High-res system block diagram
|       |-- figure2_kinematic_telemetry.png    <- High-res track slip & vibration deflection plot
|       `-- figure3_comparative_performance.png <- High-res power recovery & OpEx amortization
|-- models/
|   `-- solar_cleaning_crawler.xml             <- MuJoCo MJCF 20-deg inclined PV array and robot
|-- src/
|   |-- crawler_cleaning_controller.py         <- Anti-slip control script with student TODO blocks
|   `-- test_env.py                            <- Toolchain verification and test step script
`-- analytics/
    |-- generate_paper_figures.py              <- Automation script generating publication figures
    |-- photovoltaic_degradation_economics.py  <- CSBS soiling kinetics & LCOE payback analysis
    `-- solar_cleaning_benchmark.csv           <- N=80 trial simulation dataset
```

---

## 6. Pedagogical Boundaries: Guidance vs Student Ownership

1. **Provided Scaffolding:**
   * Inclined plane multi-contact friction formulations and soiling degradation kinetics.
   * Curated literature dossier of 5 verified papers with active DOIs.
   * Baseline MuJoCo MJCF model with inclined solar array, perimeter framing, and crawler chassis.
   * 4-page conference manuscript blueprint and publication figure generation scripts.

2. **Mandatory Student Contributions (Students Must Implement and Commit):**
   * Students must implement their respective `# TODO` blocks in `src/crawler_cleaning_controller.py`.
   * Students must tune differential track velocities ($v_L, v_R$) and brush velocity setpoints ($900	ext{ RPM}$).
   * Students must execute Monte Carlo simulation runs ($N \ge 80$), record actual physical slip and vibration telemetry, and update `analytics/solar_cleaning_benchmark.csv`.
   * Students must complete the full text of `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend it in oral vivas.
