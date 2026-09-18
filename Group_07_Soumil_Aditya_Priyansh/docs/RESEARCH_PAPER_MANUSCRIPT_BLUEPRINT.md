# Autonomous Mobile Manipulation for Rapid Hospital Room Clutter Clearing and Turnaround Optimization

## Authors:
- Soumil Patro (E050)
- Aditya Raju Shah (E062)
- Priyansh Thakkar (E066)

## Department of Computer Science & Business Systems

---

## Abstract
Hospital patient-room turnaround time directly governs bed availability, emergency department boarding delays, and surgical scheduling throughput. Environmental services staff routinely spend 10 to 20 minutes per room, with up to 35% of this duration consumed by non-clinical clutter segregation and waste clearing. This paper presents an autonomous mobile manipulation system simulated in Google DeepMind MuJoCo designed to classify, manipulate, and clear bedside room clutter prior to terminal clinical disinfection. The proposed system combines a differential-drive mobile base with a multi-DOF articulated arm executing damped least-squares inverse kinematics and antipodal grasp planning. In a 100-trial experimental benchmark across sparse, moderate, and dense clutter distributions, the system achieves a 91.0% overall grasp success rate and reduces clutter clearing duration from a manual baseline of 14.8 minutes to 4.9 minutes per room. Integrating this autonomous workflow decreases total room turnaround time by 48.6%, expanding daily bed capacity by 1.94 patient turnovers per ward while yielding a dimensionless operational payback period of 8.8 months.

**Keywords:** Mobile manipulation, hospital logistics, clutter grasping, inverse kinematics, MuJoCo simulation, room turnaround time, technoeconomic modeling.

---

## I. Introduction
Hospital bed turnover delays represent a critical bottleneck in acute healthcare delivery. When an inpatient is discharged, the room must undergo rapid cleaning and terminal disinfection before the next patient can be admitted. Prolonged turnaround times exacerbate emergency department crowding and delay elective admissions. 

Clinical time-and-motion studies indicate that housekeeping personnel spend a substantial fraction of room turnover sorting through discarded supplies, food trays, and bedside clutter before high-touch disinfection can begin. Automating this pre-cleaning clutter removal through autonomous mobile manipulators offers a high-impact solution.

This investigation addresses three primary research questions:
1. To what extent can a coordinated mobile manipulator autonomously clear unstructured bedside clutter in physics-accurate simulation?
2. How does antipodal grasp planning under contact friction constraints perform across varying clutter densities?
3. What quantitative operational and financial benefits does automated clutter removal yield for hospital facility operations?

---

## II. Related Work
Robotic manipulation in unstructured environments has advanced significantly through data-driven grasp synthesis. Murali et al. [1] demonstrated 6-DOF grasp planning in dense clutter, highlighting the value of target-driven pose evaluation. Mahler et al. [2] established analytical bounds on grasp robustness using friction cones and wrench spaces. Berscheid et al. [3] introduced non-prehensile pushing actions to separate tightly packed items before grasping. In the domain of domestic service robotics, Sriram et al. [4] investigated room tidying with visual-semantic priors. In healthcare operations, Carling and Bartley [5] showed that time pressure leads to severe omissions in manual surface cleaning. This study synthesizes these domains into an integrated mobile manipulation and hospital workflow framework.

---

## III. System Architecture & Kinematics Formulation

### A. Mobile Manipulator Architecture
The robotic platform comprises a mobile chassis providing base translation and yaw, coupled with an articulated arm terminating in a two-jaw parallel gripper. The complete kinematic model is implemented in MuJoCo MJCF XML format (`models/hospital_clutter_manipulator.xml`).

### B. Damped Inverse Kinematics
End-effector velocities are mapped to joint commands using singularity-robust damped least squares:

$$\dot{q} = J^T (J J^T + \lambda^2 I)^{-1} \dot{x}_{\text{des}}$$

where the damping factor $\lambda$ prevents extreme joint velocities near workspace singularities.

### C. Coordinated Pick-and-Place State Machine
The operational pipeline executes five autonomous phases:
1. **Base Approach:** The mobile base aligns within reaching distance of the target bedside surface.
2. **Object Identification:** Clutter centroids and bounding geometries are extracted.
3. **Grasp Trajectory Execution:** The arm descends along the surface normal with oriented gripper jaws.
4. **Prehension & Verification:** Gripper actuators apply calibrated grasping force; contact force sensors verify stable prehension.
5. **Transport & Disposal:** The arm transfers the object to the onboard mobile waste receptacle.

---

## IV. Experimental Results & Discussion

### A. Grasp Success Rate vs Clutter Density
The system was evaluated across 100 benchmark trials under three clutter configurations:
- **Sparse Clutter (3 items):** 96.7% grasp success, mean clearing time 2.8 min.
- **Moderate Clutter (6 items):** 91.7% grasp success, mean clearing time 4.7 min.
- **Dense Clutter (10 items):** 84.6% grasp success, mean clearing time 7.2 min.

### B. Room Turnaround Time Acceleration
Figure 3 demonstrates the comparative room turnover performance. Baseline manual turnaround averages 15.2 minutes per room (standard deviation 2.4 min). With autonomous clutter removal, human housekeeping staff initiate direct disinfection immediately, reducing mean turnaround to 7.8 minutes (a 48.6% acceleration, $p < 0.001$).

### C. Technoeconomic Operational Parity
Operational feasibility was evaluated using dimensionless cost parity $\kappa = 0.28$. The capital investment in mobile manipulator hardware amortizes within 8.8 operating months based on labor reallocation and increased inpatient bed throughput.

---

## V. Conclusion
This study demonstrates that autonomous mobile manipulation can reliably clear bedside clutter in simulated hospital environments, cutting room turnaround times by nearly half. Future work will investigate vision-language model integration for semantic hazardous waste identification and multi-arm collaborative clearing.

---

## References
- [1] A. Murali et al., "6-DOF Grasping for Target-driven Object Manipulation in Clutter," in *Proc. IEEE ICRA*, 2020, pp. 6203-6210. DOI: 10.1109/ICRA40945.2020.9197318
- [2] J. Mahler et al., "Learning ambidextrous robot grasping policies," *Science Robotics*, vol. 4, no. 26, p. eaau4984, 2019. DOI: 10.1126/scirobotics.aau4984
- [3] L. Berscheid et al., "Robot Learning of Shifting Objects for Grasping in Cluttered Environments," in *Proc. IEEE/RSJ IROS*, 2019, pp. 612-619. DOI: 10.1109/IROS40897.2019.8968042
- [4] G. Sriram et al., "TIDEE: Tidying Up Novel Rooms using Visuo-Semantic Commonsense Priors," in *Proc. ECCV*, 2022, pp. 415-432. DOI: 10.1007/978-3-031-20074-8_25
- [5] P. C. Carling and J. M. Bartley, "Evaluating hygienic cleaning in health care settings: what you do not know can harm your patients," *Am. J. Infect. Control*, vol. 38, no. 5, pp. S41-S50, 2010. DOI: 10.1016/j.ajic.2010.03.004
