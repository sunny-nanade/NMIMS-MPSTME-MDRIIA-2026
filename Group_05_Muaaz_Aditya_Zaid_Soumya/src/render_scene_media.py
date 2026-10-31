#!/usr/bin/env python3
"""
Scene stills + 2x2 patrol video | MDRIIA Group 05 | Owner: E043 Muaaz
Also the source footage for the LinkedIn demo (backlog M-15).

  python src/render_scene_media.py --seconds 60
Writes docs/figures/<scene>/patrol_<scene>_*.png and patrol_2x2_<scene>.mp4
"""
import argparse
import os
import subprocess
import sys

import mujoco
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import aerial_patrol_swarm as aps   # noqa: E402

FIG_ROOT = os.path.join(ROOT, "docs", "figures")
VIEWS = {
    "interior": [("atrium_view", "Atrium (ground)"), ("chase_alpha", "Alpha chase - corridor loop"),
                 ("cam_alpha_fwd", "Alpha surveillance camera (640x480)"), ("chase_bravo", "Bravo chase - atrium sweep")],
    "exterior": [("control_room", "Overview"), ("chase_alpha", "UAV Alpha chase"),
                 ("cam_alpha", "UAV Alpha nadir camera (640x480 feed)"), ("chase_bravo", "UAV Bravo chase")],
}


def label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 8 + 7 * len(text), 22), fill=(0, 0, 0))
    d.text((5, 5), text, fill=(255, 255, 255))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60.0, help="patrol seconds to record")
    ap.add_argument("--warmup", type=float, default=8.0, help="take-off seconds skipped")
    ap.add_argument("--scene", default="interior", choices=tuple(aps.SCENES))
    ap.add_argument("--policy", default="sectors")
    a = ap.parse_args()
    OUT = os.path.join(FIG_ROOT, a.scene)
    os.makedirs(OUT, exist_ok=True)

    ctl = aps.DualUAVSurveillanceController(model_path=aps.SCENES[a.scene], policy=a.policy, seed=4,
                                            intruder_appear_s=a.warmup + 2, vision=False)
    views = VIEWS[a.scene]
    while ctl.current_time_s < a.warmup:
        ctl.step_simulation(dt=1 / 30)

    W, H, fps = 640, 360, 30
    video = os.path.join(OUT, f"patrol_2x2_{a.scene}.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{2 * W}x{2 * H}", "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p",
                           "-c:v", "libx264", "-crf", "22", video], stdin=subprocess.PIPE)
    stills = {a.seconds * 0.35: "early", a.seconds * 0.8: "late"}
    with mujoco.Renderer(ctl.model, H, W) as r, mujoco.Renderer(ctl.model, 720, 1280) as big:
        n = int(a.seconds * fps)
        for k in range(n):
            ctl.step_simulation(dt=1 / fps)
            tiles = []
            for cam, name in views:
                r.update_scene(ctl.data, camera=cam)
                tiles.append(label(Image.fromarray(r.render()), f"{name}   t={ctl.current_time_s:5.1f}s"))
            grid = Image.new("RGB", (2 * W, 2 * H))
            for i, t in enumerate(tiles):
                grid.paste(t, ((i % 2) * W, (i // 2) * H))
            ff.stdin.write(grid.tobytes())
            for ts, tag in list(stills.items()):
                if k / fps >= ts:
                    for cam, _ in views:
                        big.update_scene(ctl.data, camera=cam)
                        Image.fromarray(big.render()).save(os.path.join(OUT, f"patrol_{a.scene}_{tag}_{cam}.png"))
                    del stills[ts]
    ff.stdin.close(); ff.wait()
    print("wrote", video)


if __name__ == "__main__":
    main()
