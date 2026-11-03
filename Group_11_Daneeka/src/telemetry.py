"""500 Hz telemetry recorder (one row per physics step) with metadata header."""
from __future__ import annotations

import numpy as np

COLUMNS = ["t", "seed", "condition", "state", "x_true", "y_true", "yaw_true", "x_est", "y_est", "yaw_est",
           "v_cmd", "w_cmd", "w_left", "w_right", "tau_left", "tau_right", "pan", "tilt", "lift",
           "lane_y_ref", "cross_track_err", "heading_err", "d_sensor", "tau2_cum"]
STATE_NAMES = ["INIT", "ROW_FOLLOW", "SCAN", "ANOMALY_FLAG", "GEOTAG", "NEXT_ROW", "RETURN_TO_DOCK", "DONE"]


class Telemetry:
    def __init__(self, capacity: int, seed: int, condition: str):
        self.n = 0
        self.seed, self.condition = seed, condition
        self.buf = np.full((capacity, len(COLUMNS)), np.nan)

    def log(self, **kw):
        if self.n >= len(self.buf):
            self.buf = np.vstack([self.buf, np.full_like(self.buf, np.nan)])
        row = self.buf[self.n]
        row[0] = kw["t"]
        row[1] = self.seed
        row[2] = 0 if self.condition == "baseline" else 1
        for k, v in kw.items():
            if k == "t":
                continue
            row[COLUMNS.index(k)] = v
        self.n += 1

    def data(self) -> np.ndarray:
        return self.buf[:self.n]

    def to_csv(self, path: str, stride: int = 1):
        d = self.data()[::stride]
        header = ",".join(COLUMNS)
        fmt = ["%.4f", "%d", "%d", "%d"] + ["%.5f"] * (len(COLUMNS) - 4)
        np.savetxt(path, d, delimiter=",", header=header, comments="", fmt=fmt)
