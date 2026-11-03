"""Blender 5.x scene generator for the solar-farm digital twin (visual layer).

Builds, from the SAME registry that generates the MuJoCo model (src/panel_registry.py), a rendered
copy of the farm: 40 modules with a 10x6 cell texture, racking, kerbs, fence, dock, the AMR with
mast and pan/tilt head, a sun lamp at the real sun direction (src/sun_position.py) and cameras.

Run inside Blender (macOS):
    /Applications/Blender.app/Contents/MacOS/Blender --background --python blender/generate_solar_farm.py -- \
        --out results/blender --render
or from the bpy wheel:   python blender/generate_solar_farm.py --out results/blender --render

Outputs  <out>/solar_farm.blend , <out>/solar_farm.glb , <out>/farm_overview.png (with --render)
Frame convention: ENU, +X East, +Y North, +Z up  (identical to MuJoCo, so coordinates match 1:1).
"""
from __future__ import annotations

import datetime as dt
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from panel_registry import PanelRegistry  # noqa: E402
from sun_position import SunModel  # noqa: E402
import robot_params as rp  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out, render, hour = os.path.join(ROOT, "results", "blender"), False, 11.5
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = argv[i + 1]; i += 1
        elif argv[i] == "--render":
            render = True
        elif argv[i] == "--hour":
            hour = float(argv[i + 1]); i += 1
        i += 1
    return out, render, hour


def mat(name, rgba, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def cell_material():
    """Dark-blue PV glass with a 10 x 6 cell grid (procedural, no image files needed)."""
    m = bpy.data.materials.new("pv_cells")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = nt.nodes["Material Output"]
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.12
    bsdf.inputs["Metallic"].default_value = 0.2
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Brick Width"].default_value = 1.0 / 6.0
    brick.inputs["Row Height"].default_value = 1.0 / 10.0
    brick.inputs["Color1"].default_value = (0.01, 0.03, 0.16, 1)
    brick.inputs["Color2"].default_value = (0.015, 0.04, 0.19, 1)
    brick.inputs["Mortar"].default_value = (0.7, 0.72, 0.78, 1)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def box(name, center, size, material, rot=(0, 0, 0), collection=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.rotation_euler = Euler(rot, "XYZ")
    o.data.materials.append(material)
    return o


def cyl(name, center, radius, depth, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=center, vertices=32)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = Euler(rot, "XYZ")
    o.data.materials.append(material)
    return o


def build_farm(reg: PanelRegistry):
    c = reg.cfg
    m_ground = mat("ground", (0.36, 0.30, 0.24, 1), 0.95)
    m_steel = mat("steel", (0.62, 0.64, 0.68, 1), 0.35, 0.9)
    m_frame = mat("frame", (0.75, 0.76, 0.8, 1), 0.3, 0.9)
    m_kerb = mat("kerb", (0.5, 0.5, 0.5, 1), 0.9)
    m_cells = cell_material()
    box("ground", (c.x0 + c.row_length / 2, 8.0, -0.02), (40, 50, 0.04), m_ground)
    th = c.tilt
    for spec in reg.panels:
        p = box(spec.pid, spec.center, (c.panel_w - 0.002, c.panel_l, c.panel_t), m_cells, rot=(th, 0, 0))
        f = box(spec.pid + "_frame", spec.center, (c.panel_w + 0.02, c.panel_l + 0.02, c.panel_t * 0.8), m_frame, rot=(th, 0, 0))
        f.location = Vector(spec.center) - Vector(spec.normal) * (c.panel_t * 0.55)
    for r in range(1, c.n_rows + 1):
        yl = reg.row_low_y(r)
        for xp in (c.x0 + 0.5, c.x0 + c.row_length / 2, c.x0 + c.row_length - 0.5):
            h_low, h_top = c.z_low, c.z_low + c.panel_l * math.sin(th)
            cyl(f"post_low_R{r}_{xp:.1f}", (xp, yl, h_low / 2), 0.035, h_low, m_steel)
            cyl(f"post_top_R{r}_{xp:.1f}", (xp, yl + c.panel_l * math.cos(th), h_top / 2), 0.035, h_top, m_steel)
        box(f"kerb_S_R{r}", (c.x0 + c.row_length / 2, reg.lane_y(r) - c.kerb_half_gap, 0.04), (c.row_length + 4, 0.1, 0.08), m_kerb)
        box(f"kerb_N_R{r}", (c.x0 + c.row_length / 2, reg.lane_y(r) + c.kerb_half_gap, 0.04), (c.row_length + 4, 0.1, 0.08), m_kerb)
    dx, dy, _ = reg.dock_pose
    box("dock_pad", (dx, dy, 0.01), (1.8, 1.4, 0.02), mat("dock", (0.1, 0.55, 0.3, 1)))
    box("dock_roof", (dx - 0.2, dy + 0.9, 1.6), (1.6, 1.0, 0.05), mat("roof", (0.7, 0.72, 0.76, 1)))
    for sx in (-0.7, 0.3):
        cyl(f"dock_post_{sx}", (dx + sx, dy + 0.9, 0.8), 0.04, 1.6, m_steel)


def build_robot(reg: PanelRegistry, pos=None, yaw=0.0):
    dx, dy, _ = reg.dock_pose
    x, y = (pos or (dx, dy))
    z0 = rp.CHASSIS_Z0
    m_body = mat("amr_body", (0.12, 0.50, 0.72, 1), 0.4, 0.3)
    m_dark = mat("amr_dark", (0.06, 0.06, 0.07, 1), 0.8)
    m_cam = mat("amr_cam", (0.9, 0.35, 0.08, 1), 0.4)
    parts = []
    parts.append(box("amr_chassis", (x, y, z0), (2 * rp.CHASSIS_HALF[0], 2 * rp.CHASSIS_HALF[1], 2 * rp.CHASSIS_HALF[2]), m_body))
    for s, nm in ((+1, "L"), (-1, "R")):
        w = cyl(f"amr_wheel_{nm}", (x, y + s * (rp.TRACK_WIDTH / 2), z0 + rp.WHEEL_Z_REL), rp.WHEEL_RADIUS, 2 * rp.WHEEL_HALF_WIDTH, m_dark, rot=(math.pi / 2, 0, 0))
        parts.append(w)
    mast_base = z0 + rp.MAST_BASE_Z
    parts.append(cyl("amr_mast", (x + rp.MAST_X, y, mast_base + 0.5), 0.03, 1.0, mat("mast", (0.8, 0.82, 0.85, 1), 0.4, 0.8)))
    head_z = mast_base + rp.HEAD_Z_IN_SLIDER
    parts.append(box("amr_head", (x + rp.MAST_X + 0.04, y, head_z + 0.05), (0.14, 0.12, 0.09), m_cam))
    parts.append(cyl("amr_thermal_lens", (x + rp.MAST_X + 0.11, y + 0.025, head_z + 0.05), 0.026, 0.016, m_dark, rot=(0, math.pi / 2, 0)))
    for o in parts:
        o.parent = None
    return parts


def lighting(reg, hour):
    sm = SunModel(19.076, 72.8777, 5.5)
    s = sm.at(dt.date(2026, 10, 31), hour * 3600.0)
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 20))
    sun = bpy.context.active_object
    sun.name = "sun"
    sun.data.energy = 3.0
    v = Vector(s.vec)                       # unit vector TOWARDS the sun (ENU)
    sun.rotation_euler = (-v).to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("sky")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.45, 0.62, 0.9, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    bpy.context.scene.world = w
    return s


def cameras(reg):
    c = reg.cfg
    mid = Vector((c.x0 + c.row_length / 2, 8.0, 0.5))
    bpy.ops.object.camera_add(location=(-9, -12, 8))
    cam = bpy.context.active_object
    cam.name = "overview"
    cam.rotation_euler = (mid - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 28
    bpy.context.scene.camera = cam
    return cam


def main():
    out, render, hour = parse_args()
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    reg = PanelRegistry()
    build_farm(reg)
    build_robot(reg)
    sun = lighting(reg, hour)
    cameras(reg)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "Standard"
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.cycles.device = "CPU"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "solar_farm.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "solar_farm.glb"), export_format="GLB")
    print(f"sun elevation {sun.elevation_deg:.1f} deg azimuth {sun.azimuth_deg:.1f} deg  | {len(reg)} modules built")
    if render:
        sc.render.filepath = os.path.join(out, "farm_overview.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", sc.render.filepath)


if __name__ == "__main__":
    main()
