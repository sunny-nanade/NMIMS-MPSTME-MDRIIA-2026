# Autonomous Collaborative Dual-UAV Perimeter Patrol Controller
# Group: MDRIIA Group 05
# Scene (default): INSIDE the NMIMS Main Building, Vile Parle (West), Mumbai --
#   ground-floor corridor loop + central atrium with ten gallery levels.
# Exterior perimeter variant: --scene exterior
#
# Region ownership in this file (one owner per region -- see docs/planning/):
#   E043 Muaaz   flight dynamics, cascaded control, mixer, separation, patrol
#                planning, MuJoCo integration loop, flight telemetry
#   E051 Aditya  detect_intruder_hsv, inverse_pinhole_projection
#   E075 Zaid    evaluate_geofence_status (+ alert packets)
#   E077 Soumya  analytics/campus_security_economics.py (separate file)
# A pull request may only change lines inside its author's region.
# src/check_region_ownership.py enforces this before Muaaz merges to main.

import argparse
import csv
import inspect
import math
import os
import sys
import time

import mujoco
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_telemetry import StepTelemetry   # noqa: E402  contract-B per-step log
from patrol_metrics import checkpoint_metrics   # noqa: E402  shared with the guard baseline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = {
    "interior": os.path.join(ROOT, "models", "campus_perimeter_patrol.xml"),
    "exterior": os.path.join(ROOT, "models", "campus_perimeter_patrol_exterior.xml"),
}
MODEL_PATH = SCENES["interior"]
RUNS_DIR = os.path.join(ROOT, "analytics", "runs")


class DualUAVSurveillanceController:
    """
    Collaborative Dual-UAV Swarm Patrol, Vision Tracking, and Geofencing Controller
    Student Implementation Boundaries:
    - E043 (Muaaz): 6-DOF cascaded flight control and APF inter-drone separation
    - E051 (Aditya): OpenCV vision processing, target extraction, and inverse pinhole projection
    - E075 (Zaid): 3D polygonal geofencing, 4-tier alert state machine, and telemetry logging
    - E077 (Soumya): CSBS security operations time-motion and labor reallocation analysis
    """

    def __init__(self, model_path=MODEL_PATH, policy="sectors", wind_mps=None,
                 gust_sigma=None, seed=0, intruder_appear_s=None, vision=True,
                 telemetry_path=None, run_id=None, condition=None, frame_log=True, dock_jitter_m=0.0,
                 vision_hz=None, layered_separation=True, obstacle_avoidance=True, geofence_hysteresis=True,
                 auto_exposure=True, static_handover=True):
        # ABLATION FLAGS (analytics/run_ablations.py). The defaults ARE the production code path; each
        # False switches off exactly one mitigation:
        #   layered_separation  False = the guide's APF only (no closing-speed governor, sidestep or
        #                       altitude layer); True = APF + governor + altitude layering (production)
        #   obstacle_avoidance  False = FR-18 reactive range-ring layer off (sensing still runs)
        #   geofence_hysteresis False = E075 raw tier every tick (no exit margin, no breach dwell)
        #   auto_exposure       False = E051 detector thresholds the raw frame (no low-light gain)
        #   static_handover     False = a stationary tier-0 target is held in TRACK for the full TRACK_MAX_S
        self.layered_separation = bool(layered_separation)
        self.obstacle_avoidance = bool(obstacle_avoidance)
        self.geofence_hysteresis = bool(geofence_hysteresis)
        self.auto_exposure = bool(auto_exposure)
        self.static_handover = bool(static_handover)
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.policy = policy
        self.scene_name = self._text("scene_name", "unnamed scene")

        # scaffold parameters (names kept); scene files override via <custom>
        self.cruise_speed_mps = self._num("cruise_speed", 6.0)
        self.d_safe_m = 2.5
        self.current_time_s = 0.0

        # restricted zone read from the model -- the scene is the single source of truth
        gid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "substation_zone")
        zx, zy = self.model.geom_pos[gid][:2]
        hx, hy = self.model.geom_size[gid][:2]
        self.substation_bounds = (zx - hx, zy - hy, zx + hx, zy + hy)  # xmin, ymin, xmax, ymax

        self.dock_jitter_m = float(dock_jitter_m)
        self._init_flight(wind_mps, gust_sigma)
        self._init_intruder(intruder_appear_s)

        # vision: enabled only once E051's detector exists -- never faked
        self.vision_enabled = vision
        self.vision_cams = self._text("vision_cams", "cam_alpha cam_bravo").split()
        self.renderer = None
        self.vision_status = "pending"
        self.first_detect_s = None      # first raw detector hit (any UAV), before verification
        self.vision_hz = float(vision_hz) if vision_hz else self.VISION_HZ
        self._init_surveillance()

        # Telemetry buffer (scaffold keys first, then flight-quality channels)
        self.telemetry = {
            "time_s": [],
            "inter_uav_dist_m": [],
            "alpha_pos": [],
            "bravo_pos": [],
            "detected": [],
            "detection_latency_ms": [],
            "alert_status": [],
        }
        self.flight_rows = []
        # frame_log: per-frame dict rows (interactive / legacy); off in batch runs
        self.frame_log = frame_log
        # contract-B per-physics-step telemetry; None disables it (interactive use)
        self.condition = condition or f"uav_{policy}"
        self.run_id = run_id or f"run_{self.condition}_s{seed}"
        self.step_log = (StepTelemetry(telemetry_path, self.run_id, seed, self.condition)
                         if telemetry_path else None)
        self.uav_uav_contacts = 0
        self._step_k = 0
        self.min_inter_uav_m = float("inf")
        self._touching = set()
        # flight-quality accumulators (definitions in flight_metrics)
        self._sq_err_sum, self._sq_err_n = 0.0, 0
        self._effort_n2s = 0.0
        self._torque_n2m2s = 0.0                 # integral of |tau_body|^2 (both UAVs), N^2 m^2 s
        self._wp_sq_sum, self._wp_n = 0.0, 0     # timed waypoint-path error (see _waypoint_reference)

    def _num(self, name, default):
        i = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_NUMERIC, name)
        if i < 0:
            return default
        a, n = self.model.numeric_adr[i], self.model.numeric_size[i]
        v = self.model.numeric_data[a:a + n]
        return float(v[0]) if n == 1 else np.array(v)

    def _text(self, name, default):
        i = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_TEXT, name)
        if i < 0:
            return default
        a, n = self.model.text_adr[i], self.model.text_size[i]
        return bytes(self.model.text_data[a:a + n - 1]).decode()

    # ======================================================================
    # >>> E043 MUAAZ -- FLIGHT DYNAMICS, CONTROL, APF, PATROL PLANNING  >>>
    # ======================================================================
    # Airframe constants -- must mirror models/uav_fleet.xml
    ARM_L = 0.26                 # m, rotor offset from the centre ("+" layout)
    K_Q = 0.0201                 # m, rotor drag torque / thrust ratio
    F_MAX = 7.5                  # N per rotor (actuator ctrlrange)
    ROTOR_R = 0.12               # m, prop radius (energy model)
    ETA = 0.55                   # figure of merit x motor/ESC efficiency (ASSUMED)
    RHO = 1.204                  # kg/m^3, ISA sea-level air

    # Cascaded gains: position (P) -> velocity (PI) -> attitude (PD)
    KP_POS = 0.85
    KP_VEL, KI_VEL, I_CLAMP = 2.6, 0.55, 4.0
    KP_ATT = np.array([44.0, 44.0, 14.0])
    KD_ATT = np.array([11.5, 11.5, 5.5])
    MAX_TILT_RATE = math.radians(110.0)   # slew limit: stops overshoot at corners
    V_MAX_Z = 1.5
    ARRIVE_R = 1.0               # m, waypoint acceptance radius (indoor-tight)
    K_REP = 8.5                  # N m^2, APF gain (guide section 2.2)
    # Separation is layered, because the guide's APF alone does NOT hold d >= 2.5 m:
    # in a head-on pass at 6 m/s each (12 m/s closing, 48.6 J relative KE) it lets
    # the centres reach well below the 0.76 m tip-to-tip span -- the airframes touch. Measured in
    # tests/test_e043_separation.py; analytic bound (k/2)(1/d - 1/d_safe)^2 = KE -> d = 0.26 m.
    # Scene files set the strategic layer (altitude offset or separate volumes) and the sidestep
    # speed. 'd_warn' (self.D_WARN) is still read but no longer used: the kinematic governor in
    # _control starts braking at whatever range its stopping-distance rule needs (G-07).

    # FR-18 on-board obstacle sensing: 26 single-beam rangefinders per airframe, cast with
    # mj_multiRay from the airframe centre (sites in models/uav_fleet.xml): <uav>_rf_h0..h7
    # at 45 deg in the body x-y plane, <uav>_rf_u0..u7 / rf_d0..d7 at the same azimuths
    # tilted +/-20 deg (lintels, slab edges, furniture just off the rotor plane), rf_up, rf_dn.
    #   obstacle  = any COLLIDABLE geom (contype or conaffinity != 0) that is not part of a
    #               UAV. Visual-only geoms (floor finishes, flush wall/ceiling finishes),
    #               markers (substation_zone, patrol marks; checkpoints are sites) and the
    #               non-colliding intruder are looked THROUGH (the beam is re-cast past them).
    #               The other UAV is handled by the separation layer, so it is looked through too.
    # Planar scan (G-06): N_SCAN extra beams in the body x-y plane, every 360/N_SCAN deg, cast from the same
    # centre and PREPENDED to the 26 site beams (rf_up / rf_dn stay last). The 8 site beams at 45 deg left gaps
    # of 0.77 m at 1 m range: a 0.24 m atrium tree trunk at rotor height slipped between them during TRACK
    # diversions (measured: 92 of 300 forced diversions past the six atrium trees touched a trunk). At 3 deg
    # the gap at the 4.2 m indoor braking range is 0.22 m, under the trunk diameter.
    N_SCAN = 120          # ASSUMPTION: 90-360 points per revolution, the class of small planar scanning ToF lidars
    RF_RANGE_M = 8.0      # ASSUMPTION: 4-12 m, the class of small ToF / lidar rangefinders on ~1.5 kg quads
    RF_SIGMA_M = 0.02     # ASSUMPTION: 0.01-0.05 m 1-sigma range noise (Gaussian, independent per beam and sample)
    SENSE_HZ = 100.0      # ASSUMPTION: 50-1000 Hz update rate; 100 Hz = every 5th 0.002 s step
    # Reactive layer. Each beam return gives a range r and the hit surface normal n (pointing
    # back at the UAV). Distance to that surface d = r (-dir . n); approach speed = -v_cmd . n.
    # The approach speed is capped at the largest v that can still stop before D_STOP after a
    # reaction delay T_REACT:  v T_REACT + v^2 / (2 a_brake) = d - D_STOP, and inside D_STOP
    # turns into a back-off (D_STOP - d) / T_REACT, at most BACKOFF_MPS (continuous at D_STOP). a_brake = BRAKE_FRAC x the lateral acceleration the tilt
    # limit allows (horizontal surfaces: A_BRAKE_V). The cap starts biting at about 4.2 m
    # indoors (2.5 m/s, 15 deg tilt); outdoors (6 m/s, 28 deg) it already limits the approach
    # to ~5.1 m/s at the 8 m range limit. Velocity parallel to a wall is never limited, so
    # corridor flight is not slowed and cannot oscillate between the walls.
    #   D_STOP_H 0.6 m = prop-tip radius 0.38 m + 0.22 m margin (walls, rails, furniture sides)
    #   D_STOP_V 0.35 m = landing-leg depth 0.18 m + margin (floors, ceilings, slab undersides)
    D_STOP_H, D_STOP_V = 0.6, 0.35
    BRAKE_FRAC = 0.5      # design: half the tilt authority, the rest is margin
    T_REACT = 0.5         # s, design: sensing period + velocity/attitude loop response; 0.35 s let the
                          # airframe overshoot D_STOP and hunt, 0.5 s settles (tests/test_e043_obstacle_perception.py)
    A_BRAKE_V = 2.0       # m/s^2, design: vertical braking (thrust-to-weight 2.27)
    BACKOFF_MPS = 0.5
    H_BAND = 0.6          # m, design: vertical band around the rotor plane in which a wall-like hit is a
                          # lateral threat (airframe -0.18..+0.04 m + margin). Limitation: an edge lying
                          # 0-0.6 m above/below the rotor plane with nothing at rotor height (a door
                          # lintel at flight altitude) is first seen by the +/-20 deg beams at a
                          # horizontal range of ~0.6 / tan(20 deg) = 1.6 m.

    def _init_flight(self, wind_mps, gust_sigma):
        m = self.model
        self.MAX_TILT = math.radians(self._num("max_tilt_deg", 28.0))
        self.TRANSIT_ALT = self._num("transit_alt", 0.0)      # 0 = no transit layer (indoors)
        self.D_WARN = self._num("d_warn", 14.0)
        self.SIDESTEP = self._num("sidestep", 1.6)
        # yaw mode per UAV: 0 = hold 0 (nadir camera, image axes = East/North),
        # 1 = face direction of travel (forward camera looks down the corridor),
        # 2 = face outward from the atrium centre (camera looks into the galleries)
        self.YAW_MODE = {"alpha": int(self._num("yaw_mode_alpha", 0)), "bravo": int(self._num("yaw_mode_bravo", 0))}
        self.YAW_RATE = math.radians(90.0)
        layer_b = self._num("alt_layer_bravo", 0.0) if self.layered_separation else 0.0
        self.uavs = {}
        for name, prefix in (("alpha", "uav_alpha"), ("bravo", "uav_bravo")):
            bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, prefix)
            jnt = m.body_jntadr[bid]
            # MuJoCo stores inertia in the body's PRINCIPAL frame, which may be
            # reordered (here Izz is listed first). Rotate back to body axes.
            R = np.zeros(9)
            mujoco.mju_quat2Mat(R, m.body_iquat[bid])
            R = R.reshape(3, 3)
            I_body = R @ np.diag(m.body_inertia[bid]) @ R.T
            self.uavs[name] = {
                "bid": bid,
                "qadr": m.jnt_qposadr[jnt], "vadr": m.jnt_dofadr[jnt],
                "act": [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{name}_m{k}") for k in range(4)],
                "mass": float(m.body_subtreemass[bid]),
                "I": I_body,
                "i_vel": np.zeros(3), "tilt_cmd": np.zeros(2),
                "phase": "takeoff", "route": [], "idx": 0, "laps": 0,
                "energy_j": 0.0, "dist_m": 0.0, "last_xy": None, "collisions": 0,
                "geoms": {g for g in range(m.ngeom) if m.geom_bodyid[g] == bid},
                "u": np.zeros(4), "rpy": np.zeros(3), "apf_N": 0.0,
                "layer": layer_b if name == "bravo" else 0.0, "governor": False,
                "name": name, "yaw_cmd": 0.0,
                "fsm": "TAKEOFF", "events": [], "obstacle_contacts": 0,
                # surveillance FSM (contract E): role None = flying its patrol; otherwise the
                # FSM state label; override / look_at replace the route target / heading
                "role": None, "override": None, "look_at": None, "crumbs": [],
            }
            # put the airframe on its scene dock
            sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, f"dock_{name}")
            if sid >= 0:
                q = self.uavs[name]["qadr"]
                # dock jitter: landing placement error, fixed magnitude, random bearing per UAV
                th = np.random.default_rng([self.seed, 7, 0 if name == "alpha" else 1]).uniform(0.0, 2 * math.pi)
                jit = self.dock_jitter_m * np.array([math.cos(th), math.sin(th), 0.0])
                self.data.qpos[q:q + 3] = m.site_pos[sid] + np.array([0.0, 0.0, 0.2]) + jit
                self.data.qpos[q + 3:q + 7] = (1, 0, 0, 0)
        mujoco.mj_forward(m, self.data)

        self._init_sensing()

        self.routes = {key: self._read_sites(key) for key in ("patrol_cp", "atrium_cp")}
        self.ring = self.routes["patrol_cp"]
        self.ring_len = self._loop_len(self.ring)
        self.cruise_altitude_m = float(self.ring[0][1][2])            # scaffold attribute: Alpha's layer
        self.visits = {name: [] for key in self.routes for name, _ in self.routes[key]}
        pts = self.routes["atrium_cp"] or self.routes["patrol_cp"]
        self.yaw_centre = np.mean([p[:2] for _, p in pts], axis=0)
        self._build_routes()

        # Ornstein-Uhlenbeck gust field; scene-scaled (indoors ~ HVAC drafts only)
        scale = self._num("wind_scale", 1.0)
        mean = 3.0 if wind_mps is None else wind_mps
        th = math.radians(225.0)
        self.wind_mean = scale * np.array([-mean * math.sin(th), -mean * math.cos(th), 0.0])
        self.wind = self.wind_mean.copy()
        self.gust_sigma = (1.4 if gust_sigma is None else gust_sigma) * scale
        self.gust_theta = 0.55

    def _read_sites(self, prefix):
        out, k = [], 0
        while True:
            sid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, f"{prefix}{k}")
            if sid < 0:
                return out
            out.append((f"{prefix}{k}", self.model.site_pos[sid].copy()))
            k += 1

    @staticmethod
    def _loop_len(route):
        return float(sum(np.linalg.norm(route[(i + 1) % len(route)][1][:2] - route[i][1][:2])
                         for i in range(len(route)))) if route else 0.0

    def _build_routes(self):
        """
        sectors     -- the guide's Sector Alpha / Sector Beta.
                       Interior: Alpha flies the ground-floor corridor loop (a guard's
                       round); Bravo sweeps the atrium up through every gallery level
                       and back down. Exterior: the ring is split into two equal arcs,
                       each flown out and back.
        offset_ring -- both UAVs fly the main loop in the same direction, half a lap
                       apart. Halves the ground-loop revisit time, but nobody watches
                       the upper galleries -- the trade-off the paper measures.
        Routes are lists of (xy-z point, checkpoint name or None).
        """
        a, b = self.uavs["alpha"], self.uavs["bravo"]
        loop = [(p.copy(), n) for n, p in self.ring]
        if self.policy == "offset_ring":
            half = len(loop) // 2
            a["route"] = loop
            b["route"] = loop[half:] + loop[:half]
        elif self.policy == "sectors" and self.routes["atrium_cp"]:
            a["route"] = loop
            sweep = [(p.copy(), n) for n, p in self.routes["atrium_cp"]]
            b["route"] = sweep + sweep[-2:0:-1]                       # up, then back down
        elif self.policy == "sectors":
            cum = np.cumsum([0.0] + [np.linalg.norm(loop[(i + 1) % len(loop)][0][:2] - loop[i][0][:2])
                                     for i in range(len(loop))])
            L = cum[-1]
            for u, (s0, s1) in ((a, (0.0, L / 2)), (b, (L / 2, L))):
                arc = [loop[i] for i in range(len(loop)) if s0 <= cum[i] < s1]
                u["route"] = arc + arc[-2:0:-1]
        else:
            raise ValueError(f"unknown policy {self.policy}")
        # Each UAV gets its OWN copy of every waypoint before its altitude layer is added. The routes above
        # share point arrays (offset_ring: both UAVs hold the same loop objects; an out-and-back route holds
        # each inner point twice), so an in-place += put Bravo's +4 m layer on Alpha's points too: in the
        # exterior offset_ring both UAVs flew at 24 m and a TRACK / RETURN_TO_PATROL encounter reached 2.35 m
        # (main batch, exterior_uav_offset_ring_s4). tests/test_e043_separation.py checks the layers.
        for u in (a, b):
            u["route"] = [(p + np.array([0.0, 0.0, u["layer"]]), n) for p, n in u["route"]]

    @staticmethod
    def _quat_to_rpy(q):
        w, x, y, z = q
        roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
        yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return np.array([roll, pitch, yaw])

    def mix(self, thrust, tau):
        """
        Control allocation for the "+" layout. Physical allocation implied by
        the MJCF rotor sites and gear vectors:
            tau_x = l  (F2 - F3)            tau_z = kQ (F0 + F1 - F2 - F3)
            tau_y = l  (F1 - F0)            T     = F0 + F1 + F2 + F3
        (guide notation: tau_B = [l(T4-T2), l(T1-T3), cQ(T1-T2+T3-T4)] with
         T1=rotor1, T2=rotor3, T3=rotor0, T4=rotor2). This is its exact inverse.
        """
        tx, ty, tz = tau
        l, k = self.ARM_L, self.K_Q
        f = np.array([thrust / 4 - ty / (2 * l) + tz / (4 * k),
                      thrust / 4 + ty / (2 * l) + tz / (4 * k),
                      thrust / 4 + tx / (2 * l) - tz / (4 * k),
                      thrust / 4 - tx / (2 * l) - tz / (4 * k)])
        return np.clip(f, 0.0, self.F_MAX)

    def compute_apf_separation(self, p1, p2):
        """
        # TODO [E043 - Muaaz Mohammed Iqbal Shaikh]:
        Implement the Artificial Potential Field (APF) repulsive vector between UAVs:
        F_rep = k_rep * (1/d - 1/d_safe) * (1/d^2) * unit_r  if d < d_safe else 0
        Guarantee minimum separation distance d >= 2.5 m across all patrol crossings.
        """
        r_vec = np.asarray(p1, dtype=float) - np.asarray(p2, dtype=float)
        d = float(np.linalg.norm(r_vec))
        if 0.01 < d < self.d_safe_m:
            f_mag = self.K_REP * ((1.0 / d) - (1.0 / self.d_safe_m)) * (1.0 / d ** 2)
            return f_mag * (r_vec / d)
        return np.zeros(3)

    def _init_sensing(self):
        m = self.model
        uav_geoms = set().union(*(u["geoms"] for u in self.uavs.values()))
        self.is_obstacle = np.array([bool(m.geom_contype[g] or m.geom_conaffinity[g]) and g not in uav_geoms
                                     for g in range(m.ngeom)])
        groups = {int(m.geom_group[g]) for g in range(m.ngeom) if self.is_obstacle[g]}
        self.RF_GROUPS = np.array([1 if k in groups else 0 for k in range(6)], dtype=np.uint8)
        self.SENSE_EVERY = max(1, int(round(1.0 / (self.SENSE_HZ * m.opt.timestep))))
        self.A_BRAKE_H = self.BRAKE_FRAC * 9.81 * math.tan(self.MAX_TILT)
        self.sense_rng = np.random.default_rng([self.seed, 11])
        self.min_obstacle_clearance_m = float("inf")
        self.RF_NAMES = [f"rf_{t}{k}" for t in "hud" for k in range(8)] + ["rf_up", "rf_dn"]
        az = np.arange(self.N_SCAN) * (2.0 * math.pi / self.N_SCAN)
        self.SCAN_DIRS_BODY = np.stack([np.cos(az), np.sin(az), np.zeros_like(az)], axis=1)
        self.rf_planes = [g for g in range(m.ngeom) if self.is_obstacle[g] and m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE]
        for name, u in self.uavs.items():
            sids = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, f"{name}_{n}") for n in self.RF_NAMES]
            u["rf_sids"] = np.array(sids) if min(sids) >= 0 else None
            u["rf"] = None
            u["avoid"] = False

    def _sense(self, u):
        """
        One range-ring sample for UAV u. Sets u["rf_true"] (geometric range to the first
        obstacle per beam, inf beyond RF_RANGE_M), u["rf"] (= rf_true + N(0, RF_SIGMA_M), the
        only ranges the controller uses), u["rf_dirs"] (world beam directions), u["rf_normal"]
        (hit surface normals), u["rf_geom"] (hit geom id or -1), and updates
        min_obstacle_clearance_m (smallest true beam range, airframe centre to surface) after takeoff.
        """
        if u["rf_sids"] is None:
            return
        m, d = self.model, self.data
        sids = u["rf_sids"]
        org = d.site_xpos[sids[0]].copy()
        # levelled scan: rotated by the heading only (roll/pitch-stabilised mount, ASSUMPTION), so the plane stays at
        # rotor height while the airframe tilts 15-28 deg to accelerate; a body-fixed plane dipped 0.9 m at 3.5 m and
        # the swept-tube test below then lost the trunk
        yaw = math.atan2(d.xmat[u["bid"]][3], d.xmat[u["bid"]][0])
        cy, sy = math.cos(yaw), math.sin(yaw)
        scan = self.SCAN_DIRS_BODY @ np.array([[cy, sy, 0.0], [-sy, cy, 0.0], [0.0, 0.0, 1.0]])
        dirs = np.ascontiguousarray(np.vstack([scan, d.site_xmat[sids].reshape(-1, 3, 3)[:, :, 2]]))
        n = len(dirs)
        gid, dist, nrm = np.full(n, -1, dtype=np.int32), np.full(n, -1.0), np.zeros((n, 3))
        mujoco.mj_multiRay(m, d, org, dirs.ravel(), self.RF_GROUPS, 1, u["bid"], gid, dist, nrm.ravel(), n,
                           self.RF_RANGE_M)
        nrm = nrm.reshape(n, 3)
        # mj_multiRay's cutoff prunes by bounding sphere around the geom origin, which also drops
        # an infinite plane whose origin is farther than the cutoff: intersect planes analytically.
        for pg in self.rf_planes:
            pn = d.geom_xmat[pg].reshape(3, 3)[:, 2]
            den = dirs @ pn
            with np.errstate(divide="ignore", invalid="ignore"):
                tp = ((d.geom_xpos[pg] - org) @ pn) / den
            hit = (den < -1e-9) & (tp >= 0) & ((dist < 0) | (tp < dist))
            dist[hit], gid[hit], nrm[hit] = tp[hit], pg, pn
        g1, n1 = np.zeros(1, dtype=np.int32), np.zeros(3)
        true = np.full(n, np.inf)
        ok = (gid >= 0) & (dist <= self.RF_RANGE_M)
        direct = ok & self.is_obstacle[np.maximum(gid, 0)]
        true[direct] = dist[direct]
        gid[~ok] = -1
        for i in np.nonzero(ok & ~direct)[0]:                # only beams whose first hit is see-through
            g, tot = int(gid[i]), float(dist[i])
            for _ in range(6):                       # look through markers / visual-only / other UAV
                if g < 0 or tot > self.RF_RANGE_M or self.is_obstacle[g]:
                    break
                dd = mujoco.mj_ray(m, d, org + dirs[i] * (tot + 1e-3), dirs[i], self.RF_GROUPS, 1, u["bid"], g1, n1)
                if dd >= 0:
                    g, tot = int(g1[0]), tot + 1e-3 + dd
                    nrm[i] = n1
                else:
                    g = -1
            if g >= 0 and self.is_obstacle[g] and tot <= self.RF_RANGE_M:
                true[i], gid[i] = tot, g
            else:
                gid[i] = -1
        gid[~np.isfinite(true)] = -1
        flip = np.einsum("ij,ij->i", nrm, dirs) > 0          # normal must face the UAV
        nrm[flip] *= -1.0
        u["rf_true"], u["rf_dirs"], u["rf_geom"], u["rf_normal"] = true, dirs, gid, nrm
        u["rf"] = true + self.sense_rng.normal(0.0, self.RF_SIGMA_M, n)
        # per-beam constraint geometry for _avoid_obstacles (only beams close enough to matter)
        dn = np.where(np.isfinite(u["rf"]), u["rf"], np.inf) * np.maximum(np.einsum("ij,ij->i", -dirs, nrm), 1e-9)
        vert = np.abs(nrm[:, 2]) > 0.7
        reach = np.where(vert, self.D_STOP_V + self.V_MAX_Z * self.T_REACT + self.V_MAX_Z ** 2 / (2 * self.A_BRAKE_V),
                         self.D_STOP_H + self.cruise_speed_mps * self.T_REACT
                         + self.cruise_speed_mps ** 2 / (2 * self.A_BRAKE_H))
        # a wall-like (non-horizontal) surface is a lateral threat only where the beam met it within
        # H_BAND of the rotor plane: a building face hit 0.9 m BELOW a UAV cruising over its roof
        # is not in the way (the roof top itself is a horizontal surface, handled vertically)
        dz = np.abs(dirs[:, 2] * np.where(np.isfinite(u["rf"]), u["rf"], 0.0))
        keep = (dn < reach) & (vert | (dz <= self.H_BAND))
        # the tangent plane is a threat only where the airframe could meet THIS surface patch: the hit point must lie
        # within D_STOP_H of the line through the airframe centre along the surface normal. With the 120-beam scan an
        # oblique beam otherwise reports the end face of a pilaster beside a corridor as an infinite wall across it
        # (measured: Alpha held at x = -1.9 m in the south corridor). A wall straight ahead is still seen by the beam
        # nearest its normal (3 deg spacing), and a thin obstacle ahead by the swept-tube layer.
        hp = dirs * np.where(np.isfinite(u["rf"]), u["rf"], 0.0)[:, None]
        lat = np.linalg.norm(hp - np.einsum("ij,ij->i", hp, nrm)[:, None] * nrm, axis=1)
        keep &= lat < self.D_STOP_H
        u["rf_active"] = [(float(dn[i]), nrm[i], bool(vert[i])) for i in np.nonzero(keep)[0]]
        fin = np.isfinite(u["rf"]) & (u["rf"] < self.D_STOP_H + self.cruise_speed_mps * self.T_REACT
                                      + self.cruise_speed_mps ** 2 / (2 * self.A_BRAKE_H))
        u["rf_pts"] = dirs[fin] * u["rf"][fin, None]          # hit points relative to the airframe centre
        if u["phase"] != "takeoff":
            self.min_obstacle_clearance_m = min(self.min_obstacle_clearance_m, float(true.min()))

    def _avoid_obstacles(self, u, v_cmd):
        """Reactive FR-18 layer on the velocity command (after the separation layer); see class constants."""
        u["avoid"] = False
        if u.get("rf") is None or u["phase"] == "takeoff":
            return v_cmd
        for d_n, nv, vertical in u["rf_active"]:              # d_n: distance to the hit surface
            d_st, a = (self.D_STOP_V, self.A_BRAKE_V) if vertical else (self.D_STOP_H, self.A_BRAKE_H)
            approach = -float(v_cmd @ nv)
            if approach <= 0.0:
                continue
            T = self.T_REACT
            allowed = (a * (-T + math.sqrt(T * T + 2.0 * (d_n - d_st) / a)) if d_n > d_st
                       else max(-self.BACKOFF_MPS, (d_n - d_st) / T))      # continuous back-off inside D_STOP
            if approach > allowed:
                v_cmd = v_cmd + (approach - allowed) * nv
                # anti-windup: drop the velocity integrator's push toward the surface, or the
                # stored integral carries the airframe past D_STOP and it pumps in front of it
                wind_in = -float(u["i_vel"] @ nv)
                if wind_in > 0.0:
                    u["i_vel"] = u["i_vel"] + wind_in * nv
                u["avoid"] = True
        # Swept-tube point layer (G-06). The tangent plane of a beam that grazes a THIN convex obstacle (a 0.24 m
        # trunk) is nearly parallel to the flight path, so the plane rule above lets the airframe slide into it.
        # Every hit point lying ahead inside the tube of radius D_STOP_H around the commanded direction is
        # therefore also treated as a point obstacle: the speed toward it is capped by the same braking rule at
        # distance |p| - D_STOP_H. A wall beside a corridor is outside the tube, so corridor flight is unaffected;
        # the component of v_cmd across the line to the point is kept, so the airframe slides round the trunk.
        pts = u.get("rf_pts")
        sp = float(np.linalg.norm(v_cmd))
        if pts is not None and len(pts) and sp > 1e-6:
            vh = v_cmd / sp
            along = pts @ vh
            lat2 = np.einsum("ij,ij->i", pts, pts) - along * along
            R = self.D_STOP_H
            for k in np.nonzero((along > 0.0) & (lat2 < R * R))[0]:
                rng_k = float(np.linalg.norm(pts[k]))
                ph = pts[k] / rng_k
                approach = float(v_cmd @ ph)
                if approach <= 0.0:
                    continue
                d_k, a, T = rng_k - R, self.A_BRAKE_H, self.T_REACT
                allowed = (a * (-T + math.sqrt(T * T + 2.0 * d_k / a)) if d_k > 0.0
                           else max(-self.BACKOFF_MPS, d_k / T))
                if approach > allowed:
                    cut = approach - allowed
                    v_cmd = v_cmd - cut * ph
                    wind_in = float(u["i_vel"] @ ph)
                    if wind_in > 0.0:
                        u["i_vel"] = u["i_vel"] - wind_in * ph
                    # go round: slide horizontally away from the point (right-hand when it is dead ahead)
                    side = -(pts[k] - along[k] * vh)
                    side[2] = 0.0
                    ns = float(np.linalg.norm(side))
                    side = side / ns if ns > 0.05 else np.array([vh[1], -vh[0], 0.0]) / max(1e-6, math.hypot(vh[0], vh[1]))
                    v_cmd = v_cmd + min(cut, self.BACKOFF_MPS) * side
                    u["avoid"] = True
        return v_cmd

    SEP_MARGIN_M = 0.4    # m, design: the separation governor holds the pair this far outside d_safe (velocity-loop lag)
    SIDE_CLEAR_M = 1.5    # m, design: a sidestep is not taken toward a surface closer than this (range ring)

    def _side_blocked(self, u, side):
        """True when a range-ring beam within 45 deg of the horizontal direction `side` sees a surface
        closer than SIDE_CLEAR_M (the sidestep would only push the airframe into the FR-18 layer)."""
        rf, dirs = u.get("rf"), u.get("rf_dirs")
        if rf is None or dirs is None:
            return False
        near = (dirs @ side > 0.7) & (rf < self.SIDE_CLEAR_M)
        return bool(np.any(near))

    def _waypoint(self, u):
        wp, _ = u["route"][u["idx"] % len(u["route"])]
        if u["phase"] == "takeoff":
            z = self.TRANSIT_ALT if self.TRANSIT_ALT > 0 else wp[2]
            return np.array([*u["home"], z])
        if u["phase"] == "transit" and self.TRANSIT_ALT > 0:
            return np.array([wp[0], wp[1], self.TRANSIT_ALT])
        return wp.copy()

    def _flight_target(self, u):
        """Position the controller flies to: the surveillance FSM override (TRACK standoff point or
        RETURN_TO_PATROL breadcrumb) when set, otherwise the patrol route waypoint."""
        return u["override"].copy() if u["override"] is not None else self._waypoint(u)

    PHASE_FSM = {"takeoff": "TAKEOFF", "transit": "TRANSIT", "descend": "DESCEND", "patrol": "PATROL"}

    def _set_phase(self, u, phase):
        u["phase"] = phase
        u["fsm"] = self.PHASE_FSM[phase]     # the surveillance FSM (contract E) overrides u["fsm"] from PATROL
        u["events"].append(f"phase:{phase}")

    def _advance_mission(self, u, pos, t):
        if "home" not in u:
            u["home"] = pos[:2].copy()
        wp = self._waypoint(u)
        if u["phase"] == "takeoff":
            if abs(pos[2] - wp[2]) < 0.4:
                self._set_phase(u, "transit")
        elif u["phase"] == "transit":
            if np.linalg.norm(pos[:2] - wp[:2]) < self.ARRIVE_R:
                self._set_phase(u, "descend")
        elif u["phase"] == "descend":
            if abs(pos[2] - wp[2]) < 0.5:
                self._set_phase(u, "patrol")
        elif np.linalg.norm(pos - wp) < self.ARRIVE_R:
            u["leg"] = (wp.copy(), t)                          # timed waypoint reference re-anchors here
            _, cp = u["route"][u["idx"] % len(u["route"])]
            if cp is not None:
                self.visits[cp].append(t)
                u["events"].append(f"visit:{cp}")
            u["idx"] += 1
            if u["idx"] % len(u["route"]) == 0:
                u["laps"] += 1

    def _reference(self, u, pos):
        """
        Reference position used for the tracking error (telemetry xref/yref/zref, ex/ey/ez).
        PATROL phase: the orthogonal projection of the UAV position onto the active route
          leg (previous waypoint -> current waypoint), clamped to the leg. The error is
          therefore the cross-track + vertical deviation from the planned path; progress
          ALONG the leg is not counted as error (there is no timed trajectory to lag).
        Other phases (takeoff / transit / descend) and surveillance diversions (TRACK,
        RETURN_TO_PATROL): the commanded target itself.
        """
        if u["override"] is not None:
            return u["override"].copy()
        if u["phase"] != "patrol":
            return self._waypoint(u)
        n = len(u["route"])
        b = u["route"][u["idx"] % n][0]
        a = u["route"][(u["idx"] - 1) % n][0]
        ab = b - a
        L2 = float(ab @ ab)
        s = min(1.0, max(0.0, float((pos - a) @ ab) / L2)) if L2 > 1e-9 else 0.0
        return a + s * ab

    def _waypoint_reference(self, u, pos, t):
        """
        G-09 timed reference on the COMMANDED waypoint path (independent of where the UAV is): it leaves
        the last accepted waypoint when that waypoint is accepted and moves toward the current commanded
        waypoint at cruise_speed_mps, stopping on it. Along-track lag (corner slow-down, separation
        governor, FR-18 braking) therefore counts as error, unlike the cross-track reference of
        _reference(). Re-anchored at the UAV's position whenever patrol flight (re)starts (first PATROL
        step, end of a surveillance diversion), so a diversion never accumulates as error.
        """
        wp = self._waypoint(u)
        if u.get("leg") is None:
            u["leg"] = (pos.copy(), t)
        a, t0 = u["leg"]
        ab = wp - a
        L = float(np.linalg.norm(ab))
        s = min(L, self.cruise_speed_mps * (t - t0))
        return a + ab * (s / L) if L > 1e-9 else wp

    def _control(self, u, other_pos, dt):
        q = self.data.qpos[u["qadr"]:u["qadr"] + 7]
        v = self.data.qvel[u["vadr"]:u["vadr"] + 6]
        pos, quat, vel, omega = q[:3].copy(), q[3:7].copy(), v[:3].copy(), v[3:6].copy()
        if "home" not in u:
            u["home"] = pos[:2].copy()
        target = self._flight_target(u)

        # outer loop: position -> speed-limited velocity command
        v_cmd = self.KP_POS * (target - pos)
        nxy = np.linalg.norm(v_cmd[:2])
        if nxy > self.cruise_speed_mps:
            v_cmd[:2] *= self.cruise_speed_mps / nxy
        v_cmd[2] = np.clip(v_cmd[2], -self.V_MAX_Z, self.V_MAX_Z)
        if u["phase"] == "takeoff":
            v_cmd[:2] *= 0.0                                   # climb straight up off the dock

        # tactical separation (G-07): a KINEMATIC closing-speed governor, the same braking model as FR-18
        # with the other UAV as the obstacle. Each UAV may close on the other at no more than HALF the
        # closing speed from which the pair can still stop SEP_MARGIN_M outside d_safe after a reaction
        # delay T_REACT, both braking at A_BRAKE_H (relative deceleration 2 A_BRAKE_H):
        #     V_c T_REACT + V_c^2 / (4 A_BRAKE_H) = d - (d_safe + SEP_MARGIN_M)
        # Inside d_safe + SEP_MARGIN_M the allowance turns into a back-off (both UAVs open the gap).
        # Holds for every geometry (head-on, crossing, catch-up, a returning tracker meeting the
        # patrol flow), in 3D, so an altitude layer simply shows up as a larger d. The old linear cap
        # over D_WARN let an indoor head-on reach 0.96 m (5 m/s closing, 2 m of warning). When the cap
        # bites, a right-hand sidestep (scene 'sidestep', m/s; horizontal right of the line of sight)
        # makes a head-on pair pass instead of deadlocking; a UAV whose right side is blocked by the
        # range ring (FR-18) does not sidestep and the other UAV's sidestep resolves the encounter.
        r = pos - np.asarray(other_pos)
        d = float(np.linalg.norm(r))
        u["governor"] = False
        if self.layered_separation and d > 1e-6:
            r_hat = r / d
            toward = float(np.dot(v_cmd, -r_hat))
            d_hold = self.d_safe_m + self.SEP_MARGIN_M
            a_rel, T = 2.0 * self.A_BRAKE_H, self.T_REACT
            if d > d_hold:
                allowed = 0.5 * a_rel * (-T + math.sqrt(T * T + 2.0 * (d - d_hold) / a_rel))
            else:
                allowed = 0.5 * max(-self.BACKOFF_MPS, (d - d_hold) / T)
            # Take up the other UAV's shortfall: when its MEASURED speed toward this UAV exceeds its half of the
            # allowance (its FR-18 layer pins it against a wall and cancels its back-off, or its velocity loop
            # lags), this UAV yields the difference, so the PAIR's closing speed stays within the allowance.
            # Measured: interior offset_ring, a crossing next to a corridor wall, Alpha's FR-18 layer turned a
            # 0.25 m/s back-off into 0.67 m/s toward Bravo and the pair reached 2.43 m (ablation separation/on s9).
            other = self.uavs["bravo" if u["name"] == "alpha" else "alpha"]
            v_other = float(self.data.qvel[other["vadr"]:other["vadr"] + 3] @ r_hat)    # >0: other closes on u
            if v_other > allowed:
                allowed = max(-self.cruise_speed_mps, 2.0 * allowed - v_other)
            if toward > allowed:
                v_cmd = v_cmd + (toward - allowed) * r_hat
                wind_in = -float(u["i_vel"] @ r_hat)             # anti-windup toward the other UAV
                if wind_in > 0.0:
                    u["i_vel"] = u["i_vel"] + wind_in * r_hat
                rh = np.array([-r_hat[1], r_hat[0], 0.0])        # right of the line of sight
                nh = float(np.linalg.norm(rh))
                if nh > 0.2 and not self._side_blocked(u, rh / nh):
                    v_cmd = v_cmd + self.SIDESTEP * rh / nh
                u["governor"] = True

        # FR-18: reactive obstacle avoidance from the range ring, layered after separation
        if self.obstacle_avoidance:
            v_cmd = self._avoid_obstacles(u, v_cmd)
        else:
            u["avoid"] = False                                 # ablation: FR-18 layer off

        # middle loop: PI on velocity (integral rejects steady drafts) + APF repulsion
        e_v = v_cmd - vel
        u["i_vel"] = np.clip(u["i_vel"] + e_v * dt, -self.I_CLAMP, self.I_CLAMP)
        f_rep = self.compute_apf_separation(pos, other_pos)
        u["apf_N"] = float(np.linalg.norm(f_rep))
        acc = self.KP_VEL * e_v + self.KI_VEL * u["i_vel"] + f_rep / u["mass"]

        # flat-output inversion: desired acceleration -> thrust + tilt, valid for any yaw
        rpy = self._quat_to_rpy(quat)
        u["rpy"] = rpy
        a_lat = 9.81 * math.tan(self.MAX_TILT)
        n_lat = np.linalg.norm(acc[:2])
        if n_lat > a_lat:
            acc[:2] *= a_lat / n_lat
        thrust = u["mass"] * (9.81 + acc[2]) / max(math.cos(rpy[0]) * math.cos(rpy[1]), 0.5)
        thrust = float(np.clip(thrust, 0.0, 4 * self.F_MAX))
        yaw = rpy[2]
        pitch_d = (acc[0] * math.cos(yaw) + acc[1] * math.sin(yaw)) / 9.81
        roll_d = (acc[0] * math.sin(yaw) - acc[1] * math.cos(yaw)) / 9.81
        raw = np.clip([roll_d, pitch_d], -self.MAX_TILT, self.MAX_TILT)
        step = self.MAX_TILT_RATE * dt
        u["tilt_cmd"] += np.clip(raw - u["tilt_cmd"], -step, step)

        # heading reference, slewed at 90 deg/s
        mode = self.YAW_MODE[u["name"]]
        yaw_ref = u["yaw_cmd"]
        if u["look_at"] is not None and mode in (1, 2):          # TRACK: forward camera faces the target
            if np.linalg.norm(u["look_at"][:2] - pos[:2]) > 0.8:
                yaw_ref = math.atan2(u["look_at"][1] - pos[1], u["look_at"][0] - pos[0])
        elif mode == 1 and np.linalg.norm(target[:2] - pos[:2]) > 0.8 and u["phase"] != "takeoff":
            yaw_ref = math.atan2(target[1] - pos[1], target[0] - pos[0])
        elif mode == 2 and u["phase"] != "takeoff":
            yaw_ref = math.atan2(pos[1] - self.yaw_centre[1], pos[0] - self.yaw_centre[0])
        elif mode == 0:
            yaw_ref = 0.0
        dyaw = math.atan2(math.sin(yaw_ref - u["yaw_cmd"]), math.cos(yaw_ref - u["yaw_cmd"]))
        u["yaw_cmd"] += max(-self.YAW_RATE * dt, min(self.YAW_RATE * dt, dyaw))

        # inner loop: attitude PD with gyroscopic feed-forward (I w_dot + w x I w = tau)
        e_att = np.array([u["tilt_cmd"][0] - rpy[0], u["tilt_cmd"][1] - rpy[1],
                          math.atan2(math.sin(u["yaw_cmd"] - yaw), math.cos(u["yaw_cmd"] - yaw))])
        tau = u["I"] @ (self.KP_ATT * e_att - self.KD_ATT * omega) + np.cross(omega, u["I"] @ omega)
        u["u"] = self.mix(thrust, tau)
        for a, f in zip(u["act"], u["u"]):
            self.data.ctrl[a] = f
        # body torque the clipped rotor forces actually produce (inverse of mix, see its docstring)
        f0, f1, f2, f3 = u["u"]
        l, k = self.ARM_L, self.K_Q
        tb = (l * (f2 - f3), l * (f1 - f0), k * (f0 + f1 - f2 - f3))
        self._torque_n2m2s += (tb[0] * tb[0] + tb[1] * tb[1] + tb[2] * tb[2]) * dt

        # rotor momentum-theory power, integrated
        area = math.pi * self.ROTOR_R ** 2
        u["energy_j"] += float(np.sum(u["u"] ** 1.5)) / (math.sqrt(2 * self.RHO * area) * self.ETA) * dt
        return pos

    def _gust_step(self, dt):
        noise = self.rng.standard_normal(3) * np.array([1.0, 1.0, 0.35])
        self.wind += self.gust_theta * (self.wind_mean - self.wind) * dt + self.gust_sigma * math.sqrt(dt) * noise
        self.model.opt.wind[:] = self.wind

    def revisit_intervals(self, route="patrol_cp"):
        """Worst-case gap between consecutive services of each checkpoint on a route, both UAVs merged."""
        gaps = []
        for name, ts in self.visits.items():
            if not name.startswith(route):
                continue
            ts = sorted(ts)
            gaps += [b - a for a, b in zip(ts, ts[1:])]
        return gaps

    def coverage(self, route):
        """Fraction of a route's checkpoints serviced at least once."""
        names = [n for n in self.visits if n.startswith(route)]
        return sum(1 for n in names if self.visits[n]) / len(names) if names else float("nan")

    def patrol_metrics(self):
        """Contract-A revisit / cycle / coverage columns -- the SAME function scores the guard."""
        return checkpoint_metrics(self.visits)
    # ======================================================================
    # <<< E043 MUAAZ <<<
    # ======================================================================

    # ======================================================================
    # >>> E051 ADITYA -- COMPUTER VISION  >>>
    # ======================================================================
    # Camera model (models/uav_fleet.xml: 640 x 480, fovy 56.14 deg).
    IMG_W_PX, IMG_H_PX = 640, 480
    CAM_FOVY_DEG = 56.14
    # Target colour model: RGB of material "intruder" in models/common.xml (0.90, 0.10, 0.10).
    # This is a colour SPECIFICATION (what the detector looks for), not simulator state.
    INTRUDER_RGB = (0.90, 0.10, 0.10)
    HSV_HUE_TOL = 6          # OpenCV hue units (0..179, 2 deg each): +-12 deg around red; the lobby floor sits at ~9
    HSV_SAT_FRAC = 0.75      # S_min = 0.75 * S_nominal(226) = 169. Measured: lit intruder S = 227, the terracotta VIP-lounge
                             # floor S = 165-166 (0.66 -> S_min 149 let the floor merge with the intruder blob)
    HSV_VAL_MIN = 40         # V_min (0..255): sensor-noise floor; this is the knob that decides twilight misses
    MIN_BLOB_AREA_PX = 16    # contour area below this is noise (about a 4 x 4 px patch)
    # Low-light auto-exposure (the "twilight exposure fix"; self.auto_exposure, default on). A digital gain on
    # the HSV value channel only, gain = clip(AE_TARGET_V / P_AE_PCTL(V), 1, AE_GAIN_MAX), applied before the
    # V threshold. Hue and saturation are untouched, so the colour test is unchanged; a frame whose bright
    # pixels already reach AE_TARGET_V gets gain 1 (normal light is processed exactly as before).
    AE_TARGET_V = 200        # design: bring the frame's highlights to ~80 % of full scale
    AE_PCTL = 99.0           # design: highlight percentile that sets the gain (ignores a few hot pixels)
    AE_GAIN_MAX = 8.0        # design: cap, so a black frame does not turn sensor noise into blobs
    ASSUMED_TARGET_CENTROID_Z = 0.85   # m, mid-height of a 1.7 m person; ASSUMPTION used for the ground-plane step
    HANDOFF_HYST_M = 2.0     # a UAV must be this much closer than the current tracker before control moves
    HANDOFF_EDGE_PX = 40     # target must be this far inside the image to count as "in the footprint"

    @staticmethod
    def focal_length_px(fovy_deg=56.14, height_px=480):
        """Pinhole focal length from the vertical field of view: f = (H/2) / tan(fovy/2) -> 449.9 px, i.e. 450."""
        return 0.5 * height_px / math.tan(math.radians(fovy_deg) / 2.0)

    @classmethod
    def _hsv_bands(cls):
        """HSV acceptance bands derived from the intruder colour (red hue wraps, so two bands)."""
        import cv2
        px = np.array([[[round(255 * c) for c in cls.INTRUDER_RGB]]], dtype=np.uint8)
        h0, s0, v0 = (int(x) for x in cv2.cvtColor(px, cv2.COLOR_RGB2HSV)[0, 0])
        s_min = int(cls.HSV_SAT_FRAC * s0)
        lo_h, hi_h = h0 - cls.HSV_HUE_TOL, h0 + cls.HSV_HUE_TOL
        bands = [((max(0, lo_h), s_min, cls.HSV_VAL_MIN), (min(179, hi_h), 255, 255))]
        if lo_h < 0:                                      # wrap-around band at the top of the hue circle
            bands.append(((180 + lo_h, s_min, cls.HSV_VAL_MIN), (179, 255, 255)))
        return bands

    def detect_intruder_hsv(self, rgb):
        """
        Contract C: detect the intruder in a 640x480 RGB frame. Uses ONLY the pixels passed in.
        Pipeline: RGB -> HSV -> red-band threshold -> 3x3 open (speckle) -> 5x5 close (fill gaps)
        -> external contours -> largest blob.
        Returns dict(detected, bbox=(x1, y1, x2, y2) pixel edges, centroid=(u, v), latency_ms).
        """
        import cv2
        t0 = time.perf_counter()
        frame = np.ascontiguousarray(rgb, dtype=np.uint8)
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        gain = 1.0
        if getattr(self, "auto_exposure", True):
            hi = float(np.percentile(hsv[:, :, 2], self.AE_PCTL))
            gain = min(self.AE_GAIN_MAX, max(1.0, self.AE_TARGET_V / max(hi, 1.0)))
            if gain > 1.0:
                hsv[:, :, 2] = np.clip(hsv[:, :, 2].astype(np.float32) * gain, 0, 255).astype(np.uint8)
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        for lo, hi in self._hsv_bands():
            mask |= cv2.inRange(hsv, np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        out = {"detected": False, "bbox": None, "centroid": None}
        if contours:
            best = max(contours, key=cv2.contourArea)
            if cv2.contourArea(best) >= self.MIN_BLOB_AREA_PX:
                x, y, w, h = cv2.boundingRect(best)
                m = cv2.moments(best)
                if m["m00"] > 0:
                    centroid = (m["m10"] / m["m00"], m["m01"] / m["m00"])
                else:
                    centroid = (x + w / 2.0, y + h / 2.0)
                out = {"detected": True, "bbox": (x, y, x + w, y + h), "centroid": centroid}
        out["latency_ms"] = (time.perf_counter() - t0) * 1000.0
        out["exposure_gain"] = gain
        return out

    def inverse_pinhole_projection(self, u_px, v_px, uav_pos, focal_length_px=450.0,
                                   cam_xpos=None, cam_xmat=None, ground_z=0.0):
        """
        Contract C: image pixel -> world point on the plane z = ground_z. Principal point (320, 240).
        Without a camera pose: nadir closed form (camera at uav_pos looking straight down, image-up = +y):
            X = X_uav + (u - u0) * h / f,   Y = Y_uav - (v - v0) * h / f,   h = Z_uav - ground_z.
        With a pose (MuJoCo data.cam_xpos / data.cam_xmat, camera looks along its own -z, x right, y up):
            d_cam = ((u - u0) / f, -(v - v0) / f, -1);  d_w = R d_cam;  P = C + t d_w with t = (ground_z - C_z) / d_w_z.
        Returns None when the ray does not reach the plane (at or above the horizon).
        """
        u0, v0 = self.IMG_W_PX / 2.0, self.IMG_H_PX / 2.0
        if cam_xpos is None or cam_xmat is None:
            h = float(uav_pos[2]) - ground_z
            if h <= 0.0:
                return None
            return np.array([uav_pos[0] + (u_px - u0) * h / focal_length_px,
                             uav_pos[1] - (v_px - v0) * h / focal_length_px,
                             ground_z])
        c = np.asarray(cam_xpos, dtype=float).reshape(3)
        r = np.asarray(cam_xmat, dtype=float).reshape(3, 3)
        d_w = r @ np.array([(u_px - u0) / focal_length_px, -(v_px - v0) / focal_length_px, -1.0])
        if d_w[2] >= -1e-9:
            return None
        t = (ground_z - c[2]) / d_w[2]
        if t <= 0.0:
            return None
        return c + t * d_w

    def _target_in_view(self, target_xy, state):
        """True when the target (at assumed centroid height) projects inside the image, HANDOFF_EDGE_PX from the border."""
        if isinstance(state, dict):
            pos = np.asarray(state["pos"], dtype=float)
            cam_xpos = state.get("cam_xpos", pos)
            cam_xmat = state.get("cam_xmat", np.eye(3))        # identity = nadir camera at yaw 0
        else:
            cam_xpos, cam_xmat = np.asarray(state, dtype=float), np.eye(3)
        p = np.array([target_xy[0], target_xy[1], self.ASSUMED_TARGET_CENTROID_Z])
        pc = np.asarray(cam_xmat, dtype=float).reshape(3, 3).T @ (p - np.asarray(cam_xpos, dtype=float))
        depth = -pc[2]
        if depth <= 0.1:
            return False
        f = self.focal_length_px(self.CAM_FOVY_DEG, self.IMG_H_PX)
        u = self.IMG_W_PX / 2.0 + f * pc[0] / depth
        v = self.IMG_H_PX / 2.0 - f * pc[1] / depth
        e = self.HANDOFF_EDGE_PX
        return e <= u <= self.IMG_W_PX - e and e <= v <= self.IMG_H_PX - e

    def select_tracking_uav(self, target_xy, uav_states):
        """
        Contract C: target handoff. uav_states = {name: pos(3)} or {name: dict(pos, [cam_xpos, cam_xmat])}.
        Rule: among UAVs whose camera currently holds the target pick the horizontally nearest; if none holds it,
        pick the nearest overall. Hysteresis: the current tracker (kept lazily in self._trk_uav) is retained while it
        still holds the target and nobody is more than HANDOFF_HYST_M closer, so a target near the midpoint cannot
        make control ping-pong. Uses only UAV states and the image-derived target estimate, never intruder truth.
        """
        cur = getattr(self, "_trk_uav", None)
        if target_xy is None:
            return cur
        if not uav_states:
            raise ValueError("uav_states is empty")
        tx, ty = float(target_xy[0]), float(target_xy[1])
        dist, holds = {}, {}
        for name in sorted(uav_states):
            s = uav_states[name]
            pos = np.asarray(s["pos"] if isinstance(s, dict) else s, dtype=float)
            dist[name] = math.hypot(pos[0] - tx, pos[1] - ty)
            holds[name] = self._target_in_view((tx, ty), s)
        pool = [n for n in dist if holds[n]] or list(dist)
        best = min(pool, key=lambda n: (dist[n], n))
        if cur in pool and dist[cur] - dist[best] <= self.HANDOFF_HYST_M:
            best = cur
        self._trk_uav = best
        return best
    # ======================================================================
    # <<< E051 ADITYA <<<
    # ======================================================================

    # ======================================================================
    # >>> E075 ZAID -- GEOFENCING & ALERTS  >>>
    # ======================================================================
    # Geofence design parameters. Every value below is a DESIGN CHOICE or an
    # ASSUMPTION (stated range), not a measured result.
    GEOFENCE_BUFFER_M = 5.0          # tier 2 band: within 5 m of the zone edge (guide value)
    GEOFENCE_ADVISORY_M = 15.0       # tier 1 band: within 15 m of the zone edge. ASSUMPTION, range 10-25 m
    GEOFENCE_EXIT_MARGIN_M = 2.0     # hysteresis: a tier is only left once the point is this far past its threshold
    GEOFENCE_CONFIRM_N = 5           # hysteresis: tier 3 needs this many consecutive inside readings (0.5 s at 10 Hz,
                                     # so cadence dependent). Until confirmed the reported tier is 2.
    GEOFENCE_NOISE_SIGMA_M = 1.5     # per-axis position noise. ASSUMPTION, range 0.5-3.0 m (not sourced)
    GEOFENCE_RTH_LOSS_S = 2.5        # telemetry loss that triggers return-to-home (project requirement)
    GEOFENCE_STATUS = {
        0: "STATUS_0_ROUTINE_CLEAR",
        1: "STATUS_1_PERIMETER_ADVISORY",
        2: "STATUS_2_RESTRICTED_ZONE_WARNING",
        3: "STATUS_3_CRITICAL_GEOFENCE_BREACH",
    }

    def _geofence_polygon(self):
        """Corner list (4 x 2) of the 'substation_zone' box, read from the scene geom (cached)."""
        poly = getattr(self, "_geofence_poly", None)
        if poly is None:
            gid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "substation_zone")
            if gid < 0:
                raise ValueError("scene has no geom named 'substation_zone'")
            scratch = mujoco.MjData(self.model)
            mujoco.mj_forward(self.model, scratch)          # world pose incl. any yaw of the box
            c = scratch.geom_xpos[gid]
            R = scratch.geom_xmat[gid].reshape(3, 3)
            hx, hy = self.model.geom_size[gid][:2]
            local = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
            poly = [tuple((c + R @ np.array([lx, ly, 0.0]))[:2]) for lx, ly in local]
            self._geofence_poly = poly
        return poly

    @staticmethod
    def _point_in_polygon(px, py, poly):
        """Even-odd ray casting: cast a ray toward +x and count edge crossings."""
        inside = False
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if (y1 > py) != (y2 > py):                       # edge straddles the ray's y
                x_cross = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if x_cross > px:
                    inside = not inside
        return inside

    @staticmethod
    def _dist_to_polygon_edges(px, py, poly):
        """Smallest distance from the point to any polygon edge segment."""
        best = float("inf")
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            s = 0.0 if L2 == 0.0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
            best = min(best, math.hypot(px - (x1 + s * dx), py - (y1 + s * dy)))
        return best

    def geofence_signed_distance(self, xy):
        """Signed distance (m) to the zone boundary: negative or zero inside, positive outside."""
        poly = self._geofence_polygon()
        px, py = float(xy[0]), float(xy[1])
        d = self._dist_to_polygon_edges(px, py, poly)
        if d <= 1e-9 or self._point_in_polygon(px, py, poly):
            return -d
        return d

    def _geofence_tier_of(self, d):
        if d <= 0.0:
            return 3
        if d <= self.GEOFENCE_BUFFER_M:
            return 2
        if d <= self.GEOFENCE_ADVISORY_M:
            return 1
        return 0

    def geofence_raw_tier(self, target_coords):
        """Tier from the position alone: no hysteresis, no state, no logging."""
        return self._geofence_tier_of(self.geofence_signed_distance(target_coords))

    def reset_geofence_state(self):
        self._geofence_tier = 0
        self._geofence_streak = 0
        self.geofence_events = []

    def _geofence_scene_key(self):
        return "interior" if "interior" in str(self.scene_name).lower() else "exterior"

    def evaluate_geofence_status(self, target_coords):
        """
        4-tier restricted-zone geofence on the polygon of the scene geom 'substation_zone'
        (exterior: electrical substation; interior: VIP Lounge). Footprint test only (z ignored).
          tier 0 ROUTINE_CLEAR        farther than GEOFENCE_ADVISORY_M from the zone edge
          tier 1 PERIMETER_ADVISORY   within GEOFENCE_ADVISORY_M
          tier 2 RESTRICTED_WARNING   within GEOFENCE_BUFFER_M (5 m)
          tier 3 CRITICAL_BREACH      inside the polygon (ray casting)
        Hysteresis (self.geofence_hysteresis, default True) has two parts. Exit margin: a tier is
        left only when the point is GEOFENCE_EXIT_MARGIN_M beyond the threshold that entered it
        (stops flapping on re-entry). Dwell: tiers 1 and 2 are entered at once, but tier 3 needs
        GEOFENCE_CONFIRM_N consecutive inside readings (one noisy sample must not raise a breach);
        until then the tier reported is 2. State is kept lazily on self. Tier changes are appended
        to self.geofence_events for the breach log. Returns (status_str, tier).
        """
        if not hasattr(self, "_geofence_tier"):
            self.reset_geofence_state()
        if target_coords is None:
            self._geofence_tier = 0
            self._geofence_streak = 0
            return self.GEOFENCE_STATUS[0], 0
        d = self.geofence_signed_distance(target_coords)
        raw = self._geofence_tier_of(d)
        cur = self._geofence_tier
        if not getattr(self, "geofence_hysteresis", True):
            new = raw
        else:
            self._geofence_streak = self._geofence_streak + 1 if raw == 3 else 0
            cand = 2 if (raw == 3 and cur < 3 and self._geofence_streak < self.GEOFENCE_CONFIRM_N) else raw
            new = cand if cand >= cur else None
        if new is None:                                                # de-escalate only past the exit margin
            new = min(cur, self._geofence_tier_of(d - self.GEOFENCE_EXIT_MARGIN_M))
        if new != cur:
            pos = [float(v) for v in target_coords] + [0.0] * (3 - len(target_coords))
            last = getattr(self, "_geofence_last_noisy", None)
            noisy = last is not None and np.array_equal(np.asarray(target_coords, dtype=float), last)
            self.geofence_events.append({
                "timestamp_s": round(float(self.current_time_s), 3),
                "scene": self._geofence_scene_key(),
                "position": [round(v, 3) for v in pos[:3]],
                "tier": int(new),
                "status": self.GEOFENCE_STATUS[new],
                "event": "escalate" if new > cur else "de-escalate",
                "noisy": bool(noisy),
            })
        self._geofence_tier = new
        return self.GEOFENCE_STATUS[new], new

    def reseed_geofence_noise(self, seed):
        """Own RNG stream, so geofence noise never perturbs the gust generator in self.rng."""
        self._geofence_rng = np.random.default_rng([int(seed), 75])

    def inject_position_noise(self, pos, sigma_m=None):
        """Add zero-mean Gaussian noise (std sigma_m per axis, x and y only) to a position.
        sigma_m=None uses GEOFENCE_NOISE_SIGMA_M (ASSUMPTION 1.5 m, range 0.5-3.0 m).
        sigma_m=0 returns the position unchanged (noise off). The noisy sample is remembered so
        the breach log can flag it."""
        sigma = self.GEOFENCE_NOISE_SIGMA_M if sigma_m is None else float(sigma_m)
        out = np.array(pos, dtype=float)
        if sigma > 0.0:
            if getattr(self, "_geofence_rng", None) is None:
                self.reseed_geofence_noise(getattr(self, "seed", 0))
            out[:2] += self._geofence_rng.normal(0.0, sigma, size=2)
            self._geofence_last_noisy = out.copy()
        return out

    def write_geofence_breach_log(self, path=None, extra=None):
        """Write self.geofence_events as JSON to analytics/geofence_breach_log_<scene>.json."""
        import json
        scene = self._geofence_scene_key()
        if path is None:
            path = os.path.join(ROOT, "analytics", f"geofence_breach_log_{scene}.json")
        doc = {"scene": scene, "events": list(getattr(self, "geofence_events", []))}
        doc.update(extra or {})
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        return path

    def telemetry_link_ok(self, t):
        """True when the telemetry link is up at sim time t. Outages come from
        self.telemetry_loss_windows = [(t_start, t_end), ...] (empty by default: link always up)."""
        for t0, t1 in getattr(self, "telemetry_loss_windows", ()):
            if t0 <= t < t1:
                return False
        return True

    def return_to_home_required(self, t):
        """Pure check the FSM may call each tick: True once the link has been down for at least
        GEOFENCE_RTH_LOSS_S (2.5 s). Call with non-decreasing t."""
        if self.telemetry_link_ok(t):
            self._link_down_since = None
            return False
        if getattr(self, "_link_down_since", None) is None:
            self._link_down_since = t
        return (t - self._link_down_since) >= self.GEOFENCE_RTH_LOSS_S
    # ======================================================================
    # <<< E075 ZAID <<<
    # ======================================================================

    # ======================================================================
    # >>> E043 MUAAZ -- INTEGRATION LOOP (shared plumbing, owned by the lead)  >>>
    # ======================================================================
    INTRUDER_SPEED = 1.35        # m/s, normal walking pace
    STOWED = (0.0, 0.0, -10.0)

    def _init_intruder(self, appear_s):
        m = self.model
        self.intruder_q = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "intruder_root")]
        self.intruder_v = m.jnt_dofadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "intruder_root")]
        path = self._num("intruder_path", None)
        self.intruder_path = [np.array(p) for p in np.asarray(path).reshape(-1, 2)]
        self.intruder_appear_s = float(appear_s) if appear_s is not None else float(self.rng.uniform(40.0, 160.0))

    def _intruder_xy(self, t):
        if t < self.intruder_appear_s:
            return None
        s = (t - self.intruder_appear_s) * self.INTRUDER_SPEED
        pts = self.intruder_path
        for a, b in zip(pts, pts[1:]):
            L = float(np.linalg.norm(b - a))
            if s <= L:
                return a + (b - a) * s / L
            s -= L
        return pts[-1]

    def _place_intruder(self, t):
        xy = self._intruder_xy(t)
        q, v = self.intruder_q, self.intruder_v
        self.data.qpos[q:q + 3] = self.STOWED if xy is None else (xy[0], xy[1], 0.86)
        self.data.qpos[q + 3:q + 7] = (1, 0, 0, 0)
        self.data.qvel[v:v + 6] = 0.0
        return xy

    # ---------------------------------------------------------------- surveillance FSM (contract E)
    # PATROL -> DETECT -> VERIFY -> ALERT_<tier> -> TRACK -> RETURN_TO_PATROL -> PATROL, evaluated on
    # every vision tick. Every input is image-derived (E051 detector + projection) or the UAVs' own
    # state; the intruder's true position is never read here (only surveillance_metrics(), the
    # evaluation, reads it). FR-18 obstacle avoidance and the separation layer stay active in every
    # state: TRACK and RETURN_TO_PATROL only change the target the same controller flies to.
    #   PATROL     both UAVs fly their routes; both cameras are rendered and processed each tick.
    #   DETECT     first tick with a detector hit from a UAV that is on its patrol route, unless the
    #              fix lies within CLOSED_GATE_M of an incident already closed (handed over).
    #   VERIFY     the following ticks. Verified when VERIFY_K consecutive ticks (DETECT tick included)
    #              each have a hit whose ground fix is within VERIFY_GATE_M of the previous fix (fixes of
    #              either UAV count). A tick without such a fix rejects the detection -> PATROL.
    #              The detecting UAV keeps flying its route while verifying.
    #   ALERT_<k>  one tick: tier k from E075 evaluate_geofence_status(fix); tracker chosen by E051
    #              select_tracking_uav among UAVs on their patrol route.
    #   TRACK      the tracker flies to the latest fix (nadir camera: straight above it; forward-oblique
    #              camera: TRACK_STANDOFF_M short of it, heading at it) at the altitude where it left
    #              the route, never more than TRACK_LEASH_M from that point. Each tick re-runs
    #              select_tracking_uav (target handoff) and evaluate_geofence_status (tier changes are
    #              events). Ends after TRACK_MAX_S, or when no fix within TRACK_GATE_M of the last fix
    #              has been seen for TRACK_LOST_S (lost). The incident is then closed.
    #   RETURN_TO_PATROL  the tracker retraces its own breadcrumbs (one every CRUMB_M flown while
    #              tracking) back to where it left the route, then resumes the route at the same waypoint.
    # A teammate function that raises NotImplementedError (E043 branch on its own) leaves the FSM in
    # PATROL for the whole run; detected / detection_latency_s / verify_time_s are then not measured.
    VISION_HZ = 10.0          # design: both surveillance cameras rendered + processed 10 times per sim second
    VERIFY_K = 3              # design: 3 consecutive consistent hits = 0.2 s span at 10 Hz
    VERIFY_GATE_M = 3.0       # design: walking 1.35 m/s moves 0.14 m per tick; interior projection p95 1.5 m (E051)
    TRACK_MAX_S = 30.0        # design: bounded tracking, then the incident is handed over to ground staff
    TRACK_LOST_S = 2.0        # design: lost after 2 s (20 ticks) without a consistent fix
    TRACK_GATE_M = 5.0        # design: a fix within 5 m of the last fix belongs to the tracked target
    TRACK_LEASH_M = 15.0      # design: horizontal leash from the point where the tracker left its route
    TRACK_STANDOFF_M = 4.0    # design: forward-oblique camera (30 deg down) at 2.4 m sees the floor from ~1.5 m ahead
    CLOSED_GATE_M = 8.0       # design: a hit this close to a closed incident's last fix is the same incident
    CRUMB_M = 1.0             # design: breadcrumb spacing for RETURN_TO_PATROL
    # Stationary-target handover (TRACK). A verified target whose ground fix stays within STATIC_M of one point
    # for STATIC_S while every tier E075 gave it is 0 (outside every geofence warning ring) is geotagged and
    # handed to ground staff: the incident closes ("static_handover"), the fix joins the closed-incident list
    # (CLOSED_GATE_M) and the tracker returns to its route. A target in any geofence tier >= 1 is still held for
    # TRACK_MAX_S. Why: in the exterior main batch the parked tempos' red cabs (models/nmims_main_campus.xml,
    # material tempo_cab, the same hue band as the intruder) were verified as targets and each held a UAV in
    # TRACK for the full 30 s; exterior uav_sectors Alpha then completed 1 lap instead of 2 in 7 of 30 runs.
    # The false alarms themselves are NOT removed by this rule: they are still counted in false_alarms.
    STATIC_M = 1.5            # design: walking 1.35 m/s leaves a 1.5 m circle in ~1.1 s; cab fixes jitter < 1 m
    STATIC_S = 5.0            # design: 50 ticks at 10 Hz with no movement beyond STATIC_M
    _PRIVATE_INC_KEYS = ("last_fix", "t_last_fix", "static_ref")   # FSM working state, never reported
    MATCH_M = 3.0             # EVALUATION ONLY: a verified incident is a true detection if its fix is this close
                              # to the intruder's true position at the verify time

    def _init_surveillance(self):
        self.surv_state = "PATROL"       # mission-level state of the open incident (PATROL = none open)
        self.incidents = []              # every incident opened, with its timeline (see _open_incident)
        self._inc = None                 # the open incident
        self._closed_fixes = []          # last fix of every closed incident
        self._next_vision_t = 0.0
        self._last_vision = (False, 0.0, "STATUS_0_ROUTINE_CLEAR")
        self.alert_status = "STATUS_0_ROUTINE_CLEAR"

    def _set_role(self, u, role, event=None):
        u["role"] = role
        u["fsm"] = role if role is not None else self.PHASE_FSM[u["phase"]]
        if event:
            u["events"].append(event)

    def _camera_state(self, name):
        cid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, self.vision_cams[("alpha", "bravo").index(name)])
        u = self.uavs[name]
        return {"pos": self.data.qpos[u["qadr"]:u["qadr"] + 3].copy(),
                "cam_xpos": self.data.cam_xpos[cid].copy(), "cam_xmat": self.data.cam_xmat[cid].reshape(3, 3).copy()}

    def _vision_fixes(self):
        """Render both surveillance cameras, run E051's detector, project each hit to the ground.
        Returns {uav: fix (3,) world point}, max detector latency (ms). Raises NotImplementedError
        when E051's detector is a stub."""
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, 480, 640)
        fixes, lat_ms = {}, 0.0
        proj_kw = inspect.signature(self.inverse_pinhole_projection).parameters
        for name, cam in zip(("alpha", "bravo"), self.vision_cams):
            self.renderer.update_scene(self.data, camera=cam)
            frame = self.renderer.render()
            t0 = time.perf_counter()
            hit = self.detect_intruder_hsv(frame)
            ms = (time.perf_counter() - t0) * 1000.0           # measured, not assumed
            if isinstance(hit, dict):                            # contract C
                if hit.get("latency_ms") is not None:
                    ms = float(hit["latency_ms"])
                centroid = hit.get("centroid") if hit.get("detected") else None
            else:                                                # scaffold (u, v, bbox) / None
                centroid = hit[:2] if hit is not None else None
            lat_ms = max(lat_ms, ms)
            if centroid is None:
                continue
            st = self._camera_state(name)
            kw = {}
            if "cam_xpos" in proj_kw:
                kw = {"cam_xpos": st["cam_xpos"], "cam_xmat": st["cam_xmat"]}
            if "ground_z" in proj_kw:                            # project onto the target's centroid height
                kw["ground_z"] = float(getattr(self, "ASSUMED_TARGET_CENTROID_Z", 0.0))
            p = self.inverse_pinhole_projection(float(centroid[0]), float(centroid[1]), st["pos"], **kw)
            if p is not None:
                fixes[name] = np.asarray(p, dtype=float)
        return fixes, lat_ms

    @staticmethod
    def _nearest_fix(fixes, ref, gate):
        best = None
        for name, p in fixes.items():
            d = float(np.linalg.norm(p[:2] - ref[:2]))
            if d <= gate and (best is None or d < best[1]):
                best = (name, d, p)
        return best

    def _pick_tracker(self, target_xy, pool):
        """E043 call site for E051's select_tracking_uav; falls back to the nearest eligible UAV by xy distance
        when that method is absent (teammate stub), so the FSM never depends on it being present."""
        if hasattr(self, "select_tracking_uav"):
            return self.select_tracking_uav(target_xy, pool)
        if not pool:
            return None
        tx, ty = float(target_xy[0]), float(target_xy[1])

        def dist(n):
            s = pool[n]
            pos = s["pos"] if isinstance(s, dict) else s
            return math.hypot(float(pos[0]) - tx, float(pos[1]) - ty)
        return min(sorted(pool), key=dist)

    def _eligible_states(self, allow=("TRACK",)):
        return {n: self._camera_state(n) for n, u in self.uavs.items()
                if u["phase"] == "patrol" and (u["role"] is None or u["role"] in allow)}

    def _surveillance_tick(self, t):
        """One vision tick: render, detect, and advance the surveillance FSM."""
        if not self.vision_enabled or self.vision_status == "not_implemented":
            return
        try:
            fixes, lat_ms = self._vision_fixes()
            self.vision_status = "active"
            if fixes and self.first_detect_s is None:
                self.first_detect_s = t
            self._fsm_step(t, fixes)
        except NotImplementedError as exc:                       # teammate stub: stay in PATROL, never fake
            self.vision_status = "not_implemented"
            self.vision_note = str(exc)
            for u in self.uavs.values():
                if u["role"] is not None:
                    u["override"] = u["look_at"] = None
                    self._set_role(u, None)
            self.surv_state, self._inc = "PATROL", None
            return
        self._last_vision = (bool(fixes), lat_ms, self.alert_status)

    def _open_incident(self, t, owner, fix):
        self._inc = {"id": len(self.incidents) + 1, "owner": owner, "t_detect": round(t, 3), "t_verify": None,
                     "fix_verify": None, "tier_alert": None, "tier_max": None, "tracker": None, "t_track": None,
                     "t_close": None, "close_reason": None, "handoffs": 0, "hits": 1, "last_fix": fix.copy(),
                     "t_last_fix": t}
        self.incidents.append(self._inc)
        self.surv_state = "DETECT"
        self._set_role(self.uavs[owner], "DETECT", f"detect:{self._inc['id']}")

    def _start_track(self, name, t):
        u = self.uavs[name]
        pos = self.data.qpos[u["qadr"]:u["qadr"] + 3].copy()
        u["crumbs"] = [pos]
        self._set_role(u, "TRACK", f"track:{self._inc['id']}")
        self._steer_tracker(u)

    def _steer_tracker(self, u):
        start = u["crumbs"][0]
        fix = self._inc["last_fix"]
        pos = self.data.qpos[u["qadr"]:u["qadr"] + 3]
        tgt = np.array([fix[0], fix[1], start[2]])
        if self.YAW_MODE[u["name"]] in (1, 2):                   # forward-oblique camera: stand off, face it
            d = tgt[:2] - pos[:2]
            n = float(np.linalg.norm(d))
            tgt[:2] = pos[:2] + d * max(0.0, n - self.TRACK_STANDOFF_M) / n if n > 1e-6 else pos[:2]
            u["look_at"] = np.array([fix[0], fix[1], start[2]])
        off = tgt[:2] - start[:2]
        n = float(np.linalg.norm(off))
        if n > self.TRACK_LEASH_M:
            tgt[:2] = start[:2] + off * self.TRACK_LEASH_M / n
        u["override"] = tgt

    def _release(self, u, t):
        """Tracker -> RETURN_TO_PATROL along its breadcrumbs."""
        u["look_at"] = None
        u["override"] = u["crumbs"][-1].copy() if u["crumbs"] else None
        self._set_role(u, "RETURN_TO_PATROL" if u["crumbs"] else None, "return")

    def _close_incident(self, t, reason):
        inc = self._inc
        inc["t_close"], inc["close_reason"] = round(t, 3), reason
        self._closed_fixes.append(inc["last_fix"].copy())
        for u in self.uavs.values():
            if u["role"] == "TRACK":
                u["events"].append(f"{reason}:{inc['id']}")
                self._release(u, t)
            elif u["role"] in ("DETECT", "VERIFY") or (u["role"] or "").startswith("ALERT"):
                self._set_role(u, None)
        self.evaluate_geofence_status(None)                     # E075 hysteresis state back to clear
        self.alert_status = "STATUS_0_ROUTINE_CLEAR"
        self.surv_state, self._inc = "PATROL", None

    def _fsm_step(self, t, fixes):
        # RETURN_TO_PATROL: retrace breadcrumbs, then resume the route
        for u in self.uavs.values():
            if u["role"] == "RETURN_TO_PATROL":
                pos = self.data.qpos[u["qadr"]:u["qadr"] + 3]
                if np.linalg.norm(pos - u["crumbs"][-1]) < self.ARRIVE_R:
                    u["crumbs"].pop()
                    if u["crumbs"]:
                        u["override"] = u["crumbs"][-1].copy()
                    else:
                        u["override"] = None
                        self._set_role(u, None, "resume_patrol")
            elif u["role"] == "TRACK":
                pos = self.data.qpos[u["qadr"]:u["qadr"] + 3].copy()
                if np.linalg.norm(pos - u["crumbs"][-1]) >= self.CRUMB_M:
                    u["crumbs"].append(pos)

        inc = self._inc
        if inc is None:
            for name in ("alpha", "bravo"):
                u = self.uavs[name]
                if name not in fixes or u["phase"] != "patrol" or u["role"] is not None:
                    continue
                if any(np.linalg.norm(fixes[name][:2] - c[:2]) <= self.CLOSED_GATE_M for c in self._closed_fixes):
                    continue                                     # already handed over
                self._open_incident(t, name, fixes[name])
                return
            return

        owner = self.uavs[inc["owner"]]
        if self.surv_state in ("DETECT", "VERIFY"):
            m = self._nearest_fix(fixes, inc["last_fix"], self.VERIFY_GATE_M)
            if m is None:                                        # inconsistent / missing -> reject
                inc["t_close"], inc["close_reason"] = round(t, 3), "verify_reject"
                self._set_role(owner, None, f"verify_reject:{inc['id']}")
                self.surv_state, self._inc = "PATROL", None
                return
            inc["hits"] += 1
            inc["last_fix"], inc["t_last_fix"] = m[2].copy(), t
            if inc["hits"] < self.VERIFY_K:
                self.surv_state = "VERIFY"
                self._set_role(owner, "VERIFY")
                return
            status, tier = self.evaluate_geofence_status(m[2])
            inc.update(t_verify=round(t, 3), fix_verify=[round(float(v), 3) for v in m[2]], tier_alert=int(tier),
                       tier_max=int(tier))
            self.alert_status = status
            self.surv_state = f"ALERT_{tier}"
            self._set_role(owner, f"ALERT_{tier}", f"verify:{inc['id']};alert:{tier}")
            return

        if self.surv_state.startswith("ALERT"):
            self._set_role(owner, None)
            pool = self._eligible_states()
            if not pool:
                self._close_incident(t, "no_tracker")
                return
            name = self._pick_tracker(inc["last_fix"][:2], pool)
            inc["tracker"], inc["t_track"] = name, round(t, 3)
            self.surv_state = "TRACK"
            self._start_track(name, t)
            return

        # TRACK
        tracker = self.uavs[inc["tracker"]]
        m = self._nearest_fix(fixes, inc["last_fix"], self.TRACK_GATE_M)
        if m is not None:
            inc["last_fix"], inc["t_last_fix"] = m[2].copy(), t
            status, tier = self.evaluate_geofence_status(m[2])
            if tier != inc["tier_max"] and tier > (inc["tier_max"] or 0):
                tracker["events"].append(f"alert:{tier}")
                inc["tier_max"] = int(tier)
            self.alert_status = status
        if t - inc["t_track"] >= self.TRACK_MAX_S:
            self._close_incident(t, "track_timeout")
            return
        if t - inc["t_last_fix"] >= self.TRACK_LOST_S:
            self._close_incident(t, "lost")
            return
        # stationary, tier-0 target: geotagged and handed to ground staff after STATIC_S (see STATIC_S)
        ref = inc.get("static_ref")
        if ref is None or float(np.linalg.norm(inc["last_fix"][:2] - ref[0][:2])) > self.STATIC_M:
            inc["static_ref"] = ref = (inc["last_fix"].copy(), t)
        if (self.static_handover and t - ref[1] >= self.STATIC_S and (inc["tier_max"] or 0) == 0
                and (inc.get("tier_alert") or 0) == 0):
            self._close_incident(t, "static_handover")
            return
        if m is not None:
            name = self._pick_tracker(inc["last_fix"][:2], self._eligible_states())
            if name is not None and name != inc["tracker"]:      # target handoff (E051 rule, with hysteresis)
                tracker["events"].append(f"handoff:{inc['tracker']}->{name}")
                self._release(tracker, t)
                inc["tracker"], inc["handoffs"] = name, inc["handoffs"] + 1
                self._start_track(name, t)
                tracker = self.uavs[name]
        self._steer_tracker(tracker)

    def surveillance_metrics(self):
        """
        EVALUATION (reads the intruder's true path, which the FSM above never does).
        An incident is a TRUE detection when it was verified at or after the intruder appeared and
        its verify fix lies within MATCH_M (horizontal) of the intruder's true position at that time.
          detected            1 if any incident is a true detection, else 0
          detection_latency_s t_detect (the DETECT tick) of the first true incident - intruder_appear_s
          verify_time_s       t_verify - t_detect of that incident (time spent in DETECT + VERIFY)
          false_alarms        verified incidents that are not true detections
          verify_rejects      incidents rejected in VERIFY
        None for everything when vision did not run (vision off or a teammate stub).
        """
        public = [{k: v for k, v in i.items() if k not in self._PRIVATE_INC_KEYS} for i in self.incidents]
        if self.vision_status != "active":
            return {"detected": None, "detection_latency_s": None, "verify_time_s": None,
                    "false_alarms": None, "verify_rejects": None, "incidents": public}
        true_inc, false_n = None, 0
        for inc in self.incidents:
            if inc["t_verify"] is None:
                continue
            xy = self._intruder_xy(inc["t_verify"])
            ok = xy is not None and math.hypot(inc["fix_verify"][0] - xy[0], inc["fix_verify"][1] - xy[1]) <= self.MATCH_M
            inc["true_detection"] = bool(ok)
            if ok and true_inc is None:
                true_inc = inc
            elif not ok:
                false_n += 1
        det = true_inc is not None
        return {"detected": int(det),
                "detection_latency_s": (true_inc["t_detect"] - self.intruder_appear_s) if det else None,
                "verify_time_s": (true_inc["t_verify"] - true_inc["t_detect"]) if det else None,
                "false_alarms": false_n,
                "verify_rejects": sum(1 for i in self.incidents if i["close_reason"] == "verify_reject"),
                "incidents": [{k: v for k, v in i.items() if k not in self._PRIVATE_INC_KEYS}
                              for i in self.incidents]}

    def _log_contacts(self, a, b):
        """Count contact ONSETS (a geom pair that was not touching on the previous step).
        uav_uav_contacts: Alpha airframe vs Bravo airframe, any phase.
        obstacle_contacts (per UAV): airframe vs any other collidable geom, only after the
        takeoff phase -- the dock / floor contact before lift-off is excluded."""
        now = set()
        for c in range(self.data.ncon):
            g1, g2 = int(self.data.contact.geom1[c]), int(self.data.contact.geom2[c])
            now.add((min(g1, g2), max(g1, g2)))
        for pair in now - self._touching:
            in_a = [g in a["geoms"] for g in pair]
            in_b = [g in b["geoms"] for g in pair]
            if any(in_a) and any(in_b):
                self.uav_uav_contacts += 1
                for u in (a, b):
                    u["collisions"] += 1
                    u["events"].append("contact:uav")
                continue
            for u, inside in ((a, in_a), (b, in_b)):
                if any(inside) and u["phase"] != "takeoff":
                    other = pair[1] if inside[0] else pair[0]
                    u["obstacle_contacts"] += 1
                    u["collisions"] += 1
                    name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, other) or f"geom{other}"
                    u["events"].append(f"contact:{name}")
        self._touching = now

    def step_simulation(self, dt=0.05):
        """Advance physics by dt seconds (closed loop at every physics step) and log telemetry."""
        h = self.model.opt.timestep
        n = max(1, int(round(dt / h)))
        a, b = self.uavs["alpha"], self.uavs["bravo"]
        log = self.step_log
        for _ in range(n):
            t = self.data.time
            if self._step_k % self.SENSE_EVERY == 0:
                self._sense(a)
                self._sense(b)
            self._step_k += 1
            self._gust_step(h)
            self._place_intruder(t)
            pa = self.data.qpos[a["qadr"]:a["qadr"] + 3].copy()
            pb = self.data.qpos[b["qadr"]:b["qadr"] + 3].copy()
            self._control(a, pb, h)
            self._control(b, pa, h)
            for u, p in ((a, pa), (b, pb)):   # state at t (before the step), thrust applied over [t, t + h]
                ref = self._reference(u, p)
                err = p - ref
                if u["phase"] == "patrol" and u["override"] is None:
                    self._sq_err_sum += float(err @ err)
                    self._sq_err_n += 1
                    ew = p - self._waypoint_reference(u, p, t)
                    self._wp_sq_sum += float(ew @ ew)
                    self._wp_n += 1
                else:
                    u["leg"] = None                            # re-anchor when patrol flight resumes
                self._effort_n2s += float(u["u"] @ u["u"]) * h
                if log is not None:
                    log.row(u["name"], t, p, self.data.qvel[u["vadr"]:u["vadr"] + 3], ref, err,
                            u["u"], u["fsm"], ";".join(u["events"]), rpy=u["rpy"])
            a["events"].clear(); b["events"].clear()
            mujoco.mj_step(self.model, self.data)
            for u, p in ((a, pa), (b, pb)):
                self._advance_mission(u, p, t)
                if u["last_xy"] is not None:
                    u["dist_m"] += float(np.linalg.norm(p[:2] - u["last_xy"]))
                u["last_xy"] = p[:2].copy()
            if a["phase"] != "takeoff" and b["phase"] != "takeoff":
                self.min_inter_uav_m = min(self.min_inter_uav_m, float(np.linalg.norm(pa - pb)))
            self._log_contacts(a, b)
        self.current_time_s = self.data.time

        pa = self.data.qpos[a["qadr"]:a["qadr"] + 3].copy()
        pb = self.data.qpos[b["qadr"]:b["qadr"] + 3].copy()
        if self.current_time_s >= self._next_vision_t - 1e-9:
            self._next_vision_t += 1.0 / self.vision_hz
            self._surveillance_tick(self.current_time_s)
        detected, lat_ms, status = self._last_vision
        inter = float(np.linalg.norm(pa - pb))

        self.telemetry["time_s"].append(round(self.current_time_s, 3))
        self.telemetry["inter_uav_dist_m"].append(round(inter, 3))
        self.telemetry["alpha_pos"].append(np.round(pa, 3).tolist())
        self.telemetry["bravo_pos"].append(np.round(pb, 3).tolist())
        self.telemetry["detected"].append(detected)
        self.telemetry["detection_latency_ms"].append(round(lat_ms, 3))
        self.telemetry["alert_status"].append(status)
        if not self.frame_log:
            return False

        row = {"t": round(self.current_time_s, 3), "inter_uav_dist_m": round(inter, 3),
               "wind_x": round(self.wind[0], 3), "wind_y": round(self.wind[1], 3),
               "detected": int(detected), "detection_latency_ms": round(lat_ms, 3), "alert_status": status}
        for name, u, p in (("alpha", a, pa), ("bravo", b, pb)):
            wp = self._waypoint(u)
            row.update({f"{name}_x": round(p[0], 3), f"{name}_y": round(p[1], 3), f"{name}_z": round(p[2], 3),
                        f"{name}_zref": round(float(wp[2]), 3),
                        f"{name}_roll": round(u["rpy"][0], 5), f"{name}_pitch": round(u["rpy"][1], 5),
                        f"{name}_yaw": round(u["rpy"][2], 5), f"{name}_phase": u["phase"],
                        f"{name}_u0": round(u["u"][0], 4), f"{name}_u1": round(u["u"][1], 4),
                        f"{name}_u2": round(u["u"][2], 4), f"{name}_u3": round(u["u"][3], 4),
                        f"{name}_apf_N": round(u["apf_N"], 4), f"{name}_governor": int(u["governor"]),
                        f"{name}_energy_wh": round(u["energy_j"] / 3600, 5),
                        f"{name}_dist_m": round(u["dist_m"], 2), f"{name}_collisions": u["collisions"]})
        self.flight_rows.append(row)
        return False

    def flight_metrics(self):
        """
        Run-level flight-quality metrics (contract A columns), both UAVs pooled:
          tracking_rmse_m    CROSS-TRACK RMSE = sqrt( sum |p - p_ref|^2 / n ), summed over every physics step
                               on which a UAV is in the PATROL phase and not diverted by the
                               surveillance FSM (TRACK / RETURN_TO_PATROL; one sample per UAV per
                               step); p_ref is the path reference of _reference(), so this is
                               the RMS cross-track + vertical path-following error in metres.
          waypoint_rmse_m    WAYPOINT-PATH RMSE, same steps, against the timed reference on the commanded
                               waypoint path (_waypoint_reference): cross-track AND along-track error, m.
          control_effort_N2s THRUST effort = integral over the whole run of  sum_{k=0..7} f_k(t)^2  dt
                               (Sum F^2 dt), f_k = commanded thrust of the 8 rotors (4 per UAV), N^2 s.
          torque_effort_N2m2s TORQUE effort = integral over the whole run of |tau_body|^2 dt, both UAVs,
                               tau_body = the body torque the clipped rotor forces produce (mixer
                               allocation: l(F2-F3), l(F1-F0), kQ(F0+F1-F2-F3)), N^2 m^2 s.
          energy_wh          = momentum-theory rotor energy of both UAVs (see _control), Wh.
        """
        return {
            "tracking_rmse_m": math.sqrt(self._sq_err_sum / self._sq_err_n) if self._sq_err_n else float("nan"),
            "control_effort_N2s": self._effort_n2s,
            "waypoint_rmse_m": math.sqrt(self._wp_sq_sum / self._wp_n) if self._wp_n else float("nan"),
            "torque_effort_N2m2s": self._torque_n2m2s,
            "energy_wh": sum(u["energy_j"] for u in self.uavs.values()) / 3600.0,
        }

    def close_telemetry(self):
        """Flush and close the contract-B file; returns its path (None when logging was off)."""
        return self.step_log.close() if self.step_log is not None else None

    def write_telemetry(self, tag):
        os.makedirs(RUNS_DIR, exist_ok=True)
        path = os.path.join(RUNS_DIR, f"telemetry_{tag}_{self.policy}_s{self.seed}.csv")
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(self.flight_rows[0].keys()))
            w.writeheader()
            w.writerows(self.flight_rows)
        return path
    # ======================================================================
    # <<< E043 MUAAZ <<<
    # ======================================================================


def main():
    ap = argparse.ArgumentParser(description="MPSTME GUARDIAN -- dual-UAV patrol, NMIMS Main Building")
    ap.add_argument("--scene", default="interior", choices=tuple(SCENES))
    ap.add_argument("--duration", type=float, default=180.0, help="simulated seconds")
    ap.add_argument("--policy", default="sectors", choices=("sectors", "offset_ring"))
    ap.add_argument("--wind", type=float, default=None, help="mean wind, m/s (scaled by the scene)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="demo")
    ap.add_argument("--no-vision", action="store_true")
    ap.add_argument("--no-telemetry", action="store_true", help="skip the per-step contract-B log")
    ap.add_argument("--vision-hz", type=float, default=None,
                    help=f"surveillance camera rate (default {DualUAVSurveillanceController.VISION_HZ} Hz)")
    args = ap.parse_args()

    run_id = f"{args.scene}_uav_{args.policy}_s{args.seed}"
    tel = None if args.no_telemetry else os.path.join(RUNS_DIR, f"{run_id}.csv.gz")
    ctl = DualUAVSurveillanceController(model_path=SCENES[args.scene], policy=args.policy,
                                        wind_mps=args.wind, seed=args.seed, vision=not args.no_vision,
                                        telemetry_path=tel, run_id=run_id, vision_hz=args.vision_hz)
    print("=" * 64)
    print("Starting Autonomous Collaborative Dual-UAV Surveillance Controller...")
    print(f"Scene: {ctl.scene_name}")
    print("=" * 64)
    while ctl.current_time_s < args.duration:
        ctl.step_simulation(dt=1.0 / 30.0)

    a, b = ctl.uavs["alpha"], ctl.uavs["bravo"]
    path = ctl.close_telemetry()
    print(f"Simulation Finished. Elapsed Time: {ctl.current_time_s:.1f} s   policy={args.policy}")
    print(f"Minimum Inter-UAV Separation: {min(ctl.telemetry['inter_uav_dist_m']):.2f} m (Bound: >= {ctl.d_safe_m} m)")
    for name, u in (("Alpha", a), ("Bravo", b)):
        rows = [r for r in ctl.flight_rows if r[f"{name.lower()}_phase"] == "patrol"]
        err = np.array([r[f"{name.lower()}_z"] - r[f"{name.lower()}_zref"] for r in rows]) if rows else np.zeros(1)
        print(f"  UAV {name}: laps {u['laps']}  flown {u['dist_m']:.0f} m  energy {u['energy_j']/3600:.2f} Wh"
              f"  obstacle contacts {u['obstacle_contacts']}  altitude error {err.mean():+.3f} +/- {err.std():.3f} m")
    for key, label in (("patrol_cp", "ground loop"), ("atrium_cp", "atrium galleries")):
        if ctl.routes[key]:
            g = ctl.revisit_intervals(key)
            worst = f"worst revisit {max(g):.1f} s" if g else "no repeat visits yet"
            print(f"  {label:17s}: coverage {ctl.coverage(key) * 100:5.1f} %   {worst}")
    if ctl.vision_status == "not_implemented":
        print("Vision: E051 detect_intruder_hsv not implemented -- FSM stayed in PATROL, no detections reported "
              "(none faked).")
    elif ctl.vision_status == "active":
        sm = ctl.surveillance_metrics()
        for inc in sm["incidents"]:
            print(f"  incident {inc['id']}: owner {inc['owner']}  DETECT {inc['t_detect']} s  VERIFY "
                  f"{inc['t_verify']}  tier {inc['tier_alert']} (max {inc['tier_max']})  tracker {inc['tracker']}  "
                  f"closed {inc['t_close']} ({inc['close_reason']})  true={inc.get('true_detection')}")
        if sm["detected"]:
            print(f"Detected {sm['detection_latency_s']:.2f} s after the intruder appeared; verified in "
                  f"{sm['verify_time_s']:.2f} s; false alarms {sm['false_alarms']}")
        else:
            print(f"Intruder not detected (false alarms {sm['false_alarms']})")
    fm = ctl.flight_metrics()
    print(f"UAV-UAV contacts: {ctl.uav_uav_contacts}   tracking RMSE {fm['tracking_rmse_m']:.3f} m   "
          f"control effort {fm['control_effort_N2s']:.0f} N^2 s   energy {fm['energy_wh']:.2f} Wh")
    print(f"Telemetry: {path or 'off (--no-telemetry)'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
