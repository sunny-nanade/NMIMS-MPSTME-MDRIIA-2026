"""Evaluation of a finished mission against the hidden ground truth (evaluator only)."""
from __future__ import annotations

import numpy as np

from telemetry import COLUMNS, STATE_NAMES


def mission_metrics(mission, res) -> dict:
    reg, gt = mission.reg, mission.gt
    truth = gt.defect_panel_ids()
    all_ids = set(reg.ids)
    flagged, best = {}, {}
    for rec in res.detections:
        pid = rec["panel_id_est"]
        flagged[pid] = rec
    pred = set(flagged)
    tp = len(pred & truth)
    fp = len(pred - truth)
    fn = len(truth - pred)
    tn = len(all_ids) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    # confounder false alarms (shadowed healthy modules flagged)
    conf_ids = {d.panel_id for d in gt.defects if not d.kind.is_defect}
    conf_fp = len(pred & conf_ids)
    # localisation error on true positives
    loc_err = []
    for pid in pred & truth:
        pos = flagged[pid].get("position_est")
        tpos = gt.hotspot_cell_position(pid)
        if tpos is None:
            tpos = reg.get(pid).center
        if pos is not None:
            loc_err.append(float(np.linalg.norm(np.array(pos) - tpos)))
    kind_ok = sum(1 for pid in pred & truth if flagged[pid]["kind_est"] in gt.kinds_at(pid))
    # telemetry statistics
    out = dict(
        seed=mission.cfg.seed, condition=mission.cfg.condition, completed=int(res.completed),
        duration_s=res.duration_s, wall_s=res.wall_s,
        n_defects=len(truth), n_confounders=len(conf_ids), tp=tp, fp=fp, fn=fn, tn=tn,
        precision=precision, recall=recall, conf_fp=conf_fp,
        kind_accuracy=(kind_ok / tp) if tp else float("nan"),
        loc_err_mean_m=float(np.mean(loc_err)) if loc_err else float("nan"),
        loc_err_max_m=float(np.max(loc_err)) if loc_err else float("nan"),
        modules_scanned=len(set(res.visited)),
        unassessed=len(set(mission.unassessed)),
        deferred=int(mission.deferred_flag),
        farm_mw=reg.cfg.farm_mw,
        time_per_mw_h=res.duration_s / 3600.0 / reg.cfg.farm_mw,
        control_effort=float(mission.tau2),
        obstacle_contact_s=mission.obstacle_contact_ticks * 0.02,
    )
    if mission.tel is not None and mission.tel.n:
        d = mission.tel.data()
        ci = {n: i for i, n in enumerate(COLUMNS)}
        st = d[:, ci["state"]]
        rf = st == STATE_NAMES.index("ROW_FOLLOW")
        sc = st == STATE_NAMES.index("SCAN")
        xt = d[:, ci["x_true"]]
        lane = (rf | sc) & (xt >= reg.x_west) & (xt <= reg.x_east)
        ct = d[lane, ci["cross_track_err"]]
        he = d[lane, ci["heading_err"]]
        out["track_rmse_m"] = float(np.sqrt(np.mean(ct ** 2))) if ct.size else float("nan")
        out["track_max_m"] = float(np.max(np.abs(ct))) if ct.size else float("nan")
        out["heading_rmse_rad"] = float(np.sqrt(np.mean(he ** 2))) if he.size else float("nan")
        pe = np.hypot(d[:, ci["x_est"]] - d[:, ci["x_true"]], d[:, ci["y_est"]] - d[:, ci["y_true"]])
        out["pose_err_rms_m"] = float(np.sqrt(np.mean(pe ** 2)))
        out["pose_err_max_m"] = float(np.max(pe))
    return out
