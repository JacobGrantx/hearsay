"""What a bee's mind gets (Perception) and what it gives back (Decision).

A policy, scripted or AI, sees only a Perception. It is built from that bee's own senses and its own
known map, never from the World, so nothing in it can reveal a bloom cell or a hornet the bee has not
perceived. Phase 2 renders Perception to prompt text; the field names here never reach a prompt.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

DIRECTIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
DIR_VEC = {"N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1), "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1)}
INTENTS = ("explore", "go_to", "go_home", "flee", "wait")
SOUNDS = ("none", "sound-1", "sound-2")
TRIGGERS = ("timer", "stung", "hornet", "bloom", "sound", "arrived", "home", "life50", "life25", "hatched")


def direction_of(dx: float, dy: float) -> str:
    """8-way compass direction of a vector (y grows southward)."""
    if dx == 0 and dy == 0:
        return "here"
    angle = math.degrees(math.atan2(dx, -dy)) % 360  # 0 = north, clockwise
    return DIRECTIONS[int((angle + 22.5) // 45) % 8]


def distance_band(d: float) -> str:
    return "near" if d <= 3 else "mid" if d <= 6 else "far"


@dataclass
class Decision:
    intent: str = "wait"
    direction: str | None = None          # for explore
    target: tuple[int, int] | None = None  # for go_to
    sound: str = "none"
    remember: str = ""
    say: str = ""

    def __post_init__(self):
        if self.intent not in INTENTS:
            self.intent = "wait"
        if self.intent == "explore" and self.direction not in DIRECTIONS:
            self.direction = "E"
        if self.intent == "go_to" and self.target is None:
            self.intent = "wait"
        if self.sound not in SOUNDS:
            self.sound = "none"
        self.say = " ".join(str(self.say or "").split()[:30])
        self.remember = str(self.remember or "")[:200]

    def label(self) -> str:
        if self.intent == "explore":
            return f"explore:{self.direction}"
        if self.intent == "go_to":
            return f"go_to:{self.target[0]},{self.target[1]}"
        return self.intent


@dataclass
class Perception:
    bee_id: int
    trigger: str
    position: tuple[int, int]
    home: tuple[int, int]
    life: float
    carrying: bool
    at_home: bool
    stunned: int
    grid_size: tuple[int, int]
    view: list[str]                                  # 9 rows of 9 symbols centred on the bee (see VIEW_SYMBOLS)
    bees_seen: list[tuple[int, int]]                 # other bees in view, absolute cells
    hornets_seen: list[tuple[int, int]]              # hornets in view, absolute cells
    bloom_seen: list[tuple[int, int]]                # bloom cells within bloom vision, absolute cells
    sounds: list[tuple[str, str, str]]               # (sound, direction, band) heard this tick
    recent_events: list[dict]                        # the bee's last 8 events, each with "ago" in ticks
    new_events: list[dict]                           # every event since the bee's previous decision
    heard_at_home: list[tuple[int, int, str]]        # (ago, speaker id, text), newest last
    bloom_remembered: list[tuple[int, int, int]]     # (x, y, ago) bloom cells this bee has seen before
    hornets_remembered: list[tuple[int, int, int]]   # (x, y, ago) where this bee has seen hornets
    explored: dict[str, float]                       # share of cells known, per direction from home
    intent: str                                      # current intent label
    motor_status: str                                # "moving", "arrived", "blocked" or "idle"
    life_when_left_home: float | None
    extra: dict = field(default_factory=dict)        # reserved for later phases


VIEW_SYMBOLS = {"#": "wall", ".": "open", "H": "home", "*": "bright", "b": "other", "x": "mover", "@": "self", " ": "outside"}
