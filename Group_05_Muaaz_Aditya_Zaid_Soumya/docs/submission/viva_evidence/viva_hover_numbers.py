import sys
import os
G = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))   # group folder of the tree this file sits in
sys.path.insert(0, G + "/src")
import aerial_patrol_swarm as a
for s, p in a.SCENES.items():
    c = a.DualUAVSurveillanceController(model_path=p, vision=False)
    print(f"{s}: nu={c.model.nu} timestep={c.model.opt.timestep}")
    for n, u in c.uavs.items():
        W = u["mass"] * 9.81
        print(f"  {n}: body_subtreemass={u['mass']:.4f} kg  m*g={W:.3f} N  per rotor={W/4:.3f} N  F_MAX*4={4*c.F_MAX:.1f} N  T/W={4*c.F_MAX/W:.3f}")
