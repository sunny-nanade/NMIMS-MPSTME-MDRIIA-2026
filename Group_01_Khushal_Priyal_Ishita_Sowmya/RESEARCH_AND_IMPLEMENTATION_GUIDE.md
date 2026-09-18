# Research and Implementation Guide — Group 01
## Autonomous Mobile Robot for Critical Medicine Delivery in Intensive Care Units

---

## 1. Problem Formulation and Interrogative Research Title

### Authorized Aalborg Interrogative Research Statement
> "To what extent can an autonomous mobile medicine-delivery robot (simulated in MuJoCo with dynamic obstacle avoidance) reduce ICU nurses' non-patient-facing logistics transit time and optimize labor reallocation, where clinical studies document nurses spending approximately 28% of their shift on supply retrieval?"

### 1.1 Scientific Hypotheses
* **Null Hypothesis (H0):** The introduction of an autonomous mobile medicine-delivery robot operating in a hospital corridor simulation does not produce a statistically significant reduction in non-patient-facing supply transit time compared to manual delivery (p >= 0.05), or violates liquid payload anti-slosh thresholds (lateral acceleration > 0.40 m/s^2).
* **Alternative Hypothesis (H1):** An autonomous mobile medicine-delivery robot operating under dynamic window trajectory control with jerk-limited acceleration profiles reduces logistics transit time by >= 65% (p < 0.001) while maintaining liquid medicine lateral acceleration below 0.40 m/s^2 across >= 99% of transit duration.

### 1.2 Experimental Variable Decomposition
* **Independent Variables:**
  * Navigation mode: Manual clinical walking retrieval vs autonomous AMR transit.
  * Dynamic pedestrian density: 3 to 8 moving obstacles across a standard 2.2m hospital corridor.
  * Corridor floor surface friction coefficient: mu in [0.55, 0.85].
* **Dependent Variables:**
  * Mission transit latency: Total time elapsed from dispensary dispatch to ICU bedside docking (seconds).
  * Payload stability index: Peak lateral acceleration a_lat = |v * omega| (m/s^2) and total kinematic jerk ||j|| (m/s^3).
  * Daily direct bedside care hours reclaimed: Delta_bedside (hours/shift and percentage expansion).
* **Governing International Standards:**
  * ISO 13482:2014: Robots and robotic devices — Safety requirements for personal care robots.
  * ISO 3691-4:2023: Driverless industrial trucks and autonomous mobile robots (AMRs).
  * Facility Guidelines Institute (FGI) / AIA Guidelines for Design and Construction of Hospitals.

---

## 2. Theoretical Mechanics and Physical System Architecture

### 2.1 Differential-Drive Mobile Robot Kinematics
The platform is modeled as a non-holonomic ground vehicle operating in a planar configuration space:
```
q(t) = [x(t), y(t), theta(t)]^T in R^2 x (-pi, pi]
```
where (x, y) represents the midpoint of the drive wheel axle and theta represents the heading angle relative to the global X-axis.

The generalized control input vector is:
```
u(t) = [v(t), omega(t)]^T
```
where v(t) in [0, v_max] is the linear forward velocity and omega(t) in [-omega_max, omega_max] is the yaw rate.

The continuous kinematic equations of motion under pure rolling and zero lateral slip are:
```
dx/dt = v(t) * cos(theta(t))
dy/dt = v(t) * sin(theta(t))
dtheta/dt = omega(t)
```
subject to the non-holonomic constraint:
```
-(dx/dt) * sin(theta(t)) + (dy/dt) * cos(theta(t)) = 0
```

### 2.2 Actuator-Level Wheel Transformations
Let r denote the drive wheel radius (r = 0.08 m) and b denote the track gauge (b = 0.42 m). The forward transformation mapping independent wheel angular velocities (phi_dot_R, phi_dot_L) to generalized body velocities is:
```
v = (r / 2) * (phi_dot_R + phi_dot_L)
omega = (r / b) * (phi_dot_R - phi_dot_L)
```
The inverse transformation for actuator velocity setpoints is:
```
phi_dot_R = (v / r) + (b * omega) / (2 * r)
phi_dot_L = (v / r) - (b * omega) / (2 * r)
```

### 2.3 Strict Heading Error Normalization on (-pi, pi]
Given target waypoint p_g = [x_g, y_g]^T, the desired bearing angle is:
```
theta_d = atan2(y_g - y, x_g - x)
```
To eliminate branch-cut discontinuities when crossing +/- pi, the heading error e_theta must be normalized using the four-quadrant arctangent formulation:
```
e_theta = atan2(sin(theta_d - theta), cos(theta_d - theta)) in (-pi, pi]
```

### 2.4 Liquid Payload Anti-Slosh and Dynamic Invariant Constraints
During the transport of reconstituted intravenous medications, blood bags, and liquid infusions, high lateral acceleration causes liquid sloshing, risking protein denaturing or container tipping. The motion planner must enforce:

1. **Centripetal Lateral Acceleration Bound:**
   ```
   a_lat = |v * omega| <= a_lat_crit = 0.40 m/s^2
   ```
   Consequently, linear velocity must be dynamically throttled during turns:
   ```
   v <= min(v_max, a_lat_crit / (|omega| + 1e-6))
   ```

2. **Longitudinal Acceleration Bound:**
   ```
   |dv/dt| <= a_long_crit = 0.50 m/s^2
   ```

3. **Total Kinematic Jerk Bound:**
   ```
   ||j(t)||_2 = sqrt((d^2 v / dt^2 - v * omega^2)^2 + (2 * (dv/dt) * omega + v * (domega/dt))^2) <= 1.20 m/s^3
   ```

### 2.5 Clinical Corridor Geometry (FGI Hospital Building Standard)
* Corridor clear width: W_c = 2.20 m (accommodates bidirectional transport).
* Wall boundary height: H_c = 2.80 m.
* Doorway clear opening: W_d = 1.20 m.
* Robot footprint: Length L = 0.65 m, Width W = 0.50 m, Height H = 0.85 m.
* Center of mass height: z_CoM <= 0.28 m above ground plane.

---

## 3. Dynamic Obstacle Avoidance and Trajectory Optimization

### 3.1 Dynamic Window Approach (DWA) Formulation
The trajectory generator searches over the admissible velocity space V_d:
```
V_d = {(v, omega) | v in [v_k - a_long * dt, v_k + a_long * dt] intersect [0, v_max],
                   omega in [omega_k - alpha * dt, omega_k + alpha * dt] intersect [-omega_max, omega_max]}
```
Candidate trajectories are evaluated over forward simulation horizon tau = 2.5 s via the objective function:
```
G(v, omega) = alpha * heading(v, omega) + beta * dist(v, omega) + gamma * velocity(v, omega) - lambda * P_slosh(v, omega)
```
where the anti-slosh penalty is defined as:
```
P_slosh(v, omega) = max(0, |v * omega| - 0.40)^2 + max(0, ||j|| - 1.20)^2
```
Setting lambda >> max(alpha, beta, gamma) guarantees that the robot prioritizes medicine stability over aggressive turning maneuvers.

---

## 4. Computer Science and Business Systems (CSBS) Technoeconomic Model

All financial formulations are strictly dimensionless. No raw currency symbols or fiat units are permitted.

### 4.1 Nursing Time-Motion Baseline
Let T_shift denote the duration of a standard clinical nursing shift:
```
T_shift = 12.0 hours
```
Clinical studies (Hendrich et al., replicated by Michel et al., 2021) establish that ICU nurses spend approximately 28% of their shift on non-patient-facing supply and medication retrieval:
```
eta_base = 0.28
H_transit_base = eta_base * T_shift = 0.28 * 12.0 = 3.36 hours/nurse-shift
```

Let psi represent the fraction of pharmaceutical deliveries eligible for autonomous transport (psi = 0.80, excluding scheduled narcotics requiring manual dual-key custody). Let A_AMR represent robotic system availability (A_AMR = 0.95).

The net reclaimed direct bedside care hours per nurse per shift is:
```
H_reclaimed = psi * A_AMR * H_transit_base = 0.80 * 0.95 * 3.36 = 2.5536 hours/nurse-shift
```

The residual non-patient-facing transit burden per nurse is:
```
H_transit_post = H_transit_base - H_reclaimed = 3.36 - 2.5536 = 0.8064 hours/nurse-shift
```

### 4.2 Direct Bedside Care Expansion Factor
Assuming baseline direct patient care consumes approximately 50% of the shift (6.00 hours):
```
Delta_bedside = H_reclaimed / 6.00 = 2.5536 / 6.00 = +42.56% expansion in bedside clinical focus
```

### 4.3 Full-Time Equivalent (FTE) Capacity Release
For an intensive care unit staffed by N_nurses = 10 active nurses per shift across two daily 12-hour shifts:
```
FTE_released = N_nurses * (H_reclaimed / T_shift) = 10 * (2.5536 / 12.0) = 2.128 FTE
```
Deploying the autonomous robot releases more than 2 full-time registered nurses from transport labor into acute bedside intervention.

### 4.4 Operational Cost Parity Ratio (kappa)
The dimensionless operational cost parity ratio is defined as:
```
kappa = (c_R * tau_R) / (c_N * tau_N)
```
where:
* c_N: Unit-time compensation index of an ICU registered nurse.
* c_R: Comprehensive unit-time operational, maintenance, and depreciation cost index of the robot platform.
* tau_N: Average cycle time for manual retrieval by a human nurse.
* tau_R: Average cycle time for the AMR under anti-slosh velocity constraints.

Target engineering benchmark for adoption: kappa <= 0.35 (demonstrating at least 65% operational efficiency gain).

### 4.5 Dimensionless Capital Payback Horizon (P_m)
Let M_eq denote initial capital expenditure expressed as a multiple of an annual nurse compensation unit (M_eq = 1.80). Let mu denote the annual maintenance fraction (mu = 0.12). The payback horizon in months is:
```
P_m = (12 * M_eq) / (FTE_released * (1 - mu)) = (12 * 1.80) / (2.128 * 0.88) = 11.53 months
```

---

## 5. Empirical Hypothesis Testing and Statistical Protocol

### 5.1 Experimental Design (N = 60 Monte Carlo Runs)
To evaluate the system under realistic clinical variability, students must execute N = 60 independent trials in MuJoCo:
1. Dynamic pedestrian agents: K in [3, 8] pedestrians with crossing velocities drawn from:
   ```
   v_ped ~ N(1.10, 0.25^2) m/s (clipped to [0.60, 1.80] m/s)
   ```
2. Floor dry friction coefficient: mu_surface ~ U(0.55, 0.85).
3. Payload fluid mass: m_payload ~ U(0.10, 0.50) kg.

### 5.2 Welch's Two-Sample t-Test
Because autonomous navigation and human manual transit exhibit unequal variances, Welch's t-test is mandatory:
```
t = (X_bar_manual - X_bar_AMR) / sqrt((s_manual^2 / N1) + (s_AMR^2 / N2))
```
where N1 = N2 = 60.

Effective degrees of freedom (nu) via the Welch-Satterthwaite equation:
```
nu = ((s_manual^2 / N1) + (s_AMR^2 / N2))^2 / [ ((s_manual^2 / N1)^2 / (N1 - 1)) + ((s_AMR^2 / N2)^2 / (N2 - 1)) ]
```

### 5.3 Effect Size Metric
Compute Cohen's d to quantify operational effect magnitude:
```
s_pooled = sqrt(((N1 - 1) * s_manual^2 + (N2 - 1) * s_AMR^2) / (N1 + N2 - 2))
d = |X_bar_manual - X_bar_AMR| / s_pooled
```
Benchmark: d >= 1.20 (denoting very large operational effect).

---

## 6. Publication-Ready Figures and Tables Blueprint

Every conference submission must include the following 3 figures and 2 tables:

### Figure 1: System Block Architecture
* Block 1: MuJoCo Multi-Body Physical Plant (Chassis mass, wheel drive joints, caster contacts, liquid payload).
* Block 2: Perception & Rangefinder Array (Forward ray, +/- 25 degree angled rays, obstacle distance estimation).
* Block 3: Motion Planner & Anti-Slosh Governor (DWA local planner, heading normalizer, lateral acceleration clamp).
* Block 4: Telemetry Logger & CSBS Technoeconomic Reallocation Engine.

### Figure 2: Kinematic Telemetry Time-Series
* Subplot A: Linear velocity v(t) (m/s) and angular velocity omega(t) (rad/s) across a 15-second delivery run.
* Subplot B: Measured lateral acceleration a_lat(t) compared against the clinical threshold a_lat_crit = 0.40 m/s^2.
* Subplot C: Total jerk ||j(t)||_2 (m/s^3) compared against the threshold j_crit = 1.20 m/s^3.

### Figure 3: Comparative Mission Performance Boxplot
* Boxplot showing delivery cycle duration across N = 60 runs: Manual walking courier vs Autonomous AMR.
* Secondary axis showing direct patient-facing bedside care hours reclaimed per shift.

### Table 1: Physical Simulation Calibration Parameters
* Mobile base mass: 22.0 kg.
* Payload compartment mass: 6.0 kg.
* Wheel radius r: 0.08 m.
* Wheelbase gauge b: 0.42 m.
* Center of mass height: 0.24 m.
* Tire-vinyl static friction: 0.80.
* Tire-vinyl dynamic friction: 0.005.
* Time step dt: 0.002 s (Newton solver, 50 iterations).

### Table 2: Benchmark Performance Comparison
* Columns: Metric, Manual Nurse Baseline, Autonomous AMR, Relative Improvement, p-value (Welch's t-test).
* Rows: Mean Transit Latency (s), Transit Time Standard Deviation (s), Peak Lateral Acceleration (m/s^2), Daily Reclaimed Bedside Hours (h), Operational Cost Parity (kappa).

---

## 7. Curated Benchmark of 5 Authentic Published Papers (2020–2026)

Students must cite and benchmark their findings against these 5 verified peer-reviewed articles. For an exhaustive, paper-by-paper comparative matrix, mathematical formula extractions, research gap analyses, and individual student literature viva defense responsibilities, refer directly to the dedicated dossier:
`docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md`.

### Paper 1: Design and Performance Evaluation of a Modular Mobile Robot for Autonomous Hospital Logistics
* **Authors:** Neri Niccolo Dei, Simona Gandah, Giorgia Spreafico, Andrea Firrincieli, Gastone Ciuti, et al.
* **Publication:** *IEEE Transactions on Automation Science and Engineering*, vol. 23, pp. 7748–7763 (2026)
* **DOI:** [10.1109/TASE.2026.3674356](https://doi.org/10.1109/TASE.2026.3674356)
* **Takeaway & Benchmark Integration:** Introduces the HOSBOT modular healthcare delivery platform and validates navigation through narrow hospital doorways using virtual obstacle space mapping.

### Paper 2: Navigation benchmarking for autonomous mobile robots in hospital environment
* **Authors:** C. Rondoni, M. Antonini, F. Cordella, and L. Zollo
* **Publication:** *Scientific Reports (Nature Portfolio)*, vol. 14, art. no. 18921 (2024)
* **DOI:** [10.1038/s41598-024-69040-z](https://doi.org/10.1038/s41598-024-69040-z)
* **Takeaway & Benchmark Integration:** Provides quantitative navigation performance metrics (path smoothness, collision clearances, and travel times) in actual hospital wards to validate simulation fidelity.

### Paper 3: The Multi-Trip Autonomous Mobile Robot Scheduling Problem with Time Windows in a Stochastic Environment at Smart Hospitals
* **Authors:** Lulu Cheng, Ning Zhao, Kan Wu, and Zhibin Chen
* **Publication:** *Applied Sciences*, vol. 13, no. 17, art. no. 9879 (2023)
* **DOI:** [10.3390/app13179879](https://doi.org/10.3390/app13179879)
* **Takeaway & Benchmark Integration:** Formulates mixed-integer programming for hospital AMR dispatch under stochastic travel times and delivery time windows, directly informing the CSBS dispatch queueing model.

### Paper 4: Optimal operating-speed-dependent motion profiles to reduce liquid slosh
* **Authors:** Y. Terashima, M. Suzuki, and K. Yano
* **Publication:** *Robotics*, vol. 9, no. 1, art. no. 18 (2020)
* **DOI:** [10.3390/robotics9010018](https://doi.org/10.3390/robotics9010018)
* **Takeaway & Benchmark Integration:** Establishes acceleration and jerk thresholding laws for preventing liquid slosh in moving robotic platforms, providing the mathematical basis for the lateral acceleration constraint a_lat <= 0.40 m/s^2.

### Paper 5: How do nurses spend their time? A time and motion analysis of nursing activities in an internal medicine unit
* **Authors:** P. Michel, C. Quenon, A. Djihoud, S. Tricaud-Vialle, and R. de Sarasqueta
* **Publication:** *Journal of Advanced Nursing*, vol. 77, no. 11, pp. 4459–4470 (2021)
* **DOI:** [10.1111/jan.14935](https://doi.org/10.1111/jan.14935)
* **Takeaway & Benchmark Integration:** Supplies empirical clinical time-and-motion data documenting that less than one-third of nursing work is direct patient care, providing the real-world baseline for the 28% logistics transit parameter.

---

## 8. Target Academic Conferences and Review Trends

### Primary Target (National Tier - Scopus Indexed)
* **Conference:** Conference on Advances in Robotics (AIR) / IEEE INDICON
* **Track:** Service Robotics / Healthcare Automation
* **Reviewer Focus:** Clear mathematical problem definition, physical contact mechanics in simulation, and demonstrated safety constraint enforcement under ISO 13482.

### Secondary Target (Premier International Tier - CORE Ranked)
* **Conference:** IEEE International Conference on Automation Science and Engineering (IEEE CASE - CORE B) / IEEE/RSJ IROS (CORE A)
* **Track:** Automation in Healthcare and Life Sciences
* **Reviewer Focus:** Rigorous statistical evaluation (N >= 50 Monte Carlo trials), validation against real-world clinical benchmarks, and coupling of rigid-body mechanics with operational workflow analysis.

---

## 9. Individual Student Task Breakdown and Oral Viva Defense Protocol

To ensure individual accountability and ABET Student Outcome satisfaction, each student has a dedicated technical domain, git branch responsibility, and specific viva questions:

### 9.1 Khushal Asnani (`E006` | SAP ID: `70362400061`)
* **Declared Role:** Lead Robotics Systems Architect & MuJoCo Modeler
* **Technical Boundary:** Design and validate the physical MJCF model, link inertial properties, contact friction parameters, caster ball dynamics, and FGI-compliant corridor dimensions.
* **Assigned Git Branch:** `feature/e006-amr-chassis`
* **Deliverable Files:**
  * `models/icu_medicine_amr.xml`: Complete MJCF multi-body XML model.
  * `scripts/verify_model_physics.py`: Verification script asserting static load balance and contact stability.
* **Oral Viva Defense Questions:**
  1. "In your MuJoCo model, you defined the contact friction between the rubber drive wheels and the vinyl floor using the `friction` attribute in the `<geom>` tag. How does MuJoCo's elliptic friction cone formulation handle the transition between static sticking and dynamic slipping? If the inertia matrix M(q) becomes poorly conditioned due to an improperly specified payload inertia tensor, what numerical instability occurs in the integrator, and how do `solref` and `solimp` prevent constraint divergence?"
  2. "Prove why a differential-drive robot subject to the non-holonomic constraint -x_dot * sin(theta) + y_dot * cos(theta) = 0 cannot be stabilized to an arbitrary posture [x*, y*, theta*]^T using a continuous, time-invariant, pure-state feedback control law u = f(q). Relate your proof to Brockett's Necessary Condition."

### 9.2 Priyal Kaushal Deputy (`E016` | SAP ID: `70362400041`)
* **Declared Role:** Autonomous Navigation & Obstacle Avoidance Specialist
* **Technical Boundary:** Implement the local trajectory planner, Dynamic Window Approach (DWA) with anti-slosh penalty, heading error normalization on (-pi, pi], and dynamic pedestrian evasion.
* **Assigned Git Branch:** `feature/e016-navigation-planner`
* **Deliverable Files:**
  * `src/icu_amr_controller.py`: Closed-loop controller incorporating unicycle kinematics and anti-slosh velocity limiting.
  * `src/test_heading_boundary.py`: Unit test verifying that heading error wraps smoothly across +/- pi without sign oscillation.
* **Oral Viva Defense Questions:**
  1. "Explain the mathematical failure mode of a naive proportional steering controller omega = k_p * (theta_d - theta) when an obstacle forces the robot's heading across the branch cut at +/- pi. Derive the Lyapunov function V(e_theta) = 1 - cos(e_theta) and prove that under your normalized formulation e_theta = atan2(sin(theta_d - theta), cos(theta_d - theta)), the derivative V_dot is negative semi-definite."
  2. "In your Dynamic Window Approach implementation, how do you mathematically guarantee that the admissible velocity space guarantees collision avoidance with a pedestrian walking at 1.40 m/s across the 2.20 m corridor? Specifically, how do you couple the braking deceleration limit with the maximum jerk constraint ||j|| <= 1.20 m/s^3 so that emergency stopping does not tip the liquid medicine vials?"

### 9.3 Ishita Ranjan (`E054` | SAP ID: `70362400038`)
* **Declared Role:** CSBS Healthcare Systems & Time-Motion Workflow Analyst
* **Technical Boundary:** Formulate the clinical workflow model, transit hour reduction equations, dimensionless operational parity ratio kappa, and capital payback horizon.
* **Assigned Git Branch:** `feature/e054-csbs-workflow`
* **Deliverable Files:**
  * `analytics/icu_labor_roi.py`: Computational implementation of the dimensionless technoeconomic model.
  * `analytics/sensitivity_analysis.py`: Sensitivity script analyzing variations in kappa and payback horizon across fleet sizes.
* **Oral Viva Defense Questions:**
  1. "In your dimensionless formulation, the operational cost parity ratio is defined as kappa = (c_R * tau_R) / (c_N * tau_N). Suppose that to enforce the anti-slosh constraint a_lat <= 0.40 m/s^2 around sharp 90-degree corners, the robot must slow down such that tau_R = 2.4 * tau_N. Derive the critical unit-cost ratio (c_R / c_N)_crit above which the robotic delivery system ceases to be economically viable."
  2. "If stat medicine delivery requests arrive at the central dispensary following a non-homogeneous Poisson process lambda(t) with peak bursts during morning rounds (08:00 - 10:00), what occurs to nurse waiting time and bedside hours reclaimed if the fleet size is fixed at C = 1 AMR? Using Little's Law (L = lambda * W), explain how dispatch queuing delay impacts the effective time reclaimed."

### 9.4 Sowmya Satish (`E060` | SAP ID: `70362400055`)
* **Declared Role:** Telemetry, Quality Assurance & Empirical Validation Lead
* **Technical Boundary:** Design the 50 Hz real-time telemetry logging pipeline, execute the N = 60 Monte Carlo batch simulations, and perform statistical hypothesis testing (Welch's t-test and Cohen's d).
* **Assigned Git Branch:** `feature/e060-validation-qa`
* **Deliverable Files:**
  * `src/telemetry_logger.py`: High-frequency CSV logger recording timestamps, coordinates, velocities, accelerations, and jerk.
  * `analytics/hypothesis_testing.py`: Script computing Welch's t-statistic, degrees of freedom, p-value, and Cohen's d across N = 60 runs.
* **Oral Viva Defense Questions:**
  1. "When sampling the robot's kinematic acceleration and jerk at 50 Hz from MuJoCo state vectors, high-frequency discretization noise and contact impulses create artificial spikes in acceleration. What discrete numerical differentiation filter (e.g., Savitzky-Golay FIR filter vs causal low-pass Butterworth filter) did you implement, and how did you verify that your filter did not introduce a phase lag that masks true anti-slosh limit violations?"
  2. "Why is Welch's t-test fundamentally required over Student's standard two-sample t-test when comparing transit times between human nurses and the AMR? In your N = 60 dataset, if the AMR transit time distribution exhibits positive skewness due to obstacle deadlocks, why does the Central Limit Theorem allow you to apply Welch's formulation, and what non-parametric test must be deployed if N drops below 30?"

---

## 10. AI Prompt for Guided Student Development

Students should copy and use this prompt in technical AI tools (such as Claude, ChatGPT, or `https://sci-bot.ru/`) to assist in developing their code modules without receiving hallucinated literature or generic filler:

```text
I am an undergraduate engineering student working on an autonomous mobile robot (AMR) for critical medicine delivery in hospital ICUs using MuJoCo physics and Python.

My specific role in this group project is: [Insert your role: e.g. E006 Physical Modeling / E016 Navigation Controller / E054 CSBS Economics / E060 Telemetry and Testing].

Project Constraints:
1. Physical Platform: Differential-drive mobile base (wheel radius r = 0.08m, track gauge b = 0.42m, base mass = 22kg).
2. Environment: Hospital corridor of clear width 2.20m conforming to FGI healthcare facility standards, with dynamic pedestrian obstacles crossing at 0.60 to 1.80 m/s.
3. Liquid Anti-Slosh Limits: Centripetal lateral acceleration must satisfy a_lat = |v * omega| <= 0.40 m/s^2, and total jerk ||j|| <= 1.20 m/s^3.
4. Mathematical Rigor: All heading errors must be normalized strictly on (-pi, pi] using atan2(sin(delta_theta), cos(delta_theta)).
5. Business Formulation: CSBS technoeconomic analysis must be completely dimensionless using operational cost parity ratio kappa and payback horizon in months. Absolutely NO raw currency symbols or fiat monetary denominations.
6. Statistical Standard: N = 60 Monte Carlo simulation runs evaluated using Welch's two-sample t-test and Cohen's d effect size.

Please help me implement [Insert the specific component you are coding: e.g., the DWA trajectory evaluator function / the MuJoCo MJCF XML definition / the Welch t-test statistical pipeline].
Provide modular, production-grade Python/XML code with clear mathematical annotations. Do not generate fake citations or placeholder mock functions. Guide my implementation step by step.
```
