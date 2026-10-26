#!/usr/bin/env bash
# One-time setup on Linux: venv + CUDA PyTorch + deps + scene + live water + tests
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d .venv ] || $PY -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu126     # RTX 50-series: cu128
pip install -r requirements.txt
python check_gpu.py
(cd environment && python scene_generator.py --houses 5 --seed 1 --output scene_flood.xml)
python -m pytest tests -q
echo "Setup done.  Train: ./train.sh    Watch: ./sim.sh    Replay: ./sim.sh --replay"
