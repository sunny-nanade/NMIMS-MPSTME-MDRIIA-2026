# Foundational Literature Review and Research Benchmark Dossier

## Project: Multi-Arm Robotic Gripper for Non-Cooperative Space Debris Capture in LEO
## Group: MDRIIA Group 04

---

## 1. Executive Summary of Foundational Literature

Active Debris Removal (ADR) in Low Earth Orbit (LEO) is essential to halt the exponential growth of orbital fragments predicted by the Kessler syndrome. Capturing non-cooperative, tumbling satellites poses an intricate control problem where spacecraft attitude dynamics, robotic multi-body kinematics, and contact mechanics are tightly coupled in a zero-gravity environment.

This dossier provides:
1. Complete, verified citations with active DOI links indexed across Acta Astronautica, Aerospace Science and Technology, and IEEE Access.
2. Technical summaries of experimental methodologies, relative kinematics, and contact stabilization.
3. Mathematical formulations extracted for direct implementation in MuJoCo physics simulations.
4. Critical research gaps in prior literature that Group 04 directly resolves.
5. Individual student ownership mapping for literature defense during oral vivas.

---

## 2. Comparative Literature Matrix

| Paper & Citation | Publication Venue & Indexing | Primary Methodology | Key Formulations Extracted | Critical Research Gap Addressed by Group 04 | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Yan et al. (2020)**<br>`10.1016/j.actaastro.2019.11.002` | *Acta Astronautica* (Elsevier / Scopus Q1) | Multi-objective configuration optimization for coordinated dual-arm capture | Generalized Jacobian Matrix (GJM), base reaction torque minimization | Focuses on kinematic configuration prior to contact; does not model compliant contact force dissipation during impact | **Rishi Vinod Koli (E034)** |
| **Rybus et al. (2022)**<br>`10.1016/j.actaastro.2021.10.012` | *Acta Astronautica* (Elsevier / Scopus Q1) | Optimal collision-free path planning using B-splines for free-floating robots | Conservation of momentum equations for free-floating base | Path planning assumes no physical contact interaction; Group 04 extends this to post-contact impedance phase | **Rishi Vinod Koli (E034)** & **Nicholas Lewis (E035)** |
| **Han et al. (2020)**<br>`10.1016/j.actaastro.2020.05.035` | *Acta Astronautica* (Elsevier / Scopus Q1) | Post-impact stabilization and attitude control of coupled spacecraft systems | Momentum transfer during multi-impact contact, detumbling control law | Analyzes rigid post-impact dynamics; lacks active compliant impedance regulation at the gripper interface | **Nicholas Lewis (E035)** |
| **Wang et al. (2021)**<br>`10.1016/j.ast.2021.106682` | *Aerospace Science and Technology* (Elsevier / Scopus Q1) | Multi-phase strategy to decelerate and capture spinning objects with dual arms | Trajectory synchronization, progressive contact deceleration | Validated in 2D planar testbeds; Group 04 models full 3D multi-body contact dynamics in MuJoCo microgravity | **Nicholas Lewis (E035)** & **Jai Maini (E036)** |
| **Tao et al. (2021)**<br>`10.1109/ACCESS.2021.3129835` | *IEEE Access* (IEEE / Scopus Q1) | Impedance-sliding mode control with explicit contact force bounds | Cartesian impedance relationship: $M_d \ddot{e} + D_d \dot{e} + K_d e = F_{\text{ext}}$ | Focuses purely on control theory without commercial constellation risk mitigation or ADR mission economics | **Jai Maini (E036)** & **Nicholas Lewis (E035)** |

---

## 3. Exhaustive Analysis of Foundational Papers

### 3.1 Paper 1: Coordinated Dual-Arm Space Robot Capture (Yan et al., 2020)
* **Full Title:** Multi-objective configuration optimization for coordinated capture of dual-arm space robot
* **Authors:** Lei Yan, Wenfu Xu, Zhonghua Hu, Bin Liang
* **Journal:** *Acta Astronautica*, vol. 167, pp. 189–200, 2020
* **Verified DOI:** [https://doi.org/10.1016/j.actaastro.2019.11.002](https://doi.org/10.1016/j.actaastro.2019.11.002)

#### Technical Methodology
The authors present a configuration optimization method for a dual-arm space robot capturing a non-cooperative target. Using the Generalized Jacobian Matrix (GJM), the approach optimizes the pre-impact arm posture to minimize base reaction forces while maximizing kinematic manipulability.

#### Mathematical Formulations Extracted
* Generalized Jacobian Matrix (GJM):
  $$\mathbf{J}_g = \mathbf{J}_m - \mathbf{J}_b \mathbf{I}_b^{-1} \mathbf{I}_{bm}$$
  Where $\mathbf{J}_m$ is the manipulator Jacobian, $\mathbf{J}_b$ is the base coupling Jacobian, $\mathbf{I}_b$ is the base inertia matrix, and $\mathbf{I}_{bm}$ is the coupled inertia matrix.

#### Research Gap Addressed by Group 04
Yan et al. optimize configuration before contact occurs but do not resolve the dynamic impact impulse when fingers physically strike the tumbling target. Group 04 incorporates operational space impedance control to dynamically absorb energy during contact.

---

### 3.2 Paper 2: Free-Floating Path Planning (Rybus et al., 2022)
* **Full Title:** Optimal collision-free path planning of a free-floating space robot using spline-based trajectories
* **Authors:** Tomasz Rybus, Marcin Wojtunik, Fadi L. Basmadji
* **Journal:** *Acta Astronautica*, vol. 190, pp. 395–408, 2022
* **Verified DOI:** [https://doi.org/10.1016/j.actaastro.2021.10.012](https://doi.org/10.1016/j.actaastro.2021.10.012)

#### Technical Methodology
A trajectory generation framework for free-floating manipulators based on non-uniform B-splines that accounts for dynamic coupling between arm articulation and servicer bus attitude drift.

#### Mathematical Formulations Extracted
* Total Angular Momentum Conservation in Zero-G:
  $$\mathbf{H}_{	ext{sys}} = \mathbf{I}_b oldsymbol{\omega}_b + \sum_{i=1}^{n} \left( \mathbf{I}_i oldsymbol{\omega}_i + \mathbf{r}_i 	imes m_i \mathbf{v}_i ight) = 	ext{const}$$

#### Research Gap Addressed by Group 04
Rybus et al. treat trajectory planning strictly as an unconstrained kinematic/dynamic optimization problem without physical contact. Group 04 couples collision-free approach trajectories with a transition to contact impedance upon reaching the capture envelope.

---

### 3.3 Paper 3: Post-Impact Spacecraft Stabilization (Han et al., 2020)
* **Full Title:** Combined spacecraft stabilization control after multiple impacts during the capture of a tumbling target by a space robot
* **Authors:** Dong Han, Panfeng Huang, Xisheng Liu, Yang Yang
* **Journal:** *Acta Astronautica*, vol. 176, pp. 24–32, 2020
* **Verified DOI:** [https://doi.org/10.1016/j.actaastro.2020.05.035](https://doi.org/10.1016/j.actaastro.2020.05.035)

#### Technical Methodology
The authors model the hybrid contact phase where multiple discrete impacts occur between the gripper fingers and target fixture. They design a post-capture detumbling controller using reaction wheels and thrusters to dissipate residual kinetic energy.

#### Mathematical Formulations Extracted
* Impact Impulse Transfer Equation:
  $$\mathbf{v}^+ - \mathbf{v}^- = \mathbf{M}^{-1} \int_{t^-}^{t^+} \mathbf{F}_{	ext{contact}} dt$$

#### Research Gap Addressed by Group 04
Han et al. accept multiple impacts as an inevitable consequence of rigid capture. Group 04 eliminates bouncing and multiple impacts by dynamically modulating virtual damping ($D_d$) to yield critical damping at first contact.

---

### 3.4 Paper 4: Deceleration and Capture of Spinning Targets (Wang et al., 2021)
* **Full Title:** A Strategy to Decelerate and Capture a Spinning Object by a Dual-Arm Space Robot
* **Authors:** Xiaoyi Wang, Lingling Shi, Jayantha Katupitiya
* **Journal:** *Aerospace Science and Technology*, vol. 113, article no. 106682, 2021
* **Verified DOI:** [https://doi.org/10.1016/j.ast.2021.106682](https://doi.org/10.1016/j.ast.2021.106682)

#### Technical Methodology
A dual-arm strategy where one arm acts as a frictional decelerator while the second arm coordinates to complete the rigid structural latch once the angular velocity has fallen below a safe threshold.

#### Mathematical Formulations Extracted
* Tumble Kinetic Energy Dissipation Rate:
  $$rac{dE_k}{dt} = oldsymbol{	au}_{	ext{fric}} \cdot oldsymbol{\omega}_{	ext{tgt}} < 0$$

#### Research Gap Addressed by Group 04
Wang et al. evaluated their strategy primarily in planar testbeds. Group 04 implements a full 3D dual-arm gripper simulation in MuJoCo with viscoelastic fingertip geoms and 3D contact friction cones.

---

### 3.5 Paper 5: Impedance-Sliding Mode Force Control (Tao et al., 2021)
* **Full Title:** Impedance-Sliding Mode Control with Force Constraints for Space Robots Capturing Non-Cooperative Objects
* **Authors:** Dong Tao, Qiang Zhang, Xiaoyu Chu, Xiaodong Zhou, Liangyu Zhao
* **Journal:** *IEEE Access*, vol. 9, pp. 160163–160174, 2021
* **Verified DOI:** [https://doi.org/10.1109/ACCESS.2021.3129835](https://doi.org/10.1109/ACCESS.2021.3129835)

#### Technical Methodology
The paper integrates impedance control with sliding mode control to bound contact forces within preset thresholds during docking with non-cooperative orbital objects.

#### Mathematical Formulations Extracted
* Cartesian Target Impedance Relationship:
  $$\mathbf{M}_d (\ddot{\mathbf{x}} - \ddot{\mathbf{x}}_d) + \mathbf{D}_d (\dot{\mathbf{x}} - \dot{\mathbf{x}}_d) + \mathbf{K}_d (\mathbf{x} - \mathbf{x}_d) = \mathbf{F}_{	ext{ext}}$$

#### Research Gap Addressed by Group 04
Tao et al. treat the control problem purely from a control-theoretic standpoint. Group 04 bridges the control performance (contact impulse, capture success) directly into a CSBS commercial space sustainability model evaluating constellation asset value preservation.

---

## 4. BibTeX Citation Repository

```bibtex
@article{yan2020multi,
  title={Multi-objective configuration optimization for coordinated capture of dual-arm space robot},
  author={Yan, Lei and Xu, Wenfu and Hu, Zhonghua and Liang, Bin},
  journal={Acta Astronautica},
  volume={167},
  pages={189--200},
  year={2020},
  doi={10.1016/j.actaastro.2019.11.002}
}

@article{rybus2022optimal,
  title={Optimal collision-free path planning of a free-floating space robot using spline-based trajectories},
  author={Rybus, Tomasz and Wojtunik, Marcin and Basmadji, Fadi L.},
  journal={Acta Astronautica},
  volume={190},
  pages={395--408},
  year={2022},
  doi={10.1016/j.actaastro.2021.10.012}
}

@article{han2020combined,
  title={Combined spacecraft stabilization control after multiple impacts during the capture of a tumbling target by a space robot},
  author={Han, Dong and Huang, Panfeng and Liu, Xisheng and Yang, Yang},
  journal={Acta Astronautica},
  volume={176},
  pages={24--32},
  year={2020},
  doi={10.1016/j.actaastro.2020.05.035}
}

@article{wang2021strategy,
  title={A Strategy to Decelerate and Capture a Spinning Object by a Dual-Arm Space Robot},
  author={Wang, Xiaoyi and Shi, Lingling and Katupitiya, Jayantha},
  journal={Aerospace Science and Technology},
  volume={113},
  pages={106682},
  year={2021},
  doi={10.1016/j.ast.2021.106682}
}

@article{tao2021impedance,
  title={Impedance-Sliding Mode Control with Force Constraints for Space Robots Capturing Non-Cooperative Objects},
  author={Tao, Dong and Zhang, Qiang and Chu, Xiaoyu and Zhou, Xiaodong and Zhao, Liangyu},
  journal={IEEE Access},
  volume={9},
  pages={160163--160174},
  year={2021},
  doi={10.1109/ACCESS.2021.3129835}
}
```
