"""One AI bee's own memory, kept by the mind per bee id and lost when the bee dies.

- Short-term: the last 8 events. The sim keeps these and hands them over in Perception.recent_events.
- Episodes: everything that happened to the bee, each with a rule-based importance (IMPORTANCE).
- Beliefs: up to 12 short notes the bee wrote through `remember`; the oldest is evicted.
- Recall: the top 6 episodes by recency + importance + BM25 relevance to the present moment, leaving out
  episodes the prompt already shows as recent events or recent talk.
- Landmarks (home, bright spots and moving things seen, share explored per direction) come from the bee's
  own known map and sightings in the Perception, and are rendered in render.py.
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from .perception import Perception
from .render import DEFAULT, event_text
from .vocab import Vocab

IMPORTANCE = {"stung": 5, "delivered": 5, "saw_bright": 4, "picked_up": 4, "saw_mover": 3, "heard_home": 2, "heard": 1}
MAX_BELIEFS, RECALL_K, MAX_EPISODES = 12, 6, 300
RECENCY = 0.99  # recency weight is RECENCY ** ticks ago
REGION = 8      # cells per side of the coarse regions that make places searchable
COORDS = re.compile(r"\(?(\d{1,3}),\s*(\d{1,3})\)?")
WORDS = re.compile(r"[a-z0-9-]+")


@dataclass
class Episode:
    t: int
    kind: str
    text: str
    importance: int
    tokens: list


def region(c) -> str:
    return f"r{int(c[0]) // REGION}_{int(c[1]) // REGION}"


def event_tokens(e: dict) -> list[str]:
    toks = [e["what"]]
    at = e.get("at")
    if at:
        toks += [region(c) for c in (at if isinstance(at[0], list) else [at])]
    toks += [s for s, _, _ in e.get("sounds", [])]
    return toks


def text_tokens(text: str) -> list[str]:
    return WORDS.findall(text.lower()) + [region((int(x), int(y))) for x, y in COORDS.findall(text)]


class BeeMemory:
    def __init__(self, v: Vocab = DEFAULT):
        self.v = v  # the vocabulary episode text is written in
        self.episodes: list[Episode] = []
        self.beliefs: deque = deque(maxlen=MAX_BELIEFS)  # (tick written, text)
        self.heard_keys: set = set()

    def add(self, ep: Episode) -> None:
        self.episodes.append(ep)
        if len(self.episodes) > MAX_EPISODES:
            del self.episodes[0]

    def observe(self, p: Perception, tick: int, names) -> None:
        """Store what happened since the bee last decided, and new things heard at home."""
        for e in p.new_events:
            self.add(Episode(tick - e["ago"], e["what"], event_text(e, names, self.v), IMPORTANCE[e["what"]], event_tokens(e)))
        for ago, who, said in p.heard_at_home:
            key = (tick - ago, who, said)
            if key not in self.heard_keys:
                self.heard_keys.add(key)
                text = self.v.event["heard_home"].format(who=who, text=said)
                self.add(Episode(tick - ago, "heard_home", text, IMPORTANCE["heard_home"], ["heard_home", *text_tokens(said)]))

    def remember(self, tick: int, text: str) -> None:
        text = " ".join(str(text).split())
        if text:
            self.beliefs.append((tick, text))

    def notes(self, tick: int) -> list[str]:
        return [f"{text} ({tick - t} ago)" for t, text in self.beliefs]

    def query(self, p: Perception) -> list[str]:
        q = [p.trigger, region(p.position)]
        if p.bloom_seen:
            q += ["saw_bright", "picked_up", *{region(c) for c in p.bloom_seen}]
        if p.hornets_seen:
            q += ["saw_mover", "stung", *{region(c) for c in p.hornets_seen}]
        if p.carrying:
            q += ["delivered"]
        if p.at_home:
            q += ["heard_home"]
        q += [s for s, _, _ in p.sounds]
        return q

    def recall(self, p: Perception, tick: int, k: int = RECALL_K) -> list[tuple[int, str]]:
        """Top k episodes for this moment, oldest first, as (ticks ago, text)."""
        shown = {(tick - e["ago"], e["what"]) for e in p.recent_events}
        shown |= {(tick - a, "heard_home", self.v.event["heard_home"].format(who=w, text=s)) for a, w, s in p.heard_at_home}
        pool = [ep for ep in self.episodes if (ep.t, ep.kind) not in shown and (ep.t, ep.kind, ep.text) not in shown]
        if not pool:
            return []
        scores = BM25Okapi([ep.tokens for ep in pool]).get_scores(self.query(p))
        top = max(max(scores), 0.0)
        ranked = sorted(
            range(len(pool)),
            key=lambda i: (-(RECENCY ** (tick - pool[i].t) + pool[i].importance / 5 + (max(scores[i], 0.0) / top if top > 0 else 0.0)), -pool[i].t, i))
        chosen = sorted(ranked[:k], key=lambda i: (pool[i].t, i))
        return [(tick - pool[i].t, pool[i].text) for i in chosen]
