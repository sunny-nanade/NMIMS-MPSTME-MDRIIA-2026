"""Viva-prep engineering check (NOT a dossier result): rest the Alpha airframe on its dock with rotors off for 2 s and compare
leg-contact settling with the shipped contact parameters, solref time constant halved, solref doubled and sliding friction halved.
Deterministic, single drop, exterior scene file. Reads the model; edits only the in-memory copy."""
import sys, numpy as np, mujoco
import os
G = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))   # group folder of the tree this file sits in
sys.path.insert(0, G + "/src")
import aerial_patrol_swarm as aps
def drop(solref0=None, fric0=None, label=""):
    c = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], vision=False, wind_mps=0.0, gust_sigma=0.0)
    m, d = c.model, c.data
    u = c.uavs["alpha"]
    gids = [g for g in range(m.ngeom) if m.geom_bodyid[g] == u["bid"] and m.geom_contype[g] != 0]
    for g in gids:
        if solref0 is not None: m.geom_solref[g, 0] = solref0
        if fric0 is not None: m.geom_friction[g, 0] = fric0
    d.ctrl[:] = 0.0
    q = u["qadr"]; x0 = d.qpos[q:q+2].copy(); mind = 1e9; z_end = None; n_con = 0
    for k in range(int(2.0 / m.opt.timestep)):
        mujoco.mj_step(m, d)
        for i in range(d.ncon):
            cn = d.contact[i]
            if cn.geom1 in gids or cn.geom2 in gids:
                mind = min(mind, cn.dist)
    z = d.qpos[q+2]; drift = float(np.linalg.norm(d.qpos[q:q+2] - x0))
    print(f"{label:34s} legs: n={len(gids)} solref0={m.geom_solref[gids[0],0]:.4f} friction0={m.geom_friction[gids[0],0]:.2f}  z_rest={z:.4f} m  deepest contact dist={mind*1000:.3f} mm  xy drift={drift*1000:.3f} mm")
print("timestep", mujoco.MjModel.from_xml_path(aps.SCENES["exterior"]).opt.timestep)
drop(label="shipped (solref 0.004, mu 1.0)")
drop(solref0=0.002, label="solref halved to 0.002")
drop(solref0=0.008, label="solref doubled to 0.008")
drop(fric0=0.5, label="sliding friction halved to 0.5")
drop(fric0=0.1, label="sliding friction cut to 0.1 (contrast)")
