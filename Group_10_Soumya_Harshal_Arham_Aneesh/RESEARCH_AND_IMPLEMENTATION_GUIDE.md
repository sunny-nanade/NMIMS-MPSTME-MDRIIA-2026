# Research and Implementation Guide: 7-DOF Surgical Manipulator with Tremor Filtering

## Project: MDRIIA Group 10
## Target Venue: IEEE TBME / IEEE CASE / AIR Conference Track

---

## 1. Mathematical and Algorithmic Formulation

### 1.1 Redundant 7-DOF Kinematics & Damped Least Squares (DLS)
The 7-DOF manipulator possesses kinematically redundant degrees of freedom for 6-DOF task space positioning:

$$x_e = f(q), \quad q = [q_1, q_2, \dots, q_7]^T \in \mathbb{R}^7, \quad x_e \in SE(3)$$

The relationship between end-effector velocity $\dot{x}_e$ and joint velocities $\dot{q}$ is:

$$\dot{x}_e = J(q) \dot{q}, \quad J(q) \in \mathbb{R}^{6 \times 7}$$

Near kinematic singularities, standard pseudoinverse inversion $J^\dagger = J^T (J J^T)^{-1}$ produces unbounded joint velocities. To guarantee bounded, smooth control, we employ Damped Least Squares (Levenberg-Marquardt):

$$J^* = J^T (J J^T + \lambda^2 I)^{-1}$$

where $\lambda$ is dynamically adjusted using the manipulability measure $w(q) = \sqrt{\det(J J^T)}$:

$$\lambda^2 = \begin{cases} 0 & \text{if } w(q) \ge w_0 \\ \lambda_0^2 \left(1 - \frac{w(q)}{w_0}\right)^2 & \text{if } w(q) < w_0 \end{cases}$$

Joint velocities are then computed with null-space projection for secondary joint limit avoidance:

$$\dot{q} = J^* (\dot{x}_{\text{des}} + K_p (x_{\text{des}} - x_e)) + (I - J^* J) \dot{q}_{\text{null}}$$

### 1.2 Physiological Hand Tremor Signal Modeling
Surgeon hand tremor combines voluntary movement with an involuntary narrowband physiological oscillation centered between 8 Hz and 12 Hz:

$$p_{\text{surgeon}}(t) = p_{\text{voluntary}}(t) + p_{\text{tremor}}(t)$$

$$p_{\text{tremor}}(t) = \sum_{k=1}^{M} A_k \sin(2\pi f_k t + \phi_k) + \eta(t)$$

where $f_k \in [8.0, 12.0]$ Hz, $A_k \sim \mathcal{N}(0.45, 0.12)$ mm, and $\eta(t)$ is Gaussian white noise.

### 1.3 Discrete-Time Low-Pass Filtering & Phase Delay Constraint
To suppress the 8-12 Hz tremor without introducing destabilizing latency into surgical teleoperation, the filter must satisfy a strict phase delay constraint:

$$\tau_{\text{lag}} = -\left. \frac{d\phi(\omega)}{d\omega} \right|_{\omega \to 0} \le 25 \text{ ms}$$

A 2nd-order Butterworth low-pass digital filter is implemented:

$$H(z) = \frac{b_0 + b_1 z^{-1} + b_2 z^{-2}}{1 + a_1 z^{-1} + a_2 z^{-2}}$$

with cutoff frequency $f_c = 3.5$ Hz, providing over $18$ dB of attenuation across the 8-12 Hz band.

### 1.4 Needle Placement Accuracy Benchmark
Needle tip position error $e_i = \|p_{\text{tip}}(i) - p_{\text{target}}\|$ is evaluated across $N$ discrete time samples:

$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} e_i^2} \le 0.50 \text{ mm}$$

### 1.5 CSBS Operating Room Clinical Economics
Clinical economic impact is formulated as dimensionless cost parity $\kappa$:

$$\kappa = \frac{\text{OpEx}_{\text{robot}}}{\text{OpEx}_{\text{conventional}}} = \frac{C_{\text{maintenance}} + C_{\text{sterilization}} + C_{\text{technician}}}{C_{\text{revision\_procedures}} + C_{\text{or\_delay\_overhead}}}$$

The capital amortization payback horizon in operational months is:

$$\text{Payback Months} = \frac{K_{\text{capex}}}{1 - \kappa} \times 12$$

---

## 2. Individual Student Work Boundaries & Responsibilities

```
===================================================================================================
Student Roll & Name        Assigned Technical Module                       Primary Deliverable
===================================================================================================
E071 - Soumya Singh        7-DOF Kinematics & Damped Least Squares IK      models/surgical_7dof_robot.xml
                                                                           (MJCF Robot & DLS IK Engine)
E033 - Harshal Khandekar   DSP Tremor Modeling & Digital Filtering         src/surgical_tremor_controller.py
                                                                           (8-12 Hz Generator & Filter)
E069 - Arham Khan          Needle Placement Accuracy & Telemetry           src/surgical_tremor_controller.py
                                                                           (Sub-0.5 mm RMSE Calibration)
E076 - Aneesh Kumar        CSBS Operating Room Economics & Utilization     analytics/surgical_or_economics.py
                                                                           (OR Payback & Revision Model)
===================================================================================================
```

### 2.1 E071 - Soumya Singh (Kinematics & DLS IK)
- Build the 7-DOF articulated robot arm MJCF XML model with anatomically appropriate link lengths and joint limits.
- Implement singularity-robust Damped Least Squares inverse kinematics with null-space optimization.
- **Git Branch:** `feat/e071-lead-surgical-kinema`

### 2.2 E033 - Harshal Khandekar (DSP Tremor & Filtering)
- Implement the 8-12 Hz physiological tremor signal synthesizer.
- Design and tune the 2nd-order Butterworth / exponential smoothing low-pass filter satisfying $\tau < 25$ ms.
- **Git Branch:** `feat/e033-digital-signal-proce`

### 2.3 E069 - Arham Khan (Accuracy & Telemetry)
- Formulate target tissue registration and needle tip positioning error metrics.
- Record 3D trajectory telemetry and verify sub-0.5 mm RMSE under simulated physiological tremor.
- **Git Branch:** `feat/e069-end-effector-precisi`

### 2.4 E076 - Aneesh Kumar (CSBS OR Economics)
- Formulate operating room throughput models and procedure revision avoidance analytics.
- Execute statistical hypothesis tests (Student's t-test, Cohen's d).
- Compute dimensionless OpEx savings and capital payback horizons across surgical case volumes.
- **Git Branch:** `feat/e076-csbs-surgical-clinic`

---

## 3. Step-by-Step Implementation Roadmap

1. **Sprint 0: Setup & Verification**
   - Run `python src/test_env.py` to confirm Python 3.9+, NumPy, SciPy, and Matplotlib.
   - Compile `models/surgical_7dof_robot.xml` in MuJoCo.
2. **Sprint 1: Forward Kinematics & DLS Inversion**
   - Verify 7-DOF forward kinematics and Jacobian matrix rank.
   - Run reaching trajectories across surgical workspace limits without singularity blow-ups.
3. **Sprint 2: Tremor Simulation & Filter Evaluation**
   - Run `python src/surgical_tremor_controller.py` to compare unfiltered vs filtered needle trajectories.
   - Confirm tremor attenuation $> 15$ dB with phase latency $< 25$ ms.
4. **Sprint 3: Benchmarking and Economics Simulation**
   - Run `python analytics/generate_paper_figures.py` to produce benchmark CSV and 300 DPI figures.
   - Run `python analytics/surgical_or_economics.py` to evaluate operating room economics.
5. **Sprint 4: Paper Preparation & Git Push**
   - Draft manuscript sections using `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md`.
   - Run audit script to guarantee zero emojis, zero currency, and strict compliance.
