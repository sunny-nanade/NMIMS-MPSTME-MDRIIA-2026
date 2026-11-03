"""Inspection-mission controller for the solar-farm AMR (MuJoCo physics, Python control).

Finite-state machine (dossier Section 3):

    ROW_FOLLOW -> SCAN -> [ANOMALY_FLAG -> GEOTAG] -> (next module) ... end of row -> NEXT_ROW -> ROW_FOLLOW
                                                                          last row   -> RETURN_TO_DOCK -> DONE

* ROW_FOLLOW     lane-follow with PID, estimator corrections, brake to the next module stop point.
* SCAN           aim the pan/tilt head at the module, settle, collect thermal+optical frames, analyse.
* ANOMALY_FLAG   (proposed controller only) verification views (different mast height / extra frames)
                 before a detection is accepted -- also used when glint makes a view unreliable.
* GEOTAG         write the detection record (module id, cell, estimated position, confidence).
* NEXT_ROW       headland transit to the next lane.
* RETURN_TO_DOCK drive back to the dock pose.

Conditions
----------
baseline : odometry+gyro localisation only, 1 frame per module, fixed absolute threshold, no
           irradiance gating, no glint handling, no verification (a conventional "fixed route +
           fixed threshold" survey). Module id = module nearest to the *estimated* aim point.
proposed : range-pair + fiducial localisation, 3 frames, irradiance-gated relative anomaly score,
           glint-risk-aware viewpoint (mast height) selection, optical confounder discrimination,
           verification views, frame-edge registration for module association.

Everything the controller knows comes from ``SensorSuite``; the true state is only logged.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import mujoco
import numpy as np

import robot_params as rp
from defect_detection import Detector, DetectorConfig
from fault_injection import FaultConfig, GroundTruth, seed_random_defects
from navigation import (EstimatorConfig, GoToPose, LaneFollower, PoseEstimator, serpentine_plan,
                        wrap)
from panel_registry import FarmConfig, PanelRegistry
from robot_controller import WheelController, wheel_speeds
from sensor_simulation import SensorSuite
from solar_environment import EnvConfig, SolarEnvironment
from sun_position import SunModel
from telemetry import STATE_NAMES, Telemetry

DT = 0.002
NAV_EVERY = 10           # 50 Hz navigation / sensing
ENV_EVERY = 50           # 0.1 s environment update
S = {n: i for i, n in enumerate(STATE_NAMES)}


@dataclass
class MissionConfig:
    condition: str = "proposed"            # "baseline" | "proposed"
    seed: int = 0
    max_time_s: float = 900.0
    rows: list | None = None               # default: all rows
    v_cruise: float = rp.V_CRUISE
    n_defects: int | None = None
    n_confounders: int | None = None
    env: EnvConfig = field(default_factory=EnvConfig)
    faults: FaultConfig = field(default_factory=FaultConfig)
    defects: list | None = None            # explicit list (scenarios) overrides random seeding
    log_telemetry: bool = True
    verbose: bool = False
    stop_each_module: bool = True


@dataclass
class MissionResult:
    config: MissionConfig
    detections: list
    truth: GroundTruth
    duration_s: float
    wall_s: float
    completed: bool
    telemetry: Telemetry | None
    metrics: dict
    visited: list
    events: list


class InspectionMission:
    def __init__(self, cfg: MissionConfig, model_path: str):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.reg = PanelRegistry()
        defects = cfg.defects
        if defects is None:
            defects = seed_random_defects(self.reg, np.random.default_rng(cfg.seed + 10_000),
                                          cfg.n_defects, cfg.n_confounders)
        self.gt = GroundTruth(self.reg, defects)
        self.env = SolarEnvironment(self.reg, cfg.env, self.gt, seed=cfg.seed + 20_000)
        self.m = mujoco.MjModel.from_xml_path(model_path)
        self.d = mujoco.MjData(self.m)
        mujoco.mj_forward(self.m, self.d)
        self.sensors = SensorSuite(self.m, self.d, self.reg, self.env, cfg.faults,
                                   np.random.default_rng(cfg.seed + 30_000))
        prop = cfg.condition == "proposed"
        self.proposed = prop
        ecfg = EstimatorConfig(use_gyro=True, use_range=prop, use_fiducial=prop)
        dx, dy, dth = self.reg.dock_pose
        self.est = PoseEstimator(dx + cfg.faults.nav.init_x_error, dy, dth, ecfg)
        self.det = Detector(self.reg, DetectorConfig(proposed=prop), np.random.default_rng(cfg.seed + 40_000))
        self.sun_model = SunModel(cfg.env.latitude_deg, cfg.env.longitude_deg, cfg.env.utc_offset_h)
        self.lane = LaneFollower()
        self.goto = GoToPose()
        self.wheels = WheelController()
        self.legs = serpentine_plan(self.reg, cfg.rows)
        self.leg_i = 0
        self.stop_i = 0
        self.state = S["INIT"]
        self.t_state = 0.0
        self.cmd_v = self.cmd_w = 0.0
        self.pan_cmd = self.tilt_cmd = 0.0
        self.lift_cmd = 0.0
        self.detections: list[dict] = []
        self.visited: list[str] = []
        self.events: list[str] = []
        self.frames: list = []
        self.tau2 = 0.0
        self.step_n = 0
        self.chassis = self.sensors.chassis
        self.pending_det = None
        self.hook = None
        self.hook_every = 16
        self.verify_stage = 0
        self.gate_wait = 0.0
        self.consec_gated = 0
        self.deferred_flag = False
        self.unassessed: list = []
        self.route: list = []
        self.cap = int(cfg.max_time_s / DT) + 10
        self.tel = Telemetry(int(min(self.cap, 400_000)), cfg.seed, cfg.condition) if cfg.log_telemetry else None
        self._last_frame_t = -1.0
        self._dock_goal = (dx, dy)
        self._build_stops()
        self._cur_xlim = None
        self.obstacle_ids = {i for i in range(self.m.ngeom)
                             if self.m.geom_bodyid[i] == 0 and self.m.geom_contype[i] > 0
                             and not self.m.geom(i).name.startswith("floor")}
        self.obstacle_contact_ticks = 0

    # ------------------------------------------------------------------ route helpers
    def _build_stops(self):
        c = self.reg.cfg
        self.stops = []
        for leg in self.legs:
            cols = list(range(1, c.n_cols + 1))
            if leg["direction"] < 0:
                cols = cols[::-1]
            self.stops.append([(self.reg.pid_at(leg["row"], k),
                                self.reg.panel_x(k) - leg["direction"] * rp.MAST_X) for k in cols])

    def _goto_state(self, name: str):
        self.state = S[name]
        self.t_state = self.d.time
        if self.cfg.verbose:
            print(f"  t={self.d.time:7.2f}  -> {name}")

    # ------------------------------------------------------------------ head
    def _lens_est(self, lift: float):
        x, y, th = self.est.pose
        px = x + rp.MAST_X * math.cos(th)
        py = y + rp.MAST_X * math.sin(th)
        pz = rp.CHASSIS_Z0 + rp.MAST_BASE_Z + rp.HEAD_Z_IN_SLIDER + lift
        return np.array([px, py, pz])

    def aim_at(self, target: np.ndarray, lift: float):
        lens = self._lens_est(lift)
        dv = target - lens
        horiz = math.hypot(dv[0], dv[1])
        pan = wrap(math.atan2(dv[1], dv[0]) - self.est.theta)
        tilt = math.atan2(-dv[2], horiz)
        self.pan_cmd = float(np.clip(pan, -rp.PAN_LIMIT, rp.PAN_LIMIT))
        self.tilt_cmd = float(np.clip(tilt, rp.TILT_MIN, rp.TILT_MAX))
        self.lift_cmd = float(np.clip(lift, rp.LIFT_MIN, rp.LIFT_MAX))

    def stow_head(self):
        self.pan_cmd, self.tilt_cmd, self.lift_cmd = 0.0, 0.3, 0.0

    # ------------------------------------------------------------------ context for the detector
    def context(self, lens_est, view_pid_guess):
        sun = self.sun_model.at(self.cfg.env.date, self.env.t_env % 86400.0)
        return dict(
            sun_vec=sun.vec, sun_elev=sun.elevation_deg, lens_est=lens_est,
            g_ref=self.sensors.read_reference_irradiance(),
            t_amb=float(self.env.t_amb + self.rng.normal(0, 0.3)),
            wind=float(self.env.wind + self.rng.normal(0, 0.2)),
            pid_guess=view_pid_guess, est_pose=self.est.pose, t_env=self.env.t_env,
            row=self.legs[self.leg_i]["row"] if self.leg_i < len(self.legs) else None)

    # ------------------------------------------------------------------ one 50 Hz navigation tick
    def nav_tick(self):
        dt = NAV_EVERY * DT
        sn, est = self.sensors, self.est
        for k in range(self.d.ncon):
            c = self.d.contact[k]
            if c.geom1 in self.obstacle_ids or c.geom2 in self.obstacle_ids:
                self.obstacle_contact_ticks += 1
                break
        dq, _ = sn.read_wheels()
        ds, dth = sn.odometry_increments(dq)
        est.predict(ds, dth, sn.read_gyro_z(), dt)
        leg = self.legs[self.leg_i] if self.leg_i < len(self.legs) else None
        in_lane = self.state in (S["ROW_FOLLOW"], S["SCAN"], S["ANOMALY_FLAG"], S["GEOTAG"])
        if leg is not None and in_lane and est.cfg.use_range:
            side = leg["side"]
            pair = sn.read_side_pair(side > 0)
            zs = self.d.site_xpos[sn.site["rf_lf"]][2]
            yp = self.reg.plane_y_at_height(leg["row"], zs)
            th_ref = 0.0 if leg["direction"] > 0 else math.pi
            est.update_range(pair, side, yp, th_ref)
        if est.cfg.use_fiducial:
            r_for_marker = leg["row"] if leg is not None else 1
            est.update_fiducial(sn.read_fiducial(r_for_marker))
        getattr(self, "_s_" + STATE_NAMES[self.state].lower())(dt)

    # ------------------------------------------------------------------ states
    def _s_init(self, dt):
        self.cmd_v = self.cmd_w = 0.0
        self.stow_head()
        if self.d.time - self.t_state > 1.0:
            self.lane.reset()
            self._goto_state("ROW_FOLLOW")

    def _s_row_follow(self, dt):
        leg = self.legs[self.leg_i]
        stops = self.stops[self.leg_i]
        self.stow_head() if self.stop_i == 0 and abs(self.est.x - stops[0][1]) > 1.5 else None
        if self.stop_i >= len(stops):
            self.cmd_v = self.cmd_w = 0.0
            if self.proposed:
                for r in self.det.finalise_pending():
                    self.detections.append(r.record(self.d.time, self.env.t_env, self.cfg.condition))
                    self.events.append(f"{self.d.time:.1f}s late-review {r.pid_est} {r.kind} {r.reason}")
            self.leg_i += 1
            self.stop_i = 0
            if self.leg_i >= len(self.legs):
                self.route = [(self._dock_goal[0] + 0.0, self.legs[-1]["lane_y"]), ]
                self._goto_state("RETURN_TO_DOCK")
            else:
                self._plan_transit()
                self._goto_state("NEXT_ROW")
            return
        pid, x_stop = stops[self.stop_i]
        dirn = leg["direction"]
        remain = (x_stop - self.est.x) * dirn
        v_des = self.cfg.v_cruise if not self.cfg.stop_each_module else min(self.cfg.v_cruise, 0.25 + 0.9 * max(remain, 0.0))
        if remain <= 0.015 and self.cfg.stop_each_module:
            self.cmd_v, self.cmd_w = 0.0, 0.0
            if abs(self.cmd_v) < 1e-3 and self._wheel_speed_small():
                self.frames = []
                self.verify_stage = 0
                self._goto_state("SCAN")
            return
        if remain <= 0.0:
            self.stop_i += 1
        self.cmd_v, self.cmd_w = self.lane.command(self.est, leg["lane_y"], dirn, v_des, dt)
        if self.cfg.stop_each_module and remain < 0.4:
            self.pre_aim(pid)

    def pre_aim(self, pid):
        spec = self.reg.get(pid)
        self.aim_at(spec.center, 0.5 if self.proposed else 0.5)

    def _wheel_speed_small(self):
        return abs(self.d.qvel[self.sensors.vadr_l]) < 0.15 and abs(self.d.qvel[self.sensors.vadr_r]) < 0.15

    def _s_scan(self, dt):
        self.cmd_v = self.cmd_w = 0.0
        leg = self.legs[self.leg_i]
        pid_target = self.stops[self.leg_i][self.stop_i][0]
        spec = self.reg.get(pid_target)
        t = self.d.time - self.t_state
        # lift choice: proposed = pick the lift whose predicted glint risk is lower (ephemeris + geometry only)
        lift = self._choose_lift(spec) if self.proposed else 0.5
        self.aim_at(spec.center, lift)
        settle = 0.9
        if t < settle:
            return
        if self.d.time - self._last_frame_t >= 0.2:
            self._last_frame_t = self.d.time
            obs = self.sensors.observe(self.env.t_sim)
            self.frames.append(obs)
        n_need = 3 if self.proposed else 1
        if len(self.frames) >= n_need:
            self._analyse(spec)

    def _choose_lift(self, spec):
        from sensor_simulation import estimate_glint_risk
        sun = self.sun_model.at(self.cfg.env.date, self.env.t_env % 86400.0)
        best, best_r = 0.5, 9.0
        for lift in (0.5, 0.25, 0.0):
            lens = self._lens_est(lift)
            r = estimate_glint_risk(lens, spec.center, self.reg, self.sensors.grid, sun.vec,
                                    self.env.comp["dni"] * 0.9)
            if r < best_r - 0.05:
                best, best_r = lift, r
        return best

    def _analyse(self, spec):
        ctx = self.context(self._lens_est(self.lift_cmd), spec.pid)
        res = self.det.analyse(self.frames, ctx)
        if res.gated and self.gate_wait < 30.0:
            # irradiance below the validity limit: wait (cloud passing) and look again, up to 30 s
            self.gate_wait += 2.0
            self.frames = []
            self.t_state = self.d.time - 0.9 + 2.0   # next frame in ~2 s
            return
        self.gate_wait = 0.0
        if res.gated:
            self.unassessed.append(res.pid_est)
            self.consec_gated += 1
            if self.consec_gated >= 3:
                # irradiance stays below the validity limit: abort, reschedule the mission, go home
                self.events.append(f"{self.d.time:.1f}s MISSION DEFERRED: irradiance below limit for 3 consecutive modules")
                self.deferred_flag = True
                self.stow_head()
                leg = self.legs[self.leg_i]
                x_head = leg["x_end"] + leg["direction"] * 1.6
                self._ret = [(x_head if abs(self.est.x - x_head) > 1.5 else self.est.x, leg["lane_y"]),
                             (x_head, self.reg.lane_y(1)), (self._dock_goal[0], self.reg.lane_y(1))]
                self._ret_k = 0
                self._ret_stage = True
                self._goto_state("RETURN_TO_DOCK")
                return
        else:
            self.consec_gated = 0
        self.visited.append(res.pid_est if res.pid_est else spec.pid)
        self.events.append(f"{self.d.time:.1f}s scan {spec.pid} -> {res.summary()}")
        if self.proposed and res.need_recheck and self.verify_stage < 2:
            self.verify_stage += 1
            self.pending_det = res
            self._goto_state("ANOMALY_FLAG")
            return
        if res.flagged:
            self.pending_det = res
            self._goto_state("GEOTAG")
        else:
            self._next_module()

    def _s_anomaly_flag(self, dt):
        """Verification view: change mast height, take fresh frames, then re-analyse."""
        self.cmd_v = self.cmd_w = 0.0
        spec = self.reg.get(self.stops[self.leg_i][self.stop_i][0])
        t = self.d.time - self.t_state
        alt = 0.0 if self.lift_cmd > 0.25 else 0.5
        if self.verify_stage >= 2:
            alt = 0.25
        self.aim_at(spec.center, alt)
        if t < 1.1:
            return
        obs = self.sensors.observe(self.env.t_sim)
        self.frames = [obs] + self.frames[-2:]
        self._last_frame_t = self.d.time
        if t > 1.4:
            self.frames = self.frames[:3]
            self.t_state = self.d.time
            self._analyse(spec)

    def _s_geotag(self, dt):
        self.cmd_v = self.cmd_w = 0.0
        res = self.pending_det
        rec = res.record(self.d.time, self.env.t_env, self.cfg.condition)
        self.detections.append(rec)
        self.events.append(f"{self.d.time:.1f}s GEOTAG {rec['panel_id_est']} {rec['kind_est']} cell={rec['cell_est']}")
        self._next_module()

    def _next_module(self):
        self.stop_i += 1
        self.frames = []
        self.det.reset_module()
        self._goto_state("ROW_FOLLOW")

    def _plan_transit(self):
        prev, nxt = self.legs[self.leg_i - 1], self.legs[self.leg_i]
        x_head = prev["x_end"] + prev["direction"] * 1.6
        self.route = [(x_head, prev["lane_y"]), (x_head, nxt["lane_y"]),
                      (nxt["x_start"] - 0.0, nxt["lane_y"])]
        self.route_final = 0.0 if nxt["direction"] > 0 else math.pi
        # leave a lead-in so range sensors can lock before the first module
        self.route[-1] = (nxt["x_start"], nxt["lane_y"])
        self.route_k = 0
        self.stow_head()

    def _s_next_row(self, dt):
        # first rotate to the first waypoint, etc.
        if not self.route:
            self.lane.reset()
            self._goto_state("ROW_FOLLOW")
            return
        tx, ty = self.route[self.route_k]
        last = self.route_k == len(self.route) - 1
        v, w, done = self.goto.command(self.est, tx, ty, self.route_final if last else None)
        self.cmd_v, self.cmd_w = v, w
        if done or (not last and math.hypot(tx - self.est.x, ty - self.est.y) < 0.15):
            self.route_k += 1
            if self.route_k >= len(self.route):
                self.lane.reset()
                self.route = []
                self._goto_state("ROW_FOLLOW")

    def _s_return_to_dock(self, dt):
        self.stow_head()
        leg = self.legs[-1]
        if not hasattr(self, "_ret_stage"):
            x_head = leg["x_end"] + leg["direction"] * 1.6
            y_to = self.reg.lane_y(1) - 0.0
            self._ret = [(x_head, leg["lane_y"]), (x_head, y_to - 0.0), (self._dock_goal[0], y_to)]
            self._ret_k = 0
            self._ret_stage = True
        tx, ty = self._ret[self._ret_k]
        last = self._ret_k == len(self._ret) - 1
        v, w, done = self.goto.command(self.est, tx, ty, 0.0 if last else None)
        self.cmd_v, self.cmd_w = v, w
        if done or (not last and math.hypot(tx - self.est.x, ty - self.est.y) < 0.2):
            self._ret_k += 1
            if self._ret_k >= len(self._ret):
                self.cmd_v = self.cmd_w = 0.0
                self._goto_state("DONE")

    def _s_done(self, dt):
        self.cmd_v = self.cmd_w = 0.0
        self.stow_head()

    # ------------------------------------------------------------------ run loop
    def run(self) -> MissionResult:
        t_wall0 = time.time()
        m, d, cfg = self.m, self.d, self.cfg
        sn = self.sensors
        a_l, a_r = 0, 1
        d.ctrl[:] = 0.0
        step = 0
        done_since = None
        while d.time < cfg.max_time_s:
            if step % NAV_EVERY == 0:
                self.nav_tick()
            if step % ENV_EVERY == 0:
                self.env.advance(ENV_EVERY * DT)
            # wheel loop (500 Hz)
            w_ref = np.array(wheel_speeds(self.cmd_v, self.cmd_w))
            w_meas = np.array([d.qvel[sn.vadr_l], d.qvel[sn.vadr_r]])
            tau = self.wheels.step(w_ref, w_meas, DT)
            d.ctrl[a_l], d.ctrl[a_r] = tau[0], tau[1]
            d.ctrl[2], d.ctrl[3], d.ctrl[4] = self.pan_cmd, self.tilt_cmd, self.lift_cmd
            self.tau2 += float(tau @ tau) * DT
            mujoco.mj_step(m, d)
            if self.tel is not None:
                p = d.xpos[self.chassis]
                R = d.xmat[self.chassis].reshape(3, 3)
                yaw = math.atan2(R[1, 0], R[0, 0])
                leg = self.legs[min(self.leg_i, len(self.legs) - 1)]
                th_ref = 0.0 if leg["direction"] > 0 else math.pi
                self.tel.log(t=d.time, state=self.state, x_true=p[0], y_true=p[1], yaw_true=yaw,
                             x_est=self.est.x, y_est=self.est.y, yaw_est=self.est.theta,
                             v_cmd=self.cmd_v, w_cmd=self.cmd_w, w_left=w_meas[0], w_right=w_meas[1],
                             tau_left=tau[0], tau_right=tau[1], pan=sn.d.qpos[sn.pan_q],
                             tilt=sn.d.qpos[sn.tilt_q], lift=sn.d.qpos[sn.lift_q],
                             lane_y_ref=leg["lane_y"], cross_track_err=p[1] - leg["lane_y"],
                             heading_err=wrap(yaw - th_ref), d_sensor=0.0, tau2_cum=self.tau2)
            step += 1
            if self.hook is not None and step % self.hook_every == 0:
                if self.hook(self) is False:
                    break
            if self.state == S["DONE"]:
                done_since = done_since or d.time
                if d.time - done_since > 0.5:
                    break
        completed = self.state == S["DONE"]
        return self._finish(completed, time.time() - t_wall0)

    def _finish(self, completed, wall):
        from metrics import mission_metrics
        res = MissionResult(self.cfg, self.detections, self.gt, float(self.d.time), wall, completed,
                            self.tel, {}, self.visited, self.events)
        res.metrics = mission_metrics(self, res)
        return res


def run_inspection_mission(cfg: MissionConfig, model_path: str = "models/solar_defect_amr.xml") -> MissionResult:
    return InspectionMission(cfg, model_path).run()
