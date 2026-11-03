# Running on your Mac (Terminal)

```bash
cd ~/Documents/NMIMS-MPSTME-MDRIIA-2026/Group_11_Daneeka
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. check the model loads
python -c "import mujoco; m=mujoco.MjModel.from_xml_path('models/solar_defect_amr.xml'); print(m.nu, 'actuators, dt', m.opt.timestep)"

# 2. one headless mission + 500 Hz telemetry CSV
python src/run_simulation.py --condition proposed --seed 3009 --csv results/telemetry/my_run.csv

# 3. LIVE viewer for the showcase (mjpython is required on macOS)
mjpython src/run_simulation.py --viewer --condition proposed --seed 3009
mjpython src/run_simulation.py --viewer --condition baseline --seed 3009     # same farm, baseline controller

# 4. regenerate every result (about 10 min + 40 min for scenarios)
python analytics/run_evaluation.py --n 30 --workers 2
python analytics/run_scenarios.py  --n 30 --workers 2
python analytics/statistics_report.py
python analytics/fmea.py
python analytics/solar_pv_roi.py
python analytics/make_figures.py

# 5. tests
pytest -q
```
Blender (optional visuals): `/Applications/Blender.app/Contents/MacOS/Blender --background --python blender/generate_solar_farm.py -- --out results/blender --render`

## Live dashboard (show the connection + the recording in the viva)

Terminal 1 (MuJoCo window + dashboard server + 500 Hz recording to CSV):

    source .venv/bin/activate
    mjpython src/run_simulation.py --viewer --dashboard --condition proposed --seed 3009 --speed 4 --csv results/telemetry/live_run.csv

Then open http://127.0.0.1:8765/ in a browser and put it next to the MuJoCo window.

What it shows, and how to explain it:
- The page polls /state every 200 ms. /state is filled from the running mission object (same `d.xpos`, estimator, FSM, detections) every 16 physics steps, so it is the simulation itself, not a replay.
- "Telemetry rows" counts `Telemetry.log()` calls: one per physics step (0.002 s = 500 Hz). It should read about 500 rows per simulated second. The CSV (24 columns) is written when the mission ends; open it afterwards to show the rows.
- Red = flagged defect, green = inspected healthy, amber = shadow rejected. The page never sees the hidden defect list except to count "true" flags.
