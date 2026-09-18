# SVKM's NMIMS MPSTME | Department of Computer Science & Business Systems (CSBS)
## Modern Day Robotics & Its Industrial Applications (MDRIIA - 702CO0E012)
### Problem-Based Learning (PBL) Research Cohort — Academic Year 2026–2027

**Institutional Leadership & Academic Directorate | MPSTME**  
**Pedagogical Model:** Aalborg-UNESCO Problem-Based Learning (PBL) & CDIO Engineering Studio  
**Target Exhibition:** NMIMS IUCEE Annual Engineering Symposium & Premier Robotics Conferences (IEEE INDICON / AIR / CASE / RO-MAN / IROS)  

---

## 📌 Master Cohort Repository Overview
This repository serves as the centralized version-controlled monorepo for all **10 authorized student research groups** in the MDRIIA course (CSBS Sem VI).

Every student team maintains a dedicated workspace containing their DeepMind MuJoCo physics models (`.xml`), closed-loop Python controllers, sensor telemetry loggers, CSBS business economic models, and empirical research manuscripts.

---

## 📂 Group Directory & Research Project Index

| Group # | Group Workspace Folder | Domain / Project Topic | Student Researchers | Authorized Research Title |
| :---: | :--- | :--- | :--- | :--- |
| **Group 01** | [Group_01_Khushal_Priyal_Ishita_Sowmya](./Group_01_Khushal_Priyal_Ishita_Sowmya) | Autonomous robot for delivery of critical medicines for ICUs | Khushal Asnani (E006), Priyal Kaushal Deputy (E016), Ishita Ranjan (E054), Sowmya Satish (E060) | To what extent can an autonomous mobile medicine-delivery robot (simulated in MuJoCo with dynamic obstacle avoidance) reduce ICU nurses' non-patient-facing logistics transit time and optimize labor reallocation, where clinical studies document nurses spending approximately 28% of their shift on supply retrieval? |
| **Group 02** | [Group_02_Kamakshi_Devanshi](./Group_02_Kamakshi_Devanshi) | AI companion robot for remote supervision, medication reminders and emergency response | Kamakshi Bahuguna (E007), Devanshi Sachin Kambli (B029) | How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone? |
| **Group 03** | [Group_03_Kashish_Vaishnavi_Daneeka](./Group_03_Kashish_Vaishnavi_Daneeka) | Autonomous ambulance robot for medical emergencies | Kashish Praveen Jain (E026), Vaishnavi Parashar (E046), Daneeka Abhijeet Roy (E057) | Can an autonomous last-mile ground AED delivery vehicle simulated in MuJoCo reduce time-to-first-shock below urban ambulance congestion delays (15-20 minutes), given that sudden cardiac arrest survival drops 7-10% for every minute without defibrillation? |
| **Group 04** | [Group_04_Rishi_Nicholas_Jai](./Group_04_Rishi_Nicholas_Jai) | Space Junk Collector | Rishi Vinod Koli (E034), Nicholas Lewis (E035), Jai Maini (E036) | How can a multi-arm robotic gripper mechanism simulated in MuJoCo utilize impedance contact control to synchronize with and capture tumbling non-cooperative orbital debris in LEO while mitigating collision impulse and momentum transfer? |
| **Group 05** | [Group_05_Muaaz_Aditya_Zaid_Soumya](./Group_05_Muaaz_Aditya_Zaid_Soumya) | MPSTME GUARDIAN | Muaaz Mohammed Iqbal Shaikh (E043), Aditya Rajkumar (E051), Zaid Rezaur Rahman (E075), Soumya Subhankar Ranasingh (E077) | To what extent can a collaborative dual-UAV surveillance system simulated in MuJoCo optimize campus perimeter patrol cycle time and OpenCV human detection latency compared to static security guard patrols? |
| **Group 06** | [Group_06_Arush_Ronit_Harshvardhan](./Group_06_Arush_Ronit_Harshvardhan) | Solar Panel Cleaning | Arush Ashish Patil (E048), Ronit Rajput (E052), Harshvardhan Sahi (E058) | How can an autonomous crawler cleaning robot simulated in MuJoCo recover soiling-induced energy losses (15-18% monthly) on inclined commercial rooftop solar arrays while reducing cleaning cycle operational expenditure compared to manual labor? |
| **Group 07** | [Group_07_Soumil_Aditya_Priyansh](./Group_07_Soumil_Aditya_Priyansh) | Messy Room Cleaning | Soumil Patro (E050), Aditya Raju Shah (E062), Priyansh Thakkar (E066) | How can an autonomous mobile manipulator simulated in MuJoCo for clutter classification and grasp planning reduce daily patient-room turnaround time for hospital housekeeping staff from the baseline 10-20 minutes per room? |
| **Group 08** | [Group_08_Manikya_Shourya_Keswani_Vora](./Group_08_Manikya_Shourya_Keswani_Vora) | UAV for emergency supply delivery in floods (SkyHydro) | Manikya Rathore (E056), Shourya Garg (E020), Keswani Laksh (E032), Vora Jash (E067) | To what extent can an autonomous vision-guided multirotor UAV simulated in MuJoCo for payload-range trade-offs optimize last-mile medical relief drop accuracy during NDRF flood operations while establishing fleet utilization payback parity against ground transport? |
| **Group 09** | [Group_09_Arnav_Vihan_Pratik](./Group_09_Arnav_Vihan_Pratik) | UGV for defence and hazardous applications | Arnav Saurabh Surve (E064), Vihan Shripad Joshi (E070), Pratik Mangesh Gaikwad (E073) | How can an autonomous ground vehicle utilizing simulated LiDAR rangefinders and traversability cost-mapping in MuJoCo navigate unknown unstructured hazardous terrain while reducing teleoperation cognitive workload and communication latency? |
| **Group 10** | [Group_10_Soumya_Harshal_Arham_Aneesh](./Group_10_Soumya_Harshal_Arham_Aneesh) | Intelligent robotics assistant for precision surgical task | Soumya Singh (E071), Harshal Khandekar (E033), Arham Khan (E069), Aneesh Kumar (E076) | How can a 7-DOF surgical manipulator simulated in MuJoCo implement inverse kinematics Jacobian damping and low-pass tremor filtering to achieve sub-0.5 mm needle placement accuracy under simulated physiological surgeon hand tremor? |

---

## 🚀 Student Git Submission & Branching Workflow

### 1. Zero Direct Commits to `main`
The `main` branch is protected. All code contributions must occur via personal feature branches and Pull Requests.

### 2. Individual Feature Branching
Every student must work on their personal feature branch:
```bash
# 1. Clone this repository
git clone https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026.git
cd NMIMS-MPSTME-MDRIIA-2026

# 2. Switch to your personal feature branch
git checkout -b feat/<your-roll-no>-<task-name>

# 3. Work ONLY within your group directory
cd Group_XX_<Your_Names>

# 4. Run environment verification script
python src/test_env.py

# 5. Stage and commit your changes using Conventional Commits
git add .
git commit -m "feat(group-XX): implement MuJoCo kinematics controller and telemetry"

# 6. Push your branch to GitHub
git push -u origin feat/<your-roll-no>-<task-name>

# 7. Open a Pull Request (PR) into 'main' via GitHub web UI
```

---

## 📅 PBL Sprint Milestones & Deliverables
* **Sprint 0 (Week 1 - Onboarding & Environment):** Repository clone, `docs/TEAM_ROSTER.json` verification, successful execution of `src/test_env.py`.
* **Sprint 1 (Weeks 2-4 - MJCF Physics Model):** Complete MuJoCo XML kinematic model (actuators, geoms, joint limits, friction parameters).
* **Sprint 2 (Weeks 5-7 - Closed-Loop Control & Telemetry):** Python control script (PID / state machine / trajectory generation) and 500Hz CSV data logger.
* **Sprint 3 (Weeks 8-10 - CSBS Business ROI & IEEE Draft):** Dimensionless economic model (CapEx/OpEx payback, labor reallocation efficiency), statistical validation (N >= 50 trials, Student's t-test), 4-page IEEE manuscript draft.
* **Sprint 4 (Weeks 11-12 - Symposium & Final Defense):** Live presentation slides, 60fps physics simulation video, code defense.

---

## ⚖️ Academic Integrity & Anti-Free-Riding Enforcement
* Commits must be distributed across at least **6 distinct weeks**.
* Bulk code dumps immediately preceding deadlines will be rejected by the automated audit engine.
* Individual grading directly correlates with verified Git commit authorship in `docs/TEAM_ROSTER.json`.
