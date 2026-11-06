"""Pack each run's replay-cache entries into one gzip file, so the cache stays small enough to commit.

Usage:
    python tools/pack_llm_cache.py RUN_DIR [RUN_DIR ...] [--source DIR] [--dest DIR] [--order key|run]

RUN_DIR is a seed directory, experiments/results/<experiment>/<stamp>/seed-<n>. The tool reads the
prompt_key of every decision and mind_error event in its events.jsonl (the first 12 hex digits of the
cache key), finds the matching loose entries in SOURCE (<k[:2]>/<key>.json, default
experiments/llm_cache), and writes DEST/<experiment>_<stamp>_seed-<n>.jsonl.gz (default
experiments/llm_cache): one line per call, {"key", "request", "response"}, sorted by key (or with
--order run, by bee and tick of first use), with a fixed gzip header so the same entries always
give the same bytes.

digital_life.llm reads these packs in auto and replay mode. A prompt_key with no entry, or with
more than one, is reported and the exit code is 1, so a run that cannot replay is never packed
silently.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = REPO / "experiments" / "llm_cache"


def prompt_keys(run_dir: Path, order: str = "key") -> list[str]:
    """The run's prompt keys, sorted by key, or with order "run" by (bee, tick) of first use. Run order puts each
    bee's consecutive prompts side by side, which roughly halves the gzip size; the reader does not care."""
    first: dict[str, tuple[int, int]] = {}
    with open(run_dir / "events.jsonl", encoding="utf-8") as f:
        for line in f:
            ev = json.loads(line)
            if ev.get("kind") in ("decision", "mind_error") and ev.get("prompt_key"):
                first.setdefault(ev["prompt_key"], (ev.get("bee", -1), ev["t"]))
    return sorted(first) if order == "key" else sorted(first, key=lambda k: (*first[k], k))


def loose_index(source: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in source.glob("??/*.json"):
        index.setdefault(path.stem[:12], []).append(path)
    return index


def pack_name(run_dir: Path) -> str:
    seed, stamp, experiment = run_dir.name, run_dir.parent.name, run_dir.parent.parent.name
    return f"{experiment}_{stamp}_{seed}.jsonl.gz"


def pack(run_dir: Path, index: dict[str, list[Path]], dest: Path, order: str = "key") -> tuple[Path, int, list[str]]:
    problems, lines = [], []
    for k in prompt_keys(run_dir, order):
        paths = index.get(k, [])
        if len(paths) != 1:
            problems.append(f"{k}: {len(paths)} cache entries")
            continue
        rec = json.loads(paths[0].read_text(encoding="utf-8"))
        lines.append(json.dumps({"key": paths[0].stem, "request": rec["request"], "response": rec["response"]},
                                sort_keys=True, ensure_ascii=False))
    if order == "key":
        lines.sort()
    out = dest / pack_name(run_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
        gz.write(("\n".join(lines) + "\n").encode("utf-8") if lines else b"")
    return out, len(lines), problems


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("runs", type=Path, nargs="+", help="seed directories to pack")
    ap.add_argument("--source", type=Path, default=DEFAULT_CACHE, help="loose cache to read")
    ap.add_argument("--dest", type=Path, default=DEFAULT_CACHE, help="where the packs go")
    ap.add_argument("--order", choices=["key", "run"], default="key",
                    help="entry order: by key (the main runs' packs) or by bee and tick (smaller; used from E5 on)")
    a = ap.parse_args()
    index = loose_index(a.source)
    failed = False
    for run_dir in a.runs:
        out, n, problems = pack(run_dir, index, a.dest, a.order)
        print(f"{out}: {n} calls, {out.stat().st_size / 1e6:.2f} MB")
        for p in problems:
            print(f"  missing or ambiguous: {p}", file=sys.stderr)
        failed |= bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
