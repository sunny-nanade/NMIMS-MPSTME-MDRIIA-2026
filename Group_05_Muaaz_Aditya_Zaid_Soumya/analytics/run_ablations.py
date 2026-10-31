#!/usr/bin/env python3
"""
Mitigation ablations -> analytics/ablation_trials.csv (+ .provenance.json)
Group: MDRIIA Group 05 | Owner: E043 Muaaz (integration)

Four FMEA mitigations, each switched OFF vs ON with exactly one explicit controller flag
(DualUAVSurveillanceController(..., <flag>=False)); the ON arm passes no flag at all, so it IS the
production code path of analytics/run_benchmark.py. Every run is one seeded MuJoCo flight through
run_benchmark.run_one (same draws, same metrics code), N seeds per arm, paired by seed.

  mode        flag                 scene / condition          metric(s)
  separation  layered_separation   interior uav_offset_ring   min_inter_uav_m, runs with min < 2.5 m, uav_uav_contacts
  fr18        obstacle_avoidance   interior uav_sectors       obstacle_contacts, min_obstacle_clearance_m
  geofence    geofence_hysteresis  interior uav_sectors       spurious tier escalations and breach-log events per run
                                                              (run_benchmark.geofence_probe, position noise on)
  twilight    auto_exposure        interior uav_sectors,      detected, detection_latency_s
                                   lights x TWILIGHT_SCALE

Design choices (not results): the intruder appears at a per-seed draw in INTRUDER_APPEAR_S so that every
short run contains an intrusion (TRACK diversions for 'separation' and 'fr18', a walk into the restricted
zone for 'geofence', a target to detect for 'twilight'). TWILIGHT_SCALE = 0.15 is the dim-light ASSUMPTION
of analytics/vision_illumination_benchmark.py.

  python analytics/run_ablations.py --trials 10 --duration 90 --workers 10
  python analytics/run_ablations.py --mode fr18 --trials 1 --duration 20 --out /tmp/x/abl.csv   # smoke
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import multiprocessing as mp
import os
import platform
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import run_benchmark as rb                             # noqa: E402

CANONICAL = os.path.join(HERE, "ablation_trials.csv")
TWILIGHT_SCALE = 0.15
INTRUDER_APPEAR_S = (5.0, 30.0)                       # design: the intrusion starts early in a short run
MODES = {
    "separation": {"flag": "layered_separation", "scene": "interior", "condition": "uav_offset_ring"},
    "fr18": {"flag": "obstacle_avoidance", "scene": "interior", "condition": "uav_sectors"},
    "geofence": {"flag": "geofence_hysteresis", "scene": "interior", "condition": "uav_sectors",
                 "geofence_probe": True},
    "twilight": {"flag": "auto_exposure", "scene": "interior", "condition": "uav_sectors",
                 "lighting_scale": TWILIGHT_SCALE},
}
COLUMNS = ["run_id", "mode", "arm", "flag", "flag_value", "scene", "condition", "seed", "duration_s",
           "lighting_scale", "intruder_appear_s", "min_inter_uav_m", "sep_below_2p5", "uav_uav_contacts",
           "obstacle_contacts", "min_obstacle_clearance_m", "geofence_escalations", "geofence_spurious_escalations",
           "geofence_breach_events", "geofence_spurious_breaches", "geofence_log_events", "detected",
           "detection_latency_s", "wall_s"]


def appear_draw(scene, seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, rb.SCENES.index(scene), 9]))
    return round(float(rng.uniform(*INTRUDER_APPEAR_S)), 3)


def job_for(mode, arm, seed, duration, runs_dir, vision_hz, telemetry):
    spec = MODES[mode]
    opts = {"tag": f"abl_{mode}_{arm}", "intruder_appear_s": appear_draw(spec["scene"], seed)}
    if arm == "off":
        opts[spec["flag"]] = False                     # exactly one mitigation switched off
    for k in ("lighting_scale", "geofence_probe"):
        if k in spec:
            opts[k] = spec[k]
    return (spec["scene"], spec["condition"], seed, duration, runs_dir, True, telemetry, vision_hz, opts)


def work(args):
    mode, arm, job = args
    out = rb.run_one(job)
    row, meta = out["row"], out["meta"]
    spec = MODES[mode]
    gp = meta.get("geofence_probe") or {}
    rec = {c: None for c in COLUMNS}
    rec.update(run_id=row["run_id"], mode=mode, arm=arm, flag=spec["flag"], flag_value=int(arm == "on"),
               scene=row["scene"], condition=row["condition"], seed=row["seed"], duration_s=row["duration_s"],
               lighting_scale=spec.get("lighting_scale", 1.0), intruder_appear_s=row["intruder_appear_s"],
               min_inter_uav_m=row["min_inter_uav_m"], uav_uav_contacts=row["uav_uav_contacts"],
               obstacle_contacts=row["obstacle_contacts"], min_obstacle_clearance_m=row["min_obstacle_clearance_m"],
               detected=row["detected"], detection_latency_s=row["detection_latency_s"], wall_s=meta.get("wall_s"))
    if row["min_inter_uav_m"] is not None:
        rec["sep_below_2p5"] = int(row["min_inter_uav_m"] < 2.5)
    if gp:
        rec.update(geofence_escalations=gp["escalations"], geofence_spurious_escalations=gp["spurious_escalations"],
                   geofence_breach_events=gp["breach_events"], geofence_spurious_breaches=gp["spurious_breaches"],
                   geofence_log_events=gp["log_events"])
    return rec, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--mode", default="all", choices=tuple(MODES) + ("all",))
    ap.add_argument("--trials", type=int, default=10, help="seeds per arm")
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--duration", type=float, default=90.0, help="simulated s per run")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--vision-hz", type=float, default=rb.aps.DualUAVSurveillanceController.VISION_HZ)
    ap.add_argument("--telemetry", action="store_true", help="also write contract-B telemetry per run")
    ap.add_argument("--out", default=CANONICAL)
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    runs_dir = (os.path.join(HERE, "runs", "ablations") if out == CANONICAL
                else os.path.join(os.path.dirname(out), "runs"))
    modes = tuple(MODES) if a.mode == "all" else (a.mode,)
    seeds = list(range(a.seed0, a.seed0 + a.trials))
    tasks = [(m, arm, job_for(m, arm, k, a.duration, runs_dir, a.vision_hz, a.telemetry))
             for m in modes for arm in ("off", "on") for k in seeds]
    print(f"{len(tasks)} ablation runs ({len(modes)} modes x 2 arms x {len(seeds)} seeds), {a.workers} workers")
    t0 = time.perf_counter()
    results = []
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for i, (rec, meta) in enumerate(pool.imap_unordered(work, tasks), 1):
            results.append((rec, meta))
            print(f"[{i:3d}/{len(tasks)}] {rec['run_id']:44s} {meta.get('wall_s')} s wall", flush=True)
    order = {(m, arm, t[2]): i for i, (m, arm, t) in enumerate(tasks)}
    results.sort(key=lambda r: order[(r[0]["mode"], r[0]["arm"], r[0]["seed"])])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for rec, _ in results:
            w.writerow({c: ("" if rec[c] is None else rec[c]) for c in COLUMNS})

    code = {rel: rb.sha(os.path.join(ROOT, rel)) for rel in rb.CODE_FILES + ("analytics/run_ablations.py",)}
    models = {rel: rb.sha(os.path.join(ROOT, rel)) for rel in rb.MODEL_FILES}
    prov = {
        "csv_sha256": hashlib.sha256(open(out, "rb").read()).hexdigest(),
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": "analytics/run_ablations.py",
        "command": " ".join([os.path.basename(sys.executable)] + sys.argv),
        "git_commit": rb.git_commit(),
        "python": platform.python_version(), "mujoco": rb.mujoco.__version__, "numpy": np.__version__,
        "platform": platform.platform(),
        "code_sha256_16": code, "model_sha256_16": models,
        "code_sha_combined": rb.code_sha(), "model_sha_combined": rb.model_sha(),
        "seeds": seeds, "trials_per_arm": a.trials, "duration_s": a.duration, "vision_hz": a.vision_hz,
        "timestep_s": sorted({r[1].get("timestep_s") for r in results}),
        "modes": {m: {**MODES[m], "off_arm": f"{MODES[m]['flag']}=False (only this flag)",
                      "on_arm": "no flag passed: the production code path"} for m in modes},
        "intruder_appear_s": {"rule": f"uniform{INTRUDER_APPEAR_S} per seed (design, so every short run "
                                      "contains an intrusion); identical for both arms",
                              "by_seed": {k: appear_draw("interior", k) for k in seeds}},
        "twilight_scale": {"value": TWILIGHT_SCALE, "label": "ASSUMPTION (vision_illumination_benchmark.py)"},
        "definitions": {
            "min_inter_uav_m, uav_uav_contacts, obstacle_contacts, min_obstacle_clearance_m, detected, "
            "detection_latency_s": "as in analytics/campus_patrol_real_trials.provenance.json (run_benchmark.run_one)",
            "sep_below_2p5": "1 if min_inter_uav_m < 2.5 m",
            "geofence_*": "run_benchmark.geofence_probe: the intruder's position over [appear, end] at 10 Hz plus "
                          "Gaussian noise sigma = GEOFENCE_NOISE_SIGMA_M (ASSUMPTION) fed to "
                          "evaluate_geofence_status; spurious = reported tier rises above the noise-free tier; "
                          "log_events = tier changes written to the breach log"},
        "wall_s_total": round(time.perf_counter() - t0, 1),
        "runs": {r[0]["run_id"]: {k: r[1].get(k) for k in ("wall_s", "vision_status", "resumed", "ablation_flags",
                                                           "code_sha", "model_sha", "surveillance")}
                 for r in results},
    }
    prov_path = os.path.splitext(out)[0] + ".provenance.json"
    json.dump(prov, open(prov_path, "w"), indent=2)
    print(f"\nwrote {out}\nwrote {prov_path}")


if __name__ == "__main__":
    main()
