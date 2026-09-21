# Engineering Research and Implementation Guide
## Group: MDRIIA_GROUP_11
## Project: Autonomous Mobile Robot for Solar PV Defect Inspection & Anomaly Detection
## Student Lead: Daneeka Abhijeet Roy (E057)

---

### 1. Architectural Overview
This research develops an autonomous mobile robot platform simulated in Google DeepMind MuJoCo to navigate between rows of solar panels, track string geometries, and detect defective cells using simulated infrared thermography.

### 2. Implementation Workflow
1. Verify environment using `python src/test_env.py`.
2. Implement trajectory control in `src/solar_defect_detector.py`.
3. Run Monte Carlo simulation trials and verify metrics in `analytics/solar_inspection_benchmark.csv`.
4. Render 300 DPI figures using `python analytics/generate_paper_figures.py`.
