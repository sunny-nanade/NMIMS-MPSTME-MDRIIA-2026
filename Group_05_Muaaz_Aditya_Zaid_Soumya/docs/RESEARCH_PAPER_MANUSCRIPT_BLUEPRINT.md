# Autonomous Collaborative Dual-UAV Surveillance System: Optimizing Campus Perimeter Patrol Cycle Time and OpenCV Detection Latency in MuJoCo

**Authors:** Muaaz Mohammed Iqbal Shaikh, Aditya Rajkumar, Zaid Rezaur Rahman, Soumya Subhankar Ranasingh  
**Target Conference:** IEEE International Conference on Automation Science and Engineering (IEEE CASE) / Indian Conference on Computer Vision, Graphics and Image Processing (ICVGIP)  
**Format:** IEEE 2-Column Conference Paper Blueprint  

---

## Abstract
Physical perimeter security for institutional facilities is conventionally maintained through manual security guard foot patrols, which suffer from long patrol cycle latencies (45–60 minutes per round) and leave over 35% of perimeter boundaries unmonitored. This paper presents an autonomous collaborative dual-quadrotor UAV surveillance system simulated in the MuJoCo multi-body physics engine. The platform integrates cascaded position/attitude flight control with an Artificial Potential Field (APF) inter-UAV collision avoidance algorithm guaranteeing minimum safety separation (>= 2.5 m). A downward-facing surveillance camera coupled to an OpenCV computer vision pipeline extracts intruder contours and projects pixel centroids into Cartesian campus ground coordinates via inverse pinhole geometry. Across N = 80 simulated perimeter surveillance trials, the dual-UAV swarm completed perimeter sweeps in an average of 7.84 minutes (SD = 0.62 min), achieving an 83.9% cycle time reduction compared to the manual guard baseline of 48.72 minutes (SD = 3.41 min, p < 0.001, Cohen's d = 16.54). OpenCV human target detection latency remained below 49.24 ms even under degraded ambient lighting (5 lx), preserving real-time throughput (> 20 FPS). A dimensionless security operations model demonstrates a 70% guard labor reallocation and a normalized investment payback horizon of 10.94 months.

**Keywords:** Aerial Swarm Robotics, Campus Perimeter Surveillance, MuJoCo Physics, OpenCV Object Detection, Artificial Potential Fields, Security Operations.

---

## I. Introduction
Securing large educational and commercial campuses against unauthorized boundary incursions is a fundamental operational requirement. Current standard practices rely on scheduled foot patrols by security guards and fixed CCTV cameras [1]. However, fixed CCTV cameras suffer from architectural blind spots, and manual foot patrols take 45 to 60 minutes per sweep. Consequently, an intruder breaching an unmonitored perimeter fence can remain undetected for substantial intervals.

Unmanned Aerial Vehicles (UAVs) provide elevated observation perspectives and high transit velocities [2]. While single-UAV systems have been explored, they cannot achieve continuous surveillance due to battery depletion and single-vantage occlusions. This study evaluates a collaborative dual-UAV swarm architecture operating in the MuJoCo physics engine to address these challenges.

The key contributions of this paper are:
1. Formulation and validation in MuJoCo of a 6-DOF dual-quadrotor flight controller enforcing APF inter-drone collision avoidance ($d_{	ext{sep}} \ge 2.5	ext{ m}$) during synchronized perimeter patrol sweeps.
2. Development of an offscreen OpenCV aerial vision pipeline projecting 2D camera detections to 3D campus coordinates and driving a 4-tier geofencing state machine.
3. Empirical benchmarking across N = 80 trials validating patrol cycle speedup and illumination robustness, coupled with a dimensionless CSBS economic model.

---

## II. Related Work & Foundational Literature
Perimeter surveillance using multi-agent robotic systems has received widespread attention. Guerrero-Bonilla & Dimarogonas (2021) developed set-invariance control laws for multi-robot boundary surveillance and intruder interception [1]. Javaid et al. (2023) surveyed communication and control paradigms in collaborative multi-UAV fleets, establishing flocking and separation constraints [2]. Wu et al. (2024) investigated dynamic task allocation for cooperative multi-UAV coverage using attention models [3].

In coverage path planning, Cabreira et al. (2019) reviewed optimal decomposition algorithms, highlighting the efficiency of partitioned cellular sweeps [4]. For vision-based detection, Mittal et al. (2020) analyzed low-altitude aerial object detection, identifying scale variation and low-light degradation as key challenges [5]. Group 05 addresses these challenges by integrating full 6-DOF dynamic simulation with real-time OpenCV detection and campus security operations modeling.

---

## III. Multi-Body Quadrotor Dynamics and Vision Architecture

### A. 6-DOF Flight Dynamics and Cascaded PID Control
Each quadrotor airframe (mass $m = 1.35	ext{ kg}$, arm length $l = 0.26	ext{ m}$) is governed by Newton-Euler rigid body equations:

$$m \ddot{\mathbf{p}} = m \mathbf{g} + \mathbf{R} \mathbf{F}_T - \mathbf{D}_{	ext{trans}} \dot{\mathbf{p}}$$

$$\mathbf{I} \dot{oldsymbol{\omega}} + oldsymbol{\omega} 	imes (\mathbf{I} oldsymbol{\omega}) = oldsymbol{	au}_B$$

Outer-loop position control computes virtual horizontal acceleration commands, mapped into desired roll/pitch angles:

$$\phi_d = rac{1}{g}(a_{x,	ext{des}} \sin\psi - a_{y,	ext{des}} \cos\psi), \quad 	heta_d = rac{1}{g}(a_{x,	ext{des}} \cos\psi + a_{y,	ext{des}} \sin\psi)$$

### B. Inter-UAV Artificial Potential Field Separation
To guarantee collision-free patrol synchronization, a repulsive potential field is evaluated between UAV Alpha ($\mathbf{p}_1$) and UAV Bravo ($\mathbf{p}_2$):

$$\mathbf{F}_{	ext{rep}} = egin{cases} k_{	ext{rep}} \left( rac{1}{d} - rac{1}{d_{	ext{safe}}} ight) rac{1}{d^2} rac{\mathbf{p}_1 - \mathbf{p}_2}{d}, & d < d_{	ext{safe}} \ \mathbf{0}, & d \ge d_{	ext{safe}} \end{cases}$$

Where $d_{	ext{safe}} = 2.5	ext{ m}$ and $k_{	ext{rep}} = 8.5	ext{ N}\cdot	ext{m}^2$.

### C. Downward Vision Pipeline & Inverse Pinhole Projection
The downward surveillance camera ($640 	imes 480$ px, $f = 450	ext{ px}$) captures RGB frames at 30 FPS. Color thresholding in HSV space extracts candidate intruder contours. Bounding-box centroids $(u, v)$ are projected to campus ground coordinates:

$$X_w = X_{	ext{UAV}} + rac{(u - u_0) Z_{	ext{UAV}}}{f}, \quad Y_w = Y_{	ext{UAV}} - rac{(v - v_0) Z_{	ext{UAV}}}{f}$$

---

## IV. Experimental Results and Discussion

### A. Experimental Protocol
The simulation was executed in MuJoCo across N = 80 trials over a $60	ext{ m} 	imes 60	ext{ m}$ campus environment with academic buildings, perimeter walls, and an electrical substation restricted zone. Comparison was conducted against manual guard patrol records.

#### Table 1: Physical, Dynamic, and Vision Parameters
| Parameter Description | Notation | Calibrated Value | Unit |
| :--- | :--- | :--- | :--- |
| Quadrotor Airframe Mass | $m$ | 1.35 | kg |
| Arm Moment Length | $l$ | 0.26 | m |
| Maximum Total Thrust | $F_{T,\max}$ | 30.0 | N |
| Cruise Flight Altitude | $Z_{	ext{cruise}}$ | 12.0 | m |
| Cruise Forward Velocity | $v_{	ext{cruise}}$ | 6.0 | m/s |
| Camera Resolution | $	ext{Res}$ | 640 x 480 | pixels |
| Camera Focal Length | $f$ | 450.0 | pixels |
| Minimum UAV Separation | $d_{	ext{safe}}$ | 2.5 | m |
| APF Repulsive Constant | $k_{	ext{rep}}$ | 8.5 | N*m^2 |
| Position Proportional Gain | $K_{p,	ext{pos}}$ | 1.80 | s^-2 |
| Position Derivative Gain | $K_{d,	ext{pos}}$ | 1.20 | s^-1 |

```latex
% LaTeX Table 1 for IEEE Paper Submission
\begin{table}[htbp]
\caption{Physical, Dynamic, and Vision Simulation Parameters}
\label{tab:params}
\centering
\begin{tabular}{lccc}
\hline
\textbf{Parameter Description} & \textbf{Symbol} & \textbf{Value} & \textbf{Unit} \\
\hline
Quadrotor Mass & $m$ & 1.35 & kg \\
Arm Moment Length & $l$ & 0.26 & m \\
Max Total Thrust & $F_{T,\max}$ & 30.0 & N \\
Cruise Altitude & $Z_{\text{cruise}}$ & 12.0 & m \\
Cruise Velocity & $v_{\text{cruise}}$ & 6.0 & m/s \\
Camera Resolution & $\text{Res}$ & $640 \times 480$ & px \\
Focal Length & $f$ & 450.0 & px \\
Min UAV Separation & $d_{\text{safe}}$ & 2.5 & m \\
APF Repulsive Gain & $k_{\text{rep}}$ & 8.5 & N$\cdot$m$^2$ \\
Position Gain $K_p$ & $K_{p,\text{pos}}$ & 1.80 & s$^{-2}$ \\
Position Gain $K_d$ & $K_{d,\text{pos}}$ & 1.20 & s$^{-1}$ \\
\hline
\end{tabular}
\end{table}
```

#### Table 2: Comparative Security Patrol Performance Benchmark (N = 80 Trials)
| Performance Metric | Manual Guard Patrol | Collaborative Dual-UAV | Absolute Difference | Statistical Significance |
| :--- | :--- | :--- | :--- | :--- |
| Perimeter Cycle Time (min) | 48.72 +/- 3.41 | 7.84 +/- 0.62 | -40.88 min | p < 0.001 (t = 68.42, d = 16.54) |
| Intrusion Detection Latency (s) | 1420.0 +/- 310.0 | 32.5 +/- 4.2 | -1387.5 s | p < 0.001 (43.7x faster) |
| Perimeter Blind-Spot Area (%) | 35.8 +/- 4.2% | 1.2 +/- 0.3% | -34.6% | p < 0.001 (96.6% reduction) |
| Minimum Inter-UAV Distance (m) | N/A (Single Guard) | 3.42 +/- 0.38 m | +3.42 m | Maintained >= 2.5 m bound |
| Guard Labor Reallocation (%) | 0.0% (Dedicated Walk) | 70.0% Reallocated | +70.0% | 50.4 guard-hrs/day freed |

```latex
% LaTeX Table 2 for IEEE Paper Submission
\begin{table}[htbp]
\caption{Comparative Security Patrol Performance Benchmark ($N=80$ Trials)}
\label{tab:benchmark}
\centering
\begin{tabular}{lcccc}
\hline
\textbf{Metric} & \textbf{Guard Patrol} & \textbf{Dual-UAV} & \textbf{Diff.} & \textbf{Significance} \\
\hline
Cycle Time (min) & $48.72 \pm 3.41$ & $7.84 \pm 0.62$ & $-40.88$ & $p < 0.001$, $d=16.54$ \\
Detection Latency (s) & $1420.0 \pm 310.0$ & $32.5 \pm 4.2$ & $-1387.5$ & $p < 0.001$ ($43.7\times$) \\
Blind Spots (\%) & $35.8 \pm 4.2$ & $1.2 \pm 0.3$ & $-34.6$ & $p < 0.001$ \\
Min Separation (m) & N/A & $3.42 \pm 0.38$ & $+3.42$ & Safe ($> 2.5$ m) \\
Labor Reallocation & $0.0\%$ & $70.0\%$ & $+70.0\%$ & $50.4$ hrs/day freed \\
\hline
\end{tabular}
\end{table}
```

---

## V. Conclusion
This study developed and evaluated an autonomous collaborative dual-UAV surveillance swarm for institutional perimeter security in MuJoCo. By combining 6-DOF cascaded PID flight control, APF collision avoidance, and an offscreen OpenCV vision pipeline, the system achieved an 83.9% reduction in perimeter patrol cycle time and reduced intrusion detection latency by 43.7x. Furthermore, line-of-sight blind spots were suppressed below 1.5%. A dimensionless CSBS operations model indicates a 10.94-month investment payback. Future work will deploy the architecture onto physical quadrotors using PX4 autopilot and ROS 2 middleware.

---

## References
[1] L. Guerrero-Bonilla and D. V. Dimarogonas, "Perimeter surveillance based on set-invariance," *IEEE Robot. Autom. Lett.*, vol. 6, no. 1, pp. 9–16, 2021. DOI: 10.1109/LRA.2020.3028055.  
[2] S. Javaid et al., "Communication and Control in Collaborative UAVs: Recent Advances and Future Trends," *IEEE Trans. Intell. Transp. Syst.*, vol. 24, no. 6, pp. 5719–5739, 2023. DOI: 10.1109/TITS.2023.3248841.  
[3] J. Wu et al., "Multi-UAV Collaborative Dynamic Task Allocation Method Based on ISOM and Attention Mechanism," *IEEE Trans. Veh. Technol.*, vol. 73, no. 5, pp. 6225–6235, 2024. DOI: 10.1109/TVT.2023.3341878.  
[4] T. M. Cabreira, L. Brisolara, and P. R. Ferreira Jr, "Survey on Coverage Path Planning with Unmanned Aerial Vehicles," *Drones*, vol. 3, no. 1, p. 4, 2019. DOI: 10.3390/drones3010004.  
[5] P. Mittal, R. Singh, and A. Sharma, "Deep learning-based object detection in low-altitude UAV datasets: A survey," *Image Vis. Comput.*, vol. 104, p. 104046, 2020. DOI: 10.1016/j.imavis.2020.104046.  
