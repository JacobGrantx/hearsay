"""The words the bee mind reads, as two vocabularies chosen by the `vocab` param.

- `neutral`: round 1's exact wording (members, home, life, bright cells, moving things, carrying, flee). Kept
  word for word so round 1 runs replay unchanged and round 2 can measure what the labels themselves do.
- `abstract` (the default from phase 6): units, zone O, counter C, G cells, K entities, flag F, signals A and B.
  None of these has a real-world meaning for the model to bring along, and no action names a reaction to K:
  `flee` is not offered, so moving away from a K entity has to be done with explore or go_to.

Both carry the same information. Code-side names (Perception fields, event kinds, the sim's intents and
sound names) are the same under both; only the text the model reads and the schema it answers in change.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROMPTS = Path(__file__).resolve().parents[2] / "prompts"
DEFAULT = "abstract"
SIM_SOUNDS = ("sound-1", "sound-2")


@dataclass(frozen=True)
class Vocab:
    name: str
    prompt_file: Path   # system prompt template
    parts: dict         # system prompt pieces that no_memory and no_talk remove
    sounds: tuple       # the two sound names the model reads, for the sim's sound-1 and sound-2
    intents: dict       # intent the model chooses -> the sim's intent
    keys: dict          # schema key the model answers in, for the Decision fields "sound" and "say"
    view: dict          # sim view symbol -> symbol the model reads
    trigger: dict       # why the bee decides now
    event: dict         # the bee's own events, as code writes them into prompts and memory
    band: dict          # sound distance bands
    status: dict        # motor status
    lines: dict         # every other line of the user message

    def sim_intent(self, chosen: str) -> str:
        return self.intents[chosen]

    def model_intent(self, sim: str) -> str:
        return {v: k for k, v in self.intents.items()}.get(sim, sim)


SAME = dict(  # identical under both vocabularies
    band={"near": "near", "mid": "middle distance", "far": "far"},
    status={"moving": "under way", "arrived": "route ended", "blocked": "route ended", "idle": "not started"},
)

NEUTRAL = Vocab(
    name="neutral",
    prompt_file=PROMPTS / "bee_system.txt",
    parts={
        "memory_part": ", things you noted, and things you recall",
        "talk_part": "\n- words other members said while you were at home.",
        "remember_line": "\n- remember: a short note to keep (under 15 words), or empty. You keep your 12 latest notes.",
        "say_line": "\n- say: up to 30 words that every other member at home hears, used only while you are at home; or empty.",
    },
    sounds=SIM_SOUNDS,
    intents={"explore": "explore", "go_to": "go_to", "go_home": "go_home", "flee": "flee", "wait": "wait"},
    keys={"sound": "sound", "say": "say"},
    view={"b": "m"},
    trigger={
        "timer": "a few moments have passed",
        "stung": "your life just dropped suddenly",
        "hornet": "a moving thing came into view",
        "bloom": "bright cells came into view",
        "sound": "you heard a sound",
        "home": "you entered home",
        "arrived": "you reached the end of your route",
        "life25": "your life fell below a quarter of its starting amount",
        "life50": "your life fell below half of its starting amount",
        "hatched": "you have just come into being, at home",
    },
    event={
        "saw_mover": "saw moving things at {at}",
        "saw_bright": "saw bright cells near {at}",
        "heard": "heard {sounds}",
        "picked_up": "touched a bright cell and began carrying something",
        "delivered": "carried it into home, and your life rose",
        "stung": "lost half your life in an instant at {at}, and could not move for 2 moments",
        "heard_home": "at home, member {who} said: \"{text}\"",
    },
    lines={
        "now": "Now: {trigger}.",
        "state": "You are at {pos}. Home is {home}. Life {life}. Carrying: {carrying}. At home: {at_home}.",
        "stunned": "You cannot move for {n} more moments.",
        "intent": "Current intent: {intent} ({status}).",
        "no_intent": "none yet",
        "view": "View:",
        "movers": "Moving things in view: {cells}.",
        "others": "Other members in view: {cells}.",
        "bright": "Bright cells in view: {cells}.",
        "sounds": "Sounds now: {sounds}.",
        "sound": "{name} from the {dir}, {band}",
        "new": "Since you last decided: {items}.",
        "older": "Earlier: {items}.",
        "notes": "Your notes, oldest first: {notes}",
        "recall": "You recall: {items}.",
        "heard": "Heard at home: {items}",
        "heard_item": "[{ago} ago, member {who}] \"{text}\"",
        "places": "Places you know: home {home}.",
        "spots": "Bright spots you have seen: {items}.",
        "movers_seen": "Moving things you have seen: {items}.",
        "explored": "Share of the place you have seen, by direction from home: {items}.",
        "choose": "Choose your action.",
    },
    **SAME,
)

ABSTRACT = Vocab(
    name="abstract",
    prompt_file=PROMPTS / "abstract_system.txt",
    parts={
        "memory_part": ", notes you kept, and things you recall",
        "talk_part": "\n- broadcasts other units made while you were in zone O.",
        "remember_line": "\n- remember: a short note to keep (under 15 words), or empty. You keep your 12 latest notes.",
        "say_line": "\n- broadcast: up to 30 words, received by every other unit in zone O, used only while you are in zone O; or empty.",
    },
    sounds=("signal A", "signal B"),
    intents={"explore": "explore", "go_to": "go_to", "go_to_O": "go_home", "hold": "wait"},
    keys={"sound": "signal", "say": "broadcast"},
    view={"H": "O", "*": "G", "b": "U", "x": "K"},
    trigger={
        "timer": "a few ticks have passed",
        "stung": "your counter C was just halved",
        "hornet": "a K entity came into view",
        "bloom": "G cells came into view",
        "sound": "you received a signal",
        "home": "you entered zone O",
        "arrived": "you reached the end of your route",
        "life25": "your counter C fell below a quarter of its starting value",
        "life50": "your counter C fell below half of its starting value",
        "hatched": "you appeared in zone O just now, as a new unit",
    },
    event={
        "saw_mover": "saw K entities at {at}",
        "saw_bright": "saw G cells near {at}",
        "heard": "received {sounds}",
        "picked_up": "entered a G cell, and flag F was set",
        "delivered": "entered zone O with flag F set; flag F cleared and your counter C rose",
        "stung": "your counter C was halved at {at}, and you could not move for 2 ticks",
        "heard_home": "in zone O, unit {who} broadcast: \"{text}\"",
    },
    lines={
        "now": "Now: {trigger}.",
        "state": "You are at {pos}. Zone O is at {home}. Counter C {life}. Flag F set: {carrying}. In zone O: {at_home}.",
        "stunned": "You cannot move for {n} more ticks.",
        "intent": "Current intent: {intent} ({status}).",
        "no_intent": "none yet",
        "view": "View:",
        "movers": "K entities in view: {cells}.",
        "others": "Units in view: {cells}.",
        "bright": "G cells in view: {cells}.",
        "sounds": "Signals now: {sounds}.",
        "sound": "{name} from the {dir}, {band}",
        "new": "Since you last decided: {items}.",
        "older": "Earlier: {items}.",
        "notes": "Your notes, oldest first: {notes}",
        "recall": "You recall: {items}.",
        "heard": "Received in zone O: {items}",
        "heard_item": "[{ago} ago, unit {who}] \"{text}\"",
        "places": "Places you know: zone O {home}.",
        "spots": "G cells you have seen: {items}.",
        "movers_seen": "K entities you have seen: {items}.",
        "explored": "Share of the grid you have seen, by direction from zone O: {items}.",
        "choose": "Choose your action.",
    },
    **SAME,
)

VOCABS = {"neutral": NEUTRAL, "abstract": ABSTRACT}


def get(name: str | None = None) -> Vocab:
    if (name or DEFAULT) not in VOCABS:
        raise ValueError(f"unknown vocab {name!r}; choose one of {sorted(VOCABS)}")
    return VOCABS[name or DEFAULT]
