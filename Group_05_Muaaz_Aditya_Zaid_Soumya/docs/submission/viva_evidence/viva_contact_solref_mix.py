"""Viva-prep: what solref does MuJoCo actually use for a leg-vs-dock contact? Prints the per-geom solref and the contact's combined solref."""
import sys, numpy as np, mujoco
import os
G = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))   # group folder of the tree this file sits in
sys.path.insert(0, G + "/src")
import aerial_patrol_swarm as aps
for scene in ("interior", "exterior"):
    c = aps.DualUAVSurveillanceController(model_path=aps.SCENES[scene], vision=False, wind_mps=0.0, gust_sigma=0.0)
    m, d = c.model, c.data
    d.ctrl[:] = 0.0
    for _ in range(int(0.5 / m.opt.timestep)): mujoco.mj_step(m, d)
    seen = set()
    for i in range(d.ncon):
        cn = d.contact[i]
        names = tuple(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) for g in (cn.geom1, cn.geom2))
        if names in seen: continue
        seen.add(names)
        g1, g2 = cn.geom1, cn.geom2
        print(f"{scene}: contact {names}  geom solref {m.geom_solref[g1].tolist()} / {m.geom_solref[g2].tolist()}  solmix {m.geom_solmix[g1]:.2f}/{m.geom_solmix[g2]:.2f}  -> contact solref used {cn.solref.tolist()}  friction {cn.friction[:2].tolist()}  mu geoms {m.geom_friction[g1,0]:.2f}/{m.geom_friction[g2,0]:.2f}")
    print(f"{scene}: global opt.o_solref {m.opt.o_solref.tolist()}  refsafe flag enabled? {not bool(m.opt.disableflags & mujoco.mjtDisableBit.mjDSBL_REFSAFE)}")
