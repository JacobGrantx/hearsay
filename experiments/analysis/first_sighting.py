"""What each AI bee does at its first sight of a hornet, before it was ever stung, under either vocabulary.

Round 1 (measures.naive_avoidance) counted flee or go_home. The abstract vocabulary offers no flee, so this also
classifies the move itself against the nearest hornet in view: `explore` in a direction pointing away from it
(negative dot product with the bearing), or `go_to` a cell farther from it than the bee is now, counts as away;
`go_home` (go_to_O) and `wait` (hold) are kept apart. Positions come from the state line of the tick before the
decision, which is what the bee sensed. Comparison: timer decisions taken with a hornet in view, before any sting.

Usage: .venv/bin/python experiments/analysis/first_sighting.py <seed dir> [...] [--until T]   (prints JSON)
--until T keeps decisions before tick T, to compare a full run's first spring with a pilot that stopped there.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from collections import Counter
from pathlib import Path

DIR_VEC = {"N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1), "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1)}
VISION = 4


def move_kind(e: dict, bee: tuple, hornet: tuple | None) -> str:
    if e["intent"] in ("go_home", "wait", "flee"):
        return {"go_home": "zone_O", "wait": "hold", "flee": "away"}[e["intent"]]
    if hornet is None:
        return "no_hornet_found"
    hx, hy = hornet[0] - bee[0], hornet[1] - bee[1]
    if e["intent"] == "explore":
        dx, dy = DIR_VEC[e["direction"]]
        dot = dx * hx + dy * hy
    else:  # go_to: farther from the hornet than now is away
        tx, ty = e["target"]
        dot = math.dist(bee, hornet) - math.dist((tx, ty), hornet)
    return "away" if dot < 0 else "toward" if dot > 0 else "sideways"


def classify(decisions: list[dict], states: list[dict]) -> dict:
    out = Counter()
    for e in decisions:
        st = states[max(e["t"] - 1, 0)]
        me = next((b for b in st["b"] if b[0] == e["bee"]), None)
        if me is None:
            out["no_position"] += 1
            continue
        pos = (me[1], me[2])
        seen = [(h[1], h[2]) for h in st["h"] if max(abs(h[1] - pos[0]), abs(h[2] - pos[1])) <= VISION]
        out[move_kind(e, pos, min(seen, key=lambda h: math.dist(h, pos)) if seen else None)] += 1
    n = sum(out.values())
    return {"n": n, "kinds": dict(sorted(out.items())),
            "away_share": round(out["away"] / n, 4) if n else None,
            "away_or_zone_O_share": round((out["away"] + out["zone_O"]) / n, 4) if n else None}


def report(d: Path, until: int = 10**9) -> dict:
    events = [json.loads(line) for line in (d / "events.jsonl").read_text().splitlines()]
    with gzip.open(d / "state.jsonl.gz", "rt") as f:
        states = [json.loads(line) for line in f]
    stung: dict[int, int] = {}
    for e in events:
        if e["kind"] == "sting":
            stung.setdefault(e["bee"], e["t"])
    decisions = [e for e in events if e["kind"] == "decision" and e["t"] < min(stung.get(e["bee"], 10**9), until)]
    first: dict[int, dict] = {}
    for e in decisions:
        if e["trigger"] == "hornet":
            first.setdefault(e["bee"], e)
    routine = [e for e in decisions if e["trigger"] == "timer" and e.get("ctx", {}).get("movers", 0) > 0]
    vocab = json.loads((d / "record.json").read_text())["params"].get("vocab", "neutral")
    return {"run": str(d), "vocab": vocab, "until": until if until < 10**9 else None, "first_sighting_before_any_sting": classify(list(first.values()), states),
            "first_sighting_intents": dict(Counter(e["intent"] for e in first.values())),
            "timer_with_hornet_in_view_before_any_sting": classify(routine, states)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("run_dirs", nargs="+", type=Path)
    ap.add_argument("--until", type=int, default=10**9)
    a = ap.parse_args()
    print(json.dumps([report(d, a.until) for d in a.run_dirs], indent=1))
