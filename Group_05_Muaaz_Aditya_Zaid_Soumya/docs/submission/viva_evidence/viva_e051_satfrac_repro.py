"""Viva-prep reproduction of E051's documented AI error: same benchmark frames, HSV_SAT_FRAC 0.66 (first draft) vs 0.75 (shipped).
Imports the benchmark from this tree's analytics/ (not modified); writes nothing but stdout. The detector now also has the
low-light auto-exposure gain; at noon the frame's highlights already reach AE_TARGET_V, so the gain is 1 and the noon result is unchanged."""
import os, sys
W = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, W + "/analytics"); sys.path.insert(0, W + "/src")
import numpy as np
import vision_illumination_benchmark as vb
aps = vb.aps
for frac in (0.66, 0.75):
    aps.DualUAVSurveillanceController.HSV_SAT_FRAC = frac
    rows, skipped, _ = vb.run(("interior",), 64, (("noon", 1.0),))
    iou = np.array([r["iou"] for r in rows]); det = np.array([r["detected"] for r in rows])
    print(f"HSV_SAT_FRAC={frac}: S_min={int(frac*226)}  interior noon n={len(rows)} mean IoU(all)={iou.mean():.3f} hit rate(IoU>=0.5)={(iou>=0.5).mean():.3f} det rate={det.mean():.3f} worst frame IoU={iou.min():.3f}")
