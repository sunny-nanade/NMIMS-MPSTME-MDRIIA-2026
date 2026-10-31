"""
OPTIONAL YOLO comparison | owner E051 Aditya Rajkumar

Runs a pretrained YOLO model on exactly the frames of analytics/vision_illumination_benchmark.py and appends
detector=yolo rows to analytics/vision_illumination_benchmark.csv (existing yolo rows are replaced). The OpenCV HSV
results never depend on this file; the project requirements do not include ultralytics or torch.

Licence note: Ultralytics YOLO is AGPL-3.0. It is used here only as an offline comparison tool in a separate
virtual environment; it is not imported by the controller and nothing from it is redistributed with the project.

The COCO-pretrained model has no class for "red cylinder", so the comparison is class-agnostic: the detection with
the highest confidence (conf >= 0.25) is taken as the target box. This favours YOLO; it is not fine-tuned.

Setup (separate environment, CPU only):
  python -m venv venv_yolo && venv_yolo/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  venv_yolo/bin/pip install ultralytics mujoco opencv-python
  venv_yolo/bin/python analytics/vision_yolo_compare.py --weights <dir>/yolov8n.pt
"""
import argparse
import csv
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vision_illumination_benchmark as vib  # noqa: E402

CONF = 0.25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="yolov8n.pt")
    ap.add_argument("--n-frames", type=int, default=64)
    ap.add_argument("--twilight-scale", type=float, default=0.15)
    ap.add_argument("--summary", default=os.path.join(HERE, "vision_illumination_summary.txt"))
    ap.add_argument("--csv", default=os.path.join(HERE, "vision_illumination_benchmark.csv"))
    a = ap.parse_args()
    from ultralytics import YOLO                     # imported here so the module is harmless without it
    model = YOLO(a.weights)
    model.predict(np.zeros((480, 640, 3), np.uint8), verbose=False, device="cpu")   # warm-up, not timed
    rows = []
    for scene in ("interior", "exterior"):
        sb = vib.SceneBench(scene)
        for lighting, scale in (("noon", 1.0), ("twilight", a.twilight_scale)):
            for fr in sb.frames(a.n_frames, scale):
                if fr["gt_pixels"] < vib.MIN_GT_PIXELS:
                    continue
                t0 = time.perf_counter()
                res = model.predict(fr["rgb"][..., ::-1], conf=CONF, verbose=False, device="cpu")[0]   # BGR input
                lat = (time.perf_counter() - t0) * 1000.0
                iou, det, err = 0.0, 0, ""
                if len(res.boxes):
                    k = int(res.boxes.conf.argmax())
                    x1, y1, x2, y2 = (float(v) for v in res.boxes.xyxy[k])
                    iou, det = vib.bbox_iou((x1, y1, x2, y2), fr["gt_bbox"]), 1
                    pt = sb.ctl.inverse_pinhole_projection((x1 + x2) / 2, (y1 + y2) / 2, fr["uav_pos"],
                                                           cam_xpos=fr["cam_xpos"], cam_xmat=fr["cam_xmat"],
                                                           ground_z=sb.ctl.ASSUMED_TARGET_CENTROID_Z)
                    err = "" if pt is None else round(float(np.linalg.norm(pt[:2] - fr["target_xy"])), 4)
                rows.append(dict(scene=scene, lighting=lighting, detector="yolo", frame_id=fr["frame_id"],
                                 iou=round(iou, 4), latency_ms=round(lat, 3), detected=det,
                                 gt_pixels=fr["gt_pixels"], proj_err_m=err))
        sb.close()
    with open(a.csv, newline="") as f:
        keep = [r for r in csv.DictReader(f) if r["detector"] != "yolo"]
    with open(a.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=vib.FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(keep + rows)
    lines = ["", f"YOLO COMPARISON ({os.path.basename(a.weights)}, COCO-pretrained, class-agnostic, conf >= {CONF}, CPU; same frames)"]
    for scene in ("interior", "exterior"):
        for lighting in ("noon", "twilight"):
            sel = [r for r in rows if r["scene"] == scene and r["lighting"] == lighting]
            iou = np.array([r["iou"] for r in sel])
            det = np.array([r["detected"] for r in sel])
            lines.append(f"yolo {scene:9s} {lighting:9s} n={len(sel):3d} mean IoU {iou.mean():.3f} detection rate {det.mean():.3f} "
                  f"hit rate(IoU>=0.5) {((det == 1) & (iou >= 0.5)).mean():.3f} "
                  f"latency mean {np.mean([r['latency_ms'] for r in sel]):.1f} ms")
    if os.path.exists(a.summary):                    # replace a previous YOLO section, keep the OpenCV section
        txt = open(a.summary).read()
        txt = txt.split("\nYOLO COMPARISON")[0].rstrip("\n") + "\n"
    else:
        txt = ""
    with open(a.summary, "w") as f:
        f.write(txt + "\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
