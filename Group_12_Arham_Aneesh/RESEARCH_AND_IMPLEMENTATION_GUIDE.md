# Engineering Research and Implementation Guide
## Group: MDRIIA_GROUP_12
## Project: Autonomous Drone for Industrial Pipeline Surveillance & Defect Detection
## Students: Arham Khan (E069), Aneesh Kumar (E076)

---

### 1. Architectural Overview
This research develops an autonomous multirotor UAV platform simulated in Google DeepMind MuJoCo to navigate along linear pipeline corridors, detect structural anomalies, and evaluate technoeconomic cost parity against manual ground patrols.

### 2. Implementation Workflow
1. Verify environment using `python src/test_env.py`.
2. Implement corridor guidance in `src/drone_pipeline_controller.py`.
3. Run Monte Carlo simulation trials and verify metrics in `analytics/pipeline_inspection_benchmark.csv`.
4. Render 300 DPI figures using `python analytics/generate_paper_figures.py`.
