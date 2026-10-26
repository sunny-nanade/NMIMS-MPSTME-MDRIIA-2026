# Research Paper Manuscript Blueprint (4-Page IEEE Format)

**Title:** Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation?

**Authors:** Kashish Praveen Jain (E026), Vaishnavi Parashar (E046)

**Affiliation:** SVKM's NMIMS MPSTME, Mumbai; B.Tech CSBS, Semester VI, MDRIIA (702CO0E012)

---

## Abstract
We simulate a four-wheel, independently suspended sidewalk rover that carries a 4 kg automated external defibrillator (AED) in MuJoCo and ask whether it can deliver the device before an ambulance. A differential-evolution mechanical co-design lowered the mean payload-shock objective from 6.06 g to 3.09 g and raised the share of kerb conditions inside the 3 g budget from 25% to 88%. The co-designed rover climbs kerbs up to 16 cm head-on at friction 1, at a minimum approach speed of 1.2 m/s and a peak payload shock of 2.98 g at that height. On 2250 seeded episodes of 5 controllers the success rate ranges from 50.0% to 87.6%. Against the reference controller (APF + kerb logic), Pure pursuit changes completion time by -1.7 s (paired t(231) = -8.1, p = 2.37e-14, d_z = -0.53); DWA + kerb logic changes completion time by -3.0 s (paired t(284) = -7.3, p = 2.67e-12, d_z = -0.43). Under the larsen1993 survival model the rover changes expected survival by +1.3 percentage points (95% CI +1.2 to +1.5) and the rover alone matches the ambulance within 584 m; the dimensionless economics gives kappa = 0.22, a payback horizon of 9.2 months and delta FTE = 0.50 (placeholder inputs).

**Index Terms:** MuJoCo simulation, sidewalk delivery robot, automated external defibrillator, payload shock, kerb climbing, model predictive path integral control, dimensionless technoeconomics.

---

## I. Introduction
Survival from out-of-hospital cardiac arrest falls with every minute of delay to the first shock [1]. Drones that carry an automated external defibrillator (AED) have been flown against real alerts in Sweden and arrived before the ambulance in about two thirds of comparable cases [2], and ambulances are often busy, which is associated with later arrival [3]; national statistics frame the burden [4]. A ground rover is a complementary option that is not limited by airspace, weather or darkness, but it must cross kerbs, share sidewalks with pedestrians [5] and protect a sensitive payload from shock.

This paper investigates the interrogative research question:
> "Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation?"

The premises are handled as scenario assumptions: the sourced urban ambulance response time (10 min median, 17.7 min 90th percentile in Central Norway [3]) is shorter than the 15-20 minutes of the question, and the 7-10% per minute is a guideline rule of thumb [12] that we use next to the fitted model of Larsen et al. [1].

**Contributions.** (1) A validated MuJoCo model of a four-wheel rover with an isolated payload and a payload-shock metric (Section III). (2) A kerb traversability map and a mechanical co-design (Section VI-B). (3) A benchmark of 5 controllers on 2250 seeded episodes with paired statistics (Sections VI-C and VI-D). (4) A clinical and dimensionless economic layer with sourced and assumed inputs separated (Sections IV and VI-E).

---

## II. Related Work & Foundational Literature
* **Delivery-mode evidence.** Schierbeck et al. [2] dispatched AED drones in addition to standard EMS in two Swedish controlled airspaces and compared the AED delivery time with the ambulance arrival. Naess et al. [3] estimated the prevalence of busy ambulances in Central Norway (2013-2022) and their association with response time. Tsao et al. [4] is the American Heart Association statistical update and provides epidemiological context.
* **Survival versus delay.** Larsen et al. [1] fitted survival as a linear function of the delays to CPR, first shock and advanced life support; the 7-10% per minute rule of thumb comes from resuscitation guidelines [12].
* **Sidewalk robots and pedestrians.** Weinberg et al. [5] observed a Pittsburgh sidewalk delivery-robot pilot ethnographically; pedestrians in our simulator follow a social-force model [11].
* **Local navigation.** Artificial potential fields [6], the dynamic window approach [8], sampling-based control with physics rollouts [9] and proximal policy optimisation [10] are compared on the MuJoCo physics engine [7].

None of the six foundational papers evaluates a ground delivery vehicle's kerb climbing or payload shock; this paper addresses that gap and quantifies what it means for the time to first shock.

---

## III. System Architecture and Mathematical Modeling

### A. MuJoCo Multi-Body Physics Model
The rover (`models/aed_delivery_amr.xml`) has a free-jointed chassis (22 kg), a payload of 4 kg on a three-axis viscoelastic isolator, four independent suspension slide joints, front-axle steering and velocity-controlled wheel motors. The generalised equations of motion are

$$M(q)\ddot{q} + C(q,\dot{q})\dot{q} + g(q) = \tau + J^T F_{ext}$$

and the sprung natural frequency and damping ratio are $\omega_n = \sqrt{k_s/m_s}$ and $\zeta_s = c_s/(2\sqrt{k_s m_s})$. Physics runs at 2 ms and controllers act at 50 Hz. Terrain is built from mocap bodies so that scenarios reset without recompiling.

![Fig. 1. System architecture (`docs/figures/figure1_system_architecture.png`)](figures/figure1_system_architecture.png)

**Fig. 1.** System architecture of the simulated rover, from scenario generation to the clinical layer.

### B. Payload Shock Metric
The dynamic payload acceleration is $\mathbf{a}_{dyn} = \mathbf{a}_{proper} - g\mathbf{u}_{body}$, low-pass filtered at 80 Hz with a zero-phase 4th-order Butterworth filter; the reported shock is $\max \lVert\mathbf{a}_{dyn}\rVert/g$ against a budget of 3 g (a design assumption).

### C. Controllers and Safety Filter
Five controllers share one observation interface and one speed-and-separation filter that enforces $d_{free} - v\,t_{react} - v^2/(2 a_{brake}) \ge 0$ on the footprint swept along the commanded arc (2 m/s^2, 0.1 s): pure pursuit, artificial potential field [6], dynamic window approach [8], MPPI [9] with MuJoCo rollouts (K = 128, H = 20) and a PPO policy [10]. APF and DWA can add a kerb negotiator that caps the approach speed at the measured minimum climbing speed plus a margin.

### D. Scenarios
Five seeded families (`flat_clear`, `kerb`, `crowded`, `mixed`, `slippery`) of 36 m sidewalk segments with kerbs of 0.09-0.15 m, friction 0.7-1.1, payload 3-5 kg, pedestrians and obstacles. Episodes end on goal, collision, rollover, leaving the sidewalk, stall or timeout.

---

## IV. Computer Science and Business Systems (CSBS) Technoeconomic Analysis
**Survival.** With times in minutes from collapse, $S = 0.67 - 0.023\,t_{cpr} - 0.011\,t_{defib} - 0.021\,t_{acls}$ [1]. (An earlier draft used 0.046 for the shock term; that value is not in the published model.) The rover changes only $t_{defib}$; the ambulance response time is sampled from a lognormal distribution fitted to the median and 90th percentile of [3].

**Time to first shock.** $t_{amb} = t_{c2c} + R$ and $t_{rover} = t_{c2c} + t_{alert} + d\phi/v + t_{handoff}$; the device is dispatched in addition to the ambulance, so the first shock is the earlier of the two.

**Economics (dimensionless).** $\kappa = \text{operating burden}/\text{value of reclaimed labour}$ (target $\le 0.25$), $P_{months} = \text{capital parity}/(1-\kappa)\times 12$ and $\Delta\text{FTE} = \text{reclaimed hours}/2080$. No currency is used.

---

## V. Experimental Protocol and Statistics
Every controller runs the same seeded scenarios, so comparisons are paired by scenario. Reported per comparison: degrees of freedom, $t$, exact $p$, effect size ($d_z$ for paired data) and the 95% confidence interval of the mean difference; success uses an exact McNemar test; Holm adjustment covers the family of $t$ tests. The sample size is at least 50 episodes per controller. The reference is the classical controller with the highest success rate (ties: lower median time), declared before the comparison.

---

## VI. Experimental Evaluation and Results

### A. Physics Validation
Static equilibrium: the rover settles at a ride height of 278.5 mm against the expected 278.8 mm (error -0.34 mm), and the payload accelerometer reads 9.810 m/s^2 against 9.81 m/s^2. The effective tyre radial stiffness measured from the static penetration is 313 kN/m under a wheel load of 106.4 N. Free-bounce ring-down runs (3 with enough peaks to fit) reproduce the closed-form 2-DOF quarter-car natural frequency within 0.25% and the damping ratio within 1.54%. Straight rolling at 0.5, 1, 2 m/s reaches 0.70% to 0.70% speed error with lateral drift below 0.003 mm. A random-command soak of 1,000,000 physics steps over a kerb field stayed finite: True.

### B. Kerb Traversability and Mechanical Co-Design
Head-on kerb-up climbs at friction 1: the minimum successful approach speed of the nominal rover (wheel radius 0.150 m) rises from 0.6 m/s at 6 cm to 1.8 m/s at 16 cm; the co-designed rover (0.219 m) needs 0.6 to 1.2 m/s over the same range. At the 12 cm kerb the peak payload shock at the minimum climbing speed is 2.90 g (nominal, 1.0 m/s) versus 1.93 g (optimised, 1.0 m/s), against a 3 g budget. On a low-friction surface (mu = 0.5) the 16 cm kerb is not climbable by the nominal rover within the scanned speeds, while the optimised rover climbs it at 2.2 m/s (peak shock 4.97 g). The slowest successful climb anywhere in the grids was 0.6 m/s, so every climb in these results relies on momentum. Of the head-on cells that succeed, 100% also succeed at a 15 degree approach angle (nominal), 100% also succeed at a 30 degree approach angle (nominal). The share of kerb-up (height, friction) cells with a shock-compliant climb window is 44% (nominal, 18 cells) versus 83% (optimised, 18 cells). Kerb-down peak shock is a median of 1.68 g (nominal) versus 0.96 g (optimised). Grid outcomes: nominal {'ok': 5501, 'stall': 460, 'timeout': 87} of 6048 trials, optimised {'ok': 1436, 'stall': 73, 'timeout': 3} of 1512 trials.

**TABLE I. Kerb-up minimum climbing speed and payload shock, head-on approach**

| Kerb height (cm) | Friction mu | Nominal r = 0.150 m: v_min (m/s) | peak shock (g) | Optimised r = 0.219 m: v_min (m/s) | peak shock (g) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 1 | 0.6 | 1.51 | 0.6 | 0.84 |
| 8 | 1 | 0.8 | 1.81 | 0.8 | 1.61 |
| 10 | 1 | 0.8 | 2.87 | 0.8 | 1.68 |
| 12 | 1 | 1.0 | 2.90 | 1.0 | 1.93 |
| 14 | 1 | 1.4 | 4.33 | 1.2 | 2.64 |
| 16 | 1 | 1.8 | 5.15 | 1.2 | 2.98 |
| 6 | 0.5 | 1.0 | 1.94 | 0.6 | 1.85 |
| 8 | 0.5 | 1.4 | 2.89 | 1.0 | 1.35 |
| 10 | 0.5 | 1.8 | 4.37 | 1.6 | 2.18 |
| 12 | 0.5 | 2.2 | 6.03 | 1.6 | 2.79 |
| 14 | 0.5 | 2.8 | 9.82 | 1.8 | 3.65 |
| 16 | 0.5 | no climb | n/a | 2.2 | 4.97 |

Differential evolution (1116 objective evaluations, 30 generations; best-of-generation objective 3.70 g in the first generation and 3.09 g in the last) searched six variables. The objective is the mean payload shock at the lowest kerb-climbing speed plus a margin, averaged over six kerb-up conditions (heights 0.10, 0.12, 0.14 m at two friction values) with half the mean kerb-down shock added; a condition that cannot be climbed is charged 8 g. The objective fell from 6.06 g to 3.09 g, and the share of the eight conditions within the 3 g budget rose from 25% to 88%. The optimum uses larger wheels, a softer suspension (zeta_s 1.023 to 0.577) and a much softer payload isolator (natural frequency 23.45 to 13.42 rad/s).

**TABLE II. Mechanical co-design (nominal against optimised)**

| Quantity | Nominal (draft) | Optimised (co-design) | Search bounds |
| :--- | ---: | ---: | ---: |
| Wheel radius (m) | 0.1500 | 0.2188 | 0.13 to 0.22 |
| Suspension stiffness k_s (N/m) | 4500.0 | 2656.7 | 2500 to 8000 |
| Suspension damping c_s (N s/m) | 350.0 | 151.6 | 150 to 700 |
| Isolator stiffness k_p (N/m) | 2200.0 | 720.5 | 600 to 4000 |
| Isolator damping c_p (N s/m) | 180.0 | 50.2 | 40 to 400 |
| Motor peak torque (N m) | 25.00 | 30.96 | 15 to 45 |
| Suspension damping ratio zeta_s (derived) | 1.023 | 0.577 | - |
| Suspension natural frequency (rad/s, derived) | 26.31 | 20.22 | - |
| Isolator damping ratio zeta_p (derived) | 0.959 | 0.468 | - |
| Isolator natural frequency (rad/s, derived) | 23.45 | 13.42 | - |
| Objective (mean shock, g; lower is better) | 6.06 | 3.09 | - |
| Conditions within the 3 g budget | 25.0% | 87.5% | - |
| Kerb-up conditions that cannot be climbed | 0 | 0 | - |

![Fig. 2. Kinematic telemetry (`docs/figures/figure2_kinematic_telemetry.png`)](figures/figure2_kinematic_telemetry.png)

**Fig. 2.** Kinematic telemetry of one simulated episode (DWA + kerb logic, kerb family, seed 5000, 10.1 cm kerb): speed command, per-step payload shock and lateral position; the shaded band is the road crossing. The episode peak shock (low-pass metric) is 2.15 g against the 3 g budget.

### C. Controller Benchmark
Source file `benchmark_standard.csv`: 2250 episodes, 5 controllers, 5 scenario families, 50 to 100 episodes per controller and family; every controller sees the same seeds, so comparisons are paired. All controllers ran behind the same speed-and-separation safety filter. Success rates run from 50.0% (Pure pursuit) to 87.6% (PPO). The fastest median completion time among successful episodes is 18.4 s (Pure pursuit). Collisions: Pure pursuit 32, APF + kerb logic 21, DWA + kerb logic 50, MPPI 2, PPO 4.

**TABLE III. Controller benchmark (all scenario families pooled)**

| Controller | N | Success (95% Wilson CI) | Median time (s) | Median peak shock (g) | Episodes over 3 g | Collisions | Stall or timeout | Off sidewalk or rollover |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Pure pursuit | 500 | 50.0% (45.6% to 54.4%) | 18.4 | 1.07 | 17.6% | 32 | 218 | 0 |
| APF + kerb logic | 500 | 68.0% (63.8% to 71.9%) | 21.5 | 1.06 | 13.6% | 21 | 103 | 36 |
| DWA + kerb logic | 500 | 65.6% (61.3% to 69.6%) | 21.5 | 1.13 | 5.4% | 50 | 116 | 6 |
| MPPI | 250 | 76.8% (71.2% to 81.6%) | 23.9 | 1.08 | 2.0% | 2 | 30 | 26 |
| PPO | 500 | 87.6% (84.4% to 90.2%) | 19.4 | 1.24 | 1.0% | 4 | 33 | 25 |

![Fig. 3. Comparative benchmark (`docs/figures/figure3_comparative_performance.png`)](figures/figure3_comparative_performance.png)

**Fig. 3.** Success rate by scenario family with Wilson 95% intervals, and peak payload shock and completion time of the successful episodes.

### D. Paired Statistics
Reference controller: **APF + kerb logic**, chosen by the pre-declared rule 'highest success rate among the classical controllers, ties broken by lower median time'. Differences are other minus reference, so a positive time difference means the other controller is slower. Paired t tests use scenarios that both controllers completed; d_z is the mean difference over the standard deviation of the differences; Holm adjustment covers all t tests together.

* **Pure pursuit against APF + kerb logic** (500 paired scenarios, 232 reached by both): completion time difference -1.69 s (95% CI -2.10 to -1.28), t(231) = -8.15, p = 2.37e-14, d_z = -0.53; peak shock difference +0.134 g (95% CI +0.110 to +0.157), t(231) = 11.22, p = 1.28e-23, d_z = +0.74; success rate -18.0 percentage points (exact McNemar p = 7.86e-17, 108 scenarios won only by the reference, 18 only by the other).
* **DWA + kerb logic against APF + kerb logic** (500 paired scenarios, 285 reached by both): completion time difference -2.97 s (95% CI -3.77 to -2.17), t(284) = -7.31, p = 2.67e-12, d_z = -0.43; peak shock difference -0.144 g (95% CI -0.187 to -0.100), t(284) = -6.46, p = 4.64e-10, d_z = -0.38; success rate -2.4 percentage points (exact McNemar p = 0.2664, 55 scenarios won only by the reference, 43 only by the other).
* **MPPI against APF + kerb logic** (250 paired scenarios, 145 reached by both): completion time difference +1.48 s (95% CI +0.66 to +2.30), t(144) = 3.57, p = 4.84e-04, d_z = +0.30; peak shock difference -0.484 g (95% CI -0.598 to -0.370), t(144) = -8.40, p = 3.87e-14, d_z = -0.70; success rate +9.6 percentage points (exact McNemar p = 0.0056, 23 scenarios won only by the reference, 47 only by the other).
* **PPO against APF + kerb logic** (500 paired scenarios, 326 reached by both): completion time difference -7.17 s (95% CI -8.20 to -6.15), t(325) = -13.78, p = 2.45e-34, d_z = -0.76; peak shock difference -0.160 g (95% CI -0.222 to -0.098), t(325) = -5.08, p = 6.50e-07, d_z = -0.28; success rate +19.6 percentage points (exact McNemar p = 3.69e-20, 14 scenarios won only by the reference, 112 only by the other).

**TABLE IV. Paired comparisons against the reference controller**

| Comparison (other - reference) | Metric | Pairs | Mean difference [95% CI] | df | t | Exact p | p (Holm) | Effect size [95% CI] |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Pure pursuit - APF + kerb logic | Completion time (s) | 232 | -1.687 [-2.096, -1.279] | 231 | -8.15 | 2.37e-14 | 1.42e-13 | -0.53 [-0.67, -0.40] |
| Pure pursuit - APF + kerb logic | Peak payload shock (g) | 232 | +0.134 [+0.110, +0.157] | 231 | 11.22 | 1.28e-23 | 8.96e-23 | +0.74 [+0.59, +0.88] |
| Pure pursuit - APF + kerb logic | Reached the goal (exact McNemar) | 500 | -18.0 pp | - | - | 7.86e-17 | - | 108 vs 18 discordant |
| DWA + kerb logic - APF + kerb logic | Completion time (s) | 285 | -2.969 [-3.768, -2.170] | 284 | -7.31 | 2.67e-12 | 1.07e-11 | -0.43 [-0.55, -0.31] |
| DWA + kerb logic - APF + kerb logic | Peak payload shock (g) | 285 | -0.144 [-0.187, -0.100] | 284 | -6.46 | 4.64e-10 | 1.39e-09 | -0.38 [-0.50, -0.26] |
| DWA + kerb logic - APF + kerb logic | Reached the goal (exact McNemar) | 500 | -2.4 pp | - | - | 0.2664 | - | 55 vs 43 discordant |
| MPPI - APF + kerb logic | Completion time (s) | 145 | +1.479 [+0.660, +2.298] | 144 | 3.57 | 4.84e-04 | 4.84e-04 | +0.30 [+0.13, +0.46] |
| MPPI - APF + kerb logic | Peak payload shock (g) | 145 | -0.484 [-0.598, -0.370] | 144 | -8.40 | 3.87e-14 | 1.93e-13 | -0.70 [-0.88, -0.52] |
| MPPI - APF + kerb logic | Reached the goal (exact McNemar) | 250 | +9.6 pp | - | - | 0.0056 | - | 23 vs 47 discordant |
| PPO - APF + kerb logic | Completion time (s) | 326 | -7.174 [-8.198, -6.149] | 325 | -13.78 | 2.45e-34 | 1.96e-33 | -0.76 [-0.89, -0.64] |
| PPO - APF + kerb logic | Peak payload shock (g) | 326 | -0.160 [-0.222, -0.098] | 325 | -5.08 | 6.50e-07 | 1.30e-06 | -0.28 [-0.39, -0.17] |
| PPO - APF + kerb logic | Reached the goal (exact McNemar) | 500 | +19.6 pp | - | - | 3.69e-20 | - | 14 vs 112 discordant |

### E. Clinical Outcome and Economics
Under the larsen1993 model the rover (dispatched in parallel with the ambulance) changes expected survival by +1.3 percentage points (95% CI +1.2 to +1.5) relative to the ambulance alone (0.233); the interval excludes zero. It shocks strictly earlier than the ambulance in 38% of the 2000 simulated arrests, saving a median of 3.47 min in those. Break-even: the rover acting alone matches the ambulance acting alone at a straight-line radius of 584 m; beyond that the ambulance is expected to shock first. Scenario inputs recorded in the results file: rover_controller = ppo, response_radius_m = 500, crossings_per_km_ASSUMED = 4.0, route_factor = 1.54.

**TABLE V. Expected survival by delivery mode**

| Mode | Simulated arrests | Expected survival (larsen1993) [95% CI] | Gain over ambulance (pp) [95% CI] | Shocks first | Median time saved when first (min) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| ambulance | 2000 | 0.233 [0.227, 0.239] | - | - | - |
| rover | 2000 | 0.246 [0.241, 0.252] | +1.3 [+1.2, +1.5] | 38% | 3.47 |
| drone | 2000 | 0.303 [0.298, 0.307] | +7.0 [+6.8, +7.1] | 99% | 6.36 |

Model-form sensitivity (other survival models in the results file):

| Model | Mode | Expected survival [95% CI] | Gain over ambulance (pp) [95% CI] |
| :--- | :--- | ---: | ---: |
| rule_of_thumb | ambulance | 0.025 [0.022, 0.028] | - |
| rule_of_thumb | rover | 0.025 [0.022, 0.028] | +0.0 [+0.0, +0.0] |
| rule_of_thumb | drone | 0.283 [0.283, 0.284] | +25.8 [+25.6, +26.1] |

Dimensionless economics (no currency anywhere): kappa = 0.220, which meets the course target kappa <= 0.25; payback horizon 9.2 months; staff capacity freed delta FTE = 0.50. The inputs are placeholder ratios (ASSUMPTIONS), not measurements; kappa is therefore a demonstration of the method, not a forecast.

---

## VII. Discussion and Limitations
**Conditional answer.** In this simulation study the rover dispatched in parallel with the ambulance does give a statistically clear survival gain (+1.3 percentage points, 95% CI +1.2 to +1.5, larsen1993 model), and the rover acting alone matches the ambulance acting alone at a straight-line radius of 584 m; beyond that the ambulance is expected to shock first. The answer depends on the ambulance response-time distribution and the dispatch assumptions of the scenario; it does not establish that urban ambulance delays are 15-20 minutes (the sourced Central Norway urban median is 10.0 min and 90th percentile 17.7 min, Naess et al. 2024), and it is not a statement about any Indian city.

* The clinical layer uses Western cohort data and assumed dispatch delays; the conclusion cannot be transferred to an Indian city without local response-time and outcome data.
* Larsen's model attributes 0.011 per minute to the shock delay, whereas the guideline rule of thumb is about seven times steeper; the survival conclusion is more sensitive to this model-form choice than to any controller difference.
* The simulator is idealised (rigid cylinder tyres, idealised lidar, Gaussian tracker noise, social-force pedestrians with assumed parameters) and has no hardware-in-the-loop validation; benchmark differences measure robustness to this simulator only.
* Economics uses placeholder ratios and is a demonstration of the dimensionless method.

---

## VIII. Conclusion
We built and validated a MuJoCo model of an AED delivery rover, mapped its kerb-climbing envelope, co-designed its mechanics and benchmarked five controllers with paired statistics. **Conditional answer.** In this simulation study the rover dispatched in parallel with the ambulance does give a statistically clear survival gain (+1.3 percentage points, 95% CI +1.2 to +1.5, larsen1993 model), and the rover acting alone matches the ambulance acting alone at a straight-line radius of 584 m; beyond that the ambulance is expected to shock first. The answer depends on the ambulance response-time distribution and the dispatch assumptions of the scenario; it does not establish that urban ambulance delays are 15-20 minutes (the sourced Central Norway urban median is 10.0 min and 90th percentile 17.7 min, Naess et al. 2024), and it is not a statement about any Indian city. Future work: hardware-in-the-loop validation of the kerb-climbing envelope, local ambulance response-time data, and a route-level simulation of complete missions.

---

## References

[1] Larsen MP et al. "Predicting survival from out-of-hospital cardiac arrest: A graphic model," *Annals of Emergency Medicine, 22(11):1652-1658*, 1993. DOI: [https://doi.org/10.1016/S0196-0644(05)81302-2](https://doi.org/10.1016/S0196-0644(05)81302-2)

[2] Schierbeck S et al. "Drone delivery of automated external defibrillators compared with ambulance arrival in real-life suspected out-of-hospital cardiac arrests: a prospective observational study in Sweden," *The Lancet Digital Health, 5(12):e862-e871*, 2023. DOI: [https://doi.org/10.1016/S2589-7500(23)00161-9](https://doi.org/10.1016/S2589-7500(23)00161-9)

[3] Naess LE et al. "Using machine learning to assess the extent of busy ambulances and its impact on ambulance response times: A retrospective observational study," *PLOS ONE, 19*, 2024. DOI: [https://doi.org/10.1371/journal.pone.0296308](https://doi.org/10.1371/journal.pone.0296308)

[4] Tsao CW et al. "Heart Disease and Stroke Statistics-2023 Update: A Report From the American Heart Association," *Circulation, 147*, 2023. DOI: [https://doi.org/10.1161/CIR.0000000000001123](https://doi.org/10.1161/CIR.0000000000001123)

[5] Weinberg D et al. "Sharing the Sidewalk: Observing Delivery Robot Interactions with Pedestrians during a Pilot in Pittsburgh, PA," *Multimodal Technologies and Interaction, 7*, 2023. DOI: [https://doi.org/10.3390/mti7050053](https://doi.org/10.3390/mti7050053)

[6] Khatib O "Real-Time Obstacle Avoidance for Manipulators and Mobile Robots," *The International Journal of Robotics Research, 5(1):90-98*, 1986. DOI: [https://doi.org/10.1177/027836498600500106](https://doi.org/10.1177/027836498600500106)

[7] Todorov E, Erez T, Tassa Y "MuJoCo: A physics engine for model-based control," *IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS), 2012*, 2012. DOI: [https://doi.org/10.1109/IROS.2012.6386109](https://doi.org/10.1109/IROS.2012.6386109)

[8] Fox D, Burgard W, Thrun S "The dynamic window approach to collision avoidance," *IEEE Robotics & Automation Magazine, 4(1):23-33*, 1997. DOI: [https://doi.org/10.1109/100.580977](https://doi.org/10.1109/100.580977)

[9] Williams G et al. "Information theoretic MPC for model-based reinforcement learning," *IEEE International Conference on Robotics and Automation (ICRA), 2017*, 2017. DOI: [https://doi.org/10.1109/ICRA.2017.7989202](https://doi.org/10.1109/ICRA.2017.7989202)

[10] Schulman J et al. "Proximal Policy Optimization Algorithms," *arXiv preprint, :1707.06347*, 2017. DOI: [https://doi.org/10.48550/arXiv.1707.06347](https://doi.org/10.48550/arXiv.1707.06347)

[11] Helbing D, Molnar P "Social force model for pedestrian dynamics," *Physical Review E, 51:4282*, 1995. DOI: [https://doi.org/10.1103/PhysRevE.51.4282](https://doi.org/10.1103/PhysRevE.51.4282)

[12] Kim TY et al. "2025 Korean Guidelines for Cardiopulmonary Resuscitation: Part 4. Adult advanced life support," *Clinical and Experimental Emergency Medicine, 13:S32-S60*, 2026. DOI: [https://doi.org/10.15441/ceem.26.073](https://doi.org/10.15441/ceem.26.073)
