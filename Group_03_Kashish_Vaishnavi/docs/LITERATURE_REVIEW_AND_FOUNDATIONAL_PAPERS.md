# Foundational Literature Review and Research Benchmark Dossier

## Project: Autonomous Last-Mile Ground AED Delivery Robot for Sudden Cardiac Arrest
## Group: MDRIIA_GROUP_03

---

## 1. Executive Summary of Foundational Literature

This dossier grounds the problem formulation, the mathematical models and the performance metrics of MDRIIA_GROUP_03 in six peer-reviewed publications (two seminal, four recent). Each DOI resolves on Crossref and the registered title matches the title cited; each summary below restates only what the paper's abstract reports, and says explicitly when the project takes no numerical input from a paper.

Corrections relative to the earlier draft of this dossier: the survival coefficients (the shock term is 0.011 per minute, not 0.046, and the model has a third term for advanced life support); the Schierbeck et al. study is a Swedish drone-AED study with 211 alerts and a median benefit of 3 min 14 s (not a 1 min 52 s saving); Naess et al. study busy ambulances and response times in Central Norway (not road congestion); Weinberg et al. report ethnographic observations of a Pittsburgh sidewalk-robot pilot (not clearance distances); Tsao et al. is the American Heart Association statistical update (no decay law); and the sixth paper, an in-hospital arrest study, was replaced by Khatib (1986) because it does not concern an outdoor sidewalk vehicle.

---

## 2. Comparative Literature Matrix (6 Verified Papers)

| Paper & Citation | Venue | What the paper does | What this project takes from it | Limits for this project | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Schierbeck et al. (2023)**<br>`10.1016/S2589-7500(23)00161-9` | *The Lancet Digital Health, 5(12):e862-e871* | Prospective drone-AED study in Sweden: 211 alerts, 55 comparable cases, drone first in 67%, median benefit 3 min 14 s | Arrival-before-ambulance benchmark (validation target) | Drone only, flight exclusions, no ground vehicle | Kashish Praveen Jain (E026) & Vaishnavi Parashar (E046) |
| **Tsao et al. (2023)**<br>`10.1161/CIR.0000000000001123` | *Circulation, 147* | Annual American Heart Association statistical update | Context only (no parameter taken) | US statistics, no vehicle model | Kashish Praveen Jain (E026) & Vaishnavi Parashar (E046) |
| **Naess et al. (2024)**<br>`10.1371/journal.pone.0296308` | *PLOS ONE, 19* | Busy ambulances and their association with response time, Central Norway 2013-2022 (216,787 incidents) | Response-time distribution and busy slope | Norwegian, busy ambulances not congestion, no 15-20 min delays | Kashish Praveen Jain (E026) |
| **Weinberg et al. (2023)**<br>`10.3390/mti7050053` | *Multimodal Technologies and Interaction, 7* | Ethnographic study of a sidewalk delivery-robot pilot in Pittsburgh | Qualitative scenario motivation (no parameter) | Commercial delivery pilot, no emergency use, no numbers | Kashish Praveen Jain (E026) & Vaishnavi Parashar (E046) |
| **Larsen et al. (1993)**<br>`10.1016/S0196-0644(05)81302-2` | *Annals of Emergency Medicine, 22(11):1652-1658* | Linear survival model from delays to CPR, first shock and ACLS (1,667 King County patients) | Coefficients of the primary survival model | High-survival subgroup, Western cohort, linear, no delivery device | Vaishnavi Parashar (E046) & Kashish Praveen Jain (E026) |
| **Khatib (1986)**<br>`10.1177/027836498600500106` | *The International Journal of Robotics Research, 5(1):90-98* | Artificial potential field obstacle avoidance for manipulators and mobile robots | APF baseline controller | Reactive, no kerb or shock awareness | Kashish Praveen Jain (E026) |

---

## 3. Paper-by-Paper Analysis

### 3.1 Paper 1: Drone delivery of automated external defibrillators compared with ambulance arrival in real-life suspected out-of-hospital cardiac arrests: a prospective observational study in Sweden (Schierbeck et al. (2023))
* **Full Title:** Drone delivery of automated external defibrillators compared with ambulance arrival in real-life suspected out-of-hospital cardiac arrests: a prospective observational study in Sweden
* **Authors:** Schierbeck S et al.
* **Journal / Venue:** *The Lancet Digital Health, 5(12):e862-e871*, 2023
* **Type:** Recent
* **Verified Active DOI:** [10.1016/S2589-7500(23)00161-9](https://doi.org/10.1016/S2589-7500(23)00161-9)

#### What the paper does
A prospective observational study in Sweden: five AED-equipped drones in two controlled airspaces covering about 200,000 inhabitants were dispatched in addition to standard emergency medical services for suspected out-of-hospital cardiac arrests, and flew autonomously. Flights were excluded for air-traffic non-approval, unfavourable weather, no-delivery zones and darkness. Of 211 alerts (April 2021 to May 2022) a drone was deployed in 72 (34%) and delivered an AED in 58 of those (81%). Where both arrival times were available (n = 55) the drone AED arrived before the ambulance in 37 cases (67%) with a median time benefit of 3 min 14 s. Among these, 18 were true cardiac arrests, an AED was attached in six, two patients were defibrillated by a drone-delivered AED and one survived 30 days. No adverse events occurred.

#### What this project takes from it
The benchmark for how often a delivery device arrives before the ambulance and by how much; the clinical package keeps the 67% and the 3 min 14 s as validation targets only (they feed no computation).

#### Limits for this project
A drone in controlled airspace with flight exclusions; it says nothing about ground vehicles, kerbs or payload shock, and only a third of the alerts led to a deployment.

---

### 3.2 Paper 2: Heart Disease and Stroke Statistics-2023 Update: A Report From the American Heart Association (Tsao et al. (2023))
* **Full Title:** Heart Disease and Stroke Statistics-2023 Update: A Report From the American Heart Association
* **Authors:** Tsao CW et al.
* **Journal / Venue:** *Circulation, 147*, 2023
* **Type:** Recent
* **Verified Active DOI:** [10.1161/CIR.0000000000001123](https://doi.org/10.1161/CIR.0000000000001123)

#### What the paper does
The annual statistical update of the American Heart Association with the National Institutes of Health on heart disease, stroke and cardiovascular risk factors: behaviours and health factors, major clinical heart and circulatory conditions and their outcomes, with additional COVID-19 material and a focus on health equity in the 2023 edition.

#### What this project takes from it
Epidemiological context for why time to defibrillation matters. No number or model parameter is taken from this paper in the present project.

#### Limits for this project
United States statistics; it is a data compendium, not a study of delivery vehicles or of response time.

---

### 3.3 Paper 3: Using machine learning to assess the extent of busy ambulances and its impact on ambulance response times: A retrospective observational study (Naess et al. (2024))
* **Full Title:** Using machine learning to assess the extent of busy ambulances and its impact on ambulance response times: A retrospective observational study
* **Authors:** Naess LE et al.
* **Journal / Venue:** *PLOS ONE, 19*, 2024
* **Type:** Recent
* **Verified Active DOI:** [10.1371/journal.pone.0296308](https://doi.org/10.1371/journal.pone.0296308)

#### What the paper does
A retrospective observational study of medical emergency incidents with ambulance response in Central Norway from 2013 to 2022. Machine learning on data from nearby incidents estimates, for each of 216,787 acute incidents, the probability that a candidate ambulance is busy, and groups of nearby incidents with different busy probabilities are compared. The estimated probability of a busy ambulance was 26.7% overall, 21.6% in rural and 35.0% in urban areas; each 10-percentage-point increase was associated with a delay of 0.60 min (rural 0.81 min, urban 0.30 min). The authors conclude that busy ambulances are common and associated with delayed response.

#### What this project takes from it
The ambulance response-time distribution of the clinical model: a lognormal fitted to the urban median (10 min) and 90th percentile (17.7 min) of the paper's response-time table (all incidents 12.2 and 29.1 min; rural 14.8 and 33.3 min), plus the busy-ambulance slope for sensitivity analysis.

#### Limits for this project
Norwegian data on busy ambulances; the paper is not about road congestion and does not report 15-20 minute urban delays. The premise of the project title therefore rests on a scenario assumption, not on this paper.

---

### 3.4 Paper 4: Sharing the Sidewalk: Observing Delivery Robot Interactions with Pedestrians during a Pilot in Pittsburgh, PA (Weinberg et al. (2023))
* **Full Title:** Sharing the Sidewalk: Observing Delivery Robot Interactions with Pedestrians during a Pilot in Pittsburgh, PA
* **Authors:** Weinberg D et al.
* **Journal / Venue:** *Multimodal Technologies and Interaction, 7*, 2023
* **Type:** Recent
* **Verified Active DOI:** [10.3390/mti7050053](https://doi.org/10.3390/mti7050053)

#### What the paper does
Reports the City of Pittsburgh's pilot of sidewalk delivery robots on public sidewalks: ethnographic observations and intercept interviews on how residents perceived and interacted with the robots. People with limited knowledge crafted stories about the robots' purpose; the robots caused distractions and obstructions for different sidewalk users (including children and dogs); people helped immobilised robots; and potential accessibility issues were identified. The authors contribute recommendations for future pilots and questions for the design of robots in public spaces.

#### What this project takes from it
Qualitative motivation for the crowd and obstacle scenarios and for a conservative, stopping-distance safety filter near pedestrians. No numeric parameter is taken from this paper.

#### Limits for this project
A small-robot commercial-delivery pilot: no speeds, no payload shock and no emergency use case.

---

### 3.5 Paper 5: Predicting survival from out-of-hospital cardiac arrest: A graphic model (Larsen et al. (1993))
* **Full Title:** Predicting survival from out-of-hospital cardiac arrest: A graphic model
* **Authors:** Larsen MP et al.
* **Journal / Venue:** *Annals of Emergency Medicine, 22(11):1652-1658*, 1993
* **Type:** Seminal
* **Verified Active DOI:** [10.1016/S0196-0644(05)81302-2](https://doi.org/10.1016/S0196-0644(05)81302-2)

#### What the paper does
Develops a graphic model (multiple linear regression) of survival from sudden out-of-hospital cardiac arrest as a function of the time intervals to critical prehospital interventions. The data are 1,667 cardiac arrest patients from the King County (Washington) surveillance system who had underlying heart disease, were in ventricular fibrillation and collapsed before EMS arrival. The fitted equation is survival = 67% - 2.3% per minute to CPR - 1.1% per minute to defibrillation - 2.1% per minute to advanced cardiac life support (significant at P < .001). The 67% is the survival if all three interventions occur at collapse, and the three coefficients sum to a decline of 5.5% per minute without treatment. Predicted survival for given EMS response times approximated published observed rates.

#### What this project takes from it
Primary survival model (`aedrover.clinical.survival.LarsenModel`); the coefficients are pinned by unit tests and used mainly for the difference between delivery modes.

#### Limits for this project
A high-survival-likelihood subgroup of a Western cohort, so absolute values are optimistic; linear and clipped at zero, so not valid for long delays; contains no delivery device. Its shock slope (1.1% per minute) is far below the 7-10% per minute rule of thumb quoted in resuscitation guidelines.

---

### 3.6 Paper 6: Real-Time Obstacle Avoidance for Manipulators and Mobile Robots (Khatib (1986))
* **Full Title:** Real-Time Obstacle Avoidance for Manipulators and Mobile Robots
* **Authors:** Khatib O
* **Journal / Venue:** *The International Journal of Robotics Research, 5(1):90-98*, 1986
* **Type:** Seminal
* **Verified Active DOI:** [10.1177/027836498600500106](https://doi.org/10.1177/027836498600500106)

#### What the paper does
Presents a real-time obstacle avoidance approach for manipulators and mobile robots based on the artificial potential field concept. Collision avoidance, traditionally a high-level planning problem, is distributed between levels of control; the method is extended to moving obstacles with a time-varying potential field and is applied to robot arms by controlling motion directly in operational space. It was implemented on a PUMA 560 robot in the COSMOS system with real-time avoidance of moving obstacles using visual sensing.

#### What this project takes from it
Baseline B of the controller benchmark (`aedrover.nav.apf`): attraction toward the path plus repulsion from lidar returns, tracked pedestrians and virtual sidewalk-edge walls within an influence radius.

#### Limits for this project
A reactive local method formulated for manipulators and mobile robots in general; it knows nothing about kerbs, payload shock or vehicle dynamics, which is why the benchmark also includes the dynamic window approach (described in the package as not being trapped by symmetric obstacle forces) and sampling-based control.

---


---

## 4. Cross-Paper Synthesis Matrix

| Evaluation dimension | What the six papers provide | What this project adds |
| :--- | :--- | :--- |
| Delivery-mode evidence | Drone AEDs arrived before the ambulance in 37 of 55 comparable cases in Sweden (Schierbeck et al. 2023); ambulances are often busy and busy ambulances are associated with later arrival (Naess et al. 2024) | A physics-based ground rover with a kerb-climbing and payload-shock evaluation and a survival comparison against the ambulance |
| Survival versus delay | A linear survival model with coefficients per minute of delay (Larsen et al. 1993) | The same model applied to delivery modes, plus the guideline rule of thumb as a model-form sensitivity check |
| Sidewalk interaction | Qualitative observations of distraction, obstruction and accessibility problems (Weinberg et al. 2023) | Seeded crowd and obstacle scenarios and a stopping-distance safety filter shared by all controllers |
| Local navigation | Potential-field obstacle avoidance (Khatib 1986) | Potential-field, dynamic-window, sampling-based (MPPI) and learned (PPO) controllers compared on identical scenarios with paired statistics |
| Epidemiology | Annual US heart-disease and stroke statistics (Tsao et al. 2023) | Used as context only; no number is taken from it |

---

## 5. Methodological Research Gap Formulation

### GAP-1: Kerb crossing and payload shock are unreported
None of the six papers reports kerb climbing or payload shock for a delivery vehicle. In this project's kerb study the minimum climbing speed at a 12 cm kerb is 1.0 m/s (nominal) and 1.0 m/s (optimised), and the peak payload shock at that speed is 2.90 g and 1.93 g against a 3 g budget; 83% of the optimised design's kerb-up (height, friction) cells have a shock-compliant climb window against 44% for the nominal design.

### GAP-2: No ground-rover time-to-first-shock evidence
The drone study (Schierbeck et al. 2023) reports arrival before the ambulance but no ground vehicle is evaluated in the reviewed literature. Here 5 controllers were benchmarked on 2250 seeded sidewalk episodes: the best success rate is 87.6% (PPO), so reliability, not only speed, limits a ground rover; collisions and stalls in crowded and slippery scenes are the main failure modes (see the family table in the implementation guide).

### GAP-3: The delay premise is a scenario, not a sourced fact
The title assumes ambulance delays of 15-20 minutes. The sourced urban response time in Central Norway has a median of 10 min and a 90th percentile of 17.7 min (Naess et al. 2024), a busy-ambulance effect of only 0.3 min per 10 percentage points in urban areas, and no comparable figure exists in the reviewed papers for an Indian city. With the response-time inputs of the results file, the clinical comparison gives +1.3 percentage points of marginal survival and a break-even radius of 584 m; the answer to the research question depends on the local delay distribution.

### GAP-4: Model-form uncertainty in survival versus delay
Larsen et al. attribute 0.011 per minute to the delay to the first shock (and 0.055 per minute to all three delays together), whereas resuscitation guidelines quote 7-10% per minute without CPR. This factor of roughly seven in the slope dominates any single controller difference, so both models are reported and the conclusion is stated for both.

---

## 6. Proposed Architectural Contribution

MDRIIA_GROUP_03 implements a four-wheel independent-suspension rover in MuJoCo with a shock-isolated payload, a measured kerb-climbing envelope, a mechanical co-design that trades wheel size, suspension and isolator against payload shock, five navigation controllers behind one safety filter, and a clinical and dimensionless economic layer whose inputs are separated into sourced values and flagged assumptions.

---

## 7. Literature-Grounded Student Viva Defense Questions

### Student: Kashish Praveen Jain (`E026`), branch `feat/e026-lead-autonomous-navi`
* **Assigned literature domain:** Sidewalk navigation dynamics, pedestrian crowd evasion, dynamic routing through urban choke points, and arrival latency budgets.

1. *Question:* What does Schierbeck et al. (2023) actually show, and how does it limit the claims you can make for a ground rover?
   *Model answer:* It is a prospective observational study of AED drones in two controlled Swedish airspaces, dispatched in addition to standard EMS. Of 211 alerts a drone was deployed in 72, delivered an AED in 58, and in the 55 cases with both arrival times the drone was first in 37 (67%) with a median benefit of 3 min 14 s. It excludes flights for weather, darkness, no-delivery zones and air-traffic non-approval, and says nothing about ground vehicles. We therefore use the 67% and 3 min 14 s only as validation targets for the clinical layer and make no claim that a rover replicates them.
2. *Question:* What do Naess et al. (2024) say about ambulance delays, and why is the 15-20 minute figure in the title not taken from them?
   *Model answer:* They study busy ambulances in Central Norway (216,787 incidents, 2013-2022): the estimated probability of a busy ambulance is 26.7%, and each 10-percentage-point increase is associated with 0.60 min of delay (urban 0.30 min). The urban response time used here has a median of 10 min and a 90th percentile of 17.7 min. The paper is about busy ambulances, not road congestion, and gives no 15-20 minute figure; that number is a scenario assumption of the title and must be varied in the sensitivity analysis.

### Student: Vaishnavi Parashar (`E046`), branch `feat/e046-mujoco-dynamic-chass`
* **Assigned literature domain:** Four-wheel independent suspension, curb-climbing dynamics, shock isolation for biphasic AED pads, and contact friction stability.

1. *Question:* Which coefficients does Larsen et al. (1993) give, and what would be wrong with using 0.046 per minute for the shock term?
   *Model answer:* Survival = 0.67 - 0.023 t_cpr - 0.011 t_defib - 0.021 t_acls with times in minutes from collapse (King County, 1,667 patients with heart disease and witnessed ventricular fibrillation). The three slopes sum to 0.055 per minute without treatment. The shock slope is 0.011; 0.046 is not a coefficient of the model and would overstate the value of a shock-time saving by a factor of 4.2.
2. *Question:* What does Khatib (1986) contribute, and where does your APF baseline differ from a plain potential field?
   *Model answer:* Khatib's paper presents real-time obstacle avoidance based on artificial potential fields, extended to moving obstacles with a time-varying field, and applies it to manipulators and mobile robots. The package's APF baseline follows the concept: attraction toward the path, repulsion from lidar returns and tracked pedestrians inside an influence radius of 2.5 m, plus virtual walls near the sidewalk edges, with an optional kerb-speed overlay. It is deliberately a reactive baseline; the dynamic window approach and MPPI plan against predicted motion and are compared with it on identical seeded scenarios.

