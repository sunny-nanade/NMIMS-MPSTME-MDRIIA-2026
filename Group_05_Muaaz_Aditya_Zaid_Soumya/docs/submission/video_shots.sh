#!/usr/bin/env bash
# Video shot menu | MDRIIA Group 05 MPSTME GUARDIAN | Owner: E043 Muaaz
#
# Usage (from the group folder, or from anywhere -- the script cd's there itself):
#   docs/submission/video_shots.sh            # numbered menu
#   docs/submission/video_shots.sh 1          # run one shot directly (1, 2, 3, 3b, 4)
#   docs/submission/video_shots.sh check      # headless self-test: every shot builds its model and runs 1 s
#
# The FSM timelines echoed below were MEASURED by short headless runs of the same configuration
# (same controller, same 1/60 s frame step as src/view_live.py at --speed 1):
#   python docs/submission/viva_evidence/viva_video_shot_timelines.py 1 2 3 3b
# output committed as docs/submission/viva_evidence/viva_video_shot_timelines.txt; re-run it after any
# change to src/aerial_patrol_swarm.py and copy the times here. They are sim time,
# shown in the overlay "t" row. Keep --speed 1, or the vision ticks shift and the times move.
# If the overlay says "Vision off" (off-screen renderer could not start next to the viewer), the
# FSM stays in PATROL: use the backup clips in docs/figures/video_backup/ (regenerable, never committed).

set -u
G="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$G" || exit 1

VENV_BIN="/Users/muaazshaikh/mdriia-project/.venv/bin"
if [ -x "$VENV_BIN/mjpython" ]; then MJPY="$VENV_BIN/mjpython"
elif command -v mjpython >/dev/null 2>&1; then MJPY="$(command -v mjpython)"
else MJPY="${PYTHON:-python3}"; fi            # Windows / Linux: plain python runs the passive viewer
if [ -x "$VENV_BIN/python" ]; then PY="$VENV_BIN/python"; else PY="${PYTHON:-python3}"; fi

SHOT1=(src/view_live.py --scene interior --rays --seed 4 --appear 20)
SHOT2=(src/view_live.py --scene exterior --seed 4 --appear 20)
SHOT3=(src/view_live.py --demo headon --rays)
SHOT3B=(src/view_live.py --demo headon --apf-only)
FIGS=(analytics/figures/campus_security_sensitivity.png analytics/figures/campus_security_queue.png)

shot1() {
  cat <<'EOF'
SHOT 1 -- interior (NMIMS Main Building atrium + corridors), FSM + FR-18 sensor rays
  measured (seed 4, appear 20 s, sectors):
    t ~  6.8 s  both UAVs PATROL (Bravo 6.0 s, Alpha 6.8 s)
    t ~ 36.3 s  Alpha DETECT, rejected in VERIFY at 36.4 s (one-tick blip back to PATROL -- that is the gate working)
    t ~ 36.5 s  Alpha DETECT -> VERIFY 36.6 s -> ALERT_0 36.7 s
    t ~ 36.8 s  Bravo TRACK (E051 picks Bravo as tracker; Alpha keeps patrolling)
    t ~ 44.5 s  Bravo RETURN_TO_PATROL (target lost), incident closed, true detection; Bravo PATROL 55.3 s
    t ~ 52.9 s  Alpha DETECT -> VERIFY 53.0 s -> ALERT_1 53.1 s -> Alpha TRACK 53.2 s (second incident, true detection)
    t ~ 68.9 s  Alpha RETURN_TO_PATROL, Bravo TRACK; Bravo RETURN_TO_PATROL 71.8 s (lost); both PATROL by 84.3 s
  min separation 5.71 m, 0 UAV-UAV contacts, 0 obstacle contacts in this run.
EOF
  "$MJPY" "${SHOT1[@]}"
}

shot2() {
  cat <<'EOF'
SHOT 2 -- campus, patrol inside the college wall (exterior scene)
  measured (seed 4, appear 20 s, sectors; docs/submission/viva_evidence/viva_video_shot_timelines.txt):
    t ~ 29.1 s  Bravo PATROL (Alpha still DESCEND until 34.1 s)
    t ~ 29.1 s  Bravo DETECT -> VERIFY 29.2 s -> ALERT_2 29.3 s
    t ~ 29.4 s  Bravo TRACK
    t ~ 59.4 s  Bravo RETURN_TO_PATROL (30 s track limit), incident closed, true detection
    t ~ 71.3 s  Bravo back in PATROL
  CUT BEFORE t ~ 60.2 s: Alpha then opens incidents at 60.2 s, 70.8 s, 88.2 s and 105.6 s
  that the run scores as false alarms (true_detection False).
  Do not present those as intruder detections.
  min separation 13.43 m, 0 UAV-UAV contacts, 0 obstacle contacts in this run.
EOF
  "$MJPY" "${SHOT2[@]}"
}

shot3() {
  cat <<'EOF'
SHOT 3 -- head-on separation encounter, handled (layered separation: governor + APF)
  measured: 6 m/s each, same altitude, no wind, 60 m span inside the campus wall
    min centre distance 7.12 m at t ~ 6.2 s (bound 2.5 m) -> overlay Result "held", 0 UAV-UAV contacts
EOF
  "$MJPY" "${SHOT3[@]}"
}

shot3b() {
  cat <<'EOF'
SHOT 3b -- same encounter, guide APF alone (governor disabled): the failure
  measured: min centre distance 0.43 m at t ~ 5.7 s, 4 UAV-UAV contact steps logged
    (airframes touch below 0.76 m) -> overlay Result "CONTACT"
  Show 3b first, then 3, to tell the "failure found, failure handled" story.
EOF
  "$MJPY" "${SHOT3B[@]}"
}

shot4() {
  echo "SHOT 4 -- business case graphs (E077): sensitivity, then queue. Ratios only, no currency."
  if command -v open >/dev/null 2>&1; then open -a Preview "${FIGS[@]}"
  else echo "open the figures manually: ${FIGS[*]}"; fi
}

check() {
  # Headless: run each viewer command through view_live.main() with a stand-in passive viewer
  # (real MjvScene for the rays, no window) for 1 s of sim time, then check that the figures exist.
  local rc=0 LOG
  LOG="$(mktemp -t video_shots_check.XXXXXX)"
  for args in "${SHOT1[*]}" "${SHOT2[*]}" "${SHOT3[*]}" "${SHOT3B[*]}"; do
    echo "check: $args"
    # shellcheck disable=SC2086
    if ! "$PY" - $args > "$LOG" 2>&1 <<'EOF'
import os, sys, contextlib, threading
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.join(os.getcwd(), "src"))
import mujoco, view_live as vl
class Cam: lookat = [0.0, 0.0, 0.0]; distance = azimuth = elevation = 0.0
class FakeViewer:
    def __init__(self, m, d): self.n, self.cam, self.user_scn = 0, Cam(), mujoco.MjvScene(m, maxgeom=2000)
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def is_running(self): self.n += 1; return self.n <= 60
    def lock(self): return contextlib.nullcontext()
    def set_texts(self, t): pass
    def sync(self): pass
vl.viewer.launch_passive = lambda m, d: FakeViewer(m, d)
vl.time.sleep = lambda s: None
vl.main()
print("\n  ok")
EOF
    then rc=1; echo "  FAILED:"; tail -n 20 "$LOG"
    else tr '\r' '\n' < "$LOG" | tail -n 2; fi
  done
  rm -f "$LOG"
  for f in "${FIGS[@]}"; do [ -f "$f" ] && echo "check: $f ok" || { echo "check: MISSING $f"; rc=1; }; done
  return $rc
}

run() {
  case "$1" in
    1) shot1 ;; 2) shot2 ;; 3) shot3 ;; 3b|3B) shot3b ;; 4) shot4 ;; check) check ;;
    q|Q) exit 0 ;;
    *) echo "unknown choice: $1" ;;
  esac
}

if [ $# -gt 0 ]; then run "$1"; exit $?; fi
while true; do
  cat <<'EOF'

MPSTME GUARDIAN -- video shots (viewer: mjpython; close the window to come back here)
  1)  interior: FSM PATROL -> DETECT -> VERIFY -> ALERT -> TRACK -> RETURN, with sensor rays
  2)  campus inside the wall: FSM cycle, ALERT_2
  3)  head-on conflict, handled (layered separation)
  3b) head-on conflict, APF only (the failure -- show before 3)
  4)  business graphs in Preview (sensitivity, queue)
  check) headless self-test of every shot
  q)  quit
EOF
  read -r -p "shot> " c || exit 0
  run "$c"
done
