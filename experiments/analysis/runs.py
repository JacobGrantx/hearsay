"""Shared loading and statistics for the main-run analysis (pre-registered in EXPERIMENTS.md).

Every number the analysis reports is computed from the files in a run directory:
record.json, layout.json, events.jsonl, metrics.jsonl and state.jsonl.gz.
"""
from __future__ import annotations

import gzip
import json
import os
import statistics
from functools import cached_property
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = Path(os.environ.get("DL_RESULTS", REPO / "experiments" / "results"))
OUTPUT = REPO / "experiments" / "analysis" / "output"

AI = ["full", "no_talk", "no_memory", "frozen_hornets", "labels_good_bad"]
SCRIPTED = ["rule_bees", "random_bees"]
CONDITIONS = AI + SCRIPTED
# The main runs: every condition was launched at one commit (9cb4e7a) in one batch, so they share a stamp.
MAIN_STAMP = os.environ.get("DL_MAIN_STAMP", "20261106T101558Z")
PAIRED_SEEDS = [0, 1, 2]
# Categorical slots 1 to 7 of the dataviz reference palette, in fixed order (validated for colour vision deficiency).
COLORS = dict(zip(CONDITIONS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]))
SEASONS = ["spring", "summer", "autumn", "winter"]


class Run:
    """One seed directory of one condition."""

    def __init__(self, path: Path):
        self.path = path
        self.condition = path.parent.parent.name
        self.seed = int(path.name.split("-")[1])

    @property
    def name(self) -> str:
        return str(self.path.relative_to(RESULTS))

    @cached_property
    def record(self) -> dict:
        return json.loads((self.path / "record.json").read_text())

    @cached_property
    def layout(self) -> dict:
        return json.loads((self.path / "layout.json").read_text())

    @cached_property
    def events(self) -> list[dict]:
        with open(self.path / "events.jsonl", encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    @cached_property
    def metrics(self) -> list[dict]:
        with open(self.path / "metrics.jsonl", encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    @cached_property
    def states(self) -> list[dict]:
        with gzip.open(self.path / "state.jsonl.gz", "rt", encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    @cached_property
    def hive(self) -> set[tuple[int, int]]:
        return {(x, y) for y, row in enumerate(self.layout["rows"]) for x, c in enumerate(row) if c in "HE"}

    def of(self, kind: str) -> list[dict]:
        return [e for e in self.events if e.get("kind") == kind]

    @property
    def final(self) -> dict:
        return self.record.get("final_metrics") or {}


def runs(condition: str, stamp: str = MAIN_STAMP) -> dict[int, Run]:
    """Completed seeds (those with a record.json) of one condition's main batch, by seed."""
    base = RESULTS / condition / stamp
    out = {}
    for d in sorted(base.glob("seed-*")):
        if (d / "record.json").exists():
            r = Run(d)
            out[r.seed] = r
    return out


def describe(values: dict[int, float | None]) -> dict:
    """Mean, sd and n over the seeds that have a value; missing values are listed, never counted as zero."""
    present = {s: v for s, v in values.items() if v is not None}
    vals = list(present.values())
    return {
        "n": len(vals),
        "mean": round(statistics.fmean(vals), 4) if vals else None,
        "sd": round(statistics.stdev(vals), 4) if len(vals) > 1 else None,
        "per_seed": {str(s): (round(v, 4) if v is not None else None) for s, v in sorted(values.items())},
    }


def paired(a: dict[int, float | None], b: dict[int, float | None], seeds=PAIRED_SEEDS) -> dict:
    """Pre-registered rule: a - b is consistent when it has the same sign on every paired seed
    and the mean paired difference is larger than the sd of the paired differences."""
    diffs = {s: a[s] - b[s] for s in seeds if a.get(s) is not None and b.get(s) is not None}
    d = list(diffs.values())
    mean = statistics.fmean(d) if d else None
    sd = statistics.stdev(d) if len(d) > 1 else None
    same_sign = len(d) == len(seeds) and (all(x > 0 for x in d) or all(x < 0 for x in d))
    consistent = bool(same_sign and sd is not None and abs(mean) > sd)
    return {
        "diffs": {str(s): round(v, 4) for s, v in diffs.items()},
        "mean": round(mean, 4) if mean is not None else None,
        "sd": round(sd, 4) if sd is not None else None,
        "n": len(d),
        "same_sign": same_sign,
        "consistent": consistent,
        "verdict": ("consistently higher" if consistent and mean > 0 else
                    "consistently lower" if consistent else "no consistent difference"),
    }


def fmt(stat: dict, digits: int = 3) -> str:
    """'mean (sd x, n k)' for markdown tables."""
    if stat["mean"] is None:
        return "missing (n 0)"
    sd = f"{stat['sd']:.{digits}f}" if stat["sd"] is not None else "n/a"
    return f"{stat['mean']:.{digits}f} (sd {sd}, n {stat['n']})"
