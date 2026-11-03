# Group 11 - Autonomous Solar-PV Inspection AMR (MuJoCo + Python + Blender digital twin)
Daneeka Abhijeet Roy (E057), MDRIIA capstone, NMIMS MPSTME.

**Question:** How can autonomous mobile-robot navigation and sensor-based anomaly detection improve the speed and accuracy of locating defective solar panels in large-scale solar installations compared with manual inspection?

## What is here
| Path | Purpose |
|---|---|
| `models/generate_mjcf.py` -> `solar_farm.xml`, `solar_defect_amr.xml` | MJCF (0.002 s step, dossier contact settings, 5 actuators), generated from one registry |
| `src/panel_registry.py` | single source of truth: module ids `PV_Rrr_Ccc`, positions, cells |
| `src/sun_position.py`, `irradiance_model.py`, `panel_thermal_model.py`, `solar_environment.py` | sun, irradiance, per-cell thermal state |
| `src/fault_injection.py` | hidden defects + confounders (detector can never import it; tested) |
| `src/sensor_simulation.py`, `thermal_optics.py` | encoders, gyro, range, fiducials, thermal+optical cameras |
| `src/navigation.py`, `robot_controller.py` | pose estimator, PID with anti-windup, lane follower, wheel PI |
| `src/defect_detection.py` | baseline and proposed detectors |
| `src/solar_defect_detector.py` | FSM controller (ROW_FOLLOW, SCAN, ANOMALY_FLAG, GEOTAG, NEXT_ROW, RETURN_TO_DOCK) + `run_inspection_mission` |
| `src/run_simulation.py` | headless run or live viewer |
| `analytics/run_evaluation.py` | N = 30 paired Monte Carlo -> `solar_inspection_real_trials.csv` |
| `analytics/run_scenarios.py` | stress scenarios -> `scenario_real_trials.csv` |
| `analytics/statistics_report.py`, `fmea.py`, `solar_pv_roi.py`, `make_figures.py` | statistics, FMEA, business model, figures |
| `blender/generate_solar_farm.py` | Blender 5.x visual scene (tested with the bpy 5.2.3 module) |
| `documentation/` | assumptions, AI-error log, Mac run guide |
| `tests/` | pytest suite |

## Honest status
* All numbers come from the controller's own runs; no `SIMULATED_*` file or `generate_paper_figures.py` is used.
* Sim-to-sim evaluation only - see `documentation/model_assumptions.md` for every assumption and what was / was not verified.
* The viewer (`mjpython`) was not run in the build workspace (no display); headless physics, rendering via EGL and Blender via `bpy` were.
