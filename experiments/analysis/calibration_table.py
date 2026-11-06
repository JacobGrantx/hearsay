#!/usr/bin/env python3
"""Markdown table of the setup calibration, read from experiments/results/calibrate_*/*/summary.json.

    python experiments/analysis/calibration_table.py [TAG ...]

One row per calibration point (run tag) and policy: mean and sd across seeds of the spring delivery rate
(trips that delivered / trips that ended, in spring), spring stings per trip, total deliveries and mean
colony size, with n seeds and the per-seed spring rates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"


def fmt(stat: dict | None) -> str:
    if not stat:
        return "n/a"
    return f"{stat['mean']:.3f} (sd {stat['sd']:.3f})"


def main(tags: list[str]) -> int:
    rows = []
    for summary in sorted(RESULTS.glob("calibrate_*/*/summary.json")):
        run_dir = summary.parent
        tag = run_dir.name.partition("_")[2]
        if tags and tag not in tags:
            continue
        s = json.loads(summary.read_text())
        a = s["across_seeds"]
        per_seed = [s["per_seed"][str(k)].get("spring_rate") if s["per_seed"].get(str(k)) else None for k in s["seeds"]]
        rows.append((tag, s["experiment"].removeprefix("calibrate_"), a.get("spring_rate", {}).get("n", 0),
                     fmt(a.get("spring_rate")), fmt(a.get("spring_stings_per_trip")), fmt(a.get("deliveries")),
                     fmt(a.get("bees_mean")), per_seed, f"{run_dir.parent.name}/{run_dir.name}",
                     s["provenance"]["git_dirty"]))
    print("| point | bees | n | spring delivery rate | spring stings per trip | deliveries (2 years) | mean colony size | per-seed spring rate | run directory | dirty |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
