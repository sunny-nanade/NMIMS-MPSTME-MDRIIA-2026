# Autonomous Last-Mile Ground AED Delivery Robot for Sudden Cardiac Arrest

## Project Charter and Research Scaffolding
**Group ID:** MDRIIA Group 03  
**Project Track:** Modern Day Robotics and Industrial Applications  

---

## 1. Problem Statement and Interrogative Research Question

Out-of-hospital cardiac arrest (OHCA) is a time-critical medical emergency where bystander defibrillation before emergency medical service (EMS) arrival is the single greatest determinant of survival. In dense metropolitan areas, roadway traffic congestion routinely extends ambulance response intervals to 15 to 22 minutes. Because myocardial viability and resuscitation probability decay at 7% to 10% per minute without defibrillation, conventional roadway ambulances cannot reach victims within the critical 5-minute resuscitation window in over 85% of urban incidents.

### Aalborg Interrogative Research Title
> **"Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation?"**

---

## 2. Research Hypotheses and Engineering Scope

### Scientific Hypotheses
* **Null Hypothesis (H0):** An autonomous ground AED delivery vehicle with independent suspension cannot navigate simulated urban obstacles, curbs, and pedestrian corridors to achieve delivery times statistically superior to congested roadway ambulances (p >= 0.05).
* **Alternative Hypothesis (H1):** An autonomous ground AED delivery vehicle simulated in MuJoCo successfully negotiates urban sidewalk geometry, climbs 12 cm vertical curbs, maintains payload acceleration shock below 3.0g, and delivers an AED within 5.0 minutes, yielding an estimated survival probability improvement exceeding 250% relative to roadway ambulance dispatch (p < 0.001).

---

## 3. Foundational Literature Benchmarks

The research foundation for this project is established upon five peer-reviewed publications:

1. **Schierbeck et al. (2023)** - *The Lancet Digital Health*  
   *Title:* Drone delivery of automated external defibrillators compared with ambulance arrival in real-life suspected out-of-hospital cardiac arrests: a prospective observational study  
   *DOI:* [10.1016/S2589-7500(23)00161-9](https://doi.org/10.1016/S2589-7500(23)00161-9)  
   *Key Baseline:* Real-world automated AED delivery arrived before EMS in 67% of cases, saving 1 min 52 s in transit; highlights the need for all-weather ground delivery where drones cannot fly.

2. **Tsao et al. (2023)** - *Circulation (American Heart Association)*  
   *Title:* Heart Disease and Stroke Statistics—2023 Update: A Report From the American Heart Association  
   *DOI:* [10.1161/CIR.0000000000001123](https://doi.org/10.1161/CIR.0000000000001123)  
   *Key Baseline:* Quantifies cardiac arrest survival decay of 7% to 10% per minute of defibrillation delay.

3. **Naess et al. (2024)** - *PLOS ONE*  
   *Title:* Using machine learning to assess the extent of busy ambulances and its impact on ambulance response times: A retrospective observational study  
   *DOI:* [10.1371/journal.pone.0296308](https://doi.org/10.1371/journal.pone.0296308)  
   *Key Baseline:* Demonstrates 35.0% urban ambulance unavailability and median response delays of 15.0 to 22.0 minutes during high congestion.

4. **Weinberg et al. (2023)** - *Multimodal Technologies and Interaction*  
   *Title:* Sharing the Sidewalk: Observing Delivery Robot Interactions with Pedestrians during a Pilot in Pittsburgh, PA  
   *DOI:* [10.3390/mti7050053](https://doi.org/10.3390/mti7050053)  
   *Key Baseline:* Analyzes sidewalk delivery vehicle clearances (0.60 to 1.20 m) and pedestrian avoidance dynamics.

5. **Larsen et al. (1993)** - *Annals of Emergency Medicine*  
   *Title:* Predicting survival from out-of-hospital cardiac arrest: A graphic model  
   *DOI:* [10.1016/s0196-0644(05)81302-2](https://doi.org/10.1016/s0196-0644(05)81302-2)  
   *Key Baseline:* Defines mathematical resuscitation survival decay: P(survival) = 0.67 - 0.023 * t_CPR - 0.046 * t_defib.

---

## 4. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Assigned Engineering Role | Git Feature Branch | Individual Deliverable Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **E026** | `70362400060` | Kashish Praveen Jain | Lead Vehicle Suspension Dynamics & MuJoCo Modeler | `feat/e026-suspension-amr` | MJCF 4-wheel chassis, suspension spring-dampers, curb contact dynamics |
| **E046** | `70362400074` | Vaishnavi Parashar | Navigation, Curb-Climbing & Obstacle Guidance Lead | `feat/e046-curb-navigation` | Reactive APF/VFH navigation, torque-vectoring curb climbing, telemetry logger |
| **E057** | `70362400081` | Daneeka Abhijeet Roy | Emergency Medical Logistics & Survival Decay Analyst | `feat/e057-cardiac-survival` | Larsen survival model, congestion delay distributions, QALY economics |

---

## 5. Repository Directory Architecture

```
Group_03_Kashish_Vaishnavi_Daneeka/
|-- README.md                                  <- Project charter, literature, and student matrix
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md       <- Physics formulations, control equations, viva prep
|-- docs/
|   |-- TEAM_ROSTER.json                       <- Machine-readable member identity schema
|   |-- LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md <- Exhaustive review of 5 verified papers
|   |-- RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md <- IEEE/ACM 4-page conference template
|   `-- figures/
|       |-- figure1_system_architecture.png    <- High-res system block diagram
|       |-- figure2_kinematic_telemetry.png    <- High-res curb traversal & shock plot
|       `-- figure3_comparative_performance.png <- High-res survival curve & latency comparison
|-- models/
|   `-- aed_delivery_amr.xml                   <- MuJoCo MJCF physics model with suspension & curb
|-- src/
|   |-- aed_navigation_controller.py           <- Closed-loop control script with student TODO blocks
|   `-- test_env.py                            <- Toolchain verification and test step script
`-- analytics/
    |-- aed_delivery_benchmark.csv             <- N=80 trial simulation dataset
    |-- cardiac_survival_economics.py          <- Health economics & survival decay analysis
    `-- generate_paper_figures.py              <- Automation script generating publication figures
```

---

## 6. Pedagogical Boundaries: Guidance vs Student Ownership

To ensure academic integrity and genuine engineering development:

1. **Provided Scaffolding:**
   * Mathematical foundations, kinematic equations, and survival decay models.
   * Curated literature dossier with verified DOIs and benchmark parameters.
   * Starter MuJoCo MJCF physics model skeleton and toolchain verification script.
   * Manuscript blueprint and figure templates for IEEE/ACM publication.

2. **Mandatory Student Contributions (Students Must Implement and Commit):**
   * Students must implement their respective `# TODO` algorithmic blocks in `src/aed_navigation_controller.py`.
   * Students must tune suspension damping (`cs`), spring stiffness (`ks`), and tire friction in `models/aed_delivery_amr.xml`.
   * Students must execute Monte Carlo simulation runs ($N \ge 80$), record actual physical telemetry, and update `analytics/aed_delivery_benchmark.csv`.
   * Students must draft and complete the full text of `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` and defend it in oral vivas.
