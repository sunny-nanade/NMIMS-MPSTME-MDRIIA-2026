# Group 02: AI Companion Robot for Remote Elderly Supervision and Fall Emergency Response

---

## 1. Authorized Research Title
> "How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?"

### Core Engineering Focus
* Physics and Kinematics: Google DeepMind MuJoCo multi-body physics simulation with differential-drive base, elevated camera mast ($1.10\text{ m}$), and residential clutter.
* Kinematic Vision: MediaPipe BlazePose 33-point skeletal extraction, 2nd-order Butterworth filtering ($f_c = 5.0\text{ Hz}$), vertical descent velocity ($|v_z| \ge 1.80\text{ m/s}$), aspect ratio inversion ($\text{AR} \ge 1.20$), and torso inclination ($\theta_{\text{torso}} \ge 60^\circ$).
* Safe Navigation & Standoff: ISO 13482:2014 compliant deceleration controller maintaining standoff distance $d_{\text{stop}} \in [0.80, 1.20]\text{ m}$.
* CSBS Healthcare Economics: Dimensionless model demonstrating long-lie reduction ($97.45\%$), acute hospital bed-day conservation ($14.20\text{ days}$), operational parity ratio $\kappa \le 0.30$, and capital payback horizon ($4.13\text{ months}$).

---

## 2. Student Engineering Team Matrix

| Roll No | SAP ID | Student Name | Technical Specialization | Assigned Branch |
| :--- | :--- | :--- | :--- | :--- |
| `E007` | `70362400022` | **Kamakshi Bahuguna** | Computer Vision, Pose Kinematics & Edge Inference Specialist | `feat/e007-vision-pose-kinematics` |
| `B029` | `70362400037` | **Devanshi Sachin Kambli** | MuJoCo Physics, Domestic Navigation & Healthcare Economics Lead | `feat/b029-mujoco-physics-navigation` |

---

## 3. Foundational Literature and Academic Benchmarks (5 Verified Papers)

Students must study, benchmark against, and cite these 5 authentic peer-reviewed papers. See [docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md](./docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md) for the complete mathematical extraction and gap analysis.

1. **Lightweight Edge Pose Kinematics for Fall Detection (2024):**
   * *Wang & Deng*, "Enhancing elderly care: Efficient and reliable real-time fall detection algorithm", *Digital Health*, vol. 10, art. no. 20552076241233690, 2024.
   * DOI: [10.1177/20552076241233690](https://doi.org/10.1177/20552076241233690)
   * Focus: BlazePose 33-point skeletal landmark extraction, mid-hip descent velocity, bounding box aspect ratio inversion, $29.7\text{ FPS}$ edge CPU inference.

2. **Automated Edge Fall Detection with YOLO & MediaPipe (2025):**
   * *Kothari & Chakurkar*, "Towards safer environments: A YOLO and MediaPipe-based human fall detection system with alert automation", *MethodsX*, vol. 15, art. no. 103623, 2025.
   * DOI: [10.1016/j.mex.2025.103623](https://doi.org/10.1016/j.mex.2025.103623)
   * Focus: Dual-stage bounding box filtering, automated alert dispatch pipeline, and post-fall stillness observation window ($\tau_{\text{quiet}} = 3.0\text{ s}$).

3. **Socially Assistive Robot Architecture for Eldercare (2022):**
   * *Romero-Garces et al.*, "CLARA: Building a Socially Assistive Robot to Interact with Elderly People", *Designs*, vol. 6, no. 6, art. no. 125, 2022.
   * DOI: [10.3390/designs6060125](https://doi.org/10.3390/designs6060125)
   * Focus: Mechatronic mast height ($1.10\text{ m}$), differential-drive base dimensioning, and safe domestic navigation in eldercare facilities.

4. **Smart Home Fall Detection and Ambient Baselines (2020):**
   * *Ding & Wang*, "A WiFi-Based Smart Home Fall Detection System Using Recurrent Neural Network", *IEEE Transactions on Consumer Electronics*, vol. 66, no. 4, pp. 308–317, 2020.
   * DOI: [10.1109/TCE.2020.3021398](https://doi.org/10.1109/TCE.2020.3021398)
   * Focus: Benchmarking detection latency and multipath noise filtering in domestic environments, providing an ambient sensing comparison baseline.

5. **Clinical Consequences of the "Long Lie" (2022):**
   * *Kubitza et al.*, "Therapy options for those affected by a long lie after a fall: a scoping review", *BMC Geriatrics*, vol. 22, art. no. 582, 2022.
   * DOI: [10.1186/s12877-022-03258-2](https://doi.org/10.1186/s12877-022-03258-2)
   * Focus: Clinical definition of the long lie ($> 1\text{ hr}$), establishing the baseline $18.4\text{ day}$ acute hospital stay and muscle breakdown pathology.

---

## 4. Directory Structure
```
Group_02_Kamakshi_Devanshi/
|-- README.md                             <- Group research charter, literature matrix, and status
|-- RESEARCH_AND_IMPLEMENTATION_GUIDE.md  <- Complete technical dossier, kinematic proofs, and viva defense
|-- docs/
|   |-- LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md <- Detailed analysis of 5 papers & gap matrix
|   `-- TEAM_ROSTER.json                  <- Commit attribution registry
|-- models/
|   `-- elderly_companion_base.xml        <- Physical MuJoCo MJCF model with elevated mast
|-- src/
|   |-- fall_detection_kinematics.py      <- MediaPipe pose kinematics and alert state machine
|   `-- test_env.py                       <- Local toolchain verification script
`-- analytics/
    `-- geriatric_care_economics.py       <- CSBS dimensionless healthcare economic model
```

---

## 5. Sprint Onboarding Checklist (Sprint 0)
- [ ] Every team member clones repository locally.
- [ ] Each student creates their assigned feature branch (`feat/<roll_no>-...`).
- [ ] Study assigned research papers in [docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md](./docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md).
- [ ] Execute `python src/test_env.py` and confirm clean execution.
- [ ] Execute `python src/fall_detection_kinematics.py` and review simulated fall vs ADL detection logs.
- [ ] Execute `python analytics/geriatric_care_economics.py` and inspect dimensionless ROI outputs.
- [ ] Update `docs/TEAM_ROSTER.json` with verified GitHub usernames.
- [ ] Submit and merge Sprint 0 Pull Request into `main`.
