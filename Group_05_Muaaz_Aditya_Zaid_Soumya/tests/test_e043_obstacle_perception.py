"""
FR-18 obstacle perception evidence | owner E043 Muaaz

1. Inventory: every collidable non-UAV geom of the interior scene (models/nmims_main_interior.xml
   + the ground plane of the wrapper) belongs to exactly one named obstacle class below.
2. Coverage: for one instance of every class, a UAV is placed ~1-2 m from it (on a free side,
   not touching anything) and the range ring must return that class within RF_RANGE_M.
   The coverage table is printed (run with -s, or as a script); it must read 100 %.
3. Markers (restricted-zone decal, patrol marks, checkpoints) and the non-colliding intruder
   are not obstacles; glass railings are.
4. Reactive avoidance: a UAV commanded through a corridor wall (and through a door whose lintel
   sits at flight altitude) stops short of it, without contact and without hunting.
5. A short interior patrol (both policies) has 0 obstacle and 0 UAV-UAV contacts.

  python -m pytest -s tests/test_e043_obstacle_perception.py
  python tests/test_e043_obstacle_perception.py
"""
import math
import os
import re
import sys

import mujoco
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import aerial_patrol_swarm as aps   # noqa: E402

# class -> regex on the geom name, or on "body:<body name>" for unnamed geoms of a body
CLASSES = {
    "ground floor (plane)": r"^ground$",
    "outer shell walls": r"^ext_wall_(gf|up)_\d+$",
    "ground-floor corridor walls": r"^gf_[wens]_\d+$",
    "door lintels": r"_lintel_",
    "VIP Lounge / Board Room wall": r"^gf_vip_board_\d+$",
    "Board / Conference Room wall": r"^gf_board_conf_\d+$",
    "lift lobby + foyer walls": r"^gf_(lift_[we]|foyer)_\d+$",
    "floor slabs / ceilings": r"^slab_\d\d_[nsew]$",
    "gallery glass railings": r"^rail_\d\d_[nsew]$",
    "gallery railing caps": r"^rail_\d\d_[nsew]_cap$",
    "gallery corridor walls": r"^gal_wall_\d\d_[nsew]$",
    "skylight + beams": r"^skylight(_beam_\d)?$",
    "atrium trees": r"^body:atrium_tree_\d+$",
    "atrium planters + shrubs": r"^planter_(\d|shrub_.*)$",
    "VIP Lounge chairs": r"^furn_vip_chair_",
    "Board / Conference furniture": r"^furn_(board|conf)_",
    "cafeteria counter + benches": r"^furn_cafe_(counter|bench)",
    "atrium cafe tables + chairs": r"^furn_cafe_(table|chair)_",
    "grand piano": r"^furn_piano_",
    "foyer reception, planters, stair": r"^(furn_reception_desk|foyer_(planter|shrub)_.*|stair_step_\d\d)$",
    "auditorium escalators": r"^escalator_",
}
# not present in this model (no element of that kind is modelled): reported, not tested
ABSENT = ["structural columns (none modelled: slabs span to the shell and the atrium edge)"]


def label(m, g):
    n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g)
    return n if n else "body:" + (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[g]) or "world")


def classify(m, g):
    hits = [c for c, rx in CLASSES.items() if re.search(rx, label(m, g))]
    return hits


def controller(**kw):
    return aps.DualUAVSurveillanceController(model_path=aps.SCENES["interior"], vision=False, frame_log=False,
                                            wind_mps=0.0, gust_sigma=0.0, **kw)


def place(ctl, u, pos):
    q = u["qadr"]
    ctl.data.qpos[q:q + 3] = pos
    ctl.data.qpos[q + 3:q + 7] = (1, 0, 0, 0)
    ctl.data.qvel[u["vadr"]:u["vadr"] + 6] = 0.0
    mujoco.mj_forward(ctl.model, ctl.data)


def touching(ctl, u):
    return any(ctl.data.contact.geom1[c] in u["geoms"] or ctl.data.contact.geom2[c] in u["geoms"]
               for c in range(ctl.data.ncon))


def candidates(m, d, g):
    """Free-side stand-off points around geom g (axis directions of its bounding box)."""
    if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE:
        return [np.array([0.0, -27.4, 1.0])]
    c_loc, half = m.geom_aabb[g][:3], m.geom_aabb[g][3:]
    R = d.geom_xmat[g].reshape(3, 3)
    centre = d.geom_xpos[g] + R @ c_loc
    out = []
    for so in (1.0, 1.6):
        for k in range(3):
            for s in (1.0, -1.0):
                out.append(centre + s * R[:, k] * (half[k] + so))
    return out


def coverage(verbose=True):
    ctl = controller()
    m, d = ctl.model, ctl.data
    A = ctl.uavs["alpha"]
    inv = {}
    for g in range(m.ngeom):
        if ctl.is_obstacle[g]:
            inv.setdefault(tuple(classify(m, g)), []).append(g)
    rows = []
    for cls in CLASSES:
        members = inv.get((cls,), [])
        ok, how = False, "no instance"
        for g in members[:: max(1, len(members) // 6)]:  # up to ~6 instances, first that has a free side
            for p in candidates(m, d, g):
                place(ctl, A, p)
                if touching(ctl, A):
                    continue
                A["phase"] = "patrol"
                ctl._sense(A)
                hit = [(r, int(gg)) for r, gg in zip(A["rf_true"], A["rf_geom"])
                       if gg >= 0 and classify(m, gg) == [cls] and r <= ctl.RF_RANGE_M]
                if hit:
                    r, gg = min(hit)
                    ok, how = True, f"{label(m, gg)} at {r:.2f} m from ({p[0]:.1f}, {p[1]:.1f}, {p[2]:.1f})"
                    break
            if ok:
                break
        rows.append((cls, len(members), ok, how))
    unclassified = [label(m, g) for k, gs in inv.items() if len(k) != 1 for g in gs]
    pct = 100.0 * sum(r[2] for r in rows) / len(rows)
    if verbose:
        print(f"\nFR-18 obstacle-class coverage, interior scene (range {ctl.RF_RANGE_M} m, sigma {ctl.RF_SIGMA_M} m, "
              f"min clearance H {ctl.D_STOP_H} m / V {ctl.D_STOP_V} m)")
        print(f"{'class':36s} {'geoms':>5s}  detected  evidence")
        for cls, n, ok, how in rows:
            print(f"{cls:36s} {n:5d}  {'yes' if ok else 'NO ':8s}  {how}")
        for a in ABSENT:
            print(f"{'(absent) ' + a}")
        print(f"coverage {pct:.0f} % of {len(rows)} classes; unclassified collidable geoms: {len(unclassified)}")
    return rows, unclassified, pct


def test_inventory_complete_and_every_class_detected():
    rows, unclassified, pct = coverage()
    assert not unclassified, f"collidable geoms outside every / in several classes: {unclassified[:10]}"
    assert all(n > 0 for _, n, _, _ in rows), "a class has no geom in the model"
    assert pct == 100.0, [r for r in rows if not r[2]]


def test_markers_and_intruder_are_not_obstacles_glass_is():
    ctl = controller()
    m = ctl.model
    for name in ("substation_zone", "intruder_geom", "gf_floor", "atrium_stone"):
        assert not ctl.is_obstacle[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, name)], name
    assert ctl.is_obstacle[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "rail_03_e")]
    ext = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], vision=False, frame_log=False)
    assert not ext.is_obstacle[mujoco.mj_name2id(ext.model, mujoco.mjtObj.mjOBJ_GEOM, "patrol_mark0")]
    assert not ext.is_obstacle[mujoco.mj_name2id(ext.model, mujoco.mjtObj.mjOBJ_GEOM, "substation_zone")]


def test_down_beam_sees_floor_through_floor_finish_and_restricted_decal():
    ctl = controller()
    A = ctl.uavs["alpha"]
    place(ctl, A, (-17.0, 6.0, 2.0))                     # above the VIP Lounge carpet + restricted decal
    ctl._sense(A)
    assert label(ctl.model, int(A["rf_geom"][-1])) == "ground"
    assert abs(A["rf_true"][-1] - 2.0) < 0.01


def approach(y, seconds=12.0):
    """Command Alpha from the west corridor (x = -12.3) to a point behind the wall (x = -20)."""
    ctl = controller()
    A, B = ctl.uavs["alpha"], ctl.uavs["bravo"]
    place(ctl, A, (-12.3, y, 2.4))
    A.update(phase="patrol", fsm="PATROL", route=[(np.array([-20.0, y, 2.4]), None)] * 2, idx=0,
             home=np.array([-12.3, y]))
    h = ctl.model.opt.timestep
    xs, engaged = [], False
    for k in range(int(seconds / h)):
        if k % ctl.SENSE_EVERY == 0:
            ctl._sense(A)
        pb = ctl.data.qpos[B["qadr"]:B["qadr"] + 3].copy()
        ctl._control(A, pb, h)
        mujoco.mj_step(ctl.model, ctl.data)
        engaged |= A["avoid"]
        xs.append(float(ctl.data.qpos[A["qadr"]]))
        assert not touching(ctl, A), f"contact at t = {k * h:.2f} s (y = {y})"
    return np.array(xs) - (-13.8 + 0.11), engaged, h      # centre-to-wall-face gap


def test_reactive_layer_stops_short_of_wall_and_door_lintel():
    # y = -12: plain wall; y = -10: a door whose lintel bottom (2.4 m) is exactly at flight altitude
    for y in (-12.0, -10.0):
        gap, engaged, h = approach(y)
        assert engaged, "the reactive layer never engaged"
        assert gap.min() > 0.38, f"airframe reached the wall (y = {y}): centre {gap.min():.2f} m from the face"
        tail = gap[-int(2.0 / h):]
        assert tail.max() - tail.min() < 0.05, f"still hunting in front of the wall (y = {y}): {tail.min():.2f}-{tail.max():.2f} m"


def short_patrol(policy, duration=120.0):
    ctl = controller(policy=policy, seed=3)
    while ctl.current_time_s < duration:
        ctl.step_simulation(dt=1.0 / 30.0)
    return ctl


def test_short_interior_patrol_has_no_contacts():
    for policy in ("sectors", "offset_ring"):
        ctl = short_patrol(policy)
        obst = sum(u["obstacle_contacts"] for u in ctl.uavs.values())
        assert obst == 0 and ctl.uav_uav_contacts == 0, (policy, obst, ctl.uav_uav_contacts)
        assert ctl.min_obstacle_clearance_m >= ctl.D_STOP_V, (policy, ctl.min_obstacle_clearance_m)
        print(f"\n{policy}: 120 s interior, obstacle contacts {obst}, UAV-UAV contacts {ctl.uav_uav_contacts}, "
              f"min ray clearance {ctl.min_obstacle_clearance_m:.2f} m")


def track_diversion(tree, bearing_deg, offset, alt, seconds=7.0):
    """G-06: force a TRACK diversion past an atrium tree. Alpha (forward camera, faces the target) starts 6 m
    before the tree on bearing `bearing_deg`, `offset` m to the side of the trunk axis, and is steered by the
    real TRACK code (_steer_tracker) at a fix 8 m beyond the tree. Returns the body name of the first contact
    (None = no contact). The double-tree pairs (2.4 m apart) are crossed on bearings 0 and 180."""
    ctl = controller(policy="sectors", seed=1)
    m = ctl.model
    c = ctl.data.xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, tree)][:2].copy()
    th = math.radians(bearing_deg)
    dv, nv = np.array([math.cos(th), math.sin(th)]), np.array([-math.sin(th), math.cos(th)])
    start, fix = c - dv * 6.0 + nv * offset, c + dv * 8.0 + nv * offset
    U, O = ctl.uavs["alpha"], ctl.uavs["bravo"]
    place(ctl, O, (0.0, -40.0, 1.0))
    place(ctl, U, (start[0], start[1], alt))
    p0 = np.array([start[0], start[1], alt])
    U.update(phase="patrol", route=[(p0.copy(), None)] * 2, idx=0, home=start.copy(), crumbs=[p0.copy()])
    ctl._inc = {"id": 1, "last_fix": np.array([fix[0], fix[1], 0.85])}
    ctl._set_role(U, "TRACK")
    h = m.opt.timestep
    po = ctl.data.qpos[O["qadr"]:O["qadr"] + 3].copy()
    for k in range(int(seconds / h)):
        if k % ctl.SENSE_EVERY == 0:
            ctl._sense(U)
            ctl._steer_tracker(U)
        ctl._control(U, po, h)
        mujoco.mj_step(m, ctl.data)
        for i in range(ctl.data.ncon):
            g1, g2 = int(ctl.data.contact.geom1[i]), int(ctl.data.contact.geom2[i])
            if g1 in U["geoms"] or g2 in U["geoms"]:
                return mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(m.geom_bodyid[g2 if g1 in U["geoms"] else g1]))
    return None


def test_track_diversions_past_every_atrium_tree_have_no_contacts():
    m = mujoco.MjModel.from_xml_path(aps.SCENES["interior"])
    trees = sorted(n for n in (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) for b in range(m.nbody))
                   if n and n.startswith("atrium_tree_"))
    assert len(trees) == 6, trees
    cases = [(t, b, off, 2.4) for t in trees for b in (0, 90, 180, 270) for off in (-0.2, 0.2)]   # trunk height
    cases += [(t, 45, 0.0, 5.0) for t in trees]                                                 # canopy height
    fails = [(c, hit) for c in cases for hit in [track_diversion(*c)] if hit]
    assert not fails, f"{len(fails)} of {len(cases)} TRACK diversions touched: {fails}"


if __name__ == "__main__":
    coverage()
    for pol in ("sectors", "offset_ring"):
        c = short_patrol(pol)
        print(f"{pol}: obstacle contacts {sum(u['obstacle_contacts'] for u in c.uavs.values())}, "
              f"UAV-UAV {c.uav_uav_contacts}, min clearance {c.min_obstacle_clearance_m:.2f} m")
