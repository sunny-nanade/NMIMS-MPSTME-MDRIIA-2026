"""Viva-prep: which interior frames the production detector misses (IoU < 0.5), noon and twilight (0.15 x lights, ASSUMPTION).
Same 64-sample path as analytics/vision_illumination_benchmark.py; imports it unmodified; writes nothing but stdout.
The 8 twilight misses sit in frames 55-63, the VIP Lounge stretch where the 0.66 saturation floor failed at noon (case E051-A)."""
import os, sys
W = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, W + "/analytics"); sys.path.insert(0, W + "/src")
import vision_illumination_benchmark as vb
rows, skipped, _ = vb.run(("interior",), 64, (("noon", 1.0), ("twilight", 0.15)))
for l in ("noon", "twilight"):
    bad = [(r["frame_id"], round(r["iou"], 2), r["detected"], r["gt_pixels"]) for r in rows if r["lighting"] == l and r["iou"] < 0.5]
    print(f"{l}: frames kept {sum(1 for r in rows if r['lighting'] == l)}, IoU < 0.5 in {len(bad)}: (frame_id, IoU, detected, gt_pixels) {bad}")
