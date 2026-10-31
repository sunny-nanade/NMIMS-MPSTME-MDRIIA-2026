"""
Separation evidence for the viva | owner E043 Muaaz
Head-on encounter at the guide's 6 m/s cruise, same altitude (layering disabled), no wind.
Runs INSIDE the campus boundary on the exterior scene: the 60 m centre span of the patrol ring's
east leg (patrol_cp5 -> patrol_cp6, 63 m, between the main building and the east wall) at the
20 m patrol altitude. test_encounter_segment_is_clear checks that span with mj_ray.

  python -m pytest tests/test_e043_separation.py      # as a test
  python tests/test_e043_separation.py                # prints the APF-only vs layered comparison
"""
import os, sys
import numpy as np
import mujoco

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import aerial_patrol_swarm as aps

SPAN_TIP_TO_TIP = 0.76   # m, 2 x (arm 0.26 + prop radius 0.12)
SPAN_M, ALT_M = 60.0, 20.0


def encounter_segment(model):
    """(start, end, unit) of the 60 m centre span of the ring's east leg, at patrol altitude."""
    a, b = (model.site_pos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, n)].copy()
            for n in ("patrol_cp5", "patrol_cp6"))
    a[2] = b[2] = ALT_M
    u = (b - a) / np.linalg.norm(b - a)
    mid = (a + b) / 2.0
    return mid - u * SPAN_M / 2.0, mid + u * SPAN_M / 2.0, u


def head_on(governor=True, sensing=True):
    """Fly Alpha and Bravo straight at each other; return (min centre distance, both passed, controller)."""
    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], policy="sectors",
                                            wind_mps=0.0, gust_sigma=0.0, vision=False,
                                            layered_separation=governor)   # False: the guide's APF alone
    A, B = ctl.uavs["alpha"], ctl.uavs["bravo"]
    p0, p1, axis = encounter_segment(ctl.model)
    for u, (s, e) in ((A, (p0, p1)), (B, (p1, p0))):
        ctl.data.qpos[u["qadr"]:u["qadr"] + 3] = s                     # inside the campus, east of the building
        ctl.data.qpos[u["qadr"] + 3:u["qadr"] + 7] = (1, 0, 0, 0)
        u.update(phase="patrol", route=[(e.copy(), None)] * 2, idx=0, layer=0.0, home=s[:2].copy())
    mujoco.mj_forward(ctl.model, ctl.data)
    h, dmin = ctl.model.opt.timestep, 1e9
    for k in range(int(16 / h)):
        pa = ctl.data.qpos[A["qadr"]:A["qadr"] + 3].copy()
        pb = ctl.data.qpos[B["qadr"]:B["qadr"] + 3].copy()
        if sensing and hasattr(ctl, "_sense") and k % ctl.SENSE_EVERY == 0:
            ctl._sense(A); ctl._sense(B)
        ctl._control(A, pb, h); ctl._control(B, pa, h)
        mujoco.mj_step(ctl.model, ctl.data)
        ctl._log_contacts(A, B)
        dmin = min(dmin, float(np.linalg.norm(pa - pb)))
    mid = (p0 + p1) / 2.0
    passed = (bool((ctl.data.qpos[A["qadr"]:A["qadr"] + 3] - mid) @ axis > 20.0)
              and bool((ctl.data.qpos[B["qadr"]:B["qadr"] + 3] - mid) @ axis < -20.0))
    return dmin, passed, ctl


def corridor_head_on(seconds=25.0):
    """INTERIOR, offset_ring geometry that gave 0.96 m before the kinematic governor (seed 18, t = 129 s): a
    tracker returning south along the west corridor (wall 1.3 m to its right) meets the other UAV patrolling
    north, both at the 2.4 m patrol altitude under the 3.3 m ceiling. Returns (d_min, passed, controller)."""
    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["interior"], policy="offset_ring",
                                            wind_mps=0.0, gust_sigma=0.0, vision=False)
    A, B = ctl.uavs["alpha"], ctl.uavs["bravo"]
    starts = {"alpha": np.array([-12.2, -12.0, 2.4]), "bravo": np.array([-13.0, 2.0, 2.4])}
    goals = {"alpha": np.array([-12.3, 12.0, 2.4]), "bravo": np.array([-12.3, -24.0, 2.4])}
    for u in (A, B):
        ctl.data.qpos[u["qadr"]:u["qadr"] + 3] = starts[u["name"]]
        ctl.data.qpos[u["qadr"] + 3:u["qadr"] + 7] = (1, 0, 0, 0)
        u.update(phase="patrol", route=[(goals[u["name"]].copy(), None)] * 2, idx=0, layer=0.0,
                 home=starts[u["name"]][:2].copy())
    mujoco.mj_forward(ctl.model, ctl.data)
    h, dmin = ctl.model.opt.timestep, 1e9
    for k in range(int(seconds / h)):
        pa = ctl.data.qpos[A["qadr"]:A["qadr"] + 3].copy()
        pb = ctl.data.qpos[B["qadr"]:B["qadr"] + 3].copy()
        if k % ctl.SENSE_EVERY == 0:
            ctl._sense(A); ctl._sense(B)
        ctl._control(A, pb, h); ctl._control(B, pa, h)
        mujoco.mj_step(ctl.model, ctl.data)
        ctl._log_contacts(A, B)
        dmin = min(dmin, float(np.linalg.norm(pa - pb)))
    passed = (ctl.data.qpos[A["qadr"] + 1] > 6.0) and (ctl.data.qpos[B["qadr"] + 1] < -18.0)
    return dmin, bool(passed), ctl


def test_interior_corridor_head_on_holds_separation_and_passes():
    d, passed, ctl = corridor_head_on()
    assert d >= 2.5, f"corridor head-on: d_min {d:.2f} m below 2.5 m"
    assert passed, "corridor head-on: pair failed to pass (deadlock)"
    assert ctl.uav_uav_contacts == 0 and sum(u["obstacle_contacts"] for u in ctl.uavs.values()) == 0


def test_encounter_segment_is_clear():
    """The 60 m span, widened by the FR-18 clearances (0.6 m lateral, 0.35 m vertical) and by the
    sidestep room (+-3 m lateral), meets no geom: a straight clear segment inside the compound."""
    m = mujoco.MjModel.from_xml_path(aps.SCENES["exterior"])
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    p0, p1, u = encounter_segment(m)
    n = np.array([-u[1], u[0], 0.0])
    gid = np.zeros(1, dtype=np.int32)
    for dl in (-3.0, -0.6, 0.0, 0.6, 3.0):
        for dz in (-0.35, 0.0, 0.35):
            r = mujoco.mj_ray(m, d, p0 + n * dl + np.array([0, 0, dz]), u, None, 1, -1, gid)
            assert r < 0 or r > SPAN_M, (dl, dz, r, mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, int(gid[0])))


def test_timestep_is_mandated_value():
    for scene in aps.SCENES.values():
        assert mujoco.MjModel.from_xml_path(scene).opt.timestep == 0.002


def test_apf_alone_does_not_hold_separation():
    d0, _, _ = head_on(governor=False)
    assert d0 < 2.5, "the guide's APF alone was expected to violate d >= 2.5 m (documented failure)"


def test_layered_separation_holds_and_pair_passes():
    d1, p1, ctl = head_on(governor=True)
    assert d1 >= 2.5, f"separation layer regression: d_min {d1:.2f} m below 2.5 m"
    assert p1, "pair failed to pass each other (deadlock)"
    assert ctl.uav_uav_contacts == 0
    assert sum(u["obstacle_contacts"] for u in ctl.uavs.values()) == 0, "encounter touched the building or a tree"


def test_altitude_layer_is_per_uav_in_every_policy():
    """Regression (main batch, exterior_uav_offset_ring_s4 = 2.35 m): routes shared waypoint arrays, so Bravo's
    alt_layer_bravo was added to Alpha's points too (offset_ring: both at 24 m) or twice (out-and-back points).
    Each UAV's every waypoint must sit at the scene ring altitude + its own layer, exactly once."""
    for policy in ("offset_ring", "sectors"):
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], policy=policy,
                                                wind_mps=0.0, gust_sigma=0.0, vision=False)
        layer_b = ctl._num("alt_layer_bravo", 0.0)
        assert layer_b > 0.0
        base = {n: p[2] for n, p in ctl.ring}
        for name, layer in (("alpha", 0.0), ("bravo", layer_b)):
            for p, n in ctl.uavs[name]["route"]:
                assert abs(p[2] - (base[n] + layer)) < 1e-9, (policy, name, n, p[2])
        ids_a = {id(p) for p, _ in ctl.uavs["alpha"]["route"]}
        assert not ids_a & {id(p) for p, _ in ctl.uavs["bravo"]["route"]}, "routes share waypoint arrays"
        assert {id(p) for p, _ in ctl.ring}.isdisjoint(ids_a), "a route aliases the scene ring"


if __name__ == "__main__":
    d0, p0, _ = head_on(governor=False)
    d1, p1, _ = head_on(governor=True)
    print(f"APF only (guide parameters): min centre distance {d0:5.2f} m  -> "
          f"{'CONTACT' if d0 < SPAN_TIP_TO_TIP else 'clear'}")
    print(f"APF + governor + sidestep  : min centre distance {d1:5.2f} m  -> "
          f"{'CONTACT' if d1 < SPAN_TIP_TO_TIP else 'clear'}; pair passed each other: {p1}")
    assert d1 >= 2.5 and p1, "separation layer regression: d_min below 2.5 m or pair failed to pass"
