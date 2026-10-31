#!/usr/bin/env python3
"""
G-05: manifest of the per-run 500 Hz telemetry + one committed sample per (scene, condition) cell.
Group: MDRIIA Group 05 | Owner: E043 Muaaz (integration)

The full per-run files analytics/runs/<run_id>.csv.gz stay LOCAL (about 1.4 GB for the 180-run batch, regenerable
from the seeds with analytics/run_benchmark.py). This script writes
  analytics/runs/MANIFEST.csv   one row per run in campus_patrol_real_trials.csv:
      run_id, rows (data rows in the full file), sha256 (of the full .csv.gz bytes), dt_check
      (OK, or the observed set of step sizes), t_end_s, bytes, sample_file, sample_rows
  analytics/runs/samples/<run_id>.sample.csv.gz   for seed SAMPLE_SEED of every cell: the FIRST sample_rows rows of the
      full file (header kept, cut on a whole-timestep boundary), the largest prefix whose gzip is <= MAX_SAMPLE_BYTES.
      A sample is a truncated prefix, not the whole run; sample_rows < rows says so.
dt_check: per agent (uav column; the guard has one agent) the time column t must advance by exactly TIMESTEP_S
(0.002 s; t is written with 3 decimals) at every row. Run: python analytics/make_run_manifest.py [--workers N]
"""
import argparse
import csv
import gzip
import hashlib
import io
import multiprocessing as mp
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
SAMPLES = os.path.join(RUNS, "samples")
TRIALS = os.path.join(HERE, "campus_patrol_real_trials.csv")
TIMESTEP_S = 0.002
SAMPLE_SEED = 1
MAX_SAMPLE_BYTES = 3_000_000


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def scan(run_id):
    path = os.path.join(RUNS, run_id + ".csv.gz")
    with gzip.open(path, "rt", newline="") as f:
        rd = csv.reader(f)
        head = next(rd)
        it, iu = head.index("t"), head.index("uav") if "uav" in head else None
        rows, last, bad, tmax = 0, {}, set(), 0.0
        for r in rd:
            rows += 1
            t = round(float(r[it]), 3)
            k = r[iu] if iu is not None else ""
            if k in last:
                d = round(t - last[k], 3)
                if d != TIMESTEP_S:
                    bad.add(d)
            last[k] = t
            tmax = max(tmax, t)
    return {"run_id": run_id, "rows": rows, "sha256": sha256_file(path), "bytes": os.path.getsize(path),
            "dt_check": "OK" if not bad else "FAIL steps=" + ";".join(str(b) for b in sorted(bad)), "t_end_s": tmax}


def gz_size(text):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as g:
        g.write(text.encode())
    return buf.getvalue()


def make_sample(run_id):
    """largest whole-timestep prefix of the run's telemetry whose gzip is <= MAX_SAMPLE_BYTES."""
    with gzip.open(os.path.join(RUNS, run_id + ".csv.gz"), "rt", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    head, body = lines[0], lines[1:]
    iu = head.rstrip("\n").split(",").index("uav") if "uav" in head else None
    per_step = len({ln.split(",")[iu] for ln in body[:50]}) if iu is not None else 1
    lo, hi = 1, len(body) // per_step           # steps kept
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        data = gz_size(head + "".join(body[: mid * per_step]))
        if len(data) <= MAX_SAMPLE_BYTES:
            best, lo = (mid * per_step, data), mid + 1
        else:
            hi = mid - 1
    n, data = best
    os.makedirs(SAMPLES, exist_ok=True)
    out = run_id + ".sample.csv.gz"
    with open(os.path.join(SAMPLES, out), "wb") as f:
        f.write(data)
    return out, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    with open(TRIALS, newline="") as f:
        runs = [(r["run_id"], r["scene"], r["condition"], int(r["seed"])) for r in csv.DictReader(f)]
    with mp.Pool(a.workers) as p:
        info = dict((x["run_id"], x) for x in p.map(scan, [r[0] for r in runs]))
        want = [r[0] for r in runs if r[3] == SAMPLE_SEED]
        smp = dict(zip(want, p.map(make_sample, want)))
    cols = ["run_id", "rows", "sha256", "dt_check", "t_end_s", "bytes", "sample_file", "sample_rows"]
    with open(os.path.join(RUNS, "MANIFEST.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        for rid, *_ in runs:
            row = dict(info[rid])
            row["sample_file"], row["sample_rows"] = smp.get(rid, ("", ""))
            w.writerow({c: row.get(c, "") for c in cols})
    print("wrote", os.path.join(RUNS, "MANIFEST.csv"), len(runs), "runs;", len(smp), "samples")


if __name__ == "__main__":
    main()
