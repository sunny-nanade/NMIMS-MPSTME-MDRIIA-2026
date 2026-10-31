#!/usr/bin/env python3
"""
Facts for docs/DOSSIER_FILL_SHEET.md (E043). Read-only: prints values read from the model, the controller source,
the real-trials CSV, a per-step telemetry file and git. Every line starts with a key such as [F-mass] so the fill
sheet can cite "docs/dossier_fill_facts_output.txt, key F-mass". Nothing here is typed in as a result.

  python docs/dossier_fill_facts.py [--telemetry-dir DIR] [--integration-tree DIR] [--csv PATH] > docs/dossier_fill_facts_output.txt

--csv                the trials CSV (default analytics/campus_patrol_real_trials.csv); its sha256 must equal the provenance
                     csv_sha256, otherwise the script stops (a test CSV needs its own .provenance.json)

--telemetry-dir      folder with <scene>_<condition>_s<seed>.csv.gz (analytics/runs is gitignored in a clone)
--integration-tree   group folder of a tree that already contains the E051/E075/E077 patches; only used to print
                     the line numbers of the same snippet there (they move when the teammate regions are merged).
"""
import argparse
import csv
import glob
import gzip
import math
import os
import re
import statistics as st
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "analytics"))
import mujoco                                   # noqa: E402
import numpy as np                              # noqa: E402
import aerial_patrol_swarm as aps               # noqa: E402
import censored_revisit as cr                  # noqa: E402  (right-censoring of the equal-window revisit)
import statistical_validation as sv              # noqa: E402  (hash gate and loader shared with the statistics)

C = aps.DualUAVSurveillanceController
SRC = os.path.join(ROOT, "src", "aerial_patrol_swarm.py")
CSV_PATH = os.path.join(ROOT, "analytics", "campus_patrol_real_trials.csv")


def L(a):
    return [float(x) for x in a]


def out(key, text):
    print(f"[{key}] {text}")


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args], stderr=subprocess.DEVNULL).decode().strip()


def model_facts():
    for scene, path in aps.SCENES.items():
        m = mujoco.MjModel.from_xml_path(path)
        out("F-load", f"{scene}: MjModel.from_xml_path OK ({os.path.relpath(path, ROOT)}), nu={m.nu} actuators, "
                      f"nbody={m.nbody}, ngeom={m.ngeom}, timestep={m.opt.timestep} s ({1.0 / m.opt.timestep:.0f} Hz), "
                      f"integrator={['Euler', 'RK4', 'implicit', 'implicitfast'][m.opt.integrator]}")
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(m.nu)]
        out("F-act", f"{scene}: actuators = {names}")
        # contact parameters of an airframe geom and of the world floor
        g_leg = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "alpha_leg0")
        g_flr = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "ground")
        for nm, g in (("alpha_leg0 (class quad)", g_leg), ("ground plane", g_flr)):
            out("F-contact", f"{scene}: {nm}: friction={L(np.round(m.geom_friction[g], 4))} condim={m.geom_condim[g]} "
                             f"solref={L(np.round(m.geom_solref[g], 4))} solimp={L(np.round(m.geom_solimp[g], 3))}")
        out("F-refsafe", f"{scene}: solref timeconst / timestep = {m.geom_solref[g_leg][0] / m.opt.timestep:.2f} "
                         f"(MuJoCo clamps timeconst below 2 x timestep unless refsafe is off)")
    m = mujoco.MjModel.from_xml_path(aps.SCENES["interior"])
    g = -m.opt.gravity[2]
    for name in ("uav_alpha", "uav_bravo"):
        bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, name)
        mass = float(m.body_subtreemass[bid])
        w = mass * g
        out("F-mass", f"{name}: body_subtreemass = {mass:.4f} kg; g = {g:.2f} m/s^2; W = m g = {mass:.4f} x {g:.2f} = {w:.3f} N; "
                      f"hover thrust per rotor = W/4 = {w / 4:.3f} N; max thrust 4 x {C.F_MAX} = {4 * C.F_MAX:.1f} N; "
                      f"T/W = {4 * C.F_MAX:.1f} / {w:.2f} = {4 * C.F_MAX / w:.2f}")
        bid_inertia = m.body_inertia[bid]
        out("F-inertia", f"{name}: principal inertia (kg m^2) = {L(np.round(bid_inertia, 5))}")


def contact_mix():
    """Drop the Alpha airframe on its dock with the rotors off and print the solref MuJoCo actually uses for a leg contact."""
    for scene in ("interior", "exterior"):
        c = aps.DualUAVSurveillanceController(aps.SCENES[scene], vision=False, wind_mps=0.0, gust_sigma=0.0)
        m, d = c.model, c.data
        u = c.uavs["alpha"]
        gids = {g for g in range(m.ngeom) if m.geom_bodyid[g] == u["bid"]}
        d.ctrl[:] = 0.0
        seen = {}
        for _ in range(int(1.0 / m.opt.timestep)):
            mujoco.mj_step(m, d)
            for i in range(d.ncon):
                cn = d.contact[i]
                if cn.geom1 in gids or cn.geom2 in gids:
                    n1 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, cn.geom1)
                    n2 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, cn.geom2)
                    seen[(n1, n2)] = (L(np.round(m.geom_solref[cn.geom1], 4)), L(np.round(m.geom_solref[cn.geom2], 4)),
                                      L(np.round(cn.solref, 4)))
        for (n1, n2), (s1, s2, sc) in sorted(seen.items(), key=lambda kv: str(kv[0]))[:2]:
            out("F-solref-mix", f"{scene}: leg contact {n1} / {n2}: geom solref {s1} and {s2} -> solref used by the solver {sc} "
                                f"(timestep {m.opt.timestep} s, 2 x timestep = {2 * m.opt.timestep:.3f} s; refsafe enabled = "
                                f"{bool(m.opt.disableflags & mujoco.mjtDisableBit.mjDSBL_REFSAFE == 0)})")
        out("F-solref-mix", f"{scene}: contacts seen {len(seen)}; all used time constants "
                            f"{sorted(set(v[2][0] for v in seen.values()))}")


def gains():
    rows = [
        ("KP_POS", C.KP_POS, "1/s (m/s of velocity command per m of position error)"),
        ("KP_VEL", C.KP_VEL, "1/s (m/s^2 per m/s)"),
        ("KI_VEL", C.KI_VEL, "1/s^2 (m/s^2 per m of integrated velocity error)"),
        ("I_CLAMP", C.I_CLAMP, "m (clamp on the integrated velocity error, per axis)"),
        ("KP_ATT [roll pitch yaw]", L(C.KP_ATT), "1/s^2 (rad/s^2 per rad; multiplied by the inertia matrix)"),
        ("KD_ATT [roll pitch yaw]", L(C.KD_ATT), "1/s (rad/s^2 per rad/s; multiplied by the inertia matrix)"),
        ("MAX_TILT_RATE", round(math.degrees(C.MAX_TILT_RATE), 1), "deg/s"),
        ("V_MAX_Z", C.V_MAX_Z, "m/s"),
        ("ARRIVE_R", C.ARRIVE_R, "m"),
        ("K_REP", C.K_REP, "N m^2 (APF gain)"),
        ("F_MAX", C.F_MAX, "N per rotor"), ("ARM_L", C.ARM_L, "m"), ("K_Q", C.K_Q, "m"),
    ]
    for n, v, u in rows:
        out("F-gain", f"{n} = {v} {u}")
    m_i = mujoco.MjModel.from_xml_path(aps.SCENES["interior"])
    m_e = mujoco.MjModel.from_xml_path(aps.SCENES["exterior"])
    for scene, m in (("interior", m_i), ("exterior", m_e)):
        def num(nm):
            i = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_NUMERIC, nm)
            return float(m.numeric_data[m.numeric_adr[i]]) if i >= 0 else None
        out("F-scene-num", f"{scene}: cruise_speed={num('cruise_speed')} m/s, max_tilt_deg={num('max_tilt_deg')} deg, "
                           f"d_warn={num('d_warn')} m, sidestep={num('sidestep')} m/s, alt_layer_bravo={num('alt_layer_bravo')} m, "
                           f"wind_scale={num('wind_scale')}")
    src_txt = open(SRC).read()
    ds = re.search(r"self\.d_safe_m\s*=\s*([\d.]+)", src_txt)
    out("F-sep", f"separation: d_safe = {ds.group(1) if ds else 'not found in source'} m (read from the source), APF F = K_REP (1/d - 1/d_safe) / d^2 for d < d_safe, "
                 f"layered governor between D_WARN and d_safe, sidestep to the right of the line of sight (src/aerial_patrol_swarm.py)")
    _mi = mujoco.MjModel.from_xml_path(aps.SCENES["interior"])
    _n_rf = sum(1 for i in range(_mi.nsite) if (mujoco.mj_id2name(_mi, mujoco.mjtObj.mjOBJ_SITE, i) or "").startswith("alpha_rf_"))
    out("F-fr18", f"FR-18: RF_RANGE_M={C.RF_RANGE_M} m, RF_SIGMA_M={C.RF_SIGMA_M} m, SENSE_HZ={C.SENSE_HZ} Hz, "
                  f"D_STOP_H={C.D_STOP_H} m, D_STOP_V={C.D_STOP_V} m, BRAKE_FRAC={C.BRAKE_FRAC}, T_REACT={C.T_REACT} s, "
                  f"A_BRAKE_V={C.A_BRAKE_V} m/s^2, BACKOFF_MPS={C.BACKOFF_MPS} m/s, H_BAND={C.H_BAND} m; beams per UAV = {_n_rf} (sites named *_rf_* in models/uav_fleet.xml)")
    out("F-fsm-consts", f"surveillance: VISION_HZ={C.VISION_HZ}, VERIFY_K={C.VERIFY_K}, VERIFY_GATE_M={C.VERIFY_GATE_M}, "
                        f"TRACK_MAX_S={C.TRACK_MAX_S}, TRACK_LOST_S={C.TRACK_LOST_S}, TRACK_GATE_M={C.TRACK_GATE_M}, "
                        f"TRACK_LEASH_M={C.TRACK_LEASH_M}, TRACK_STANDOFF_M={C.TRACK_STANDOFF_M}, CLOSED_GATE_M={C.CLOSED_GATE_M}")
    out("F-phases", f"flight phases (fsm_state while no incident): {sorted(set(C.PHASE_FSM.values()))}")
    out("F-fsm", "FSM states in code: PATROL, DETECT, VERIFY, ALERT_0..ALERT_3, TRACK, RETURN_TO_PATROL "
                 "(src/aerial_patrol_swarm.py, _fsm_step and _set_role)")


def snippet(path, label, start_text, n_lines):
    lines = open(path).read().splitlines()
    idx = [i for i, ln in enumerate(lines) if ln.strip() == start_text]
    if not idx:
        out(f"F-snip-{label}", f"start text not found in {path}")
        return
    i0 = idx[0]
    out(f"F-snip-{label}", f"{os.path.relpath(path)} lines {i0 + 1}-{i0 + n_lines} ({n_lines} lines)")
    for k in range(i0, i0 + n_lines):
        print(f"{k + 1:5d}  {lines[k]}")


def csv_stats(csv_path):
    try:
        rows, prov, digest = sv.load_validated(csv_path)
    except sv.Refused as e:
        raise SystemExit(f"[REFUSED] {e}")
    out("F-csv", f"{os.path.relpath(csv_path, ROOT) if csv_path.startswith(ROOT) else csv_path}: {len(rows)} rows; sha256 {digest} "
                 f"(equals provenance csv_sha256); code commit {prov.get('git_commit', prov.get('e043_commit'))}")
    cols = ["cycle_time_s", "worst_revisit_ground_s", "tracking_rmse_m", "waypoint_rmse_m",
            "control_effort_N2s", "torque_effort_N2m2s", "energy_wh", "min_inter_uav_m", "min_obstacle_clearance_m",
            "detection_latency_s", "verify_time_s", "n_ground_laps", "n_laps_alpha", "n_laps_bravo", "n_laps_guard"]
    for scene in sv.SCENES:
        for cond in sv.CONDITIONS:
            sub = [r for r in rows if r["scene"] == scene and r["condition"] == cond]
            seeds = sorted(int(r["seed"]) for r in sub)
            has = lambda c: c in sub[0]          # noqa: E731
            sm = lambda c: sum(int(float(r[c] or 0)) for r in sub) if has(c) else "column absent"      # noqa: E731
            out("F-cell", f"{scene}/{cond}: N={len(sub)} seeds {seeds[0]}..{seeds[-1]} dt={sorted(set(r['timestep_s'] for r in sub))} "
                          f"duration_s={sorted(set(r['duration_s'] for r in sub))} eqwin_s={sorted(set(r['eqwin_s'] for r in sub)) if has('eqwin_s') else 'column absent'} "
                          f"detected={sm('detected')}/{len(sub)} obstacle_contacts_total={sm('obstacle_contacts')} uav_uav_contacts_total={sm('uav_uav_contacts')}")
            cs = cr.cell_stats(rows, scene, cond)
            if cs is None:
                out("F-stat", f"{scene}/{cond}/{cr.EQWIN_METRIC}: not applicable or not measured (no values)")
            else:
                out("F-stat", f"{scene}/{cond}/{cr.EQWIN_METRIC}: right-censored at eqwin_s={cs['window_s']:g} s, no t test; "
                              f"censored runs {cs['k_censored']} of {cs['n']}; max={cs['max_s']:.4f}"
                              + ("" if cs["k_censored"] == cs["n"] else f" mean={st.mean(cs['values']):.4f} (lower bound where censored)"))
            for c in cols:
                v = [float(r[c]) for r in sub if c in r and r[c] not in ("", None)]
                if v:
                    sd = st.stdev(v) if len(v) > 1 else float("nan")
                    out("F-stat", f"{scene}/{cond}/{c}: n={len(v)} mean={st.mean(v):.4f} sd={sd:.4f} min={min(v):.4f} max={max(v):.4f}")
                else:
                    out("F-stat", f"{scene}/{cond}/{c}: not applicable or not measured (no values)")
    for scene in sv.SCENES:
        sub = [r for r in rows if r["scene"] == scene]
        for c in ("mean_wind_mps", "gust_sigma_mps", "intruder_appear_s", "dock_jitter_m"):
            v = [float(r[c]) for r in sub if r[c] not in ("", None)]
            if v:
                out("F-draw", f"{scene}/{c}: n={len(v)} min={min(v):.3f} max={max(v):.3f} mean={st.mean(v):.3f}")


def telemetry(tdir):
    if not tdir or not os.path.isdir(tdir):
        out("F-tel", "no telemetry directory given: logging rate not measured by this script")
        return
    files = sorted(glob.glob(os.path.join(tdir, "*.csv.gz")))
    out("F-tel", f"{len(files)} telemetry files in {tdir}")
    by_cell = {}
    for f in files:
        by_cell.setdefault(os.path.basename(f).rsplit("_s", 1)[0], []).append(f)
    for cell, fl in sorted(by_cell.items()):
        out("F-tel-cell", f"{cell}: {len(fl)} runs with per-step telemetry")
    p = os.path.join(tdir, "interior_uav_sectors_s1.csv.gz")
    if not os.path.exists(p):
        return
    ts, fsm, thrust = [], [], []
    with gzip.open(p, "rt") as fh:
        rd = csv.DictReader(fh)
        header = rd.fieldnames
        for r in rd:
            if r["uav"] == "alpha":
                ts.append(float(r["t"]))
                fsm.append(r["fsm_state"])
                thrust.append(sum(float(r[f"f{k}"]) for k in range(4)))
    dts = np.diff(ts)
    out("F-tel-rate", f"{os.path.basename(p)}: header={header}; alpha rows={len(ts)}; median dt={float(np.median(dts)):.4f} s "
                      f"(max dt {float(dts.max()):.4f} s) -> {1.0 / float(np.median(dts)):.0f} Hz; fsm states seen={sorted(set(fsm))}")
    patrol = [T for T, s in zip(thrust, fsm) if s == "PATROL"]
    if patrol:
        out("F-tel-hover", f"alpha total thrust f0+f1+f2+f3 while fsm_state == PATROL: median {float(np.median(patrol)):.3f} N "
                           f"(n={len(patrol)} rows); columns f0..f3 are the per-rotor forces in N")


def authorship():
    out("F-git-tip", git("log", "-1", "--format=%h %s"))
    out("F-git-count", f"commits main..HEAD touching this folder: {git('rev-list', '--count', 'main..HEAD', '--', '.')}")
    out("F-git-short", git("shortlog", "-sne", "HEAD", "--", ".").replace("\n", " | "))
    for f in ("models/campus_perimeter_patrol.xml", "models/campus_perimeter_patrol_exterior.xml", "models/common.xml",
              "models/uav_fleet.xml", "src/aerial_patrol_swarm.py", "src/foot_patrol_baseline.py", "src/patrol_metrics.py",
              "src/run_telemetry.py", "src/view_live.py", "analytics/run_benchmark.py", "analytics/generate_paper_figures.py",
              "analytics/campus_security_economics.py", "tests/test_e043_separation.py",
              "tests/test_e043_surveillance_fsm.py", "tests/test_e043_obstacle_perception.py"):
        n = git("rev-list", "--count", "HEAD", "--", f)
        first = git("log", "--diff-filter=A", "--format=%h %s", "--", f).splitlines()
        last = git("log", "-1", "--format=%h %s", "--", f)
        out("F-git-file", f"{f}: {n} commit(s); first: {first[-1] if first else '-'}; last: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--telemetry-dir")
    ap.add_argument("--integration-tree")
    ap.add_argument("--csv", default=CSV_PATH)
    a = ap.parse_args()
    model_facts()
    contact_mix()
    gains()
    snippet(SRC, "e043", 'if self.surv_state in ("DETECT", "VERIFY"):', 19)
    if a.integration_tree:
        snippet(os.path.join(a.integration_tree, "src", "aerial_patrol_swarm.py"), "integrated",
                'if self.surv_state in ("DETECT", "VERIFY"):', 19)
    csv_stats(os.path.abspath(a.csv))
    telemetry(a.telemetry_dir)
    authorship()


if __name__ == "__main__":
    main()
