"""Writes a run directory in the format documented in docs/BUILD_NOTES.md ("Log format")."""
from __future__ import annotations

import gzip
import io
import json

FORMAT = 1
BEE_FIELDS = ["id", "x", "y", "life", "carrying", "stunned", "intent"]
HORNET_FIELDS = ["id", "x", "y", "smell", "hearing", "ambush", "target", "mode"]
SOUND_FIELDS = ["bee", "x", "y", "sound"]


class SimLog:
    """Wraps a RunLog. With log=None every call is a no-op, so tests can run the sim without files."""

    def __init__(self, log, *, state: bool = True, decisions: bool = True):
        self.log, self.decisions = log, decisions
        # mtime=0: gzip otherwise stamps the write time into byte 4 of the header, so two identical runs
        # would differ byte for byte whenever they finish in different seconds.
        self._state = (io.TextIOWrapper(gzip.GzipFile(str(log.path("state.jsonl.gz")), mode="wb", mtime=0, compresslevel=6),
                                        encoding="utf-8")
                       if (log and state) else None)

    def layout(self, world, cal, p: dict, seed: int, vision: tuple[int, int, int]) -> None:
        if not self.log:
            return
        doc = {
            "format": FORMAT, "width": world.width, "height": world.height, "rows": world.rows(),
            "home": list(world.home), "entrances": [list(e) for e in world.entrances],
            "bloom": {s: [list(c) for c in cs] for s, cs in world.bloom.items()},
            "bloom_distance": world.bloom_distance,
            "season_names": ["spring", "summer", "autumn", "winter"],
            "season_length": cal.season_length, "years": cal.years, "ticks": cal.ticks,
            "base_life": p["base_life"], "life_cap": p["base_life"] * p["life_cap_factor"], "max_bees": p["max_bees"],
            "vision": vision[0], "bloom_vision": vision[1], "hearing": vision[2],
            "condition": p["condition"], "seed": seed,
            "bee_fields": BEE_FIELDS, "hornet_fields": HORNET_FIELDS, "sound_fields": SOUND_FIELDS,
        }
        self.log.path("layout.json").write_text(json.dumps(doc, separators=(",", ":")) + "\n")

    def event(self, kind: str, t: int, **data) -> None:
        if self.log and (self.decisions or kind != "decision"):
            self.log.event(kind, t=t, **data)

    def metric(self, row: dict) -> None:
        if self.log:
            self.log.metric(**row)

    def state(self, t: int, season: int, year: int, bees, hornets, sounds) -> None:
        if not self._state:
            return
        line = {
            "t": t, "s": season, "y": year,
            "b": [[b.id, b.x, b.y, round(b.life, 1), int(b.carrying), b.stunned, b.labelled] for b in bees],
            "h": [[h.id, h.x, h.y, *h.genes, h.target, h.mode] for h in hornets],
            "snd": [list(s) for s in sounds],
        }
        self._state.write(json.dumps(line, separators=(",", ":")) + "\n")

    def close(self) -> None:
        if self._state:
            self._state.close()
