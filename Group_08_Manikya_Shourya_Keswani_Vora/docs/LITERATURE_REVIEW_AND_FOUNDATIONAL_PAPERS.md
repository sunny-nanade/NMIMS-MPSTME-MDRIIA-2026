# Exhaustive Literature Review & Foundational Benchmark Papers

## Project Group: MDRIIA Group 08
## Domain: Autonomous UAV Aerial Relief Logistics & Slung-Load Precision Delivery

---

## 1. Verified Foundational Literature Portfolio

The following five peer-reviewed benchmark publications form the theoretical and empirical baseline for this research project. Every citation includes an active, validated Digital Object Identifier (DOI).

```
========================================================================================================================
#  Authors (Year)               Title / Venue                                            DOI
========================================================================================================================
1  Dorling et al. (2017)        Vehicle Routing Problems for Drone Delivery              10.1109/TSMC.2016.2582745
                                (IEEE Trans. Syst. Man Cybern. Syst.)
2  Chowdhury et al. (2017)      Drones for Disaster Response and Relief Operations:     10.1016/j.ijpe.2017.03.024
                                A Continuous Approximation Model (Int. J. Prod. Econ.)
3  Sreenath et al. (2013)       Trajectory Generation and Control of a Quadrotor with    10.1109/ICRA.2013.6631278
                                a Cable-Suspended Load (IEEE ICRA 2013)
4  Falanga et al. (2017)        Vision-Based Autonomous Quadrotor Landing on a Moving    10.1109/SSRR.2017.8088164
                                Platform (IEEE SSRR 2017)
5  Rabta et al. (2018)          A Drone Fleet Model for Last-Mile Distribution in        10.1016/j.ijdrr.2018.02.003
                                Disaster Relief Operations (Int. J. Disaster Risk Red.)
========================================================================================================================
```

---

## 2. In-Depth Methodological Analysis of Each Paper

### Paper 1: Vehicle Routing Problems for Drone Delivery
- **Authors:** Kevin Dorling, Jordan Heinrichs, Geoffrey G. Messier, Sebastian Magierowski
- **Venue:** *IEEE Transactions on Systems, Man, and Cybernetics: Systems*, Vol. 47, No. 1, pp. 70-85, 2017.
- **DOI:** [10.1109/TSMC.2016.2582745](https://doi.org/10.1109/TSMC.2016.2582745)
- **Key Contribution:** Derives an analytical power consumption model for multirotor UAVs as an explicit function of vehicle gross weight, battery mass, payload mass, and aerodynamic drag. Formulates the drone vehicle routing problem under strict energy battery constraints.
- **Direct Relevance to Group 08:** Provides the closed-form energy consumption equations relating relief kit payload weight (1.0 kg to 3.5 kg) to operating radius and battery depletion rates during flood missions.

### Paper 2: Drones for Disaster Response and Relief Operations: A Continuous Approximation Model
- **Authors:** Sudipta Chowdhury, Adindu Emelogu, Mohammad Marufuzzaman, Sarah G. Nurre, Linkan Bian
- **Venue:** *International Journal of Production Economics*, Vol. 188, pp. 167-184, 2017.
- **DOI:** [10.1016/j.ijpe.2017.03.024](https://doi.org/10.1016/j.ijpe.2017.03.024)
- **Key Contribution:** Develops continuous approximation optimization models to determine optimal drone fleet sizes, launch base locations, and dispatch schedules during post-disaster humanitarian logistics operations.
- **Direct Relevance to Group 08:** Supplies the macroscopic disaster logistics framework comparing aerial drone delivery against surface-bound rescue boats across flooded urban and rural sectors.

### Paper 3: Trajectory Generation and Control of a Quadrotor with a Cable-Suspended Load
- **Authors:** Koushil Sreenath, Nathan Michael, Vijay Kumar
- **Venue:** *2013 IEEE International Conference on Robotics and Automation (ICRA)*, pp. 4888-4895.
- **DOI:** [10.1109/ICRA.2013.6631278](https://doi.org/10.1109/ICRA.2013.6631278)
- **Key Contribution:** Proves that a quadrotor with a cable-suspended point-mass payload is differentially flat, enabling minimum-snap trajectory planning that suppresses residual pendulum oscillations at the drop destination.
- **Direct Relevance to Group 08:** Forms the mathematical basis for modeling payload sway dynamics, cable tension forces, and swing-free deceleration profiles in `skyhydro_flood_uav.xml`.

### Paper 4: Vision-Based Autonomous Quadrotor Landing on a Moving Platform
- **Authors:** Davide Falanga, Alessio Zanchettin, Alessandro Simovic, Jeffrey Delmerico, Davide Scaramuzza
- **Venue:** *2017 IEEE International Symposium on Safety, Security and Rescue Robotics (SSRR)*, pp. 200-207.
- **DOI:** [10.1109/SSRR.2017.8088164](https://doi.org/10.1109/SSRR.2017.8088164)
- **Key Contribution:** Implements visual odometry and downward-looking camera target tracking using visual fiducial markers to achieve high-precision descent on moving target platforms without external GPS assistance.
- **Direct Relevance to Group 08:** Provides the vision-in-the-loop tracking architecture used to guide the UAV above isolated rooftops or designated relief drop targets amidst floodwaters.

### Paper 5: A Drone Fleet Model for Last-Mile Distribution in Disaster Relief Operations
- **Authors:** Boualem Rabta, Christian Wankmüller, Gerald Reiner
- **Venue:** *International Journal of Disaster Risk Reduction*, Vol. 28, pp. 107-112, 2018.
- **DOI:** [10.1016/j.ijdrr.2018.02.003](https://doi.org/10.1016/j.ijdrr.2018.02.003)
- **Key Contribution:** Formulates a queuing and optimization model for last-mile distribution of emergency medical supplies and water purification packets, accounting for recharging logistics and flight range limits.
- **Direct Relevance to Group 08:** Establishes the CSBS operational metrics for turnaround dispatch intervals, recharging turnaround, and dimensionless cost-parity benchmarks.

---

## 3. Comparative Literature Synthesis

| Study | Platform Type | Payload Mechanism | Environmental Disturbance | Primary Metric | Core Limitation | Active DOI |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dorling et al. (2017)** | Multirotor Drone | Rigid Mount | Simplified Drag | Energy Consumption (Wh/km) | No suspended load physics | `10.1109/TSMC.2016.2582745` |
| **Chowdhury et al. (2017)**| Macro Fleet Network | General Relief Cargo | Static Demand Zones | Cost / Coverage Trade-off | Macroscopic model, no physics | `10.1016/j.ijpe.2017.03.024` |
| **Sreenath et al. (2013)** | Quadrotor UAV | Cable-Suspended Load | Ideal Quiescent Air | Pendulum Swing Angle | No vision feedback / no wind | `10.1109/ICRA.2013.6631278` |
| **Falanga et al. (2017)** | Vision-Guided Quad | Onboard Camera | Laboratory Wind | Landing Precision (cm) | Focuses on landing, not drops | `10.1109/SSRR.2017.8088164` |
| **Rabta et al. (2018)** | Disaster Drone Fleet| Package Release | Operational Delays | Mission Completion Rate | Empirical logistics, no aerodynamics | `10.1016/j.ijdrr.2018.02.003` |
| **Group 08 Proposed** | Multirotor UAV (MuJoCo) | Winch-Suspended Kit | Turbulent Crosswinds | Circular Error Probable (CEP) | Simulation fidelity validation | **Our Contribution** |

---

## 4. Research Gap and Proposed Innovation

Existing literature separates high-level fleet logistics (Dorling et al., Chowdhury et al.) from low-level pendulum control (Sreenath et al.). Group 08 bridges these domains by providing:
1. Full multi-body MuJoCo simulation of a multirotor with active cable-suspended medical payloads subject to Dryden wind turbulence.
2. Vision-guided winch drop control evaluating Circular Error Probable (CEP50 and CEP95) drop accuracy.
3. A CSBS queuing and cost-parity model demonstrating that UAV fleets establish operational breakeven within months compared to motorized boat operations in inundated zones.
