"""Re-run one recorded seed offline from the replay cache and check the result is identical.

Usage:
    python experiments/replay_check.py experiments/results/<experiment>/<stamp>/seed-<n> [--out DIR]

Reads the run's own config.toml (saved beside the seed directories) and the overrides in its
record.json, runs that seed again with LLM_MODE=replay (no network, no key, no spend; a missing
cache entry stops the run), writes it under --out (default: a temporary directory), then compares
events.jsonl, metrics.jsonl, the decompressed state.jsonl.gz and final_metrics with the original.
Exit code 0 means every file is identical.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["LLM_MODE"] = "replay"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import run  # noqa: E402


def content(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()


def compare(original: Path, replay: Path) -> list[tuple[str, bool]]:
    out = []
    for name in ("events.jsonl", "metrics.jsonl", "state.jsonl.gz", "layout.json"):
        if (original / name).exists():
            out.append((name, (replay / name).exists() and content(original / name) == content(replay / name)))
    a = json.loads((original / "record.json").read_text())
    b = json.loads((replay / "record.json").read_text())
    out.append(("final_metrics", a["final_metrics"] == b["final_metrics"] and b["error"] is None))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    original = a.run_dir.resolve()
    record = json.loads((original / "record.json").read_text())
    root = a.out or Path(tempfile.mkdtemp(prefix="replay_"))
    overrides = list(record.get("overrides", []))
    if "vocab" not in record["params"]:
        # Runs made before phase 6 used the wording now called vocab "neutral", and their saved configs do not
        # say so. Every AI config since names its vocab (tests/test_vocab.py), so a missing vocab means round 1.
        overrides.append("vocab=neutral")
    if record.get("stopped_at_tick") is not None:
        # A run stopped by the wall clock (round 2) replays to the same tick, whatever the time is now.
        overrides += [f"stop_after={record['stopped_at_tick']}", "stop_wallclock_utc=None"]
    out = run(original.parent / "config.toml", [record["seed"]], "replay", overrides, results_root=root)
    replay = out / original.name
    rec = json.loads((replay / "record.json").read_text())
    print(f"original: {a.run_dir} (commit {record['provenance']['git_commit'][:7]}, {record['seconds']} s)")
    print(f"replay:   {replay} (commit {rec['provenance']['git_commit'][:7]}, {rec['seconds']} s, error {rec['error']})")
    results = compare(original, replay)
    for name, same in results:
        print(f"  {name:16s} {'identical' if same else 'DIFFERENT'}")
    ok = all(same for _, same in results)
    print("REPLAY IDENTICAL" if ok else "REPLAY DIFFERS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
