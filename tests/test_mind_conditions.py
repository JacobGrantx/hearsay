"""The bee mind replays exactly, its condition flags disable what they claim to, and failures fall back to wait.
Every test runs under both vocabularies."""
import gzip
import json

import pytest
from conftest import CaptureLog, FakeMind

from digital_life import vocab as vocabs
from digital_life.mind import AIPolicy
from digital_life.render import decision_schema
from digital_life.runlog import RunLog
from digital_life.sim import Sim

SMALL = dict(width=40, height=24, season_length=30, years=1, min_bloom_distance=20, mind_retries=0)
VOCABS = pytest.mark.parametrize("vocab", ["neutral", "abstract"])


def run(tmp_path, condition, vocab, seed=0, client=None, **extra):
    log = CaptureLog(tmp_path / f"{condition}-{vocab}-{seed}")
    params = {**SMALL, "log_state": False, "condition": condition, "vocab": vocab, **extra}
    sim = Sim(params, seed, log, policy=AIPolicy(params, seed, client=client or FakeMind()))
    sim.run()
    return sim, log, sim.policy.client


def kinds(log, kind):
    return [e for e in log.events if e["kind"] == kind]


def head(v, key):
    """The fixed start of one rendered line, e.g. "Heard at home: "."""
    return v.lines[key].split("{")[0]


def read_dir(d):
    with gzip.open(d / "state.jsonl.gz", "rt") as f:
        return f.read(), (d / "events.jsonl").read_text(), (d / "metrics.jsonl").read_text()


@VOCABS
def test_replay_gives_an_identical_run(tmp_path, llm_sandbox, monkeypatch, vocab):
    params = {**SMALL, "condition": "full", "vocab": vocab}
    fake = FakeMind()
    for name, client in (("live", fake), ("replay", None)):
        if name == "replay":
            monkeypatch.setenv("LLM_MODE", "replay")  # a cache miss would raise
        log = RunLog(tmp_path / name)
        Sim(params, 2, log, policy=AIPolicy(params, 2, client=client)).run()
        log.close()
    live, replay = read_dir(tmp_path / "live"), read_dir(tmp_path / "replay")
    decisions = [json.loads(line) for line in live[1].splitlines() if '"decision"' in line]
    assert fake.calls == len(decisions) > 100
    assert all(d["usage"]["output_tokens"] == 40 and d["prompt_key"] and set(d["ctx"]) == {"movers", "bright", "carrying", "home"}
               for d in decisions)
    assert live == replay


@VOCABS
def test_full_condition_talks_remembers_and_recalls(tmp_path, llm_sandbox, vocab):
    v = vocabs.get(vocab)
    sim, log, fake = run(tmp_path, "full", vocab)
    assert any(e["heard_by"] for e in kinds(log, "say"))
    prompts = [u for _, u in fake.prompts]
    assert any(head(v, "heard") in u for u in prompts) and any(head(v, "notes") in u for u in prompts)
    assert any(head(v, "recall") in u for u in prompts)
    assert all(f"{v.keys['say']}:" in s and "remember:" in s for s, _ in fake.prompts)


@VOCABS
def test_no_talk_disables_say_and_hearing(tmp_path, llm_sandbox, vocab):
    v = vocabs.get(vocab)
    sim, log, fake = run(tmp_path, "no_talk", vocab)
    assert v.keys["say"] not in decision_schema("no_talk", v)["properties"]
    assert not kinds(log, "say") and all(d["say"] == "" for d in kinds(log, "decision"))
    assert all(f"{v.keys['say']}:" not in s and v.parts["talk_part"].strip() not in s for s, _ in fake.prompts)
    assert not any(head(v, "heard") in u for _, u in fake.prompts)
    assert all(not b.heard for b in sim.bees.values())


@VOCABS
def test_no_memory_disables_episodes_beliefs_and_recall(tmp_path, llm_sandbox, vocab):
    v = vocabs.get(vocab)
    sim, log, fake = run(tmp_path, "no_memory", vocab)
    assert "remember" not in decision_schema("no_memory", v)["properties"]
    assert not sim.policy.mem and all(d["remember"] == "" for d in kinds(log, "decision"))
    for s, u in fake.prompts:
        assert "remember:" not in s and "things you recall" not in s
        for gone in ("notes", "recall", "older", "spots", "movers_seen", "explored"):
            assert head(v, gone) not in u
    assert any(e["heard_by"] for e in kinds(log, "say"))  # talk still works without memory


@VOCABS
def test_labels_condition_renames_the_sounds_only_in_the_prompt(tmp_path, llm_sandbox, vocab):
    v = vocabs.get(vocab)
    key = v.keys["sound"]
    assert decision_schema("labels_good_bad", v)["properties"][key]["enum"] == ["none", "good noise", "bad noise"]
    assert decision_schema("full", v)["properties"][key]["enum"] == ["none", *v.sounds]
    sim, log, fake = run(tmp_path, "labels_good_bad", vocab)
    assert all("good noise" in s for s, _ in fake.prompts)
    made = {d["sound"] for d in kinds(log, "decision")}
    assert made == {"none", "sound-1", "sound-2"}  # mapped back: the world and the logs use the sim's names
    _, _, plain = run(tmp_path, "full", vocab)
    assert not any("noise" in s + u for s, u in plain.prompts)


def test_round_1_schema_is_unchanged():
    """Round 1 runs replay from their cache only if the neutral schema is byte for byte what they sent."""
    assert decision_schema("full", vocabs.NEUTRAL)["properties"]["sound"]["enum"] == ["none", "sound-1", "sound-2"]
    assert list(decision_schema("full", vocabs.NEUTRAL)["properties"]) == ["intent", "direction", "x", "y", "sound", "remember", "say"]


@VOCABS
@pytest.mark.parametrize("bad", ["fail", "garbage"])
def test_model_failures_fall_back_to_wait_and_are_logged(tmp_path, llm_sandbox, bad, vocab):
    sim, log, fake = run(tmp_path, "full", vocab, client=FakeMind(**{bad: range(3, 200, 7)}))
    errors = kinds(log, "mind_error")
    fallbacks = [d for d in kinds(log, "decision") if d.get("fallback")]
    assert errors and len(errors) == len(fallbacks) and all(d["intent"] == "wait" for d in fallbacks)
    assert {d["fallback"] for d in fallbacks} == {"error" if bad == "fail" else "parse"}
