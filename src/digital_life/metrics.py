"""Per-season measures and the run summary (field meanings in docs/BUILD_NOTES.md, "metrics.jsonl")."""
from __future__ import annotations

import statistics

from .world import SEASONS


def _ratio(a, b):
    return round(a / b, 4) if b else None


class SeasonMetrics:
    def __init__(self):
        self.rows: list[dict] = []
        self.start(0, 0, 0)

    def start(self, t: int, season: int, year: int) -> None:
        self.t0, self.season, self.year = t, season, year
        self.trips = self.trips_ended = self.trips_delivered = self.deliveries = self.stings = self.hatches = self.queen_hatches = self.deaths = 0
        self.sounds = {"sound-1": 0, "sound-2": 0}
        self.damage, self.to_bloom, self.sizes = 0.0, [], []
        self.first_delivery = None

    def delivery(self, t: int) -> None:
        self.deliveries += 1
        if self.first_delivery is None:
            self.first_delivery = t - self.t0

    def sting(self, amount: float) -> None:
        self.stings += 1
        self.damage += amount

    def end(self, t: int, hornets) -> dict:
        genes = [h.genes for h in hornets]
        mean = lambda i: round(statistics.fmean(g[i] for g in genes), 3) if genes else None  # noqa: E731
        row = {
            "step": t, "year": self.year, "season": SEASONS[self.season],
            "trips": self.trips, "trips_ended": self.trips_ended, "trips_delivered": self.trips_delivered,
            "deliveries": self.deliveries, "delivery_rate": _ratio(self.trips_delivered, self.trips_ended),
            "stings": self.stings, "stings_per_trip": _ratio(self.stings, self.trips_ended),
            "median_to_bloom": statistics.median(self.to_bloom) if self.to_bloom else None,
            "first_delivery": self.first_delivery,
            "bees_end": self.sizes[-1] if self.sizes else 0,
            "bees_mean": round(statistics.fmean(self.sizes), 3) if self.sizes else 0,
            "hatches": self.hatches, "queen_hatches": self.queen_hatches, "deaths": self.deaths,
            "sounds_1": self.sounds["sound-1"], "sounds_2": self.sounds["sound-2"],
            "hornets": len(genes), "smell": mean(0), "hearing": mean(1), "ambush": mean(2),
            "hornet_damage": round(self.damage, 1),
        }
        self.rows.append(row)
        return row


def summarise(rows: list[dict], world, extra: dict | None = None) -> dict:
    """Flat numeric run summary for experiments/run.py (null values are left out)."""
    s: dict = {}
    tot = lambda k, rs: sum(r[k] for r in rs)  # noqa: E731
    s["trips"], s["deliveries"], s["stings"] = tot("trips", rows), tot("deliveries", rows), tot("stings", rows)
    ended = tot("trips_ended", rows)
    s["delivery_rate"], s["stings_per_trip"] = _ratio(tot("trips_delivered", rows), ended), _ratio(s["stings"], ended)
    for name in SEASONS[:3]:
        rs = [r for r in rows if r["season"] == name]
        s[f"{name}_trips"], s[f"{name}_deliveries"] = tot("trips_ended", rs), tot("deliveries", rs)
        s[f"{name}_rate"] = _ratio(tot("trips_delivered", rs), s[f"{name}_trips"])
        s[f"{name}_stings_per_trip"] = _ratio(tot("stings", rs), s[f"{name}_trips"])
    for r in rows:
        if r["season"] == "spring" and r["first_delivery"] is not None:
            s[f"first_delivery_y{r['year'] + 1}_spring"] = r["first_delivery"]
    meds = [r["median_to_bloom"] for r in rows if r["median_to_bloom"] is not None]
    s["median_to_bloom"] = statistics.median(meds) if meds else None
    s["hatches"], s["queen_hatches"], s["deaths"] = tot("hatches", rows), tot("queen_hatches", rows), tot("deaths", rows)
    s["bees_mean"] = round(statistics.fmean(r["bees_mean"] for r in rows), 3) if rows else 0
    s["bees_final"] = rows[-1]["bees_end"] if rows else 0
    last = [r for r in rows if r["hornets"]]
    if last:
        for g in ("smell", "hearing", "ambush"):
            s[f"{g}_first"], s[f"{g}_last"] = last[0][g], last[-1][g]
    for name, d in world.bloom_distance.items():
        s[f"bloom_distance_{name}"] = d
    s.update(extra or {})
    return {k: v for k, v in s.items() if v is not None}
