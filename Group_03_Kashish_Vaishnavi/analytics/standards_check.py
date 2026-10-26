"""Dossier Section 1.2: check the pod model against the standards the course lists.

    python analytics/standards_check.py

Runs a braking test in MuJoCo and reads the Monte Carlo trials, then writes
``analytics/standards_check.csv`` (one row per requirement: required, achieved, MET / DEVIATION).
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import aedrover  # noqa: F401
except ImportError:                      # exported course folder: the package is vendored under ../src
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from aedrover.capstone.standards import standards_report  # noqa: E402

HERE = Path(__file__).resolve().parent


def main() -> pd.DataFrame:
    csv = HERE / "aed_delivery_real_trials.csv"
    trials = pd.read_csv(csv) if csv.exists() else None
    rep = standards_report(trials)
    rep.to_csv(HERE / "standards_check.csv", index=False)
    for r in rep.itertuples():
        print(f"[{r.status:12s}] {r.standard}: {r.requirement}\n    required: {r.required}\n    achieved: {r.achieved}")
    return rep


if __name__ == "__main__":
    main()
