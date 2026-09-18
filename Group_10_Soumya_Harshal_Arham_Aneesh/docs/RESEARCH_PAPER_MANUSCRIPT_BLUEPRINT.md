# Inverse Kinematics Jacobian Damping and Physiological Tremor Suppression in a 7-DOF Robotic Surgical Assistant

## Authors:
- Soumya Singh (E071)
- Harshal Khandekar (E033)
- Arham Khan (E069)
- Aneesh Kumar (E076)

## Department of Computer Science & Business Systems

---

## Abstract
Precision needle placement in minimally invasive microsurgery (ophthalmology, neurosurgery, microvascular anastomosis) demands positioning tolerances below 0.50 mm. However, unavoidable physiological hand tremor among surgeons exhibits involuntary oscillatory amplitudes of 0.30 to 0.80 mm in the 8 to 12 Hz frequency band, exacerbating the risk of accidental tissue laceration and requiring costly revision interventions. This paper presents a 7-DOF redundant surgical robotic manipulator framework simulated in Google DeepMind MuJoCo featuring singularity-robust Damped Least Squares (DLS) inverse kinematics and real-time low-pass digital tremor filtering. The system models surgeon voluntary intent corrupted by physiological tremor and passes commanded trajectories through a 2nd-order Butterworth filter designed to maintain phase lag below 22.5 ms. Across a 100-trial experimental benchmark under simulated surgeon tremor, the filtered robotic assistant reduces 3D needle tip Root Mean Square Error (RMSE) from an unfiltered baseline of 0.82 mm to 0.31 mm, achieving a 62.2% precision enhancement and comfortably exceeding the sub-0.5 mm clinical safety threshold. Technoeconomic analysis based on operating room utilization and surgical complication avoidance demonstrates a dimensionless cost parity of 0.24, yielding capital amortization within 7.1 operating months.

**Keywords:** Surgical robotics, physiological tremor suppression, 7-DOF redundant manipulator, Damped Least Squares, inverse kinematics, sub-millimeter precision, MuJoCo simulation, operating room economics.

---

## I. Introduction
Microsurgical interventions require dexterous manipulation at spatial scales where human physiological limitations become the governing constraint. Even experienced surgeons exhibit involuntary physiological hand tremor—a complex oscillatory phenomenon driven by neuromuscular firing rhythms that manifests predominantly in the 8-12 Hz frequency range with peak-to-peak amplitudes exceeding 500 $\mu$m.

In delicate procedures such as retinal vein cannulation or deep-brain electrode placement, tremor-induced positioning deviations can cause permanent structural trauma. Robotic surgical assistants provide mechanical decoupling and digital signal filtering to suppress involuntary tremor while faithfully reproducing voluntary surgeon intent.

This research investigates three central questions:
1. How effectively can a 7-DOF redundant articulated arm execute Damped Least Squares inverse kinematics to maintain trajectory smoothness near workspace singularities?
2. To what degree can discrete-time low-pass filtering suppress 8-12 Hz tremor oscillations while constraining phase latency below 25 ms?
3. What quantitative improvements in needle targeting precision (sub-0.5 mm RMSE) and operating room economics does this framework deliver?

---

## II. Related Work
Active tremor compensation in handheld instruments was demonstrated by Yang et al. [1] with the 6-DOF "Micron" manipulator. High-level surgical robotics architecture and computer-integrated surgery were established by Taylor and Stoianovici [2]. Singularity management in redundant manipulators was formulated by Chiaverini [3], demonstrating task-priority damped least squares for real-time control. Biophysical tremor characterization and adaptive Fourier filtering were pioneered by Riviere and Thakor [4]. In operating room economics, Childers and Maggard-Gibbons [5] quantified minute-by-minute OR costs, establishing the financial imperative for surgical complication and revision reduction. This paper integrates redundant manipulator dynamics with digital filtering and clinical economics.

---

## III. Kinematics, Filtering & Physics Simulation

### A. 7-DOF Manipulator Architecture
The robotic assistant is implemented in MuJoCo MJCF XML format (`models/surgical_7dof_robot.xml`). The serial kinematic chain consists of 7 revolute joints (shoulder yaw/pitch, elbow roll/pitch, forearm roll, wrist pitch/roll) terminating in a fine-gauge surgical needle tool.

### B. Singularity-Robust Damped Least Squares IK
To prevent extreme joint accelerations near singular arm configurations, joint velocity commands are computed via:

$$\dot{q} = J^T (J J^T + \lambda^2 I)^{-1} \dot{x}_{\text{des}} + (I - J^* J) \dot{q}_{\text{null}}$$

where damping parameter $\lambda$ scales dynamically according to Yoshikawa's manipulability index.

### C. Digital Tremor Filtering Pipeline
Simulated surgeon input signals combine low-frequency voluntary motion ($< 1.0$ Hz) with synthetic 8-12 Hz physiological tremor. A discrete 2nd-order Butterworth filter ($f_c = 3.5$ Hz) attenuates tremor frequencies by over 18 dB while maintaining group delay $\tau_{\text{delay}} = 21.8$ ms, well below the 25 ms psychophysical teleoperation threshold.

---

## IV. Experimental Results & Discussion

### A. Sub-Millimeter Needle Placement Accuracy
The system was benchmarked across 100 simulated needle insertion trials under three operating conditions:
- **Unfiltered Teleoperation:** Mean RMSE = 0.82 mm (std 0.09 mm); 96% of runs breached the 0.50 mm safety bound.
- **Basic Exponential Smoothing:** Mean RMSE = 0.46 mm (std 0.06 mm); 32 ms phase lag.
- **DLS + 2nd-Order Butterworth:** Mean RMSE = 0.31 mm (std 0.04 mm); 21.8 ms phase lag, achieving 100% compliance with the sub-0.5 mm threshold ($p < 0.001$).

### B. Spectral Attenuation Analysis
Figure 2(c) displays the power spectral density (PSD) of the needle tip motion. The 8-12 Hz tremor peak is attenuated by 19.4 dB, while the low-frequency voluntary motion profile is preserved with over 98.5% fidelity.

### C. Technoeconomic Operational Parity
Operational cost parity $\kappa = 0.24$ demonstrates a 76.0% OpEx advantage over conventional surgical teams experiencing baseline revision rates. Capital investment amortizes within 7.1 operating months based on procedural throughput expansion and complication avoidance.

---

## V. Conclusion
This study demonstrates that a 7-DOF redundant surgical manipulator with Damped Least Squares inverse kinematics and real-time digital filtering achieves sub-0.5 mm needle placement accuracy, overcoming physiological hand tremor with negligible phase latency. Future research will explore bio-impedance force feedback integration for adaptive puncture detection.

---

## References
- [1] S. Yang, R. A. MacLachlan, and C. N. Riviere, "Manipulator Design and Operation of a Six-Degree-of-Freedom Handheld Tremor-Canceling Microsurgical Instrument," *IEEE/ASME Trans. Mechatronics*, vol. 20, no. 2, pp. 761-772, 2015. DOI: 10.1109/TMECH.2014.2320858
- [2] R. H. Taylor and D. Stoianovici, "Medical Robotics in Computer-Integrated Surgery," *IEEE Trans. Rob. Autom.*, vol. 19, no. 5, pp. 765-781, 2003. DOI: 10.1109/TRA.2003.817058
- [3] S. Chiaverini, "Singularity-robust task-priority redundancy resolution for real-time kinematic control of robot manipulators," *IEEE Trans. Rob. Autom.*, vol. 13, no. 3, pp. 398-410, 1997. DOI: 10.1109/70.585902
- [4] C. N. Riviere and N. V. Thakor, "Adaptive canceling of physiological tremor for improved precision in microsurgery," *IEEE Trans. Biomed. Eng.*, vol. 45, no. 7, pp. 839-846, 1998. DOI: 10.1109/10.686791
- [5] C. P. Childers and M. Maggard-Gibbons, "Understanding Costs of Care in the Operating Room," *JAMA Surg.*, vol. 153, no. 4, p. e176233, 2018. DOI: 10.1001/jamasurg.2017.6233
