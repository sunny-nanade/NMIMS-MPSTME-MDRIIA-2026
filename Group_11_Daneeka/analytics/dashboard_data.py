"""Collects the numbers shown on the dashboard into results/dashboard_data.json (nothing typed by hand)."""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "analytics"))
from run_evaluation import MODEL, make_config  # noqa: E402
from solar_defect_detector import InspectionMission  # noqa: E402

DEMO_SEED = 3009


def module_map(cond):
    cfg = make_config(DEMO_SEED, cond); cfg.log_telemetry = False
    res = InspectionMission(cfg, MODEL).run()
    flagged = {d["panel_id_est"]: d for d in res.detections}
    mods = []
    for pid in res.truth.reg.ids:
        kinds = sorted(res.truth.kinds_at(pid))
        conf = any(not d.kind.is_defect for d in res.truth.by_panel(pid))
        f = flagged.get(pid)
        mods.append(dict(id=pid, truth=kinds, confounder=conf, flagged=bool(f), est_kind=f["kind_est"] if f else None))
    return dict(modules=mods, metrics={k: (None if isinstance(v, float) and v != v else v) for k, v in res.metrics.items()},
                weather=cfg.weather_label, start_h=cfg.start_h)


def main():
    out = {}
    st = pd.read_csv(os.path.join(ROOT, "analytics", "statistics_summary.csv"))
    out["stats"] = json.loads(st.to_json(orient="records"))
    tr = pd.read_csv(os.path.join(ROOT, "analytics", "solar_inspection_real_trials.csv"))
    out["n_missions"] = int(len(tr) // 2)
    out["deferred"] = int(tr[(tr.condition == "proposed")].deferred.sum())
    out["business"] = json.load(open(os.path.join(ROOT, "results", "business_results.json")))
    fm = os.path.join(ROOT, "analytics", "fmea_table.csv")
    if os.path.exists(fm):
        out["fmea"] = json.loads(pd.read_csv(fm).to_json(orient="records"))
    sc = os.path.join(ROOT, "analytics", "scenario_real_trials.csv")
    if os.path.exists(sc):
        d = pd.read_csv(sc)
        g = d.groupby(["scenario", "condition"]).agg(n=("seed", "size"), recall=("recall", "mean"), precision=("precision", "mean"),
                                                   fp=("fp", "mean"), fn=("fn", "mean"), contact_s=("obstacle_contact_s", "mean"),
                                                   completed=("completed", "mean"), deferred=("deferred", "mean")).reset_index()
        out["scenarios"] = json.loads(g.to_json(orient="records"))
    out["demo"] = {c: module_map(c) for c in ("baseline", "proposed")}
    out["demo_seed"] = DEMO_SEED
    json.dump(out, open(os.path.join(ROOT, "results", "dashboard_data.json"), "w"), indent=1, default=str)
    print("wrote results/dashboard_data.json")


if __name__ == "__main__":
    main()
