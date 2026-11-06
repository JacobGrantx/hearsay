"""Per-run measures, each as pre-registered in EXPERIMENTS.md ("Pre-registration"). One function per measure.

Each function takes one Run (runs.py) and returns plain numbers or dicts; None means no data (missing).
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter

from runs import SEASONS, Run

HORNET_SEASONS = ("spring", "summer", "autumn")
COORD = re.compile(r"\(\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)")  # "(27,17)", the form the perception text uses


def season_rows(run: Run) -> list[dict]:
    return sorted(run.metrics, key=lambda r: r["step"])


# ---------- E1 ----------

def deliveries_by_season(run: Run) -> list[int]:
    return [r["deliveries"] for r in season_rows(run)]


# ---------- E2 ----------

def stings_per_trip_by_year(run: Run) -> dict[int, float | None]:
    out = {}
    for year in (0, 1):
        rows = [r for r in run.metrics if r["year"] == year and r["season"] in HORNET_SEASONS]
        ended = sum(r["trips_ended"] for r in rows)
        out[year] = sum(r["stings"] for r in rows) / ended if ended else None
    return out


def sting_change(run: Run) -> float | None:
    y = stings_per_trip_by_year(run)
    return y[1] - y[0] if y[0] is not None and y[1] is not None else None


def gene_means(run: Run) -> list[dict]:
    """Hornet gene means at the end of each season with hornets."""
    return [{"year": r["year"], "season": r["season"], **{g: r[g] for g in ("smell", "hearing", "ambush")}}
            for r in season_rows(run) if r["season"] in HORNET_SEASONS and r.get("smell") is not None]


def damage_per_bee_tick_outside(run: Run) -> dict[int, float | None]:
    """Life removed by stings / bee-ticks spent outside the hive, over the seasons with hornets, per year."""
    outside = Counter()
    for st in run.states:
        if st["s"] != 3:
            outside[st["y"]] += sum(1 for b in st["b"] if (b[1], b[2]) not in run.hive)
    damage = Counter()
    for r in run.metrics:
        if r["season"] in HORNET_SEASONS:
            damage[r["year"]] += r["hornet_damage"]
    return {y: (damage[y] / outside[y] if outside[y] else None) for y in (0, 1)}


# ---------- E3 ----------

def first_spring_delivery(run: Run, year: int) -> int:
    """Ticks after the spring's start of its first delivery, censored at the season length."""
    row = next(r for r in run.metrics if r["year"] == year and r["season"] == "spring")
    return row["first_delivery"] if row["first_delivery"] is not None else run.layout["season_length"]


def spring_gain(run: Run) -> int:
    return first_spring_delivery(run, 0) - first_spring_delivery(run, 1)


def carryover(run: Run) -> dict:
    """Separates culture from individual memory: did any bee live through both springs, and had the
    first year-2 spring forager heard a coordinate near the spring bloom at home before it left?"""
    L = run.layout["season_length"]
    y2 = run.layout["season_length"] * 4
    alive_y1_spring = {b[0] for st in run.states[:L] for b in st["b"]}
    alive_y2_start = {b[0] for b in run.states[y2]["b"]} if len(run.states) > y2 else set()
    out = {"bees_alive_both_springs": sorted(alive_y1_spring & alive_y2_start), "forager": None,
           "forager_alive_y1_spring": None, "forager_heard_bloom_coord": None}
    first = next((e for e in run.of("delivery") if y2 <= e["t"] < y2 + L), None)
    if first is None:
        return out
    bee = first["bee"]
    trip = next((e for e in run.of("trip") if e["bee"] == bee and e["delivered"]
                 and e["start"] <= first["t"] <= e["start"] + e["ticks"]), None)
    left = trip["start"] if trip else first["t"]
    bloom = run.layout["bloom"]["spring"]
    heard = [e for e in run.of("say") if bee in e.get("heard_by", []) and e["t"] < left]
    near = any(max(abs(int(x) - bx), abs(int(y) - by)) <= 3
               for e in heard for x, y in COORD.findall(e["text"]) for bx, by in bloom)
    out.update(forager=bee, forager_left=left, forager_alive_y1_spring=bee in alive_y1_spring,
               forager_heard_bloom_coord=near)
    return out


# ---------- E4 ----------

def context(ctx: dict) -> str:
    m, b = ctx.get("movers", 0) > 0, ctx.get("bright", 0) > 0
    return "both" if m and b else "movers" if m else "bright" if b else "neither"


def sound_decisions(run: Run, t0: int = 0, t1: int = 10**9) -> list[tuple[str, str]]:
    return [(e["sound"], context(e.get("ctx", {}))) for e in run.of("decision")
            if e.get("sound") not in (None, "none") and t0 <= e["t"] < t1 and "ctx" in e]


def mutual_information(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    joint, a, b = Counter(pairs), Counter(p[0] for p in pairs), Counter(p[1] for p in pairs)
    return sum(c / n * math.log2(c * n / (a[x] * b[y])) for (x, y), c in joint.items())


def mi_test(pairs: list[tuple[str, str]], permutations: int = 1000, seed: int = 0) -> dict:
    """MI between sound and context, with a within-run permutation test on the sound labels."""
    sounds = Counter(p[0] for p in pairs)
    out = {"n_sounds": len(pairs), "by_sound": dict(sounds), "by_context": {f"{s}|{c}": n for (s, c), n in sorted(Counter(pairs).items())}}
    if len(pairs) < 2:
        return {**out, "mi": None, "note": "missing: fewer than 2 sounds"}
    mi = mutual_information(pairs)
    rng = random.Random(seed)
    labels, ctxs = [p[0] for p in pairs], [p[1] for p in pairs]
    null = []
    for _ in range(permutations):
        rng.shuffle(labels)
        null.append(mutual_information(list(zip(labels, ctxs))))
    null.sort()
    p95 = null[int(0.95 * permutations) - 1]
    return {**out, "mi": round(mi, 4), "perm_p95": round(p95, 4),
            "perm_p": round(sum(v >= mi for v in null) / permutations, 4),
            "above_p95": mi > p95,
            "note": "degenerate: one sound or one context only, so MI is 0" if len(sounds) < 2 or len(set(ctxs)) < 2 else ""}


def listener_response(run: Run) -> dict:
    """Share of flee or go_home at decisions triggered by hearing a sound, against timer decisions."""
    def share(evs):
        return {"n": len(evs), "flee_or_home": round(sum(e["intent"] in ("flee", "go_home") for e in evs) / len(evs), 4) if evs else None}
    decisions = run.of("decision")
    return {"sound": share([e for e in decisions if e["trigger"] == "sound"]),
            "timer": share([e for e in decisions if e["trigger"] == "timer"])}


# ---------- Further measures ----------

def talk_claims(run: Run) -> Counter:
    """Every coordinate pair in hive talk: near a bloom cell of the current or previous season,
    near a moving thing the speaker had in view before, or neither (unsupported)."""
    L, vision = run.layout["season_length"], run.layout["vision"]
    seen: dict[int, dict[tuple[int, int], int]] = {}
    for st in run.states:
        for b in st["b"]:
            for h in st["h"]:
                if max(abs(h[1] - b[1]), abs(h[2] - b[2])) <= vision:
                    seen.setdefault(b[0], {}).setdefault((h[1], h[2]), st["t"])
    out = Counter()
    for e in run.of("say"):
        s = (e["t"] // L) % 4
        cells = [c for name in (SEASONS[s], SEASONS[(s - 1) % 4]) for c in run.layout["bloom"].get(name, [])]
        mine = seen.get(e["bee"], {})
        for x, y in COORD.findall(e["text"]):
            x, y = int(x), int(y)
            if any(max(abs(x - bx), abs(y - by)) <= 3 for bx, by in cells):
                out["bloom"] += 1
            elif any(mine.get((x + dx, y + dy), 10**9) < e["t"] for dx in range(-3, 4) for dy in range(-3, 4)):
                out["mover"] += 1
            else:
                out["neither"] += 1
    return out


def naive_avoidance(run: Run) -> dict:
    """Each bee's first decision triggered by seeing a moving thing, before it was ever stung."""
    stung = {}
    for e in run.of("sting"):
        stung.setdefault(e["bee"], e["t"])
    first = {}
    for e in run.of("decision"):
        if e["trigger"] == "hornet" and e["bee"] not in first:
            first[e["bee"]] = e
    naive = [e for b, e in first.items() if e["t"] < stung.get(b, 10**9)]
    n = len(naive)
    return {"n": n, "flee_or_home": round(sum(e["intent"] in ("flee", "go_home") for e in naive) / n, 4) if n else None}


def mind_health(run: Run) -> dict:
    decisions = run.of("decision")
    errors = run.of("mind_error")
    fallbacks = sum(1 for e in decisions if e.get("fallback"))
    n = len(decisions)
    return {"decisions": n, "mind_errors": len(errors), "fallbacks": fallbacks,
            "fallback_share": round(fallbacks / n, 4) if n else None, "flagged": bool(n and fallbacks / n > 0.05),
            "input_tokens": sum(e.get("usage", {}).get("input_tokens", 0) for e in decisions),
            "output_tokens": sum(e.get("usage", {}).get("output_tokens", 0) for e in decisions)}
