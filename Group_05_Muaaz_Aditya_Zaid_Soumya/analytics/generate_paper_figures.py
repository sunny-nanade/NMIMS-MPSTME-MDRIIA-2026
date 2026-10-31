# Automation Script: Render 300 DPI publication figures from the real trial CSV
# Group: MDRIIA Group 05
# Project: Collaborative Dual-UAV Autonomous Surveillance System
# Owner: E043 Muaaz (integration) -- figures are READ-ONLY consumers of data.
#
# INTEGRITY RULES (PRD L-03):
#   * The ONLY benchmark input is analytics/campus_patrol_real_trials.csv, written
#     by analytics/run_benchmark.py together with campus_patrol_real_trials.provenance.json.
#     (A different CSV is accepted only for tests, with --csv and --out-dir, and only together
#     with its own provenance record; figures then never go to docs/figures.)
#   * The provenance record must exist and its csv_sha256 must match the CSV byte
#     for byte; otherwise the script refuses to draw anything.
#   * Any file whose name starts with SIMULATED_ (the course scaffold's synthetic
#     placeholder, kept only as a historical artefact) is refused outright, whether it
#     is the benchmark CSV or the one named with --csv.
#   * There is no placeholder / watermark mode: no data, no figure.
#
# Figures written to docs/figures/ (PNG, 300 DPI, no watermark; docs/figures/README.md is the faculty's and is never written):
#   trajectory_<scene>.png      plan view + speed of one representative run per condition
#   revisit_boxplot_<scene>.png box plots per condition: cycle_time_s (PRIMARY, window-independent) and
#                               worst_revisit_ground_eqwin_s (equal window, every condition), N and windows from the CSV
#   interior_obstacle_clearance.png  min_obstacle_clearance_m of the interior UAV runs, minimum marked
#   separation_hist_<scene>.png histogram of min_inter_uav_m of the UAV runs, design separation marked
#   fmea_before_after.png       RPN before / after each mitigation, read from campus_security_fmea.fmea_table
#                               (needs analytics/ablation_trials.csv + provenance; skipped with a message when absent)
#   video_poster.png            title card over a real MuJoCo render already in docs/figures/
#
# Representative-run rule (stated on every trajectory figure): among the runs of a cell whose
# per-run telemetry file is present, the run whose revisit metric (worst_revisit_ground_eqwin_s, or
# worst_revisit_ground_s for a CSV that predates it) is closest to the median of ALL runs of that cell (ties: lower seed). Without telemetry (for example a fresh
# clone, where analytics/runs/ is gitignored) the trajectory figures are skipped with a message;
# regenerate the runs with analytics/run_benchmark.py (same seeds give the same runs).
#
#   python analytics/generate_paper_figures.py --runs-dir <dir with <scene>_<condition>_s<seed>.csv.gz>

import argparse
import csv
import gzip
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import censored_revisit as cr                  # noqa: E402  (right-censoring of the equal-window revisit)
import statistical_validation as sv            # noqa: E402  (shared loader: sha256 gate, SIMULATED_ gate)
import campus_security_fmea as fmea            # noqa: E402  (FMEA table: before / after RPN)
ROOT = os.path.dirname(SCRIPT_DIR)
DOC_FIG_DIR = os.path.join(ROOT, "docs", "figures")
FIG_DIR = DOC_FIG_DIR
BENCH = os.path.join(SCRIPT_DIR, "campus_patrol_real_trials.csv")
PROVENANCE = os.path.join(SCRIPT_DIR, "campus_patrol_real_trials.provenance.json")
ABLATION = fmea.ABLATION_PATH
RUNS = os.path.join(SCRIPT_DIR, "runs")
MODELS = {"interior": os.path.join(ROOT, "models", "campus_perimeter_patrol.xml"),
          "exterior": os.path.join(ROOT, "models", "campus_perimeter_patrol_exterior.xml")}
CONDITIONS = ("guard_baseline", "uav_sectors", "uav_offset_ring")
LABELS = {"guard_baseline": "Guard foot patrol", "uav_sectors": "UAV sectors", "uav_offset_ring": "UAV offset ring"}
COLORS = {"guard_baseline": "#C62828", "uav_sectors": "#1565C0", "uav_offset_ring": "#2E7D32"}
UAV_COLORS = {"alpha": "#1565C0", "bravo": "#EF6C00", "guard": "#C62828"}
PLAN_STRIDE_S = 0.1          # telemetry thinning for plotting only (the physics step is the CSV timestep_s)
DPI = 300
POSTER_SOURCE = os.path.join("interior", "patrol_interior_late_chase_alpha.png")


def refuse(msg):
    print(f"[REFUSED] {msg}")
    print("          Produce real trials first: python analytics/run_benchmark.py --scene all --condition all")
    sys.exit(2)


def load_bench(csv_path=BENCH):
    """Read the real-trials CSV after checking it is provenanced (sha256 equal to the provenance csv_sha256) and not synthetic."""
    try:
        rows, prov, _digest = sv.load_validated(csv_path)
    except sv.Refused as e:
        refuse(str(e))
    if prov.get("generator") != "analytics/run_benchmark.py":
        refuse("provenance does not name analytics/run_benchmark.py as the generator")
    for r in rows:
        if "SIMULATED" in r["run_id"].upper():
            refuse(f"row {r['run_id']} is marked SIMULATED")
    return rows, prov


def revisit_metric(rows):
    """Equal-window revisit column when the batch has it, else the per-run-window column (stated on the figure)."""
    eq = "worst_revisit_ground_eqwin_s"
    if eq in rows[0] and any((r[eq] or "").strip() for r in rows):
        return eq
    return "worst_revisit_ground_s"


def timestep_text(rows):
    v = sorted({r["timestep_s"] for r in rows})
    return "/".join(v)


def cell(rows, scene, condition):
    return [r for r in rows if r["scene"] == scene and r["condition"] == condition]


def fval(r, name):
    try:
        v = float(r[name])
    except (KeyError, TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def col(rows, name, scene=None, condition=None):
    """Finite float values of one column, optionally filtered; empty cells are skipped (not measured)."""
    out = []
    for r in rows:
        if scene and r["scene"] != scene:
            continue
        if condition and r["condition"] != condition:
            continue
        v = fval(r, name)
        if v is not None:
            out.append(v)
    return np.array(out)


def duration_text(rows, scene, condition):
    d = sorted({float(r["duration_s"]) for r in cell(rows, scene, condition)})
    return "/".join(f"{x:g}" for x in d)


def eqwin_text(rows, scene):
    if "eqwin_s" not in rows[0]:
        return None
    d = sorted({float(r["eqwin_s"]) for r in rows if r["scene"] == scene and (r["eqwin_s"] or "").strip()})
    return "/".join(f"{x:g}" for x in d) if d else None


# ----------------------------------------------------------------------------------------------
# Telemetry (contract B)
# ----------------------------------------------------------------------------------------------
def read_telemetry(path, expect_run_id, stride_s=PLAN_STRIDE_S):
    """Contract-B file -> {vehicle: {t,x,y,z,speed}} thinned to one sample per stride_s; also the FSM-state set."""
    per, counters, states = {}, {}, set()
    step = None
    with gzip.open(path, "rt") as fh:
        for r in csv.DictReader(fh):
            if r["run_id"] != expect_run_id:
                raise ValueError(f"{path}: run_id {r['run_id']} is not {expect_run_id}")
            u = r["uav"]
            t = float(r["t"])
            if step is None and t > 0:
                step = t
            n = counters.get(u, 0)
            counters[u] = n + 1
            states.add(r["fsm_state"])
            if step is not None and n % max(1, int(round(stride_s / step))) != 0 and n != 1:
                continue
            d = per.setdefault(u, {"t": [], "x": [], "y": [], "z": [], "speed": []})
            d["t"].append(t); d["x"].append(float(r["x"])); d["y"].append(float(r["y"])); d["z"].append(float(r["z"]))
            d["speed"].append(float(np.sqrt(float(r["vx"]) ** 2 + float(r["vy"]) ** 2 + float(r["vz"]) ** 2)))
    return {u: {k: np.array(v) for k, v in d.items()} for u, d in per.items()}, states


def pick_representative(rows, scene, condition, runs_dir):
    """Run closest to the cell median of the revisit metric among runs whose telemetry file exists."""
    cr = cell(rows, scene, condition)
    metric = revisit_metric(rows)
    allv = [fval(r, metric) for r in cr]
    allv = [v for v in allv if v is not None]
    if not allv:
        return None, None
    med = float(np.median(allv))
    have = []
    for r in cr:
        v = fval(r, metric)
        p = os.path.join(runs_dir, f"{r['run_id']}.csv.gz")
        if v is not None and os.path.exists(p):
            have.append((abs(v - med), int(r["seed"]), r, p))
    if not have:
        return None, med
    have.sort(key=lambda h: (h[0], h[1]))
    return (have[0][2], have[0][3]), med


# ----------------------------------------------------------------------------------------------
# Scene footprint from the MuJoCo model (plan view of static box geoms)
# ----------------------------------------------------------------------------------------------
def scene_footprint(scene):
    """Plan-view polygons of the static geoms of a scene model, read from the model file itself."""
    import mujoco
    m = mujoco.MjModel.from_xml_path(MODELS[scene])
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    keep = {"interior": ("ext", "gf", "atrium", "rail", "planter"),
            "exterior": ("boundary", "bldg", "nmims", "campus")}[scene]
    walls, zone = [], None
    for i in range(m.ngeom):
        name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i) or ""
        if m.geom_type[i] != mujoco.mjtGeom.mjGEOM_BOX:
            continue
        if m.geom_bodyid[i] != 0 and "nmims_main_building" != mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[i]):
            continue
        sx, sy, _ = m.geom_size[i]
        R = d.geom_xmat[i].reshape(3, 3)
        c = d.geom_xpos[i]
        pts = np.array([c[:2] + (R[:2, :2] @ np.array([a * sx, b * sy])) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        if name.startswith("substation"):
            zone = pts
        elif name.startswith(keep):
            walls.append((name, pts))
    return walls, zone


def draw_footprint(ax, scene, cache={}):
    if scene not in cache:
        cache[scene] = scene_footprint(scene)
    walls, zone = cache[scene]
    for name, pts in walls:
        boundary = name.startswith("boundary")
        ax.add_patch(Polygon(pts, closed=True, facecolor="#455A64" if boundary else "#CFD8DC",
                             edgecolor="#455A64", lw=0.4, alpha=0.9 if boundary else 0.8, zorder=1))
    if zone is not None:
        ax.add_patch(Polygon(zone, closed=True, fill=False, edgecolor="#6A1B9A", lw=1.2, ls="--", zorder=2))
        ax.text(zone[:, 0].mean(), zone[:, 1].max() + 1.5, "restricted zone", fontsize=6, color="#6A1B9A", ha="center", zorder=5)


# ----------------------------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------------------------
def fig_trajectory(rows, scene, runs_dir):
    picks = {c: pick_representative(rows, scene, c, runs_dir) for c in CONDITIONS}
    if all(p[0] is None for p in picks.values()):
        print(f"[SKIP] trajectory_{scene}.png: no per-run telemetry in {runs_dir} "
              f"(regenerate with analytics/run_benchmark.py --scene {scene} --condition all, or pass --runs-dir)")
        return None
    fig, axes = plt.subplots(2, 3, figsize=(15, 9.2), gridspec_kw={"height_ratios": [3.2, 1]})
    used = {}
    all_xy = []
    for j, c in enumerate(CONDITIONS):
        axp, axs = axes[0, j], axes[1, j]
        (sel, med) = picks[c]
        axp.set_aspect("equal"); axp.grid(True, ls=":", alpha=0.5)
        axp.set_xlabel("x (m)"); axs.set_xlabel("simulation time (s)")
        if j == 0:
            axp.set_ylabel("y (m)"); axs.set_ylabel("speed (m/s)")
        axs.grid(True, ls=":", alpha=0.5)
        if sel is None:
            axp.set_title(f"{LABELS[c]}: telemetry not available", fontsize=10)
            axp.text(0.5, 0.5, "no per-run telemetry file\nfor this condition", ha="center", va="center", transform=axp.transAxes)
            continue
        row, path = sel
        tel, _ = read_telemetry(path, row["run_id"])
        draw_footprint(axp, scene)
        for u, tr in tel.items():
            axp.plot(tr["x"], tr["y"], color=UAV_COLORS.get(u, "k"), lw=0.9, alpha=0.9, zorder=3, label=u)
            axp.plot(tr["x"][0], tr["y"][0], "o", color=UAV_COLORS.get(u, "k"), ms=5, zorder=4)
            axs.plot(tr["t"], tr["speed"], color=UAV_COLORS.get(u, "k"), lw=0.5, alpha=0.8, label=u)
            all_xy.append(np.c_[tr["x"], tr["y"]])
        metric = revisit_metric(rows)
        wr = float(row[metric])
        used[c] = f"{row['run_id']} ({wr:.1f} s vs cell median {med:.1f} s)"
        win = float(row["eqwin_s"]) if metric.endswith("eqwin_s") else float(row["duration_s"])
        axp.set_title(f"{LABELS[c]}  -  {row['run_id']}\nworst revisit {wr:.1f} s in a {win:g} s window", fontsize=10)
        axp.legend(loc="upper right", fontsize=7, title="o = start", title_fontsize=6)
        axs.legend(loc="upper right", fontsize=7, ncol=2)
    if all_xy:
        xy = np.vstack(all_xy)
        pad = 0.08 * max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]))
        for j in range(3):
            axes[0, j].set_xlim(xy[:, 0].min() - pad, xy[:, 0].max() + pad)
            axes[0, j].set_ylim(xy[:, 1].min() - pad, xy[:, 1].max() + pad)
    fig.suptitle(f"{scene.capitalize()} scene: representative trajectories (plan view, x east / y north)", fontsize=12, fontweight="bold", y=0.995)
    fig.text(0.5, 0.005,
             f"Representative run = run with telemetry whose {revisit_metric(rows)} is closest to the cell median (ties: lower seed). "
             f"Telemetry thinned to {PLAN_STRIDE_S:g} s for plotting; physics step {timestep_text(rows)} s. "
             "Footprint: static box geoms of the MuJoCo model; UAV altitude not shown in plan.",
             ha="center", fontsize=7, color="#37474F")
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    out = os.path.join(FIG_DIR, f"trajectory_{scene}.png")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] {os.path.relpath(out, ROOT)}  representative runs: " + "; ".join(f"{k}={v}" for k, v in used.items()))
    return out


def _box_panel(ax, rows, scene, metric, ylabel, title, logy=False):
    """Box per condition. On the equal-window revisit metric a fully right-censored cell (guard: no revisit inside
    the window) is NOT drawn as a box (its sd is 0, a box or test would be meaningless): it gets a triangle at the
    window and the annotation '>= W s (right-censored), k of N runs'."""
    data, labels, cols, pos, cens = [], [], [], [], []
    for i, c in enumerate(CONDITIONS, start=1):
        v = col(rows, metric, scene, c)
        if not len(v):
            continue
        lab = f"{LABELS[c].replace(' ', chr(10), 1)}\nN = {len(v)}"
        cs = cr.cell_stats(rows, scene, c) if metric == cr.EQWIN_METRIC else None
        if cs is not None and cs["k_censored"] == cs["n"]:
            cens.append((i, c, cs, lab))
        else:
            data.append(v); labels.append(lab); cols.append(COLORS[c]); pos.append(i)
    if not data and not cens:
        ax.text(0.5, 0.5, f"{metric}: no values\n(column absent or not measured)", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title, fontsize=10)
        return False
    if data:
        bp = ax.boxplot(data, positions=pos, widths=0.5, patch_artist=True, showmeans=True,
                        meanprops=dict(marker="D", markerfacecolor="white", markeredgecolor="#212121", markersize=6),
                        medianprops=dict(color="#212121", lw=1.5))
    else:
        bp = {"boxes": []}
    rng = np.random.default_rng(0)      # jitter of the displayed points only (not data)
    for i, patch, color, v in zip(pos, bp["boxes"], cols, data):
        patch.set_facecolor(color); patch.set_alpha(0.35); patch.set_edgecolor(color); patch.set_linewidth(1.5)
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(v)), v, s=14, color=color, alpha=0.8, zorder=3)
        ax.text(i + 0.3, np.mean(v), f"mean {np.mean(v):.1f}", fontsize=8, va="center", color="#212121")
    for i, c, cs, lab in cens:
        ax.scatter([i], [cs["window_s"]], marker="^", s=120, color=COLORS[c], edgecolor="#212121", zorder=4)
        ax.annotate(f">= {cs['window_s']:g} s (right-censored)\n{cs['k_censored']} of {cs['n']} runs: no revisit\ninside the window; no test",
                    (i, cs["window_s"]), xytext=(0, -42), textcoords="offset points", ha="center", fontsize=8, color="#212121")
    allpos = [(i, lab) for i, _, _, lab in cens] + list(zip(pos, labels))
    allpos.sort()
    ax.set_xticks([a for a, _ in allpos]); ax.set_xticklabels([b for _, b in allpos])
    ax.set_xlim(0.4, len(CONDITIONS) + 0.6)
    if logy:
        ax.set_yscale("log")
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, which="both", axis="y", ls=":", alpha=0.6)
    ax.set_title(title, fontsize=10, fontweight="bold")
    return True


def fig_boxplot(rows, scene):
    """Two panels per scene: PRIMARY cycle_time_s and the equal-window worst revisit."""
    metric = revisit_metric(rows)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8))
    ok1 = _box_panel(axes[0], rows, scene, "cycle_time_s", "Mean time per completed ground lap (s, log scale)",
                     "PRIMARY: cycle time per lap (window-independent)", logy=True)
    eq = eqwin_text(rows, scene)
    if metric.endswith("eqwin_s"):
        t2 = f"Worst revisit gap, equal window ({eq} s, every condition)"
    else:
        t2 = "Worst revisit gap over each run's own window (batch predates the equal-window column)"
    ok2 = _box_panel(axes[1], rows, scene, metric, "Worst ground-checkpoint revisit gap (s)", t2)
    if not (ok1 or ok2):
        plt.close(fig)
        print(f"[SKIP] revisit_boxplot_{scene}.png: no rows")
        return None
    wins = "; ".join(f"{LABELS[c]} {duration_text(rows, scene, c)} s" for c in CONDITIONS)
    fig.suptitle(f"{scene.capitalize()} scene: patrol revisit performance per run", fontsize=12, fontweight="bold")
    fig.text(0.5, 0.005, f"Run windows (duration_s): {wins}. Same metric function for every condition. "
             "Cycle time needs >= 2 completed laps in a run (otherwise the run has no value).\n"
             "Box = quartiles, line = median, diamond = mean, dots = individual runs (horizontal jitter only). N = runs with a value. Triangle = right-censored at the window (lower bound, never a mean).",
             ha="center", fontsize=7, color="#37474F")
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    out = os.path.join(FIG_DIR, f"revisit_boxplot_{scene}.png")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] {os.path.relpath(out, ROOT)}")
    return out


def fig_separation(rows, scene):
    series = {c: col(rows, "min_inter_uav_m", scene, c) for c in ("uav_sectors", "uav_offset_ring")}
    series = {c: v for c, v in series.items() if len(v)}
    if not series:
        print(f"[SKIP] separation_hist_{scene}.png: no min_inter_uav_m values")
        return None
    allv = np.concatenate(list(series.values()))
    lo, hi = min(allv.min(), sv.D_SAFE_M), max(allv.max(), sv.D_SAFE_M)
    bins = np.linspace(lo, hi, 16) if hi > lo else 15
    fig, ax = plt.subplots(figsize=(8, 5.4))
    ax.hist(list(series.values()), bins=bins, color=[COLORS[c] for c in series], alpha=0.85,
            label=[f"{LABELS[c]} (N = {len(v)})" for c, v in series.items()], edgecolor="white")
    ax.axvline(sv.D_SAFE_M, color="#B71C1C", lw=2, ls="--")
    ax.text(sv.D_SAFE_M, ax.get_ylim()[1] * 0.95, f" design separation {sv.D_SAFE_M:g} m", color="#B71C1C", fontsize=9, va="top")
    below = {c: int((v < sv.D_SAFE_M).sum()) for c, v in series.items()}
    ax.set_xlabel("Per-run minimum UAV-UAV centre distance (m), after both UAVs have left the takeoff phase")
    ax.set_ylabel("Number of runs")
    ax.grid(True, axis="y", ls=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title(f"{scene.capitalize()} scene: inter-UAV separation", fontsize=12, fontweight="bold")
    contacts = {c: int(sum(float(r["uav_uav_contacts"]) for r in cell(rows, scene, c) if (r.get("uav_uav_contacts") or "") != "")) for c in series}
    fig.text(0.5, 0.005, "Runs below the design separation: " + ", ".join(f"{LABELS[c]} {n} of {len(series[c])}" for c, n in below.items())
             + "; UAV-UAV contacts (from the CSV): " + ", ".join(f"{LABELS[c]} {n}" for c, n in contacts.items()) + ".",
             ha="center", fontsize=7, color="#37474F")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = os.path.join(FIG_DIR, f"separation_hist_{scene}.png")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] {os.path.relpath(out, ROOT)}  min separation {allv.min():.3f} m")
    return out


def fig_fmea(rows, ablation_path):
    """RPN before / after each mitigation, read from fmea.fmea_table (no number is typed here)."""
    if not os.path.isfile(ablation_path):
        print(f"[SKIP] fmea_before_after.png: {os.path.relpath(ablation_path, ROOT)} not found "
              "(the ablation batch analytics/run_ablations.py has not produced it)")
        return None
    abl = fmea.load_ablation(ablation_path, sv.default_provenance(ablation_path))   # exits loudly on a bad hash
    table = fmea.fmea_table(rows, abl)
    scenes = [s for s in ("interior", "exterior") if any(r["scene"] == s for r in rows)]
    fig, axes = plt.subplots(1, len(scenes), figsize=(6.8 * len(scenes), 5.6), squeeze=False)
    n_unmeasured = 0
    for ax, scene in zip(axes[0], scenes):
        keys = [k for k, *_ in fmea.MODES]
        labs, before, after = [], [], []
        for k in keys:
            r = table[(scene, k)]
            labs.append(r["title"].split(" (")[0])
            if r["rpn_before"] is None or r["rpn_after"] is None:
                before.append(np.nan); after.append(np.nan); n_unmeasured += 1
            else:
                before.append(r["rpn_before"]); after.append(r["rpn_after"])
        y = np.arange(len(keys))
        ax.barh(y - 0.2, before, 0.4, color="#C62828", alpha=0.85, label="before (mitigation off)")
        ax.barh(y + 0.2, after, 0.4, color="#1565C0", alpha=0.85, label="after (production)")
        for yi, (b, a) in enumerate(zip(before, after)):
            if np.isnan(b):
                ax.text(0.5, yi, "not measured", va="center", fontsize=8, color="#37474F")
            else:
                ax.text(b, yi - 0.2, f" {b:g}", va="center", fontsize=8)
                ax.text(a, yi + 0.2, f" {a:g}", va="center", fontsize=8)
        ax.set_yticks(y)
        ax.set_yticklabels([l if len(l) < 38 else l[:36] + "..." for l in labs], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Risk priority number RPN = S x O x D")
        ax.set_title(f"{scene.capitalize()} scene", fontsize=11, fontweight="bold")
        ax.grid(True, axis="x", ls=":", alpha=0.6)
        ax.legend(loc="lower right", fontsize=8)
    fig.suptitle("FMEA: risk priority number before and after each mitigation", fontsize=12, fontweight="bold")
    fig.text(0.5, 0.005, "O and D are computed from measured failure and escape rates (analytics/campus_security_fmea.py; "
             "ablation_trials.csv for the before arm); S is team judgement. Rows without both arms are shown as not measured.",
             ha="center", fontsize=7, color="#37474F")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    out = os.path.join(FIG_DIR, "fmea_before_after.png")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] {os.path.relpath(out, ROOT)}  ({n_unmeasured} mode/scene rows not measured)")
    return out


def fig_clearance(rows):
    series = {c: col(rows, "min_obstacle_clearance_m", "interior", c) for c in ("uav_sectors", "uav_offset_ring")}
    series = {c: v for c, v in series.items() if len(v)}
    if not series:
        print("[SKIP] interior_obstacle_clearance.png: no interior UAV rows")
        return None
    allv = np.concatenate(list(series.values()))
    best = min((r for r in rows if r["scene"] == "interior" and fval(r, "min_obstacle_clearance_m") is not None),
               key=lambda r: fval(r, "min_obstacle_clearance_m"))
    bins = np.linspace(allv.min(), allv.max(), 16)
    fig, ax = plt.subplots(figsize=(8, 5.4))
    ax.hist(list(series.values()), bins=bins, color=[COLORS[c] for c in series], alpha=0.85,
            label=[f"{LABELS[c]} (N = {len(v)})" for c, v in series.items()], edgecolor="white")
    mn = float(allv.min())
    ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
    ax.axvline(mn, color="#B71C1C", lw=2)
    ax.annotate(f"minimum {mn:.3f} m\n({best['run_id']})", xy=(mn, ax.get_ylim()[1] * 0.8), xytext=(mn + 0.04 * np.ptp(allv), ax.get_ylim()[1] * 0.6),
                color="#B71C1C", fontsize=9, arrowprops=dict(arrowstyle="->", color="#B71C1C"))
    contacts = {c: int(sum(float(r["obstacle_contacts"]) for r in cell(rows, "interior", c) if r["obstacle_contacts"] != "")) for c in series}
    ax.set_xlabel("Per-run minimum obstacle clearance (m)\n(smallest range-ring beam length, airframe centre to surface)")
    ax.set_ylabel("Number of runs")
    ax.grid(True, axis="y", ls=":", alpha=0.6)
    ax.legend(loc="upper center", fontsize=9)
    ax.set_title("Interior scene: obstacle clearance of the dual-UAV patrol (FR-18)", fontsize=12, fontweight="bold")
    fig.text(0.5, 0.005, "Obstacle contacts (airframe vs any collidable geom, from the CSV): "
             + ", ".join(f"{LABELS[c]} {n}" for c, n in contacts.items()) + ". Clearance is measured to the centre, not the rotor tips.",
             ha="center", fontsize=7, color="#37474F")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = os.path.join(FIG_DIR, "interior_obstacle_clearance.png")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] {os.path.relpath(out, ROOT)}  min clearance {mn:.4f} m in {best['run_id']}")
    return out


def fig_poster():
    """Title card over a real MuJoCo render already in docs/figures/ (no numbers on it)."""
    src = os.path.join(DOC_FIG_DIR, POSTER_SOURCE)
    if not os.path.exists(src):
        print(f"[SKIP] video_poster.png: render {POSTER_SOURCE} not found")
        return None
    img = plt.imread(src)
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.imshow(img, extent=(0, 1280, 720, 0))
    ax.add_patch(plt.Rectangle((0, 0), 1280, 720, color="#0B1220", alpha=0.55))
    ax.add_patch(plt.Rectangle((40, 40), 1200, 640, fill=False, edgecolor="#90CAF9", lw=1.5))
    ax.text(70, 90, "SVKM'S NMIMS MPSTME  |  MDRIIA (702CO0E012)  |  SEMESTER VI (B.TECH CSBS)", color="#CFD8DC", fontsize=13, fontweight="bold")
    ax.text(70, 160, "MDRIIA GROUP 05  -  MPSTME GUARDIAN", color="#4FC3F7", fontsize=22, fontweight="bold")
    ax.text(70, 215, "Collaborative dual-UAV surveillance of the NMIMS Main Building,\nsimulated in MuJoCo, compared with a guard foot patrol",
            color="white", fontsize=17, va="top")
    ax.add_patch(plt.Circle((640, 480), 48, color="#2563EB", ec="#93C5FD", lw=3))
    ax.add_patch(Polygon([(623, 455), (623, 505), (668, 480)], closed=True, color="white"))
    ax.text(640, 560, "Simulation walkthrough (real MuJoCo render shown behind)", color="#ECEFF1", fontsize=13, ha="center")
    out = os.path.join(FIG_DIR, "video_poster.png")
    fig.savefig(out, dpi=100)
    plt.close(fig)
    print(f"[OK] {os.path.relpath(out, ROOT)}")
    return out


def generate_publication_assets(runs_dir, csv_path=BENCH, ablation_path=ABLATION):
    rows, prov = load_bench(csv_path)
    os.makedirs(FIG_DIR, exist_ok=True)
    scenes = [s for s in ("interior", "exterior") if any(r["scene"] == s for r in rows)]
    print(f"[INFO] {len(rows)} real trials from {os.path.relpath(csv_path, ROOT) if csv_path.startswith(ROOT) else csv_path} "
          f"(git commit {prov.get('git_commit', prov.get('e043_commit'))}, N = {prov.get('trials_per_cell')} per cell, timestep {prov.get('timestep_s')} s); "
          f"runs dir {runs_dir}; figures to {FIG_DIR}")
    if not os.path.isdir(runs_dir):
        print(f"[WARN] runs dir {runs_dir} does not exist: trajectory figures will be skipped")
    for s in scenes:
        fig_trajectory(rows, s, runs_dir)
        fig_boxplot(rows, s)
        fig_separation(rows, s)
    fig_clearance(rows)
    fig_fmea(rows, ablation_path)
    fig_poster()
    print(f"[DONE] figures in {FIG_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default=RUNS, help="directory of contract-B telemetry files (default analytics/runs)")
    ap.add_argument("--csv", default=BENCH, help="benchmark CSV (default analytics/campus_patrol_real_trials.csv); any other CSV needs "
                    "its own .provenance.json with a matching csv_sha256 and --out-dir; SIMULATED_* is refused")
    ap.add_argument("--ablation", default=ABLATION, help="ablation CSV for the FMEA figure (skipped when absent)")
    ap.add_argument("--out-dir", default=None, help="figure folder (default docs/figures; required for a non-canonical --csv)")
    a = ap.parse_args()
    if os.path.abspath(a.csv) != os.path.abspath(BENCH):
        if not a.out_dir or os.path.abspath(a.out_dir).startswith(os.path.abspath(os.path.join(ROOT, "docs"))):
            refuse("a non-canonical --csv needs --out-dir outside docs/ (test figures must never overwrite the dossier figures)")
    if a.out_dir:
        FIG_DIR = os.path.abspath(a.out_dir)
    generate_publication_assets(a.runs_dir, a.csv, a.ablation)
