"""The abstract vocabulary: no word in anything code writes into a prompt that carries real-world meaning about the
world, no action that names a reaction to K, and every AI config says which vocabulary it uses.

Banned words match at word boundaries, with regular endings (bees, hornets, fleeing, safely, harmful, ...) and the
irregular forms listed in IRREGULAR. Exceptions, each with its reason:
- "fall" matches only as the bare word: "your counter C falls each tick" and "fell below half" describe the counter
  going down, never the season.
- "good noise" and "bad noise" are allowed under labels_good_bad only: loaded sound names are that condition's point.
- Placeholders in templates ({home}, {carrying}) are code names that are filled in before the model reads anything;
  the rendered prompts are checked as well.
"""
import re
import tomllib
from pathlib import Path

import pytest
from conftest import CaptureLog, FakeMind
from test_mind_prompt import rich_perception

from digital_life import render
from digital_life.mind import AI_CONDITIONS, AIPolicy
from digital_life.perception import TRIGGERS
from digital_life.sim import Sim
from digital_life.vocab import ABSTRACT as A
from digital_life.vocab import NEUTRAL, get

STEMS = ("bee hive flower bloom nectar pollen honey hornet wasp predator prey danger dangerous avoid enemy threat harm hurt "
         "pain safe safety season winter summer spring autumn cold warm food eat hungry good bad home life alive live die "
         "dead death kill flee escape attack sting carry member family sister nest colony queen worker").split()
IRREGULAR = "carried carries stung fled dying living ate eaten hunger colonies families enemies lives".split()
BANNED = re.compile(r"\b(?:(?:%s)(?:s|es|d|ed|r|er|ers|ing|y|ly|ful|less)?|%s|fall)\b" % ("|".join(STEMS), "|".join(IRREGULAR)),
                    re.IGNORECASE)
CONFIGS = Path(__file__).resolve().parents[1] / "experiments" / "configurations"


def hints(text: str, condition: str = "full") -> list[str]:
    if condition == "labels_good_bad":
        text = text.replace("good noise", "").replace("bad noise", "")
    return BANNED.findall(re.sub(r"\{\w+\}", "", text))


def test_the_banned_list_catches_what_it_should():
    for word in ("Bees", "hornet's", "fleeing", "carrying", "safely", "harmful", "stung", "home", "fall", "lives", "dies"):
        assert hints(word), word
    for word in ("been", "east", "falls", "fell", "cell", "string", "starting", "units", "zone"):
        assert not hints(word), word
    assert hints(NEUTRAL.prompt_file.read_text())  # the neutral wording has loaded words, which is why abstract exists


def test_abstract_prompts_templates_and_schema_carry_no_hints():
    assert not hints(A.prompt_file.read_text())
    for table in (A.parts, A.trigger, A.event, A.band, A.status, A.lines):
        assert not [t for t in table.values() if hints(t)], table
    assert not hints(" ".join(A.sounds) + " " + " ".join(A.intents) + " " + " ".join(A.keys.values()))
    for cond in AI_CONDITIONS:
        assert not hints(render.system_prompt(cond, 56, 34, A), cond), cond
        assert not hints(str(render.decision_schema(cond, A)), cond), cond
        for trig in TRIGGERS:
            for memory in (True, False):
                text = render.render(rich_perception(trig), render.sound_names(cond, A), A, memory=memory, talk=True,
                                     notes=["a note (3 ago)"], recalled=[(9, "a thing")])
                assert not hints(text, cond), (cond, trig, text)


@pytest.mark.parametrize("condition", ["full", "no_memory"])
def test_every_prompt_of_a_whole_abstract_run_carries_no_hints(tmp_path, llm_sandbox, condition):
    """End to end: memory episodes, recall, talk heard in zone O and notes, as they reach real prompts."""
    params = dict(width=40, height=24, season_length=40, years=1, min_bloom_distance=20, log_state=False,
                  condition=condition, vocab="abstract")
    fake = FakeMind()
    Sim(params, 1, CaptureLog(tmp_path / condition), policy=AIPolicy(params, 1, client=fake)).run()
    assert len(fake.prompts) > 100
    for system, user in fake.prompts:
        assert not hints(system) and not hints(user), hints(system + user)


def test_abstract_schema_offers_no_flee():
    for cond in AI_CONDITIONS:
        intents = render.decision_schema(cond, A)["properties"]["intent"]["enum"]
        assert intents == ["explore", "go_to", "go_to_O", "hold"] and "flee" not in intents
        assert "flee" not in render.system_prompt(cond, 56, 34, A)
    with pytest.raises(ValueError):
        render.parse('{"intent": "flee"}', "full", (40, 24), A)
    assert "flee" in render.decision_schema("full", NEUTRAL)["properties"]["intent"]["enum"]  # round 1 keeps it


def test_abstract_replies_map_back_to_the_sims_terms():
    reply = '{"intent": "go_to_O", "direction": "N", "x": 1, "y": 2, "signal": "signal B", "remember": "r", "broadcast": "at (3, 4)"}'
    d = render.parse(reply, "full", (40, 24), A)
    assert (d.intent, d.sound, d.say, d.remember) == ("go_home", "sound-2", "at (3, 4)", "r")
    assert render.parse(reply.replace("go_to_O", "hold"), "full", (40, 24), A).intent == "wait"
    assert render.intent_text("go_home", A) == "go_to_O" and render.intent_text("wait", A) == "hold"
    assert render.intent_text("explore:NE", A) == "explore NE" and render.intent_text("go_to:3,4", A) == "go_to (3, 4)"


def test_every_ai_config_names_its_vocab():
    """experiments/replay_check.py reads a missing vocab as a round 1 run (neutral), so new configs must say."""
    for path in sorted(CONFIGS.glob("*.toml")):
        params = tomllib.loads(path.read_text()).get("params", {})
        if params.get("condition") in AI_CONDITIONS:
            assert params.get("vocab") in ("neutral", "abstract"), path.name
    assert get() is A
    with pytest.raises(ValueError):
        get("bees")
