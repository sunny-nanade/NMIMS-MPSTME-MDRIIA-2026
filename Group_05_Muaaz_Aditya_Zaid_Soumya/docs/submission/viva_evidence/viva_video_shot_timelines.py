"""Video shot timelines: headless replay of the exact configurations in docs/submission/video_shots.sh, stepped like
src/view_live.py at --speed 1 (frame 1/60 s, off-screen 480x640 renderer for vision, the same controller arguments).
Prints every FSM change per UAV with sim time, every incident, and for the head-on demos the minimum centre distance.
One deterministic run per shot, NOT a dossier result. Nothing is written.

    python docs/submission/viva_evidence/viva_video_shot_timelines.py 1 2 3 3b > docs/submission/viva_evidence/viva_video_shot_timelines.txt
"""
import os
import sys

import mujoco
import numpy as np

G = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(G, "src"))
import aerial_patrol_swarm as aps   # noqa: E402
import view_live as vl              # noqa: E402

FRAME = 1 / 60
SHOTS = {"1": ("interior", 110.0), "2": ("exterior", 110.0), "3": ("headon", 15.0), "3b": ("headon_apf", 15.0)}


def run(shot):
    scene, dur = SHOTS[shot]
    if scene.startswith("headon"):
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES["exterior"], policy="sectors",
                                                wind_mps=0.0, gust_sigma=0.0, vision=False,
                                                layered_separation=(scene != "headon_apf"))
        vl.setup_head_on(ctl)
        print(f"SHOT {shot}: --demo headon{' --apf-only' if scene == 'headon_apf' else ''}, {dur:g} s")
    else:
        ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES[scene], policy="sectors",
                                                wind_mps=None, seed=4, intruder_appear_s=20.0, vision=True)
        ctl.renderer = mujoco.Renderer(ctl.model, 480, 640)
        print(f"SHOT {shot}: --scene {scene} --seed 4 --appear 20 (sectors), {dur:g} s, vision_hz {ctl.vision_hz:g}")
    last = {"alpha": None, "bravo": None}
    dmin, tmin = float("inf"), None
    while ctl.current_time_s < dur:
        ctl.step_simulation(dt=FRAME)
        pa = ctl.data.qpos[ctl.uavs["alpha"]["qadr"]:ctl.uavs["alpha"]["qadr"] + 3]
        pb = ctl.data.qpos[ctl.uavs["bravo"]["qadr"]:ctl.uavs["bravo"]["qadr"] + 3]
        d = float(np.linalg.norm(pa - pb))
        if d < dmin:
            dmin, tmin = d, ctl.current_time_s
        for n, u in ctl.uavs.items():
            if u["fsm"] != last[n]:
                if last[n] is not None:
                    print(f"  t = {ctl.current_time_s:7.2f} s  {n:5s} {last[n]} -> {u['fsm']}")
                last[n] = u["fsm"]
    if not scene.startswith("headon"):
        sm = ctl.surveillance_metrics()
        for i in sm["incidents"]:
            print(f"  incident {i['id']}: owner {i['owner']} DETECT {i['t_detect']} VERIFY {i['t_verify']} tier {i['tier_alert']} "
                  f"tracker {i['tracker']} closed {i['t_close']} ({i['close_reason']}) true_detection {i.get('true_detection')}")
    print(f"  min centre distance {dmin:.2f} m at t = {tmin:.2f} s; UAV-UAV contacts {ctl.uav_uav_contacts}; "
          f"obstacle contacts {sum(u['obstacle_contacts'] for u in ctl.uavs.values())}")


if __name__ == "__main__":
    for s in sys.argv[1:] or list(SHOTS):
        run(s)
