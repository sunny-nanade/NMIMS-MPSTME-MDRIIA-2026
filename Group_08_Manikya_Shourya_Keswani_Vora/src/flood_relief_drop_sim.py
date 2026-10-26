"""
Group 08 SkyHydro: closed-loop UAV relief-drop controller + Monte Carlo trials (MuJoCo).

Physics: models/skyhydro_flood_uav.xml (official airframe, timestep 0.002 s = 500 Hz,
RK4). Four rotor motors produce thrust + drag torque on their own sites, the canister
hangs on a 2-DOF cable pendulum with a winch, and RELEASE switches off the hook
constraint so the canister falls and lands under MuJoCo contact physics.

Mission FSM (both controllers):
  TAKEOFF -> CRUISE -> APPROACH_DROP_ZONE -> HOVER -> WINCH_LOWER -> RELEASE -> WINCH_UP -> RETURN_TO_BASE
  (ABORT: canister never steady inside the release window -> keep it, return)

Control law: cascaded PID
  position loop   v_cmd = Kp*(p_ref - p) + Ki*integral(p_ref - p) + v_ref      [Ki = 0 for the baseline]
  velocity loop   a_cmd = Kv*(v_cmd - v) + g      -> collective thrust T = m_hat * a_cmd . z_body
  attitude loop   geometric SO(3) PD (Lee et al. 2010): tau = -kR*e_R - kW*omega
  mixer           [T1..T4] = A^-1 [T, tau_x, tau_y, tau_z]   (X layout, arm 0.30 m, k_m 0.016 m)

Conditions compared (Section 4 of the dossier):
  baseline  "GPS waypoint drop": PD position control of the DRONE over the target,
            no payload sensing, canister released as soon as the winch is down.
  proposed  "vision-guided drop": the downward camera measures the canister relative to
            the drop marker (noise 5 cm, 30 Hz, alpha-beta filter); the drone is moved so
            the CANISTER (not the drone) is over the target, integral action rejects the
            steady crosswind, crane-style anti-sway damps the swing, and the canister is
            released only inside a steady window (error < 0.35 m, rel. speed < 0.35 m/s).

Wind: mean crosswind U (+y, across the approach) + first-order Gauss-Markov gusts
(Dryden-like, sigma = 0.1*U, tau = 2 s); quadratic drag on airframe and canister.

Usage
  python src/flood_relief_drop_sim.py --view                          # watch one proposed drop (10 m/s wind)
  python src/flood_relief_drop_sim.py --view --controller baseline --wind 15
  python src/flood_relief_drop_sim.py --trials 30                     # Monte Carlo: 30 runs x 4 winds x 2 controllers
  python src/flood_relief_drop_sim.py --replay-run 17 --telemetry out.csv   # re-create one run's 500 Hz log from its seed
"""
import argparse
import csv
import gzip
import math
import os
import time

import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODEL = os.path.join(ROOT, "models", "skyhydro_flood_uav.xml")
G = 9.81
RHO = 1.225                       # air density (kg/m^3), ISA sea level

# ---------------------------------------------------------------- parameters
STATES = ["TAKEOFF", "CRUISE", "APPROACH_DROP_ZONE", "HOVER", "WINCH_LOWER", "RELEASE",
          "WINCH_UP", "RETURN_TO_BASE", "ABORT"]
STATE_RGBA = {"TAKEOFF": (1, 1, 1, 1), "CRUISE": (0.2, 0.5, 1, 1), "APPROACH_DROP_ZONE": (0, 0.9, 0.9, 1),
              "HOVER": (1, 0.85, 0, 1), "WINCH_LOWER": (1, 0.5, 0, 1), "RELEASE": (1, 0, 0, 1),
              "WINCH_UP": (0.7, 0, 1, 1), "RETURN_TO_BASE": (0, 0.8, 0, 1), "ABORT": (0.3, 0.3, 0.3, 1)}

ROOF_Z = 6.0                      # roof top of the target building (m)
TARGET = np.array([0.0, 0.0, ROOF_Z])
PAD = np.array([-45.0, 0.0, 1.0]) # relief hub launch pad top
Z_CRUISE = ROOF_Z + 12.0          # 18 m
Z_HOVER = ROOF_Z + 7.0            # 13 m: drone height while the winch works
RELEASE_CLEAR = 1.0               # canister bottom 1 m above the roof at release
V_CRUISE, V_CLIMB = 8.0, 3.0      # m/s
WINCH_SPEED = 0.8                 # m/s pay-out / reel-in
CABLE0 = 3.6                      # nominal cable length (m)

# controller gains (units in brackets)
KP_POS = np.array([1.2, 1.2, 1.5])     # [1/s]       position -> velocity
KI_POS = np.array([0.35, 0.35, 0.4])   # [1/s^2]     proposed only
KV = np.array([2.5, 2.5, 3.0])         # [1/s]       velocity -> acceleration
K_R, K_W = 7.0, 1.1                    # [N m/rad], [N m s/rad]  attitude PD
K_SWAY = 0.6                           # [-]         anti-sway: v += K_SWAY * (v_payload - v_drone)
K_CENTRE = 0.35                        # [1/s]       canister-centring: drone hold point moves by -K_CENTRE * (canister error)
MAX_TILT = math.radians(35.0)
V_LIM = 9.0                            # m/s command limit
REL_ERR, REL_SPD = 0.35, 0.35          # release window (m, m/s)
WINDOW_TIMEOUT = 20.0                  # s in RELEASE without a steady window -> ABORT
HANG_LIMIT_DEG = 40.0                  # proposed: steady canister hang angle above this for 3 s -> ABORT (wind envelope)

# aerodynamics (assumptions, see dossier 2.1 / README)
CDA_UAV = 0.10                    # m^2  drag area of the airframe
CDA_PAYLOAD = 0.08                # m^2  canister side area 0.28 x 0.36 m x Cd 0.8
GUST_SIGMA_FRAC, GUST_TAU = 0.10, 2.0
# power / battery (assumptions)
ROTOR_AREA = math.pi * 0.20 ** 2  # 0.4 m props
FIG_MERIT_ETA = 0.60              # figure of merit x motor/ESC efficiency
BATTERY_WH = 355.0 * 0.80         # 6S 16 Ah pack, 80 % usable


def mjid(m, kind, name):
    return mujoco.mj_name2id(m, kind, name)


def min_jerk(p0, p1, T, t):
    u = np.clip(t / max(T, 1e-6), 0.0, 1.0)
    s = u ** 3 * (10 - 15 * u + 6 * u * u)
    ds = (30 * u ** 2 - 60 * u ** 3 + 30 * u ** 4) / max(T, 1e-6)
    return p0 + (p1 - p0) * s, (p1 - p0) * ds


def seg_time(p0, p1, v):
    return max(2.0, 1.875 * float(np.linalg.norm(p1 - p0)) / v)   # min-jerk peak speed = 1.875 D / T


class Wind:
    """Mean crosswind along +y plus Gauss-Markov gusts on x and y."""

    def __init__(self, U, rng):
        self.U, self.rng = U, rng
        self.sigma = GUST_SIGMA_FRAC * U
        self.g = np.zeros(2)

    def step(self, dt):
        if self.sigma > 0:
            a = math.exp(-dt / GUST_TAU)
            self.g = a * self.g + self.sigma * math.sqrt(1 - a * a) * self.rng.standard_normal(2)
        return np.array([self.g[0], self.U + self.g[1], 0.0])


class DropMission:
    def __init__(self, controller="proposed", wind=0.0, payload_kg=2.0, seed=0, start_jitter=2.0,
                 battery_soc=1.0, model_path=MODEL):
        self.ctrl_name = controller
        self.rng = np.random.default_rng(seed)
        self.m = mujoco.MjModel.from_xml_path(model_path)
        self.d = mujoco.MjData(self.m)
        m = self.m
        B = mujoco.mjtObj
        self.b_uav = mjid(m, B.mjOBJ_BODY, "uav_chassis")
        self.b_pl = mjid(m, B.mjOBJ_BODY, "relief_payload")
        self.g_light = mjid(m, B.mjOBJ_GEOM, "fsm_light")
        self.g_pl = mjid(m, B.mjOBJ_GEOM, "payload_box")
        self.g_roof = mjid(m, B.mjOBJ_GEOM, "building_block")
        self.g_water = mjid(m, B.mjOBJ_GEOM, "flood_water")
        self.eq_hold = mjid(m, B.mjOBJ_EQUALITY, "hook_hold")
        self.a_rotor = [mjid(m, B.mjOBJ_ACTUATOR, f"rotor{i}_thrust") for i in range(1, 5)]
        self.a_winch = mjid(m, B.mjOBJ_ACTUATOR, "winch_motor")
        j = lambda n: mjid(m, B.mjOBJ_JOINT, n)
        self.q_uav, self.v_uav = m.jnt_qposadr[j("uav_root_joint")], m.jnt_dofadr[j("uav_root_joint")]
        self.q_pl, self.v_pl = m.jnt_qposadr[j("payload_free")], m.jnt_dofadr[j("payload_free")]
        self.q_winch = m.jnt_qposadr[j("winch")]

        # canister mass for this trial (inertia scaled with it)
        m0 = m.body_mass[self.b_pl]
        m.body_mass[self.b_pl] = payload_kg
        m.body_inertia[self.b_pl] *= payload_kg / m0
        self.payload_kg = payload_kg
        # the controller only knows the airframe + a nominal 2 kg canister (actual is 1-3 kg)
        self.m_hat = float(m.body_subtreemass[self.b_uav]) + 2.0

        # mixer: rows [T, tau_x, tau_y, tau_z], columns rotors 1..4
        r = np.array([[0.30, 0.30], [-0.30, 0.30], [-0.30, -0.30], [0.30, -0.30]])
        km = np.array([-0.016, 0.016, -0.016, 0.016])
        self.A_inv = np.linalg.inv(np.vstack([np.ones(4), r[:, 1], -r[:, 0], km]))

        # initial state: on the pad (jittered), winch reeled in, canister on the hook
        self.start = PAD + np.array([*self.rng.uniform(-start_jitter, start_jitter, 2), 0.9])
        mujoco.mj_resetData(m, self.d)
        d = self.d
        d.qpos[self.q_uav:self.q_uav + 3] = self.start
        d.qpos[self.q_uav + 3:self.q_uav + 7] = [1, 0, 0, 0]
        d.qpos[self.q_winch] = -3.3
        d.ctrl[self.a_winch] = -3.3
        d.qpos[self.q_pl:self.q_pl + 3] = self.start + np.array([0, 0, -0.15 - (CABLE0 - 3.3) - 0.18])
        d.qpos[self.q_pl + 3:self.q_pl + 7] = [1, 0, 0, 0]
        mujoco.mj_forward(m, d)

        self.wind = Wind(wind, self.rng)
        self.wind_speed = wind
        self.state, self.t_state = "TAKEOFF", 0.0
        self.integ = np.zeros(3)
        self.soc = battery_soc
        self.energy_j = 0.0
        # reference segments
        self.ref_p, self.ref_v = self.start.copy(), np.zeros(3)
        self.seg = None
        self._new_segment(self.start, np.array([self.start[0], self.start[1], Z_CRUISE]), V_CLIMB)
        # vision estimator (canister relative to drop marker / drone)
        self.meas_dt, self.t_meas = 1.0 / 30.0, 0.0
        self.est_rel = np.zeros(2); self.est_rel_v = np.zeros(2)       # canister - drone (xy)
        self.est_err = np.zeros(2)                                       # canister - aim point (xy)
        self.err_lp = np.zeros(2)
        self.offset_hat = np.zeros(2)                                    # mean hanging offset (canister - drone)
        self.shift = np.zeros(2)                                         # proposed: drone hold point shift
        # outcome
        self.released = False; self.t_release = None
        self.landing = None; self.outcome = "running"
        self.swing_max = 0.0; self.swing_at_release = None
        self.t_over_hang = 0.0
        self.winch_target = Z_HOVER - 0.15 - CABLE0 - (ROOF_Z + RELEASE_CLEAR + 0.18)   # extra pay-out (m)
        self.log = []

    # ------------------------------------------------------------ helpers
    def _new_segment(self, p0, p1, v):
        self.seg = (p0.copy(), p1.copy(), seg_time(p0, p1, v), self.d.time)

    def pos(self):
        return self.d.qpos[self.q_uav:self.q_uav + 3].copy()

    def vel(self):
        return self.d.qvel[self.v_uav:self.v_uav + 3].copy()

    def R(self):
        return self.d.xmat[self.b_uav].reshape(3, 3)

    def payload(self):
        return self.d.xpos[self.b_pl].copy()

    def payload_vel(self):
        return self.d.qvel[self.v_pl:self.v_pl + 3].copy()

    def swing_deg(self):
        rel = self.payload() - self.pos()
        return float(np.degrees(math.atan2(math.hypot(rel[0], rel[1]), max(-rel[2], 1e-6))))

    def set_state(self, s):
        self.state, self.t_state = s, self.d.time
        self.m.geom_rgba[self.g_light] = STATE_RGBA[s]

    # ------------------------------------------------------------ sensing
    def _vision(self):
        """Downward camera at 30 Hz: canister position relative to the drone and to the
        drop marker, with 5 cm noise; alpha-beta filter for the relative velocity."""
        if self.d.time + 1e-9 < self.t_meas:
            return
        self.t_meas += self.meas_dt
        noise = self.rng.normal(0, 0.05, 2)
        rel = (self.payload() - self.pos())[:2] + noise
        a, b, dt = 0.5, 0.15, self.meas_dt
        pred = self.est_rel + self.est_rel_v * dt
        r = rel - pred
        self.est_rel = pred + a * r
        self.est_rel_v = self.est_rel_v + b / dt * r
        k = dt / 2.0                                              # mean hanging offset (low-pass, tau 2 s)
        self.offset_hat += k * (self.est_rel - self.offset_hat)
        # aim point: the canister drifts downwind while it falls h metres; in a steady crosswind
        # drift ~ h * tan(theta_hang), so aim that far upwind of the marker
        lv = max(self.pos()[2] - self.payload()[2], 1.0)
        aim = TARGET[:2] - (RELEASE_CLEAR + 0.18) * self.offset_hat / lv
        self.est_err = (self.payload()[:2] + noise) - aim
        self.err_lp += dt / 1.0 * (self.est_err - self.err_lp)

    # ------------------------------------------------------------ FSM
    def _fsm(self):
        t, p, v = self.d.time, self.pos(), self.vel()
        ts = t - self.t_state
        p0, p1, T, t0 = self.seg
        ref_done = t - t0 >= T
        err = float(np.linalg.norm(self.ref_p - p))
        s = self.state
        if s == "TAKEOFF" and ref_done and err < 1.5:
            self.set_state("CRUISE")
            self._new_segment(p, np.array([TARGET[0], TARGET[1], Z_CRUISE]), V_CRUISE)
        elif s == "CRUISE" and ref_done and err < 1.5:
            self.set_state("APPROACH_DROP_ZONE")
            self._new_segment(np.array([TARGET[0], TARGET[1], Z_CRUISE]), np.array([TARGET[0], TARGET[1], Z_HOVER]), V_CLIMB)
        elif s == "APPROACH_DROP_ZONE" and ref_done and err < 1.0:
            self.set_state("HOVER")
        elif s == "HOVER":
            if self.ctrl_name == "baseline":
                ok = err < 0.5 and np.linalg.norm(v) < 0.5
            else:
                ok = np.linalg.norm(self.est_err) < 0.6 and np.linalg.norm(v) < 0.5
            if (ok and ts > 1.0) or ts > 15.0:
                self.set_state("WINCH_LOWER")
        elif s == "WINCH_LOWER":
            if self.d.qpos[self.q_winch] >= self.winch_target - 0.03:
                self.set_state("RELEASE")
        elif s == "RELEASE":
            if self.ctrl_name == "baseline":
                go = True                                         # timed release at the waypoint
            else:
                go = (np.linalg.norm(self.est_err) < REL_ERR and np.linalg.norm(self.est_rel_v) < REL_SPD)
            if go:
                self._release()
                self.set_state("WINCH_UP")
            elif ts > WINDOW_TIMEOUT:
                self.outcome = "aborted_no_steady_window"
                self.set_state("ABORT")
        elif s in ("WINCH_UP", "ABORT"):
            if self.d.qpos[self.q_winch] <= -3.2 or ts > 12.0:
                self.set_state("RETURN_TO_BASE")
                self._new_segment(p, np.array([PAD[0], PAD[1], Z_CRUISE]), V_CRUISE)
        # wind envelope (proposed): the canister hangs too far off vertical for a controlled drop
        if self.ctrl_name == "proposed" and s in ("HOVER", "WINCH_LOWER", "RELEASE"):
            lv = max(p[2] - self.payload()[2], 1.0)
            hang = math.degrees(math.atan(np.linalg.norm(self.offset_hat) / lv))
            self.t_over_hang = self.t_over_hang + self.m.opt.timestep if hang > HANG_LIMIT_DEG else 0.0
            if self.t_over_hang > 3.0:
                self.outcome = "aborted_wind_limit"
                self.set_state("ABORT")
                return
        # battery reserve: abort the drop if the predicted state of charge at the pad < 25 %
        if s in ("CRUISE", "APPROACH_DROP_ZONE", "HOVER", "WINCH_LOWER", "RELEASE"):
            dist_home = float(np.linalg.norm(p[:2] - PAD[:2]))
            p_now = self.energy_j / max(t, 1e-3)
            soc_home = self.soc - p_now * (dist_home / V_CRUISE + 30.0) / 3600.0 / BATTERY_WH
            if soc_home < 0.25:
                self.outcome = "aborted_battery_reserve"
                self.set_state("ABORT")

    def _release(self):
        self.d.eq_active[self.eq_hold] = 0
        self.released, self.t_release = True, self.d.time
        self.swing_at_release = self.swing_deg()

    # ------------------------------------------------------------ control
    def _reference(self):
        p0, p1, T, t0 = self.seg
        if self.state in ("TAKEOFF", "CRUISE", "APPROACH_DROP_ZONE", "RETURN_TO_BASE"):
            self.ref_p, self.ref_v = min_jerk(p0, p1, T, self.d.time - t0)
        else:                                                     # hold over the drop zone
            hold = np.array([TARGET[0], TARGET[1], Z_HOVER])
            if self.ctrl_name == "proposed":
                hold[:2] += self.shift                            # moved so the CANISTER sits over the aim point
                                                                  # (frozen after release: no step in the hold point)
            self.ref_p, self.ref_v = hold, np.zeros(3)

    def _control(self, dt):
        d = self.d
        p, v = self.pos(), self.vel()
        e = self.ref_p - p
        if self.ctrl_name == "proposed":
            if self.state in ("HOVER", "WINCH_LOWER", "RELEASE") and not self.released:
                self.shift = np.clip(self.shift - K_CENTRE * self.err_lp * dt, -6.0, 6.0)
            self.integ = np.clip(self.integ + e * dt, -6.0, 6.0)
            v_cmd = KP_POS * e + KI_POS * self.integ + self.ref_v
            if self.state in ("HOVER", "WINCH_LOWER", "RELEASE") and not self.released:
                v_cmd[:2] += K_SWAY * self.est_rel_v                 # crane anti-sway
        else:
            v_cmd = KP_POS * e + self.ref_v
        n = np.linalg.norm(v_cmd)
        if n > V_LIM:
            v_cmd *= V_LIM / n
        a = KV * (v_cmd - v)
        a[2] += G
        a[2] = max(a[2], 0.3 * G)
        h, hmax = math.hypot(a[0], a[1]), math.tan(MAX_TILT) * a[2]
        if h > hmax:
            a[:2] *= hmax / h
        F = self.m_hat * a
        R = self.R()
        T = float(F @ R[:, 2])
        zd = F / (np.linalg.norm(F) + 1e-9)
        yd = np.cross(zd, [1.0, 0.0, 0.0]); yd /= np.linalg.norm(yd) + 1e-9
        Rd = np.stack([np.cross(yd, zd), yd, zd], 1)
        E = 0.5 * (Rd.T @ R - R.T @ Rd)
        e_R = np.array([E[2, 1], E[0, 2], E[1, 0]])
        omega = d.qvel[self.v_uav + 3:self.v_uav + 6]
        tau = -K_R * e_R - K_W * omega
        thr = np.clip(self.A_inv @ np.array([T, *tau]), 0.0, 35.0)
        for i, aid in enumerate(self.a_rotor):
            d.ctrl[aid] = thr[i]
        # winch
        if self.state == "WINCH_LOWER":
            d.ctrl[self.a_winch] = min(self.winch_target, d.ctrl[self.a_winch] + WINCH_SPEED * dt)
        elif self.state in ("WINCH_UP", "ABORT", "RETURN_TO_BASE"):
            d.ctrl[self.a_winch] = max(-3.3, d.ctrl[self.a_winch] - WINCH_SPEED * dt)
        return thr

    def _apply_wind(self, dt):
        w = self.wind.step(dt)
        self.d.xfrc_applied[:] = 0.0
        for bid, vel, cda in ((self.b_uav, self.vel(), CDA_UAV), (self.b_pl, self.payload_vel(), CDA_PAYLOAD)):
            vr = w - vel
            self.d.xfrc_applied[bid, :3] = 0.5 * RHO * cda * np.linalg.norm(vr) * vr
        return w

    def _landing_check(self):
        if not self.released or self.landing is not None:
            return
        for c in self.d.contact[:self.d.ncon]:
            if self.g_pl in (c.geom1, c.geom2):
                other = c.geom2 if c.geom1 == self.g_pl else c.geom1
                pl = self.payload()
                r = float(np.hypot(pl[0] - TARGET[0], pl[1] - TARGET[1]))
                on_roof = other == self.g_roof and pl[2] > ROOF_Z - 0.05
                self.landing = dict(t=self.d.time, x=pl[0], y=pl[1], r=r, on_roof=on_roof)
                self.outcome = "delivered" if (on_roof and r <= 2.0) else ("off_zone_on_roof" if on_roof else "missed_into_water")
                return

    # ------------------------------------------------------------ run
    def step(self):
        dt = self.m.opt.timestep
        self._vision()
        self._fsm()
        self._reference()
        thr = self._control(dt)
        w = self._apply_wind(dt)
        mujoco.mj_step(self.m, self.d)
        self._landing_check()
        P = float(np.sum(thr ** 1.5) / (FIG_MERIT_ETA * math.sqrt(2 * RHO * ROTOR_AREA)))
        self.energy_j += P * dt
        if self.state in ("HOVER", "WINCH_LOWER", "RELEASE") and not self.released:
            self.swing_max = max(self.swing_max, self.swing_deg())
        return thr, w, P

    def failed(self):
        p = self.pos()
        return self.d.xmat[self.b_uav][8] < math.cos(math.radians(70)) or p[2] < 0.5

    def run(self, t_max=150.0, log=True, viewer=None, realtime=1.0):
        t_wall0 = time.time()
        while self.d.time < t_max:
            thr, w, P = self.step()
            if log:
                p, v, pl = self.pos(), self.vel(), self.payload()
                self.log.append((self.d.time, STATES.index(self.state), *p, *self.ref_p, *v, *pl,
                                 self.swing_deg(), self.d.qpos[self.q_winch] + CABLE0, w[0], w[1], *thr, P))
            if self.failed():
                self.outcome = "crashed"
                break
            if self.state == "RETURN_TO_BASE" and self.d.time - self.t_state > 6.0:
                break
            if viewer is not None:
                if not viewer.is_running():
                    break
                if int(self.d.time / self.m.opt.timestep) % 8 == 0:
                    viewer.cam.lookat[:] = self.pos()
                    try:
                        viewer.set_texts((mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_TOPLEFT,
                                          f"{self.ctrl_name}  wind {self.wind_speed:.0f} m/s  payload {self.payload_kg:.1f} kg",
                                          f"FSM: {self.state}   t = {self.d.time:5.1f} s   swing {self.swing_deg():4.1f} deg"))
                    except Exception:
                        pass
                    viewer.sync()
                    lag = self.d.time / realtime - (time.time() - t_wall0)
                    if lag > 0:
                        time.sleep(lag)
        if self.outcome == "running":
            self.outcome = "no_release" if not self.released else "not_landed"
        return self.summary()

    def summary(self):
        L = np.array(self.log) if self.log else None
        rmse = effort = mean_p = float("nan")
        n = 0
        if L is not None:
            n = len(L)
            dt = self.m.opt.timestep
            path = np.isin(L[:, 1], [STATES.index("CRUISE"), STATES.index("APPROACH_DROP_ZONE")])
            if path.any():
                e = L[path][:, 2:5] - L[path][:, 5:8]
                rmse = float(np.sqrt(np.mean(np.sum(e ** 2, axis=1))))
            thr = L[:, 18:22]
            effort = float(np.sum(thr ** 2) * dt)
            mean_p = float(np.mean(L[:, 22]))
        endurance = BATTERY_WH * 3600.0 / mean_p / 60.0 if mean_p == mean_p and mean_p > 0 else float("nan")
        lg = self.landing or {}
        return dict(controller=self.ctrl_name, wind_ms=self.wind_speed, payload_kg=round(self.payload_kg, 3),
                    outcome=self.outcome, released=int(self.released),
                    landed_on_roof=int(bool(lg.get("on_roof", False))),
                    success=int(self.outcome == "delivered"),
                    radial_error_m=round(lg["r"], 4) if lg else "",
                    landing_x_m=round(lg["x"], 4) if lg else "", landing_y_m=round(lg["y"], 4) if lg else "",
                    max_swing_deg=round(self.swing_max, 3),
                    swing_at_release_deg=round(self.swing_at_release, 3) if self.swing_at_release is not None else "",
                    rmse_path_m=round(rmse, 4), control_effort_N2s=round(effort, 1),
                    t_release_s=round(self.t_release, 3) if self.t_release else "",
                    mission_time_s=round(self.d.time, 3), mean_power_W=round(mean_p, 1),
                    endurance_min=round(endurance, 2), n_samples=n,
                    log_hz=round(1.0 / self.m.opt.timestep, 1))


LOG_COLS = ["t_s", "fsm_state", "x", "y", "z", "x_ref", "y_ref", "z_ref", "vx", "vy", "vz",
            "payload_x", "payload_y", "payload_z", "swing_deg", "cable_len_m", "wind_x", "wind_y",
            "T1_N", "T2_N", "T3_N", "T4_N", "power_W"]


def write_telemetry(path, log):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(LOG_COLS + ["fsm_name"])
        for row in log:
            w.writerow([f"{v:.4f}" if isinstance(v, float) else v for v in row] + [STATES[int(row[1])]])


# ---------------------------------------------------------------- Monte Carlo
def plan(trials, winds, base_seed=2026):
    """Same randomised conditions for both controllers (paired seeds)."""
    runs, rid = [], 0
    for ctrl in ("baseline", "proposed"):
        for w in winds:
            for k in range(trials):
                seed = base_seed + int(w) * 1000 + k                # identical seed for both controllers
                rng = np.random.default_rng(seed)
                runs.append(dict(run_id=rid, controller=ctrl, wind_ms=float(w),
                                 payload_kg=float(rng.uniform(1.0, 3.0)), seed=seed))
                rid += 1
    return runs


def run_one(spec):
    sim = DropMission(spec["controller"], spec["wind_ms"], spec["payload_kg"], seed=spec["seed"])
    s = sim.run()
    return {**{"run_id": spec["run_id"], "seed": spec["seed"]}, **s}, sim.log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--view", action="store_true", help="watch one drop in the MuJoCo viewer")
    ap.add_argument("--controller", choices=["baseline", "proposed"], default="proposed")
    ap.add_argument("--wind", type=float, default=10.0, help="mean crosswind for --view (m/s)")
    ap.add_argument("--payload", type=float, default=2.0, help="canister mass for --view (kg)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--battery-soc", type=float, default=1.0, help="initial state of charge (try 0.3 to see the reserve abort)")
    ap.add_argument("--speed", type=float, default=1.0, help="viewer playback speed")
    ap.add_argument("--trials", type=int, default=0, help="Monte Carlo runs per wind level per controller")
    ap.add_argument("--winds", type=float, nargs="+", default=[0, 5, 10, 15])
    ap.add_argument("--out", default=os.path.join(ROOT, "analytics", "flood_relief_real_trials.csv"))
    ap.add_argument("--telemetry-dir", default=os.path.join(ROOT, "analytics", "telemetry"))
    ap.add_argument("--save-telemetry", type=int, default=3, help="500 Hz logs saved for the first K runs of each condition (all runs are logged in memory and re-creatable with --replay-run)")
    ap.add_argument("--replay-run", type=int, default=None, help="re-run one trial of the plan by run_id")
    ap.add_argument("--telemetry", default=None, help="file for --replay-run's 500 Hz log (.csv or .csv.gz)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    if args.view:
        import mujoco.viewer
        sim = DropMission(args.controller, args.wind, args.payload, seed=args.seed, battery_soc=args.battery_soc)
        print("FSM light colours: TAKEOFF white, CRUISE blue, APPROACH cyan, HOVER yellow, WINCH_LOWER orange, "
              "RELEASE red, WINCH_UP purple, RETURN green, ABORT grey")
        with mujoco.viewer.launch_passive(sim.m, sim.d) as v:
            v.cam.distance, v.cam.elevation, v.cam.azimuth = 22.0, -20.0, 135.0
            last = None
            orig = sim.set_state

            def logged(s):
                print(f"[t={sim.d.time:6.2f}s] {sim.state:>18} -> {s}")
                orig(s)
            sim.set_state = logged
            s = sim.run(viewer=v, realtime=args.speed, log=False)
            print({k: s[k] for k in ("outcome", "radial_error_m", "max_swing_deg", "swing_at_release_deg", "t_release_s")})
            while v.is_running():
                v.sync(); time.sleep(0.05)
        return

    runs = plan(max(args.trials, 1), args.winds)
    if args.replay_run is not None:
        spec = runs[args.replay_run]
        s, log = run_one(spec)
        print(s)
        if args.telemetry:
            write_telemetry(args.telemetry, log)
            print(f"500 Hz telemetry ({len(log)} rows) -> {args.telemetry}")
        return

    if args.trials <= 0:
        ap.error("use --view, --trials N or --replay-run ID")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    os.makedirs(args.telemetry_dir, exist_ok=True)
    t0 = time.time()
    results = []
    keep = {r["run_id"] for r in runs if (r["seed"] - 2026) % 1000 < args.save_telemetry}
    if args.workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(args.workers) as ex:
            for (s, log), spec in zip(ex.map(run_one, runs, chunksize=2), runs):
                results.append(s)
                if spec["run_id"] in keep:
                    write_telemetry(os.path.join(args.telemetry_dir, f"run_{spec['run_id']:03d}_{spec['controller']}_w{int(spec['wind_ms']):02d}.csv.gz"), log)
                print(f"run {s['run_id']:3d} {s['controller']:8s} wind {s['wind_ms']:4.0f}  m={s['payload_kg']:.2f}  {s['outcome']:<26} "
                      f"err {s['radial_error_m']}  rmse {s['rmse_path_m']}", flush=True)
    else:
        for spec in runs:
            s, log = run_one(spec)
            results.append(s)
            if spec["run_id"] in keep:
                write_telemetry(os.path.join(args.telemetry_dir, f"run_{spec['run_id']:03d}_{spec['controller']}_w{int(spec['wind_ms']):02d}.csv.gz"), log)
            print(f"run {s['run_id']:3d} {s['controller']:8s} wind {s['wind_ms']:4.0f}  {s['outcome']:<26} err {s['radial_error_m']}", flush=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader(); w.writerows(results)
    print(f"{len(results)} runs in {time.time() - t0:.0f} s -> {args.out}")


if __name__ == "__main__":
    main()
