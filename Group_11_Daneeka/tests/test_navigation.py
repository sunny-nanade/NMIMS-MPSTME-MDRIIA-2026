import math

from navigation import PID, EstimatorConfig, GoToPose, PoseEstimator, wrap


def test_wrap():
    assert abs(wrap(3 * math.pi) - math.pi) < 1e-9 or abs(wrap(3 * math.pi) + math.pi) < 1e-9


def test_pid_antiwindup_integral_bounded():
    pid = PID(1.0, 5.0, 0.0, out_limit=1.0, i_limit=10.0)
    for _ in range(2000):
        pid.step(5.0, 0.01)       # saturated for a long time
    assert pid.i < 1.5            # conditional integration stops the integral growing without bound


def test_dead_reckoning_straight_line():
    est = PoseEstimator(0, 0, 0, EstimatorConfig(use_range=False, use_fiducial=False))
    for _ in range(100):
        est.predict(0.01, 0.0, 0.0, 0.02)
    assert abs(est.x - 1.0) < 1e-9 and abs(est.y) < 1e-9


def test_fiducial_correction_pulls_x():
    est = PoseEstimator(0.4, 0, 0, EstimatorConfig())
    est.update_fiducial(0.0)
    assert abs(est.x) < 0.05


def test_range_pair_gives_heading_and_lateral():
    est = PoseEstimator(0, 0, 0.0, EstimatorConfig(range_heading_gain=1.0, range_y_gain=1.0))
    # lane 1 geometry: plane y at sensor height 0.549 m, robot at y=-1.9: expect d = 0.549+1.9-0.24 = 2.209
    est.y = -1.85
    est.update_range((2.209, 2.209), +1, 0.549, 0.0)
    assert abs(est.y + 1.9) < 1e-6 and abs(est.theta) < 1e-9


def test_goto_stops_at_goal():
    est = PoseEstimator(0, 0, 0)
    est.x, est.y = 1.0, 1.0
    v, w, done = GoToPose().command(est, 1.0, 1.0, None)
    assert done and v == 0
