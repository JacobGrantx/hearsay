"""The bee mind's words: the system prompt, Perception rendered as text, the decision schema and the parser.

Every piece of fixed text a prompt can contain comes from the chosen vocabulary (vocab.py) and its prompt
template, so the no-hints tests (tests/test_mind_prompt.py, tests/test_vocab.py) can check all of it for words
that would tell the model what the world is. Under `neutral` the model gets a grid, a home, bright cells, moving
things, two sounds and a life number; under `abstract` (the default) zone O, G cells, K entities, two signals and
a counter C. It never hears bee, hive, bloom, hornet, season, food, danger and the like.
"""
from __future__ import annotations

import json

from . import vocab as vocabs
from .perception import DIRECTIONS, Decision, Perception
from .vocab import SIM_SOUNDS, Vocab

LABELLED_SOUNDS = ("good noise", "bad noise")  # only under labels_good_bad
DEFAULT = vocabs.get()


def sound_names(condition: str, v: Vocab = DEFAULT) -> tuple[str, str]:
    return LABELLED_SOUNDS if condition == "labels_good_bad" else v.sounds


# Round 2 arm A (`tell_reward`): the one fact the abstract prompt otherwise leaves for the units to discover.
REWARD_TOLD = " Entering zone O with flag F set raises counter C."


def system_prompt(condition: str, width: int, height: int, v: Vocab = DEFAULT, tell_reward: bool = False) -> str:
    s1, s2 = sound_names(condition, v)
    memory, talk = condition != "no_memory", condition != "no_talk"
    if tell_reward and "{reward_part}" not in v.prompt_file.read_text():
        raise ValueError(f"tell_reward needs a prompt with a reward part; vocab {v.name} has none")
    return v.prompt_file.read_text().format(
        width=width, height=height, sound_1=s1, sound_2=s2, reward_part=REWARD_TOLD if tell_reward else "",
        memory_part=v.parts["memory_part"] if memory else "",
        talk_part=v.parts["talk_part"] if talk else "",
        remember_line=v.parts["remember_line"] if memory else "",
        say_line=v.parts["say_line"] if talk else "").strip()


def xy(c) -> str:
    return f"({c[0]}, {c[1]})"


def sounds_text(sounds, names: tuple[str, str], v: Vocab) -> str:
    return "; ".join(v.lines["sound"].format(name=sound_label(s, names), dir=d, band=v.band[b]) for s, d, b in sounds)


def event_text(e: dict, names: tuple[str, str], v: Vocab = DEFAULT) -> str:
    what = e["what"]
    if what == "heard":
        return v.event["heard"].format(sounds=sounds_text(e["sounds"], names, v))
    at = e.get("at")
    if at and isinstance(at[0], list):
        at = ", ".join(xy(c) for c in at)
    elif at:
        at = xy(at)
    return v.event[what].format(at=at)


def sound_label(sound: str, names: tuple[str, str]) -> str:
    return names[SIM_SOUNDS.index(sound)] if sound in SIM_SOUNDS else sound


def intent_text(label: str, v: Vocab = DEFAULT) -> str:
    if not label:
        return v.lines["no_intent"]
    if label.startswith("go_to:"):
        return f"go_to ({label[6:].replace(',', ', ')})"
    kind, _, arg = label.partition(":")
    return f"{v.model_intent(kind)} {arg}" if arg else v.model_intent(kind)


def clusters(cells: list[tuple[int, int, int]]) -> list[tuple[tuple[int, int], int]]:
    """Group remembered bright cells into spots: (a central cell, ticks since last seen)."""
    groups: list[list[tuple[int, int, int]]] = []
    for c in sorted(cells):
        for g in groups:
            if max(abs(c[0] - g[0][0]), abs(c[1] - g[0][1])) <= 2:
                g.append(c)
                break
        else:
            groups.append([c])
    out = []
    for g in groups:
        g.sort()
        mid = g[len(g) // 2]
        out.append(((mid[0], mid[1]), min(a for _, _, a in g)))
    return out


def render(p: Perception, names: tuple[str, str], v: Vocab = DEFAULT, *, memory: bool, talk: bool, notes=(), recalled=(),
           since: int = 5) -> str:
    """The user message for one decision. Under no_memory (memory=False) only the present is shown:
    what happened and what was said at home since the bee last decided, plus where home is."""
    yn = lambda b: "yes" if b else "no"  # noqa: E731
    cells = lambda cs: ", ".join(xy(c) for c in cs)  # noqa: E731
    items = lambda es: "; ".join(f"{e['ago']} ago, {event_text(e, names, v)}" for e in es)  # noqa: E731
    L = v.lines
    out = [L["now"].format(trigger=v.trigger[p.trigger]),
           L["state"].format(pos=xy(p.position), home=xy(p.home), life=f"{p.life:g}", carrying=yn(p.carrying), at_home=yn(p.at_home))]
    if p.stunned:
        out.append(L["stunned"].format(n=p.stunned))
    out.append(L["intent"].format(intent=intent_text(p.intent, v), status=v.status.get(p.motor_status, p.motor_status)))
    out.append(L["view"])
    view = str.maketrans(v.view)
    out += [row.translate(view) for row in p.view]
    if p.hornets_seen:
        out.append(L["movers"].format(cells=cells(p.hornets_seen)))
    if p.bees_seen:
        out.append(L["others"].format(cells=cells(p.bees_seen)))
    if p.bloom_seen:
        out.append(L["bright"].format(cells=cells(p.bloom_seen)))
    out.append(L["sounds"].format(sounds=sounds_text(p.sounds, names, v) or "none"))
    new = [e for e in p.new_events if e["what"] != "heard" or e["ago"] > 0]
    if new:
        out.append(L["new"].format(items=items(new)))
    if memory:
        older = [e for e in p.recent_events if e not in p.new_events]
        if older:
            out.append(L["older"].format(items=items(older)))
        if notes:
            out.append(L["notes"].format(notes=" | ".join(notes)))
        if recalled:
            out.append(L["recall"].format(items="; ".join(f"{a} ago, {text}" for a, text in recalled)))
    if talk:
        said = [h for h in p.heard_at_home if memory or h[0] <= since]
        if said:
            out.append(L["heard"].format(items=" ".join(L["heard_item"].format(ago=a, who=who, text=text) for a, who, text in said)))
    out.append(L["places"].format(home=xy(p.home)))
    if memory:
        spots = clusters(p.bloom_remembered)
        if spots:
            out.append(L["spots"].format(items=", ".join(f"around {xy(c)} {a} ago" for c, a in spots)))
        movers = {}
        for x, y, a in p.hornets_remembered:
            movers[(x, y)] = min(a, movers.get((x, y), a))
        if movers:
            out.append(L["movers_seen"].format(items=", ".join(f"{xy(c)} {a} ago" for c, a in movers.items())))
        out.append(L["explored"].format(items=", ".join(f"{d} {round(100 * p.explored.get(d, 0))}%" for d in DIRECTIONS)))
    out.append(L["choose"])
    return "\n".join(out)


def decision_schema(condition: str, v: Vocab = DEFAULT) -> dict:
    props = {
        "intent": {"type": "string", "enum": list(v.intents)},
        "direction": {"type": "string", "enum": list(DIRECTIONS)},
        "x": {"type": "integer"},
        "y": {"type": "integer"},
        v.keys["sound"]: {"type": "string", "enum": ["none", *sound_names(condition, v)]},
    }
    if condition != "no_memory":
        props["remember"] = {"type": "string"}
    if condition != "no_talk":
        props[v.keys["say"]] = {"type": "string"}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def parse(text: str, condition: str, grid: tuple[int, int], v: Vocab = DEFAULT) -> Decision:
    """Model reply (JSON matching decision_schema) -> Decision in the sim's terms. Raises ValueError on a malformed reply."""
    d = json.loads(text)
    if not isinstance(d, dict) or d.get("intent") not in v.intents:
        raise ValueError(f"bad decision: {text[:120]!r}")
    intent, names = v.sim_intent(d["intent"]), sound_names(condition, v)
    sound = d.get(v.keys["sound"], "none")
    sound = SIM_SOUNDS[names.index(sound)] if sound in names else "none"
    target = None
    if intent == "go_to":
        target = (min(max(int(d.get("x", 0)), 0), grid[0] - 1), min(max(int(d.get("y", 0)), 0), grid[1] - 1))
    return Decision(intent=intent, direction=d.get("direction"), target=target, sound=sound,
                    remember=d.get("remember", "") if condition != "no_memory" else "",
                    say=d.get(v.keys["say"], "") if condition != "no_talk" else "")
