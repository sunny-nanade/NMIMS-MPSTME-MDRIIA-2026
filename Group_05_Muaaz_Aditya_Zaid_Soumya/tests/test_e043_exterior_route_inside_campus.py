"""
Exterior patrol stays INSIDE the college | owner E043 Muaaz
  * every patrol_cp lies inside the campus boundary polygon (the boundary_wall_* geoms),
    tested by even-odd point-in-polygon
  * every ring leg, at Alpha's (patrol_cp altitude) and Bravo's (+4 m layer) patrol altitude, is clear: mj_ray
    from the leg start, on the centre line and offset by the FR-18 minimum clearances (0.6 m
    lateral, 0.35 m vertical), hits nothing before the next checkpoint
  * the guard baseline walks the same ring at ground level and every planned walking leg is clear
    for a body (src/foot_patrol_baseline.py, ground legs)
  * every UAV route leg clears the top of every roof within the sidestep reach of the leg by the FR-18
    vertical margin (footprints from the compiled model)
Prints the ring length (UAV ring and guard walking length). Lengths are geometry, not results.

  python -m pytest -s tests/test_e043_exterior_route_inside_campus.py
"""
import math
import os
import sys

import mujoco
import numpy as np

GROUP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GROUP, "src"))
import aerial_patrol_swarm as aps          # noqa: E402
import foot_patrol_baseline as fpb         # noqa: E402

LAT_CLEAR, VERT_CLEAR = 0.6, 0.35            # FR-18 minimum clearances (aerial_patrol_swarm D_STOP_H / D_STOP_V)


def load():
    m = mujoco.MjModel.from_xml_path(aps.SCENES["exterior"])
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    return m, d


def checkpoints(m):
    out, k = [], 0
    while (sid := mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, f"patrol_cp{k}")) >= 0:
        out.append(m.site_pos[sid].copy())
        k += 1
    return out


def boundary_polygon(m, d):
    """Wall centre line: each boundary_wall_<i> box is one edge, from its centre +- (half length - half
    thickness) along its own x axis (the builder pads the box by half a wall thickness)."""
    poly, i = [], 0
    while (gid := mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"boundary_wall_{i}")) >= 0:
        c, R = d.geom_xpos[gid], d.geom_xmat[gid].reshape(3, 3)
        half = m.geom_size[gid][0] - m.geom_size[gid][1]
        poly.append(tuple((c - R[:, 0] * half)[:2]))
        i += 1
    return poly


def inside(p, poly):
    x, y, ins = p[0], p[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            ins = not ins
    return ins


def test_every_checkpoint_inside_the_boundary_wall():
    m, d = load()
    poly = boundary_polygon(m, d)
    assert len(poly) >= 3
    cps = checkpoints(m)
    assert len(cps) >= 3
    for k, p in enumerate(cps):
        assert inside(p, poly), f"patrol_cp{k} at {p[:2]} is outside the campus boundary"
    ring = sum(math.dist(cps[i][:2], cps[(i + 1) % len(cps)][:2]) for i in range(len(cps)))
    wall = min(np.hypot(*(np.array(p[:2]) - np.array(q))) for p in cps for q in poly)
    print(f"\nexterior patrol ring: {len(cps)} checkpoints, {ring:.1f} m, all inside the wall "
          f"(min checkpoint-to-wall-corner distance {wall:.2f} m)")


def test_every_leg_clear_at_patrol_altitude():
    m, d = load()
    cps = checkpoints(m)
    layer_b = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], vision=False,
                                                frame_log=False)._num("alt_layer_bravo", 0.0)
    gid = np.zeros(1, dtype=np.int32)
    for dz_layer in (0.0, layer_b):
        for i in range(len(cps)):
            a, b = cps[i] + np.array([0, 0, dz_layer]), cps[(i + 1) % len(cps)] + np.array([0, 0, dz_layer])
            v = b - a
            L = float(np.linalg.norm(v))
            u = v / L
            n = np.array([-u[1], u[0], 0.0])
            for dl in (-LAT_CLEAR, 0.0, LAT_CLEAR):
                for dz in (-VERT_CLEAR, 0.0, VERT_CLEAR):
                    r = mujoco.mj_ray(m, d, a + n * dl + np.array([0, 0, dz]), u, None, 1, -1, gid)
                    assert r < 0 or r > L, (f"leg patrol_cp{i} -> next at z {a[2]:.1f} m (offset {dl}, {dz}) hits "
                                            f"{mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, int(gid[0]))} at {r:.2f} m")


def test_guard_walks_the_same_ring_on_clear_legs():
    rng = np.random.default_rng(1)
    g = fpb.FootPatrol(aps.SCENES["exterior"], 1, fpb.draw_guard_params(rng), 30.0, rng)
    m, _ = load()
    cps = checkpoints(m)
    assert [q.tolist() for _, q in g.ground] == [list(p[:2]) for p in cps]
    walk_len = 0.0
    for (i, j), vias in g.ground_vias.items():
        pts = [g.ground[i][1]] + list(vias)
        assert np.allclose(pts[-1], g.ground[j][1]), "every walking leg ends on its checkpoint"
        for p, q in zip(pts, pts[1:]):
            assert g._leg_clear(p, q), f"guard leg {i}->{j} blocked between {p} and {q}"
            walk_len += float(np.linalg.norm(np.asarray(q) - np.asarray(p)))
    n_detour = sum(1 for v in g.ground_vias.values() if len(v) > 1)
    print(f"\nguard walking ring: {walk_len:.1f} m, {n_detour} of {len(g.ground_vias)} legs shifted sideways "
          f"around trees")


def _seg_seg_dist(p1, p2, q1, q2):
    """Exact minimum distance between 2-D segments p1p2 and q1q2 (0 when they intersect)."""
    p1, p2, q1, q2 = (np.asarray(v, dtype=float)[:2] for v in (p1, p2, q1, q2))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2, d3, d4 = cross(q1, q2, p1), cross(q1, q2, p2), cross(p1, p2, q1), cross(p1, p2, q2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 * d2 < 0 and d3 * d4 < 0:
        return 0.0

    def pt_seg(p, a, b):
        ab = b - a
        L2 = float(ab @ ab)
        s = 0.0 if L2 == 0 else min(1.0, max(0.0, float((p - a) @ ab) / L2))
        return float(np.linalg.norm(p - (a + s * ab)))
    return min(pt_seg(p1, q1, q2), pt_seg(p2, q1, q2), pt_seg(q1, p1, p2), pt_seg(q2, p1, p2))


def test_seg_seg_dist_fixture():
    # FIXTURE geometry, not simulation output
    assert _seg_seg_dist((0, 0), (2, 0), (1, -1), (1, 1)) == 0.0                     # crossing
    assert abs(_seg_seg_dist((0, 0), (2, 0), (3, 1), (3, 5)) - math.hypot(1, 1)) < 1e-12   # end to end
    assert abs(_seg_seg_dist((0, 0), (4, 0), (1, 2), (3, 2)) - 2.0) < 1e-12           # parallel


def test_every_route_leg_strictly_inside_the_wall_with_true_segment_distance():
    """G-13: every leg of every UAV route (both policies, both UAVs, incl. the out-and-back arcs) and of the
    guard's walking ring lies inside the boundary polygon (both ends inside, no crossing of any wall edge), and
    its exact segment-to-wall-segment distance exceeds the wall half thickness + the 0.6 m FR-18 clearance."""
    m, d = load()
    poly = boundary_polygon(m, d)
    half_t = max(m.geom_size[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"boundary_wall_{i}")][1]
                 for i in range(len(poly)))
    edges = [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    legs = []
    for policy in ("sectors", "offset_ring"):
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], policy=policy, vision=False,
                                                frame_log=False)
        for name, u in ctl.uavs.items():
            r = [p for p, _ in u["route"]]
            legs += [(f"{policy}/{name}", r[i], r[(i + 1) % len(r)]) for i in range(len(r))]
    rng = np.random.default_rng(1)
    g = fpb.FootPatrol(aps.SCENES["exterior"], 1, fpb.draw_guard_params(rng), 30.0, rng)
    for (i, j), vias in g.ground_vias.items():
        pts = [g.ground[i][1]] + list(vias)
        legs += [("guard", p, q) for p, q in zip(pts, pts[1:])]
    worst = (float("inf"), None)
    for who, a, b in legs:
        assert inside(a, poly) and inside(b, poly), f"{who} leg {a[:2]} -> {b[:2]} has an end outside the wall"
        dmin = min(_seg_seg_dist(a, b, e0, e1) for e0, e1 in edges)
        assert dmin > half_t + LAT_CLEAR, f"{who} leg {a[:2]} -> {b[:2]} only {dmin:.2f} m from the wall line"
        worst = min(worst, (dmin, who))
    print(f"\n{len(legs)} legs inside the wall; smallest leg-to-wall-centre-line distance {worst[0]:.2f} m ({worst[1]})")


def _footprints(m, d, skip):
    """(name, 2-D convex footprint, top z) of every collidable geom except `skip` and planes. Meshes use their
    world-frame vertices; primitives the 8 corners of their local AABB (geom_aabb) rotated to the world."""
    out = []
    for g in range(m.ngeom):
        if g in skip or m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE:
            continue
        if m.geom_contype[g] == 0 and m.geom_conaffinity[g] == 0:
            continue
        R, c = d.geom_xmat[g].reshape(3, 3), d.geom_xpos[g]
        if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
            mid = m.geom_dataid[g]
            V = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]]
        else:
            a = m.geom_aabb[g]
            V = a[:3] + a[3:] * np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
        W = V @ R.T + c
        out.append((mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or f"geom{g}", _hull(W[:, :2]),
                    float(W[:, 2].max())))
    return out


def _hull(P):
    """Andrew monotone chain convex hull, counter-clockwise."""
    P = sorted(map(tuple, np.round(P, 9)))
    if len(P) < 3:
        return [np.array(p) for p in P]

    def half(pts):
        h = []
        for p in pts:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1])
                                   - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(P[::-1])
    return [np.array(p) for p in lo[:-1] + up[:-1]]


def _seg_poly_dist(a, b, poly):
    """Horizontal distance from segment ab to a convex polygon (0 when the segment touches or enters it)."""
    if len(poly) >= 3 and any(inside(p, [tuple(q) for q in poly]) for p in (a, b)):
        return 0.0
    if len(poly) == 1:
        return _seg_seg_dist(a, b, poly[0], poly[0])
    return min(_seg_seg_dist(a, b, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def test_seg_poly_dist_fixture():
    # FIXTURE geometry, not simulation output
    sq = _hull(np.array([[0, 0], [2, 0], [2, 2], [0, 2], [1, 1]]))
    assert len(sq) == 4
    assert _seg_poly_dist(np.array([-1, 1]), np.array([3, 1]), sq) == 0.0           # passes through
    assert abs(_seg_poly_dist(np.array([-1, 3.5]), np.array([3, 3.5]), sq) - 1.5) < 1e-12   # 1.5 m north
    assert _seg_poly_dist(np.array([0.5, 0.5]), np.array([0.6, 0.6]), sq) == 0.0      # inside


def test_every_route_leg_clears_every_roof_within_sidestep_reach():
    """Regression (main batch, exterior offset_ring seeds 7, 13, 19, 21, 22: Alpha touched bldg_791070237_0).
    Every leg of every exterior UAV route (both policies, both UAVs) must clear the top of every collidable geom
    whose footprint lies within the leg's lateral reach by at least the FR-18 vertical margin:
      reach   = D_STOP_H + SIDE_CLEAR_M  (airframe stop distance + the range the sidestep may close to a surface)
      margin  = H_BAND + D_STOP_V        (the roof edge stays below the band in which FR-18 treats a hit as a
                                          lateral wall, plus the vertical stop distance)
    All four constants are read from DualUAVSurveillanceController; footprints come from the compiled model."""
    m, d = load()
    C = aps.DualUAVSurveillanceController
    reach, margin = C.D_STOP_H + C.SIDE_CLEAR_M, C.H_BAND + C.D_STOP_V
    worst, n_legs = (float("inf"), None), 0
    for policy in ("sectors", "offset_ring"):
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], policy=policy, vision=False,
                                                frame_log=False)
        skip = set().union(*(u["geoms"] for u in ctl.uavs.values()))
        fps = _footprints(ctl.model, ctl.data, skip)
        for name, u in ctl.uavs.items():
            r = [p for p, _ in u["route"]]
            for i in range(len(r)):
                a, b = r[i], r[(i + 1) % len(r)]
                n_legs += 1
                z_leg = min(a[2], b[2])
                for gname, poly, top in fps:
                    if _seg_poly_dist(a[:2], b[:2], poly) > reach:
                        continue
                    clear = z_leg - top
                    assert clear >= margin, (f"{policy}/{name} leg {a[:2]} -> {b[:2]} at {z_leg:.1f} m clears {gname} "
                                             f"(top {top:.2f} m) by only {clear:.2f} m < {margin:.2f} m")
                    worst = min(worst, (clear, f"{policy}/{name} over {gname}"))
    print(f"\n{n_legs} exterior UAV legs; reach {reach:.2f} m, margin {margin:.2f} m; "
          f"smallest roof clearance {worst[0]:.2f} m ({worst[1]})")
