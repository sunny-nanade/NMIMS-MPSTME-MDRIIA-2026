#!/usr/bin/env python3
"""Generate the MuJoCo scene from the panel registry (single source of truth).

Writes, next to this file:
    solar_farm.xml         ground, lanes, kerbs, 40 detailed modules (frame + 60 cells each),
                           rails, posts, cable trays, fiducials, fence, dock, per-panel
                           status beacons, and spare 'slot' geoms for run-time defects
    solar_defect_amr.xml   options, defaults, the robot, actuators, sensors; includes the farm

Run:  python models/generate_mjcf.py
Visual geoms are contype=0/conaffinity=0 (no collision cost). Collision geometry is
deliberately tiny: one thin slab per module row (group 3), the lane kerbs, the floor,
and the robot's own chassis/wheels/casters.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import robot_params as rp                       # noqa: E402
from panel_registry import PanelRegistry         # noqa: E402

N_CRACK_SLOTS = 8
N_OBSTR_SLOTS = 24
N_EXT_SLOTS = 3


def f(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x)


def vec(*v):
    return " ".join(f(float(a)) for a in v)


def farm_xml(reg: PanelRegistry) -> str:
    c = reg.cfg
    th = c.tilt
    L = []
    a = L.append
    a('<mujoco model="solar_farm_fragment">')
    a("  <asset>")
    a('    <texture name="skybox" type="skybox" builtin="gradient" rgb1="0.62 0.76 0.93" '
      'rgb2="0.16 0.27 0.48" width="512" height="3072"/>')
    a('    <texture name="tex_gravel" type="2d" builtin="flat" rgb1="0.46 0.43 0.39" rgb2="0.46 0.43 0.39" '
      'width="512" height="512" mark="random" random="0.18" markrgb="0.27 0.25 0.23"/>')
    a('    <texture name="tex_lane" type="2d" builtin="flat" rgb1="0.40 0.38 0.35" rgb2="0.40 0.38 0.35" '
      'width="256" height="256" mark="random" random="0.10" markrgb="0.22 0.21 0.20"/>')
    a('    <texture name="tex_marker" type="2d" builtin="checker" rgb1="0.05 0.05 0.05" rgb2="0.95 0.95 0.95" '
      'width="64" height="64"/>')
    a('    <material name="mat_gravel" texture="tex_gravel" texrepeat="14 14" texuniform="true" specular="0.05"/>')
    a('    <material name="mat_lane" texture="tex_lane" texrepeat="6 6" texuniform="true" specular="0.05"/>')
    a('    <material name="mat_glass" rgba="0.035 0.06 0.17 1" specular="0.75" shininess="0.85"/>')
    a('    <material name="mat_cell" rgba="0.07 0.12 0.30 1" specular="0.55" shininess="0.7"/>')
    a('    <material name="mat_frame" rgba="0.74 0.76 0.79 1" specular="0.8" shininess="0.6"/>')
    a('    <material name="mat_steel" rgba="0.55 0.58 0.62 1" specular="0.5" shininess="0.4"/>')
    a('    <material name="mat_concrete" rgba="0.62 0.62 0.60 1" specular="0.05"/>')
    a('    <material name="mat_cable" rgba="0.04 0.04 0.04 1" specular="0.1"/>')
    a('    <material name="mat_marker" texture="tex_marker" texrepeat="1 1" specular="0.1"/>')
    a('    <material name="mat_lane_line" rgba="0.95 0.78 0.12 1"/>')
    a('    <material name="mat_fence" rgba="0.30 0.33 0.36 1" specular="0.3"/>')
    a('    <material name="mat_dock" rgba="0.20 0.55 0.35 1" specular="0.2"/>')
    a('    <material name="mat_sun" rgba="1 0.96 0.75 1" emission="1"/>')
    a('    <material name="mat_beacon" rgba="0.5 0.5 0.5 1" emission="0.4"/>')
    a('    <material name="mat_crack" rgba="0.02 0.02 0.02 1"/>')
    a('    <material name="mat_obstr" rgba="0.18 0.30 0.10 1"/>')
    a('    <material name="mat_ext" rgba="0.25 0.25 0.28 1"/>')
    a("  </asset>")
    a("  <worldbody>")
    # light, sun disc, ground
    a('    <light name="sun" directional="true" castshadow="true" pos="0 0 40" dir="0 0 -1" '
      'diffuse="0.85 0.82 0.75" specular="0.4 0.4 0.4"/>')
    a('    <geom name="sun_disc" class="vis" type="sphere" size="2.5" pos="0 0 80" material="mat_sun"/>')
    xmid = c.x0 + c.row_length / 2.0
    ytop = reg.row_low_y(c.n_rows) + c.panel_l * math.cos(th)
    ymid = (reg.lane_y(1) + ytop) / 2.0
    a('    <geom name="floor" type="plane" size="40 40 0.1" material="mat_gravel" friction="0.9 0.02 0.001"/>')

    # lane strips, centre lines, headland pads
    x_lo = c.x0 - c.headland - 1.0
    x_hi = c.x0 + c.row_length + c.headland + 1.0
    for r in range(1, c.n_rows + 1):
        ly = reg.lane_y(r)
        a(f'    <geom name="LANE_R{r:02d}" class="vis" type="box" pos="{vec(xmid, ly, 0.002)}" '
          f'size="{vec(c.row_length / 2 + 0.8, c.kerb_half_gap, 0.002)}" material="mat_lane"/>')
        a(f'    <geom name="LANE_LINE_R{r:02d}" class="vis" type="box" pos="{vec(xmid, ly, 0.0045)}" '
          f'size="{vec(c.row_length / 2 + 0.8, 0.03, 0.001)}" material="mat_lane_line"/>')
        # kerbs (collision): 0.14 m tall -> higher than the wheel radius, the wheels cannot climb them
        for tag, sgn in (("N", +1), ("S", -1)):
            a(f'    <geom name="KERB_R{r:02d}_{tag}" type="box" '
              f'pos="{vec(xmid, ly + sgn * (c.kerb_half_gap + 0.05), 0.07)}" '
              f'size="{vec(c.row_length / 2 + 0.6, 0.05, 0.07)}" material="mat_concrete" '
              f'friction="0.6 0.01 0.001"/>')
    for tag, x in (("W", c.x0 - c.headland / 2 - 0.3), ("E", c.x0 + c.row_length + c.headland / 2 + 0.3)):
        a(f'    <geom name="HEADLAND_{tag}" class="vis" type="box" '
          f'pos="{vec(x, (reg.lane_y(1) + reg.lane_y(c.n_rows)) / 2, 0.003)}" '
          f'size="{vec(c.headland / 2 + 0.3, (reg.lane_y(c.n_rows) - reg.lane_y(1)) / 2 + 1.3, 0.002)}" '
          f'material="mat_lane"/>')

    # rows: collision slab, rails, posts, tray, cables, fiducials
    for r in range(1, c.n_rows + 1):
        yl = reg.row_low_y(r)
        cy = yl + 0.5 * c.panel_l * math.cos(th)
        cz = c.z_low + 0.5 * c.panel_l * math.sin(th)
        a(f'    <geom name="ROW_R{r:02d}_slab" type="box" group="3" pos="{vec(xmid, cy, cz)}" '
          f'euler="{vec(th, 0, 0)}" size="{vec(c.row_length / 2, c.panel_l / 2, 0.0005)}" '
          f'rgba="0 0 0 0.004" friction="0.4 0.005 0.0001"/>')
        for k, off in (("a", -0.45), ("b", +0.45)):
            p = (xmid, cy + off * math.cos(th) - (c.panel_t / 2 + 0.035) * (-math.sin(th)) * -1.0,
                 cz + off * math.sin(th) - (c.panel_t / 2 + 0.035) * math.cos(th))
            a(f'    <geom name="RAIL_R{r:02d}_{k}" class="vis" type="box" pos="{vec(*p)}" '
              f'euler="{vec(th, 0, 0)}" size="{vec(c.row_length / 2, 0.025, 0.025)}" material="mat_steel"/>')
        # posts every 2 columns, front and back legs + concrete foundations
        for xi in range(0, c.n_cols + 1, 2):
            px = c.x0 + xi * c.col_pitch
            fy, fz = yl + 0.05, c.z_low - 0.06
            by = yl + c.panel_l * math.cos(th) - 0.05
            bz = c.z_low + c.panel_l * math.sin(th) - 0.06
            a(f'    <geom name="POST_R{r:02d}_{xi:02d}_F" class="vis" type="cylinder" '
              f'fromto="{vec(px, fy, 0.0, px, fy, fz)}" size="0.032" material="mat_steel"/>')
            a(f'    <geom name="POST_R{r:02d}_{xi:02d}_B" class="vis" type="cylinder" '
              f'fromto="{vec(px, by, 0.0, px, by, bz)}" size="0.032" material="mat_steel"/>')
            a(f'    <geom name="FOUND_R{r:02d}_{xi:02d}_F" class="vis" type="cylinder" '
              f'fromto="{vec(px, fy, 0.0, px, fy, 0.12)}" size="0.075" material="mat_concrete"/>')
            a(f'    <geom name="FOUND_R{r:02d}_{xi:02d}_B" class="vis" type="cylinder" '
              f'fromto="{vec(px, by, 0.0, px, by, 0.12)}" size="0.075" material="mat_concrete"/>')
        # cable tray + three cables + junction box + conduit
        ty, tz = yl + 0.55, 0.30
        a(f'    <geom name="TRAY_R{r:02d}" class="vis" type="box" pos="{vec(xmid, ty, tz)}" '
          f'size="{vec(c.row_length / 2, 0.09, 0.012)}" material="mat_steel"/>')
        for q, dy in enumerate((-0.04, 0.0, 0.04)):
            a(f'    <geom name="CABLE_R{r:02d}_{q}" class="vis" type="capsule" '
              f'fromto="{vec(c.x0, ty + dy, tz + 0.02, c.x0 + c.row_length, ty + dy, tz + 0.02)}" '
              f'size="0.009" material="mat_cable"/>')
        a(f'    <geom name="JB_R{r:02d}" class="vis" type="box" pos="{vec(c.x0 + c.row_length + 0.18, ty, 0.30)}" '
          f'size="0.12 0.09 0.16" material="mat_steel"/>')
        a(f'    <geom name="CONDUIT_R{r:02d}" class="vis" type="capsule" '
          f'fromto="{vec(c.x0 + c.row_length, ty, tz + 0.02, c.x0 + c.row_length + 0.12, ty, tz + 0.02)}" '
          f'size="0.014" material="mat_cable"/>')
        for mx in reg.marker_xs():
            a(f'    <geom name="FID_R{r:02d}_{int(round(mx * 100)):04d}" class="vis" type="box" '
              f'pos="{vec(mx, yl - 0.10, 0.50)}" size="0.07 0.006 0.07" material="mat_marker"/>')

    # panels
    for p in reg.panels:
        px, py, pz = p.center
        pid = p.pid
        a(f'    <body name="{pid}" pos="{vec(px, py, pz)}" euler="{vec(th, 0, 0)}">')
        a(f'      <geom name="{pid}_glass" class="vis" type="box" size="{vec(c.panel_w / 2, c.panel_l / 2, c.panel_t / 2 - 0.006)}" '
          f'material="mat_glass"/>')
        t2 = c.panel_t / 2
        fw = c.frame_w
        a(f'      <geom name="{pid}_frame_s" class="vis" type="box" pos="{vec(0, -(c.panel_l / 2 - fw / 2), t2 - 0.008)}" '
          f'size="{vec(c.panel_w / 2, fw / 2, 0.012)}" material="mat_frame"/>')
        a(f'      <geom name="{pid}_frame_n" class="vis" type="box" pos="{vec(0, +(c.panel_l / 2 - fw / 2), t2 - 0.008)}" '
          f'size="{vec(c.panel_w / 2, fw / 2, 0.012)}" material="mat_frame"/>')
        a(f'      <geom name="{pid}_frame_w" class="vis" type="box" pos="{vec(-(c.panel_w / 2 - fw / 2), 0, t2 - 0.008)}" '
          f'size="{vec(fw / 2, c.panel_l / 2, 0.012)}" material="mat_frame"/>')
        a(f'      <geom name="{pid}_frame_e" class="vis" type="box" pos="{vec(+(c.panel_w / 2 - fw / 2), 0, t2 - 0.008)}" '
          f'size="{vec(fw / 2, c.panel_l / 2, 0.012)}" material="mat_frame"/>')
        for i in range(c.cells_along):
            for j in range(c.cells_across):
                off = reg.cell_offsets[i, j]
                # offsets are world-frame (x east, slope along up_slope); convert to panel-local:
                lx = float(off[0])
                ly = float(off[1]) / math.cos(th)
                a(f'      <geom name="{pid}_cell_i{i:02d}_j{j:02d}" class="vis" type="box" '
                  f'pos="{vec(lx, ly, t2 - 0.003)}" size="{vec(reg.cell_w / 2 - 0.004, reg.cell_l / 2 - 0.004, 0.003)}" '
                  f'material="mat_cell"/>')
        a("    </body>")
        # status beacon above the high edge (colour = DETECTION RESULT, never ground truth)
        bp = p.center + p.up_slope * (c.panel_l / 2 + 0.10) + p.normal * 0.10
        a(f'    <geom name="MARK_{pid}" class="vis" type="cylinder" pos="{vec(*bp)}" size="0.06 0.03" '
          f'material="mat_beacon" rgba="0.55 0.55 0.58 1"/>')

    # fence (visual)
    fx0, fx1 = c.x0 - c.headland - 4.5, c.x0 + c.row_length + c.headland + 5.0
    fy0, fy1 = reg.lane_y(1) - 3.6, ytop + 3.6
    def fence_line(name, p0, p1):
        n = max(2, int(math.dist(p0, p1) // 3.0) + 1)
        for k in range(n + 1):
            t = k / n
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            a(f'    <geom name="{name}_post{k:02d}" class="vis" type="cylinder" fromto="{vec(x, y, 0.0, x, y, 2.0)}" '
              f'size="0.04" material="mat_fence"/>')
        for zz, tag in ((0.5, "lo"), (1.0, "mid"), (1.9, "hi")):
            a(f'    <geom name="{name}_rail_{tag}" class="vis" type="capsule" '
              f'fromto="{vec(p0[0], p0[1], zz, p1[0], p1[1], zz)}" size="0.015" material="mat_fence"/>')
    fence_line("FENCE_S", (fx0, fy0), (fx1, fy0))
    fence_line("FENCE_N", (fx0, fy1), (fx1, fy1))
    fence_line("FENCE_W", (fx0, fy0), (fx0, fy1))
    fence_line("FENCE_E", (fx1, fy0), (fx1, fy1))

    # dock station
    dx, dy, _ = reg.dock_pose
    a(f'    <geom name="DOCK_PAD" class="vis" type="box" pos="{vec(dx, dy, 0.012)}" size="1.3 0.9 0.012" material="mat_dock"/>')
    a(f'    <geom name="DOCK_BACKSTOP" class="vis" type="box" pos="{vec(dx - 1.15, dy, 0.25)}" size="0.06 0.7 0.25" material="mat_steel"/>')
    for k, yy in enumerate((-0.75, 0.75)):
        a(f'    <geom name="DOCK_POST_{k}" class="vis" type="cylinder" fromto="{vec(dx - 0.9, dy + yy, 0.0, dx - 0.9, dy + yy, 2.2)}" '
          f'size="0.05" material="mat_steel"/>')
    a(f'    <geom name="DOCK_ROOF" class="vis" type="box" pos="{vec(dx - 0.9, dy, 2.25)}" size="{vec(0.9, 0.95, 0.04)}" material="mat_steel"/>')
    a(f'    <geom name="DOCK_CHARGER" class="vis" type="box" pos="{vec(dx - 1.02, dy, 0.30)}" size="0.04 0.14 0.12" '
      f'rgba="0.9 0.75 0.1 1"/>')

    # spare geoms for run-time defects (positioned by the simulation; parked underground)
    for k in range(N_CRACK_SLOTS):
        a(f'    <geom name="CRACK_SLOT_{k}" class="vis" type="capsule" fromto="-0.07 0 -20 0.07 0 -20" size="0.004" '
          f'material="mat_crack"/>')
    for k in range(N_OBSTR_SLOTS):
        a(f'    <geom name="OBSTR_SLOT_{k}" class="vis" type="box" size="{vec(reg.cell_w / 2, reg.cell_l / 2, 0.008)}" '
          f'pos="0 0 -20" material="mat_obstr"/>')
    for k in range(N_EXT_SLOTS):
        a(f'    <geom name="EXT_SLOT_{k}" class="vis" type="box" size="0.30 0.12 0.06" pos="0 0 -20" material="mat_ext"/>')

    # overview cameras
    def lookat_cam(name, pos, target, fovy):
        import numpy as np
        pos = np.array(pos, float); target = np.array(target, float)
        z = pos - target; z /= np.linalg.norm(z)
        x = np.cross([0, 0, 1.0], z); x /= np.linalg.norm(x)
        y = np.cross(z, x)
        a(f'    <camera name="{name}" pos="{vec(*pos)}" xyaxes="{vec(*x, *y)}" fovy="{fovy}"/>')
    lookat_cam("overview", (xmid - 14.0, reg.lane_y(1) - 15.0, 9.0), (xmid, ymid, 0.6), 50)
    lookat_cam("lane_view", (c.x0 - 2.2, reg.lane_y(1) - 0.6, 1.9), (c.x0 + 6.0, reg.lane_y(1) + 1.5, 0.9), 55)
    a(f'    <camera name="top_view" pos="{vec(xmid, ymid, 38.0)}" xyaxes="1 0 0 0 1 0" fovy="40"/>')
    a("  </worldbody>")
    a("</mujoco>")
    return "\n".join(L)


def main_xml(reg: PanelRegistry) -> str:
    c = reg.cfg
    dx, dy, _ = reg.dock_pose
    r, b = rp.WHEEL_RADIUS, rp.TRACK_WIDTH
    ch = rp.CHASSIS_HALF
    L = []
    a = L.append
    a('<mujoco model="solar_defect_amr">')
    a("  <!-- GENERATED by models/generate_mjcf.py -- edit the generator or src/robot_params.py, not this file -->")
    a('  <compiler angle="radian" autolimits="true"/>')
    a('  <option gravity="0 0 -9.81" timestep="0.002" solver="Newton" iterations="40" integrator="implicitfast"/>')
    a('  <size memory="128M"/>')
    a('  <visual>')
    a('    <global offwidth="1280" offheight="720"/>')
    a('    <quality shadowsize="4096" offsamples="8"/>')
    a('    <headlight ambient="0.35 0.35 0.38" diffuse="0.35 0.35 0.35" specular="0.1 0.1 0.1"/>')
    a('    <map znear="0.02" zfar="400"/>')
    a('  </visual>')
    a('  <statistic center="5.25 9 0.5" extent="30"/>')
    a("  <default>")
    # dossier contact settings: wheel 1.2/0.05/0.002 ; panel 0.4/0.005/0.0001 ; solref 0.005 1 ; solimp 0.9 0.95 0.001 0.5 2
    a('    <geom condim="4" friction="1.2 0.05 0.002" solref="0.005 1.0" solimp="0.9 0.95 0.001 0.5 2"/>')
    a('    <joint damping="0.0" armature="0.0"/>')
    a('    <default class="vis"><geom contype="0" conaffinity="0" group="1" condim="1" mass="0"/></default>')
    a("  </default>")
    a('  <include file="solar_farm.xml"/>')
    a("  <worldbody>")
    a(f'    <body name="amr_chassis" pos="{vec(dx, dy, rp.CHASSIS_Z0)}">')
    a('      <freejoint name="amr_root"/>')
    a(f'      <geom name="chassis_geom" type="box" size="{vec(*ch)}" rgba="0.12 0.50 0.72 1" mass="16.0"/>')
    a(f'      <geom name="chassis_cover" class="vis" type="box" pos="0 0 {f(ch[2] + 0.012)}" size="{vec(ch[0] - 0.03, ch[1] - 0.03, 0.012)}" rgba="0.92 0.93 0.95 1"/>')
    a(f'      <geom name="chassis_stripe" class="vis" type="box" pos="{f(ch[0] - 0.005)} 0 0.0" size="0.006 {f(ch[1])} 0.03" rgba="0.95 0.55 0.1 1"/>')
    a(f'      <geom name="fender_l" class="vis" type="box" pos="0 {f(b / 2 + 0.01)} {f(rp.WHEEL_Z_REL + 0.14)}" size="{vec(0.15, 0.05, 0.012)}" rgba="0.1 0.1 0.12 1"/>')
    a(f'      <geom name="fender_r" class="vis" type="box" pos="0 {f(-(b / 2 + 0.01))} {f(rp.WHEEL_Z_REL + 0.14)}" size="{vec(0.15, 0.05, 0.012)}" rgba="0.1 0.1 0.12 1"/>')
    a(f'      <geom name="bumper_front" class="vis" type="box" pos="{f(ch[0] + 0.02)} 0 -0.03" size="0.02 {f(ch[1] - 0.02)} 0.03" rgba="0.1 0.1 0.12 1"/>')
    a('      <site name="imu" pos="0 0 0" size="0.01"/>')
    a('      <site name="body_origin" pos="0 0 0" size="0.012" rgba="1 0 0 0"/>')
    # drive wheels (hinge about +y; positive speed = forward)
    for side, sg in (("left", +1), ("right", -1)):
        a(f'      <body name="wheel_{side}" pos="0 {f(sg * b / 2)} {f(rp.WHEEL_Z_REL)}">')
        a(f'        <joint name="wheel_{side}_joint" type="hinge" axis="0 1 0" damping="0.05"/>')
        a(f'        <geom name="wheel_{side}_geom" type="cylinder" size="{f(r)} {f(rp.WHEEL_HALF_WIDTH)}" zaxis="0 1 0" '
          f'rgba="0.08 0.08 0.08 1" mass="2.0" friction="1.2 0.05 0.002"/>')
        a(f'        <geom name="wheel_{side}_hub" class="vis" type="cylinder" pos="0 {f(sg * (rp.WHEEL_HALF_WIDTH + 0.002))} 0" '
          f'size="0.05 0.004" zaxis="0 1 0" rgba="0.75 0.75 0.78 1"/>')
        a("      </body>")
    # skid casters (frictionless spheres rigidly fixed to the chassis)
    for tag, sx in (("front", +1), ("rear", -1)):
        a(f'      <geom name="caster_{tag}_geom" type="sphere" size="{f(rp.CASTER_RADIUS)}" '
          f'pos="{f(sx * rp.CASTER_X)} 0 {f(rp.CASTER_Z_REL)}" rgba="0.2 0.2 0.22 1" mass="0.8" friction="0.01 0.001 0.0001" priority="1"/>')
    # side range-sensor posts (visual) + sites
    for tag, sx, sy in (("lf", +1, +1), ("lr", -1, +1), ("rf", +1, -1), ("rr", -1, -1)):
        a(f'      <geom name="rfpost_{tag}" class="vis" type="cylinder" fromto="{vec(sx * rp.RF_X, sy * rp.RF_Y, ch[2], sx * rp.RF_X, sy * rp.RF_Y, rp.RF_Z_REL)}" size="0.008" rgba="0.2 0.2 0.2 1"/>')
        a(f'      <site name="rf_{tag}" pos="{vec(sx * rp.RF_X, sy * rp.RF_Y, rp.RF_Z_REL)}" size="0.012" rgba="1 0.2 0.2 1"/>')
    a(f'      <site name="rf_front" pos="{vec(ch[0] + 0.03, 0, 0.0)}" size="0.012" rgba="1 0.2 0.2 1"/>')
    # sensor mast with lift, pan and tilt
    a(f'      <body name="sensor_mast" pos="{vec(rp.MAST_X, 0, rp.MAST_BASE_Z)}">')
    a('        <geom name="mast_lower" class="vis" type="cylinder" fromto="0 0 0 0 0 0.55" size="0.032" rgba="0.65 0.67 0.70 1"/>')
    a('        <body name="mast_slider" pos="0 0 0">')
    a(f'          <joint name="mast_lift_joint" type="slide" axis="0 0 1" range="{f(rp.LIFT_MIN)} {f(rp.LIFT_MAX)}" damping="20"/>')
    a(f'          <geom name="mast_upper" type="cylinder" fromto="0 0 0.05 0 0 {f(rp.HEAD_Z_IN_SLIDER)}" size="0.024" '
      f'rgba="0.85 0.86 0.88 1" mass="1.2" contype="0" conaffinity="0"/>')
    a(f'          <site name="ref_pyranometer" pos="0 0 {f(rp.HEAD_Z_IN_SLIDER + 0.16)}" size="0.015" rgba="1 1 0.2 1"/>')
    a(f'          <geom name="ref_cell_plate" class="vis" type="box" pos="0 0 {f(rp.HEAD_Z_IN_SLIDER + 0.15)}" euler="{f(c.tilt)} 0 0" size="0.05 0.035 0.004" rgba="0.1 0.2 0.5 1"/>')
    a(f'          <body name="gimbal_pan" pos="0 0 {f(rp.HEAD_Z_IN_SLIDER)}">')
    a(f'            <joint name="pan_joint" type="hinge" axis="0 0 1" range="{f(-rp.PAN_LIMIT)} {f(rp.PAN_LIMIT)}" damping="0.1"/>')
    a('            <geom name="gimbal_bracket" type="box" size="0.045 0.045 0.02" rgba="0.15 0.15 0.17 1" mass="0.4" contype="0" conaffinity="0"/>')
    a('            <geom name="gimbal_fork_l" class="vis" type="box" pos="0.035 0.075 0.03" size="0.03 0.012 0.045" rgba="0.15 0.15 0.17 1"/>')
    a('            <geom name="gimbal_fork_r" class="vis" type="box" pos="0.035 -0.075 0.03" size="0.03 0.012 0.045" rgba="0.15 0.15 0.17 1"/>')
    a('            <body name="gimbal_tilt" pos="0.035 0 0.03">')
    a(f'              <joint name="tilt_joint" type="hinge" axis="0 1 0" range="{f(rp.TILT_MIN)} {f(rp.TILT_MAX)}" damping="0.05"/>')
    a('              <geom name="camera_housing" type="box" size="0.07 0.062 0.045" rgba="0.90 0.35 0.08 1" mass="0.6" contype="0" conaffinity="0"/>')
    a('              <geom name="thermal_lens_ring" class="vis" type="cylinder" pos="0.072 0.025 0" size="0.026 0.008" zaxis="1 0 0" rgba="0.1 0.1 0.1 1"/>')
    a('              <geom name="optical_lens_ring" class="vis" type="cylinder" pos="0.072 -0.025 0" size="0.02 0.008" zaxis="1 0 0" rgba="0.05 0.1 0.2 1"/>')
    a(f'              <site name="thermal_lens" pos="{f(rp.LENS_X)} 0.025 0" size="0.012" rgba="1 0 0 1"/>')
    a(f'              <site name="optical_lens" pos="{f(rp.LENS_X)} -0.025 0" size="0.012" rgba="0 0.4 1 1"/>')
    a(f'              <camera name="thermal_cam" pos="{f(rp.LENS_X)} 0.025 0" xyaxes="0 -1 0 0 0 1" fovy="45"/>')
    a(f'              <camera name="optical_cam" pos="{f(rp.LENS_X)} -0.025 0" xyaxes="0 -1 0 0 0 1" fovy="55"/>')
    a("            </body>")
    a("          </body>")
    a("        </body>")
    a("      </body>")
    a("    </body>")
    a("  </worldbody>")
    a("  <actuator>")
    lim = rp.WHEEL_TORQUE_LIMIT
    a(f'    <motor name="motor_wheel_left" joint="wheel_left_joint" gear="1" ctrllimited="true" ctrlrange="{f(-lim)} {f(lim)}"/>')
    a(f'    <motor name="motor_wheel_right" joint="wheel_right_joint" gear="1" ctrllimited="true" ctrlrange="{f(-lim)} {f(lim)}"/>')
    a(f'    <position name="servo_pan" joint="pan_joint" kp="30" kv="3" ctrllimited="true" ctrlrange="{f(-rp.PAN_LIMIT)} {f(rp.PAN_LIMIT)}" forcelimited="true" forcerange="-6 6"/>')
    a(f'    <position name="servo_tilt" joint="tilt_joint" kp="20" kv="2" ctrllimited="true" ctrlrange="{f(rp.TILT_MIN)} {f(rp.TILT_MAX)}" forcelimited="true" forcerange="-4 4"/>')
    a(f'    <position name="servo_mast_lift" joint="mast_lift_joint" kp="4000" kv="150" ctrllimited="true" ctrlrange="{f(rp.LIFT_MIN)} {f(rp.LIFT_MAX)}" forcelimited="true" forcerange="-150 150"/>')
    a("  </actuator>")
    a("  <sensor>")
    a('    <jointpos name="enc_left_pos" joint="wheel_left_joint"/>')
    a('    <jointpos name="enc_right_pos" joint="wheel_right_joint"/>')
    a('    <jointvel name="enc_left_vel" joint="wheel_left_joint"/>')
    a('    <jointvel name="enc_right_vel" joint="wheel_right_joint"/>')
    a('    <jointpos name="pan_pos" joint="pan_joint"/>')
    a('    <jointpos name="tilt_pos" joint="tilt_joint"/>')
    a('    <jointpos name="lift_pos" joint="mast_lift_joint"/>')
    a('    <gyro name="imu_gyro" site="imu"/>')
    a('    <accelerometer name="imu_acc" site="imu"/>')
    a('    <framepos name="gt_pos" objtype="site" objname="body_origin"/>')
    a('    <framequat name="gt_quat" objtype="site" objname="body_origin"/>')
    a("  </sensor>")
    a("</mujoco>")
    return "\n".join(L)


def main():
    reg = PanelRegistry()
    with open(os.path.join(HERE, "solar_farm.xml"), "w") as fh:
        fh.write(farm_xml(reg))
    with open(os.path.join(HERE, "solar_defect_amr.xml"), "w") as fh:
        fh.write(main_xml(reg))
    print("wrote solar_farm.xml and solar_defect_amr.xml in", HERE)


if __name__ == "__main__":
    main()
