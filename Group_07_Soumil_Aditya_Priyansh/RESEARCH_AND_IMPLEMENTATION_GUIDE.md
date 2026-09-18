# Research and Implementation Guide: Autonomous Hospital Clutter Mobile Manipulator

## Project: MDRIIA Group 07
## Target Venue: IEEE CASE / IEEE ICRA / AIR Conference Track

---

## 1. Mathematical and Algorithmic Formulation

### 1.1 Mobile Manipulator Kinematics
The system consists of a mobile base possessing 3 degrees of freedom in SE(2) and an articulated manipulator with $n = 4$ to $6$ revolute joints. The combined generalized state vector is:

$$q = [x_b, y_b, \theta_b, q_1, q_2, \dots, q_n]^T \in \mathbb{R}^{3+n}$$

The operational end-effector pose $x_e = [p_e^T, \phi_e^T]^T \in SE(3)$ is related to joint velocities via the system Jacobian matrix $J(q)$:

$$\dot{x}_e = J(q) \dot{q} = \begin{bmatrix} J_{\text{base}}(q) & J_{\text{arm}}(q) \end{bmatrix} \begin{bmatrix} \dot{q}_{\text{base}} \\ \dot{q}_{\text{arm}} \end{bmatrix}$$

To prevent algorithmic singularities during reaching trajectories near bedside boundaries, the controller employs Damped Least Squares (Levenberg-Marquardt) inverse kinematics:

$$\dot{q} = J^T (J J^T + \lambda^2 I)^{-1} (\dot{x}_{\text{des}} + K_p (x_{\text{des}} - x_e))$$

where $\lambda$ is the damping factor dynamically scaled by the manipulability index $w = \sqrt{\det(J J^T)}$:

$$\lambda^2 = \begin{cases} 0 & \text{if } w \ge w_0 \\ \lambda_{\max}^2 \left(1 - \frac{w}{w_0}\right)^2 & \text{if } w < w_0 \end{cases}$$

### 1.2 Grasp Quality Metric and Contact Mechanics
The parallel-jaw gripper applies normal gripping forces $F_n$ at contact points. To ensure stable prehension without slipping or crushing delicate clinical items:

$$F_{\text{tangential}} \le \mu F_n$$

where $\mu$ is the Coulomb friction coefficient between the silicone gripper pads and the object material. The antipodal grasp condition requires:

$$\mathbf{n}_1 \cdot \mathbf{n}_2 \le -\cos(2 \arctan \mu)$$

where $\mathbf{n}_1, \mathbf{n}_2$ are the inward-pointing surface normal vectors at the contact patches.

### 1.3 Hospital Room Turnaround Time Reduction Model
Baseline manual room cleaning latency $T_{\text{manual}}$ is decomposed into clutter removal and terminal clinical disinfection:

$$T_{\text{manual}} = T_{\text{clutter\_manual}} + T_{\text{disinfect\_manual}}$$

With the autonomous mobile manipulator deployed, clutter is cleared autonomously during the patient discharge and linen stripping phase:

$$T_{\text{turnaround\_robot}} = \max(T_{\text{clutter\_robot}}, T_{\text{linen}}) + T_{\text{disinfect\_targeted}}$$

Because housekeeping staff are liberated from sorting scattered personal effects, discarded cups, and packaging, their disinfection focus is sharper and surface omission rate drops significantly.

### 1.4 CSBS Technoeconomic Operational Cost Parity
To evaluate financial feasibility without arbitrary currency assumptions, operational cost is formulated as a dimensionless ratio $\kappa$:

$$\kappa = \frac{\text{OpEx}_{\text{robot}}}{\text{OpEx}_{\text{manual}}} = \frac{C_{\text{energy}} + C_{\text{maintenance}} + C_{\text{supervision}}}{C_{\text{labor}}}$$

The dimensionless capital amortization payback horizon in months is:

$$\text{Payback Months} = \frac{K_{\text{capex}}}{1 - \kappa} \times 12$$

---

## 2. Individual Student Work Boundaries & Responsibilities

```
===================================================================================================
Student Roll & Name        Assigned Technical Module                       Primary Deliverable
===================================================================================================
E050 - Soumil Patro        Mobile Base Navigation, SLAM & Motion Planning  src/clutter_manipulator_controller.py
                                                                           (Base Navigation Module)
E062 - Aditya Raju Shah    Manipulator Kinematics & Grasp Planning         src/clutter_manipulator_controller.py
                                                                           (IK, Gripper & State Machine)
E066 - Priyansh Thakkar    CSBS Room Turnaround & Econometric Modeling     analytics/nosocomial_turnover_economics.py
                                                                           (Queuing & Payback Model)
===================================================================================================
```

### 2.1 E050 - Soumil Patro (Mobile Base Navigation)
- Implement mobile base localization, bedside waypoint navigation, and collision-free base repositioning.
- Tune the kinematic control law that rotates and translates the mobile platform into optimal arm workspace range.
- **Git Branch:** `feat/e050-lead-mobile-base-nav`

### 2.2 E062 - Aditya Raju Shah (Arm Kinematics & Grasping)
- Formulate the 6-DOF / 4-DOF manipulator kinematic chain in `hospital_clutter_manipulator.xml`.
- Implement closed-loop inverse kinematics with singularity damping and parallel-jaw grasp actuation.
- Develop the pick-and-place state machine (approach, close gripper, lift, carry to bin, open gripper).
- **Git Branch:** `feat/e062-manipulator-arm-kine`

### 2.3 E066 - Priyansh Thakkar (CSBS Healthcare Economics)
- Formulate the hospital room turnover model and evaluate bed availability expansion.
- Execute empirical statistical analyses (paired t-test, Cohen's d, boxplot distributions).
- Compute dimensionless OpEx savings and payback horizons across varying room turnover volumes.
- **Git Branch:** `feat/e066-csbs-hospital-workfl`

---

## 3. Step-by-Step Implementation Roadmap

1. **Sprint 0: Setup & Verification**
   - Run `python src/test_env.py` to confirm Python 3.9+, NumPy, SciPy, and Matplotlib.
   - Inspect `models/hospital_clutter_manipulator.xml` in MuJoCo viewer (`python -m mujoco.viewer --mjcf=models/hospital_clutter_manipulator.xml`).
2. **Sprint 1: Base Positioning & Manipulator Workspace**
   - Run baseline kinematic trajectories for arm joints.
   - Verify that the end-effector reaches bedside table clutter without self-collision.
3. **Sprint 2: Closed-Loop Grasping Execution**
   - Run `python src/clutter_manipulator_controller.py` to execute automated picking runs.
   - Record grasp success rates and end-effector tracking errors.
4. **Sprint 3: Benchmarking and Economics Simulation**
   - Run `python analytics/generate_paper_figures.py` to produce benchmark CSV and 300 DPI figures.
   - Run `python analytics/nosocomial_turnover_economics.py` to evaluate hospital room turnaround metrics.
5. **Sprint 4: Paper Preparation & Git Push**
   - Draft manuscript sections using `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md`.
   - Audit code and documentation to ensure strict compliance with publication guidelines.
