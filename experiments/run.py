#!/usr/bin/env python3
"""Run one experiment config across its seeds and record what is needed to reproduce it.

    python experiments/run.py experiments/configurations/smoke.toml
    python experiments/run.py CONFIG --seeds 0 1 2 3 4 --tag more-seeds
    python experiments/run.py CONFIG --set mutation_rate=0.05     # override a param

Config (TOML):
    [experiment]
    name = "smoke"
    entrypoint = "digital_life.smoke:run"   # module:function
    hypothesis = "..."                       # copied into each run record
    seeds = [0, 1, 2]

    [params]
    # anything; passed to the entrypoint as a dict

The entrypoint is run(params: dict, seed: int, log: RunLog) -> dict | None.
What it returns is stored as the run's final metrics; log.metric() records time series.

Output:
    experiments/results/<name>/<UTC time>[_<tag>]/
        config.toml                 the exact config used
        summary.json                final metrics per seed, plus mean/sd/min/max across seeds
        seed-<n>/record.json        params, seed, provenance (git commit, dirty flag, versions), timing
        seed-<n>/metrics.jsonl      time series
        seed-<n>/events.jsonl       notable behaviour
"""
from __future__ import annotations

import argparse
import ast
import importlib
import json
import shutil
import statistics
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from digital_life.runlog import RunLog, provenance, seed_everything, utc_now  # noqa: E402


def load_entrypoint(spec: str):
    module, _, func = spec.partition(":")
    return getattr(importlib.import_module(module), func)


def parse_override(s: str):
    k, _, v = s.partition("=")
    try:
        return k, ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return k, v


def summarise(finals: dict[int, dict]) -> dict:
    keys = sorted({k for m in finals.values() for k, v in (m or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)})
    across = {}
    for k in keys:
        vals = [m[k] for m in finals.values() if m and k in m]
        across[k] = {
            "n": len(vals),
            "mean": statistics.fmean(vals),
            "sd": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "min": min(vals),
            "max": max(vals),
        }
    return across


def run(config_path: Path, seeds: list[int] | None = None, tag: str = "", overrides: list[str] | None = None, results_root: Path | None = None) -> Path:
    cfg = tomllib.loads(config_path.read_text())
    exp = cfg["experiment"]
    params = dict(cfg.get("params", {}))
    overrides = list(overrides or [])
    for o in overrides:
        k, v = parse_override(o)
        params[k] = v
    seeds = list(seeds or exp.get("seeds", [0]))
    fn = load_entrypoint(exp["entrypoint"])

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (results_root or REPO / "experiments" / "results") / exp["name"] / (stamp + (f"_{tag}" if tag else ""))
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(config_path, out / "config.toml")

    prov = provenance()
    finals = {}
    for seed in seeds:
        sdir = out / f"seed-{seed}"
        log = RunLog(sdir)
        seed_everything(seed)
        t0, started = time.perf_counter(), utc_now()
        error = None
        try:
            finals[seed] = fn(params, seed, log) or {}
        except Exception as ex:  # record the failure; a crash is a result too
            error = f"{type(ex).__name__}: {ex}"
            finals[seed] = None
        finally:
            log.close()
        record = {
            "experiment": exp["name"],
            "hypothesis": exp.get("hypothesis"),
            "entrypoint": exp["entrypoint"],
            "params": params,
            "overrides": list(overrides),
            "seed": seed,
            "started": started,
            "seconds": round(time.perf_counter() - t0, 3),
            "final_metrics": finals[seed],
            "error": error,
            "provenance": prov,
        }
        (sdir / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"seed {seed}: {'ERROR ' + error if error else finals[seed]}")

    summary = {"experiment": exp["name"], "config": str(config_path), "seeds": seeds, "per_seed": finals, "across_seeds": summarise(finals), "provenance": prov}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if prov["git_dirty"]:
        print("note: working tree had uncommitted changes; commit before runs you plan to cite")
    print(f"results: {out.relative_to(REPO) if out.is_relative_to(REPO) else out}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", type=Path)
    ap.add_argument("--seeds", type=int, nargs="+")
    ap.add_argument("--tag", default="")
    ap.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    run(a.config, a.seeds, a.tag, a.overrides)
    return 0


if __name__ == "__main__":
    sys.exit(main())
