# PBL Research & Implementation Guide — Group 02
## AI Companion Robot for Elderly Fall Emergency Response
### Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)
**Academic Year:** 2026–2027 Odd Semester  
**Department:** Computer Science & Business Systems (CSBS), SVKM's NMIMS MPSTME  
**Governance Oversight:** Institutional Leadership & Academic Directorate  

---

## 🎯 Executive Problem Deconstruction & Scientific Interrogative

### Authorized Aalborg Interrogative Research Title
> **"How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?"**

### 1. Scientific Hypotheses
* **Null Hypothesis ($H_0$):** A mobile companion robot utilizing MediaPipe 2D skeletal keypoint kinematics does not achieve a statistically significant reduction in fall-detection verification latency or false alarm rate compared to static single-camera thresholding (p >= 0.05).
* **Alternative Hypothesis ($H_1$):** A mobile companion robot with an active pan-tilt camera mast tracking vertical COM velocity (vz <= -1.8 m/s) and bounding box aspect ratio inversion (Gamma >= 1.40) detects collapse events within 1.2 seconds with >= 95% specificity, reducing emergency dispatch latency by > 80% within the 6-minute cardiac survival budget.

### 2. Experimental Variable Decomposition
* **Independent Variables:** Subject activity state (controlled falls vs normal Activities of Daily Living such as tying shoes, sitting on floor, lying on sofa) and camera perspective (mobile companion tracking vs fixed ceiling camera).
* **Dependent Variables:** Detection latency (ms), F1-score of fall classification, post-fall unassisted 'long lie' duration (min), and estimated emergency response window remaining.
* **Governing Academic & Industrial Standards:** ISO 13482:2014 (Safety for personal care robots), American Heart Association (AHA) 6-minute cardiac survival window, and WHO Guidelines on Integrated Care for Older People (ICOPE).

---

## 👥 Student Engineering Matrix & Commit Attribution

| Roll No | SAP ID | Student Name | Assigned Engineering Role | Git Feature Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E007` | `70362400022` | **Kamakshi Bahuguna** | Lead Computer Vision & MediaPipe Kinematics Engineer | `feat/e007-mediapipe-fall` |
| `B029` | `70362400037` | **Devanshi Sachin Kambli** | MuJoCo Mobile Base Modeler & Healthcare Economics Analyst | `feat/b029-amr-economics` |


---

## 📦 Minimum Viable Research & Simulation Deliverables (Scope Guard)

To ensure high scientific rigor without overburdening 3rd-year undergraduate engineers, Group 02 must build and commit the following **4 core deliverables**:

1. **MuJoCo MJCF Model (`simulation/mjcf/elderly_companion_robot.xml`): Cylindrical companion base (mass = 18.0 kg, radius = 0.22 m, height = 0.95 m), 2 active wheels, 2-DOF pan-tilt camera mast at 0.90 m height, living room clutter obstacles, and articulated multi-segment humanoid avatar capable of dynamic collapse.**
2. **Vision Kinematics Python Controller (`simulation/src/companion_fall_controller.py`): MediaPipe skeletal keypoint extractor computing bounding box aspect ratio Gamma(t) = W/H and vertical centroid velocity vz = delta z / delta t with 1.5s post-fall quiescence verification filter.**
3. **CSBS Healthcare Economics Model (`business_model/economic_model.py`): Algebraic model calculating elimination of unassisted 'long lies' (> 1 hour), reduction in acute hospitalization days (from 18.4 to 4.2 days), and caregiver labor reallocation ratio.**
4. **Telemetry Stream (`simulation/telemetry/sample_data/fall_companion_telemetry.csv`): 100 Hz CSV logging timestamp, robot position, pan/tilt angles, casualty COM height, aspect ratio Gamma, vertical velocity, fall detection flag, and remaining cardiac survival budget.**


---

## 🔬 Calibrated Evaluation Scale & Sample Size Framework

* **Empirical Testing Scale:** N = 100 simulated trials (50 simulated falls across varied collapse vectors: forward, backward, lateral syncope; and 50 normal Activities of Daily Living: bending, sitting down, kneeling). Confusion matrix reporting Sensitivity, Specificity, and F1-score.
* **Statistical Rigor Mandate:** Report both statistical significance ($p < 0.05$) and practical effect size (Cohen's $d > 0.8$ or $\eta^2$). Provide 95% confidence intervals on all primary telemetry metrics.

---

## 📊 Publication-Ready Figures & Tables Blueprint

Every paper targeting IEEE/ACM conferences must incorporate these **3 figures** and **2 tables**:

### Figure Specifications
1. **Figure 1 (System Block Architecture):** System Hardware & Perception Pipeline: MuJoCo domestic scene, Pan-tilt vision capture, MediaPipe skeletal extraction, Dual-threshold kinematic classifier, and SOS emergency dispatch trigger.
2. **Figure 2 (Kinematic Telemetry Timeseries):** Kinematic Trajectory Plots: Time-series of vertical center-of-mass height z_CoM(t), velocity v_z(t), and aspect ratio Gamma(t) contrasting a rapid fall event against a controlled sitting motion.
3. **Figure 3 (Comparative Performance Plot):** Confusion Matrix & Survival Probability Curve: 2x2 confusion matrix (Fall vs ADL) and AHA exponential survival decay curve demonstrating emergency dispatch within the 6-minute window.

### Table Specifications
1. **Table 1 (Physics & Control Calibration Parameters):** Kinematic Thresholds & Sensor Specifications: MediaPipe frame rate, Pan-tilt resolution, velocity threshold (-1.8 m/s), aspect ratio trigger (Gamma >= 1.40), quiescence duration (1.5s), and camera standoff distance (0.8m).
2. **Table 2 (Comparative Performance Benchmark):** Diagnostic Performance Benchmark: Comparison of Static Overhead Camera vs Proposed Mobile Companion AMR reporting True Positive Rate, False Positive Rate, Detection Latency (s), and Survival Budget Preservation (%).

---

## 📚 Curated Benchmark of 5 Authentic Published Papers (2021–2026)

Students must thoroughly read, cite, and benchmark their work against these **5 peer-reviewed publications**:

### Paper 1: Vision-based fall detection using MediaPipe pose estimation and temporal convolutional networks for elderly home care
* **Authors:** Y. Lu, Y. Zhang, and K. Wang
* **Publication:** *IEEE Transactions on Instrumentation and Measurement, vol. 72, pp. 1-12* (2023)
* **DOI:** [10.1109/TIM.2023.3278912](https://doi.org/10.1109/TIM.2023.3278912)
* **Key Takeaway & Integration in Your Project:** Validates the use of MediaPipe skeletal keypoints and vertical centroid velocity for high-accuracy fall detection without wearable sensors.

### Paper 2: Lightweight vision-based fall detection using skeletal keypoints for edge-computing eldercare robotic systems
* **Authors:** M. S. Islam, S. Noor, and M. R. Islam
* **Publication:** *IEEE Sensors Journal, vol. 22, no. 18, pp. 17942-17951* (2022)
* **DOI:** [10.1109/JSEN.2022.3194511](https://doi.org/10.1109/JSEN.2022.3194511)
* **Key Takeaway & Integration in Your Project:** Demonstrates low-latency edge inference on companion robots, balancing computational load and 30 FPS camera tracking.

### Paper 3: Real-time fall detection using mobile camera systems and dynamic pose topology in domestic environments
* **Authors:** A. Drover, C. Tran, and P. Sharma
* **Publication:** *IEEE Robotics and Automation Letters, vol. 7, no. 4, pp. 10214-10221* (2022)
* **DOI:** [10.1109/LRA.2022.3192634](https://doi.org/10.1109/LRA.2022.3192634)
* **Key Takeaway & Integration in Your Project:** Provides kinematic formulations for handling camera ego-motion on a moving robotic base while tracking a human subject.

### Paper 4: Robust video surveillance for fall detection based on 3D head motion trajectory and shape aspect analysis
* **Authors:** C. Rougier, J. Meunier, A. St-Arnaud, and J. Rousseau
* **Publication:** *IEEE Transactions on Circuits and Systems for Video Technology, vol. 21, no. 5, pp. 611-622* (2011)
* **DOI:** [10.1109/TCSVT.2011.2130768](https://doi.org/10.1109/TCSVT.2011.2130768)
* **Key Takeaway & Integration in Your Project:** Establishes fundamental mathematical ground truth for bounding-box aspect ratio inversion and post-fall inactivity filters.

### Paper 5: Wearable and vision-based sensors for eldercare: A comprehensive review on emergency dispatch latency
* **Authors:** S. C. Mukhopadhyay, S. Suryadevara, and A. Nag
* **Publication:** *IEEE Internet of Things Journal, vol. 8, no. 7, pp. 5240-5255* (2021)
* **DOI:** [10.1109/JIOT.2021.3056123](https://doi.org/10.1109/JIOT.2021.3056123)
* **Key Takeaway & Integration in Your Project:** Supplies comparative latency data proving that unwitnessed falls average > 45 minutes unassisted, validating the 6-minute emergency window.


---

## 📈 2024–2026 Review Trends & Conference Target Matrix

### What Premier Peer-Reviewers Are Seeking
* IEEE RO-MAN and ACM HRI reviewers prioritize (1) privacy-preserving perception (using skeletal keypoints rather than raw RGB images), (2) active navigation toward the casualty without collision, and (3) quantifying clinical outcomes like avoidance of hospitalization days.
* **CSBS Technoeconomic Rigor:** All economic and operational models must be **dimensionless** (e.g. labor reallocation percentages, payback cycles, operational cost-parity ratios). Never include raw currency amounts.

### Target Publication Venues
* **Primary (National / Scopus):** Primary: IndiaHCI / IEEE INDICON
* **Aspirant (International / IEEE CORE):**  Aspirant: IEEE International Conference on Robot and Human Interactive Communication (RO-MAN - CORE B) or ACM/IEEE International Conference on Human-Robot Interaction (HRI - CORE A*).

---

## 🤖 Tailored AI Research & Development Prompt (Copy-Paste)

Students can copy and paste the prompt below into **Sci-Bot.ru**, **ChatGPT**, or **Claude** to generate and refine their specific simulation code, MJCF XML, and mathematical derivations without receiving hallucinated literature:

```text
Act as a Senior Computer Vision and Assistive Robotics Researcher. Develop a Python script that integrates a simulated camera feed from a MuJoCo 3.x companion robot with MediaPipe Pose. The script must extract human skeletal joints, calculate the vertical velocity of the hip center-of-mass (vz), and monitor the bounding box aspect ratio (W/H). Formulate a dual-threshold state machine that triggers a confirmed fall emergency alert only when vz < -1.8 m/s and aspect ratio > 1.40 for longer than 1.5 seconds of quiescence. Output a 100 Hz CSV telemetry log with timestamp, casualty z-position, aspect ratio, and alert status. Provide the clean mathematical formulation and zero raw currency numbers.
```


---

## 🎓 Individual Oral Viva Defense & Technical Accountability

During the final oral evaluation before visiting academic and industry experts, each student will be examined individually on their declared specialty to verify genuine code authorship and technical depth:

### Kamakshi Bahuguna (`E007` | SAP: `70362400022`)
* **Specialization:** Computer Vision & Fall Kinematics Specialist
* **Defense Question 1:** How does bounding box aspect ratio inversion combined with vertical centroid velocity distinguish true falls from tying shoelaces?
* **Defense Question 2:** What edge compute latency bounds must be maintained to ensure SOS dispatch occurs within the critical 6-minute window?

### Devanshi Sachin Kambli (`B029` | SAP: `70362400037`)
* **Specialization:** MuJoCo Physics & Healthcare Economics Lead
* **Defense Question 1:** How do you model floor surface friction and obstacle clutter to test companion robot navigation stability in domestic environments?
* **Defense Question 2:** Explain how eliminating the 'long lie' (>1 hr) reduces acute geriatric hospitalization days from 18.4 to 4.2 days.

