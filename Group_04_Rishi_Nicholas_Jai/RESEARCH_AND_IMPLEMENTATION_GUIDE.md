# Research & Implementation Guide: Multi-Arm Space Debris Gripper in LEO
## Modern Day Robotics & Its Industrial Applications (MDRIIA)
**Project Title:** How can a multi-arm robotic gripper mechanism simulated in MuJoCo utilize impedance contact control to synchronize with and capture tumbling non-cooperative orbital debris in LEO while mitigating collision impulse and momentum transfer?  
**Group ID:** MDRIIA Group 04  

---

## 1. Executive Scientific Problem Deconstruction

Active Debris Removal (ADR) in Low Earth Orbit (LEO) is an urgent technical prerequisite for sustainable orbital commercialization. Capturing an uncooperative, tumbling target presents severe dynamic risks:
1. **Dynamic Contact Rebound:** In zero gravity, unanchored contact produces an impulse $J = \int F dt$ that pushes the debris away with velocity $\Delta v = J / m_{\text{tgt}}$.
2. **Base Reaction Disturbance:** Moving robotic arms on a free-floating servicer bus induces equal and opposite momentum transfers on the servicer ($I_b \dot{\boldsymbol{\omega}}_b + \sum \boldsymbol{\tau}_{\text{arm}} = 0$), destabilizing sensor tracking.
3. **Collision Impulse Shock:** Stiff position control causes destructive stress on robotic joints and risk of debris structural fragmentation.

This project designs and simulates a dual-arm space robot in MuJoCo operating under Cartesian operational space impedance control to synchronize with tumbling debris, absorb contact energy, and lock the target with minimal reaction disturbance.

---

## 2. Mathematical Formulations & Physical Modeling

### 2.1 Relative Orbital Kinematics (Hill-Clohessy-Wiltshire Equations)
In the Local Vertical Local Horizontal (LVLH) frame centered on the target debris orbit:

$$\ddot{x} - 2\omega_o \dot{z} = \frac{f_x}{m_c}$$

$$\ddot{y} + \omega_o^2 y = \frac{f_y}{m_c}$$

$$\ddot{z} + 2\omega_o \dot{x} - 3\omega_o^2 z = \frac{f_z}{m_c}$$

Where $\omega_o = \sqrt{\mu / R_o^3}$ is the orbital mean motion at radius $R_o = 7000\text{ km}$ ($h \approx 622\text{ km}$ LEO), and $m_c = 180.0\text{ kg}$ is the servicer spacecraft mass.

### 2.2 Tumbling Target Attitude Dynamics (Euler's Rotational Equations)
The tumbling target is modeled as an asymmetric rigid body ($m_{\text{tgt}} = 28.0\text{ kg}$) with inertia tensor $\mathbf{I}_{\text{tgt}} = \text{diag}(1.45, 1.85, 0.95)\text{ kg}\cdot\text{m}^2$:

$$\mathbf{I}_{\text{tgt}} \dot{\boldsymbol{\omega}}_{\text{tgt}} + \boldsymbol{\omega}_{\text{tgt}} \times (\mathbf{I}_{\text{tgt}} \boldsymbol{\omega}_{\text{tgt}}) = \mathbf{0}$$

Initial tumble rates range from $\omega_0 = 2.0^\circ/\text{s}$ to $15.0^\circ/\text{s}$.

### 2.3 Cartesian Operational Space Impedance Contact Control
The target dynamic interaction relationship between the robotic end-effector and target debris is governed by:

$$\mathbf{M}_d (\ddot{\mathbf{x}} - \ddot{\mathbf{x}}_d) + \mathbf{D}_d (\dot{\mathbf{x}} - \dot{\mathbf{x}}_d) + \mathbf{K}_d (\mathbf{x} - \mathbf{x}_d) = \mathbf{F}_{\text{ext}}$$

Where:
* $\mathbf{M}_d = \text{diag}(4.0, 4.0, 4.0)\text{ kg}$ is the virtual desired inertia.
* $\mathbf{D}_d = \text{diag}(120.0, 120.0, 120.0)\text{ N}\cdot\text{s/m}$ is the virtual damping matrix.
* $\mathbf{K}_d = \text{diag}(350.0, 350.0, 350.0)\text{ N/m}$ is the virtual stiffness matrix.
* The damping ratio $\zeta = \frac{D_d}{2\sqrt{M_d K_d}} = \frac{120.0}{2\sqrt{4.0 \times 350.0}} \approx 1.60$ (overdamped to prevent bounce).

Joint actuator torques are computed via the transposed Jacobian:

$$\boldsymbol{\tau} = \mathbf{J}^T \left( \mathbf{K}_d (\mathbf{x}_d - \mathbf{x}) + \mathbf{D}_d (\dot{\mathbf{x}}_d - \dot{\mathbf{x}}) \right) + \mathbf{C}(\mathbf{q}, \dot{\mathbf{q}})$$

### 2.4 Free-Floating Base Coupling (Generalized Jacobian Matrix)
Because the servicer bus is unanchored in microgravity, moving the arms exerts reaction forces on the bus:

$$\mathbf{v}_{ee} = \mathbf{J}_g \dot{\mathbf{q}}$$

$$\mathbf{J}_g = \mathbf{J}_m - \mathbf{J}_b \mathbf{I}_b^{-1} \mathbf{I}_{bm}$$

Where reaction wheels on the servicer apply internal torques $\boldsymbol{\tau}_{rw} = -\mathbf{K}_{rw} \boldsymbol{\theta}_b - \mathbf{D}_{rw} \boldsymbol{\omega}_b$ to desaturate momentum and keep base attitude disturbance $|\Delta \theta_b| \le 3.5^\circ$.

### 2.5 Dimensionless CSBS Commercial Space Economics Model
To maintain compliance with CSBS guidelines without raw currency values:
* Multi-Target Amortization Efficiency ($\Gamma_{\text{multi}}$):
  $$\Gamma_{\text{multi}} = \frac{N_{\text{serviced}} \times P_{\text{capture}}}{1.0 + \kappa_{\text{prop}} \cdot N_{\text{serviced}}}$$
  Where $\kappa_{\text{prop}} = 0.08$ is the fractional delta-v propellant consumption per orbital rendezvous.
* Constellation Asset Value Preservation Index ($\Psi_{\text{constellation}}$):
  $$\Psi_{\text{constellation}} = 1.0 - \exp(-\lambda_{\text{Kessler}} \cdot N_{\text{removed}})$$
  Where $\lambda_{\text{Kessler}} = 0.045$ represents the collision probability reduction factor per removed debris object.

---

## 3. Student Task Breakdown and Oral Defense Questions

### 3.1 Student E034 - Rishi Vinod Koli
* **Assigned Role:** Lead Orbital Dynamics & MuJoCo Multi-Body Physics Architect
* **Git Branch:** `feat/e034-lead-orbital-dynamic`
* **Core Technical Responsibility:** Develop the zero-gravity MuJoCo simulation (`models/space_debris_gripper.xml`). Model free-floating 6-DOF joints for servicer and debris, parameterize asymmetric inertia tensors, and tune viscoelastic fingertip contact properties (`solref`, `solimp`).
* **Viva Defense Questions:**
  1. *Question:* Why does a standard rigid penalty contact solver fail in zero gravity, and how do `solref` and `solimp` in MuJoCo prevent target ejection?  
     *Model Answer:* In zero gravity, there are no gravitational normal forces to maintain contact. A standard rigid solver creates instantaneous impulse spikes ($J = \int F dt$) that act as elastic rebound kicks, accelerating unanchored debris away at velocity $\Delta v = J / m$. MuJoCo regularizes constraints using Kelvin-Voigt contact viscoelasticity parameterized by `solref` (time constant and damping ratio) and `solimp` (impedance width). Setting a high damping ratio ($\zeta \ge 1.0$) transforms the collision into an energy-dissipating plastic interaction, preventing rebound.
  2. *Question:* How do you model non-cooperative tumbling in MuJoCo, and why does intermediate axis rotation exhibit the Dzhanibekov effect?  
     *Model Answer:* We assign an asymmetric inertia tensor ($I_{xx} < I_{yy} < I_{zz}$) to the debris body and initialize angular velocity $\boldsymbol{\omega}_0$ with components along the intermediate axis ($y$). According to Euler's equations, rotation about the maximum and minimum inertia axes is Lyapunov stable, but rotation about the intermediate axis is unstable, leading to periodic 180-degree flips (the Dzhanibekov effect or Tennis Racket theorem), which simulates realistic non-cooperative satellite tumble.

### 3.2 Student E035 - Nicholas Lewis
* **Assigned Role:** Impedance Contact Control & Robotic Kinematics Engineer
* **Git Branch:** `feat/e035-impedance-contact-co`
* **Core Technical Responsibility:** Implement Cartesian impedance control in `src/debris_capture_controller.py`. Derive geometric Jacobians, formulate trajectory phase synchronization with the tumbling target fixture, and execute contact force absorption.
* **Viva Defense Questions:**
  1. *Question:* Contrast Cartesian operational space impedance control against standard joint-space PD control during the capture of a tumbling satellite?  
     *Model Answer:* Joint-space PD control tracks precomputed joint angles with constant, high dynamic stiffness. When striking a tumbling body with kinematic phase error, the arm resists deflection with maximum motor torque, generating extreme impact forces that damage joints or push the debris away. Operational space impedance control treats the end-effector as a tunable mass-spring-damper ($M_d, D_d, K_d$). Upon contact, the arm compliant yields, absorbing kinetic energy and matching the target's surface velocity before closing the gripper fingers.
  2. *Question:* How does the Generalized Jacobian Matrix (GJM) account for spacecraft base motion when the robotic arms articulate?  
     *Model Answer:* For a free-floating manipulator without external anchoring, arm motions generate reaction forces and torques that displace and rotate the spacecraft base according to total momentum conservation ($L_{\text{total}} = \text{const}$). The Generalized Jacobian $\mathbf{J}_g = \mathbf{J}_m - \mathbf{J}_b \mathbf{I}_b^{-1} \mathbf{I}_{bm}$ maps joint velocities directly to inertial end-effector velocity while implicitly accounting for the dynamic recoil of the base.

### 3.3 Student E036 - Jai Maini
* **Assigned Role:** CSBS Commercial Space Economics & Satellite De-Orbiting Business Analyst
* **Git Branch:** `feat/e036-csbs-commercial-spac`
* **Core Technical Responsibility:** Implement the commercial space economics model in `analytics/constellation_economics.py`. Evaluate multi-target ADR sortie economics, Kessler syndrome collision risk reduction, and regulatory compliance without currency metrics.
* **Viva Defense Questions:**
  1. *Question:* How does mitigating peak contact force in simulation translate to commercial space mission feasibility?  
     *Model Answer:* In space logistics, peak contact force governs structural mass requirements and capture abort risks. High impact forces require heavier gripper links and higher-torque actuators, inflating spacecraft mass and launch costs. Furthermore, high impact risks shattering fragile solar panels or multi-layer insulation (MLI), creating thousands of untrackable lethal fragments. Minimizing contact impulse via impedance control directly reduces mission risk ($P_{\text{fail}}$) and preserves the servicer's reusable lifespan across multiple capture sorties.
  2. *Question:* How do international de-orbiting regulations (such as the FCC 5-year post-mission disposal rule) impact constellation commercial viability?  
     *Model Answer:* Regulators require commercial constellation operators to remove non-functional satellites within 5 years to maintain their orbital spectrum licenses. In our dimensionless model, failure to comply introduces a regulatory risk penalty factor that threatens the operator's entire constellation revenue. Autonomous ADR services provide a verified compliance mechanism that de-risks regulatory license forfeiture.

---

## 4. Minimum Viable Deliverables and Student Work Scope

To complete the project, the student team must commit the following:

1. **`models/space_debris_gripper.xml`:** Verified zero-G MJCF model with servicer bus, dual 3-DOF arms, and asymmetric tumbling target.
2. **`src/debris_capture_controller.py`:** Working implementation of `# TODO` blocks for trajectory phase synchronization, impedance contact control, and reaction wheel stabilization.
3. **`analytics/space_debris_capture_benchmark.csv`:** Real simulation telemetry dataset generated from at least 80 experimental runs.
4. **`docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md`:** Completed 4-page conference manuscript with student findings and populated data tables.
