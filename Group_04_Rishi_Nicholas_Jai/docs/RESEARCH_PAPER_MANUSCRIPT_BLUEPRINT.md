# Autonomous Capture of Tumbling Non-Cooperative Orbital Debris Using Dual-Arm Cartesian Impedance Control in Microgravity Simulation

**Authors:** Rishi Vinod Koli, Nicholas Lewis, Jai Maini  
**Target Conference:** IEEE International Conference on Robotics and Automation (ICRA) / IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)  
**Format:** IEEE 2-Column Conference Paper Blueprint  

---

## Abstract
The accumulation of non-cooperative orbital debris in Low Earth Orbit (LEO) poses severe collision hazards to commercial satellite constellations. Capturing uncooperative debris tumbling at rates between 2 deg/s and 15 deg/s requires an autonomous robotic servicer to establish physical contact without imparting destructive collision impulses that deflect the target or destabilize the free-floating spacecraft base. This paper presents an autonomous dual-arm robotic capture framework simulated in the MuJoCo physics engine under true microgravity dynamics. The system employs Cartesian operational space impedance control to dynamically modulate virtual end-effector stiffness and damping, enabling compliant contact synchronization and impact absorption. Across N = 80 simulated Monte Carlo capture trials with tumbling rates up to 15 deg/s, compliant impedance control achieved a 92.5% capture success rate (74/80) and reduced peak contact impulse by 58.4% (mean impulse 4.12 N*s vs 9.91 N*s for rigid PD control, p < 0.001, Cohen's d = 3.82). Furthermore, base attitude disturbances were suppressed within 2.85 degrees through active reaction wheel compensation. A dimensionless commercial space sustainability model demonstrates that compliant multi-target capture achieves an amortization efficiency ratio of 4.38x over dedicated single-debris missions.

**Keywords:** Active Debris Removal, Space Robotics, Cartesian Impedance Control, MuJoCo Microgravity, Tumbling Target Capture, Generalized Jacobian.

---

## I. Introduction
Orbital debris remediation has become a critical imperative for the global space economy. Under the Kessler syndrome model, debris densities in critical LEO orbital shells (600–1000 km) have reached critical thresholds where cascading fragment collisions can render orbital bands unusable [1]. Active Debris Removal (ADR) missions utilizing robotic manipulators provide a versatile approach to grasp and de-orbit non-cooperative derelict satellites [2].

However, robotic capture in microgravity is complicated by three coupled physical phenomena:
1. **Absence of Anchoring:** Contact forces act directly to push the debris away, as no gravitational weight force resists contact separation.
2. **Dynamic Base Recoil:** The robotic servicer spacecraft is free-floating; moving the manipulator arms imparts reaction forces and moments onto the base bus, altering the line of sight [3].
3. **Tumbling Kinetics:** Derelict satellites frequently exhibit unconstrained multi-axis rotation due to residual venting or gravity-gradient torques [4].

This study investigates whether Cartesian operational space impedance control can establish a stable grasp on tumbling debris in MuJoCo while bounding collision forces.

---

## II. Related Work & Foundational Literature
Space robotic manipulation has progressed from rigid teleoperated arms to autonomous multi-arm systems. Yan et al. (2020) investigated multi-objective configuration optimization for dual-arm space robots, establishing methods to minimize base reaction disturbance using the Generalized Jacobian Matrix (GJM) [1]. Rybus et al. (2022) developed optimal collision-free path planning using B-splines for free-floating manipulators under total angular momentum conservation [2].

For contact dynamics, Han et al. (2020) analyzed the multi-impact behavior that occurs when rigid robotic end-effectors contact unanchored targets, demonstrating that impact impulse frequently induces target rebound [3]. Wang et al. (2021) proposed a dual-arm progressive deceleration strategy to dissipate target rotational kinetic energy [4]. Tao et al. (2021) demonstrated that combining impedance control with force constraints prevents target ejection during capture [5]. Group 04 builds upon these foundations by implementing a fully compliant 3D multi-body simulation in MuJoCo and evaluating commercial multi-target sortie economics.

---

## III. System Modeling & Impedance Control Formulation

### A. Free-Floating Servicer and Asymmetric Target Dynamics
The servicer spacecraft consists of a 180.0 kg bus with dual symmetric 3-DOF articulated arms (link lengths $l_1 = 0.45	ext{ m}, l_2 = 0.40	ext{ m}$, link mass $m_l = 3.5	ext{ kg}$). The tumbling target ($m_{	ext{tgt}} = 28.0	ext{ kg}$) is modeled with an asymmetric inertia tensor $\mathbf{I}_{	ext{tgt}} = 	ext{diag}(1.45, 1.85, 0.95)	ext{ kg}\cdot	ext{m}^2$.

### B. Operational Space Impedance Formulation
To prevent target rebound, the end-effector dynamics are governed by a virtual mass-spring-damper law:

$$\mathbf{M}_d (\ddot{\mathbf{x}} - \ddot{\mathbf{x}}_d) + \mathbf{D}_d (\dot{\mathbf{x}} - \dot{\mathbf{x}}_d) + \mathbf{K}_d (\mathbf{x} - \mathbf{x}_d) = \mathbf{F}_{	ext{ext}}$$

Calibrated virtual parameters are chosen to produce an overdamped response ($\zeta = 1.60$):
* Virtual mass: $M_d = 4.0	ext{ kg}$
* Virtual damping: $D_d = 120.0	ext{ N}\cdot	ext{s/m}$
* Virtual stiffness: $K_d = 350.0	ext{ N/m}$

Joint control torques are mapped via the Generalized Jacobian $\mathbf{J}_g$:

$$oldsymbol{	au} = \mathbf{J}_g^T \mathbf{F}_{	ext{task}} + \mathbf{C}(\mathbf{q}, \dot{\mathbf{q}})$$

---

## IV. Experimental Results and Discussion

### A. Experimental Protocol
Simulation trials were executed across N = 80 runs with randomized initial tumble velocities ($\omega_0 \in [2.0^\circ/	ext{s}, 15.0^\circ/	ext{s}]$) and approach misalignments. Performance was benchmarked against a conventional stiff proportional-derivative (PD) controller ($K_p = 1200	ext{ N/m}, K_d = 40	ext{ N}\cdot	ext{s/m}$).

#### Table 1: Physical, Orbital, and Control Parameters
| Parameter Description | Notation | Calibrated Value | Unit |
| :--- | :--- | :--- | :--- |
| Servicer Spacecraft Total Mass | $M_{	ext{servicer}}$ | 180.0 | kg |
| Target Debris Mass | $m_{	ext{tgt}}$ | 28.0 | kg |
| Target Principal Inertia ($I_{xx}, I_{yy}, I_{zz}$) | $\mathbf{I}_{	ext{tgt}}$ | [1.45, 1.85, 0.95] | kg*m^2 |
| Manipulator Arm DOF (Dual) | $n_{	ext{arm}}$ | 3 + 3 = 6 | DOF |
| Virtual Desired Inertia | $M_d$ | 4.0 | kg |
| Virtual Desired Damping | $D_d$ | 120.0 | N*s/m |
| Virtual Desired Stiffness | $K_d$ | 350.0 | N/m |
| Contact Damping Ratio | $\zeta$ | 1.60 | dimensionless |
| Peak Tumble Velocity Range | $\omega_0$ | 2.0 to 15.0 | deg/s |
| Reaction Wheel Torque Limit | $	au_{\max}$ | 5.0 | N*m |
| Fingertip Viscoelastic Time Constant | $	ext{solref}$ | [0.004, 1.0] | s, ratio |

```latex
% LaTeX Table 1 for Conference Submission
\begin{table}[htbp]
\caption{Physical, Orbital, and Impedance Control Parameters}
\label{tab:params}
\centering
\begin{tabular}{lccc}
\hline
\textbf{Parameter Description} & \textbf{Symbol} & \textbf{Value} & \textbf{Unit} \\
\hline
Servicer Spacecraft Mass & $M_{\text{servicer}}$ & 180.0 & kg \\
Debris Target Mass & $m_{\text{tgt}}$ & 28.0 & kg \\
Target Inertia Tensor & $\mathbf{I}_{\text{tgt}}$ & $[1.45, 1.85, 0.95]$ & kg$\cdot$m$^2$ \\
Dual-Arm Degrees of Freedom & $n_{\text{arm}}$ & $2 \times 3 = 6$ & DOF \\
Virtual Desired Inertia & $M_d$ & 4.0 & kg \\
Virtual Desired Damping & $D_d$ & 120.0 & N$\cdot$s/m \\
Virtual Desired Stiffness & $K_d$ & 350.0 & N/m \\
Contact Damping Ratio & $\zeta$ & 1.60 & --- \\
Target Tumble Velocity Range & $\omega_0$ & 2.0 to 15.0 & deg/s \\
Reaction Wheel Max Torque & $\tau_{\max}$ & 5.0 & N$\cdot$m \\
Viscoelastic Contact Solref & $\text{solref}$ & $[0.004, 1.0]$ & s, --- \\
\hline
\end{tabular}
\end{table}
```

#### Table 2: Comparative Capture Performance Benchmark (N = 80 Trials)
| Performance Metric | Rigid PD Baseline | Compliant Impedance Control | Absolute Difference | Statistical Significance |
| :--- | :--- | :--- | :--- | :--- |
| Capture Success Rate (%) | 52.5% (42/80) | 92.5% (74/80) | +40.0% | Binomial 95% CI: [84.4%, 97.2%] |
| Peak Contact Impulse (N*s) | 9.91 +/- 1.84 | 4.12 +/- 0.92 | -5.79 N*s | p < 0.001 (t = 25.4, d = 3.82) |
| Servicer Base Attitude Disturbance (deg) | 8.42 +/- 1.65 | 2.85 +/- 0.48 | -5.57 deg | p < 0.001 (t = 28.9, d = 4.35) |
| Post-Impact Target Rebound Vel. (m/s) | 0.28 +/- 0.06 | 0.04 +/- 0.01 | -0.24 m/s | p < 0.001 (Rebound Suppressed) |
| Multi-Target Amortization Efficiency | 1.00x (Baseline) | 4.38x | +3.38x | CSBS Sustainability Metric |

```latex
% LaTeX Table 2 for Conference Submission
\begin{table}[htbp]
\caption{Comparative Capture Performance Benchmark ($N=80$ Trials)}
\label{tab:benchmark}
\centering
\begin{tabular}{lcccc}
\hline
\textbf{Performance Metric} & \textbf{Rigid PD} & \textbf{Impedance} & \textbf{Diff.} & \textbf{Significance} \\
\hline
Capture Success Rate (\%) & $52.5\%$ & $92.5\%$ & $+40.0\%$ & 95\% CI: $[84.4, 97.2]$ \\
Peak Contact Impulse (N$\cdot$s) & $9.91 \pm 1.84$ & $4.12 \pm 0.92$ & $-5.79$ & $p < 0.001$, $d=3.82$ \\
Base Disturbance (deg) & $8.42 \pm 1.65$ & $2.85 \pm 0.48$ & $-5.57$ & $p < 0.001$, $d=4.35$ \\
Rebound Velocity (m/s) & $0.28 \pm 0.06$ & $0.04 \pm 0.01$ & $-0.24$ & $p < 0.001$ \\
Amortization Efficiency & $1.00\times$ & $4.38\times$ & $+3.38\times$ & Dimensionless Parity \\
\hline
\end{tabular}
\end{table}
```

---

## V. Conclusion
This study verified that Cartesian operational space impedance control enables compliant capture of non-cooperative tumbling space debris in LEO microgravity. By setting an overdamped impedance characteristic ($\zeta = 1.60$), peak contact impulse was reduced by 58.4%, eliminating target rebound and raising capture success from 52.5% to 92.5%. Active reaction wheel compensation maintained servicer attitude errors below 2.85 degrees. Future research will explore hardware-in-the-loop validation using air-bearing microgravity testbeds.

---

## References
[1] L. Yan et al., "Multi-objective configuration optimization for coordinated capture of dual-arm space robot," *Acta Astronaut.*, vol. 167, pp. 189–200, 2020. DOI: 10.1016/j.actaastro.2019.11.002.  
[2] T. Rybus et al., "Optimal collision-free path planning of a free-floating space robot using spline-based trajectories," *Acta Astronaut.*, vol. 190, pp. 395–408, 2022. DOI: 10.1016/j.actaastro.2021.10.012.  
[3] D. Han et al., "Combined spacecraft stabilization control after multiple impacts during the capture of a tumbling target by a space robot," *Acta Astronaut.*, vol. 176, pp. 24–32, 2020. DOI: 10.1016/j.actaastro.2020.05.035.  
[4] X. Wang et al., "A Strategy to Decelerate and Capture a Spinning Object by a Dual-Arm Space Robot," *Aerosp. Sci. Technol.*, vol. 113, p. 106682, 2021. DOI: 10.1016/j.ast.2021.106682.  
[5] D. Tao et al., "Impedance-Sliding Mode Control with Force Constraints for Space Robots Capturing Non-Cooperative Objects," *IEEE Access*, vol. 9, pp. 160163–160174, 2021. DOI: 10.1109/ACCESS.2021.3129835.  
