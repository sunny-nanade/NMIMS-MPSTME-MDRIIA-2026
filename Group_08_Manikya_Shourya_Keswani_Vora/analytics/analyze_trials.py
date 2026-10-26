"""
Group 08 SkyHydro: statistics + figures from OUR MuJoCo trials (Telemetry QA: E032).

Reads  analytics/flood_relief_real_trials.csv   (written by src/flood_relief_drop_sim.py)
       analytics/telemetry/*.csv.gz             (500 Hz logs, for the trajectory plot)
Writes docs/figures/fig_trajectory.png, docs/figures/fig_boxplot.png, analytics/trial_stats.json

Primary metric: radial drop error (m) = horizontal distance between the canister's first
contact point and the drop-marker centre, for every run in which the canister was released.
Baseline vs proposed: Welch's two-sided t-test (alpha 0.05), Cohen's d (pooled SD), 95 % CI
of the difference (Welch-Satterthwaite df). Mann-Whitney U is reported as a robustness check.
"""
import csv
import glob
import gzip
import json
import math
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(ROOT, "docs", "figures")


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    t, p = stats.ttest_ind(a, b, equal_var=False)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    diff = a.mean() - b.mean()
    half = stats.t.ppf(0.975, df) * math.sqrt(va + vb)
    sp = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    d = diff / sp if sp > 0 else float("nan")
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    return dict(n_a=len(a), n_b=len(b), mean_a=a.mean(), sd_a=a.std(ddof=1), mean_b=b.mean(), sd_b=b.std(ddof=1),
                t=float(t), df=float(df), p=float(p), cohens_d=float(d), diff=float(diff),
                ci95=(float(diff - half), float(diff + half)), mannwhitney_p=float(u.pvalue))


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "flood_relief_real_trials.csv"))))
    f = lambda r, k: float(r[k]) if r[k] not in ("", "nan") else float("nan")
    B = [r for r in rows if r["controller"] == "baseline"]
    P = [r for r in rows if r["controller"] == "proposed"]
    winds = sorted({float(r["wind_ms"]) for r in rows})
    out = {"n_total": len(rows), "per_condition": {}, "tests": {}}

    def col(R, k, released_only=False):
        v = [f(r, k) for r in R if (not released_only or r["released"] == "1")]
        return [x for x in v if x == x]

    # measures over all runs of each controller
    for name, k, rel in (("radial_error_m", "radial_error_m", True), ("rmse_path_m", "rmse_path_m", False),
                         ("control_effort_N2s", "control_effort_N2s", False), ("max_swing_deg", "max_swing_deg", False),
                         ("swing_at_release_deg", "swing_at_release_deg", True), ("endurance_min", "endurance_min", False)):
        out["tests"][name] = welch(col(B, k, rel), col(P, k, rel))
    for ctrl, R in (("baseline", B), ("proposed", P)):
        for w in winds:
            S = [r for r in R if float(r["wind_ms"]) == w]
            err = col(S, "radial_error_m", True)
            out["per_condition"][f"{ctrl}_w{int(w)}"] = dict(
                n=len(S), released=sum(r["released"] == "1" for r in S),
                success_rate=sum(r["outcome"] == "delivered" for r in S) / len(S),
                missed_into_water=sum(r["outcome"] == "missed_into_water" for r in S),
                off_zone_on_roof=sum(r["outcome"] == "off_zone_on_roof" for r in S),
                aborted=sum(r["outcome"].startswith("aborted") for r in S),
                crashed=sum(r["outcome"] == "crashed" for r in S),
                CEP_m=float(np.median(err)) if err else float("nan"),
                mean_err_m=float(np.mean(err)) if err else float("nan"),
                rmse_m=float(np.mean(col(S, "rmse_path_m"))), effort=float(np.mean(col(S, "control_effort_N2s"))),
                max_swing_deg=float(np.mean(col(S, "max_swing_deg"))),
                endurance_min=float(np.mean(col(S, "endurance_min"))))
        out[f"{ctrl}_success_rate"] = sum(r["outcome"] == "delivered" for r in R) / len(R)
        out[f"{ctrl}_unsafe_drop_rate"] = sum(r["outcome"] in ("missed_into_water", "off_zone_on_roof") for r in R) / len(R)
    # per-wind tests of the primary metric
    out["tests_by_wind"] = {}
    for w in winds:
        a = col([r for r in B if float(r["wind_ms"]) == w], "radial_error_m", True)
        b = col([r for r in P if float(r["wind_ms"]) == w], "radial_error_m", True)
        if len(a) > 2 and len(b) > 2:
            out["tests_by_wind"][f"w{int(w)}"] = welch(a, b)
    out["log_hz"] = float(rows[0]["log_hz"])
    # FBD check: steady hover in one logged 10 m/s run (dossier 2.4)
    tl = sorted(glob.glob(os.path.join(HERE, "telemetry", "*proposed_w10*.csv.gz")))
    if tl:
        rid = int(os.path.basename(tl[0]).split("_")[1])
        mrow = next(r for r in rows if int(r["run_id"]) == rid)
        with gzip.open(tl[0], "rt") as fh:
            H = [r for r in csv.DictReader(fh) if r["fsm_name"] == "HOVER"]
        sw = np.array([float(r["swing_deg"]) for r in H]); th = np.array([[float(r[f"T{i}_N"]) for i in range(1, 5)] for r in H])
        wy = np.array([float(r["wind_y"]) for r in H])
        mp = float(mrow["payload_kg"])
        pred = math.degrees(math.atan(0.5 * 1.225 * 0.08 * np.mean(wy) ** 2 / (mp * 9.81)))
        out["fbd_check"] = dict(run_id=rid, payload_kg=mp, n=len(H), swing_mean=float(sw.mean()), swing_sd=float(sw.std()),
                                thrust_per_rotor=float(th.mean()), wind_mean=float(wy.mean()), swing_pred=pred,
                                text=(f"run {rid} ({os.path.basename(tl[0])}), m_p = {mp:.2f} kg, HOVER state, {len(H)} samples at 500 Hz: "
                                      f"swing_deg = {sw.mean():.1f} ± {sw.std():.1f}° vs {pred:.1f}° predicted for the mean wind {wy.mean():.1f} m/s "
                                      f"(gusts make it swing about that value); mean T1_N…T4_N = {th.mean():.1f} N per rotor vs "
                                      f"{(3.355 + mp) * 9.81 / 4:.1f} N static prediction."))
    out["mean_samples_per_run"] = float(np.mean([int(r["n_samples"]) for r in rows]))
    json.dump(out, open(os.path.join(HERE, "trial_stats.json"), "w"), indent=1, default=float)

    # ---------------------------------------------------------------- figures
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    os.makedirs(FIG, exist_ok=True)

    fig, ax = plt.subplots(figsize=(3.7, 2.8))
    pos, data, cols = [], [], []
    for i, w in enumerate(winds):
        for j, (R, c) in enumerate(((B, "#c0392b"), (P, "#1f6fb4"))):
            data.append(col([r for r in R if float(r["wind_ms"]) == w], "radial_error_m", True))
            pos.append(i * 3 + j); cols.append(c)
    bp = ax.boxplot(data, positions=pos, widths=0.75, patch_artist=True, showfliers=True,
                    flierprops=dict(markersize=2.5))
    for patch, c in zip(bp["boxes"], cols):
        patch.set_facecolor(c); patch.set_alpha(0.55)
    for med in bp["medians"]:
        med.set_color("black")
    ax.axhline(2.0, color="#777", ls="--", lw=0.8); ax.text(len(winds) * 3 - 1.7, 2.08, "zone r = 2 m", fontsize=7, color="#555")
    ax.set_xticks([i * 3 + 0.5 for i in range(len(winds))]); ax.set_xticklabels([f"{w:.0f}" for w in winds])
    ax.set_xlabel("mean crosswind (m/s)"); ax.set_ylabel("radial drop error (m)")
    nb = sum(len(x) for x in data[0::2]); npp = sum(len(x) for x in data[1::2])
    ax.set_title(f"Drop error: baseline (red, n={nb}) vs proposed (blue, n={npp})", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_boxplot.png"), dpi=200); plt.close(fig)

    tel = sorted(glob.glob(os.path.join(HERE, "telemetry", "*proposed_w10*.csv.gz")))
    if tel:
        with gzip.open(tel[0], "rt") as fh:
            rd = list(csv.DictReader(fh))
        T = np.array([[float(r[k]) for k in ("t_s", "x", "y", "z", "x_ref", "y_ref", "z_ref", "payload_x", "payload_y", "payload_z", "fsm_state")] for r in rd])
        fig, ax = plt.subplots(2, 1, figsize=(3.7, 3.8))
        ax[0].plot(T[:, 4], T[:, 5], "--", color="#555", lw=1, label="reference")
        ax[0].plot(T[:, 1], T[:, 2], color="#1f6fb4", lw=1.2, label="UAV")
        ax[0].plot(T[:, 7], T[:, 8], color="#e67e22", lw=0.8, alpha=0.8, label="canister")
        ax[0].add_patch(plt.Circle((0, 0), 2.0, fill=False, color="#b7950b"))
        ax[0].set_xlabel("x (m)"); ax[0].set_ylabel("y (m)"); ax[0].set_aspect("auto")
        ax[0].set_title("Top view, proposed, 10 m/s crosswind (+y)", fontsize=8); ax[0].legend(frameon=False, fontsize=7)
        ax[1].plot(T[:, 0], T[:, 6], "--", color="#555", lw=1, label="z_ref")
        ax[1].plot(T[:, 0], T[:, 3], color="#1f6fb4", lw=1.2, label="UAV z")
        ax[1].plot(T[:, 0], T[:, 9], color="#e67e22", lw=0.8, label="canister z")
        st = T[:, 10]
        names = ["TAKEOFF", "CRUISE", "APPROACH", "HOVER", "WINCH↓", "RELEASE", "WINCH↑", "RTB", "ABORT"]
        for k in np.flatnonzero(np.diff(st)) + 1:
            ax[1].axvline(T[k, 0], color="#ddd", lw=0.6)
            ax[1].text(T[k, 0], 19.5, names[int(st[k])], rotation=90, fontsize=6, va="top", color="#666")
        ax[1].set_xlabel("t (s)"); ax[1].set_ylabel("z (m)"); ax[1].set_ylim(0, 20)
        ax[1].set_title("Altitude and FSM states (500 Hz log)", fontsize=8); ax[1].legend(frameon=False, fontsize=7, loc="lower right")
        fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_trajectory.png"), dpi=200); plt.close(fig)

    t = out["tests"]["radial_error_m"]
    print(f"radial drop error: baseline {t['mean_a']:.3f} ± {t['sd_a']:.3f} m (n={t['n_a']}), "
          f"proposed {t['mean_b']:.3f} ± {t['sd_b']:.3f} m (n={t['n_b']})")
    print(f"Welch t({t['df']:.1f}) = {t['t']:.2f}, p = {t['p']:.2e}, d = {t['cohens_d']:.2f}, "
          f"95% CI of diff [{t['ci95'][0]:.3f}, {t['ci95'][1]:.3f}] m; Mann-Whitney p = {t['mannwhitney_p']:.2e}")
    for k in ("rmse_path_m", "control_effort_N2s", "max_swing_deg"):
        s = out["tests"][k]
        print(f"{k}: baseline {s['mean_a']:.3f} ± {s['sd_a']:.3f}, proposed {s['mean_b']:.3f} ± {s['sd_b']:.3f}, p = {s['p']:.2e}")
    print(f"success: baseline {out['baseline_success_rate']:.1%}, proposed {out['proposed_success_rate']:.1%}; "
          f"unsafe drops: baseline {out['baseline_unsafe_drop_rate']:.1%}, proposed {out['proposed_unsafe_drop_rate']:.1%}")
    for k, v in out["per_condition"].items():
        print(f"  {k:<14} n={v['n']} success {v['success_rate']:.0%}  CEP {v['CEP_m']:.2f} m  water {v['missed_into_water']} "
              f"off-zone {v['off_zone_on_roof']} aborted {v['aborted']} crashed {v['crashed']}  RMSE {v['rmse_m']:.2f}")


if __name__ == "__main__":
    main()
