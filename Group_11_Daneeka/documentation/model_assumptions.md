# Model assumptions, sources and limits (read before the viva)

Everything below is either **SOURCE** (checked), **MODEL** (a published equation implemented here) or
**ASSUMPTION** (my engineering choice, labelled, not calibrated to measurements).

## Physics / environment
| Item | Value / form | Status |
|---|---|---|
| Sun position | Spencer-type Fourier declination + equation of time, direct ENU vector | MODEL (verified: noon elevation at Mumbai, 31-Oct = 56-58 deg; `tests/test_solar_model.py`) |
| Clear-sky irradiance | Hottel with tropical correction factors, haze multiplier | MODEL |
| Cloud factor | Kasten-Czeplak | MODEL |
| Diffuse on tilted plane | Liu-Jordan isotropic, albedo 0.2 | MODEL |
| Module temperature | Faiman: T = Ta + G/(U0 + U1 v), U0 = 25 W/m2K, U1 = 6.84 W s/m3K | MODEL (the two coefficients are the commonly used defaults; the original paper was not re-read in this session - **verify before citing**) |
| Thermal inertia | first-order lag, C_th = 11 kJ/m2K | ASSUMPTION |
| Reverse-bias heating of partly shaded modules | KAPPA_RB = 55 K at 1000 W/m2 beam | ASSUMPTION (uncalibrated; chosen so a partly shaded cell is ~ +15-25 K) |
| Defect excess temperatures | HOTSPOT 16-40 K, HOT_MODULE 9-18 K (at 1000 W/m2) | ASSUMPTION |
| Sensor noise | thermal 0.4 K per pixel, 0.7 K common-mode, 0.15 % spikes, 1 % frame drop-out | ASSUMPTION |
| Emissivity | Fresnel with n = 1.5 (glass), sky temperature depression 20 K (sensor) / 10 K assumed by detector | MODEL + ASSUMPTION |
| Sun glint | Gaussian in angle (5 deg) around the mirror direction, +60 K peak | ASSUMPTION |
| Optical detector | rule-based scores on simulated crack/obstruction/shadow visibility | **Not a trained vision model**: it is a simulated optical channel |

## Thresholds from standards
| Item | Value | Status |
|---|---|---|
| Minimum irradiance for thermography | 600 W/m2 | **Secondary source only**: a vendor article (Sitemark support) states "the IEC standard states that you need a minimum irradiance of 600 W/m2". The standard's own Table 3 ("Required inspection conditions") was NOT read (paywalled). Check IEC TS 62446-3 Table 3 in the university library. |
| Temperature-difference projection | The standard has a clause "Projection of temperature differences to nominal irradiance" | The proposed detector normalises excess temperature to 1000 W/m2 in the same spirit; the clause itself was not read |
| 15 K hotspot threshold (starter code, used by the *baseline* here) | 15 K | **Unverified.** No source for 15 K as a normative threshold was found. It is used only as the baseline's fixed rule. |

## Business inputs
| Item | Value | Status |
|---|---|---|
| Manual inspection effort | 10 h/MW | SOURCE (secondary, trade press, unnamed underlying study): Solar Builder, "This Drone for Hire...", G. Shambo (Borrego O&M). The starter value 8.5 h/MW had no source and is not used. |
| Everything else (robot cost, life, prevalence, supervision, repair time ...) | see `Inputs` in `analytics/solar_pv_roi.py` | ASSUMPTION, each varied +/-30 % in the sensitivity figure |

## Known limits
* The simulated detector is evaluated on the simulator's own sensor model (sim-to-sim). Results show relative
  controller quality inside this model, **not** field performance.
* The test array is 16 kW (40 modules). Time per MW is the per-module time scaled to 1 MW (2500 modules).
* Defect density in the Monte Carlo (4-7 of 40 modules) is a stress density, not a field prevalence.
* Thresholds of the proposed detector were adjusted once after looking at seeds 1000-1029
  (`analytics/tuning_trials_seeds1000.csv`). The reported evaluation uses fresh seeds 3000-3029 that were not used for tuning.
* At the project site (Mumbai) the camera, looking north from the south side of the array, never sees specular sun glint in any month
  (checked numerically). The glint failure mode is therefore exercised only in a labelled stress scenario (6 N, 21 June).
* The 5th actuator (mast lift) is my design choice; the dossier only fixes 5 actuators.
