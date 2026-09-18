# Autonomous Vision-Guided Multirotor UAV for Precision Last-Mile Relief Drops in Flood Inundation Zones

## Authors:
- Manikya Rathore (E056)
- Shourya Garg (E020)
- Keswani Laksh (E032)
- Vora Jash (E067)

## Department of Computer Science & Business Systems

---

## Abstract
Severe flood disasters paralyze surface transportation networks, leaving vulnerable populations stranded in submerged sectors where motorized rescue boats face severe navigational hazards, shallow debris, and extreme transit latencies (often exceeding 2 hours). Unmanned Aerial Vehicles (UAVs) provide rapid, infrastructure-independent relief delivery, yet high-altitude airdrops risk cargo destruction while low-altitude hovering induces hazardous propwash and cable swing oscillations under turbulent crosswinds. This paper presents an autonomous vision-guided multirotor UAV platform simulated in Google DeepMind MuJoCo featuring an actively stabilized winch delivery mechanism and visual fiducial tracking. We evaluate vehicle flight stability, payload-range energy trade-offs, and drop precision under varying Dryden wind gust conditions. Across a 100-trial Monte Carlo benchmark, the proposed platform achieves a Circular Error Probable (CEP50) drop accuracy of 0.84 m in calm air and 1.46 m under severe 8 m/s turbulent crosswinds, ensuring undamaged supply delivery on confined rooftops. Compared to conventional rescue boat convoys, the autonomous aerial fleet reduces emergency medical dispatch latency from 145 minutes to 18.2 minutes per sortie (an 87.4% acceleration) while demonstrating a dimensionless capital amortization payback period of 5.8 operating months.

**Keywords:** Multirotor UAV, flood disaster logistics, cable-suspended payload, visual servoing, winch mechanism, Circular Error Probable, MuJoCo simulation, technoeconomic modeling.

---

## I. Introduction
Flooding events represent over 40% of all natural disaster occurrences globally, generating immediate emergencies characterized by submerged road arteries, severed electrical grids, and isolated communities. Rapid distribution of critical medical supplies (insulin, antivenom, oral rehydration salts, water purification kits) is critical within the first 72 hours following inundation.

Conventional relief logistics rely primarily on shallow-draft boats and amphibious vehicles. However, floodwaters contain hidden debris, downed electrical cables, and localized rapids that severely limit boat operating speeds to 5-10 km/h, resulting in dispatch latencies exceeding 2 hours for isolated residential clusters. Autonomous multirotor UAVs offer rapid aerial access, but deploying delicate medical supplies onto restricted elevated surfaces (such as balconies and rooftops) requires high drop accuracy under gusty meteorological conditions.

This research investigates three central engineering questions:
1. How does cable-suspended payload pendulum dynamics affect multirotor flight stability under turbulent crosswind gusts in physics-accurate simulation?
2. To what degree can downward visual tracking and controlled winch descents minimize Circular Error Probable (CEP) on confined target pads?
3. What are the comparative fleet sizing, dispatch throughput, and cost-parity advantages of an aerial drone fleet versus marine rescue boat convoys?

---

## II. Related Work
UAV vehicle routing and analytical energy modeling were systematically formulated by Dorling et al. [1], establishing the fundamental relationship between battery payload fraction and mission range. In disaster management, Chowdhury et al. [2] demonstrated the operational efficiency of drone-assisted relief distribution networks. Cable-suspended load dynamics and anti-sway trajectory generation were pioneered by Sreenath et al. [3], demonstrating differential flatness properties for quadrotors with slung point-masses. Real-time visual tracking for autonomous aerial rendezvous and landing was validated by Falanga et al. [4] using onboard vision. Rabta et al. [5] developed fleet-level queuing frameworks for emergency medical deliveries. This paper unifies these contributions into a multi-body physics simulation and fleet economics pipeline tailored for flood operations.

---

## III. System Modeling & Control Architecture

### A. Multirotor & Winch MJCF Simulation
The system is modeled in MuJoCo MJCF XML format (`models/skyhydro_flood_uav.xml`). The quadrotor airframe (mass 3.8 kg, arm length 0.45 m) incorporates 4 aerodynamic rotor actuators and an actively actuated winch drum capable of paying out a low-stretch braided cable attached to a 1.5 kg shock-damped medical relief canister.

### B. Disturbance Rejection & Trajectory Guidance
Crosswinds are modeled via the Dryden wind turbulence gust model, introducing stochastic wind velocity components $u_w, v_w, w_w$. The vehicle attitude and position controllers employ cascaded PID with feedforward thrust compensation to counteract horizontal cable reaction forces during payload swing:

$$F_{\text{thrust\_des}} = m_q (\ddot{p}_{\text{des}} + K_p e_p + K_d \dot{e}_p + g e_3) + T_{\text{cable}}$$

### C. Vision-Guided Controlled Winch Descent
Rather than executing an unguided ballistic free-drop, the UAV hovers at a safe clearance altitude (12 m) above floodwaters and roof obstructions. A downward-facing camera tracks the target fiducial marker, guiding the winch descent at $0.8$ m/s until ground proximity sensors trigger canister release at an altitude of $0.3$ m, eliminating impact shock.

---

## IV. Experimental Evaluation & Results

### A. Circular Error Probable (CEP) Benchmark
The experimental evaluation encompassed 100 simulated relief drop missions across three meteorological regimes:
- **Calm Air ($v_w < 1.5$ m/s):** $\text{CEP}_{50} = 0.84$ m, $\text{CEP}_{95} = 1.75$ m.
- **Moderate Wind ($v_w = 4.5$ m/s):** $\text{CEP}_{50} = 1.18$ m, $\text{CEP}_{95} = 2.45$ m.
- **Severe Crosswind Gusts ($v_w = 8.0$ m/s):** $\text{CEP}_{50} = 1.46$ m, $\text{CEP}_{95} = 3.04$ m.
All drops fell safely within standard $4 \times 4$ m domestic rooftop landing perimeters.

### B. Response Latency Comparison
Figure 3(b) highlights response times across distances from 2 to 15 km in flooded zones. At a 10 km operational radius, motorized rescue boats average 145 minutes due to circuitous waterways and submerged obstacles. The autonomous UAV achieves delivery in 18.2 minutes, representing an 87.4% reduction in critical dispatch latency ($p < 0.001$).

### C. Fleet Technoeconomics & Payback Parity
Operational cost parity $\kappa = 0.31$ reflects lower energy consumption and streamlined maintenance relative to marine operations. Capital expenditure for a 4-UAV fleet amortizes within 5.8 operating months during flood season deployments.

---

## V. Conclusion
This study demonstrates that autonomous vision-guided multirotor UAVs with controlled winch mechanisms achieve sub-1.5 meter drop accuracy under severe crosswinds while delivering critical flood relief 8 times faster than conventional surface craft. Future extensions will incorporate multi-agent fleet swarm coordination and autonomous battery hot-swapping.

---

## References
- [1] K. Dorling, J. Heinrichs, G. G. Messier, and S. Magierowski, "Vehicle Routing Problems for Drone Delivery," *IEEE Trans. Syst. Man Cybern. Syst.*, vol. 47, no. 1, pp. 70-85, 2017. DOI: 10.1109/TSMC.2016.2582745
- [2] S. Chowdhury, A. Emelogu, M. Marufuzzaman, S. G. Nurre, and L. Bian, "Drones for disaster response and relief operations: A continuous approximation model," *Int. J. Prod. Econ.*, vol. 188, pp. 167-184, 2017. DOI: 10.1016/j.ijpe.2017.03.024
- [3] K. Sreenath, N. Michael, and V. Kumar, "Trajectory generation and control of a quadrotor with a cable-suspended load—a differentially-flat hybrid system," in *Proc. IEEE ICRA*, 2013, pp. 4888-4895. DOI: 10.1109/ICRA.2013.6631278
- [4] D. Falanga, A. Zanchettin, A. Simovic, J. Delmerico, and D. Scaramuzza, "Vision-based autonomous quadrotor landing on a moving platform," in *Proc. IEEE SSRR*, 2017, pp. 200-207. DOI: 10.1109/SSRR.2017.8088164
- [5] B. Rabta, C. Wankmüller, and G. Reiner, "A drone fleet model for last-mile distribution in disaster relief operations," *Int. J. Disaster Risk Reduct.*, vol. 28, pp. 107-112, 2018. DOI: 10.1016/j.ijdrr.2018.02.003
