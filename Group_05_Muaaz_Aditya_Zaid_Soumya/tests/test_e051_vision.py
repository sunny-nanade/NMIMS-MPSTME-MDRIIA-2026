"""
E051 vision tests | owner E051 Aditya Rajkumar

Rendered-frame tests use the real MuJoCo scenes (mujoco.Renderer, segmentation ground truth).
Tests that build a numpy image by hand are labelled FIXTURE: they check the geometry code and are never reported
as results. Run:  python -m pytest tests/test_e051_vision.py -q
"""
import ast
import inspect
import math
import os
import sys

import mujoco
import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "analytics"))
import aerial_patrol_swarm as aps  # noqa: E402

C = aps.DualUAVSurveillanceController


def bare():
    """Controller object with NO model or data: anything that needs simulator state raises AttributeError."""
    return object.__new__(C)


@pytest.fixture(scope="module")
def benches():
    try:
        import vision_illumination_benchmark as vib
        out = {s: vib.SceneBench(s) for s in ("interior", "exterior")}
    except Exception as exc:                      # no OpenGL context available
        pytest.skip(f"offscreen rendering unavailable: {exc}")
    yield vib, out
    for sb in out.values():
        sb.close()


# ---------------------------------------------------------------- detector on hand-made images (FIXTURE)
def test_fixture_bbox_exact_on_known_rectangle():
    """FIXTURE: a pure intruder-red rectangle on a grey frame must give exactly that bounding box."""
    img = np.full((480, 640, 3), 120, np.uint8)
    img[100:260, 300:360] = (230, 26, 26)                         # rows 100..259, cols 300..359
    r = bare().detect_intruder_hsv(img)
    assert r["detected"] and r["bbox"] == (300, 100, 360, 260)
    assert r["centroid"] == pytest.approx((329.5, 179.5), abs=0.01)
    assert r["latency_ms"] > 0.0


def test_fixture_no_red_means_no_detection():
    img = np.full((480, 640, 3), 120, np.uint8)
    img[:, :, 2] = 160                                            # blue-grey frame
    r = bare().detect_intruder_hsv(img)
    assert r["detected"] is False and r["bbox"] is None and r["centroid"] is None


def test_fixture_speckle_is_removed_and_largest_blob_wins():
    """FIXTURE: a 2x2 red speck (opened away) plus two blobs: the larger blob must be returned."""
    img = np.full((480, 640, 3), 120, np.uint8)
    img[10:12, 10:12] = (230, 26, 26)
    img[200:230, 100:120] = (230, 26, 26)                         # 600 px
    img[300:400, 400:450] = (230, 26, 26)                         # 5000 px
    r = bare().detect_intruder_hsv(img)
    assert r["bbox"] == (400, 300, 450, 400)


def test_detector_reads_no_simulator_state():
    """The detector runs on an object with no model/data and touches only image-derived names and constants."""
    tree = ast.parse(inspect.getsource(C.detect_intruder_hsv).replace("\n    ", "\n").lstrip())
    used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name) and n.value.id == "self"}
    assert used <= {"MIN_BLOB_AREA_PX", "_hsv_bands", "AE_TARGET_V", "AE_PCTL", "AE_GAIN_MAX"}, used   # constants only
    img = np.zeros((480, 640, 3), np.uint8)
    assert bare().detect_intruder_hsv(img)["detected"] is False   # would raise AttributeError on any self.data use


def test_fixture_low_light_gain_recovers_a_dim_target_and_leaves_normal_light_alone():
    """FIXTURE: a red patch at 15 % brightness (V below HSV_VAL_MIN) on a dim grey floor. The low-light value gain
    (auto_exposure, production) finds it; the raw-frame arm does not. A normally lit frame gets gain 1."""
    dim = np.full((480, 640, 3), 18, np.uint8)
    dim[300:360, 400:440] = (35, 4, 4)                            # 0.15 x (230, 26, 26)
    on, off = bare(), bare()
    off.auto_exposure = False
    r_on, r_off = on.detect_intruder_hsv(dim), off.detect_intruder_hsv(dim)
    assert r_on["detected"] and r_on["bbox"] == (400, 300, 440, 360) and r_on["exposure_gain"] > 1.0
    assert not r_off["detected"] and r_off["exposure_gain"] == 1.0
    lit = np.full((480, 640, 3), 120, np.uint8)
    lit[300:400, 400:450] = (230, 26, 26)
    assert on.detect_intruder_hsv(lit)["exposure_gain"] == 1.0


def test_hsv_bands_come_from_the_intruder_colour():
    """Bands are derived from the material rgba (0.90, 0.10, 0.10): hue 0 wraps, S_nominal 226 (from RGB 230,26,26) -> S_min 169."""
    b = C._hsv_bands()
    assert b[0][0][0] == 0 and b[0][1][0] == C.HSV_HUE_TOL
    assert b[1][0][0] == 180 - C.HSV_HUE_TOL and b[1][1][0] == 179
    assert b[0][0][1] == int(C.HSV_SAT_FRAC * 226)


# ---------------------------------------------------------------- camera model
def test_focal_length_from_fovy_is_450px():
    assert C.focal_length_px(56.14, 480) == pytest.approx(450.0, abs=0.1)


def test_fixture_nadir_closed_form():
    """FIXTURE: nadir camera at (10, 20, 30): the principal point maps straight below; 90 px right = +6 m in x at f=450, h=30."""
    c = bare()
    p = c.inverse_pinhole_projection(320, 240, (10.0, 20.0, 30.0))
    assert p == pytest.approx([10.0, 20.0, 0.0])
    p = c.inverse_pinhole_projection(410, 240, (10.0, 20.0, 30.0))
    assert p == pytest.approx([16.0, 20.0, 0.0])
    p = c.inverse_pinhole_projection(320, 330, (10.0, 20.0, 30.0))   # image-down = world -y
    assert p == pytest.approx([10.0, 14.0, 0.0])
    assert c.inverse_pinhole_projection(320, 240, (0, 0, 0.0)) is None


def test_fixture_camera_ray_roundtrip_oblique():
    """FIXTURE: the cam_*_fwd frame of models/uav_fleet.xml (xyaxes 0 -1 0 / 0.5 0 0.866, 30 deg below the horizon)
    on a UAV yawed 40 deg. Project a world point forward, invert it: error < 1e-9 m."""
    x = np.array([0.0, -1.0, 0.0])
    y = np.array([0.5, 0.0, 0.866])
    y = y / np.linalg.norm(y)
    z = np.cross(x, y)
    yaw = math.radians(40.0)
    ry = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
    r = ry @ np.column_stack([x, y, z])               # MuJoCo cam_xmat: columns are the camera axes in world
    assert np.linalg.det(r) == pytest.approx(1.0)
    cam = np.array([1.0, 2.0, 2.4])
    world = np.array([1.0 + 4.0 * math.cos(yaw), 2.0 + 4.0 * math.sin(yaw), 0.85])   # 4 m ahead, in front of the camera
    pc = r.T @ (world - cam)
    assert pc[2] < 0                                  # in front of the camera
    f = 450.0
    u, v = 320 + f * pc[0] / -pc[2], 240 - f * pc[1] / -pc[2]
    assert 0 <= u <= 640 and 0 <= v <= 480
    back = bare().inverse_pinhole_projection(u, v, cam, cam_xpos=cam, cam_xmat=r.reshape(9), ground_z=0.85)
    assert back == pytest.approx(world, abs=1e-9)


def test_camera_ray_above_horizon_returns_none():
    r = np.eye(3)                                                 # camera looks straight down; a ray cannot go up
    assert bare().inverse_pinhole_projection(320, 240, (0, 0, 5.0), cam_xpos=(0, 0, 5.0), cam_xmat=r, ground_z=9.0) is None


# ---------------------------------------------------------------- rendered frames, real scenes
def _frames(vib, sb, n_path, scale):
    return [f for f in sb.frames(n_path, scale) if f["gt_pixels"] >= vib.MIN_GT_PIXELS]


@pytest.mark.parametrize("scene", ["interior", "exterior"])
def test_bbox_on_a_known_rendered_frame(benches, scene):
    """One rendered frame: the detector box must overlap the segmentation ground-truth box with IoU >= 0.85."""
    vib, sb = benches[0], benches[1][scene]
    fr = _frames(vib, sb, 12, 1.0)[0]
    res = sb.ctl.detect_intruder_hsv(fr["rgb"])
    assert res["detected"]
    assert vib.bbox_iou(res["bbox"], fr["gt_bbox"]) >= 0.85


@pytest.mark.parametrize("scene", ["interior", "exterior"])
def test_noon_iou_at_least_0_70(benches, scene):
    vib, sb = benches[0], benches[1][scene]
    frames = _frames(vib, sb, 24, 1.0)
    assert len(frames) >= 10
    ious = [vib.evaluate(sb.ctl, f)[0] for f in frames]
    assert np.mean(ious) >= 0.70


@pytest.mark.parametrize("scene,bound_m", [("interior", 1.0), ("exterior", 0.25)])
def test_projection_error_bound(benches, scene, bound_m):
    """Mean horizontal error of the image-only ground estimate. Bounds are set from the first benchmark run
    (interior mean 0.47 m at 2-8 m oblique range, exterior 0.06 m at 20-24 m nadir) with headroom."""
    vib, sb = benches[0], benches[1][scene]
    errs = [e for _, _, d, e in (vib.evaluate(sb.ctl, f) for f in _frames(vib, sb, 24, 1.0)) if d and e is not None]
    assert len(errs) >= 10
    assert np.mean(errs) < bound_m


# ---------------------------------------------------------------- handoff (FIXTURE states, no simulator)
A, B = np.array([0.0, 0.0, 20.0]), np.array([30.0, 0.0, 20.0])


def test_fixture_handoff_follows_the_target():
    c = bare()
    assert c.select_tracking_uav((2.0, 0.0), {"alpha": A, "bravo": B}) == "alpha"
    assert c.select_tracking_uav((28.0, 0.0), {"alpha": A, "bravo": B}) == "bravo"


def test_fixture_handoff_hysteresis_prevents_ping_pong():
    """Target jitters +-1 m about the midpoint: control may change hands at most once, never every step."""
    c = bare()
    states = {"alpha": A, "bravo": B}
    c.select_tracking_uav((5.0, 0.0), states)
    owners = [c.select_tracking_uav((15.0 + (1.0 if i % 2 else -1.0), 0.0), states) for i in range(40)]
    switches = sum(1 for a, b in zip(owners, owners[1:]) if a != b)
    assert switches == 0 and owners[0] == "alpha"
    assert c.select_tracking_uav((20.0, 0.0), states) == "bravo"      # a clear lead (10 m closer) does hand over
    assert c.select_tracking_uav((16.0, 0.0), states) == "bravo"      # and the new owner is sticky


def test_fixture_handoff_prefers_the_uav_that_can_see_the_target():
    """Nearest-by-distance alone is wrong: alpha is closer (5 m) but, flying at 5 m, its footprint is only +-3.6 m
    wide and misses the target; bravo is 11 m away at 30 m altitude (footprint +-21 m) and holds it."""
    c = bare()
    low = np.array([4.0, 0.0, 5.0])
    high = np.array([20.0, 0.0, 30.0])
    assert c.select_tracking_uav((9.0, 0.0), {"alpha": low, "bravo": high}) == "bravo"
    c2 = bare()
    assert c2.select_tracking_uav((5.0, 0.0), {"alpha": low, "bravo": high}) == "alpha"   # both hold it: nearest wins


def test_fixture_handoff_with_nobody_in_view_picks_nearest():
    c = bare()
    far = c.select_tracking_uav((500.0, 0.0), {"alpha": A, "bravo": B})
    assert far == "bravo"
