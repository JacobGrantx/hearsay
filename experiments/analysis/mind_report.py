"""Behaviour and cost report for an AI run directory: how often bees decide, what they choose, and what it cost.

Usage: .venv/bin/python experiments/analysis/mind_report.py experiments/results/<name>/<stamp>/seed-<n> [...]
Prints JSON. Cost is priced from the token counts in decision events at the list prices in digital_life.llm.
Looks for the degenerate patterns the pilot is meant to catch: everyone waiting, endless sounds, never leaving home.
"""
from __future__ import annotations

import gzip
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from digital_life.llm import cost_usd  # noqa: E402


def report(d: Path) -> dict:
    events = [json.loads(line) for line in (d / "events.jsonl").read_text().splitlines()]
    record = json.loads((d / "record.json").read_text()) if (d / "record.json").exists() else {}
    model = record.get("params", {}).get("mind_model", "claude-haiku-5-5")
    dec = [e for e in events if e["kind"] == "decision"]
    ticks = 1 + max(e["t"] for e in events)
    per_tick = Counter(e["t"] for e in dec)
    usage = Counter()
    for e in dec:
        usage.update(e.get("usage", {}))
    home_ticks = total_ticks = 0
    with gzip.open(d / "state.jsonl.gz", "rt") as f:
        rows = f.read().splitlines()
    layout = json.loads((d / "layout.json").read_text())
    hive = {(x, y) for y, r in enumerate(layout["rows"]) for x, c in enumerate(r) if c in "HE"}
    for line in rows:
        for b in json.loads(line)["b"]:
            total_ticks += 1
            home_ticks += (b[1], b[2]) in hive
    says = [e for e in events if e["kind"] == "say"]
    return {
        "run": str(d), "ticks": ticks, "decisions": len(dec),
        "decisions_per_tick": round(len(dec) / ticks, 3),
        "ticks_with_a_decision": len(per_tick), "max_decisions_in_a_tick": max(per_tick.values(), default=0),
        "triggers": dict(Counter(e["trigger"] for e in dec).most_common()),
        "intents": dict(Counter(e["intent"] for e in dec).most_common()),
        "sounds": dict(Counter(e["sound"] for e in dec).most_common()),
        "remember_share": round(sum(bool(e["remember"]) for e in dec) / max(len(dec), 1), 3),
        "say_events": len(says), "say_heard_by_mean": round(statistics.mean(len(e["heard_by"]) for e in says), 2) if says else None,
        "share_of_bee_ticks_at_home": round(home_ticks / max(total_ticks, 1), 3),
        "fallbacks": sum(1 for e in dec if e.get("fallback")), "mind_errors": sum(e["kind"] == "mind_error" for e in events),
        "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
        "input_tokens_per_decision": round(usage["input_tokens"] / max(len(dec), 1)),
        "cost_usd_list_price": round(cost_usd(model, dict(usage)), 4),
        "events": dict(Counter(e["kind"] for e in events if e["kind"] not in ("decision", "llm_call")).most_common()),
        "wall_seconds": record.get("elapsed_s") or record.get("seconds"),
        "final_metrics": record.get("final_metrics"),
    }


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(json.dumps(report(Path(arg)), indent=1))
