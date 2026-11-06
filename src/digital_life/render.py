"""The bee mind's words: the system prompt, Perception rendered as text, the decision schema and the parser.

Every piece of fixed text a prompt can contain lives here or in prompts/bee_system.txt, so the no-hints test
(tests/test_mind.py) can check all of it for words that would tell the model what the world is. The model
never hears bee, hive, bloom, hornet, season, food, danger and the like: it gets a grid, a home, bright cells,
moving things, two sounds and a life number, and has to work out the rest.
"""
from __future__ import annotations

import json
from pathlib import Path

from .perception import DIRECTIONS, INTENTS, Decision, Perception

PROMPT_FILE = Path(__file__).resolve().parents[2] / "prompts" / "bee_system.txt"
NEUTRAL_SOUNDS = ("sound-1", "sound-2")
LABELLED_SOUNDS = ("good noise", "bad noise")  # only under labels_good_bad

SYSTEM_PARTS = {
    "memory_part": ", things you noted, and things you recall",
    "talk_part": "\n- words other members said while you were at home.",
    "remember_line": "\n- remember: a short note to keep (under 15 words), or empty. You keep your 12 latest notes.",
    "say_line": "\n- say: up to 30 words that every other member at home hears, used only while you are at home; or empty.",
}
TRIGGER_TEXT = {
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
}
EVENT_TEXT = {
    "saw_mover": "saw moving things at {at}",
    "saw_bright": "saw bright cells near {at}",
    "heard": "heard {sounds}",
    "picked_up": "touched a bright cell and began carrying something",
    "delivered": "carried it into home, and your life rose",
    "stung": "lost half your life in an instant at {at}, and could not move for 2 moments",
    "heard_home": "at home, member {who} said: \"{text}\"",
}
BAND_TEXT = {"near": "near", "mid": "middle distance", "far": "far"}
STATUS_TEXT = {"moving": "under way", "arrived": "route ended", "blocked": "route ended", "idle": "not started"}
VIEW_SYMBOLS = str.maketrans({"b": "m"})  # the sim marks other members "b"; the prompt calls them "m"


def sound_names(condition: str) -> tuple[str, str]:
    return LABELLED_SOUNDS if condition == "labels_good_bad" else NEUTRAL_SOUNDS


def system_prompt(condition: str, width: int, height: int) -> str:
    s1, s2 = sound_names(condition)
    memory, talk = condition != "no_memory", condition != "no_talk"
    return PROMPT_FILE.read_text().format(
        width=width, height=height, sound_1=s1, sound_2=s2,
        memory_part=SYSTEM_PARTS["memory_part"] if memory else "",
        talk_part=SYSTEM_PARTS["talk_part"] if talk else "",
        remember_line=SYSTEM_PARTS["remember_line"] if memory else "",
        say_line=SYSTEM_PARTS["say_line"] if talk else "").strip()


def xy(c) -> str:
    return f"({c[0]}, {c[1]})"


def event_text(e: dict, names: tuple[str, str]) -> str:
    what = e["what"]
    if what == "heard":
        sounds = "; ".join(f"{sound_label(s, names)} from the {d}, {BAND_TEXT[b]}" for s, d, b in e["sounds"])
        return EVENT_TEXT["heard"].format(sounds=sounds)
    at = e.get("at")
    if at and isinstance(at[0], list):
        at = ", ".join(xy(c) for c in at)
    elif at:
        at = xy(at)
    return EVENT_TEXT[what].format(at=at)


def sound_label(sound: str, names: tuple[str, str]) -> str:
    return names[NEUTRAL_SOUNDS.index(sound)] if sound in NEUTRAL_SOUNDS else sound


def intent_text(label: str) -> str:
    if not label:
        return "none yet"
    if label.startswith("go_to:"):
        return f"go_to ({label[6:].replace(',', ', ')})"
    return label.replace(":", " ")


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


def render(p: Perception, names: tuple[str, str], *, memory: bool, talk: bool, notes=(), recalled=(), since: int = 5) -> str:
    """The user message for one decision. Under no_memory (memory=False) only the present is shown:
    what happened and what was said at home since the bee last decided, plus where home is."""
    yn = lambda v: "yes" if v else "no"  # noqa: E731
    out = [f"Now: {TRIGGER_TEXT[p.trigger]}.",
           f"You are at {xy(p.position)}. Home is {xy(p.home)}. Life {p.life:g}. Carrying: {yn(p.carrying)}. At home: {yn(p.at_home)}."]
    if p.stunned:
        out.append(f"You cannot move for {p.stunned} more moments.")
    out.append(f"Current intent: {intent_text(p.intent)} ({STATUS_TEXT.get(p.motor_status, p.motor_status)}).")
    out.append("View:")
    out += [row.translate(VIEW_SYMBOLS) for row in p.view]
    if p.hornets_seen:
        out.append("Moving things in view: " + ", ".join(xy(c) for c in p.hornets_seen) + ".")
    if p.bees_seen:
        out.append("Other members in view: " + ", ".join(xy(c) for c in p.bees_seen) + ".")
    if p.bloom_seen:
        out.append("Bright cells in view: " + ", ".join(xy(c) for c in p.bloom_seen) + ".")
    heard = "; ".join(f"{sound_label(s, names)} from the {d}, {BAND_TEXT[b]}" for s, d, b in p.sounds)
    out.append(f"Sounds now: {heard or 'none'}.")
    new = [e for e in p.new_events if e["what"] != "heard" or e["ago"] > 0]
    if new:
        out.append("Since you last decided: " + "; ".join(f"{e['ago']} ago, {event_text(e, names)}" for e in new) + ".")
    if memory:
        older = [e for e in p.recent_events if e not in p.new_events]
        if older:
            out.append("Earlier: " + "; ".join(f"{e['ago']} ago, {event_text(e, names)}" for e in older) + ".")
        if notes:
            out.append("Your notes, oldest first: " + " | ".join(notes))
        if recalled:
            out.append("You recall: " + "; ".join(f"{a} ago, {text}" for a, text in recalled) + ".")
    if talk:
        said = [h for h in p.heard_at_home if memory or h[0] <= since]
        if said:
            out.append("Heard at home: " + " ".join(f"[{a} ago, member {who}] \"{text}\"" for a, who, text in said))
    out.append(f"Places you know: home {xy(p.home)}.")
    if memory:
        spots = clusters(p.bloom_remembered)
        if spots:
            out.append("Bright spots you have seen: " + ", ".join(f"around {xy(c)} {a} ago" for c, a in spots) + ".")
        movers = {}
        for x, y, a in p.hornets_remembered:
            movers[(x, y)] = min(a, movers.get((x, y), a))
        if movers:
            out.append("Moving things you have seen: " + ", ".join(f"{xy(c)} {a} ago" for c, a in movers.items()) + ".")
        out.append("Share of the place you have seen, by direction from home: "
                   + ", ".join(f"{d} {round(100 * p.explored.get(d, 0))}%" for d in DIRECTIONS) + ".")
    out.append("Choose your action.")
    return "\n".join(out)


def decision_schema(condition: str) -> dict:
    props = {
        "intent": {"type": "string", "enum": list(INTENTS)},
        "direction": {"type": "string", "enum": list(DIRECTIONS)},
        "x": {"type": "integer"},
        "y": {"type": "integer"},
        "sound": {"type": "string", "enum": ["none", *sound_names(condition)]},
    }
    if condition != "no_memory":
        props["remember"] = {"type": "string"}
    if condition != "no_talk":
        props["say"] = {"type": "string"}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def parse(text: str, condition: str, grid: tuple[int, int]) -> Decision:
    """Model reply (JSON matching decision_schema) -> Decision. Raises ValueError on a malformed reply."""
    d = json.loads(text)
    if not isinstance(d, dict) or d.get("intent") not in INTENTS:
        raise ValueError(f"bad decision: {text[:120]!r}")
    names = sound_names(condition)
    sound = d.get("sound", "none")
    sound = NEUTRAL_SOUNDS[names.index(sound)] if sound in names else "none"
    target = None
    if d["intent"] == "go_to":
        target = (min(max(int(d.get("x", 0)), 0), grid[0] - 1), min(max(int(d.get("y", 0)), 0), grid[1] - 1))
    return Decision(intent=d["intent"], direction=d.get("direction"), target=target, sound=sound,
                    remember=d.get("remember", "") if condition != "no_memory" else "",
                    say=d.get("say", "") if condition != "no_talk" else "")
