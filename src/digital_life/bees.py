"""Bees: state, the life rules (drain, sting, heal, delivery) and the senses.

`sense` is the only place a bee looks at the World. It writes what the bee perceives into the bee's own
state (known map, sightings, sounds). `perceive` then builds the Perception from that state alone.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from .motor import KHIVE, KOPEN, KWALL, KnownMap, MotorState
from .perception import Decision, Perception, direction_of, distance_band
from .world import ENTRANCE, HIVE, WALL, World

VISION, BLOOM_VISION, HEARING = 4, 6, 10


@dataclass
class Bee:
    id: int
    x: int
    y: int
    life: float
    born: int
    km: KnownMap
    carrying: bool = False
    stunned: int = 0
    stung_loss: float = 0.0
    healed: bool = False
    hold: int = 3                       # newborns stay inside for their first ticks
    decision: Decision = field(default_factory=Decision)
    labelled: str = ""                  # intent label for the log; "" before the first decision
    motor: MotorState = field(default_factory=MotorState)
    motor_status: str = "idle"
    last_decided: int = -10**6
    triggers: list = field(default_factory=list)
    recent: deque = field(default_factory=lambda: deque(maxlen=8))
    unseen: list = field(default_factory=list)
    heard: deque = field(default_factory=lambda: deque(maxlen=6))
    bloom_mem: dict = field(default_factory=dict)
    hornet_mem: deque = field(default_factory=lambda: deque(maxlen=6))
    bees_seen: list = field(default_factory=list)
    hornets_seen: list = field(default_factory=list)
    hornet_ids_seen: set = field(default_factory=set)
    bloom_seen: list = field(default_factory=list)
    sounds: list = field(default_factory=list)
    life_left_home: float | None = None
    trip: dict | None = None

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


def note(bee: Bee, t: int, kind: str, **data) -> None:
    """Record an event in the bee's own short-term memory."""
    e = {"t": t, "what": kind, **data}
    bee.recent.append(e)
    bee.unseen.append(e)


def drain(bee: Bee, winter: bool, in_hive: bool) -> None:
    bee.life -= (0.5 if in_hive else 2.0) if winter else 1.0


def sting(bee: Bee) -> int:
    """A sting takes half the bee's current life (rounded down) and stuns it for 2 ticks."""
    amount = int(bee.life // 2)
    bee.life -= amount
    bee.stung_loss += amount
    bee.stunned = 2
    return amount


def heal(bee: Bee, cap: float) -> float:
    """Once per life, a stung bee at home gets back half of what stings took."""
    if bee.healed or bee.stung_loss <= 0:
        return 0.0
    amount = min(bee.stung_loss / 2, cap - bee.life)
    bee.life += amount
    bee.healed = True
    return amount


def deliver(bee: Bee, cap: float) -> tuple[float, float] | None:
    """Carrying bloom into the hive doubles life, capped."""
    if not bee.carrying:
        return None
    before = bee.life
    bee.life = min(cap, 2 * bee.life)
    bee.carrying = False
    return before, bee.life


def sense(bee: Bee, world: World, t: int, others, hornets, bloom, sounds) -> None:
    """Update the bee's own state from what is in range. others: [(id, x, y)]; hornets: [(id, x, y)];
    bloom: this season's bloom cells; sounds: last tick's [(bee id, x, y, sound)]."""
    bx, by = bee.x, bee.y
    for y in range(by - VISION, by + VISION + 1):
        for x in range(bx - VISION, bx + VISION + 1):
            if 0 <= x < world.width and 0 <= y < world.height:
                c = world.grid[y * world.width + x]
                bee.km.learn(x, y, KWALL if c == WALL else KHIVE if c in (HIVE, ENTRANCE) else KOPEN)
    near = lambda x, y, r: abs(x - bx) <= r and abs(y - by) <= r  # noqa: E731
    bee.bees_seen = [(x, y) for i, x, y in others if i != bee.id and near(x, y, VISION)]
    seen = [(i, x, y) for i, x, y in hornets if near(x, y, VISION)]
    ids = {i for i, _, _ in seen}
    if ids - bee.hornet_ids_seen:
        bee.triggers.append("hornet")
        note(bee, t, "saw_mover", at=[[x, y] for _, x, y in seen])
    bee.hornet_ids_seen = ids
    bee.hornets_seen = [(x, y) for _, x, y in seen]
    for x, y in bee.hornets_seen:
        bee.hornet_mem.append((x, y, t))
    was = bool(bee.bloom_seen)
    bee.bloom_seen = [c for c in bloom if near(c[0], c[1], BLOOM_VISION)]
    for c in bee.bloom_seen:
        bee.bloom_mem[c] = t
    if bee.bloom_seen and not was:
        bee.triggers.append("bloom")
        note(bee, t, "saw_bright", at=list(bee.bloom_seen[4] if len(bee.bloom_seen) > 4 else bee.bloom_seen[0]))
    bee.sounds = []
    for i, x, y, s in sounds:
        d = math.dist((x, y), (bx, by))
        if i != bee.id and d <= HEARING:
            bee.sounds.append((s, direction_of(x - bx, y - by), distance_band(d)))
    if bee.sounds:
        bee.triggers.append("sound")
        note(bee, t, "heard", sounds=[list(s) for s in bee.sounds])


def view(bee: Bee) -> list[str]:
    km, rows = bee.km, []
    marks = {c: "*" for c in bee.bloom_seen}
    marks.update({c: "b" for c in bee.bees_seen})
    marks.update({c: "x" for c in bee.hornets_seen})
    marks[bee.pos] = "@"
    for y in range(bee.y - VISION, bee.y + VISION + 1):
        row = []
        for x in range(bee.x - VISION, bee.x + VISION + 1):
            k = km.get(x, y) if 0 <= x < km.w and 0 <= y < km.h else None
            row.append(marks.get((x, y)) or (" " if k is None else "#" if k == KWALL else "H" if k == KHIVE else "."))
        rows.append("".join(row))
    return rows


def perceive(bee: Bee, t: int, trigger: str) -> Perception:
    """Everything the bee's mind gets, built only from the bee's own state."""
    ago = lambda e: {**{k: v for k, v in e.items() if k != "t"}, "ago": t - e["t"]}  # noqa: E731
    return Perception(
        bee_id=bee.id, trigger=trigger, position=bee.pos, home=bee.km.home, life=round(bee.life, 1),
        carrying=bee.carrying, at_home=bee.km.get(*bee.pos) == KHIVE, stunned=bee.stunned,
        grid_size=(bee.km.w, bee.km.h), view=view(bee), bees_seen=list(bee.bees_seen),
        hornets_seen=list(bee.hornets_seen), bloom_seen=list(bee.bloom_seen), sounds=list(bee.sounds),
        recent_events=[ago(e) for e in bee.recent], new_events=[ago(e) for e in bee.unseen],
        heard_at_home=[(t - ht, who, text) for ht, who, text in bee.heard],
        bloom_remembered=sorted((x, y, t - st) for (x, y), st in bee.bloom_mem.items()),
        hornets_remembered=[(x, y, t - st) for x, y, st in bee.hornet_mem],
        explored=bee.km.explored(), intent=bee.labelled, motor_status=bee.motor_status,
        life_when_left_home=bee.life_left_home)
