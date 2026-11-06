"""The model wrapper must record, replay and stop at the budget without touching the network."""
import json
from types import SimpleNamespace

import pytest

from digital_life import llm


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=f"reply {self.calls}")],
            model=kwargs["model"],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=1000, output_tokens=500, cache_read_input_tokens=0, cache_creation_input_tokens=0),
        )


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(llm, "SPEND_FILE", tmp_path / "spend.json")
    monkeypatch.setattr(llm, "_client", None)
    monkeypatch.delenv("LLM_MODE", raising=False)
    monkeypatch.delenv("LLM_BUDGET_USD", raising=False)


def test_records_then_replays():
    fake = FakeClient()
    a = llm.complete("hello", client=fake)
    b = llm.complete("hello", client=fake)
    assert fake.calls == 1 and a.text == b.text == "reply 1"
    assert not a.cached and b.cached
    assert a.cost_usd == pytest.approx((1000 * 4 + 500 * 20) / 1e6)


def test_tag_gives_independent_samples():
    fake = FakeClient()
    assert llm.complete("hi", tag="s0", client=fake).text != llm.complete("hi", tag="s1", client=fake).text


def test_replay_mode_never_calls(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "replay")
    with pytest.raises(llm.CacheMiss):
        llm.complete("never seen", client=FakeClient())


def test_budget_cap_stops_live_calls(monkeypatch):
    fake = FakeClient()
    monkeypatch.setenv("LLM_BUDGET_USD", "0.01")
    llm.complete("one", client=fake)  # $0.014 spent, over the cap afterwards
    with pytest.raises(llm.BudgetExceeded):
        llm.complete("two", client=fake)
    assert llm.complete("one", client=fake).cached  # cached replays still work over budget


def test_logs_usage_to_run(tmp_path):
    events = []
    log = SimpleNamespace(event=lambda kind, **d: events.append({"kind": kind, **d}))
    llm.complete("x", client=FakeClient(), log=log, tag="t")
    assert events[0]["kind"] == "llm_call" and events[0]["usage"]["output_tokens"] == 500
    json.dumps(events)


def test_schema_and_thinking_reach_the_api_and_the_cache_key():
    seen = {}

    class Capture(FakeClient):
        def create(self, **kwargs):
            seen.update(kwargs)
            return super().create(**kwargs)

    schema = {"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"], "additionalProperties": False}
    a = llm.complete("act", client=Capture(), schema=schema, thinking={"type": "disabled"}, effort="low")
    assert seen["output_config"] == {"effort": "low", "format": {"type": "json_schema", "schema": schema}}
    assert seen["thinking"] == {"type": "disabled"}
    b = llm.complete("act", client=Capture(), effort="low")  # same prompt, no schema: a different request
    assert a.key != b.key
