"""
Right-censoring of the equal-window worst revisit (worst_revisit_ground_eqwin_s) | analysis layer, CSV columns only.

src/patrol_metrics.worst_revisit_window scores a ground checkpoint that was never serviced in [0, eqwin_s] as
exactly eqwin_s, and the gap from the last service to the window end also counts. A value >= eqwin_s therefore means
"at least eqwin_s": the run is right-censored (no revisit inside the window), not a measured revisit time. A
cell whose values are all censored has sd 0, so t, d and CI on this metric are meaningless and are never computed.
Cycle time (cycle_time_s) stays the primary metric.

Everything here is derived from the CSV columns worst_revisit_ground_eqwin_s and eqwin_s; no constant is typed in.
"""
EQWIN_METRIC = "worst_revisit_ground_eqwin_s"
EQWIN_COL = "eqwin_s"
TOL_S = 1e-6   # a value within TOL_S below the window counts as reaching it (CSV carries 3 decimals)


def _f(x):
    x = (x or "").strip() if isinstance(x, str) else x
    return None if x in ("", None) else float(x)


def cell_stats(rows, scene, cond):
    """dict(n, k_censored, window_s, uav_max_s, values) for one cell; None when the cell has no equal-window values.
    window_s is the single eqwin_s of the cell (ValueError if the cell mixes windows)."""
    sel = [r for r in rows if r["scene"] == scene and r["condition"] == cond and _f(r.get(EQWIN_METRIC)) is not None]
    if not sel:
        return None
    wins = sorted({_f(r[EQWIN_COL]) for r in sel})
    if len(wins) != 1 or wins[0] is None:
        raise ValueError(f"{scene}/{cond}: one eqwin_s per cell expected, got {wins}")
    w = wins[0]
    vals = [_f(r[EQWIN_METRIC]) for r in sel]
    return dict(n=len(vals), k_censored=sum(1 for v in vals if is_censored(v, w)), window_s=w,
                max_s=max(vals), values=vals)


def is_censored(value, window_s, tol=TOL_S):
    return value >= window_s - tol


def censored_count(values, window_s):
    return sum(1 for v in values if is_censored(v, window_s))


def uav_worst_max(rows, scene, uav_conditions):
    """Largest worst revisit over every run of the UAV cells in the scene (None when absent)."""
    v = [x for c in uav_conditions for x in (cell_stats(rows, scene, c) or {}).get("values", [])]
    return max(v) if v else None


def guard_value_text(window_s):
    return f">= {window_s:g} s (right-censored)"


def descriptive_line(rows, scene, guard="guard_baseline", uav_conditions=("uav_sectors", "uav_offset_ring")):
    """'k of N guard runs had no revisit inside W s; UAV worst revisit max X s' (all four numbers computed)."""
    g = cell_stats(rows, scene, guard)
    if g is None:
        return f"{scene}: equal-window worst revisit not measured (column absent or empty)"
    x = uav_worst_max(rows, scene, uav_conditions)
    xt = "not measured" if x is None else f"{x:.2f} s"
    return (f"{g['k_censored']} of {g['n']} guard runs had no revisit inside {g['window_s']:g} s; "
            f"UAV worst revisit max {xt}")


def revisit_gate(uav_values, window_s):
    """Gate PASS only if EVERY UAV worst revisit < window_s (a UAV run at exactly the window is censored -> FAIL).
    The guard value is only a lower bound (>= window_s), so it is not compared with the UAV mean."""
    return bool(uav_values) and all(v < window_s - TOL_S for v in uav_values)


GATE_REASONING = ("guard worst revisit is right-censored (>= window), a lower bound; the gate therefore passes only "
                  "if every UAV worst revisit in the cell is below the window (a UAV run at the window is censored too)")
