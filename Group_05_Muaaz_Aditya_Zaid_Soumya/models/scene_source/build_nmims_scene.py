#!/usr/bin/env python3
"""
NMIMS Main Building campus scene generator | MDRIIA Group 05
Owner: E043 Muaaz Mohammed Iqbal Shaikh (scene + flight environment)

Builds models/nmims_main_campus.xml -- the static world the dual-UAV patrol
flies in -- from two real sources:

  1. GEOMETRY  OpenStreetMap extract (nmims_main_osm_extract.json):
               building footprints, campus boundary, roads, traffic signals,
               in metres. (c) OpenStreetMap contributors, ODbL 1.0.
  2. APPEARANCE  NMIMS official virtual tour, exterior panorama "Main Building"
               (https://nmims.edu/virtual-tour-nmims-main-mumbai.php):
               white curved-corner block, ribbed balcony bands, ~10 storeys,
               trees along the boundary wall, autos parked on Gulmohar Road.
               Used as visual reference only -- no tour imagery is embedded.

Everything that is NOT measured is marked ASSUMED here and in
building_manifest.csv. Fix those values on site; do not cite them as data.

Frame: local ENU, metres. Origin = OSM campus point 19.10344 N, 72.83646 E.
       +x = East, +y = North, +z = Up.

  python models/scene_source/build_nmims_scene.py
"""
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.dirname(HERE)
SRC = os.path.join(HERE, "nmims_main_osm_extract.json")
OUT_XML = os.path.join(MODELS, "nmims_main_campus.xml")
OUT_MANIFEST = os.path.join(HERE, "building_manifest.csv")

LAT0, LON0 = 19.10344, 72.83646
R_EARTH = 6378137.0

MAIN_BUILDING_ID = 791070239       # OSM way: NMIMS Main Building footprint
CAMPUS_ID = 1170351966             # OSM way: NMIMS campus boundary
CONTEXT_RADIUS = 165.0             # m, surrounding buildings kept for context/occlusion
ROAD_CLIP = 210.0                  # m, half-size of the square roads are clipped to

# ---- main building: storey count ESTIMATED from the tour panorama (G+9) ----
MAIN_FLOORS = 10                   # ASSUMED -- count from panorama, verify on site
FLOOR_H = 3.6                      # m, ASSUMED typical academic floor-to-floor
BAND_H = 1.45                      # m, white balcony parapet band per floor
FIN_SPACING = 4.2                  # m, vertical balcony fins (cellular facade in the panorama)
CORE_INSET = 1.4                   # m, recessed glazing line behind the bands
MAIN_HEIGHT = MAIN_FLOORS * FLOOR_H

WALL_H, WALL_T = 2.4, 0.25         # m, ASSUMED boundary wall
PATROL_INSET = 3.0                 # m, patrol ring = boundary wall line offset INWARD (patrolling stays inside
                                   # the college). The tightest wall-to-building gap is ~5.4 m (east side), so
                                   # 3.0 m leaves >= 2.4 m to the main building at patrol altitude (FR-18
                                   # minimum lateral clearance 0.6 m) and 3.0 m to the wall line; checked with
                                   # mj_ray in tests/test_e043_exterior_route_inside_campus.py
ROUTE_ALT = 22.0                   # m, Alpha patrol layer; Bravo +4 m. Clears the ~15 m canopy and every roof within
                                   # the sidestep reach of a leg by >= H_BAND + D_STOP_V (FR-18), checked in
                                   # tests/test_e043_exterior_route_inside_campus.py. 20 m sat 0.8 m above the 19.2 m
                                   # roof of bldg_791070237_0 (1.6 m north of leg patrol_cp6 -> cp7): the separation
                                   # governor, catching up on Bravo 4 m above, pushed Alpha down and right (north)
                                   # into its roof edge (main batch, exterior offset_ring seeds 7, 13, 19, 21, 22).
FLOOR_H_CONTEXT = 3.2              # m per storey for surrounding buildings

# storeys used when OSM has no building:levels -- ASSUMED, by building type
DEFAULT_LEVELS = {"apartments": 6, "residential": 6, "college": 5, "school": 4,
                  "university": 6, "hospital": 8, "commercial": 6, "yes": 3}

ROAD_WIDTH = {"trunk": 18, "primary": 14, "secondary": 12, "tertiary": 9,
              "primary_link": 7, "secondary_link": 7, "residential": 6,
              "service": 4, "unclassified": 6}


from osm_geometry import (enu, ring, signed_area, centroid, convex_hull, offset_polygon,  # noqa: E402
                          ear_clip, prism_vertices)

# --------------------------------------------------------------------------
# load OSM
# --------------------------------------------------------------------------
data = json.load(open(SRC))
els = [e for e in data["elements"] if "geometry" in e or e["type"] == "node"]
by_id = {e["id"]: e for e in els}
osm_stamp = data.get("osm3s", {}).get("timestamp_osm_base", "unknown")

main_fp = ring(by_id[MAIN_BUILDING_ID])
campus = ring(by_id[CAMPUS_ID])

assets, world, manifest = [], [], []

# --------------------------------------------------------------------------
# main building -- collision hull + banded visual facade
# --------------------------------------------------------------------------
hull = convex_hull(main_fp)
core = offset_polygon(hull, -CORE_INSET)
assets += [
    f'<mesh name="nmims_main_collision" vertex="{prism_vertices(hull, 0.0, MAIN_HEIGHT)}"/>',
    f'<mesh name="nmims_main_core" vertex="{prism_vertices(core, 0.0, MAIN_HEIGHT - 0.06)}"/>',
    f'<mesh name="nmims_main_roof" vertex="{prism_vertices(offset_polygon(hull, -0.3), 0.0, 0.25)}"/>',
    f'<mesh name="nmims_main_band" vertex="{prism_vertices(hull, 0.0, BAND_H)}"/>',
    f'<mesh name="nmims_main_podium" vertex="{prism_vertices(offset_polygon(hull, -0.6), 0.0, FLOOR_H)}"/>',
]
world.append('<!-- ===== NMIMS MAIN BUILDING  (OSM way %d, footprint %.0f m2) =====' % (MAIN_BUILDING_ID, abs(signed_area(main_fp))))
world.append('     %d storeys x %.1f m = %.1f m  -- storey count ASSUMED from tour panorama -->' % (MAIN_FLOORS, FLOOR_H, MAIN_HEIGHT))
world.append('<body name="nmims_main_building">')
world.append('  <geom name="nmims_main_collision" type="mesh" mesh="nmims_main_collision" group="3" rgba="1 0 0 0.15"/>')
world.append('  <geom name="nmims_main_core" type="mesh" mesh="nmims_main_core" class="visual" material="glazing"/>')
world.append('  <geom name="nmims_main_podium" type="mesh" mesh="nmims_main_podium" class="visual" material="podium"/>')
for k in range(1, MAIN_FLOORS + 1):
    z = k * FLOOR_H - (BAND_H if k == MAIN_FLOORS else 0.0)
    world.append(f'  <geom name="nmims_band_{k:02d}" type="mesh" mesh="nmims_main_band" class="visual" material="facade_white" pos="0 0 {z:.2f}"/>')
world.append(f'  <geom name="nmims_roof" type="mesh" mesh="nmims_main_roof" class="visual" material="roof" pos="0 0 {MAIN_HEIGHT - 0.2:.2f}"/>')
# vertical fins: thin white blades spanning the recess between glazing line and band edge
fin = 0
for i in range(len(hull)):
    (x1, y1), (x2, y2) = hull[i], hull[(i + 1) % len(hull)]
    L = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = uy, -ux                                   # outward normal (CCW hull)
    yaw = math.atan2(uy, ux)
    for k in range(1, max(1, int(L // FIN_SPACING))):
        s_ = k * L / max(1, int(L // FIN_SPACING))
        fx = x1 + ux * s_ - nx * CORE_INSET / 2
        fy = y1 + uy * s_ - ny * CORE_INSET / 2
        zc = (FLOOR_H + MAIN_HEIGHT) / 2
        world.append(f'  <geom name="nmims_fin_{fin}" type="box" class="visual" material="facade_white" '
                     f'size="0.12 {CORE_INSET/2:.2f} {(MAIN_HEIGHT - FLOOR_H)/2:.2f}" pos="{fx:.2f} {fy:.2f} {zc:.2f}" euler="0 0 {yaw:.4f}"/>')
        fin += 1
cx, cy = centroid(hull)
world.append(f'  <geom name="nmims_lift_room" type="box" class="visual" material="facade_white" size="6 4 2.2" pos="{cx:.2f} {cy:.2f} {MAIN_HEIGHT + 2.2:.2f}"/>')
world.append(f'  <site name="dock_alpha" pos="{cx + 9:.2f} {cy + 18:.2f} {MAIN_HEIGHT + 0.02:.2f}" type="cylinder" size="0.7 0.01" rgba="0.95 0.75 0.1 1"/>')
world.append(f'  <site name="dock_bravo" pos="{cx - 9:.2f} {cy - 18:.2f} {MAIN_HEIGHT + 0.02:.2f}" type="cylinder" size="0.7 0.01" rgba="0.95 0.75 0.1 1"/>')
world.append('</body>')
manifest.append(dict(osm_id=MAIN_BUILDING_ID, name="NMIMS Main Building", type="college",
                     levels=MAIN_FLOORS, levels_source="ASSUMED (tour panorama count)",
                     height_m=round(MAIN_HEIGHT, 1), footprint_m2=round(abs(signed_area(main_fp))),
                     representation="convex hull"))

# --------------------------------------------------------------------------
# campus ground, boundary wall, patrol ring
# --------------------------------------------------------------------------
# exact triangulation -- a convex hull would spill paving outside the concave wall line
paving = ear_clip(campus)
for j, tri in enumerate(paving):
    assets.append(f'<mesh name="campus_paving_{j}" vertex="{prism_vertices(tri, 0.0, 0.03)}"/>')
world.append('<!-- ===== CAMPUS BOUNDARY (OSM way %d) =====  wall height ASSUMED -->' % CAMPUS_ID)
for j in range(len(paving)):
    world.append(f'<geom name="campus_paving_{j}" type="mesh" mesh="campus_paving_{j}" class="visual" material="paving"/>')
for i in range(len(campus)):
    (x1, y1), (x2, y2) = campus[i], campus[(i + 1) % len(campus)]
    L = math.hypot(x2 - x1, y2 - y1)
    yaw = math.atan2(y2 - y1, x2 - x1)
    world.append(f'<geom name="boundary_wall_{i}" type="box" material="wall" '
                 f'size="{L/2 + WALL_T/2:.3f} {WALL_T/2:.3f} {WALL_H/2:.3f}" '
                 f'pos="{(x1+x2)/2:.3f} {(y1+y2)/2:.3f} {WALL_H/2:.3f}" euler="0 0 {yaw:.5f}"/>')

patrol = offset_polygon(campus, -PATROL_INSET)
world.append(f'<!-- ===== PATROL RING: campus boundary offset {PATROL_INSET:.0f} m INWARD, inside the wall ('
             f'{sum(math.dist(patrol[i], patrol[(i+1) % len(patrol)]) for i in range(len(patrol))):.0f} m) =====')
world.append('     Read by name (patrol_cp*) from Python -- the model is the single source of truth. -->')
for i, (x, y) in enumerate(patrol):
    # waypoint at route altitude (read by the controller) + a ground disc to see it
    world.append(f'<site name="patrol_cp{i}" pos="{x:.3f} {y:.3f} {ROUTE_ALT:.1f}" type="sphere" size="0.25" rgba="0.1 0.85 0.55 0.5" group="4"/>')
    world.append(f'<geom name="patrol_mark{i}" class="visual" type="cylinder" size="1.2 0.02" pos="{x:.3f} {y:.3f} 0.06" material="checkpoint"/>')

# restricted zone + intruder (scene-specific; names kept from the course scaffold)
world.append('<!-- Restricted zone: electrical substation / service yard. LOCATION ASSUMED. -->')
world.append('<geom name="substation_zone" class="visual" type="box" material="restricted" size="9 4 0.02" pos="-21 28.5 0.05"/>')
world.append('<body name="human_intruder" pos="0 0 -10"><freejoint name="intruder_root"/>'
             '<geom name="intruder_geom" type="cylinder" size="0.28 0.85" material="intruder" mass="75.0" contype="0" conaffinity="0"/>'
             '<site name="intruder_head" pos="0 0 0.85"/></body>')

# --------------------------------------------------------------------------
# trees along the street frontages (seen in the tour panorama)
# --------------------------------------------------------------------------
world.append('<!-- ===== TREES along V.L. Mehta Rd (south) and Gulmohar Rd (east) frontages =====')
world.append('     canopy tops ~15 m, ASSUMED from the panorama; they DO occlude the gimbal cameras -->')
south_east_edges = []
for i in range(len(campus)):
    a, b = campus[i], campus[(i + 1) % len(campus)]
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if mid[1] < -45 or mid[0] > 25:     # south arc and east side
        south_east_edges.append((a, b))
t_id = 0
for a, b in south_east_edges:
    L = math.dist(a, b)
    n = max(1, int(L // 7.0))
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -uy, ux                    # inward normal for CCW polygon
    for k in range(n):
        s = (k + 0.5) * L / n
        x, y = a[0] + ux * s + nx * 2.6, a[1] + uy * s + ny * 2.6
        if t_id % 2 == 0:               # broad canopy (rain tree / gulmohar type)
            world.append(f'<body name="tree_{t_id}" pos="{x:.2f} {y:.2f} 0">'
                         f'<geom type="capsule" size="0.3" fromto="0 0 0 0 0 7.5" material="bark"/>'
                         f'<geom type="ellipsoid" size="3.6 3.6 3.2" pos="0 0 11.4" material="foliage"/></body>')
        else:                           # columnar mast tree (Polyalthia longifolia)
            world.append(f'<body name="tree_{t_id}" pos="{x:.2f} {y:.2f} 0">'
                         f'<geom type="capsule" size="0.18" fromto="0 0 0 0 0 3" material="bark"/>'
                         f'<geom type="ellipsoid" size="1.15 1.15 6.2" pos="0 0 8.8" material="foliage_dark"/></body>')
        t_id += 1

# --------------------------------------------------------------------------
# parked autos / tempos / cars along Gulmohar Road (panorama detail)
# --------------------------------------------------------------------------
world.append('<!-- ===== Parked vehicles on Gulmohar Rd (visual only) ===== -->')
def park_along(a, b, kinds, k0, start=3.0, gap=5.4):
    L = math.dist(a, b); ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L; nx, ny = uy, -ux
    yaw = math.atan2(uy, ux); out = []
    for j, kind in enumerate(kinds):
        s_ = start + j * gap
        if s_ > L - 3:
            break
        x, y = a[0] + ux * s_ + nx * 2.4, a[1] + uy * s_ + ny * 2.4
        k = k0 + j
        if kind == "auto":
            out.append(f'<body name="parked_{k}" pos="{x:.2f} {y:.2f} 0" euler="0 0 {yaw:.4f}">'
                       f'<geom class="visual" type="box" size="1.3 0.65 0.55" pos="0 0 0.75" material="auto_black"/>'
                       f'<geom class="visual" type="box" size="1.05 0.62 0.07" pos="-0.1 0 1.65" material="auto_yellow"/></body>')
        elif kind == "tempo":
            out.append(f'<body name="parked_{k}" pos="{x:.2f} {y:.2f} 0" euler="0 0 {yaw:.4f}">'
                       f'<geom class="visual" type="box" size="2.3 0.9 1.1" pos="0 0 1.2" material="tempo"/>'
                       f'<geom class="visual" type="box" size="0.6 0.88 0.8" pos="1.9 0 0.95" material="tempo_cab"/></body>')
        else:
            out.append(f'<body name="parked_{k}" pos="{x:.2f} {y:.2f} 0" euler="0 0 {yaw:.4f}">'
                       f'<geom class="visual" type="box" size="2.1 0.85 0.5" pos="0 0 0.65" material="car_silver"/>'
                       f'<geom class="visual" type="box" size="1.2 0.8 0.35" pos="-0.2 0 1.4" material="car_silver"/></body>')
    return out

mix = ["auto", "car", "tempo", "auto", "auto", "car", "tempo", "auto", "car", "auto", "auto", "tempo"]
n_parked = 0
for a, b in south_east_edges:
    if math.dist(a, b) < 12:
        continue
    block = park_along(a, b, mix, n_parked)
    world.extend(block); n_parked += len(block)

# --------------------------------------------------------------------------
# surrounding buildings (context + occlusion)
# --------------------------------------------------------------------------
world.append('<!-- ===== SURROUNDING BUILDINGS within %.0f m (OSM; heights mostly ASSUMED) ===== -->' % CONTEXT_RADIUS)
for e in els:
    t = e.get("tags", {})
    if e["type"] != "way" or "building" not in t or e["id"] in (MAIN_BUILDING_ID, CAMPUS_ID):
        continue
    P = ring(e)
    if len(P) < 3 or math.hypot(*centroid(P)) > CONTEXT_RADIUS:
        continue
    if "building:levels" in t:
        try:
            levels, src = int(float(t["building:levels"])), "OSM building:levels"
        except ValueError:
            levels, src = DEFAULT_LEVELS.get(t["building"], 3), "ASSUMED (bad OSM levels)"
    else:
        levels, src = DEFAULT_LEVELS.get(t["building"], 3), f"ASSUMED (type={t['building']})"
    h = levels * FLOOR_H_CONTEXT
    area = abs(signed_area(P))
    hullP = convex_hull(P)
    pieces = [hullP] if abs(signed_area(hullP)) <= 1.15 * area else ear_clip(P)
    rep = "convex hull" if len(pieces) == 1 else f"{len(pieces)} convex pieces"
    mat = "context_college" if t["building"] in ("college", "university", "school") else "context"
    for j, piece in enumerate(pieces):
        nm = f"bldg_{e['id']}_{j}"
        assets.append(f'<mesh name="{nm}" vertex="{prism_vertices(piece, 0.0, h)}"/>')
        world.append(f'<geom name="{nm}" type="mesh" mesh="{nm}" material="{mat}"/>')
    manifest.append(dict(osm_id=e["id"], name=t.get("name", ""), type=t["building"], levels=levels,
                         levels_source=src, height_m=round(h, 1), footprint_m2=round(area),
                         representation=rep))

# --------------------------------------------------------------------------
# roads and junction signals
# --------------------------------------------------------------------------
world.append('<!-- ===== ROADS (OSM highways), visual only ===== -->')
seg = 0
for e in els:
    t = e.get("tags", {})
    if e["type"] != "way" or "highway" not in t or t["highway"] not in ROAD_WIDTH:
        continue
    w = ROAD_WIDTH[t["highway"]]
    pts = [enu(p) for p in e["geometry"]]
    road_i = e["id"] % 7
    z = (0.016 if w >= 9 else 0.010) + 0.0015 * road_i      # stagger tops to avoid z-fighting
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if max(abs(x1), abs(x2), abs(y1), abs(y2)) > ROAD_CLIP:
            continue
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 0.05:
            continue
        world.append(f'<geom name="road_{seg}" class="visual" type="box" material="asphalt" '
                     f'size="{L/2:.2f} {w/2:.2f} {z:.3f}" pos="{(x1+x2)/2:.2f} {(y1+y2)/2:.2f} 0" '
                     f'euler="0 0 {math.atan2(y2-y1, x2-x1):.5f}"/>')
        world.append(f'<geom class="visual" type="cylinder" material="asphalt" size="{w/2:.2f} {z:.3f}" pos="{x2:.2f} {y2:.2f} 0"/>')
        seg += 1
for e in els:
    if e["type"] == "node" and e.get("tags", {}).get("highway") == "traffic_signals":
        x, y = enu(e)
        world.append(f'<body name="signal_{e["id"]}" pos="{x:.2f} {y:.2f} 0">'
                     f'<geom type="cylinder" size="0.09 2.8" pos="0 0 2.8" material="pole"/>'
                     f'<geom class="visual" type="box" size="0.18 0.18 0.55" pos="0 0 5.2" material="pole"/>'
                     f'<geom class="visual" type="sphere" size="0.12" pos="0.19 0 5.5" rgba="0.9 0.1 0.1 1"/>'
                     f'<geom class="visual" type="sphere" size="0.12" pos="0.19 0 4.95" rgba="0.1 0.85 0.3 1"/></body>')

# --------------------------------------------------------------------------
# emit
# --------------------------------------------------------------------------
header = f"""<!-- ======================================================================
     GENERATED FILE -- do not hand-edit. Regenerate with:
         python models/scene_source/build_nmims_scene.py
     NMIMS Main Building campus, V.L. Mehta Road x Gulmohar Road,
     Vile Parle (West), Mumbai 400056.
     Geometry: (c) OpenStreetMap contributors, ODbL 1.0  (extract {osm_stamp})
     Appearance reference: NMIMS official virtual tour, exterior panorama.
     Frame: local ENU metres, origin {LAT0} N {LON0} E, +x East, +y North.
     Values marked ASSUMED are estimates -- see building_manifest.csv.
     ====================================================================== -->"""
custom = [
    "  <custom>",
    '    <text name="scene_name" data="NMIMS campus -- inside the boundary wall"/>',
    '    <text name="vision_cams" data="cam_alpha cam_bravo"/>',
    '    <numeric name="transit_alt" data="44"/>',
    '    <numeric name="alt_layer_bravo" data="4"/>',
    '    <numeric name="cruise_speed" data="6"/>',
    '    <numeric name="max_tilt_deg" data="28"/>',
    '    <numeric name="d_warn" data="14"/>',
    '    <numeric name="sidestep" data="1.6"/>',
    '    <numeric name="wind_scale" data="1"/>',
    '    <numeric name="intruder_path" data="-21 41  -21 34  -21 29  -14 29"/>',
    "  </custom>",
]
xml = [header, "<mujoco>"] + custom + ["  <asset>"]
xml += ["    " + a for a in assets]
xml += ["  </asset>", "  <worldbody>"]
xml += ["    " + w for w in world]
xml += ["  </worldbody>", "</mujoco>", ""]
open(OUT_XML, "w").write("\n".join(xml))

with open(OUT_MANIFEST, "w", newline="") as fh:
    cw = csv.DictWriter(fh, fieldnames=list(manifest[0].keys()))
    cw.writeheader()
    cw.writerows(manifest)

print(f"wrote {OUT_XML}")
print(f"  main building: {MAIN_FLOORS} floors, {MAIN_HEIGHT:.1f} m, footprint {abs(signed_area(main_fp)):.0f} m2")
print(f"  campus boundary: {len(campus)} wall segments; patrol ring {len(patrol)} checkpoints")
print(f"  context buildings: {len(manifest) - 1}  | trees: {t_id} | parked vehicles: {n_parked} | road segments: {seg}")
print(f"wrote {OUT_MANIFEST}")
