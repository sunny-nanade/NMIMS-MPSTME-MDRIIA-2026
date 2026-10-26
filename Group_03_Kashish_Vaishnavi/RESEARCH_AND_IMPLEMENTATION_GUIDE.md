# Research & Implementation Guide: Autonomous Ground AED Delivery AMR
## Modern Day Robotics & Its Industrial Applications (MDRIIA)
**Project Title:** Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation?
**Group ID:** MDRIIA Group 03

---

## 1. Executive Scientific Problem Deconstruction

Out-of-hospital cardiac arrest (OHCA) is time critical: in the linear survival model of Larsen et al. (1993) every minute of delay to the first shock, to CPR and to advanced life support removes survival probability, and the three delays together remove 5.5% per minute when nothing is done. This project asks whether a compact ground rover that drives on sidewalks, climbs kerbs and protects an AED payload from shock loads can deliver the device earlier than an ambulance.

Two premises of the title need care and are treated as scenario assumptions, not as established facts:

1. **"Ambulance congestion delays of 15-20 minutes."** The best sourced distribution available to this project (Naess et al. 2024, Central Norway, 216,787 incidents, 2013-2022) has an urban median response time of 10 min and a 90th percentile of 17.7 min; that paper is about busy ambulances, not road congestion. Nothing in the sourced data establishes 15-20 minutes for any Indian city, so the analysis reports its answer as a function of the response-time distribution.
2. **"Survival drops 7-10% for every minute without defibrillation."** This is a guideline rule of thumb (Kim et al. 2026, doi 10.15441/ceem.26.073), not the fitted Larsen model, whose shock coefficient is 0.011 per minute. Both are used: the Larsen model as the primary model and the rule of thumb as a model-form sensitivity check.

The engineering question is therefore: how fast can the rover travel on realistic sidewalk scenes (kerbs of 6-16 cm, pedestrians, obstacles, low friction) while keeping the peak payload shock below a budget of 3 g (a design assumption of this project), and how does that speed compare with the ambulance in the clinical model?

---

## 2. Mathematical Formulations & Kinematic Modeling (corrected)

### 2.1 Quarter-Car Suspension Dynamics
Each wheel station $i \in \{1,2,3,4\}$ is a two-degree-of-freedom quarter car:

$$m_s \ddot{z}_{s,i} + c_s (\dot{z}_{s,i} - \dot{z}_{u,i}) + k_s (z_{s,i} - z_{u,i}) = 0$$

$$m_u \ddot{z}_{u,i} - c_s (\dot{z}_{s,i} - \dot{z}_{u,i}) - k_s (z_{s,i} - z_{u,i}) + k_t (z_{u,i} - z_{r,i}) = 0$$

where $m_s$ is the sprung mass per wheel (chassis plus payload divided by four), $m_u$ the unsprung mass (wheel, hub motor and knuckle), $k_s$ and $c_s$ the suspension spring and damper, $k_t$ the effective tyre radial stiffness and $z_{r,i}$ the ground profile. The sprung-mass natural frequency and damping ratio used in this guide are $\omega_n = \sqrt{k_s/m_s}$ and $\zeta_s = c_s / (2\sqrt{k_s m_s})$. In the simulation $k_t$ is not a free parameter: it emerges from the MuJoCo contact softness (`solref`) and is measured by static penetration.

| Parameter | Nominal (draft design) | Optimised (co-design, shipped model) |
| :--- | ---: | ---: |
| Chassis mass (kg) | 22.0 | 22.0 |
| Payload mass (kg) | 4.0 | 4.0 |
| Wheelbase (m) | 0.62 | 0.62 |
| Track (m) | 0.62 | 0.62 |
| Wheel radius (m) | 0.1500 | 0.2188 |
| Wheel and hub-motor mass (kg) | 1.650 | 3.749 |
| Knuckle mass (kg) | 0.60 | 0.60 |
| Suspension stiffness k_s (N/m) | 4500.0 | 2656.7 |
| Suspension damping c_s (N s/m) | 350.0 | 151.6 |
| Isolator stiffness k_p (N/m) | 2200.0 | 720.5 |
| Isolator damping c_p (N s/m) | 180.0 | 50.2 |
| Motor peak torque per wheel (N m) | 25.00 | 30.96 |
| Wheel speed limit (rad/s) | 30 | 30 |
| Tyre-ground friction | 1.00 | 1.00 |
| Total mass (kg, derived) | 35.00 | 43.40 |
| Sprung mass per wheel (kg, derived) | 6.50 | 6.50 |
| Unsprung mass per wheel (kg, derived) | 2.250 | 4.349 |
| Suspension damping ratio zeta_s (derived) | 1.023 | 0.577 |
| Suspension natural frequency (rad/s, derived) | 26.31 | 20.22 |
| Tyre contact solref (s, damping ratio) | 0.03, 1 | 0.03, 1 |

### 2.2 Payload Isolator and Shock Metric
The AED payload sits on a viscoelastic isolator (slide joints along x, y, z; the vertical joint has stiffness $k_p$ and damping $c_p$):

$$m_p \ddot{z}_p = -k_p (z_p - z_c) - c_p (\dot{z}_p - \dot{z}_c)$$

The payload accelerometer reports proper acceleration, so the shock is the dynamic part $\mathbf{a}_{dyn} = \mathbf{a}_{proper} - g\,\mathbf{u}_{body}$, where $\mathbf{u}_{body}$ is the world-up direction in the chassis frame; it is passed through a zero-phase 4th-order Butterworth low-pass filter at 80 Hz and the peak of $\lVert\mathbf{a}_{dyn}\rVert / g$ is reported. The limit 3 g is a project design assumption. (The earlier draft attributed 3 g to ISO 16750-3; that attribution could not be verified and is not used.)

### 2.3 Cardiac Survival Model (Larsen et al. 1993, corrected)
With all times in minutes measured from collapse,

$$S(t_{cpr}, t_{defib}, t_{acls}) = 0.67 - 0.023\,t_{cpr} - 0.011\,t_{defib} - 0.021\,t_{acls}, \qquad S \in [0, 0.67].$$

The intercept 0.67 is the survival if all three interventions happen at collapse; the three slopes sum to 0.055 per minute. **Correction of the earlier draft:** it used 0.046 per minute for the shock term and no ACLS term. Neither is part of the published model. Because the shock slope is only 0.011 per minute, the model attributes modest survival value to a shock-time saving; the guideline rule of thumb (7-10 percentage points per minute, Kim et al. 2026) is about seven times steeper, and the two bracket the plausible range.

Worked example from the package: with CPR at 3 min and ACLS at 10 min, shocking at 2 min instead of 6 min changes survival by 4.4 percentage points under Larsen and by 28 to 40 under the rule of thumb (7% to 10% per minute).

### 2.4 Time to First Shock
From collapse, with $R$ the sampled ambulance response time (which already runs from the emergency call):

$$t_{amb} = t_{c2c} + R, \qquad t_{rover} = t_{c2c} + t_{alert} + \frac{d\,\phi}{v} + t_{handoff}$$

where $t_{c2c}$ is collapse-to-call, $t_{alert}$ the call-taker and dispatch latency, $d$ the straight-line radius, $\phi$ the route factor, $v$ the rover speed and $t_{handoff}$ the time for a bystander to take the AED and apply the pads. CPR time and ACLS time are common to all modes, so a delivery device changes survival only through $t_{defib}$. Two comparisons are used and must not be confused: dispatch in parallel with the ambulance (first shock is the minimum of the two times, so the gain is the marginal benefit of adding the device) and the device alone against the ambulance alone (the radius at which the two expected survivals are equal is the break-even radius). Defaults of the scenario (all ASSUMPTIONS unless a results file says otherwise):

| Parameter | Default | Status |
| :--- | ---: | :--- |
| `radius_m` | 1000 | ASSUMPTION |
| `rover_speed_mps` | 2 | ASSUMPTION |
| `route_factor` | 1.3 | ASSUMPTION |
| `drone_speed_mps` | 15 | ASSUMPTION |
| `drone_launch_min` | 0.5 | ASSUMPTION |
| `ems_median_min` | 10 | sourced: Naess et al. 2024, urban median |
| `ems_p90_over_median` | 1.77 | sourced: Naess et al. 2024, urban 90th percentile / median |
| `busy_increase` | 0 | ASSUMPTION |
| `dispatch.collapse_to_call_min` | 1 | ASSUMPTION |
| `dispatch.call_to_alert_min` | 1.5 | ASSUMPTION |
| `dispatch.handoff_min` | 1 | ASSUMPTION |
| `dispatch.bystander_cpr_delay_min` | 3 | ASSUMPTION |
| `dispatch.ems_arrival_to_shock_min` | 0 | ASSUMPTION |

### 2.5 Statistical Framework
* **Paired t test:** $t = \bar{d} / (s_d/\sqrt{n})$ with $df = n - 1$, exact two-sided $p$, effect size $d_z = \bar{d}/s_d$ and the t-based 95% confidence interval of $\bar{d}$; Welch's test is used for independent groups.
* **Cohen's d** for independent samples uses the pooled standard deviation; its 95% interval is the non-central-t pivot interval.
* **Proportions:** Wilson score intervals; paired success rates use an exact McNemar test on the discordant scenarios.
* **Multiplicity:** Holm adjustment across the family of t tests.
* **Sample size:** at least $N \ge 50$ episodes per controller (course mandate).

### 2.6 Dimensionless Health Economics & Operational Parity
No currency is used anywhere. Every cost is a ratio to the annualised value of the labour hours the system reclaims:

$$\kappa = \frac{\text{annualised operating burden (energy, maintenance, infrastructure)}}{\text{annualised value of reclaimed labour hours}} \le 0.25$$

$$P_{months} = \frac{\text{capital parity factor}}{1 - \kappa} \times 12, \qquad \Delta \text{FTE} = \frac{\text{annual reclaimed task hours}}{2080\ \text{h/year}}$$

$$\Delta Q = \Delta S \times L_{exp} \times QoL \quad \text{(undiscounted QALYs per encounter; inputs must be supplied and are assumptions)}$$

The draft's fixed values (kappa of 0.095, 12 years of life expectancy, quality of life 0.85) were unsourced placeholders and are not used as results.

---

## 3. Simulation Model

The rover is generated by `aedrover.sim.vehicle_mjcf` and placed in a procedural sidewalk world by `aedrover.sim.world`. Topology: a free-jointed chassis; a payload body on three slide joints (viscoelastic isolator) carrying the accelerometer; four knuckles on vertical slide joints (independent suspension), the two front ones with a steering hinge; and one spin hinge with a cylinder tyre per wheel. Drive uses velocity actuators with a torque clamp on the spin joints and position actuators on the steering joints, so the Python loop writes only eight numbers per control step. Controllers command a forward speed and a bicycle steering angle that an Ackermann allocation turns into wheel speeds and steer angles. The environment steps physics at 2 ms and the controllers act at 50 Hz.

**Scenario families** (`aedrover.sim.scenario`): `flat_clear`, `kerb`, `crowded`, `mixed`, `slippery`. A segment is a straight 36 m stretch of sidewalk; kerb families add a road crossing (walk A, road, walk B). Kerb height is sampled from 0.09-0.15 m, friction from 0.7-1.1 (lower in the slippery family), payload mass from 3 to 5 kg, and pedestrians walk in streams under a social-force model (Helbing and Molnar 1995 form; the strengths and ranges are ASSUMPTIONS, not fitted). Episodes end on goal, collision, rollover, leaving the sidewalk, stall or time limit.

**Perception:** a 73-ray lidar with 240 degrees field of view and 10 m range, a forward terrain-height scan, and a pedestrian tracker with Gaussian position and velocity noise. All controllers consume the same observations.

**Shipped MJCF:** `models/aed_delivery_amr.xml` is the co-designed rover on a 12 cm kerb crossing, generated by `aedrover.sim.world.build_xml(VehicleParams.optimized(), ...)` with the two sidewalk slabs moved into place at compile time. It loads with plain `mujoco.MjModel.from_xml_path`.

---

## 4. Controllers and Safety

| Controller | How it decides | Key parameters (package defaults) |
| :--- | :--- | :--- |
| Pure pursuit (baseline A) | Steers toward a point on the centre line; constant speed; no avoidance, no kerb logic. | cruise 1.4 m/s, look-ahead 1.2 m |
| APF, Khatib 1986 (baseline B) | Attraction toward the path plus repulsion from lidar returns, tracked pedestrians and the sidewalk edges; optional kerb-speed overlay ('APF + kerb logic'). | cruise 1.6 m/s, influence radius 2.5 m, eta 0.9, wall at +/-1.25 m |
| DWA, Fox 1997 (baseline C) | Samples 9 speeds x 15 steering angles inside the kinematic window, rolls each out on a bicycle model, rejects candidates that cannot stop before contact and scores progress, lane centring, speed, clearance to lidar points and constant-velocity pedestrian predictions; optional kerb-speed overlay. | cruise 1.8 m/s, horizon 2.4 s (step 0.15 s), a_max 1.6, a_brake 2 m/s^2 |
| MPPI, Williams 2017 with MuJoCo rollouts | Samples 128 (speed, steering) sequences, rolls all of them out in a MuJoCo copy of the world with `mujoco.rollout`, scores progress, payload shock, clearance, lane, heading, stability and smoothness, and moves the mean by the exponentially weighted average. The internal model is deliberately imperfect (coarser step, nominal friction and payload, no pedestrians in the physics). | K = 128, H = 20 x 0.1 s, physics step 0.01 s, temperature 0.3, re-plan every 5 control steps, v_max 2.6 m/s |
| PPO, Schulman 2017 | Stable-Baselines3 PPO with a MLP 256-256 with tanh activations policy trained on domain-randomised episodes (kerb height 0.06-0.16 m, friction 0.5-1.2) behind the same safety filter. | decision every 5 control steps, shock budget in the reward 2.5 g |
| Kerb negotiator (overlay for APF and DWA) | Detects a kerb step from the forward height scan and caps the approach speed at the tabulated minimum climbing speed for that height and an assumed friction, plus a margin (table `configs/curb_table.json`, measured in the kerb study). | assumed friction 0.8, margin 0.15 m/s, descent 0.8 m/s, planned deceleration 1.2 m/s^2 |

In the benchmark every controller was given the same top speed of 2 m/s (overriding the cruise speeds above), so time differences reflect planning quality and not a speed advantage. The MPPI settings are the variant frozen by `configs/mppi_tuned.json` on tuning seeds disjoint from every evaluation seed, and the PPO policy is the checkpoint chosen on validation seeds (`results/ppo_selection.csv`).

All controllers can be wrapped by the same speed-and-separation filter, so comparisons hold identical safety constraints:

| Safety-filter parameter | Default |
| :--- | ---: |
| Service braking used in the barrier | 2 m/s^2 |
| Reaction allowance | 0.1 s |
| Extra clearance ahead of the footprint | 0.15 m |
| Extra clearance to the sides | 0.04 m |
| Extra allowance around pedestrians | 0.1 m |
| Arc length considered | 6 m |
| Speed cap near pedestrians (policy parameter) | 1.4 m/s within 3 m |

**Standards mapping (honest).** The course manual lists constraints for this group; the table states where the implementation meets them and where it does not.

| Requirement (course manual) | Threshold | This implementation | Status |
| :--- | :--- | :--- | :--- |
| ISO 13482: speed limit in shared pedestrian zones | <= 0.80 m/s | 1.4 m/s within 3 m of a pedestrian (policy parameter) | Not met by default (the cap is a sweepable parameter; the manual states 0.80 m/s for occupied indoor zones) |
| ISO 13482: emergency braking deceleration | >= 1.5 m/s^2 | 2 m/s^2 assumed in the barrier | Consistent (planning value; not separately measured on the rover) |
| ISO 13482: dynamic clearance | >= 0.50 m | MPPI comfort clearance 0.5 m (soft cost); shield margins 0.15 m front, 0.04 m side (hard) | Partly met (hard constraint is smaller than 0.50 m) |
| ISO 3691-4: detection latency | <= 50 ms | 100 ms reaction allowance | Not met (assumed value) |
| ISO 3691-4: personnel detection field of view | >= 180 degrees | 240 degrees lidar, 10 m range | Met |
| ISO 3691-4: dual-zone warning and stop (1.5 m, 0.4 m) | fixed zones | continuous stopping-distance barrier on the swept footprint | Different mechanism |
| REP-103 axes and SI units | x forward, y left, z up | as documented in `sim/vehicle_mjcf.py` | Met |
| Sample size per controller | N >= 50 | 250 to 500 episodes | Met |
| Operating-burden ratio kappa | <= 0.25 | 0.220 (placeholder inputs) | Met |

---

## 5. Experimental Protocol

1. **Physics validation** against closed-form mechanics (static equilibrium, tyre stiffness, ring-down, rolling, million-step soak).
2. **Kerb traversability study:** kerb height x approach speed x approach angle x friction, kerb-up and kerb-down, for the nominal and the optimised design.
3. **Mechanical co-design:** differential evolution over wheel radius, suspension, isolator and motor torque.
4. **Controller benchmark:** every controller on the same seeded scenarios of all families; results are paired by scenario.
5. **Clinical and economic layer:** survival comparison, break-even radius and dimensionless economics.

---

## 6. Results (read from the result files at export time)

### 6.1 Physics validation
Static equilibrium: the rover settles at a ride height of 278.5 mm against the expected 278.8 mm (error -0.34 mm), and the payload accelerometer reads 9.810 m/s^2 against 9.81 m/s^2. The effective tyre radial stiffness measured from the static penetration is 313 kN/m under a wheel load of 106.4 N. Free-bounce ring-down runs (3 with enough peaks to fit) reproduce the closed-form 2-DOF quarter-car natural frequency within 0.25% and the damping ratio within 1.54%. Straight rolling at 0.5, 1, 2 m/s reaches 0.70% to 0.70% speed error with lateral drift below 0.003 mm. A random-command soak of 1,000,000 physics steps over a kerb field stayed finite: True.

| Target zeta | omega_n analytic (rad/s) | omega_n measured (rad/s) | error | zeta analytic | zeta measured | error |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.10 | 20.14 | 20.15 | +0.09% | 0.099 | 0.100 | +1.54% |
| 0.20 | 20.15 | 20.14 | -0.04% | 0.198 | 0.199 | +0.85% |
| 0.30 | 20.16 | 20.11 | -0.25% | 0.297 | 0.298 | +0.60% |

### 6.2 Kerb traversability
Head-on kerb-up climbs at friction 1: the minimum successful approach speed of the nominal rover (wheel radius 0.150 m) rises from 0.6 m/s at 6 cm to 1.8 m/s at 16 cm; the co-designed rover (0.219 m) needs 0.6 to 1.2 m/s over the same range. At the 12 cm kerb the peak payload shock at the minimum climbing speed is 2.90 g (nominal, 1.0 m/s) versus 1.93 g (optimised, 1.0 m/s), against a 3 g budget. On a low-friction surface (mu = 0.5) the 16 cm kerb is not climbable by the nominal rover within the scanned speeds, while the optimised rover climbs it at 2.2 m/s (peak shock 4.97 g). The slowest successful climb anywhere in the grids was 0.6 m/s, so every climb in these results relies on momentum. Of the head-on cells that succeed, 100% also succeed at a 15 degree approach angle (nominal), 100% also succeed at a 30 degree approach angle (nominal). The share of kerb-up (height, friction) cells with a shock-compliant climb window is 44% (nominal, 18 cells) versus 83% (optimised, 18 cells). Kerb-down peak shock is a median of 1.68 g (nominal) versus 0.96 g (optimised). Grid outcomes: nominal {'ok': 5501, 'stall': 460, 'timeout': 87} of 6048 trials, optimised {'ok': 1436, 'stall': 73, 'timeout': 3} of 1512 trials.

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

### 6.3 Mechanical co-design
Differential evolution (1116 objective evaluations, 30 generations; best-of-generation objective 3.70 g in the first generation and 3.09 g in the last) searched six variables. The objective is the mean payload shock at the lowest kerb-climbing speed plus a margin, averaged over six kerb-up conditions (heights 0.10, 0.12, 0.14 m at two friction values) with half the mean kerb-down shock added; a condition that cannot be climbed is charged 8 g. The objective fell from 6.06 g to 3.09 g, and the share of the eight conditions within the 3 g budget rose from 25% to 88%. The optimum uses larger wheels, a softer suspension (zeta_s 1.023 to 0.577) and a much softer payload isolator (natural frequency 23.45 to 13.42 rad/s).

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

### 6.4 Controller benchmark and paired statistics
Source file `benchmark_standard.csv`: 2250 episodes, 5 controllers, 5 scenario families, 50 to 100 episodes per controller and family; every controller sees the same seeds, so comparisons are paired. All controllers ran behind the same speed-and-separation safety filter. Success rates run from 50.0% (Pure pursuit) to 87.6% (PPO). The fastest median completion time among successful episodes is 18.4 s (Pure pursuit). Collisions: Pure pursuit 32, APF + kerb logic 21, DWA + kerb logic 50, MPPI 2, PPO 4.

| Controller | N | Success (95% Wilson CI) | Median time (s) | Median peak shock (g) | Episodes over 3 g | Collisions | Stall or timeout | Off sidewalk or rollover |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Pure pursuit | 500 | 50.0% (45.6% to 54.4%) | 18.4 | 1.07 | 17.6% | 32 | 218 | 0 |
| APF + kerb logic | 500 | 68.0% (63.8% to 71.9%) | 21.5 | 1.06 | 13.6% | 21 | 103 | 36 |
| DWA + kerb logic | 500 | 65.6% (61.3% to 69.6%) | 21.5 | 1.13 | 5.4% | 50 | 116 | 6 |
| MPPI | 250 | 76.8% (71.2% to 81.6%) | 23.9 | 1.08 | 2.0% | 2 | 30 | 26 |
| PPO | 500 | 87.6% (84.4% to 90.2%) | 19.4 | 1.24 | 1.0% | 4 | 33 | 25 |

Success rate by scenario family:

| Controller | flat_clear | kerb | crowded | mixed | slippery |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Pure pursuit | 100% | 100% | 21% | 13% | 16% |
| APF + kerb logic | 100% | 100% | 70% | 47% | 23% |
| DWA + kerb logic | 100% | 100% | 69% | 32% | 27% |
| MPPI | 100% | 100% | 70% | 56% | 58% |
| PPO | 100% | 100% | 100% | 69% | 69% |

Reference controller: **APF + kerb logic**, chosen by the pre-declared rule 'highest success rate among the classical controllers, ties broken by lower median time'. Differences are other minus reference, so a positive time difference means the other controller is slower. Paired t tests use scenarios that both controllers completed; d_z is the mean difference over the standard deviation of the differences; Holm adjustment covers all t tests together.

* **Pure pursuit against APF + kerb logic** (500 paired scenarios, 232 reached by both): completion time difference -1.69 s (95% CI -2.10 to -1.28), t(231) = -8.15, p = 2.37e-14, d_z = -0.53; peak shock difference +0.134 g (95% CI +0.110 to +0.157), t(231) = 11.22, p = 1.28e-23, d_z = +0.74; success rate -18.0 percentage points (exact McNemar p = 7.86e-17, 108 scenarios won only by the reference, 18 only by the other).
* **DWA + kerb logic against APF + kerb logic** (500 paired scenarios, 285 reached by both): completion time difference -2.97 s (95% CI -3.77 to -2.17), t(284) = -7.31, p = 2.67e-12, d_z = -0.43; peak shock difference -0.144 g (95% CI -0.187 to -0.100), t(284) = -6.46, p = 4.64e-10, d_z = -0.38; success rate -2.4 percentage points (exact McNemar p = 0.2664, 55 scenarios won only by the reference, 43 only by the other).
* **MPPI against APF + kerb logic** (250 paired scenarios, 145 reached by both): completion time difference +1.48 s (95% CI +0.66 to +2.30), t(144) = 3.57, p = 4.84e-04, d_z = +0.30; peak shock difference -0.484 g (95% CI -0.598 to -0.370), t(144) = -8.40, p = 3.87e-14, d_z = -0.70; success rate +9.6 percentage points (exact McNemar p = 0.0056, 23 scenarios won only by the reference, 47 only by the other).
* **PPO against APF + kerb logic** (500 paired scenarios, 326 reached by both): completion time difference -7.17 s (95% CI -8.20 to -6.15), t(325) = -13.78, p = 2.45e-34, d_z = -0.76; peak shock difference -0.160 g (95% CI -0.222 to -0.098), t(325) = -5.08, p = 6.50e-07, d_z = -0.28; success rate +19.6 percentage points (exact McNemar p = 3.69e-20, 14 scenarios won only by the reference, 112 only by the other).

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

### 6.5 Clinical outcome and economics
Under the larsen1993 model the rover (dispatched in parallel with the ambulance) changes expected survival by +1.3 percentage points (95% CI +1.2 to +1.5) relative to the ambulance alone (0.233); the interval excludes zero. It shocks strictly earlier than the ambulance in 38% of the 2000 simulated arrests, saving a median of 3.47 min in those. Break-even: the rover acting alone matches the ambulance acting alone at a straight-line radius of 584 m; beyond that the ambulance is expected to shock first. Scenario inputs recorded in the results file: rover_controller = ppo, response_radius_m = 500, crossings_per_km_ASSUMED = 4.0, route_factor = 1.54.

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

| Quantity | Value |
| :--- | ---: |
| Operating-burden ratio kappa | 0.220 |
| Course target | kappa <= 0.25 |
| Meets target | yes |
| Payback horizon (months) | 9.2 |
| Staff capacity freed, delta FTE | 0.50 |

### 6.6 Answer to the research question
**Conditional answer.** In this simulation study the rover dispatched in parallel with the ambulance does give a statistically clear survival gain (+1.3 percentage points, 95% CI +1.2 to +1.5, larsen1993 model), and the rover acting alone matches the ambulance acting alone at a straight-line radius of 584 m; beyond that the ambulance is expected to shock first. The answer depends on the ambulance response-time distribution and the dispatch assumptions of the scenario; it does not establish that urban ambulance delays are 15-20 minutes (the sourced Central Norway urban median is 10.0 min and 90th percentile 17.7 min, Naess et al. 2024), and it is not a statement about any Indian city.

### 6.7 Limitations
* Simulation only: rigid cylinder tyres, idealised lidar and terrain scan, Gaussian tracker noise, no drivetrain elasticity, no hardware-in-the-loop.
* Pedestrian behaviour follows a social-force model whose strengths are assumptions; the benchmark measures robustness to that model, not to real crowds.
* The clinical inputs are Western cohort data (King County for Larsen, Central Norway for response times); no claim is made about Mumbai or any Indian setting.
* Larsen's model is linear and was fitted on a high-survival subgroup; it is not valid for non-shockable rhythms or long delays.
* Physics is simulated per 36 m segment; a 1-2 km route is composed at the route level.
* Economics is a course template with placeholder ratios, undiscounted and single period.

---

## 7. Student Task Breakdown and Oral Defense Questions

Both students defend the whole system at a high level and their own modules in depth. The model answers below are generated from the shipped model and the result files, so every number matches this folder.


#### Student E026: Kashish Praveen Jain
* **Role:** Lead Autonomous Navigation & Traffic Congestion Modeling Specialist
* **Git branch:** `feat/e026-lead-autonomous-navi`
* **Owned modules:** `src/aedrover/nav/` (pure pursuit, APF, DWA, MPPI), `src/aedrover/control/safety_filter.py`, `src/aedrover/sim/pedestrians.py`, `src/aedrover/clinical/` (survival, ambulance delay, decision), `analytics/cardiac_survival_economics.py`.
* **Deliverables:** (i) the closed-loop navigation stack and its baselines, (ii) the pedestrian and crowd scenarios, (iii) the time-to-first-shock decomposition and the survival comparison, (iv) the paired statistical comparison of controllers. Each item needs at least four distinct feature commits on your branch (Standards Manual, section 5).

**Viva questions and model answers (true for this implementation)**

1. *Question:* State the Larsen et al. (1993) survival equation with its units, and explain what changes if the first shock is delivered four minutes earlier. What was wrong in the earlier draft?
   *Model answer:* Survival = 0.67 - 0.023 t_cpr - 0.011 t_defib - 0.021 t_acls, with each t in minutes from collapse (to CPR, to first shock, to advanced life support) and the result clipped to [0, 0.67]. The shock coefficient is 0.011 per minute, so with CPR at 3 min and ACLS at 10 min, moving the shock from 6 to 2 min raises survival by 4.4 percentage points. The earlier draft used 0.046 per minute for the shock term and no ACLS term; that value is not a coefficient of the published model and would have predicted 18.4 points for the same saving. The model was fitted to 1,667 King County patients with heart disease and witnessed ventricular fibrillation, a high-survival subgroup, so absolute values are optimistic and we use it mainly for differences. The 7-10% per minute in the project title is a guideline rule of thumb (Kim et al. (2026), doi 10.15441/ceem.26.073), not this model; on the same four-minute saving it gives 28 to 40 points, which is why both are reported.
2. *Question:* How does the DWA planner choose the speed and steering command, and why is the kerb negotiator an overlay rather than part of the planner?
   *Model answer:* Every 2 control steps it samples 9 speeds inside the dynamic window and 15 steering angles, rolls each pair out on a bicycle model for 2.4 s in steps of 0.15 s, drops candidates that cannot stop before contact with braking 2 m/s^2, and picks the highest score of progress, lane centring, speed, clearance and heading. Pedestrians enter through constant-velocity predictions of the tracker output. The kerb negotiator only caps the maximum speed using the measured minimum-climb-speed table plus a margin; keeping it separate lets the same overlay serve both APF and DWA and lets the benchmark measure what the kerb logic is worth ('with' and 'without' variants).
3. *Question:* What does the safety filter guarantee and what does it not?
   *Model answer:* It sweeps the 1.04 x 0.72 m footprint along the arc of the commanded steering angle, finds the first arc length d_free where the inflated footprint overlaps a lidar return or a tracked pedestrian, and clips the speed so that d_free - v t_react - v^2 / (2 a_brake) >= 0, with t_react = 0.1 s and a_brake = 2 m/s^2; it also caps the speed at 1.4 m/s within 3 m of a pedestrian. It only ever reduces speed. In the benchmark the APF + kerb logic controller, behind the safety filter, still had 21 collision episodes out of 500 (4.2%): the filter limits speed along the commanded arc, it does not choose the path, and it relies on a noisy tracker and a finite look-ahead, so pedestrians that step into the arc late can still be reached.
4. *Question:* What does MPPI plan with, and why is its internal model imperfect on purpose?
   *Model answer:* Every planning cycle (10 Hz) it samples 128 control sequences of 20 steps of 0.1 s, simulates all of them in a MuJoCo copy of the world with `mujoco.rollout` (contacts, suspension, isolator and wheel loops included) at a 0.01 s step, and averages the perturbations with exponential weights. The planner uses nominal friction 0.9 and payload 4 kg and has no pedestrians in its physics (they enter through predicted positions), whereas the environment randomises friction and payload. Planning against a perfect copy of the test world would overstate what a real controller can do.
5. *Question:* How is the time to first shock composed, and where does the simulated rover enter?
   *Model answer:* From collapse: ambulance = collapse-to-call + sampled response time (the response time already runs from the call); rover = collapse-to-call + call-to-alert + travel + hand-off. The package defaults for the non-travel delays are ASSUMPTIONS: 1 min to call, 1.5 min to alert the rover, 1 min for the bystander to take the AED and apply the pads, bystander CPR at 3 min. Travel is radius x route factor / speed (1.3); a measured travel time from the simulation can replace it. CPR and ACLS times are shared by all modes, so the device changes survival only through the shock term.
6. *Question:* Why paired tests, and what does the example from your results show?
   *Model answer:* Every controller runs the same seeded scenarios, so the natural unit is the scenario: differences within a scenario remove the large between-scenario variance (kerb height, friction, crowd). The paired t test on scenarios both controllers completed gives df, t, an exact p, d_z and a 95% interval of the mean difference; success uses an exact McNemar test on the discordant scenarios; Holm adjustment covers the family of t tests. The reference controller (APF + kerb logic) is chosen by a rule declared in advance, not after seeing the differences. Example from the results: Pure pursuit against APF + kerb logic on 232 scenarios that both completed, completion time difference -1.69 s, t(231) = -8.15, p = 2.37e-14, d_z = -0.53.


#### Student E046: Vaishnavi Parashar
* **Role:** MuJoCo Dynamic Chassis Modeler & Path Optimization Engineer
* **Git branch:** `feat/e046-mujoco-dynamic-chass`
* **Owned modules:** `src/aedrover/sim/vehicle_mjcf.py`, `src/aedrover/sim/world.py`, `src/aedrover/sim/validate.py`, `src/aedrover/sim/curb_study.py`, `src/aedrover/sim/codesign.py`, `src/aedrover/control/curb.py`, `models/aed_delivery_amr.xml`.
* **Deliverables:** (i) the parametric MJCF rover and terrain, (ii) the physics validation against closed-form mechanics, (iii) the kerb traversability study, (iv) the mechanical co-design. Each item needs at least four distinct feature commits on your branch.

**Viva questions and model answers (true for this implementation)**

1. *Question:* What are the suspension natural frequency and damping ratio of the nominal and the optimised rover, and how do you know the simulation matches them?
   *Model answer:* With the sprung mass per wheel m_s = (chassis + payload) / 4 = 6.50 kg, omega_n = sqrt(k_s / m_s) and zeta = c_s / (2 sqrt(k_s m_s)). Nominal: k_s = 4500 N/m and c_s = 350 N s/m give omega_n = 26.31 rad/s (4.19 Hz) and zeta = 1.023. Optimised: k_s = 2656.7 N/m and c_s = 151.6 N s/m give 20.22 rad/s (3.22 Hz) and zeta = 0.577. The ring-down validation reproduced the closed-form 2-DOF natural frequency within 0.25% and the damping ratio within 1.54% (3 fitted runs), and the effective tyre stiffness measured from static penetration is 313 kN/m. (The earlier draft quoted a tyre stiffness of 30 kN/m; the simulated contact stiffness is a calibrated property of the MuJoCo contact model, not a free choice, and is measured rather than assumed.)
2. *Question:* Why is the sidewalk terrain built from mocap bodies instead of static geoms?
   *Model answer:* MuJoCo builds the collision broad-phase tree of static bodies at compile time, so editing the pose of a static geom at run time silently has no effect on collisions. Every re-positionable piece (sidewalk slabs, ramps, obstacles, pedestrians) is therefore a mocap body with a fixed compile-time size that is only moved or rotated, and parked 50 m below the road when unused; `mj_resetData` restores mocap poses, so the world object re-applies its authoritative poses after every reset. This makes a scenario reset cost microseconds instead of a recompile. The shipped file `models/aed_delivery_amr.xml` places the two slabs at compile time so that it loads with plain `mujoco.MjModel.from_xml_path`.
3. *Question:* Why does a kerb need an approach speed, and what do your results say about it?
   *Model answer:* In the kerb study the minimum climbing speed at a 12 cm kerb (friction 1) is 1.0 m/s (nominal) and 1.0 m/s (optimised) with a peak payload shock of 2.90 g and 1.93 g; nothing in the grids succeeded at the slowest scanned speed of 0.4 m/s, so climbing is momentum-driven and the shock rises with the speed that momentum requires. The quasi-static picture explains why: pressed against a step of height h a rigid wheel of radius r has an edge-contact direction at angle phi above the horizontal with tan(phi) = (r - h) / sqrt(2 r h - h^2); the smaller phi is, the more horizontal drive force (about W / tan(phi) for the wheel load W) is needed to lift the wheel, and it approaches infinity as h approaches r. For h = 0.12 m this angle is 11.5 degrees for the nominal wheel and 26.8 degrees for the optimised wheel, so a slow approach cannot lift the wheel with the available torque and the rover uses kinetic energy instead.
4. *Question:* What did the co-design change, and what did it cost?
   *Model answer:* Objective 6.06 g to 3.09 g; conditions within the 3 g budget 25% to 88%; wheel radius 0.150 m to 0.219 m; suspension zeta_s 1.023 to 0.577; isolator natural frequency 23.45 to 13.42 rad/s. The price: unsprung mass per wheel grows from 2.25 kg to 4.35 kg and total mass from 35.0 kg to 43.4 kg (wheel and hub-motor mass follows an engineering-estimate model, an ASSUMPTION).
5. *Question:* How is payload shock defined, and why does a softer isolator lower it?
   *Model answer:* The payload accelerometer measures proper acceleration, which reads +g along the local up at rest; the shock is the magnitude of a_dyn = a_proper - g u_body (u_body is world-up expressed in the chassis frame, so pitch and roll do not leak in), passed through a zero-phase 4th-order Butterworth low-pass at 80 Hz, and the peak is reported in g against a 3 g budget (a design assumption of this project; no standard is applied). The isolator is a spring-damper on three slide joints: with payload mass 4 kg, k_p = 2200 N/m and c_p = 180 N s/m give omega = 23.45 rad/s and zeta = 0.959; the optimised k_p = 720 N/m and c_p = 50 N s/m give 13.42 rad/s and 0.468. A lower isolator frequency filters more of the kerb impulse before it reaches the payload, at the price of a larger payload stroke (limited to +/-5 cm by the joint range).
6. *Question:* How is contact friction stability handled in the simulation, and what happens on slippery ground?
   *Model answer:* The model uses `cone="pyramidal"` friction cones, the `implicitfast` integrator, a 0.002 s physics step and 30 solver iterations; the tyre contact softness is set by `solref` = (0.03, 1) and tyre friction is written per episode into the model arrays (scenario friction 0.7-1.1 normally, lower in the slippery family). Long soak runs keep the state finite. At friction 0.5 the 16 cm kerb needs 2.2 m/s for the optimised rover (peak 4.97 g) and cannot be climbed by the nominal rover within the scanned speeds.


---

## 8. Minimum Viable Deliverables and Student Work Scope

1. **`models/aed_delivery_amr.xml`:** four-wheel independent suspension rover, kerb crossing and isolated payload (shipped, compiles with plain MuJoCo).
2. **`src/aed_navigation_controller.py`:** working entry point that runs the DWA and MPPI controllers from the vendored package and can log telemetry.
3. **`analytics/aed_delivery_benchmark.csv`:** real simulation episodes, at least 80 rows (this folder ships 2250).
4. **`docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md`:** four-page manuscript with all sections drafted and the results filled in; students must verify and rewrite it.

---

## 9. Reproduction

```powershell
pip install mujoco numpy scipy pandas matplotlib pyyaml gymnasium
python src/test_env.py
python src/aed_navigation_controller.py --controllers dwa --family kerb --seed 5000 --telemetry analytics/kerb_crossing_telemetry.csv
python analytics/generate_paper_figures.py
python analytics/cardiac_survival_economics.py
```

The benchmark CSV comes from the research repository's controller-benchmark experiment; a single row can be replayed with the entry point (identical scenario and controller; small differences appear if the simulator code changed after the benchmark was run).

---

## 10. Data Provenance

| Result | Source file | Content | SHA-256 (first 12 hex) |
| :--- | :--- | :--- | :--- |
| physics validation | `results/validation_optimized.json` | 3 ring-down and 3 rolling runs | `c793c40d4b7e` |
| kerb traversability (nominal) | `results/curb_traversability_nominal_standard.csv` | 6048 trials | `5988195070db` |
| kerb climb windows (nominal) | `results/curb_window_nominal_standard.json` | 144 cells | `ae562ec2100a` |
| kerb traversability (optimized) | `results/curb_traversability_optimized_standard.csv` | 1512 trials | `32840ba16b75` |
| kerb climb windows (optimized) | `results/curb_window_optimized_standard.json` | 36 cells | `8715bf84a5d3` |
| mechanical co-design | `results/codesign.json` | 1116 evaluations, 30 generations | `2826efb7f13e` |
| controller benchmark | `results/benchmark_standard.csv` | 2250 episodes, controllers ['apf', 'dwa', 'mppi', 'ppo', 'pure_pursuit'] | `afa81b03d378` |
| clinical survival by mode | `results/clinical_survival_vs_radius.csv` | 6 rows at 500 m, controller ppo | `7d05cb285f75` |
| clinical and economics | `results/clinical.json` | 6 mode rows, model larsen1993 | `4bf8e8b7f9a2` |

Telemetry replay check: replayed benchmark episode (dwa, kerb, seed 5000): outcome goal (benchmark goal), time 21.72 s (benchmark 21.72 s), episode peak shock 2.15 g (benchmark 2.21 g). The replay reproduces the benchmark row.
