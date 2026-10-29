# Foundational Literature Review and Research Benchmark Dossier

## Project: Autonomous Drone for Industrial Pipeline Surveillance & Defect Detection
## Group: MDRIIA_GROUP_12
## Students: Arham Khan (E069), Aneesh Kumar (E076)

---

## 1. Executive Summary of Foundational Literature

This dossier establishes the comprehensive academic foundation for MDRIIA_GROUP_12. Grounded in 6 verified peer-reviewed publications validated against the global CrossRef registry, this research resolves key gaps in aerial corridor tracking, optical/thermal anomaly detection, and technoeconomic payback for industrial pipeline monitoring.

---

## 2. Comparative Literature Matrix (6 Verified Papers)

| Paper & Citation | Publication Venue & Indexing | Primary Methodology | Key Formulations Extracted | Critical Research Gap Addressed | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stokkeland, Klausen, & Johansen (2015)**<br>`10.1109/icuas.2015.7152389` | *2015 ICUAS* | Vision-based autonomous flight corridor tracking along linear utility infrastructure. | Lateral corridor error: $e_y = y_{\text{uav}} - y_{\text{pipeline}}$; yaw heading regulation $\psi_e$. | Pure geometric corridor following; lacks multi-spectral thermal leak detection and dynamic obstacle avoidance. | **Arham Khan (E069)** |
| **Hui & Bian (2018)**<br>`10.1177/1729881417752821` | *Int. J. Adv. Robotic Systems* | Computer vision Hough transform line tracking and orientation alignment for aerial inspection. | Feature orientation: $\theta = \arctan2(\Delta y, \Delta x)$; corridor boundary safety buffer $d_{\text{safe}}$. | Focuses exclusively on power transmission lines; does not model ground pipeline thermal anomalies or gas leak signatures. | **Arham Khan (E069) & Aneesh Kumar (E076)** |
| **Car & Markovic (2020)**<br>`10.1109/access.2020.3009738` | *IEEE Access* | LiDAR-based autonomous proximity inspection of curved industrial surfaces. | Surface clearance metric: $d = \min \|p_{\text{uav}} - p_{\text{surface}}\|$; trajectory safety bounds. | High payload and compute requirements for 3D LiDAR; our system optimizes lightweight optical-thermal fusion. | **Arham Khan (E069)** |
| **Okoli & Ubochi (2022)**<br>`10.12785/ijcds/110166` | *Int. J. Computing and Digital Systems* | Ground-based autonomous crawler for gas pipeline inspection and localized leak sensing. | Atmospheric gas dispersion model: $C(x, y, z) = \frac{Q}{2\pi u \sigma_y \sigma_z} \exp(-\dots)$. | Ground crawlers are trapped by terrain obstacles, washouts, and river crossings; aerial UAVs provide unobstructed coverage. | **Aneesh Kumar (E076)** |
| **Shadrenkin & Tokarev (2023)**<br>`10.17122/ntj-oil-2023-3-103-115` | *Problems of Gathering Treatment & Transp.* | Empirical field analysis of UAV pipeline monitoring throughput and operational logistics. | Inspection throughput: $\eta = \frac{L_{\text{inspected}}}{t_{\text{flight}}}$; battery recharge scheduling bounds. | Focuses on empirical operational metrics without providing closed-loop physics simulation models in MuJoCo. | **Aneesh Kumar (E076) & Arham Khan (E069)** |
| **Bretschneider & Bollmann (2024)**<br>`10.3389/frobt.2024.1426206` | *Frontiers in Robotics and AI* | Review of aerial thermal and acoustic concepts for pipeline leak detection. | Radiometric temperature gradient: $\Delta T_{\text{leak}} = T_{\text{soil}} - T_{\text{pipeline}}$. | Identifies lack of open, reproducible physics-based multirotor simulation environments as a key research barrier. | **Aneesh Kumar (E076)** |

---

## 3. Mathematical Formulations & Multi-Body Physics
The multirotor equations of motion modeled in MuJoCo (`models/pipeline_surveillance_drone.xml`):
$$m \ddot{p} = \sum_{i=0}^3 F_i - m g \mathbf{e}_3, \quad I \dot{\omega} + \omega \times (I \omega) = \sum_{i=0}^3 \tau_i$$
Corridor tracking maintains lateral position error $e_y \le 0.25\text{ m}$ along linear pipeline corridor $x \in [-25, 25]\text{ m}$.

---

## 4. Oral Viva Voce Defense Framework
* **Q1 (Arham Khan):** How does your vision controller maintain corridor tracking when pipeline sections are partially obscured by sand or vegetation?
* **Q2 (Aneesh Kumar):** How does your CSBS technoeconomic model demonstrate cost parity without relying on fiat currency numbers?
