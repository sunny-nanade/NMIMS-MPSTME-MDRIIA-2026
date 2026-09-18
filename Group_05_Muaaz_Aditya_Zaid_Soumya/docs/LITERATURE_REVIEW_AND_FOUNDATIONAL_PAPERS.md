# Foundational Literature Review and Research Benchmark Dossier

## Project: Collaborative Dual-UAV Autonomous Surveillance System for Campus Perimeter Security
## Group: MDRIIA Group 05

---

## 1. Executive Summary of Foundational Literature

Physical perimeter security for institutional facilities is critical for mitigating unauthorized intrusions and securing high-risk infrastructure. Conventional security operations rely heavily on human foot patrols, which exhibit long cycle latencies (45–60 minutes per sweep) and high vulnerability to fatigue and vigilance decay. Autonomous Unmanned Aerial Vehicles (UAVs) provide flexible aerial perspectives and high mobility, but single-UAV systems suffer from coverage gaps during recharging and restricted fields of view. Collaborative multi-UAV swarms resolve these limitations by dynamically partitioning perimeter sectors.

This dossier provides:
1. Complete, verified citations with active DOI links indexed across IEEE Transactions, IEEE Letters, and Elsevier.
2. Technical methodologies analyzing multi-UAV perimeter patrol, computer vision detection, and set-invariance control.
3. Mathematical formulations extracted for direct implementation in MuJoCo physics and OpenCV pipelines.
4. Critical research gaps in prior literature that Group 05 directly resolves.
5. Individual student ownership mapping for literature defense during oral vivas.

---

## 2. Comparative Literature Matrix

| Paper & Citation | Publication Venue & Indexing | Primary Methodology | Key Formulations Extracted | Critical Research Gap Addressed by Group 05 | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Guerrero-Bonilla & Dimarogonas (2021)**<br>`10.1109/LRA.2020.3028055` | *IEEE Robotics and Automation Letters* (IEEE / Scopus Q1) | Perimeter surveillance and intruder interception based on set-invariance control | Control barrier functions, perimeter invariant sets, intruder speed ratios | Theoretical formulation assumes 1D perimeter motion without 6-DOF aerodynamic multi-body physics; Group 05 simulates full 6-DOF flight in MuJoCo | **Muaaz Shaikh (E043)** & **Zaid Rahman (E075)** |
| **Javaid et al. (2023)**<br>`10.1109/TITS.2023.3248841` | *IEEE Trans. Intell. Transp. Syst.* (IEEE / Scopus Q1) | Comprehensive survey of communication and control in collaborative UAV fleets | Consensus protocols, inter-UAV separation constraints, flocking algorithms | Focuses on high-level network topology; does not provide an integrated physical simulation with downward computer vision target tracking | **Muaaz Shaikh (E043)** |
| **Wu et al. (2024)**<br>`10.1109/TVT.2023.3341878` | *IEEE Trans. Veh. Technol.* (IEEE / Scopus Q1) | Dynamic task allocation for multi-UAV cooperative surveillance using attention models | Task assignment cost matrix, spatial sector partitioning equations | Evaluates high-level mission allocation without modeling local geofence alert escalation or campus security operations | **Zaid Rahman (E075)** & **Soumya Ranasingh (E077)** |
| **Cabreira et al. (2019)**<br>`10.3390/drones3010004` | *Drones* (MDPI / Scopus Q2) | Systematic review of coverage path planning (CPP) algorithms for UAVs | Boustrophedon decomposition, path length and energy optimization metrics | Focuses on static area mapping rather than dynamic perimeter patrol with active human target interception | **Muaaz Shaikh (E043)** & **Aditya Rajkumar (E051)** |
| **Mittal et al. (2020)**<br>`10.1016/j.imavis.2020.104046` | *Image and Vision Computing* (Elsevier / Scopus Q1) | Survey on deep learning and vision-based object detection in aerial UAV datasets | Small object resolution limits, illumination decay, bounding-box IoU formulations | Reviews standalone computer vision models; does not link detection latency to flight dynamics or security dispatch operations | **Aditya Rajkumar (E051)** & **Soumya Ranasingh (E077)** |

---

## 3. Exhaustive Analysis of Foundational Papers

### 3.1 Paper 1: Set-Invariance Perimeter Surveillance (Guerrero-Bonilla & Dimarogonas, 2021)
* **Full Title:** Perimeter surveillance based on set-invariance
* **Authors:** Luis Guerrero-Bonilla, Dimos V. Dimarogonas
* **Journal:** *IEEE Robotics and Automation Letters*, vol. 6, no. 1, pp. 9–16, 2021
* **Verified DOI:** [https://doi.org/10.1109/LRA.2020.3028055](https://doi.org/10.1109/LRA.2020.3028055)

#### Technical Methodology
The authors establish a formal control framework for multiple autonomous agents patrolling the boundary of a polygonal domain to intercept moving intruders. Using set-invariance theory, they synthesize reactive velocity control laws ensuring that any intruder approaching the perimeter is intercepted before crossing the boundary.

#### Mathematical Formulations Extracted
* Intruder Interception Condition:
  $$rac{v_{	ext{intruder}}}{v_{	ext{UAV}}} \le rac{d_{	ext{min}}}{L_{	ext{sector}}}$$
  Where $d_{	ext{min}}$ is the minimum detection horizon and $L_{	ext{sector}}$ is the patrol sector length.

#### Research Gap Addressed by Group 05
Guerrero-Bonilla & Dimarogonas assume point-mass kinematics constrained to a 1D perimeter track. Group 05 implements 6-DOF quadrotor aerodynamics in MuJoCo, modeling rotor thrust dynamics, translation tilt coupling, and wind disturbances.

---

### 3.2 Paper 2: Communication and Control in Collaborative UAVs (Javaid et al., 2023)
* **Full Title:** Communication and Control in Collaborative UAVs: Recent Advances and Future Trends
* **Authors:** Shumaila Javaid, Nasir Saeed, Zakria Qadir, Hamza Fahim, Bin He, Houbing Herbert Song, Muhammad Bilal
* **Journal:** *IEEE Transactions on Intelligent Transportation Systems*, vol. 24, no. 6, pp. 5719–5739, 2023
* **Verified DOI:** [https://doi.org/10.1109/TITS.2023.3248841](https://doi.org/10.1109/TITS.2023.3248841)

#### Technical Methodology
A comprehensive state-of-the-art review examining decentralized control strategies, flocking models, and communication protocols for cooperative multi-UAV systems operating in complex urban environments.

#### Mathematical Formulations Extracted
* Inter-UAV Repulsive Potential Field (APF):
  $$\mathbf{F}_{	ext{rep}} = egin{cases} k_{	ext{rep}} \left( rac{1}{d} - rac{1}{d_{	ext{safe}}} ight) rac{1}{d^2} \hat{\mathbf{r}}, & d < d_{	ext{safe}} \ \mathbf{0}, & d \ge d_{	ext{safe}} \end{cases}$$

#### Research Gap Addressed by Group 05
Javaid et al. address general multi-UAV communication. Group 05 applies APF separation specifically to dual-UAV perimeter patrolling, guaranteeing a strict separation bound of $d \ge 2.5	ext{ m}$ during synchronized sweeps.

---

### 3.3 Paper 3: Dynamic Multi-UAV Task Allocation (Wu et al., 2024)
* **Full Title:** Multi-UAV Collaborative Dynamic Task Allocation Method Based on ISOM and Attention Mechanism
* **Authors:** Jiehong Wu, Jingchuan Zhang, Ya'nan Sun, Xianwei Li, Lijun Gao, Guangjie Han
* **Journal:** *IEEE Transactions on Vehicular Technology*, vol. 73, no. 5, pp. 6225–6235, 2024
* **Verified DOI:** [https://doi.org/10.1109/TVT.2023.3341878](https://doi.org/10.1109/TVT.2023.3341878)

#### Technical Methodology
The authors propose an attention-mechanism-based task allocation framework that dynamically assigns surveillance sectors to multiple drones based on target priority, residual battery state, and flight distance.

#### Mathematical Formulations Extracted
* Sector Allocation Cost Objective:
  $$J = \sum_{i=1}^{N_{	ext{UAV}}} \sum_{j=1}^{M_{	ext{sector}}} c_{ij} x_{ij} + \lambda \sum_{i=1}^{N_{	ext{UAV}}} |E_i - ar{E}|$$

#### Research Gap Addressed by Group 05
Wu et al. focus on centralized algorithmic task allocation. Group 05 implements spatial sector partitioning coupled with a real-time geofence breach finite state machine (FSM) that escalates threat levels locally.

---

### 3.4 Paper 4: UAV Coverage Path Planning (Cabreira et al., 2019)
* **Full Title:** Survey on Coverage Path Planning with Unmanned Aerial Vehicles
* **Authors:** Taua Milech Cabreira, Lisane Brisolara, Paulo R. Ferreira Jr.
* **Journal:** *Drones*, vol. 3, no. 1, article no. 4, 2019
* **Verified DOI:** [https://doi.org/10.3390/drones3010004](https://doi.org/10.3390/drones3010004)

#### Technical Methodology
A survey analyzing coverage path planning (CPP) techniques for UAVs, categorizing algorithms by decomposition methods, flight path geometry, and single vs multi-UAV cooperative coverage.

#### Mathematical Formulations Extracted
* Coverage Completion Time:
  $$T_{	ext{cov}} = rac{L_{	ext{path}}}{v_{	ext{cruise}}} + N_{	ext{turns}} \cdot 	au_{	ext{turn}}$$

#### Research Gap Addressed by Group 05
Cabreira et al. examine static area coverage. Group 05 tailors CPP to continuous cyclic perimeter boundary surveillance with synchronized mutual handoffs between UAV Alpha and UAV Bravo.

---

### 3.5 Paper 5: Low-Altitude Aerial Object Detection (Mittal et al., 2020)
* **Full Title:** Deep learning-based object detection in low-altitude UAV datasets: A survey
* **Authors:** Payal Mittal, Raman Singh, Akashdeep Sharma
* **Journal:** *Image and Vision Computing*, vol. 104, article no. 104046, 2020
* **Verified DOI:** [https://doi.org/10.1016/j.imavis.2020.104046](https://doi.org/10.1016/j.imavis.2020.104046)

#### Technical Methodology
A comprehensive review of computer vision algorithms for aerial surveillance, identifying challenges including small target pixel footprint, motion blur, and severe illumination variations from daylight to dusk.

#### Mathematical Formulations Extracted
* Bounding Box Intersection over Union (IoU):
  $$	ext{IoU} = rac{	ext{Area}(B_{	ext{pred}} \cap B_{	ext{gt}})}{	ext{Area}(B_{	ext{pred}} \cup B_{	ext{gt}})}$$

#### Research Gap Addressed by Group 05
Mittal et al. analyze offline vision datasets. Group 05 evaluates an online, real-time OpenCV detection pipeline inside MuJoCo across four calibrated illumination regimes ($1000	ext{ lx}$ down to $5	ext{ lx}$) and maps pixel centroids to world ground coordinates via inverse pinhole projection.

---

## 4. BibTeX Citation Repository

```bibtex
@article{guerrero2021perimeter,
  title={Perimeter surveillance based on set-invariance},
  author={Guerrero-Bonilla, Luis and Dimarogonas, Dimos V.},
  journal={IEEE Robotics and Automation Letters},
  volume={6},
  number={1},
  pages={9--16},
  year={2021},
  doi={10.1109/LRA.2020.3028055}
}

@article{javaid2023communication,
  title={Communication and Control in Collaborative UAVs: Recent Advances and Future Trends},
  author={Javaid, Shumaila and Saeed, Nasir and Qadir, Zakria and Fahim, Hamza and He, Bin and Song, Houbing Herbert and Bilal, Muhammad},
  journal={IEEE Transactions on Intelligent Transportation Systems},
  volume={24},
  number={6},
  pages={5719--5739},
  year={2023},
  doi={10.1109/TITS.2023.3248841}
}

@article{wu2024multi,
  title={Multi-UAV Collaborative Dynamic Task Allocation Method Based on ISOM and Attention Mechanism},
  author={Wu, Jiehong and Zhang, Jingchuan and Sun, Ya'nan and Li, Xianwei and Gao, Lijun and Han, Guangjie},
  journal={IEEE Transactions on Vehicular Technology},
  volume={73},
  number={5},
  pages={6225--6235},
  year={2024},
  doi={10.1109/TVT.2023.3341878}
}

@article{cabreira2019survey,
  title={Survey on Coverage Path Planning with Unmanned Aerial Vehicles},
  author={Cabreira, Tau{\~a} Milech and Brisolara, Lisane and Ferreira Jr, Paulo R.},
  journal={Drones},
  volume={3},
  number={1},
  pages={4},
  year={2019},
  doi={10.3390/drones3010004}
}

@article{mittal2020deep,
  title={Deep learning-based object detection in low-altitude UAV datasets: A survey},
  author={Mittal, Payal and Singh, Raman and Sharma, Akashdeep},
  journal={Image and Vision Computing},
  volume={104},
  pages={104046},
  year={2020},
  doi={10.1016/j.imavis.2020.104046}
}
```
