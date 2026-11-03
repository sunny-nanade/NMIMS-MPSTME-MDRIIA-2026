"""Figures for the dossier / viva from REAL controller output (trials CSV + 500 Hz telemetry)."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "results", "figures")
os.makedirs(FIG, exist_ok=True)
C = {"baseline": "#c0504d", "proposed": "#2e75b6"}
STATE_NAMES = ["INIT", "ROW_FOLLOW", "SCAN", "ANOMALY_FLAG", "GEOTAG", "NEXT_ROW", "RETURN_TO_DOCK", "DONE"]


def box_panel(ax, df, col, title, ylabel):
    data = [df[df.condition == c][col].dropna().to_numpy() for c in ("baseline", "proposed")]
    bp = ax.boxplot(data, patch_artist=True, widths=0.55, showmeans=True)
    for patch, c in zip(bp["boxes"], ("baseline", "proposed")):
        patch.set_facecolor(C[c]); patch.set_alpha(0.6)
    for i, c in enumerate(("baseline", "proposed"), 1):
        y = data[i - 1]
        ax.scatter(np.random.default_rng(0).normal(i, 0.05, len(y)), y, s=10, color="k", alpha=0.5, zorder=3)
    ax.set_xticks([1, 2]); ax.set_xticklabels(["baseline", "proposed"])
    ax.set_title(title, fontsize=10); ax.set_ylabel(ylabel)


def fig_trials():
    df = pd.read_csv(os.path.join(ROOT, "analytics", "solar_inspection_real_trials.csv"))
    df = df[~df.seed.isin(df[(df.condition == "proposed") & (df.deferred == 1)].seed)]
    fig, ax = plt.subplots(2, 3, figsize=(12, 7))
    box_panel(ax[0, 0], df, "recall", "Recall", "defects found / present")
    box_panel(ax[0, 1], df, "precision", "Precision", "true flags / all flags")
    box_panel(ax[0, 2], df, "fp", "False alarms per mission", "modules")
    box_panel(ax[1, 0], df, "loc_err_mean_m", "Localisation error", "m")
    box_panel(ax[1, 1], df, "track_rmse_m", "Lane-tracking RMSE", "m")
    box_panel(ax[1, 2], df, "pose_err_rms_m", "Pose-estimate RMS error", "m")
    fig.suptitle(f"Monte Carlo, N = {len(df) // 2} paired missions per condition (deferred missions excluded)")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "mc_boxplots.png"), dpi=160); plt.close(fig)


def load_tel(cond):
    p = os.path.join(ROOT, "results", "telemetry", f"demo_{cond}_seed3009_500Hz.csv")
    return pd.read_csv(p) if os.path.exists(p) else None


def fig_paths():
    import sys
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from panel_registry import PanelRegistry
    reg = PanelRegistry(); c = reg.cfg
    fig, ax = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
    for a, cond in zip(ax, ("baseline", "proposed")):
        t = load_tel(cond)
        if t is None:
            continue
        for r in range(1, c.n_rows + 1):
            y0 = reg.row_low_y(r)
            a.add_patch(plt.Rectangle((c.x0, y0), c.row_length, c.panel_l * np.cos(c.tilt), color="#9db7d5", alpha=0.8))
        a.plot(t.x_true, t.y_true, color=C[cond], lw=1.2, label="true path (MuJoCo)")
        a.plot(t.x_est, t.y_est, color="k", lw=0.6, ls="--", label="robot's own estimate")
        a.set_aspect("equal"); a.set_title(f"{cond}: path over the array"); a.set_xlabel("x East [m]"); a.legend(loc="upper right", fontsize=8)
    ax[0].set_ylabel("y North [m]")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "paths.png"), dpi=160); plt.close(fig)


def fig_tracking_timeseries():
    fig, ax = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    for cond in ("baseline", "proposed"):
        t = load_tel(cond)
        if t is None:
            continue
        m = t.state.isin([1, 2]) & (t.x_true >= 0) & (t.x_true <= 10.5)
        ax[0].plot(t.t[m], t.cross_track_err[m] * 100, ".", ms=1, color=C[cond], label=cond)
        ax[1].plot(t.t, t.tau2_cum, color=C[cond], label=cond)
    ax[0].set_ylabel("cross-track error [cm]"); ax[0].legend(markerscale=8); ax[0].set_title("Row-following error (inside the array span)")
    ax[1].set_ylabel("cumulative  int tau^2 dt"); ax[1].set_xlabel("time [s]"); ax[1].legend()
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "tracking_and_effort.png"), dpi=160); plt.close(fig)


def fig_fsm():
    t = load_tel("proposed")
    if t is None:
        return
    fig, ax = plt.subplots(figsize=(12, 3.2))
    ax.step(t.t[::50], t.state[::50], where="post", color=C["proposed"])
    ax.set_yticks(range(len(STATE_NAMES))); ax.set_yticklabels(STATE_NAMES, fontsize=8)
    ax.set_xlabel("time [s]"); ax.set_title("FSM state timeline, proposed controller (500 Hz telemetry)")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fsm_timeline.png"), dpi=160); plt.close(fig)


if __name__ == "__main__":
    fig_trials(); fig_paths(); fig_tracking_timeseries(); fig_fsm()
    print("figures ->", FIG)
