# Foundational Literature Review and Research Benchmark Dossier

## Project: Autonomous Mobile Robot for Solar PV Defect Inspection & Anomaly Detection
## Group: MDRIIA_GROUP_11
## Student Lead: Daneeka Abhijeet Roy (E057)

---

## 1. Executive Summary of Foundational Literature

This dossier establishes the comprehensive academic foundation for MDRIIA_GROUP_11. Grounded in 6 verified peer-reviewed publications validated against the global CrossRef registry, this research resolves key gaps in automated thermographic defect detection and mobile robot navigation in utility-scale solar farms.

---

## 2. Comparative Literature Matrix (6 Verified Papers)

| Paper & Citation | Publication Venue & Indexing | Primary Methodology | Key Formulations Extracted | Critical Research Gap Addressed | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Salazar & Macabebe (2016)**<br>`10.1051/matecconf/20167010015` | *MATEC Web of Conferences* | Quantitative thermographic hotspot identification in crystalline silicon modules under steady solar irradiance. | Thermal gradient threshold: $\Delta T = T_{\text{hotspot}} - T_{\text{ambient}} \ge 15.0^{\circ}\text{C}$. | Handheld manual thermography; lacks automated mobile rover integration and dynamic waypoint traversal. | **Daneeka Abhijeet Roy (E057)** |
| **Vaněk & Repko (2016)**<br>`10.1149/07401.0293ecst` | *ECS Transactions* | Automation capabilities and radiometric calibration for solar module thermography. | Radiometric defect metric: $D_{\text{th}} = \int_0^T \sigma(T) dt$. | Laboratory bench setup; does not account for ground rover chassis vibration or wheel slip on sandy terrain. | **Daneeka Abhijeet Roy (E057)** |
| **Ma & Zhang (2021)**<br>`10.1109/jphotov.2021.3059425` | *IEEE Journal of Photovoltaics* | Current mismatch fault diagnosis combining electrical I-V data with optical inspection. | Mismatch index: $I_{\text{loss}} = I_{\text{mp}} - I_{\text{meas}}$; bypass diode activation bound. | Electrical sensor based; lacks real-time spatial geo-referencing of individual defective cells across vast arrays. | **Daneeka Abhijeet Roy (E057)** |
| **Oliveira & Bracht (2023)**<br>`10.1016/j.solener.2023.01.058` | *Solar Energy* | Automatic fault detection in utility-scale solar generators using aerial thermography and orthomosaicking. | Classification metric: $A = \frac{\text{TP} + \text{TN}}{N}$; orthomosaic feature alignment error $\epsilon_{\text{geo}}$. | Aerial drone flight regulations, high battery drain, and airspace restrictions; ground AMRs offer continuous, all-weather close-proximity inspection. | **Daneeka Abhijeet Roy (E057)** |
| **Spajić & Talajić (2024)**<br>`10.2478/bsrj-2024-0003` | *Business Systems Research Journal* | Convolutional Neural Networks for PV panel defect detection via infrared thermography in Industry 4.0. | Feature extraction activation: $f(x) = \text{ReLU}(W * x + b)$; loss cross-entropy $\mathcal{L}$. | High computational overhead; does not formulate embedded edge inference budgets on resource-constrained mobile robots. | **Daneeka Abhijeet Roy (E057)** |
| **Liu & Wu (2025)**<br>`10.1016/j.solener.2025.113489` | *Solar Energy* | Comprehensive state-of-the-art review on fault diagnosis and degradation modeling of photovoltaic modules. | Reliability and degradation function: $R(t) = \exp(-\lambda t)$; MTBF formulations. | Review paper establishing global benchmarks; identifies autonomous mobile inspection as the foremost emerging frontier. | **Daneeka Abhijeet Roy (E057)** |

---

## 3. Mathematical Formulations & Control Principles
The physical system combines differential-drive ground kinematics with pan-tilt sensor tracking:
$$\begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\theta} \end{bmatrix} = \begin{bmatrix} \frac{r}{2}(v_r + v_l) \cos\theta \\ \frac{r}{2}(v_r + v_l) \sin\theta \\ \frac{r}{L}(v_r - v_l) \end{bmatrix}$$
where $r = 0.12\text{ m}$ is wheel radius and $L = 0.56\text{ m}$ is axle track width.

---

## 4. Oral Viva Voce Defense Framework
* **Q1:** How does your controller distinguish between a genuine localized hotspot defect and transient reflections of direct solar irradiance on the glass panel?
* **Q2:** How does your technoeconomic model justify ground AMR inspection over aerial drone surveys in terms of operating hours and capital amortization?
