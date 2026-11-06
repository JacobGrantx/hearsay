"""Shared test helpers for the AI bee mind: a fake model client and an isolated replay cache. No network."""
import hashlib
import json
import re
import threading
from types import SimpleNamespace

import pytest

from digital_life import llm

COORD = re.compile(r"\((\d+), (\d+)\)")
DIRS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
TWICE = ("explore", "go_to")  # the fake picks these twice as often as the other intents


class FakeMind:
    """Stands in for the model. The reply is a pure function of the prompt, and every coordinate it uses
    comes from that prompt, so anything a bee later perceives through its own notes or talk was already
    in some prompt. fail: call numbers that raise; garbage: call numbers that return text that is not JSON."""

    def __init__(self, fail=(), garbage=()):
        self.messages = self
        self.calls, self.prompts, self.fail, self.garbage = 0, [], set(fail), set(garbage)
        self.lock = threading.Lock()

    def create(self, **kw):
        text = kw["messages"][0]["content"]
        with self.lock:
            self.calls += 1
            n = self.calls
            self.prompts.append((kw.get("system"), text))
        if n in self.fail:
            raise RuntimeError("fake API failure")
        h = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        coords = COORD.findall(text)
        x, y = (int(v) for v in coords[h % len(coords)]) if coords else (0, 0)
        props = kw["output_config"]["format"]["schema"]["properties"]
        intents = [i for i in props["intent"]["enum"] for _ in range(2 if i in TWICE else 1)]
        intent = intents[h % len(intents)]
        sound = "sound" if "sound" in props else "signal"  # the schema keys depend on the vocabulary
        d = {"intent": intent if (coords or intent != "go_to") else "explore", "direction": DIRS[(h >> 8) % 8],
             "x": x, "y": y, sound: props[sound]["enum"][(h >> 16) % 3]}
        if "remember" in props:
            d["remember"] = f"mark ({x}, {y})" if (h >> 20) % 2 else ""
        for say in ("say", "broadcast"):
            if say in props:
                d[say] = f"look at ({x}, {y})"
        reply = "not json" if n in self.garbage else json.dumps(d)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=reply)], model=kw["model"], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=len(text) // 4, output_tokens=40,
                                                     cache_read_input_tokens=0, cache_creation_input_tokens=0))


class CaptureLog:
    """Enough of RunLog for the sim: events kept in a list, files under a temp dir."""

    def __init__(self, d):
        self.d, self.events = d, []
        d.mkdir(parents=True, exist_ok=True)

    def event(self, kind, **data):
        self.events.append({"kind": kind, **data})

    def metric(self, **row):
        pass

    def path(self, name):
        return self.d / name


@pytest.fixture
def llm_sandbox(tmp_path, monkeypatch):
    """A private replay cache and spend ledger, auto mode, so tests never touch the real ones."""
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm_cache")
    monkeypatch.setattr(llm, "SPEND_FILE", tmp_path / "spend.json")
    monkeypatch.setattr(llm, "_client", None)
    monkeypatch.delenv("LLM_MODE", raising=False)
    monkeypatch.delenv("LLM_BUDGET_USD", raising=False)
    return tmp_path
