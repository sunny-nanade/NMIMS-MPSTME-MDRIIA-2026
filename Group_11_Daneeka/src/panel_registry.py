"""Single source of truth for the solar-farm layout and panel identifiers.

Coordinate convention (used by Blender, MuJoCo and every Python module):
    world frame = local ENU:  +x = East, +y = North, +z = Up   [metres]
Rows run East-West (along +x). Panels face true South, tilted up from the
horizontal by ``tilt_deg``; the panel normal is therefore
    n = (0, -sin(tilt), +cos(tilt))
and the "up-slope" direction (from the low edge to the high edge) is
    u = (0, +cos(tilt), +sin(tilt)).

Panel IDs have the form ``PV_R<row>_C<col>`` (1-based, zero padded), e.g.
``PV_R01_C01``. The MJCF generator, the Blender script, the solar model, the
sensors, the detector and the analytics all take IDs from this module.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FarmConfig:
    n_rows: int = 4
    n_cols: int = 10
    panel_w: float = 1.00        # width along the row (x) [m]
    panel_l: float = 1.70        # length along the slope [m]
    panel_t: float = 0.035       # glass+frame thickness [m]
    col_pitch: float = 1.05      # centre-to-centre spacing along the row [m]
    tilt_deg: float = 20.0       # fixed tilt from horizontal [deg]
    z_low: float = 0.55          # height of the low (south) edge above ground [m]
    row_pitch: float = 6.0       # distance between low edges of adjacent rows (y) [m]
    lane_offset: float = 1.9     # lane centre-line lies this far south of the low edge [m]
    cells_along: int = 10        # cell rows along the slope (60-cell module = 10 x 6)
    cells_across: int = 6        # cell columns across the width
    frame_w: float = 0.03        # aluminium frame width [m]
    panel_wp: float = 400.0      # rated power per module [Wp]  (assumption)
    x0: float = 0.0              # west end of row 1 [m]
    y0: float = 0.0              # y of low edge of row 1 [m]
    kerb_half_gap: float = 1.1   # kerb strips sit +/- this from the lane centre-line [m]
    dock_x: float = -4.0         # dock pose (robot centre) [m]
    headland: float = 3.0        # free turning space beyond each row end [m]
    marker_every: int = 5        # a fiducial post marker every N columns (and at both ends)

    @property
    def n_panels(self) -> int:
        return self.n_rows * self.n_cols

    @property
    def tilt(self) -> float:
        return math.radians(self.tilt_deg)

    @property
    def row_length(self) -> float:
        return self.n_cols * self.col_pitch

    @property
    def farm_mw(self) -> float:
        return self.n_panels * self.panel_wp / 1e6


_ID_RE = re.compile(r"^PV_R(\d{2})_C(\d{2})$")


def make_id(row: int, col: int) -> str:
    return f"PV_R{row:02d}_C{col:02d}"


def parse_id(pid: str) -> tuple[int, int]:
    m = _ID_RE.match(pid)
    if not m:
        raise ValueError(f"bad panel id: {pid!r}")
    return int(m.group(1)), int(m.group(2))


@dataclass(frozen=True)
class PanelSpec:
    pid: str
    index: int
    row: int
    col: int
    center: np.ndarray       # (3,)
    normal: np.ndarray       # (3,)
    up_slope: np.ndarray     # (3,)
    along_row: np.ndarray    # (3,)


class PanelRegistry:
    """Geometry + identity of every module. Immutable after construction."""

    def __init__(self, cfg: FarmConfig | None = None):
        self.cfg = cfg or FarmConfig()
        c = self.cfg
        th = c.tilt
        self.normal = np.array([0.0, -math.sin(th), math.cos(th)])
        self.up_slope = np.array([0.0, math.cos(th), math.sin(th)])
        self.along_row = np.array([1.0, 0.0, 0.0])

        self.panels: list[PanelSpec] = []
        self._by_id: dict[str, PanelSpec] = {}
        centers = []
        for r in range(1, c.n_rows + 1):
            for k in range(1, c.n_cols + 1):
                cx = c.x0 + (k - 0.5) * c.col_pitch
                cy = self.row_low_y(r) + 0.5 * c.panel_l * math.cos(th)
                cz = c.z_low + 0.5 * c.panel_l * math.sin(th)
                spec = PanelSpec(
                    pid=make_id(r, k), index=len(self.panels), row=r, col=k,
                    center=np.array([cx, cy, cz]), normal=self.normal,
                    up_slope=self.up_slope, along_row=self.along_row)
                self.panels.append(spec)
                self._by_id[spec.pid] = spec
                centers.append(spec.center)
        self.centers = np.array(centers)                      # (N,3)
        self.ids = [p.pid for p in self.panels]
        self.rows = np.array([p.row for p in self.panels])
        self.cols = np.array([p.col for p in self.panels])

        # cell centres (N, A, C, 3): i along slope (0 = low edge), j across (0 = west)
        A, C = c.cells_along, c.cells_across
        cw = (c.panel_w - 2 * c.frame_w) / C
        cl = (c.panel_l - 2 * c.frame_w) / A
        self.cell_w, self.cell_l = cw, cl
        ii = (np.arange(A) - (A - 1) / 2.0) * cl
        jj = (np.arange(C) - (C - 1) / 2.0) * cw
        off = (ii[:, None, None] * self.up_slope[None, None, :]
               + jj[None, :, None] * self.along_row[None, None, :])   # (A,C,3)
        self.cell_offsets = off
        self.cell_centers = self.centers[:, None, None, :] + off[None]  # (N,A,C,3)

    # ------------------------------------------------------------------ ids
    def __len__(self) -> int:
        return len(self.panels)

    def get(self, pid: str) -> PanelSpec:
        return self._by_id[pid]

    def index(self, pid: str) -> int:
        return self._by_id[pid].index

    def pid_at(self, row: int, col: int) -> str:
        return make_id(row, col)

    # ------------------------------------------------------------- geometry
    def row_low_y(self, row: int) -> float:
        return self.cfg.y0 + (row - 1) * self.cfg.row_pitch

    def lane_y(self, row: int) -> float:
        """y of the lane centre-line from which row ``row`` is inspected."""
        return self.row_low_y(row) - self.cfg.lane_offset

    def panel_x(self, col: int) -> float:
        return self.cfg.x0 + (col - 0.5) * self.cfg.col_pitch

    def plane_y_at_height(self, row: int, z: float) -> float:
        """y where the panel plane of ``row`` crosses height z (for range sensing)."""
        c = self.cfg
        return self.row_low_y(row) + (z - c.z_low) / math.tan(c.tilt)

    @property
    def x_west(self) -> float:
        return self.cfg.x0

    @property
    def x_east(self) -> float:
        return self.cfg.x0 + self.cfg.row_length

    @property
    def dock_pose(self) -> tuple[float, float, float]:
        return (self.cfg.dock_x, self.lane_y(1), 0.0)   # x, y, heading (east)

    def marker_xs(self) -> list[float]:
        c = self.cfg
        xs = [c.x0 + k * c.col_pitch for k in range(0, c.n_cols + 1, c.marker_every)]
        if abs(xs[-1] - self.x_east) > 1e-9:
            xs.append(self.x_east)
        return xs

    def rect_occluders(self) -> dict:
        """One long rectangle per row (gaps between modules ignored) for shading tests."""
        c = self.cfg
        out = {"center": [], "half_w": [], "half_l": []}
        for r in range(1, c.n_rows + 1):
            cx = c.x0 + 0.5 * c.row_length
            cy = self.row_low_y(r) + 0.5 * c.panel_l * math.cos(c.tilt)
            cz = c.z_low + 0.5 * c.panel_l * math.sin(c.tilt)
            out["center"].append([cx, cy, cz])
            out["half_w"].append(0.5 * c.row_length)
            out["half_l"].append(0.5 * c.panel_l)
        out["center"] = np.array(out["center"])
        out["half_w"] = np.array(out["half_w"])
        out["half_l"] = np.array(out["half_l"])
        return out

    def hit_panel(self, origin: np.ndarray, direction: np.ndarray,
                  margin: float = 0.0):
        """Intersect a ray with the panel planes. Returns (panel_index, hit_xyz, t) or None.

        The nearest forward intersection that lies within a module's rectangle
        (shrunk by ``margin`` metres) wins.
        """
        d = np.asarray(direction, float)
        o = np.asarray(origin, float)
        denom = float(self.normal @ d)
        if abs(denom) < 1e-9:
            return None
        best = None
        for r in range(1, self.cfg.n_rows + 1):
            c0 = self.centers[(r - 1) * self.cfg.n_cols]
            t = float(self.normal @ (c0 - o)) / denom
            if t <= 0:
                continue
            p = o + t * d
            k = self._col_of_x(p[0])
            if k is None:
                continue
            spec = self._by_id[make_id(r, k)]
            rel = p - spec.center
            if (abs(rel @ self.along_row) <= self.cfg.panel_w / 2 - margin and
                    abs(rel @ self.up_slope) <= self.cfg.panel_l / 2 - margin):
                if best is None or t < best[2]:
                    best = (spec.index, p, t)
        return best

    def _col_of_x(self, x: float):
        c = self.cfg
        k = int(math.floor((x - c.x0) / c.col_pitch)) + 1
        return k if 1 <= k <= c.n_cols else None

    def nearest_col(self, x: float) -> int:
        """Column index (1-based) whose centre is nearest to x (clipped to the row)."""
        c = self.cfg
        k = int(round((x - c.x0) / c.col_pitch + 0.5))
        return max(1, min(c.n_cols, k))

    def cell_position(self, panel_index: int, i: int, j: int) -> np.ndarray:
        return self.cell_centers[panel_index, i, j]
