#!/usr/bin/env python3
"""
Benchmark trial runner -> analytics/campus_patrol_real_trials.csv (+ .provenance.json)
Group: MDRIIA Group 05 | Owner: E043 Muaaz (integration)

The ONLY sanctioned producer of the trial CSV (contract A). Every row is one seeded
MuJoCo run of one condition in one scene:
  scene      interior | exterior
  condition  guard_baseline   kinematic guard, src/foot_patrol_baseline.py
             uav_sectors      Alpha ground loop / Bravo galleries (exterior: two arcs)
             uav_offset_ring  both UAVs on the main loop, half a lap apart
Each run also writes its per-step telemetry (contract B) to <runs>/<run_id>.csv.gz and a
summary JSON to <runs>/summary/<run_id>.json. The runner is RESUMABLE: a run whose
summary already exists with the same duration, timestep and vision setting is not re-run.
<runs> = analytics/runs for the canonical CSV, otherwise <dir of --out>/runs.

Per-seed randomisation (one generator per (scene, seed), shared by all three conditions,
so the conditions are compared on the same draws): see RANDOMISATION below.
Revisit / cycle / coverage columns come from ONE function (src/patrol_metrics.py) for
all conditions. Columns that do not apply to a condition are empty and listed in the
provenance under "not_applicable"; columns that apply but were not measured in this
batch (vision off, FSM verify stage absent) are empty and listed under "not_measured".

  python analytics/run_benchmark.py --scene all --condition all --trials 50 --workers 8
  python analytics/run_benchmark.py --scene interior --condition uav_sectors --trials 2 --duration 120 --out /tmp/x/smoke.csv
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
import aerial_patrol_swarm as aps                     # noqa: E402
import foot_patrol_baseline as fpb                    # noqa: E402
import patrol_metrics as pm_mod                       # noqa: E402
import mujoco                                          # noqa: E402

CANONICAL = os.path.join(HERE, "campus_patrol_real_trials.csv")
COLUMNS = ["run_id", "scene", "condition", "seed", "duration_s", "timestep_s", "mean_wind_mps", "gust_sigma_mps",
           "intruder_appear_s", "dock_jitter_m", "n_ground_laps", "cycle_time_s", "worst_revisit_ground_s",
           "mean_revisit_ground_s", "worst_revisit_gallery_s", "gallery_coverage", "detected", "detection_latency_s",
           "verify_time_s", "min_inter_uav_m", "tracking_rmse_m", "control_effort_N2s", "energy_wh",
           "min_obstacle_clearance_m", "obstacle_contacts", "uav_uav_contacts", "guard_speed_mps", "guard_stop_mean_s",
           # appended (contract A is append-only): G-08 equal window, per-agent laps, G-09, G-10
           "worst_revisit_ground_eqwin_s", "eqwin_s", "n_laps_alpha", "n_laps_bravo", "n_laps_guard",
           "waypoint_rmse_m", "torque_effort_N2m2s"]
SCENES = ("interior", "exterior")
CONDITIONS = ("guard_baseline", "uav_sectors", "uav_offset_ring")

# Per-seed draws, uniform on [lo, hi]. Units in the key. Wind values are NOMINAL; the scene's
# <numeric name="wind_scale"> multiplies them (interior 0.08: HVAC drafts only), and the CSV
# records the EFFECTIVE values the airframes feel.
RANDOMISATION = {
    "interior": {
        "mean_wind_nominal_mps": ((0.0, 6.0), "ASSUMPTION: 0-6 m/s outdoor mean wind; x wind_scale 0.08 indoors"),
        "gust_sigma_nominal_mps": ((0.5, 2.0), "ASSUMPTION: 0.5-2.0 m/s OU gust intensity; x wind_scale"),
        "intruder_appear_s": ((40.0, 160.0), "design: intruder enters after the patrol is established"),
        "dock_jitter_m": ((0.0, 0.30), "ASSUMPTION: 0-0.3 m landing placement error on the dock"),
    },
    "exterior": {
        "mean_wind_nominal_mps": ((0.0, 6.0), "ASSUMPTION: 0-6 m/s mean wind at 20-40 m AGL"),
        "gust_sigma_nominal_mps": ((0.5, 2.0), "ASSUMPTION: 0.5-2.0 m/s OU gust intensity"),
        "intruder_appear_s": ((40.0, 160.0), "design: intruder enters after the patrol is established"),
        "dock_jitter_m": ((0.0, 0.30), "ASSUMPTION: 0-0.3 m landing placement error on the dock"),
    },
}
# Same window for every condition of a scene. Chosen so the SLOWEST guard draw of
# foot_patrol_baseline.CONFIG (1.272 m/s, 60 s mean pause, 0.25 m/s stairs) still services
# every ground checkpoint at least twice: over 40 pause draws at that corner the second
# service of every ground checkpoint came by 4666 s interior (nine gallery floors per cycle)
# and 1675 s exterior (ring inside the campus wall, 302 m walked). Interior gallery revisits need about two full cycles (up to ~8000 s)
# and stay EMPTY for slow guard draws; gallery_coverage is still reported.
DEFAULT_DURATION_S = {"interior": 5000.0, "exterior": 1800.0}
# G-08: worst revisit is ALSO scored on this equal window [0, EQWIN_S] for every condition (guard included),
# from each run's own service times (patrol_metrics.worst_revisit_window). The primary, window-independent
# metric is cycle_time_s (mean time per completed full ground lap).
EQWIN_S = 300.0
PER_CONDITION_NA = {
    "guard_baseline": ["mean_wind_mps", "gust_sigma_mps", "dock_jitter_m", "min_inter_uav_m", "tracking_rmse_m",
                       "control_effort_N2s", "energy_wh", "min_obstacle_clearance_m", "obstacle_contacts",
                       "uav_uav_contacts", "verify_time_s", "n_laps_alpha", "n_laps_bravo", "waypoint_rmse_m",
                       "torque_effort_N2m2s"],
    "uav_sectors": ["guard_speed_mps", "guard_stop_mean_s", "n_laps_guard"],
    "uav_offset_ring": ["guard_speed_mps", "guard_stop_mean_s", "n_laps_guard"],
}
PER_SCENE_NA = {"exterior": ["worst_revisit_gallery_s", "gallery_coverage"], "interior": []}


# Ablation switches of DualUAVSurveillanceController with their PRODUCTION values. A run passes only the
# flags that differ (analytics/run_ablations.py); the main batch passes none, i.e. the production path.
ABLATION_FLAGS = {"layered_separation": True, "obstacle_avoidance": True, "geofence_hysteresis": True,
                  "auto_exposure": True, "static_handover": True}


def scale_lighting(model, scale):
    """Dim light (ablation d): headlight + every scene light ambient/diffuse/specular x scale, the same
    rule as analytics/vision_illumination_benchmark.py ('twilight' = 0.15, an ASSUMPTION)."""
    h = model.vis.headlight
    h.ambient[:], h.diffuse[:], h.specular[:] = h.ambient * scale, h.diffuse * scale, h.specular * scale
    model.light_ambient[:] *= scale
    model.light_diffuse[:] *= scale
    model.light_specular[:] *= scale


def geofence_probe(ctl, seed, rate_hz=10.0, sigma_m=None):
    """
    Ablation (c), run after the flight: feed the E075 geofence the intruder's position over
    [appear, end of run] at rate_hz, with Gaussian position noise (sigma_m, default the controller's
    GEOFENCE_NOISE_SIGMA_M ASSUMPTION), using the controller's own geofence_hysteresis flag.
    SPURIOUS escalation = the reported tier rises above the TRUE (noise-free) tier of that sample.
    Returns counts per run: escalations, spurious_escalations, breach_events (escalations to tier 3),
    spurious_breaches, log_events (every tier change written to the breach log).
    """
    ctl.reset_geofence_state()
    ctl.reseed_geofence_noise(seed)
    ctl._geofence_last_noisy = None
    out = {"escalations": 0, "spurious_escalations": 0, "breach_events": 0, "spurious_breaches": 0,
           "log_events": 0, "samples": 0, "rate_hz": rate_hz,
           "sigma_m": ctl.GEOFENCE_NOISE_SIGMA_M if sigma_m is None else sigma_m}
    t, prev = ctl.intruder_appear_s, 0
    while t <= ctl.current_time_s + 1e-9:
        xy = ctl._intruder_xy(t)
        if xy is not None:
            p = (float(xy[0]), float(xy[1]), 0.0)
            true_tier = ctl.geofence_raw_tier(p)
            _, tier = ctl.evaluate_geofence_status(ctl.inject_position_noise(p, out["sigma_m"]))
            out["samples"] += 1
            if tier > prev:
                out["escalations"] += 1
                out["spurious_escalations"] += int(tier > true_tier)
                if tier == 3:
                    out["breach_events"] += 1
                    out["spurious_breaches"] += int(true_tier < 3)
            prev = tier
        t += 1.0 / rate_hz
    out["log_events"] = len(ctl.geofence_events)
    return out


def draws(scene, seed):
    """All per-seed random inputs for one (scene, seed); identical for every condition."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, SCENES.index(scene)]))
    cfg = RANDOMISATION[scene]
    out = {k: float(rng.uniform(*cfg[k][0])) for k in ("mean_wind_nominal_mps", "gust_sigma_nominal_mps",
                                                         "intruder_appear_s", "dock_jitter_m")}
    out["guard"] = fpb.draw_guard_params(np.random.default_rng(np.random.SeedSequence([seed, SCENES.index(scene), 1])))
    return out


def sha(path, n=16):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:n]


CODE_FILES = ("src/aerial_patrol_swarm.py", "src/foot_patrol_baseline.py", "src/patrol_metrics.py",
              "src/run_telemetry.py", "analytics/run_benchmark.py")
MODEL_FILES = ("models/common.xml", "models/uav_fleet.xml", "models/nmims_main_interior.xml",
               "models/nmims_main_campus.xml", "models/campus_perimeter_patrol.xml",
               "models/campus_perimeter_patrol_exterior.xml")


def _combined_sha(rels):
    h = hashlib.sha256()
    for rel in rels:
        h.update(rel.encode() + b"\0" + open(os.path.join(ROOT, rel), "rb").read() + b"\0")
    return h.hexdigest()[:16]


def code_sha():
    """Fingerprint of every source file that shapes a run's numbers (G-12)."""
    return _combined_sha(CODE_FILES)


def model_sha():
    """Fingerprint of every MJCF file of both scenes (G-12)."""
    return _combined_sha(MODEL_FILES)


def cached_summary(summ_path, expect):
    """
    Resume rule (G-12): reuse a summary only if EVERY key of `expect` (duration, timestep, vision,
    telemetry, vision_hz, ablation flags, eqwin_s, code_sha, model_sha) equals the cached meta.
    A summary written by other code or other models (or by an older runner without the hashes)
    is stale and the run is redone. Returns the cached dict or None.
    """
    if not os.path.exists(summ_path):
        return None
    try:
        old = json.load(open(summ_path))
    except (OSError, ValueError):
        return None
    m = old.get("meta", {})
    if any(m.get(k) != v for k, v in expect.items()):
        return None
    if set(old.get("row", {})) != set(COLUMNS):
        return None
    old["meta"]["resumed"] = True
    return old


def git_commit():
    try:
        h = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.check_output(["git", "-C", ROOT, "status", "--porcelain", "--", "src", "models", "analytics/run_benchmark.py"],
                                        stderr=subprocess.DEVNULL).decode().strip()
        return h + ("-dirty" if dirty else "")
    except Exception:
        return "not-a-git-repo"


def _num(v, nd):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    return round(float(v), nd)


def run_one(job):
    """One (scene, condition, seed) run. Returns the summary dict (also written as JSON)."""
    scene, condition, seed, duration, runs_dir, vision, telemetry, vision_hz = job[:8]
    opts = dict(job[8]) if len(job) > 8 and job[8] else {}
    flags = {k: bool(opts[k]) for k in ABLATION_FLAGS if k in opts and opts[k] != ABLATION_FLAGS[k]}
    eqwin = float(opts.get("eqwin_s", EQWIN_S))
    appear = opts.get("intruder_appear_s")              # ablation override; None = the per-seed draw
    tag = opts.get("tag", "")
    run_id = f"{scene}_{condition}_s{seed}" + (f"_{tag}" if tag else "")
    summ_path = os.path.join(runs_dir, "summary", f"{run_id}.json")
    tel_path = os.path.join(runs_dir, f"{run_id}.csv.gz") if telemetry else None
    model_path = aps.SCENES[scene]
    timestep = float(mujoco.MjModel.from_xml_path(model_path).opt.timestep)
    meta = {"duration_s": duration, "timestep_s": timestep, "vision": vision, "telemetry": bool(telemetry),
            "vision_hz": vision_hz, "eqwin_s": eqwin, "ablation_flags": flags,
            "intruder_appear_override_s": appear, "lighting_scale": opts.get("lighting_scale"),
            "code_sha": code_sha(), "model_sha": model_sha()}
    old = cached_summary(summ_path, dict(meta))
    if old is not None:
        return old
    d = draws(scene, seed)
    if appear is not None:
        d["intruder_appear_s"] = float(appear)
    row = {c: None for c in COLUMNS}
    row.update(run_id=run_id, scene=scene, condition=condition, seed=seed, duration_s=duration, timestep_s=timestep,
               intruder_appear_s=_num(d["intruder_appear_s"], 3), eqwin_s=eqwin)
    t0 = time.perf_counter()

    if condition == "guard_baseline":
        rng = np.random.default_rng(np.random.SeedSequence([seed, SCENES.index(scene), 2]))
        g = fpb.FootPatrol(model_path, seed, d["guard"], d["intruder_appear_s"], rng)
        g.run(duration, telemetry_path=tel_path, run_id=run_id, condition=condition)
        m = g.metrics()
        row.update({k: m[k] for k in ("n_ground_laps", "cycle_time_s", "worst_revisit_ground_s", "mean_revisit_ground_s",
                                      "worst_revisit_gallery_s", "gallery_coverage", "detected", "detection_latency_s",
                                      "guard_speed_mps", "guard_stop_mean_s")})
        row["n_laps_guard"] = m["n_ground_laps"]          # one agent: its laps are the ground cycles
        row["worst_revisit_ground_eqwin_s"] = pm_mod.worst_revisit_window(g.visits, eqwin)
        meta["detection_model"] = "line of sight + detect_radius_m (labelled ASSUMPTION in foot_patrol_baseline.CONFIG)"
    else:
        policy = condition[len("uav_"):]
        ctl = aps.DualUAVSurveillanceController(
            model_path=model_path, policy=policy, wind_mps=d["mean_wind_nominal_mps"],
            gust_sigma=d["gust_sigma_nominal_mps"], seed=seed, intruder_appear_s=d["intruder_appear_s"],
            vision=vision, telemetry_path=tel_path, run_id=run_id, condition=condition, frame_log=False,
            dock_jitter_m=d["dock_jitter_m"], vision_hz=vision_hz, **flags)
        if opts.get("lighting_scale") is not None:
            scale_lighting(ctl.model, float(opts["lighting_scale"]))
        scale = ctl._num("wind_scale", 1.0)
        while ctl.current_time_s < duration - 1e-9:
            ctl.step_simulation(dt=min(1.0 / 30.0, duration - ctl.current_time_s))
        ctl.close_telemetry()
        pm, fm = ctl.patrol_metrics(), ctl.flight_metrics()
        row.update({k: pm[k] for k in ("n_ground_laps", "cycle_time_s", "worst_revisit_ground_s", "mean_revisit_ground_s",
                                       "worst_revisit_gallery_s", "gallery_coverage")})
        row.update(fm)
        row.update(n_laps_alpha=ctl.uavs["alpha"]["laps"], n_laps_bravo=ctl.uavs["bravo"]["laps"],
                   worst_revisit_ground_eqwin_s=pm_mod.worst_revisit_window(ctl.visits, eqwin))
        row.update(mean_wind_mps=d["mean_wind_nominal_mps"] * scale, gust_sigma_mps=d["gust_sigma_nominal_mps"] * scale,
                   dock_jitter_m=d["dock_jitter_m"],
                   min_inter_uav_m=ctl.min_inter_uav_m if math.isfinite(ctl.min_inter_uav_m) else None,
                   min_obstacle_clearance_m=getattr(ctl, "min_obstacle_clearance_m", None),
                   obstacle_contacts=sum(u["obstacle_contacts"] for u in ctl.uavs.values()),
                   uav_uav_contacts=ctl.uav_uav_contacts)
        meta["vision_status"] = ctl.vision_status
        if opts.get("geofence_probe"):
            meta["geofence_probe"] = geofence_probe(ctl, seed)
        if vision and ctl.vision_status == "active":
            sm = ctl.surveillance_metrics()           # FSM incidents scored against the true intruder path
            row.update({k: sm[k] for k in ("detected", "detection_latency_s", "verify_time_s")})
            meta["surveillance"] = {k: sm[k] for k in ("false_alarms", "verify_rejects", "incidents")}
        meta["wind_scale"] = scale
    meta["wall_s"] = round(time.perf_counter() - t0, 2)
    meta["telemetry_path"] = os.path.relpath(tel_path, ROOT) if tel_path and tel_path.startswith(ROOT) else tel_path
    meta["telemetry_bytes"] = os.path.getsize(tel_path) if tel_path and os.path.exists(tel_path) else None

    nd = {"mean_wind_mps": 4, "gust_sigma_mps": 4, "dock_jitter_m": 4, "cycle_time_s": 3, "worst_revisit_ground_s": 3,
          "mean_revisit_ground_s": 3, "worst_revisit_gallery_s": 3, "gallery_coverage": 4, "detection_latency_s": 3,
          "verify_time_s": 3,
          "min_inter_uav_m": 4, "tracking_rmse_m": 5, "control_effort_N2s": 3, "energy_wh": 5,
          "min_obstacle_clearance_m": 4, "guard_speed_mps": 4, "guard_stop_mean_s": 3,
          "worst_revisit_ground_eqwin_s": 3, "waypoint_rmse_m": 5, "torque_effort_N2m2s": 5}
    for k, n in nd.items():
        row[k] = _num(row[k], n)
    os.makedirs(os.path.dirname(summ_path), exist_ok=True)
    out = {"row": row, "meta": meta}
    tmp = summ_path + ".tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, summ_path)                            # atomic: a killed batch never leaves half a summary
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--scene", default="all", choices=SCENES + ("all",))
    ap.add_argument("--condition", default="all", choices=CONDITIONS + ("all",))
    ap.add_argument("--trials", type=int, default=50, help="seeds per (scene, condition) cell")
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--duration", type=float, default=None,
                    help=f"simulated s per run, every condition; default per scene {DEFAULT_DURATION_S}")
    ap.add_argument("--uav-duration", type=float, default=None,
                    help="simulated s per UAV run (uav_sectors, uav_offset_ring); overrides --duration for them")
    ap.add_argument("--guard-duration", type=float, default=None,
                    help="simulated s per guard run; overrides --duration for guard_baseline")
    ap.add_argument("--eqwin", type=float, default=EQWIN_S,
                    help="equal window [0, eqwin] s for worst_revisit_ground_eqwin_s (every condition)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--out", default=CANONICAL)
    ap.add_argument("--no-vision", action="store_true", help="skip camera rendering / E051 detection")
    ap.add_argument("--no-telemetry", action="store_true", help="skip the per-step contract-B files")
    ap.add_argument("--vision-hz", type=float, default=aps.DualUAVSurveillanceController.VISION_HZ,
                    help="surveillance camera render + detection rate, Hz")
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    runs_dir = os.path.join(HERE, "runs") if out == CANONICAL else os.path.join(os.path.dirname(out), "runs")
    scenes = SCENES if a.scene == "all" else (a.scene,)
    conds = CONDITIONS if a.condition == "all" else (a.condition,)
    seeds = list(range(a.seed0, a.seed0 + a.trials))
    def duration_of(s, c):
        own = a.guard_duration if c == "guard_baseline" else a.uav_duration
        if own is not None:
            return float(own)
        return float(a.duration if a.duration is not None else DEFAULT_DURATION_S[s])
    dur = {s: {c: duration_of(s, c) for c in conds} for s in scenes}
    for s in scenes:
        for c in conds:
            if a.eqwin > dur[s][c] + 1e-9:
                sys.exit(f"--eqwin {a.eqwin} s exceeds the {s}/{c} run of {dur[s][c]} s")
    opts = {"eqwin_s": a.eqwin} if a.eqwin != EQWIN_S else None
    jobs = [(s, c, k, dur[s][c], runs_dir, not a.no_vision, not a.no_telemetry, a.vision_hz, opts)
            for s in scenes for c in conds for k in seeds]
    print(f"{len(jobs)} runs ({len(scenes)} scene x {len(conds)} condition x {len(seeds)} seeds), "
          f"{a.workers} workers, runs dir {runs_dir}")

    results = []
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(run_one, jobs), 1):
            results.append(r)
            row, meta = r["row"], r["meta"]
            print(f"[{i:4d}/{len(jobs)}] {row['run_id']:32s} "
                  f"{'resumed' if meta.get('resumed') else f'{meta['wall_s']:7.1f} s wall'}  "
                  f"worst_revisit_ground {row['worst_revisit_ground_s']}  contacts {row['obstacle_contacts']}", flush=True)

    order = {(s, c, k): i for i, (s, c, k, *_) in enumerate(jobs)}
    results.sort(key=lambda r: order[(r["row"]["scene"], r["row"]["condition"], r["row"]["seed"])])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in results:
            w.writerow({c: ("" if r["row"][c] is None else r["row"][c]) for c in COLUMNS})

    files = {os.path.relpath(p, ROOT): sha(p) for p in
             [aps.SCENES[s] for s in scenes] + [os.path.join(ROOT, "models", f) for f in
                                                 ("common.xml", "uav_fleet.xml", "nmims_main_interior.xml", "nmims_main_campus.xml")]}
    code = {os.path.relpath(p, ROOT): sha(p) for p in
            (aps.__file__, fpb.__file__, os.path.join(ROOT, "src", "patrol_metrics.py"),
             os.path.join(ROOT, "src", "run_telemetry.py"), os.path.abspath(__file__))}
    not_measured = {}
    if a.no_vision:
        not_measured["detected"] = not_measured["detection_latency_s"] = not_measured["verify_time_s"] = \
            "UAV conditions: run with --no-vision"
    elif any(r["meta"].get("vision_status") not in (None, "active") for r in results):
        not_measured["detected"] = not_measured["detection_latency_s"] = not_measured["verify_time_s"] = \
            "UAV conditions: E051 detect_intruder_hsv not implemented in this build (surveillance FSM stayed in PATROL)"
    prov = {
        "csv_sha256": hashlib.sha256(open(out, "rb").read()).hexdigest(),
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": "analytics/run_benchmark.py",
        "command": " ".join([os.path.basename(sys.executable)] + sys.argv),
        "git_commit": git_commit(),
        "python": platform.python_version(), "mujoco": mujoco.__version__, "numpy": np.__version__,
        "platform": platform.platform(),
        "timestep_s": sorted({r["row"]["timestep_s"] for r in results}),
        "trials_per_cell": a.trials, "seeds": seeds, "scenes": list(scenes), "conditions": list(conds),
        "duration_s": dur,
        "windows": {"simulated_duration_s": dur, "eqwin_s": a.eqwin,
                    "primary_metric": "cycle_time_s: mean time per completed full ground lap (window-independent; "
                                      "needs >= 2 lap completions in the run)",
                    "equal_window_metric": f"worst_revisit_ground_eqwin_s: longest unserviced interval of any ground "
                                           f"checkpoint within [0, {a.eqwin:g}] s, every condition incl. the guard, "
                                           "from the run's own per-step service times (patrol_metrics."
                                           "worst_revisit_window)",
                    "unequal_window_columns": "worst_revisit_ground_s, mean_revisit_ground_s, worst_revisit_gallery_s, "
                                              "n_ground_laps are over each run's own duration (guard and UAV windows "
                                              "differ); never compare them across conditions as primary"},
        "code_sha_combined": code_sha(), "model_sha_combined": model_sha(),
        "vision": not a.no_vision, "telemetry": not a.no_telemetry, "vision_hz": a.vision_hz,
        "randomisation": {s: RANDOMISATION[s] for s in scenes},
        "guard_config": fpb.CONFIG,
        "model_sha256_16": files, "code_sha256_16": code,
        "not_applicable": {"by_condition": PER_CONDITION_NA, "by_scene": PER_SCENE_NA},
        "not_measured": not_measured,
        "definitions": {"revisit_cycle_coverage": "src/patrol_metrics.py checkpoint_metrics",
                        "tracking_rmse_m (CROSS-TRACK), waypoint_rmse_m (timed waypoint path), control_effort_N2s "
                        "(THRUST effort, sum F^2 dt), torque_effort_N2m2s (integral |tau_body|^2 dt), energy_wh":
                            "DualUAVSurveillanceController.flight_metrics",
                        "n_laps_alpha, n_laps_bravo, n_laps_guard": "completed passes of each agent's own route "
                                                                    "(guard: completed ground cycles)",
                        "obstacle_contacts, uav_uav_contacts": "DualUAVSurveillanceController._log_contacts (onsets)",
                        "min_inter_uav_m": "min centre distance once both UAVs have left the takeoff phase",
                        "detected, detection_latency_s, verify_time_s":
                            "UAV: DualUAVSurveillanceController.surveillance_metrics (FSM incidents, true detection "
                            "= verify fix within MATCH_M of the intruder); guard: foot_patrol_baseline line of sight"},
        "runs": {r["row"]["run_id"]: {k: r["meta"].get(k) for k in ("wall_s", "telemetry_path", "telemetry_bytes",
                                                                      "vision_status", "resumed", "surveillance")}
                 for r in results},
    }
    prov_path = os.path.splitext(out)[0] + ".provenance.json"
    json.dump(prov, open(prov_path, "w"), indent=2)
    print(f"\nwrote {out}\nwrote {prov_path}")


if __name__ == "__main__":
    main()
