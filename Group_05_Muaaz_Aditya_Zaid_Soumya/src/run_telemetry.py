"""
Per-physics-step run telemetry (contract B) | MDRIIA Group 05 | Owner: E043 Muaaz

One gzip CSV per run, analytics/runs/<scene>_<condition>_s<seed>.csv.gz, one row per
0.002 s physics step per vehicle (alpha, bravo, or guard). Columns, in this order
(contract B -- append only, never rename):

  t, run_id, seed, condition, uav, x, y, z, vx, vy, vz, xref, yref, zref,
  ex, ey, ez, f0..f7, fsm_state, event, roll, pitch, yaw

  t            s, simulation time at the START of the physics step (state before mj_step)
  x y z        m, vehicle position, world ENU frame (guard: eye point, floor + 1.6 m)
  vx vy vz     m/s, world-frame linear velocity
  xref..zref   m, reference position (UAV: see DualUAVSurveillanceController._reference;
               guard: the walking-route point it is heading for)
  ex ey ez     m, position - reference (empty for the guard: it has no controller)
  f<k>         N, commanded thrust of model actuator k over this step:
               alpha_m0..m3 = f0..f3 (alpha rows), bravo_m0..m3 = f4..f7 (bravo rows);
               the other vehicle's columns are empty on each row, all empty for the guard
  fsm_state    surveillance / mission state of that vehicle on this step
  event        ';'-separated events raised on this step (checkpoint service, phase
               change, contact onset, detection), empty otherwise
  roll pitch yaw  rad, UAV attitude (ZYX Euler from the free-joint quaternion) at t, the
               state the controller acted on; empty for the guard. Appended (G-11).

Rounding: t to 1 ms (exact for a 0.002 s grid), positions/references/errors to 1 mm,
velocities to 1 mm/s, rotor forces to 1 mN. Rows are formatted with a pre-built
%-template and written through gzip in blocks, so logging every step stays cheap.
"""
import gzip
import os

COLUMNS = (["t", "run_id", "seed", "condition", "uav", "x", "y", "z", "vx", "vy", "vz",
            "xref", "yref", "zref", "ex", "ey", "ez"] + [f"f{k}" for k in range(8)] + ["fsm_state", "event", "roll", "pitch", "yaw"])
ROTOR_SLOTS = {"alpha": range(0, 4), "bravo": range(4, 8), "guard": range(0)}
FLUSH_ROWS = 20000


class StepTelemetry:
    """Buffered writer for one run's contract-B telemetry file."""

    def __init__(self, path, run_id, seed, condition, compresslevel=6):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        self._fh = gzip.open(path, "wt", compresslevel=compresslevel, newline="")
        self._fh.write(",".join(COLUMNS) + "\n")
        self._buf = []
        self.rows = 0
        lead = f"%.3f,{run_id},{seed},{condition},"
        self._tpl = {}
        for uav, slots in ROTOR_SLOTS.items():
            f = ",".join("%.3f" if k in slots else "" for k in range(8))
            err = "%.3f,%.3f,%.3f" if uav != "guard" else ",,"
            att = ",%.5f,%.5f,%.5f" if uav != "guard" else ",,,"
            self._tpl[uav] = (lead + uav + ",%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f," + err + "," + f
                              + ",%s,%s" + att + "\n")

    def row(self, uav, t, pos, vel, ref, err=None, forces=(), fsm_state="", event="", rpy=(0.0, 0.0, 0.0)):
        """Append one row. `forces` = that vehicle's 4 rotor thrusts, `rpy` its attitude (UAVs only)."""
        vals = (t, pos[0], pos[1], pos[2], vel[0], vel[1], vel[2], ref[0], ref[1], ref[2])
        if uav != "guard":
            vals += (err[0], err[1], err[2]) + tuple(forces)
        tail = (fsm_state, event) + ((rpy[0], rpy[1], rpy[2]) if uav != "guard" else ())
        self._buf.append(self._tpl[uav] % (vals + tail))
        if len(self._buf) >= FLUSH_ROWS:
            self.flush()

    def flush(self):
        if self._buf:
            self._fh.write("".join(self._buf))
            self.rows += len(self._buf)
            self._buf = []

    def close(self):
        if self._fh is not None:
            self.flush()
            self._fh.close()
            self._fh = None
        return self.path
