"""Bee policies: what turns a Perception into a Decision.

The interface phase 2's AI mind implements:
    decide_many(perceptions) -> decisions   one call per tick with every bee that is due to decide
    bee_died(bee_id)                        optional clean-up
A policy never receives the World. The one exception is OraclePolicy, a calibration-only cheat that is
handed the current bloom cells at construction; it is never reported as a result.
"""
from __future__ import annotations

from .perception import DIRECTIONS, Decision, Perception


class Policy:
    name = "base"

    def decide(self, p: Perception) -> Decision:
        raise NotImplementedError

    def decide_many(self, perceptions: list[Perception]) -> list[Decision]:
        return [self.decide(p) for p in perceptions]

    def bee_died(self, bee_id: int) -> None:
        pass


class RandomPolicy(Policy):
    """Random intents and random sounds, with no use of what the bee perceives."""
    name = "random"

    def __init__(self, rng):
        self.rng = rng

    def decide(self, p: Perception) -> Decision:
        r = self.rng
        intent = ("explore", "go_to", "go_home", "flee", "wait")[r.randrange(5)]
        return Decision(intent=intent, direction=DIRECTIONS[r.randrange(8)],
                        target=(r.randrange(p.grid_size[0]), r.randrange(p.grid_size[1])),
                        sound=("none", "sound-1", "sound-2")[r.randrange(3)])


class RulePolicy(Policy):
    """Explore in a random direction, take bloom it sees, go home when carrying or at half the life it
    left home with. No sounds, no talk, no memory of bloom between trips."""
    name = "rule"

    def __init__(self, rng, return_fraction: float = 0.5):
        self.rng, self.return_fraction = rng, return_fraction
        self.heading: dict[int, str] = {}

    def decide(self, p: Perception) -> Decision:
        if p.carrying:
            return Decision("go_home")
        if not p.at_home and p.life_when_left_home and p.life <= self.return_fraction * p.life_when_left_home:
            return Decision("go_home")
        if p.bloom_seen:
            x, y = p.position
            return Decision("go_to", target=min(p.bloom_seen, key=lambda c: (abs(c[0] - x) + abs(c[1] - y), c)))
        h = self.heading.get(p.bee_id)
        if h is None or p.at_home or (p.trigger == "arrived" and p.motor_status in ("arrived", "blocked")):
            h = self.heading[p.bee_id] = DIRECTIONS[self.rng.randrange(8)]
        return Decision("explore", direction=h)

    def bee_died(self, bee_id: int) -> None:
        self.heading.pop(bee_id, None)


class OraclePolicy(Policy):
    """Calibration only: told where this season's bloom is. Goes there, carries home, waits out winter."""
    name = "oracle"

    def __init__(self, bloom_now):
        self.bloom_now = bloom_now

    def decide(self, p: Perception) -> Decision:
        if p.carrying:
            return Decision("go_home")
        cells = self.bloom_now()
        if not cells:
            return Decision("wait") if p.at_home else Decision("go_home")
        x, y = p.position
        return Decision("go_to", target=min(cells, key=lambda c: (abs(c[0] - x) + abs(c[1] - y), c)))


def make_policy(name: str, rng, *, bloom_now=None, params: dict | None = None) -> Policy:
    params = params or {}
    if name == "random":
        return RandomPolicy(rng)
    if name == "rule":
        return RulePolicy(rng, params.get("return_fraction", 0.5))
    if name == "oracle":
        return OraclePolicy(bloom_now)
    raise ValueError(f"unknown policy {name!r}")
