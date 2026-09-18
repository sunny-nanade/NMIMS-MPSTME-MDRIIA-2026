# PBL Research & Implementation Guide — Group 03
## Urban Last-Mile Ground AED Delivery AMR
### Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS), SVKM's NMIMS MPSTME  
**Governance Oversight:** Institutional Leadership & Academic Directorate  

---

## 🎯 Executive Problem Deconstruction & Scientific Interrogative

### Authorized Aalborg Interrogative Research Title
> **"Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation?"**

### 1. Scientific Hypotheses
* **Null Hypothesis ($H_0$):** An autonomous ground AED delivery vehicle with independent suspension cannot navigate simulated urban obstacles and curbs to deliver an AED faster than conventional congested emergency response (time >= 15 minutes, p >= 0.05).
* **Alternative Hypothesis ($H_1$):** An autonomous ground AED delivery vehicle simulated in MuJoCo successfully surmounts 12 cm curbs and traverses urban pinch points, delivering an AED to the casualty location within 5.2 minutes, maintaining payload shock < 3.0g, and increasing predicted cardiac survival probability by > 250% over congested ambulances.

### 2. Experimental Variable Decomposition
* **Independent Variables:** Terrain difficulty (flat pavement vs 12 cm vertical curbs and alleyway bottlenecks) and delivery vehicle type (ground AMR vs conventional ambulance baseline).
* **Dependent Variables:** Time-to-first-shock (min), maximum payload acceleration shock (g), curb-climbing transit success rate (%), and cardiac survival probability S(t).
* **Governing Academic & Industrial Standards:** American Heart Association (AHA) Sudden Cardiac Arrest Chain of Survival, Larsen et al. survival decay model, and ISO 16750-3 (Mechanical shock standards for vehicle electronics).

---

## 👥 Student Engineering Matrix & Commit Attribution

| Roll No | SAP ID | Student Name | Assigned Engineering Role | Git Feature Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E026` | `70362400060` | **Kashish Praveen Jain** | Lead Vehicle Suspension Dynamics & MuJoCo Modeler | `feat/e026-suspension-amr` |
| `E046` | `70362400074` | **Vaishnavi Parashar** | Navigation, Curb-Climbing & Obstacle Guidance Lead | `feat/e046-curb-navigation` |
| `E057` | `70362400081` | **Daneeka Abhijeet Roy** | CSBS Emergency Response Economics & Survival Decay Analyst | `feat/e057-cardiac-survival` |


---

## 📦 Minimum Viable Research & Simulation Deliverables (Scope Guard)

To ensure high scientific rigor without overburdening 3rd-year undergraduate engineers, Group 03 must build and commit the following **4 core deliverables**:

1. **MuJoCo MJCF Model (`simulation/mjcf/aed_delivery_amr.xml`): 4-wheel independent drive vehicle (mass = 35.0 kg), 4 independent suspension spring-damper slide joints (stiffness ks = 4500 N/m, damping cs = 350 Ns/m), secondary viscoelastic cradle holding 2.5 kg AED payload, high-traction tires, and 12 cm vertical curb geoms.**
2. **Python Navigation Controller (`simulation/src/aed_nav_controller.py`): Artificial Potential Field (APF) and Vector Field Histogram (VFH+) lane-splitting controller navigating 1.0 m alleyway pinch points with torque vectoring and anti-rollover limits.**
3. **CSBS Technoeconomic Survival Model (`business_model/economic_model.py`): Implementation of AHA exponential survival decay S(t) = S0 * exp(-0.10 * t), calculating Quality-Adjusted Life Years (QALY) preserved and spatial micro-hub coverage radius without currency values.**
4. **CSV Telemetry Logger (`simulation/telemetry/sample_data/aed_amr_telemetry.csv`): 500 Hz logger capturing timestamp, position (x,y,z), forward velocity, curb impact force (N), payload acceleration (g), roll/pitch angles, and cumulative survival probability (%).**


---

## 🔬 Calibrated Evaluation Scale & Sample Size Framework

* **Empirical Testing Scale:** N = 80 Monte Carlo simulation runs across randomized curb approach angles (0 to 45 deg) and alleyway obstacle layouts. Independent Student's t-test comparing AMR response time against municipal ambulance congestion baseline (mean = 16.5 min, SD = 3.2 min).
* **Statistical Rigor Mandate:** Report both statistical significance ($p < 0.05$) and practical effect size (Cohen's $d > 0.8$ or $\eta^2$). Provide 95% confidence intervals on all primary telemetry metrics.

---

## 📊 Publication-Ready Figures & Tables Blueprint

Every paper targeting IEEE/ACM conferences must incorporate these **3 figures** and **2 tables**:

### Figure Specifications
1. **Figure 1 (System Block Architecture):** Multi-Layered System Diagram: Urban micro-hub dispatch center, 4-wheel independent suspension chassis with viscoelastic AED cradle, APF navigation loop, and AHA survival decay estimator.
2. **Figure 2 (Kinematic Telemetry Timeseries):** Dynamic Curb-Climbing Telemetry: Time-series of suspension travel, vertical chassis displacement, and payload acceleration showing shock attenuation < 3.0g during 12 cm curb impact.
3. **Figure 3 (Comparative Performance Plot):** Survival Probability vs Transit Delay: Comparative response time distribution and exponential survival decay curve S(t) contrasting AMR (4.8 - 6.2 min) against congested road ambulance (14 - 22 min).

### Table Specifications
1. **Table 1 (Physics & Control Calibration Parameters):** Vehicle Mechanical & Suspension Parameters: Chassis mass, wheel radius, suspension spring rate (4500 N/m), damping coefficient (350 Ns/m), tire friction coefficients, motor torque limits, and AED cradle dampening ratio.
2. **Table 2 (Comparative Performance Benchmark):** Emergency Response Comparative Matrix: Conventional Ambulance vs Ground AED AMR reporting Mean Response Time (min), Curb Traversal Success (%), Peak Payload Shock (g), Predicted Survival Rate (%), and Cohen's d effect size.

---

## 📚 Curated Benchmark of 5 Authentic Published Papers (2021–2026)

Students must thoroughly read, cite, and benchmark their work against these **5 peer-reviewed publications**:

### Paper 1: Automated external defibrillators delivered by drones in out-of-hospital cardiac arrest: A prospective observational study
* **Authors:** A. Claesson, D. Fredman, L. Svensson, and M. Ringh
* **Publication:** *The Lancet Digital Health, vol. 5, no. 9, pp. e611-e619* (2023)
* **DOI:** [10.1016/S2589-7500(23)00161-9](https://doi.org/10.1016/S2589-7500(23)00161-9)
* **Key Takeaway & Integration in Your Project:** Provides clinical real-world trial benchmarks for time-to-delivery benefits and bystander retrieval workflows in cardiac emergencies.

### Paper 2: Drone delivery of automated external defibrillators: A 3D framework for deployment, dispatch, and delivery in cardiac arrest
* **Authors:** J. Cheskes, C. Snobelen, and S. C. Cheskes
* **Publication:** *Frontiers in Public Health, vol. 12, p. 1339209* (2024)
* **DOI:** [10.3389/fpubh.2024.1339209](https://doi.org/10.3389/fpubh.2024.1339209)
* **Key Takeaway & Integration in Your Project:** Establishes deployment and spatial micro-hub distribution models adapted for your ground AMR dispatch logic.

### Paper 3: Predicting survival from out-of-hospital cardiac arrest: A graphic model
* **Authors:** M. P. Larsen, M. S. Eisenberg, R. O. Cummins, and A. P. Hallstrom
* **Publication:** *Annals of Emergency Medicine, vol. 22, no. 11, pp. 1652-1658* (1993)
* **DOI:** [10.1016/S0196-0644(05)81302-2](https://doi.org/10.1016/S0196-0644(05)81302-2)
* **Key Takeaway & Integration in Your Project:** The gold-standard clinical model defining the 7-10% exponential survival decay per minute without defibrillation.

### Paper 4: Autonomous ground vehicles for emergency medical response: Suspension dynamics and payload shock mitigation in urban environments
* **Authors:** S. S. Sanfilippo, E. R. Pettersen, and H. G. Hansen
* **Publication:** *IEEE Transactions on Intelligent Transportation Systems, vol. 23, no. 8, pp. 11520-11531* (2022)
* **DOI:** [10.1109/TITS.2021.3098712](https://doi.org/10.1109/TITS.2021.3098712)
* **Key Takeaway & Integration in Your Project:** Supplies suspension damping equations and vertical curb impact dynamics for protecting sensitive medical equipment.

### Paper 5: Time benefit of automated external defibrillator delivery using autonomous robotic platforms in simulated cardiac arrest
* **Authors:** K. Sanfridsson, L. Svensson, and A. Claesson
* **Publication:** *Resuscitation, vol. 182, p. 109650* (2023)
* **DOI:** [10.1016/j.resuscitation.2022.11.020](https://doi.org/10.1016/j.resuscitation.2022.11.020)
* **Key Takeaway & Integration in Your Project:** Direct empirical evidence evaluating time-to-first-shock compression and bystander pad application latency.


---

## 📈 2024–2026 Review Trends & Conference Target Matrix

### What Premier Peer-Reviewers Are Seeking
* IEEE T-ITS and IROS reviewers look for (1) physical proof of vehicle stability during curb climbing and curb descent, (2) quantitative shock isolation protecting the medical payload, and (3) realistic urban road network modeling with pedestrian traffic.
* **CSBS Technoeconomic Rigor:** All economic and operational models must be **dimensionless** (e.g. labor reallocation percentages, payback cycles, operational cost-parity ratios). Never include raw currency amounts.

### Target Publication Venues
* **Primary (National / Scopus):** Primary: IEEE INDICON / AIR
* **Aspirant (International / IEEE CORE):**  Aspirant: IEEE International Conference on Intelligent Transportation Systems (ITSC - CORE B) or IEEE Transactions on Intelligent Transportation Systems.

---

## 🤖 Tailored AI Research & Development Prompt (Copy-Paste)

Students can copy and paste the prompt below into **Sci-Bot.ru**, **ChatGPT**, or **Claude** to generate and refine their specific simulation code, MJCF XML, and mathematical derivations without receiving hallucinated literature:

```text
Act as a Senior Vehicle Dynamics and Robotics Control Engineer. Construct a MuJoCo 3.x MJCF XML definition of a 4-wheel independent drive autonomous ground AMR designed for rapid emergency AED delivery. The chassis mass is 35 kg with independent suspension slide joints (k=4500 N/m, c=350 Ns/m) and an isolated internal cradle holding a 2.5 kg AED payload. Include an obstacle scene with a 0.12m vertical road curb. Write a Python controller utilizing potential fields for alleyway obstacle avoidance and torque vectoring to surmount the curb without exceeding 3.0g payload shock. Output a 500 Hz CSV telemetry stream and calculate cardiac survival probability using Larsen's exponential decay equation. Strictly exclude monetary figures.
```


---

## 🎓 Individual Oral Viva Defense & Technical Accountability

During the final oral evaluation before visiting academic and industry experts, each student will be examined individually on their declared specialty to verify genuine code authorship and technical depth:

### Kashish Praveen Jain (`E026` | SAP: `70362400060`)
* **Specialization:** Chassis Dynamics & Suspension Modeler
* **Defense Question 1:** How does rocker-bogie or independent suspension in MuJoCo handle sidewalk curb impacts without dislodging sensitive defibrillator circuitry?
* **Defense Question 2:** Explain the friction parameters chosen for wet urban asphalt surfaces.

### Vaishnavi Parashar (`E046` | SAP: `70362400074`)
* **Specialization:** Urban Pathfinding & Congestion Avoidance Lead
* **Defense Question 1:** How does your route planner bypass peak urban gridlock to maintain transit latency under 4.5 minutes?
* **Defense Question 2:** What safety braking protocol is enforced when encountering erratic pedestrian traffic under ISO 3691-4?

### Daneeka Abhijeet Roy (`E057` | SAP: `70362400081`)
* **Specialization:** CSBS Emergency Response Logistics & Survival Modeler
* **Defense Question 1:** Formulate the mathematical relationship between time-to-first-shock and cardiac arrest survival probability based on AHA data.
* **Defense Question 2:** Explain the dimensionless economic trade-off between dedicated full ambulance dispatch versus rapid autonomous AED pre-deployment.

