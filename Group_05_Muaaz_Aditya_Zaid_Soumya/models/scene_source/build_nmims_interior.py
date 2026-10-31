#!/usr/bin/env python3
"""
NMIMS Main Building INTERIOR scene generator | MDRIIA Group 05
Owner: E043 Muaaz Mohammed Iqbal Shaikh

Builds models/nmims_main_interior.xml: the inside of the NMIMS Main Building,
V.L. Mehta Rd x Gulmohar Rd, Vile Parle (West) -- a ten-storey building wrapped
around a central atrium with gallery corridors on every floor.

Sources, and how much each one is trusted:
  MEASURED  outer walls     OSM way 791070239 footprint (ODbL)
  MEASURED  atrium void     satellite skylight, ~21.6 x 38.5 m, +/- ~2 m
                            (roof edges aligned to the OSM footprint to remove parallax)
  REFERENCE appearance      NMIMS official virtual tour interior panoramas:
                            Atrium Sitting Area, NMIMS Wall of Fame, Lifts,
                            Cafeteria, VIP Lounge, Auditorium Lobby, Entry Staircase
  ASSUMED   room placement  inferred from the tour's navigation links; no floor
                            plan is public. Verify against the fire-evacuation
                            plans posted beside the lifts (visible in the tour).

Frame: ENU metres, same origin as the exterior scene. z = 0 is the ground floor.
Geom group 2 holds everything above the ground-floor ceiling, so a renderer
with group 2 disabled shows a "dollhouse" cut-away of the ground floor.

  python models/scene_source/build_nmims_interior.py
"""
import csv
import math
import os

from osm_geometry import (load_osm, ring, convex_hull, clip_halfplane, prism_vertices,
                          signed_area, MAIN_BUILDING_ID)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_XML = os.path.join(os.path.dirname(HERE), "nmims_main_interior.xml")
OUT_MANIFEST = os.path.join(HERE, "interior_manifest.csv")

# ---------------- dimensions ----------------
N_FLOORS, FLOOR_H, SLAB_T = 10, 3.6, 0.30          # storeys ASSUMED (exterior panorama count)
ROOF_Z = N_FLOORS * FLOOR_H
AX0, AX1, AY0, AY1 = -10.8, 10.8, -25.9, 12.6       # atrium void, MEASURED (satellite)
CORR_W = 3.0                                         # gallery corridor width, ASSUMED
CX0, CX1, CY0, CY1 = AX0 - CORR_W, AX1 + CORR_W, AY0 - CORR_W, AY1 + CORR_W
CEIL = FLOOR_H - SLAB_T                              # ground-floor ceiling (3.3 m)
WALL_T, EXT_T = 0.22, 0.35
RAIL_H = 1.1
# FR-18 collision policy: every physical object a UAV could fly into is collidable
# (cls SOLID, so it is both a contact obstacle and visible to the on-board range ring).
# class "visual" is kept ONLY for floor finishes and decals, the restricted-zone
# marker, flush wall/ceiling finishes (door leaves, lift doors, light panels,
# portrait frames, wall-mounted screens) that sit within ~0.1 m of a collidable
# surface, and the human intruder (contype 0, see below).
SOLID = None

# patrol design (E043): Alpha walks the guard's ground-floor corridor loop;
# Bravo sweeps the atrium at every gallery level.
ALPHA_Z = 2.4                     # 0.9 m below the corridor ceiling
BRAVO_INSET = 2.5                 # m inside the atrium edge
LOOP_X, LOOP_Y0, LOOP_Y1 = AX1 + CORR_W / 2, AY0 - CORR_W / 2, AY1 + CORR_W / 2

assets, world, custom, manifest = [], [], [], []


def box(name, cls, mat, cx, cy, cz, hx, hy, hz, group=None, yaw=0.0, extra=""):
    g = f' group="{group}"' if group is not None else ""
    c = f' class="{cls}"' if cls else ""
    n = f' name="{name}"' if name else ""
    e = f' euler="0 0 {yaw:.5f}"' if yaw else ""
    world.append(f'<geom{n}{c} type="box" material="{mat}" size="{hx:.3f} {hy:.3f} {hz:.3f}" '
                 f'pos="{cx:.3f} {cy:.3f} {cz:.3f}"{e}{g}{extra}/>')


def wall_x(name, x, y0, y1, z0, z1, mat, gaps=(), group=None, cls=None, t=WALL_T):
    """Wall along y at constant x, with door gaps [(yc, width), ...]."""
    cuts = sorted((yc - w / 2, yc + w / 2) for yc, w in gaps)
    s, k = y0, 0
    for a, b in cuts + [(y1, y1)]:
        if a - s > 0.05:
            box(f"{name}_{k}", cls, mat, x, (s + a) / 2, (z0 + z1) / 2, t / 2, (a - s) / 2, (z1 - z0) / 2, group); k += 1
        s = b
    for yc, w in gaps:                                  # lintel over each door
        box(f"{name}_lintel_{yc:+.0f}", SOLID, mat, x, yc, (2.4 + z1) / 2, t / 2, w / 2, (z1 - 2.4) / 2, group)


def wall_y(name, y, x0, x1, z0, z1, mat, gaps=(), group=None, cls=None, t=WALL_T):
    cuts = sorted((xc - w / 2, xc + w / 2) for xc, w in gaps)
    s, k = x0, 0
    for a, b in cuts + [(x1, x1)]:
        if a - s > 0.05:
            box(f"{name}_{k}", cls, mat, (s + a) / 2, y, (z0 + z1) / 2, (a - s) / 2, t / 2, (z1 - z0) / 2, group); k += 1
        s = b
    for xc, w in gaps:
        box(f"{name}_lintel_{xc:+.0f}", SOLID, mat, xc, y, (2.4 + z1) / 2, w / 2, t / 2, (z1 - 2.4) / 2, group)


# --------------------------------------------------------------------------
# building shell from the OSM footprint
# --------------------------------------------------------------------------
_, els, by_id = load_osm()
hull = convex_hull(ring(by_id[MAIN_BUILDING_ID]))
world.append(f'<!-- ===== SHELL: OSM way {MAIN_BUILDING_ID}, {abs(signed_area(hull)):.0f} m2 hull ===== -->')
for i in range(len(hull)):
    (x1, y1), (x2, y2) = hull[i], hull[(i + 1) % len(hull)]
    L = math.hypot(x2 - x1, y2 - y1); yaw = math.atan2(y2 - y1, x2 - x1)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    box(f"ext_wall_gf_{i}", None, "wall_cream", mx, my, CEIL / 2 + 0.15, L / 2 + EXT_T / 2, EXT_T / 2, CEIL / 2 + 0.15, yaw=yaw)
    box(f"ext_wall_up_{i}", None, "wall_white", mx, my, (CEIL + 0.3 + ROOF_Z) / 2, L / 2 + EXT_T / 2, EXT_T / 2,
        (ROOF_Z - CEIL - 0.3) / 2, group=2, yaw=yaw)

# ground-floor base finish (stone) over the whole footprint
assets.append(f'<mesh name="gf_floor" vertex="{prism_vertices(hull, 0.0, 0.02)}"/>')
world.append('<geom name="gf_floor" type="mesh" mesh="gf_floor" class="visual" material="stone_floor"/>')

# floor slabs with the atrium void: four convex pieces per floor (hull minus rectangle)
pieces = {
    "n": clip_halfplane(hull, 0, -1, -AY1),
    "s": clip_halfplane(hull, 0, 1, AY0),
    "w": clip_halfplane(clip_halfplane(clip_halfplane(hull, 1, 0, AX0), 0, 1, AY1), 0, -1, -AY0),
    "e": clip_halfplane(clip_halfplane(clip_halfplane(hull, -1, 0, -AX1), 0, 1, AY1), 0, -1, -AY0),
}
for k, P in pieces.items():
    assets.append(f'<mesh name="slab_{k}" vertex="{prism_vertices(P, 0.0, SLAB_T)}"/>')
world.append(f'<!-- ===== FLOOR SLABS x{N_FLOORS} around the atrium void (galleries) ===== -->')
for f in range(1, N_FLOORS + 1):
    z = f * FLOOR_H - SLAB_T
    for k in pieces:
        world.append(f'<geom name="slab_{f:02d}_{k}" type="mesh" mesh="slab_{k}" material="slab_edge" pos="0 0 {z:.2f}" group="2"/>')

# skylight over the atrium (collision: keeps the aircraft inside)
box("skylight", None, "skylight", 0, (AY0 + AY1) / 2, ROOF_Z - 0.05, (AX1 - AX0) / 2, (AY1 - AY0) / 2, 0.05, group=2)
for i, x in enumerate([AX0 + k * (AX1 - AX0) / 6 for k in range(1, 6)]):
    box(f"skylight_beam_{i}", SOLID, "steel", x, (AY0 + AY1) / 2, ROOF_Z - 0.2, 0.08, (AY1 - AY0) / 2, 0.12, group=2)

# --------------------------------------------------------------------------
# galleries on floors 1..9: glass railing at the void edge, room fronts behind
# --------------------------------------------------------------------------
world.append('<!-- ===== GALLERIES: glass railings, corridor back walls with doors ===== -->')
for f in range(1, N_FLOORS):
    z0 = f * FLOOR_H
    zr = z0 + RAIL_H / 2
    for name, (cx, cy, hx, hy) in {"n": (0, AY1, (AX1 - AX0) / 2, 0.04), "s": (0, AY0, (AX1 - AX0) / 2, 0.04),
                                   "w": (AX0, (AY0 + AY1) / 2, 0.04, (AY1 - AY0) / 2),
                                   "e": (AX1, (AY0 + AY1) / 2, 0.04, (AY1 - AY0) / 2)}.items():
        box(f"rail_{f:02d}_{name}", None, "glass_rail", cx, cy, zr, hx, hy, RAIL_H / 2, group=2)
        box(f"rail_{f:02d}_{name}_cap", SOLID, "steel", cx, cy, z0 + RAIL_H, max(hx, 0.05), max(hy, 0.05), 0.03, group=2)
    zt = z0 + (FLOOR_H - SLAB_T) / 2
    hz = (FLOOR_H - SLAB_T) / 2
    box(f"gal_wall_{f:02d}_w", SOLID, "wall_cream", CX0, (CY0 + CY1) / 2, zt, WALL_T / 2, (CY1 - CY0) / 2, hz, group=2)
    box(f"gal_wall_{f:02d}_e", SOLID, "wall_cream", CX1, (CY0 + CY1) / 2, zt, WALL_T / 2, (CY1 - CY0) / 2, hz, group=2)
    box(f"gal_wall_{f:02d}_n", SOLID, "wall_cream", 0, CY1, zt, (CX1 - CX0) / 2, WALL_T / 2, hz, group=2)
    box(f"gal_wall_{f:02d}_s", SOLID, "wall_cream", 0, CY0, zt, (CX1 - CX0) / 2, WALL_T / 2, hz, group=2)
    for y in [CY0 + 3 + 5.5 * k for k in range(8) if CY0 + 3 + 5.5 * k < CY1 - 2]:
        for x in (CX0 + 0.13, CX1 - 0.13):
            box(None, "visual", "door_dark", x, y, z0 + 1.1, 0.02, 0.55, 1.1, group=2)
    for x in (-8, -3, 3, 8):
        for y in (CY0 + 0.13, CY1 - 0.13):
            box(None, "visual", "door_dark", x, y, z0 + 1.1, 0.55, 0.02, 1.1, group=2)

# --------------------------------------------------------------------------
# ground floor: corridor ring, rooms
# --------------------------------------------------------------------------
world.append('<!-- ===== GROUND FLOOR (room placement ASSUMED from tour topology) ===== -->')
GF = dict(cls=None)
# corridor-side walls of the wings, with doors / openings
wall_x("gf_w", CX0, CY0, CY1, 0, CEIL, "wall_cream", gaps=[(4.0, 2.0), (-10.0, 1.8), (-22.0, 1.8)])
wall_x("gf_e", CX1, CY0, CY1, 0, CEIL, "wall_cream", gaps=[(5.0, 3.2), (-20.0, 3.2)])
wall_y("gf_n", CY1, CX0, CX1, 0, CEIL, "wall_cream", gaps=[(-6.0, 3.0), (6.0, 3.0)])
wall_y("gf_s", CY0, CX0, CX1, 0, CEIL, "stone_clad", gaps=[(0.0, 5.0)])
# west wing dividers: VIP Lounge | Board Room | Conference Room
WX0 = -21.6
wall_y("gf_vip_board", -4.0, WX0 - 2.2, CX0, 0, CEIL, "wood_panel")
wall_y("gf_board_conf", -16.0, WX0 - 2.4, CX0, 0, CEIL, "wood_panel")
# south wing: lift lobby, service rooms, entry foyer
LY0 = -40.0
wall_x("gf_lift_w", -6.0, LY0, CY0, 0, CEIL, "wood_panel")
wall_x("gf_lift_e", 6.0, LY0, CY0, 0, CEIL, "wood_panel")
wall_y("gf_foyer", LY0, -22.5, 22.5, 0, CEIL, "stone_clad", gaps=[(0.0, 5.0)])
for y in (-32.0, -36.5):                               # four lifts, wood-framed steel doors
    for x, sgn in ((-6.0, 1), (6.0, -1)):
        box(None, "visual", "wood_panel", x + sgn * 0.14, y, 1.35, 0.03, 1.15, 1.35)
        box(None, "visual", "steel", x + sgn * 0.18, y, 1.1, 0.02, 0.62, 1.1)

# floor finishes per room (visual)
box("floor_cafe", "visual", "cafe_floor", (CX1 + 23.2) / 2, (CY0 + CY1) / 2, 0.025, (23.2 - CX1) / 2, (CY1 - CY0) / 2, 0.005)
box("floor_vip", "visual", "carpet", (WX0 + CX0) / 2, (-4.0 + CY1) / 2, 0.025, (CX0 - WX0) / 2, (CY1 + 4.0) / 2, 0.005)
box("floor_board", "visual", "carpet", (WX0 + CX0) / 2, -10.0, 0.025, (CX0 - WX0) / 2, 6.0, 0.005)
box("floor_lifts", "visual", "lobby_floor", 0, (LY0 + CY0) / 2, 0.025, 6.0, (CY0 - LY0) / 2, 0.005)
box("floor_foyer", "visual", "marble_floor", 0, -48.5, 0.025, 17.0, 8.3, 0.005)
box("floor_audlobby", "visual", "marble_floor", 0, (CY1 + 21.0) / 2, 0.025, 17.0, (21.0 - CY1) / 2, 0.005)

# ceiling light panels (emissive) under the first-floor slab
for x in (CX0 + 1.5, CX1 - 1.5):
    for y in range(int(CY0) + 2, int(CY1) - 1, 4):
        box(None, "visual", "ceiling_light", x, y, CEIL - 0.02, 0.5, 0.5, 0.01, group=2)
for x in range(-12, 13, 4):
    for y in (CY0 + 1.5, CY1 - 1.5):
        box(None, "visual", "ceiling_light", x, y, CEIL - 0.02, 0.5, 0.5, 0.01, group=2)

# ---- Wall of Fame: wood panels with portrait frames on the south corridor wall, facing the atrium
world.append('<!-- Wall of Fame (tour: "NMIMS Wall of Fame") -->')
for xc in (-8.0, 8.0):
    box(None, "visual", "stone_clad", xc, CY0 + 0.14, 1.65, 4.6, 0.03, 1.55)
    for c in range(-2, 3):
        box(None, "visual", "wood_panel", xc + c * 1.8, CY0 + 0.19, 1.7, 0.75, 0.025, 1.2)
        for r in range(3):
            box(None, "visual", "frame_photo", xc + c * 1.8 + (-0.3 if r % 2 else 0.3), CY0 + 0.22, 1.1 + 0.55 * r, 0.18, 0.012, 0.22)
box(None, "visual", "dark_wood", 0, CY0 - 0.14 + 0.0, 1.6, 2.4, 0.03, 1.2)   # NMIMS logo panel beside the lift opening

# ---- Cafeteria: counters + menu screens on the outer wall, long tables with benches
world.append('<!-- Cafeteria (tour: "Cafeteria") -->')
box("furn_cafe_counter", SOLID, "counter", 22.4, (CY0 + CY1) / 2, 0.55, 0.45, (CY1 - CY0) / 2 - 2, 0.55)
for y in range(int(CY0) + 3, int(CY1) - 2, 4):
    box(None, "visual", "screen", 22.8, y, 2.45, 0.04, 1.4, 0.35)
for x in (16.0, 19.2):
    for y in range(int(CY0) + 3, int(CY1) - 3, 5):
        box(f"furn_cafe_bench_table_{x:.0f}_{y}", SOLID, "bench_wood", x, y + 1.6, 0.74, 0.45, 1.8, 0.03)
        for sx in (-0.75, 0.75):
            box(f"furn_cafe_bench_{x + sx:.1f}_{y}", SOLID, "bench_wood", x + sx, y + 1.6, 0.44, 0.15, 1.8, 0.03)

# ---- VIP Lounge (restricted): rows of black leather lounge chairs, panelling, TV
world.append('<!-- VIP Lounge (tour: "VIP Lounge") -- RESTRICTED ZONE -->')
for r in range(4):
    for c in range(4):
        x = -19.8 + c * 1.25; y = 9.5 - r * 1.4
        box(f"furn_vip_chair_{r}{c}", SOLID, "leather_black", x, y, 0.42, 0.5, 0.45, 0.22)
        box(f"furn_vip_chair_{r}{c}_back", SOLID, "leather_black", x, y + 0.42, 0.85, 0.5, 0.08, 0.35)
box(None, "visual", "screen", WX0 - 0.6, 3.0, 1.9, 0.04, 1.0, 0.6)
box(None, "visual", "wood_panel", -17.6, 15.0, 1.6, 3.6, 0.04, 1.5)
# Board Room: long table and chairs
box("furn_board_table", SOLID, "dark_wood", -17.8, -10.0, 0.75, 1.0, 4.0, 0.04)
for y in range(-13, -6, 1):
    for x in (-19.2, -16.4):
        box(f"furn_board_chair_{x:.0f}_{y}", SOLID, "leather_black", x, y + 0.5, 0.5, 0.25, 0.25, 0.25)
# Conference Room
box("furn_conf_table", SOLID, "dark_wood", -17.8, -22.5, 0.75, 1.2, 3.0, 0.04)

# ---- Entry foyer: reception desk, planters, grand stair (visual) on the east side
world.append('<!-- Entry foyer (tour: "Entry Staircase") -->')
box("furn_reception_desk", SOLID, "table_white", -3.0, -47.0, 0.55, 1.6, 0.45, 0.55)
for k in range(12):
    box(f"stair_step_{k:02d}", SOLID, "marble_floor", 12.0, -44.0 - k * 0.32, 0.09 + k * 0.17, 3.0, 0.16, 0.09 + k * 0.17)
for x in (-9.0, 9.0):
    box(f"foyer_planter_{x:+.0f}", SOLID, "planter", x, -44.0, 0.45, 1.0, 1.0, 0.45)
    world.append(f'<geom name="foyer_shrub_{x:+.0f}" type="ellipsoid" size="1.1 1.1 1.3" pos="{x} -44 2.0" material="foliage"/>')
# Auditorium lobby: escalators rising to the auditorium (visual)
world.append('<!-- Auditorium lobby (tour: "Auditorium Lobby") -->')
for x in (-1.0, 1.0):
    world.append(f'<geom name="escalator_{x:+.0f}" type="box" material="escalator" size="0.55 3.2 0.35" pos="{x} {CY1 + 3.3:.2f} 1.4" euler="0.45 0 0"/>')

# --------------------------------------------------------------------------
# atrium floor: deck, turf, planter islands with trees, grand piano, cafe tables
# --------------------------------------------------------------------------
world.append('<!-- ===== ATRIUM (tour: "Atrium Sitting Area") ===== -->')
box("atrium_stone", "visual", "stone_floor", 0, (AY0 + AY1) / 2, 0.026, (AX1 - AX0) / 2, (AY1 - AY0) / 2, 0.004)
box("atrium_deck", "visual", "deck_wood", 0, -6.0, 0.03, 5.5, 5.0, 0.004)
box("atrium_turf", "visual", "grass_turf", 0, -20.0, 0.03, 6.0, 3.5, 0.004)
TREES = []
for i, (px, py) in enumerate([(0.0, 6.5), (0.0, -6.0), (0.0, -15.0)]):
    box(f"planter_{i}", None, "planter", px, py, 0.35, 2.4, 1.6, 0.35)
    box(None, "visual", "deck_wood", px, py, 0.72, 2.6, 1.8, 0.03)
    for dx in (-1.2, 1.2):
        tx, ty = px + dx, py
        TREES.append((tx, ty))
        world.append(f'<body name="atrium_tree_{len(TREES)}" pos="{tx} {ty} 0.7">'
                     f'<geom type="capsule" size="0.12" fromto="0 0 0 0 0 3.6" material="bark"/>'
                     f'<geom type="ellipsoid" size="1.6 1.6 1.4" pos="0 0 4.3" material="foliage"/>'
                     f'<geom type="ellipsoid" size="1.2 1.2 1.0" pos="0.5 0.3 5.3" material="foliage_dark"/></body>')
    for dx, dy in ((-2.0, 1.2), (2.0, -1.2), (1.8, 1.3), (-1.9, -1.1)):
        world.append(f'<geom name="planter_shrub_{i}_{dx:+.0f}{dy:+.0f}" type="ellipsoid" size="0.6 0.6 0.5" pos="{px + dx} {py + dy} 1.0" material="foliage"/>')
# grand piano on the deck
world.append('<body name="grand_piano" pos="3.4 -8.6 0">'
             '<geom name="furn_piano_body" type="box" size="0.75 0.8 0.15" pos="0 0 0.85" material="piano"/>'
             '<geom name="furn_piano_lid" type="box" size="0.72 0.1 0.45" pos="0 0.5 1.28" euler="-0.9 0 0" material="piano"/>'
             '<geom name="furn_piano_leg" type="cylinder" size="0.05 0.35" pos="0 -0.55 0.35" material="piano"/>'
             '<geom name="furn_piano_keys" type="box" size="0.7 0.08 0.05" pos="0 -0.85 0.9" material="table_white"/>'
             '<geom name="furn_piano_bench" type="box" size="0.4 0.2 0.22" pos="0 -1.35 0.22" material="leather_black"/></body>')
# cafe tables with pink chairs along both long sides of the atrium
t = 0
for x in (-7.2, 7.2):
    for y in (9.5, 1.5, -11.5, -23.0):
        world.append(f'<body name="cafe_table_{t}" pos="{x} {y} 0">'
                     f'<geom name="furn_cafe_table_{t}" type="cylinder" size="0.55 0.02" pos="0 0 0.74" material="table_white"/>'
                     f'<geom name="furn_cafe_table_{t}_stem" type="cylinder" size="0.04 0.36" pos="0 0 0.37" material="steel"/>'
                     + "".join(f'<geom name="furn_cafe_chair_{t}_{j}" type="box" size="0.22 0.22 0.22" pos="{0.85*math.cos(a):.2f} {0.85*math.sin(a):.2f} 0.25" material="chair_pink"/>'
                               f'<geom name="furn_cafe_chair_{t}_{j}_back" type="box" size="0.22 0.04 0.2" pos="{1.05*math.cos(a):.2f} {1.05*math.sin(a):.2f} 0.65" euler="0 0 {a + math.pi/2:.3f}" material="chair_pink"/>'
                               for j, a in enumerate((0.0, math.pi / 2, math.pi, 3 * math.pi / 2)))
                     + '</body>')
        t += 1

# --------------------------------------------------------------------------
# restricted zone, intruder, docks, patrol routes, lights, cameras
# --------------------------------------------------------------------------
zx0, zx1, zy0, zy1 = WX0 + 0.2, CX0 - 0.2, -4.0 + 0.2, CY1 - 0.2
world.append('<!-- Restricted zone = VIP Lounge (scaffold name "substation_zone" kept for API compatibility) -->')
box("substation_zone", "visual", "restricted_soft", (zx0 + zx1) / 2, (zy0 + zy1) / 2, 0.035, (zx1 - zx0) / 2, (zy1 - zy0) / 2, 0.004)
world.append('<body name="human_intruder" pos="0 0 -10"><freejoint name="intruder_root"/>'
             '<geom name="intruder_geom" type="cylinder" size="0.28 0.85" material="intruder" mass="75.0" contype="0" conaffinity="0"/>'
             '<site name="intruder_head" pos="0 0 0.85"/></body>')
# docks sit ON each UAV's route so the first leg crosses no wall or tree canopy
world.append(f'<site name="dock_alpha" pos="0 {LOOP_Y0:.2f} 0.03" type="cylinder" size="0.6 0.01" rgba="0.95 0.75 0.1 1"/>')
world.append(f'<site name="dock_bravo" pos="{-(AX1 - BRAVO_INSET):.2f} -19.0 0.04" type="cylinder" size="0.6 0.01" rgba="0.95 0.75 0.1 1"/>')

loop = [(-LOOP_X, LOOP_Y0), (-LOOP_X, (LOOP_Y0 + LOOP_Y1) / 2), (-LOOP_X, LOOP_Y1), (0.0, LOOP_Y1),
        (LOOP_X, LOOP_Y1), (LOOP_X, (LOOP_Y0 + LOOP_Y1) / 2), (LOOP_X, LOOP_Y0), (0.0, LOOP_Y0)]
world.append(f'<!-- Alpha: ground-floor corridor loop at {ALPHA_Z} m (a guard\'s round) -->')
for i, (x, y) in enumerate(loop):
    world.append(f'<site name="patrol_cp{i}" pos="{x:.2f} {y:.2f} {ALPHA_Z}" type="sphere" size="0.15" rgba="0.1 0.85 0.55 0.6" group="4"/>')
bx, by0, by1 = AX1 - BRAVO_INSET, AY0 + BRAVO_INSET, AY1 - BRAVO_INSET
corners = [(-bx, by0), (-bx, by1), (bx, by1), (bx, by0)]
k = 0
world.append('<!-- Bravo: atrium sweep, one loop per gallery level, mid-storey height -->')
for f in range(1, N_FLOORS):
    z = f * FLOOR_H + 1.8
    for j, (x, y) in enumerate(corners):
        world.append(f'<site name="atrium_cp{k}" pos="{x:.2f} {y:.2f} {z:.2f}" type="sphere" size="0.15" rgba="0.2 0.5 1 0.6" group="4"/>')
        k += 1

world.append('<light name="skylight_sun" directional="true" pos="0 -7 60" dir="0.12 0.18 -1" diffuse="0.62 0.62 0.6" specular="0.1 0.1 0.1" castshadow="true"/>')
# NOTE: no spot lights -- in MuJoCo's renderer they left every surface outside
# their cones pure black (verified by toggling lights). A shadowless directional
# fill + emissive ceiling panels light the ground floor instead.
world.append('<light name="interior_fill" directional="true" pos="0 -18 30" dir="-0.25 0.15 -1" diffuse="0.38 0.37 0.35" specular="0 0 0" castshadow="false"/>')

def cam(name, pos, target, fovy=78):
    fx, fy, fz = (target[0] - pos[0], target[1] - pos[1], target[2] - pos[2])
    n = math.sqrt(fx * fx + fy * fy + fz * fz); fx, fy, fz = fx / n, fy / n, fz / n
    rx, ry, rz = fy * 1 - fz * 0, fz * 0 - fx * 1, 0.0          # right = fwd x up(0,0,1)
    rn = math.hypot(rx, ry); rx, ry = rx / rn, ry / rn
    ux, uy, uz = ry * fz - rz * fy, rz * fx - rx * fz, rx * fy - ry * fx
    world.append(f'<camera name="{name}" pos="{pos[0]} {pos[1]} {pos[2]}" '
                 f'xyaxes="{rx:.4f} {ry:.4f} {rz:.4f} {ux:.4f} {uy:.4f} {uz:.4f}" fovy="{fovy}"/>')


# validation cameras: each approximates one tour panorama's viewpoint
cam("atrium_view", (-6.5, -21.0, 1.6), (2.0, 5.0, 8.0))
cam("wall_of_fame_view", (-2.0, -23.5, 1.6), (-8.0, -29.0, 1.6))
cam("cafeteria_view", (17.6, 14.0, 1.6), (17.6, -10.0, 1.0))
cam("lift_lobby_view", (0.0, -29.6, 1.6), (0.0, -40.0, 1.3))
cam("vip_lounge_view", (-14.4, -3.2, 1.7), (-19.0, 10.0, 0.8))
cam("gallery_view", (-12.3, -12.0, 5 * FLOOR_H + 1.6), (11.0, -4.0, 4 * FLOOR_H))
cam("atrium_top", (0.0, -24.5, ROOF_Z - 3.0), (0.0, 4.0, 0.0), fovy=70)

custom = [
    "  <custom>",
    '    <text name="scene_name" data="NMIMS Main Building -- interior (atrium + ground floor)"/>',
    '    <text name="vision_cams" data="cam_alpha_fwd cam_bravo_fwd"/>',
    '    <numeric name="transit_alt" data="0"/>',
    '    <numeric name="alt_layer_bravo" data="0"/>',
    '    <numeric name="cruise_speed" data="2.5"/>',
    '    <numeric name="max_tilt_deg" data="15"/>',
    '    <numeric name="d_warn" data="4.5"/>',
    '    <numeric name="sidestep" data="0.4"/>',
    '    <numeric name="wind_scale" data="0.08"/>',
    '    <numeric name="yaw_mode_alpha" data="1"/>',
    '    <numeric name="yaw_mode_bravo" data="2"/>',
    f'    <numeric name="intruder_path" data="0 -50  0 -42  0 {LOOP_Y0:.1f}  {-LOOP_X:.1f} {LOOP_Y0:.1f}  {-LOOP_X:.1f} 4  -16.5 4  -18.5 9"/>',
    "  </custom>",
]

header = f"""<!-- ======================================================================
     GENERATED FILE -- do not hand-edit. Regenerate with:
         python models/scene_source/build_nmims_interior.py
     NMIMS Main Building INTERIOR, Vile Parle (West), Mumbai 400056.
     Shell: (c) OpenStreetMap contributors, ODbL 1.0. Atrium: satellite skylight.
     Appearance: NMIMS official virtual tour interior panoramas (reference only).
     Room placement ASSUMED -- see scene_source/interior_manifest.csv.
     ====================================================================== -->"""
xml = [header, "<mujoco>"] + custom + ["  <asset>"] + ["    " + a for a in assets] + ["  </asset>", "  <worldbody>"]
xml += ["    " + w for w in world] + ["  </worldbody>", "</mujoco>", ""]
open(OUT_XML, "w").write("\n".join(xml))

rows = [
    ("Building shell", "OSM way 791070239 convex hull", "MEASURED"),
    ("Atrium void 21.6 x 38.5 m", "satellite skylight, parallax-aligned to OSM", "MEASURED +/- ~2 m"),
    ("Storeys 10 x 3.6 m", "exterior panorama band count", "ASSUMED"),
    ("Gallery corridor width 3.0 m", "tour panoramas (Wall of Fame, Lifts)", "ASSUMED"),
    ("VIP Lounge, Board Room, Conference -- west wing", "tour links from Atrium/Entry", "ASSUMED"),
    ("Cafeteria -- east wing", "tour link Wall of Fame -> Cafeteria", "ASSUMED"),
    ("Lift lobby + entry foyer -- south wing", "satellite: lift cores in south wing", "PARTLY MEASURED"),
    ("Auditorium lobby -- north strip", "tour links", "ASSUMED"),
    ("Restricted zone = VIP Lounge", "design choice for the geofence", "DESIGN"),
]
with open(OUT_MANIFEST, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["element", "source", "status"]); w.writerows(rows)
loop_len = sum(math.dist(loop[i], loop[(i + 1) % len(loop)]) for i in range(len(loop)))
print(f"wrote {OUT_XML}")
print(f"  atrium {AX1 - AX0:.1f} x {AY1 - AY0:.1f} m, {N_FLOORS} floors, roof {ROOF_Z:.0f} m")
print(f"  Alpha corridor loop {loop_len:.0f} m at {ALPHA_Z} m; Bravo atrium sweep {k} waypoints over {N_FLOORS - 1} levels")
