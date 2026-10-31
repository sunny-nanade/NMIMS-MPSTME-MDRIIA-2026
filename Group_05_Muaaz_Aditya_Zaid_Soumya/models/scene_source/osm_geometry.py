"""
Shared OSM geometry helpers for the NMIMS scene generators | Owner: E043 Muaaz
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "nmims_main_osm_extract.json")
LAT0, LON0 = 19.10344, 72.83646        # ENU origin (OSM NMIMS campus point)
R_EARTH = 6378137.0
MAIN_BUILDING_ID = 791070239            # OSM way: NMIMS Main Building footprint
CAMPUS_ID = 1170351966                  # OSM way: NMIMS campus boundary


def enu(p):
    x = math.radians(p["lon"] - LON0) * math.cos(math.radians(LAT0)) * R_EARTH
    y = math.radians(p["lat"] - LAT0) * R_EARTH
    return (x, y)


def ring(e):
    P = [enu(p) for p in e["geometry"]]
    if P[0] == P[-1]:
        P = P[:-1]
    if signed_area(P) < 0:              # normalise to counter-clockwise
        P = P[::-1]
    return P


def signed_area(P):
    return 0.5 * sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
                     for i in range(len(P)))


def centroid(P):
    return (sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P))


def convex_hull(P):
    pts = sorted(set(P))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def offset_polygon(P, d):
    """Miter offset of a CCW polygon; d > 0 grows it outward."""
    n = len(P)
    lines = []
    for i in range(n):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % n]
        L = math.hypot(x2 - x1, y2 - y1)
        nx, ny = (y2 - y1) / L, -(x2 - x1) / L       # outward normal for CCW
        lines.append(((x1 + nx * d, y1 + ny * d), (x2 + nx * d, y2 + ny * d)))
    out = []
    for i in range(n):
        (a1, a2), (b1, b2) = lines[i - 1], lines[i]
        dax, day = a2[0] - a1[0], a2[1] - a1[1]
        dbx, dby = b2[0] - b1[0], b2[1] - b1[1]
        den = dax * dby - day * dbx
        if abs(den) < 1e-9:
            out.append(b1)
            continue
        t = ((b1[0] - a1[0]) * dby - (b1[1] - a1[1]) * dbx) / den
        out.append((a1[0] + t * dax, a1[1] + t * day))
    return out


def ear_clip(P):
    """Triangulate a simple CCW polygon into convex pieces (MuJoCo meshes are convex)."""
    idx = list(range(len(P)))
    tris = []
    def is_convex(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 1e-9
    def inside(p, a, b, c):
        def s(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = P[i0], P[i1], P[i2]
            if not is_convex(a, b, c):
                continue
            if any(inside(P[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append([a, b, c])
            idx.pop(k)
            break
        else:
            break                       # degenerate polygon -- fall back below
    if len(idx) == 3:
        tris.append([P[i] for i in idx])
    return tris


def prism_vertices(P, z0, z1):
    return " ".join(f"{x:.3f} {y:.3f} {z:.3f}" for z in (z0, z1) for (x, y) in P)




def clip_halfplane(P, a, b, c):
    """Sutherland-Hodgman: keep the part of convex polygon P where a*x + b*y <= c."""
    out = []
    n = len(P)
    for i in range(n):
        p, q = P[i], P[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def load_osm():
    data = json.load(open(SRC))
    els = [e for e in data["elements"] if "geometry" in e or e["type"] == "node"]
    return data, els, {e["id"]: e for e in els}
