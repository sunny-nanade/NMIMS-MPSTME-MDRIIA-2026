"""
results/ — everything a training run produces that the simulation needs,
saved automatically by rl/train.py:

  results/
    registry.json              which trained pilot to use (latest + one per stage)
    stage1/  stage2/  stage3/
      model.zip                the trained pilot (best evaluation checkpoint)
      training_summary.json    settings, device, time, learning curve, test results
      replay.json              the trained pilot flying 3 test missions (positions, events, rewards)

simulate.py reads registry.json: `python simulate.py` flies the mission with
the most advanced trained pilot (live, the network decides every 0.1 s);
`python simulate.py --replay` plays its recorded flight from replay.json.
"""
import datetime
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
REGISTRY = os.path.join(RESULTS, "registry.json")


def _rel(p):
    return os.path.relpath(os.path.abspath(p), ROOT).replace(os.sep, "/")


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def load_registry():
    if os.path.exists(REGISTRY):
        with open(REGISTRY) as f:
            return json.load(f)
    return {"stages": {}, "latest": None}


def stage_dir(stage):
    return os.path.join(RESULTS, f"stage{stage}")


def save_stage(stage, model_zip, summary):
    """Copy the trained model into results/stage<k>/ and register it."""
    d = stage_dir(stage)
    if os.path.isdir(d) and os.listdir(d):                 # keep the previous result of this stage
        stamp = datetime.datetime.fromtimestamp(os.path.getmtime(d)).strftime("%Y%m%d_%H%M%S")
        old = os.path.join(RESULTS, "history", f"stage{stage}_{stamp}")
        os.makedirs(os.path.dirname(old), exist_ok=True)
        shutil.move(d, old)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(model_zip, os.path.join(d, "model.zip"))
    reg = load_registry()
    entry = {"stage": stage, "algo": summary.get("algo"), "model": _rel(os.path.join(d, "model.zip")),
             "replay": _rel(os.path.join(d, "replay.json")), "summary": _rel(os.path.join(d, "training_summary.json")),
             "trained_on": summary.get("device"), "timesteps": summary.get("timesteps"),
             "saved": datetime.datetime.now().isoformat(timespec="seconds")}
    reg["stages"][str(stage)] = entry
    reg["latest"] = entry
    with open(REGISTRY, "w") as f:
        json.dump(reg, f, indent=1)
    return d


def update_test(stage, test):
    reg = load_registry()
    if str(stage) in reg["stages"]:
        reg["stages"][str(stage)]["test"] = test
        if reg.get("latest") and reg["latest"]["stage"] == stage:
            reg["latest"]["test"] = test
        with open(REGISTRY, "w") as f:
            json.dump(reg, f, indent=1)


def best_entry(stage=None):
    """The registered pilot for `stage`, or the most advanced stage available."""
    reg = load_registry()
    st = reg.get("stages", {})
    keys = [str(stage)] if stage else sorted(st, key=int, reverse=True)
    for k in keys:
        e = st.get(k)
        if e and os.path.exists(_abs(e["model"])):
            return {**e, "model": _abs(e["model"]), "replay": _abs(e["replay"]), "summary": _abs(e["summary"])}
    return None


def model_for_stage(stage):
    e = best_entry(stage)
    return e["model"] if e else None
