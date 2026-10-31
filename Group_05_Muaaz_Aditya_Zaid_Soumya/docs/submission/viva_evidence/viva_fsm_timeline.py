"""Viva-prep: headless FSM timeline on the production controller (the same one run_benchmark.py uses), vision at the batch rate
(10 Hz), exterior scene, intruder appears at 25 s, seed 4 (the default of src/view_live.py), 60 s. Prints every surveillance-state
change per UAV with its simulated time. One deterministic run for the viva, NOT a dossier result. Nothing is written."""
import os, sys
G = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, G + "/src")
import aerial_patrol_swarm as aps
scene = sys.argv[1] if len(sys.argv) > 1 else "exterior"
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
c = aps.DualUAVSurveillanceController(model_path=aps.SCENES[scene], policy="sectors", seed=4, intruder_appear_s=25.0)
last = {"alpha": None, "bravo": None}
print(f"scene {scene}, duration {dur:g} s, intruder appears at {c.intruder_appear_s:g} s, vision_hz {c.vision_hz:g}")
while c.current_time_s < dur:
    c.step_simulation(dt=1.0 / 30.0)
    for n, u in c.uavs.items():
        if u["fsm"] != last[n]:
            if last[n] is not None or u["fsm"] != "TAKEOFF":
                print(f"  t = {c.current_time_s:7.2f} s  {n:5s} {last[n]} -> {u['fsm']}")
            last[n] = u["fsm"]
sm = c.surveillance_metrics()
for i in sm["incidents"]:
    print(f"incident {i['id']}: owner {i['owner']} DETECT {i['t_detect']} VERIFY {i['t_verify']} tier {i['tier_alert']} (max {i['tier_max']}) "
          f"tracker {i['tracker']} closed {i['t_close']} ({i['close_reason']}) true_detection {i.get('true_detection')}")
print(f"detected {sm['detected']}  detection_latency_s {sm['detection_latency_s']}  verify_time_s {sm['verify_time_s']}  false_alarms {sm['false_alarms']}")
