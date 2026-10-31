"""
Shared checkpoint-service metrics | MDRIIA Group 05 | Owner: E043 Muaaz

ONE function, checkpoint_metrics(), turns a record of checkpoint services into the
revisit / cycle / coverage columns of the trial CSV (contract A). Every condition --
guard_baseline, uav_sectors, uav_offset_ring -- goes through it, so the guard and the
UAVs are scored by the same rule.

Input: visits = {checkpoint name: [service times, s]} (names as in the MJCF sites,
patrol_cp<k> = ground loop / perimeter, atrium_cp<k> = gallery checkpoints).
A "service" is the UAV passing within ARRIVE_R of the checkpoint, or the guard
reaching the walkable observation point defined for it in src/foot_patrol_baseline.py.

Definitions (s = seconds):
  worst_revisit_ground_s   PRIMARY. Max gap between consecutive services of any
                           ground checkpoint. Empty (None) unless EVERY ground
                           checkpoint was serviced at least twice, because otherwise
                           the true worst gap is not observable within the run.
  mean_revisit_ground_s    Mean of all consecutive-service gaps of ground checkpoints
                           (same availability rule).
  worst_revisit_gallery_s  As worst_revisit_ground_s for the gallery checkpoints.
  gallery_coverage         Fraction of gallery checkpoints serviced at least once.
  n_ground_laps            Number of completed full ground cycles: a cycle completes
                           when every ground checkpoint has been serviced at least once
                           since the previous completion.
  cycle_time_s             Mean time between consecutive cycle completions (needs >= 2).
Gallery values are None when the scene has no gallery checkpoints (exterior).
"""

GROUND = "patrol_cp"
GALLERY = "atrium_cp"


def _route(visits, prefix):
    return {n: sorted(ts) for n, ts in visits.items() if n.startswith(prefix)}


def _gaps(route):
    if not route or any(len(ts) < 2 for ts in route.values()):
        return None
    return [b - a for ts in route.values() for a, b in zip(ts, ts[1:])]


def checkpoint_metrics(visits, ground_prefix=GROUND, gallery_prefix=GALLERY):
    """Contract-A revisit / cycle / coverage metrics from {checkpoint: [service times]}."""
    ground, gallery = _route(visits, ground_prefix), _route(visits, gallery_prefix)
    g = _gaps(ground)
    out = {
        "worst_revisit_ground_s": max(g) if g else None,
        "mean_revisit_ground_s": sum(g) / len(g) if g else None,
        "worst_revisit_gallery_s": None,
        "gallery_coverage": None,
    }
    if gallery:
        gg = _gaps(gallery)
        out["worst_revisit_gallery_s"] = max(gg) if gg else None
        out["gallery_coverage"] = sum(1 for ts in gallery.values() if ts) / len(gallery)

    completions, seen = [], set()
    for t, name in sorted((t, n) for n, ts in ground.items() for t in ts):
        seen.add(name)
        if ground and len(seen) == len(ground):
            completions.append(t)
            seen = set()
    out["n_ground_laps"] = len(completions)
    out["cycle_time_s"] = ((completions[-1] - completions[0]) / (len(completions) - 1)
                           if len(completions) >= 2 else None)
    return out


def worst_revisit_window(visits, window_s, prefix=GROUND):
    """
    Equal-window worst revisit (G-08): the longest sub-interval of [0, window_s] during which
    some ground checkpoint was NOT serviced, over all ground checkpoints. Censored at both ends
    (the gap from t = 0 to the first service and from the last service to window_s count), so it
    is defined for every run, also when a checkpoint is serviced fewer than twice in the window;
    a checkpoint never serviced in the window scores window_s. Only services with t <= window_s
    are used, so a long run and a short run are scored on the same window. Service times come
    from the run's own per-step (0.002 s) trajectory test (UAV: within ARRIVE_R; guard: at the
    observation point). Returns None when the scene has no checkpoints with this prefix.
    """
    route = _route(visits, prefix)
    if not route:
        return None
    W = float(window_s)
    worst = 0.0
    for ts in route.values():
        pts = [0.0] + [t for t in ts if 0.0 <= t <= W] + [W]
        worst = max(worst, max(b - a for a, b in zip(pts, pts[1:])))
    return worst
