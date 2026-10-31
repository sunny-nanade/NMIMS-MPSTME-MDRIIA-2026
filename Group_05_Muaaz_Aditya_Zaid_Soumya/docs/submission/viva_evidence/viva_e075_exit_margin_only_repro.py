"""Viva-prep reproduction of E075's documented AI error: exit margin only (tier-3 dwell off via GEOFENCE_CONFIRM_N = 1).
Imports the demo from this tree's analytics/ (not modified); --no-write so no breach log is touched."""
import os, sys
W = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, W + "/analytics"); sys.path.insert(0, W + "/src")
import geofence_noise_demo as d
if os.environ.get("VIVA_FULL_HYSTERESIS") != "1":
    d.aps.DualUAVSurveillanceController.GEOFENCE_CONFIRM_N = 1      # dwell off -> exit margin only
sys.argv = ["x", "--no-write"]
d.main()
