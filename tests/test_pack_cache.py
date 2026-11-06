"""Packed replay caches: a run packed by tools/pack_llm_cache.py replays offline with no loose entries left."""
import gzip
import json
import shutil
from types import SimpleNamespace

import pytest

import pack_llm_cache as pk
from digital_life import llm


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=f'{{"intent": "wait", "n": {self.calls}}}')],
            model=kwargs["model"], stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=100, output_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0),
        )


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(llm, "SPEND_FILE", tmp_path / "spend.json")
    monkeypatch.setattr(llm, "_client", None)
    monkeypatch.delenv("LLM_MODE", raising=False)
    return tmp_path / "cache"


def fake_run(tmp_path, keys):
    run = tmp_path / "results" / "full" / "20261106T000000Z" / "seed-0"
    run.mkdir(parents=True)
    lines = [json.dumps({"kind": "decision", "t": i, "bee": 0, "prompt_key": k[:12]}) for i, k in enumerate(keys)]
    (run / "events.jsonl").write_text("\n".join(lines + [json.dumps({"kind": "end", "t": 9})]) + "\n")
    return run


def test_packed_run_replays_offline(cache, tmp_path, monkeypatch):
    fake = FakeClient()
    live = [llm.complete("view", tag=f"0:{t}:0:full", client=fake) for t in range(3)]
    run = fake_run(tmp_path, [c.key for c in live])
    out, n, problems = pk.pack(run, pk.loose_index(cache), cache)
    assert (n, problems) == (3, []) and out.name == "full_20261106T000000Z_seed-0.jsonl.gz"
    for sub in cache.glob("??"):
        shutil.rmtree(sub)
    monkeypatch.setenv("LLM_MODE", "replay")
    again = [llm.complete("view", tag=f"0:{t}:0:full", client=fake) for t in range(3)]
    assert fake.calls == 3
    assert [c.text for c in again] == [c.text for c in live] and all(c.cached for c in again)
    with pytest.raises(llm.CacheMiss):
        llm.complete("view", tag="0:99:0:full", client=fake)


def test_pack_is_byte_stable_and_reports_missing(cache, tmp_path):
    fake = FakeClient()
    c = llm.complete("view", tag="0:1:0:full", client=fake)
    run = fake_run(tmp_path, [c.key, "deadbeef0000" + "0" * 52])
    out, n, problems = pk.pack(run, pk.loose_index(cache), cache)
    first = out.read_bytes()
    out2, _, _ = pk.pack(run, pk.loose_index(cache), cache)
    assert n == 1 and problems == ["deadbeef0000: 0 cache entries"]
    assert out2.read_bytes() == first


def test_run_order_pack_holds_the_same_entries_and_is_byte_stable(cache, tmp_path):
    fake = FakeClient()
    calls = [llm.complete("view", tag=f"0:{t}:0:full", client=fake) for t in range(4)]
    run = fake_run(tmp_path, [c.key for c in reversed(calls)])  # first use in the run differs from key order
    by_key = pk.pack(run, pk.loose_index(cache), tmp_path / "k")[0].read_bytes()
    out, n, problems = pk.pack(run, pk.loose_index(cache), tmp_path / "r", order="run")
    first = out.read_bytes()
    assert (n, problems) == (4, []) and pk.pack(run, pk.loose_index(cache), tmp_path / "r", order="run")[0].read_bytes() == first
    run_lines = gzip.decompress(first).decode().splitlines()
    assert sorted(run_lines) == gzip.decompress(by_key).decode().splitlines()
    assert [json.loads(line)["key"] for line in run_lines] == [c.key for c in reversed(calls)]
