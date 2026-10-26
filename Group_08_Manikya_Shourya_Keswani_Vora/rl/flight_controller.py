"""
Cascaded velocity flight controller for the SkyHydro UAV (MuJoCo).

The RL agent (or a human / scripted mission) commands a velocity setpoint
(vx, vy, vz) in world frame — the same interface as PX4/ArduPilot
"offboard velocity" mode. This module turns it into actuator commands:

  1. velocity loop:   a_des = Kv (v_cmd - v) + g      (tilt-limited)
  2. thrust:          T = m a_des . z_body  -> split over the 4 official
                      rotor motors (rotor1..4_thrust, 0..35 N each)
  3. attitude loop:   geometric SO(3) controller (Lee et al. 2010) that
                      rotates the body z-axis onto a_des with fixed yaw,
                      applied as body torque (the differential-thrust
                      moment the official model's pure-z motors can't make)

Physics stays fully MuJoCo: gravity, the winch cable + payload pendulum
(which the agent has to keep from swinging), contacts.
"""
import numpy as np

G = 9.81


class VelocityController:
    def __init__(self, model, data, mujoco_mod, body="uav_chassis", joint="uav_root_joint",
                 kv=(2.2, 2.2, 3.0), k_att=60.0, k_rate=18.0, max_tilt_deg=30.0, motor_max=35.0):
        mj = mujoco_mod
        self.m, self.d = model, data
        self.bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, body)
        jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, joint)
        if self.bid < 0 or jid < 0:
            raise ValueError("scene has no dynamic drone (uav_chassis with uav_root_joint) — "
                             "use scene_train.xml or scene_flood_dynamic.xml")
        self.qadr = int(model.jnt_qposadr[jid])
        self.vadr = int(model.jnt_dofadr[jid])
        self.mass = float(model.body_subtreemass[self.bid])     # airframe + winch cable + payload
        self.motors = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, f"rotor{i}_thrust") for i in range(1, 5)]
        self.kv = np.array(kv, float)
        self.k_att, self.k_rate = k_att, k_rate
        self.tan_tilt = np.tan(np.radians(max_tilt_deg))
        self.motor_max = motor_max

    # ---- state helpers -------------------------------------------------
    def pos(self):
        return self.d.qpos[self.qadr:self.qadr + 3].copy()

    def vel(self):
        return self.d.qvel[self.vadr:self.vadr + 3].copy()            # world frame

    def omega_body(self):
        return self.d.qvel[self.vadr + 3:self.vadr + 6].copy()        # body frame (MuJoCo free joint)

    def R(self):
        return self.d.xmat[self.bid].reshape(3, 3).copy()

    # ---- control -------------------------------------------------------
    def apply(self, v_cmd, yaw=0.0):
        """Compute and write rotor commands + attitude torque for one control tick."""
        v = self.vel()
        a = self.kv * (np.asarray(v_cmd, float) - v)
        a[2] += G
        a[2] = max(a[2], 0.3 * G)                                     # never command free fall
        h = np.hypot(a[0], a[1])
        hmax = self.tan_tilt * a[2]
        if h > hmax:
            a[:2] *= hmax / h
        F = self.mass * a
        R = self.R()
        zb = R[:, 2]
        T = float(np.clip(F @ zb, 0.0, 4 * self.motor_max))
        for mid in self.motors:
            self.d.ctrl[mid] = T / 4.0

        zd = F / (np.linalg.norm(F) + 1e-9)
        xc = np.array([np.cos(yaw), np.sin(yaw), 0.0])
        yd = np.cross(zd, xc); yd /= np.linalg.norm(yd) + 1e-9
        xd = np.cross(yd, zd)
        Rd = np.stack([xd, yd, zd], 1)
        E = 0.5 * (Rd.T @ R - R.T @ Rd)
        e_R = np.array([E[2, 1], E[0, 2], E[1, 0]])
        tau_body = -self.k_att * e_R - self.k_rate * self.omega_body()
        self.d.xfrc_applied[self.bid, 3:6] = R @ tau_body
        self.d.xfrc_applied[self.bid, 0:3] = 0.0
        return T

    def tilt_deg(self):
        return float(np.degrees(np.arccos(np.clip(self.R()[2, 2], -1, 1))))
