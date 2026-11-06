"""Progress of the round 2 runs: per run, the last tick logged, ticks per second, spend, decisions and model errors.

Usage: .venv/bin/python tools/round2_progress.py [--results DIR] [--caches DIR]
Defaults are the round 2 clone and cache folders on /dev/shm (docs/BUILD_NOTES.md, "Round 2 runs").
Reads only the tail of each events.jsonl, so it is cheap to run while the runs go on.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def last_line(path: Path) -> dict | None:
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - 65536))
        lines = f.read().splitlines()
    for line in reversed(lines):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=Path("/dev/shm/dl-r2/experiments/results"))
    ap.add_argument("--caches", type=Path, default=Path("/dev/shm/dl-r2-cache"))
    a = ap.parse_args()
    now, total = datetime.now(timezone.utc), 0.0
    for d in sorted(a.results.glob("r2_*/*_s*/seed-*")):
        ev = d / "events.jsonl"
        if not ev.exists():
            continue
        name, tag = d.parent.parent.name, d.parent.name.rsplit("_", 1)[-1]
        stamp = datetime.strptime(d.parent.name.split("_")[0], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        last = last_line(ev) or {}
        tick = last.get("t", 0)
        secs = (now - stamp).total_seconds()
        spend_file = a.caches / f"{name}_{tag}" / "spend.json"
        spend = json.loads(spend_file.read_text()) if spend_file.exists() else {"usd": 0.0, "calls": 0}
        total += spend["usd"]
        done = (d / "record.json").exists()
        print(f"{name:13s} {tag:3s} tick {tick:5d}  {tick / secs if secs else 0:5.2f} t/s  ${spend['usd']:.3f}  "
              f"{spend['calls']:6d} calls  {'DONE' if done else 'running'}")
    print(f"total run spend ${total:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
