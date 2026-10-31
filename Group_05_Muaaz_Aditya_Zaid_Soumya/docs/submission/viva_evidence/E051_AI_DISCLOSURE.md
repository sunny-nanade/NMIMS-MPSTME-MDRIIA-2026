# AI_DISCLOSURE.md -- E051 vision draft

## What was AI-drafted
Everything in this packet was drafted by an AI coding assistant (Anthropic model, run as a sub-agent) under Muaaz's
instructions: the three region functions and helpers in src/aerial_patrol_swarm.py (detect_intruder_hsv, _hsv_bands,
focal_length_px, inverse_pinhole_projection, _target_in_view, select_tracking_uav), tests/test_e051_vision.py (19 tests),
analytics/vision_illumination_benchmark.py, analytics/vision_yolo_compare.py, the generated data files
(vision_illumination_benchmark.csv, .provenance.json, vision_illumination_summary.txt, vision_illumination_sweep.csv)
and this packet (EXPLAIN.md, COMMITS.md, AI_DISCLOSURE.md).
Estimated AI-drafted share: about 100 percent of the lines and text. Your own contribution starts when you read, run,
understand and, where needed, change it. The numbers in the data files are real measurements produced by the scripts,
not typed in, but they come from a run on Muaaz's machine.

## What you must verify or redo
1. Read EXPLAIN.md and be able to derive, on a whiteboard: the HSV values of the intruder colour, the pinhole model
   X = X_uav + (u - u0) h / f, the camera-ray / ground-plane intersection, and why handoff needs hysteresis.
2. Re-run on your machine: pytest tests/test_e051_vision.py (expect 19 passed), the benchmark with --sweep, and commit the
   data you generated, not the packet copy.
3. Open two or three rendered frames yourself (the benchmark can yield them; see EXPLAIN.md section 7) and look at what the
   detector sees, especially the terracotta floor of the VIP lounge in the interior scene.
4. Decide whether you accept these design choices (they are assumptions, not facts): twilight = 0.15 x authored light,
   minimum visible target 50 px, target centroid height 0.85 m, handoff hysteresis 2 m, 40 px image-edge margin.
5. The literature (HSV thresholding, pinhole model, YOLO) is not cited in the code; if the report cites any source you must
   find and check it yourself. None was invented here.
6. The YOLO part is optional, was run in a separate environment, and needs the AGPL-3.0 note kept in the report if used.

## One real AI error from this drafting (evidence)
The first version of the saturation threshold was too loose. The detector used S_min = 0.66 x S_nominal (149 of 255).
Benchmark output at noon, interior scene, 58 frames, before the fix:
    mean IoU 0.874, hit rate (IoU >= 0.5) 0.862
Inspection of the failing frames (VIP lounge, frames 55-63 of the path) showed detector boxes as large as
(160, 62, 640, 475) against a ground-truth box of (288, 62, 352, 249): the terracotta carpet of the lounge
(RGB 186, 91, 66; HSV 6, 165, 186) satisfied the hue band and had saturation 165, above 149, so it merged with the
intruder blob. After measuring the intruder saturation (227 lit) against the floor (165-166), S_min was raised to
0.75 x S_nominal = 169. After the fix: interior noon mean IoU 0.985, hit rate 1.000; exterior noon stayed at about 0.94 (0.944 on the 26 frames of the first run, 0.942 on the final 100-frame set). Caveat: the threshold was tuned on the same frames the benchmark reports (in-sample), and the sweep
shows the floor confusion returns when the scene is dimmed to 0.7 x or less (interior hit rate 0.862). That residual
weakness is reported, not hidden.
Smaller errors caught by the test run: a handoff test that claimed to check "prefers the UAV that sees the target" but
had the seeing UAV also closer (it could not fail), and an oblique round-trip test with leftover scratch lines that made the
inverse projection return None. Both were rewritten before the packet was made.
