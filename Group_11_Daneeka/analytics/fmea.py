"""FMEA with sim-derived Occurrence.  RPN = S x O x D, each 1..10.

O  (occurrence)  : computed here from the scenario Monte Carlo (analytics/scenario_real_trials.csv and
                   analytics/solar_inspection_real_trials.csv): per-mission frequency of the failure EVENT,
                   with a half-event floor (0 events in N missions -> p = 0.5/N) and the scale below.
S  (severity)   : engineering judgement (stated reason in the table) - NOT measured.
D  (detection)  : engineering judgement tied to a named check in the code (stated in 'basis').
"Pre"  = baseline controller on the scenario;  "Post" = proposed controller on the SAME seeds.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCEN = os.path.join(ROOT, "analytics", "scenario_real_trials.csv")
NOM = os.path.join(ROOT, "analytics", "solar_inspection_real_trials.csv")

O_SCALE = [(0.5, 10), (0.3, 9), (0.2, 8), (0.1, 7), (0.05, 6), (0.02, 5), (0.01, 4), (0.005, 3), (0.001, 2), (0.0, 1)]


def occurrence_rating(p: float) -> int:
    for thr, r in O_SCALE:
        if p >= thr:
            return r
    return 1


def freq(events: np.ndarray) -> float:
    n = len(events)
    k = int(np.sum(events))
    return max(k, 0.5) / n


# failure mode -> (data source, scenario, event function, severity, S basis,
#                  D pre, D post, mitigation, shown in, D basis)
def modes():
    return [
        dict(name="Missed / mislocated hotspot, false alarm: sun glint or poor sensor angle corrupts the thermal image",
             effect="Defective module missed (energy loss, fire risk) or healthy module sent for repair",
             src=SCEN, scen="glint_stress", ev=lambda d: (d.fn + d.fp) > 0, S=8,
             S_basis="undetected hot cell can lead to module loss / fire (judgement)",
             D_pre=8, D_post=4, mitig="glint-risk model picks mast height with the lowest specular risk; pixels within 10 deg of the mirror direction are masked; verification view at another height",
             shown="src/solar_defect_detector.py _choose_lift / defect_detection.py glint mask; analytics/run_scenarios.py glint_stress",
             D_basis="baseline has no check (D=8); proposed raises RECHECK and a second view, so the error is usually caught before geotagging (D=4)"),
        dict(name="AMR drifts into inter-row gap or kerb (localisation drift)",
             effect="Collision with kerb / module frame, mission aborted, equipment damage",
             src=SCEN, scen="nav_drift", ev=lambda d: (d.obstacle_contact_s > 0) | (d.completed == 0) | (d.track_rmse_m > 0.25), S=9,
             S_basis="contact with a live PV row can damage glass / robot (judgement)",
             D_pre=7, D_post=3, mitig="side range-pair feedback on the module plane + surveyed fiducials every 5 modules replace pure dead reckoning",
             shown="src/navigation.py PoseEstimator.update_range / update_fiducial; analytics/run_scenarios.py nav_drift",
             D_basis="baseline can only see the error when it hits something (D=7); proposed measures lateral gap every 20 ms (D=3)"),
        dict(name="Wrong module identified / geotag on the wrong module (dock or odometry offset)",
             effect="Technician sent to the wrong module; real defect left unrepaired",
             src=SCEN, scen="misassociation", ev=lambda d: (d.fn + d.fp) > 0, S=7,
             S_basis="repair effort wasted and defect persists (judgement)",
             D_pre=8, D_post=4, mitig="fiducial position fixes (every 5 modules) re-anchor the module index",
             shown="src/navigation.py update_fiducial; analytics/run_scenarios.py misassociation",
             D_basis="no cross-check in baseline (D=8); proposed re-anchors at each fiducial (D=4)"),
        dict(name="Thermal assessment made below the valid irradiance (low sun / cloud)",
             effect="Temperature excess misread: false alarms or missed defects",
             src=SCEN, scen="low_irradiance", ev=lambda d: ((d.fn + d.fp) > 0) & (d.deferred == 0), S=6,
             S_basis="mis-prioritised repairs, no safety consequence (judgement)",
             D_pre=7, D_post=2, mitig="reference-cell irradiance gate (>= 600 W/m2, to be checked against IEC TS 62446-3 Table 3), wait-and-retry, abort and reschedule",
             shown="src/defect_detection.py gate; src/solar_defect_detector.py consec_gated / deferral",
             D_basis="baseline never checks irradiance (D=7); proposed refuses to assess (D=2)"),
        dict(name="Thermal sensor noise, spikes or frame drop-outs",
             effect="False alarms from single hot pixels / missed anomalies from lost frames",
             src=SCEN, scen="sensor_stress", ev=lambda d: (d.fn + d.fp) > 0, S=6,
             S_basis="wasted dispatches / missed finding (judgement)",
             D_pre=7, D_post=3, mitig="3-frame temporal median, cluster (>=2 pixel) rule, repeat on dropout",
             shown="src/defect_detection.py median + _neighbour_cluster",
             D_basis="baseline trusts one frame (D=7); proposed median rejects spikes (D=3)"),
        dict(name="External shadow (confounder) triggers a false 'defect'",
             effect="Healthy module sent for repair",
             src=NOM, scen=None, ev=lambda d: d.conf_fp > 0, S=5,
             S_basis="one wasted repair visit (judgement)",
             D_pre=7, D_post=3, mitig="optical shadow score + hot-cluster coincidence rule classifies SHADOW_CONFOUNDER",
             shown="src/defect_detection.py shadow branch; src/fault_injection.py EXT_SHADOW",
             D_basis="baseline has no optical cross-check (D=7); proposed has one (D=3)"),
    ]


def main():
    rows = []
    for m in modes():
        if not os.path.exists(m["src"]):
            print("missing", m["src"])
            continue
        df = pd.read_csv(m["src"])
        if m["scen"]:
            df = df[df.scenario == m["scen"]]
        pre = df[df.condition == "baseline"]
        post = df[df.condition == "proposed"]
        p_pre, p_post = freq(m["ev"](pre).to_numpy()), freq(m["ev"](post).to_numpy())
        O_pre, O_post = occurrence_rating(p_pre), occurrence_rating(p_post)
        rows.append(dict(failure_mode=m["name"], effect=m["effect"], S=m["S"], O_pre=O_pre, D_pre=m["D_pre"],
                         RPN_pre=m["S"] * O_pre * m["D_pre"], mitigation=m["mitig"], O_post=O_post, D_post=m["D_post"],
                         RPN_post=m["S"] * O_post * m["D_post"], p_event_pre=round(p_pre, 3), p_event_post=round(p_post, 3),
                         N=len(pre), shown_in=m["shown"], S_basis=m["S_basis"], D_basis=m["D_basis"]))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(ROOT, "analytics", "fmea_table.csv"), index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 60)
    print(out[["failure_mode", "S", "O_pre", "D_pre", "RPN_pre", "O_post", "D_post", "RPN_post", "p_event_pre", "p_event_post", "N"]].to_string(index=False))
    return out


if __name__ == "__main__":
    main()
