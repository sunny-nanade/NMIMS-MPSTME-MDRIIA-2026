"""
Vision illumination benchmark | owner E051 Aditya Rajkumar

REAL measurements, no synthetic data: the intruder is placed at known positions in view of a UAV camera
inside the MuJoCo scene, the frame is rendered with mujoco.Renderer, the ground-truth bounding box comes from a
SEGMENTATION rendering of the intruder geom (exact pixel mask), and the OpenCV HSV detector
(aerial_patrol_swarm.DualUAVSurveillanceController.detect_intruder_hsv) sees only the RGB frame.

Two lightings, both applied to the loaded model and restored afterwards:
  noon      = the scene as authored (headlight + scene lights unchanged)
  twilight  = headlight ambient/diffuse/specular and every scene light diffuse/specular/ambient scaled by
              --twilight-scale (default 0.15). The scale is an ASSUMPTION chosen for a dim-light stress case;
              it is not a measured lux value. Skybox and emissive ceiling-light materials are left untouched.

Frame placement (fully deterministic, no random numbers):
  interior  UAV alpha at its patrol altitude (min z of its route), trailing the intruder along the authored
            intruder_path at 4-8 m, yaw toward the target, forward-oblique camera (vision_cams of the scene).
  exterior  every path sample is seen by UAV alpha (cam_alpha) and by bravo (cam_bravo) at their patrol
            altitudes, nadir cameras, yaw 0, offset from directly above the target by fractions of the footprint.
Frames whose exact segmentation mask has fewer than MIN_GT_PIXELS pixels (target occluded or out of frame) are
skipped and counted; the same frame list is used for both lightings.

Output columns (analytics/vision_illumination_benchmark.csv):
  scene, lighting, detector, frame_id, iou, latency_ms, detected, gt_pixels, proj_err_m
iou = 0 when nothing is detected. proj_err_m = horizontal distance between inverse_pinhole_projection of the
detected centroid (camera-ray / ground-plane form at the assumed centroid height) and the true intruder (x, y);
empty when nothing is detected.

  python analytics/vision_illumination_benchmark.py [--scene both|interior|exterior] [--n-frames 64]
"""
import argparse
import csv
import json
import math
import os
import platform
import sys

import cv2
import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
import aerial_patrol_swarm as aps  # noqa: E402

MIN_GT_PIXELS = 50
INTRUDER_Z = 0.86            # m, geom centre height used to stand the 1.7 m cylinder on the floor
FIELDS = ["scene", "lighting", "detector", "frame_id", "iou", "latency_ms", "detected", "gt_pixels", "proj_err_m"]
UAVS_PER_SCENE = {"interior": ("alpha",), "exterior": ("alpha", "bravo")}
TRAIL_M = (4.0, 6.0, 8.0, 5.0, 7.0)                       # interior trailing distances, cycled
OFFSET_FRAC = ((-0.5, 0.3), (0.4, -0.4), (0.0, 0.0), (0.6, 0.5), (-0.3, -0.6))   # exterior footprint offsets, cycled


AUTO_EXPOSURE = True        # detector low-light gain (production); --no-auto-exposure measures the raw-frame detector


def bbox_iou(a, b):
    """IoU of two (x1, y1, x2, y2) boxes in pixel-edge convention."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def mask_bbox(mask):
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


class LightingRig:
    """Applies and restores a brightness scale on the headlight and every scene light."""

    def __init__(self, model):
        self.m = model
        h = model.vis.headlight
        self.orig = dict(h_amb=h.ambient.copy(), h_dif=h.diffuse.copy(), h_spec=h.specular.copy(),
                         l_amb=model.light_ambient.copy(), l_dif=model.light_diffuse.copy(),
                         l_spec=model.light_specular.copy())

    def apply(self, scale):
        m, o, h = self.m, self.orig, self.m.vis.headlight
        h.ambient[:], h.diffuse[:], h.specular[:] = o["h_amb"] * scale, o["h_dif"] * scale, o["h_spec"] * scale
        m.light_ambient[:], m.light_diffuse[:], m.light_specular[:] = (o["l_amb"] * scale, o["l_dif"] * scale,
                                                                       o["l_spec"] * scale)

    def describe(self, scale):
        o = self.orig
        return {"scale": scale,
                "headlight_ambient": [round(float(x) * scale, 4) for x in o["h_amb"]],
                "headlight_diffuse": [round(float(x) * scale, 4) for x in o["h_dif"]],
                "light_diffuse": [[round(float(x) * scale, 4) for x in row] for row in o["l_dif"]]}


class SceneBench:
    """One scene: controller (model + detector), renderer, frame generator."""

    def __init__(self, scene):
        self.scene = scene
        self.ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES[scene], vision=False,
                                                     auto_exposure=AUTO_EXPOSURE)
        self.model, self.data = self.ctl.model, self.ctl.data
        self.rig = LightingRig(self.model)
        self.renderer = mujoco.Renderer(self.model, aps.DualUAVSurveillanceController.IMG_H_PX,
                                        aps.DualUAVSurveillanceController.IMG_W_PX)
        self.gid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "intruder_geom")
        self.cams = dict(zip(("alpha", "bravo"), self.ctl.vision_cams))

    def close(self):
        self.renderer.close()

    # ---- geometry -------------------------------------------------------------------------------
    def _patrol_alt(self, name):
        return float(min(p[0][2] for p in self.ctl.uavs[name]["route"]))

    def _path_points(self):
        pts = [np.asarray(p, float) for p in self.ctl.intruder_path]
        seg = [float(np.linalg.norm(b - a)) for a, b in zip(pts, pts[1:])]
        return pts, seg

    def _path_at(self, s):
        pts, seg = self._path_points()
        for a, b, L in zip(pts, pts[1:], seg):
            if s <= L:
                return a + (b - a) * s / L
            s -= L
        return pts[-1]

    def plan(self, n_frames):
        """List of (uav_name, uav_pos, yaw, target_xy). Deterministic."""
        _, seg = self._path_points()
        total = sum(seg)
        names = UAVS_PER_SCENE[self.scene]
        out = []
        if self.scene == "interior":
            s_lo = max(TRAIL_M)
            for i, s in enumerate(np.linspace(s_lo, total, n_frames)):
                name = names[i % len(names)]
                tgt = self._path_at(s)
                src = self._path_at(s - TRAIL_M[i % len(TRAIL_M)])
                yaw = math.atan2(tgt[1] - src[1], tgt[0] - src[0])
                out.append((name, np.array([src[0], src[1], self._patrol_alt(name)]), yaw, tgt))
        else:
            for i, s in enumerate(np.linspace(0.0, total, n_frames)):
                tgt = self._path_at(s)
                for j, name in enumerate(names):          # every path sample is seen by both UAVs
                    alt = self._patrol_alt(name)
                    hw, hh = alt * 320.0 / 450.0, alt * 240.0 / 450.0
                    fx, fy = OFFSET_FRAC[(i + j) % len(OFFSET_FRAC)]
                    out.append((name, np.array([tgt[0] - fx * hw, tgt[1] - fy * hh, alt]), 0.0, tgt))
        return out

    def pose(self, name, pos, yaw, tgt):
        d, m = self.data, self.model
        u = self.ctl.uavs[name]
        d.qpos[u["qadr"]:u["qadr"] + 3] = pos
        d.qpos[u["qadr"] + 3:u["qadr"] + 7] = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
        d.qvel[u["vadr"]:u["vadr"] + 6] = 0.0
        q = self.ctl.intruder_q
        d.qpos[q:q + 3] = (tgt[0], tgt[1], INTRUDER_Z)
        d.qpos[q + 3:q + 7] = (1, 0, 0, 0)
        mujoco.mj_forward(m, d)

    # ---- rendering ------------------------------------------------------------------------------
    def render_rgb(self, cam):
        self.renderer.update_scene(self.data, camera=cam)
        return self.renderer.render().copy()

    def render_gt(self, cam):
        self.renderer.enable_segmentation_rendering()
        self.renderer.update_scene(self.data, camera=cam)
        seg = self.renderer.render()
        self.renderer.disable_segmentation_rendering()
        mask = (seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM)) & (seg[..., 0] == self.gid)
        return int(mask.sum()), mask_bbox(mask)

    def frames(self, n_frames, lighting_scale):
        """Yield frame dicts for one lighting. The geometry/GT part is independent of lighting."""
        self.rig.apply(lighting_scale)
        try:
            for i, (name, pos, yaw, tgt) in enumerate(self.plan(n_frames)):
                cam = self.cams[name]
                self.pose(name, pos, yaw, tgt)
                gt_px, gt_box = self.render_gt(cam)
                cid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, cam)
                yield dict(frame_id=i, uav=name, cam=cam, uav_pos=pos.copy(), target_xy=np.asarray(tgt, float),
                           gt_pixels=gt_px, gt_bbox=gt_box, rgb=self.render_rgb(cam),
                           cam_xpos=self.data.cam_xpos[cid].copy(), cam_xmat=self.data.cam_xmat[cid].copy())
        finally:
            self.rig.apply(1.0)


def evaluate(ctl, fr):
    """Run the detector on one frame dict -> (iou, latency_ms, detected, proj_err_m)."""
    res = ctl.detect_intruder_hsv(fr["rgb"])
    if not res["detected"]:
        return 0.0, res["latency_ms"], 0, None
    iou = bbox_iou(res["bbox"], fr["gt_bbox"])
    pt = ctl.inverse_pinhole_projection(res["centroid"][0], res["centroid"][1], fr["uav_pos"],
                                        cam_xpos=fr["cam_xpos"], cam_xmat=fr["cam_xmat"],
                                        ground_z=ctl.ASSUMED_TARGET_CENTROID_Z)
    err = None if pt is None else float(np.linalg.norm(pt[:2] - fr["target_xy"]))
    return iou, res["latency_ms"], 1, err


def run(scenes, n_frames, lightings):
    """lightings = ((label, scale), ...). Returns the CSV rows, skipped-frame counts and the applied lighting values."""
    rows, skipped, rigs = [], {}, {}
    for scene in scenes:
        sb = SceneBench(scene)
        rigs[scene] = {name: sb.rig.describe(sc) for name, sc in lightings}
        skipped[scene] = 0
        for lighting, scale in lightings:
            n_kept = 0
            for fr in sb.frames(n_frames, scale):
                if fr["gt_pixels"] < MIN_GT_PIXELS:
                    if lighting == "noon":
                        skipped[scene] += 1
                    continue
                iou, lat, det, err = evaluate(sb.ctl, fr)
                rows.append(dict(scene=scene, lighting=lighting, detector="opencv_hsv", frame_id=fr["frame_id"],
                                 iou=round(iou, 4), latency_ms=round(lat, 3), detected=det,
                                 gt_pixels=fr["gt_pixels"], proj_err_m="" if err is None else round(err, 4)))
                n_kept += 1
            print(f"{scene:9s} {lighting:9s} frames kept {n_kept}", flush=True)
        sb.close()
    return rows, skipped, rigs


def pct(vals, q):
    return float(np.percentile(vals, q)) if len(vals) else float("nan")


def summarise(rows, skipped, rigs, twilight_scale, n_frames):
    lines = ["VISION ILLUMINATION BENCHMARK (E051) -- opencv_hsv detector, real MuJoCo renders, GT from segmentation",
             f"path samples per scene: {n_frames}; minimum GT mask {MIN_GT_PIXELS} px; skipped (occluded/out of frame): "
             + ", ".join(f"{k}={v}" for k, v in skipped.items()),
             f"twilight = noon values x {twilight_scale} on headlight and scene lights (ASSUMPTION, not a measured lux)",
             f"host: {platform.platform()} | python {platform.python_version()} | mujoco {mujoco.__version__} | opencv {cv2.__version__}",
             "definitions: IoU(all) counts a missed frame as 0; detection rate = detector flag raised; hit = detected and IoU >= 0.5;",
             "             miss rate = 1 - hit rate (no detection, or a blob that is not the intruder); latency = detector only (perf_counter)", ""]
    hdr = (f"{'scene':9s} {'lighting':9s} {'n':>4s} {'IoU(all)':>9s} {'IoU(det)':>9s} {'det.rate':>9s} {'hit.rate':>9s} "
           f"{'miss.rate':>10s} {'lat mean ms':>12s} {'lat p95 ms':>11s} {'proj err mean m':>16s} {'p95 m':>7s}")
    lines.append(hdr)
    flags = []
    for scene in sorted({r["scene"] for r in rows}):
        for lighting in ("noon", "twilight"):
            sel = [r for r in rows if r["scene"] == scene and r["lighting"] == lighting]
            if not sel:
                continue
            iou = np.array([r["iou"] for r in sel])
            det = np.array([r["detected"] for r in sel])
            hit = (det == 1) & (iou >= 0.5)
            lat = [r["latency_ms"] for r in sel]
            err = [r["proj_err_m"] for r, h in zip(sel, hit) if h and r["proj_err_m"] != ""]
            iou_det = iou[det == 1]
            lines.append(f"{scene:9s} {lighting:9s} {len(sel):4d} {iou.mean():9.3f} "
                         f"{(iou_det.mean() if iou_det.size else float('nan')):9.3f} {det.mean():9.3f} {hit.mean():9.3f} "
                         f"{1 - hit.mean():10.3f} {np.mean(lat):12.2f} {pct(lat, 95):11.2f} "
                         f"{(np.mean(err) if err else float('nan')):16.3f} {pct(err, 95):7.3f}")
            if lighting == "noon" and iou.mean() < 0.70:
                flags.append(f"NOTE: {scene} noon mean IoU {iou.mean():.3f} is below the 0.70 target (reported as measured).")
    lines += [""] + flags
    lines.append("lighting values applied: " + json.dumps(rigs))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="both", choices=["both", "interior", "exterior"])
    ap.add_argument("--n-frames", type=int, default=64)
    ap.add_argument("--twilight-scale", type=float, default=0.15)
    ap.add_argument("--sweep", default="", help="comma list of extra brightness scales, e.g. 0.5,0.35,0.25,0.15,0.1; "
                                                 "writes vision_illumination_sweep.csv (sensitivity of the twilight result)")
    ap.add_argument("--csv", default=os.path.join(HERE, "vision_illumination_benchmark.csv"))
    ap.add_argument("--summary", default=os.path.join(HERE, "vision_illumination_summary.txt"))
    ap.add_argument("--no-auto-exposure", action="store_true",
                    help="detector without the low-light value gain (ablation arm; production has it on)")
    a = ap.parse_args()
    global AUTO_EXPOSURE
    AUTO_EXPOSURE = not a.no_auto_exposure
    scenes = ("interior", "exterior") if a.scene == "both" else (a.scene,)
    rows, skipped, rigs = run(scenes, a.n_frames, (("noon", 1.0), ("twilight", a.twilight_scale)))
    with open(a.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    text = summarise(rows, skipped, rigs, a.twilight_scale, a.n_frames)
    with open(a.summary, "w") as f:
        f.write(text + "\n")
    with open(os.path.splitext(a.csv)[0] + ".provenance.json", "w") as f:
        json.dump({"script": "analytics/vision_illumination_benchmark.py", "scenes": list(scenes),
                   "n_frames_requested": a.n_frames, "min_gt_pixels": MIN_GT_PIXELS, "placement": "deterministic, no random numbers",
                   "skipped_frames": skipped, "lighting": rigs, "gt_source": "mujoco segmentation rendering of intruder_geom",
                   "detector_input": "RGB frame only", "rows": len(rows), "auto_exposure": AUTO_EXPOSURE,
                   "detector_constants": {k: getattr(aps.DualUAVSurveillanceController, k) for k in
                                          ("HSV_HUE_TOL", "HSV_SAT_FRAC", "HSV_VAL_MIN", "MIN_BLOB_AREA_PX",
                                           "AE_TARGET_V", "AE_PCTL", "AE_GAIN_MAX")},
                   "command": " ".join(["python"] + sys.argv)}, f, indent=2)
    print(text)
    if a.sweep:
        scales = [float(x) for x in a.sweep.split(",")]
        srows, _, _ = run(scenes, a.n_frames, tuple((f"scale_{x}", x) for x in scales))
        table = ["", "BRIGHTNESS SWEEP (same frames, scale x authored lighting; reported as measured)",
                 f"{'scene':9s} {'scale':>6s} {'n':>4s} {'mean IoU':>9s} {'det.rate':>9s} {'hit.rate':>9s} {'miss.rate':>10s}"]
        with open(os.path.join(os.path.dirname(os.path.abspath(a.csv)), "vision_illumination_sweep.csv"), "w",
                  newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["scene", "brightness_scale", "n_frames", "mean_iou", "detection_rate", "hit_rate", "miss_rate"])
            for scene in scenes:
                for x in scales:
                    sel = [r for r in srows if r["scene"] == scene and r["lighting"] == f"scale_{x}"]
                    iou = np.array([r["iou"] for r in sel])
                    det = np.array([r["detected"] for r in sel])
                    hit = float(((det == 1) & (iou >= 0.5)).mean())
                    rec = [scene, x, len(sel), round(float(iou.mean()), 4), round(float(det.mean()), 4),
                           round(hit, 4), round(1 - hit, 4)]
                    w.writerow(rec)
                    table.append(f"{scene:9s} {x:6.2f} {rec[2]:4d} {rec[3]:9.3f} {rec[4]:9.3f} {rec[5]:9.3f} {rec[6]:10.3f}")
        with open(a.summary, "a") as f:
            f.write("\n".join(table) + "\n")
        print("\n".join(table))
        print("sweep written to analytics/vision_illumination_sweep.csv")


if __name__ == "__main__":
    main()
