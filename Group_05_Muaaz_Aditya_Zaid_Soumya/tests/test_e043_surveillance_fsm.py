"""
Surveillance FSM (contract E) checks | owner E043 Muaaz
  * transitions PATROL -> DETECT -> VERIFY -> ALERT_<tier> -> TRACK -> RETURN_TO_PATROL -> PATROL
    driven by injected ground fixes (the teammate functions are replaced by labelled stubs, so the
    test runs on the E043 branch alone and on the integrated tree)
  * an inconsistent fix in VERIFY rejects the detection; a closed incident is not reopened
  * FR-18 obstacle avoidance and the separation layer run in TRACK and RETURN_TO_PATROL
  * with E051's stub detector (E043 branch alone) the FSM stays in PATROL and nothing is reported
Every number here is a test fixture, never a result.

  python -m pytest tests/test_e043_surveillance_fsm.py
"""
import os
import sys

import mujoco
import numpy as np
import pytest

GROUP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GROUP, "src"))
import aerial_patrol_swarm as aps          # noqa: E402

def east_leg(model):
    """Ends of the exterior ring's east leg (patrol_cp5 -> patrol_cp6), inside the campus wall, at 20 m."""
    a, b = (model.site_pos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, n)].copy()
            for n in ("patrol_cp5", "patrol_cp6"))
    a[2] = b[2] = 20.0
    return a, b


_M = mujoco.MjModel.from_xml_path(aps.SCENES["exterior"])
_A, _B = east_leg(_M)
_U = (_B - _A) / np.linalg.norm(_B - _A)
P = np.array([*(_A + 10.0 * _U)[:2], 0.85])   # fixture ground fix 10 m along the leg from Alpha


def make_ctl(tier=2, tracker="alpha"):
    """Exterior controller with both UAVs already on patrol at the two ends of the east leg (fixture)."""
    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], seed=3, wind_mps=0.0,
                                            gust_sigma=0.0, vision=True, frame_log=False)
    for u, p in ((ctl.uavs["alpha"], _A), (ctl.uavs["bravo"], _B)):
        ctl.data.qpos[u["qadr"]:u["qadr"] + 3] = p
        ctl.data.qpos[u["qadr"] + 3:u["qadr"] + 7] = (1, 0, 0, 0)
        u.update(phase="patrol", fsm="PATROL", route=[(p.copy(), None)] * 2, idx=0, home=p[:2].copy())
    mujoco.mj_forward(ctl.model, ctl.data)
    # labelled stubs for the teammate functions (contract C / D signatures)
    ctl.evaluate_geofence_status = lambda p: ("STATUS_0_ROUTINE_CLEAR", 0) if p is None else (f"STATUS_{tier}", tier)
    ctl.select_tracking_uav = lambda xy, states: tracker if tracker in states else sorted(states)[0]
    return ctl


def drive(ctl, ticks, fixes_fn, t0=0.0):
    """Call the FSM once per vision tick; returns the (alpha, bravo) fsm labels after each tick."""
    out = []
    for k in range(ticks):
        t = t0 + k / ctl.vision_hz
        ctl._fsm_step(t, fixes_fn(k, t))
        out.append((ctl.uavs["alpha"]["fsm"], ctl.uavs["bravo"]["fsm"]))
    return out


def test_full_cycle_and_incident_record():
    ctl = make_ctl(tier=2)
    labels = drive(ctl, 4, lambda k, t: {"alpha": P + np.array([*(0.1 * k * _U[:2]), 0.0])})
    assert [a for a, _ in labels] == ["DETECT", "VERIFY", "ALERT_2", "TRACK"]
    assert all(b == "PATROL" for _, b in labels)                 # the other UAV keeps patrolling
    a = ctl.uavs["alpha"]
    assert a["override"] is not None and abs(a["override"][2] - 20.0) < 1e-6   # tracks at its patrol altitude
    assert np.linalg.norm(a["override"][:2] - P[:2]) < 1.0       # nadir camera: straight above the fix
    inc = ctl.incidents[0]
    assert inc["t_detect"] == 0.0 and inc["t_verify"] == pytest.approx(0.2) and inc["tier_alert"] == 2
    # no further fixes: lost after TRACK_LOST_S, then RETURN_TO_PATROL and back to PATROL
    n = int(ctl.TRACK_LOST_S * ctl.vision_hz) + 5
    labels = drive(ctl, n, lambda k, t: {}, t0=0.4)
    seq = [a for a, _ in labels]
    assert "RETURN_TO_PATROL" in seq or seq[-1] == "PATROL"
    assert seq[-1] == "PATROL" and a["override"] is None and a["role"] is None
    assert inc["close_reason"] == "lost" and ctl.surv_state == "PATROL"


def test_verify_reject_and_closed_incident_not_reopened():
    ctl = make_ctl()
    labels = drive(ctl, 2, lambda k, t: {"alpha": P} if k == 0 else {"alpha": P + np.array([*(20.0 * _U[:2]), 0.0])})
    assert [a for a, _ in labels] == ["DETECT", "PATROL"]
    assert ctl.incidents[0]["close_reason"] == "verify_reject"
    # a full incident at P, closed by the time bound
    ctl2 = make_ctl()
    drive(ctl2, 4, lambda k, t: {"alpha": P})
    ctl2._inc["t_track"] = -100.0
    drive(ctl2, 1, lambda k, t: {"alpha": P}, t0=0.4)
    assert ctl2.incidents[0]["close_reason"] == "track_timeout"
    drive(ctl2, 3, lambda k, t: {"bravo": P + np.array([*(3.0 * _U[:2]), 0.0])}, t0=0.5)   # same place: handed over
    assert len(ctl2.incidents) == 1


def test_handoff_moves_tracking_to_the_other_uav():
    ctl = make_ctl(tracker="alpha")
    drive(ctl, 4, lambda k, t: {"alpha": P})
    ctl.select_tracking_uav = lambda xy, states: "bravo"
    labels = drive(ctl, 1, lambda k, t: {"bravo": P}, t0=0.4)
    assert labels[-1] == ("RETURN_TO_PATROL", "TRACK") and ctl.incidents[0]["handoffs"] == 1


def test_fr18_avoidance_and_separation_stay_active_while_tracking():
    ctl = make_ctl()
    drive(ctl, 4, lambda k, t: {"alpha": P})
    ctl.vision_enabled = False              # freeze the FSM in TRACK for this check
    calls = {"alpha": 0, "bravo": 0}
    real = ctl._avoid_obstacles

    def spy(u, v_cmd):
        calls[u["name"]] += 1
        return real(u, v_cmd)
    ctl._avoid_obstacles = spy
    for _ in range(15):
        ctl.step_simulation(dt=1.0 / 30.0)
    assert ctl.uavs["alpha"]["fsm"] == "TRACK"
    steps = 15 * max(1, int(round((1.0 / 30.0) / ctl.model.opt.timestep)))
    assert calls["alpha"] == steps and calls["bravo"] == steps
    assert ctl.uavs["alpha"]["obstacle_contacts"] == 0 and ctl.uav_uav_contacts == 0


def test_stub_detector_keeps_patrol_and_reports_nothing():
    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], seed=2, vision=True, frame_log=False,
                                            intruder_appear_s=0.5)
    try:
        ctl.detect_intruder_hsv(np.zeros((480, 640, 3), dtype=np.uint8))
    except NotImplementedError:
        pass
    else:
        pytest.skip("E051 detector present in this tree (integrated build)")
    while ctl.current_time_s < 3.0 - 1e-9:
        ctl.step_simulation(dt=1.0 / 30.0)
    assert ctl.vision_status == "not_implemented"
    assert ctl.surv_state == "PATROL" and ctl.incidents == []
    sm = ctl.surveillance_metrics()
    assert sm["detected"] is None and sm["detection_latency_s"] is None and sm["verify_time_s"] is None


def _real_ctl(cls=aps.DualUAVSurveillanceController):
    """As make_ctl, but with the REAL teammate functions (no stubs, no monkeypatching)."""
    ctl = cls(model_path=aps.SCENES["exterior"], seed=3, wind_mps=0.0, gust_sigma=0.0, vision=True, frame_log=False)
    for u, p in ((ctl.uavs["alpha"], _A), (ctl.uavs["bravo"], _B)):
        ctl.data.qpos[u["qadr"]:u["qadr"] + 3] = p
        ctl.data.qpos[u["qadr"] + 3:u["qadr"] + 7] = (1, 0, 0, 0)
        u.update(phase="patrol", fsm="PATROL", route=[(p.copy(), None)] * 2, idx=0, home=p[:2].copy())
    mujoco.mj_forward(ctl.model, ctl.data)
    return ctl


def test_g03_select_tracking_uav_drives_alert_to_track_without_monkeypatching():
    ctl = _real_ctl()
    assert "select_tracking_uav" not in vars(ctl) and "evaluate_geofence_status" not in vars(ctl)
    calls = []
    real = type(ctl).select_tracking_uav

    def spy(self, xy, states):
        calls.append(sorted(states))
        return real(self, xy, states)
    cls = type("Spy", (type(ctl),), {"select_tracking_uav": spy})
    ctl.__class__ = cls                                   # observe the real method; it still decides
    labels = drive(ctl, 4, lambda k, t: {"alpha": P + np.array([*(0.1 * k * _U[:2]), 0.0])})
    a_states = [a for a, _ in labels]
    assert a_states[:2] == ["DETECT", "VERIFY"] and a_states[2].startswith("ALERT_")
    assert calls and calls[0] == ["alpha", "bravo"], "ALERT -> TRACK must go through select_tracking_uav"
    inc = ctl.incidents[0]
    assert ctl.surv_state == "TRACK" and inc["tracker"] in ("alpha", "bravo")
    assert ctl.uavs[inc["tracker"]]["fsm"] == "TRACK"
    exp = real(ctl, inc["last_fix"][:2], {n: ctl._camera_state(n) for n in ("alpha", "bravo")})
    assert inc["tracker"] == exp


def test_g03_hasattr_fallback_picks_the_nearest_uav():
    class NoSelector(aps.DualUAVSurveillanceController):
        @property
        def select_tracking_uav(self):                   # behaves as if E051's method were absent
            raise AttributeError("select_tracking_uav")
    ctl = _real_ctl(NoSelector)
    assert not hasattr(ctl, "select_tracking_uav")
    near_b = P + np.array([*((np.linalg.norm(_B[:2] - P[:2]) - 2.0) * (_B[:2] - P[:2]) /
                             np.linalg.norm(_B[:2] - P[:2])), 0.0])
    pool = {n: ctl._camera_state(n) for n in ("alpha", "bravo")}
    assert ctl._pick_tracker(near_b[:2], pool) == "bravo"
    assert ctl._pick_tracker(_A[:2], pool) == "alpha"
    labels = drive(ctl, 4, lambda k, t: {"alpha": _A.copy()})
    assert labels[-1][0] == "TRACK" and ctl.incidents[0]["tracker"] == "alpha"


def test_stationary_tier0_target_is_handed_over_and_not_reopened():
    """A verified target that does not move (a parked red cab) with geofence tier 0 is handed over after
    STATIC_S instead of holding the tracker for TRACK_MAX_S; the same place is not re-opened."""
    ctl = make_ctl(tier=0)
    n = 4 + int(ctl.STATIC_S * ctl.vision_hz) + 3
    jitter = lambda k: np.array([0.3 * np.sin(k), 0.3 * np.cos(k), 0.0])        # fixture fix jitter < STATIC_M
    drive(ctl, n, lambda k, t: {"alpha": P + jitter(k)})
    inc = ctl.incidents[0]
    assert inc["close_reason"] == "static_handover"
    assert inc["t_close"] - inc["t_track"] == pytest.approx(ctl.STATIC_S, abs=0.25)
    assert ctl.uavs["alpha"]["fsm"] in ("RETURN_TO_PATROL", "PATROL")
    drive(ctl, 5, lambda k, t: {"alpha": P}, t0=n / ctl.vision_hz)
    assert len(ctl.incidents) == 1                                               # closed place: not re-opened
    ctl.vision_status = "active"
    import json
    json.dumps(ctl.surveillance_metrics()["incidents"])                          # FSM working state stays private


def test_moving_or_geofenced_target_is_not_handed_over():
    walk = 1.35 / 10.0                                                            # fixture: walking pace per tick
    ctl = make_ctl(tier=0)
    drive(ctl, 4 + 80, lambda k, t: {"alpha": P + np.array([*(walk * k * _U[:2]), 0.0])})
    assert ctl.incidents[0]["close_reason"] is None and ctl.uavs["alpha"]["fsm"] == "TRACK"
    ctl = make_ctl(tier=2)                                                        # stationary but in a geofence tier
    drive(ctl, 4 + 80, lambda k, t: {"alpha": P})
    assert ctl.incidents[0]["close_reason"] is None and ctl.uavs["alpha"]["fsm"] == "TRACK"
    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], vision=False, static_handover=False)
    assert ctl.static_handover is False
