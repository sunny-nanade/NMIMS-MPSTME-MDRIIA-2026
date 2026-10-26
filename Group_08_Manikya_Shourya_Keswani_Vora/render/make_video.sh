#!/usr/bin/env bash
# Cinematic flood video (the one shown in chat): Linux + MuJoCo C SDK + EGL + ffmpeg.
# Usage: bash render/make_video.sh /path/to/mujoco-3.3.0   [out.mp4]
set -e
MJ=${1:?path to the MuJoCo 3.x release folder (contains include/ and lib/)}
OUT=${2:-skyhydro_flood.mp4}
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(dirname "$HERE"); TMP=${TMPDIR:-/tmp}/skyhydro_render
mkdir -p "$TMP"
gcc -O2 "$HERE/skyrender.c" -I"$MJ/include" -L"$MJ/lib" -lmujoco -l:libEGL.so.1 -lm -Wl,-rpath,"$MJ/lib" -o "$TMP/skyrender"
python3 "$HERE/flight_path.py" "$TMP/path.txt"
( cd "$ROOT/environment" && EGL_PLATFORM=surfaceless "$TMP/skyrender" scene_flood.xml "$TMP/path.txt" 24 "$TMP/full" 1.2 )
mkdir -p "$TMP/frames"
python3 "$HERE/water_shader.py" "$TMP/full" "$TMP/frames" --path "$TMP/path.txt" --xml "$ROOT/environment/scene_flood.xml"
ffmpeg -y -loglevel error -framerate 24 -i "$TMP/frames/frame_%04d.png" -pix_fmt yuv420p -c:v libx264 -crf 20 "$OUT"
echo "video -> $OUT"
