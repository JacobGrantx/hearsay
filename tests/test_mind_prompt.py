"""Acceptance tests for the bee mind's prompts: no hints about the world, and no leaked coordinates.

The no-hints test here is round 1's, unchanged, on the neutral vocabulary; the abstract one is in test_vocab.py.
"""
import re

import pytest
from conftest import COORD, CaptureLog, FakeMind

from digital_life import bees as B
from digital_life import render
from digital_life.bees import BLOOM_VISION, VISION
from digital_life.mind import AI_CONDITIONS, AIPolicy
from digital_life.perception import TRIGGERS, Perception
from digital_life.sim import Sim
from digital_life.vocab import NEUTRAL as N

SMALL = dict(width=40, height=24, season_length=40, years=1, min_bloom_distance=20, log_state=False)
BANNED = re.compile(r"\b(bee|hive|flower|bloom|nectar|hornet|wasp|predator|danger|avoid|enemy|season|winter|summer|spring"
                    r"|autumn|food|good|bad)", re.IGNORECASE)
REAL_SENSE = B.sense
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))  # noqa: E731


def hints(text: str, condition: str = "full") -> list[str]:
    if condition == "labels_good_bad":
        text = text.replace("good noise", "").replace("bad noise", "")
    return BANNED.findall(text)


def rich_perception(trigger: str) -> Perception:
    events = [{"what": "saw_mover", "at": [[5, 5]], "ago": 3}, {"what": "saw_bright", "at": [6, 6], "ago": 2},
              {"what": "heard", "sounds": [["sound-1", "NE", "near"], ["sound-2", "S", "far"]], "ago": 1},
              {"what": "picked_up", "ago": 1}, {"what": "delivered", "ago": 0}, {"what": "stung", "at": [4, 4], "ago": 0}]
    return Perception(1, trigger, (4, 4), (2, 2), 120.5, True, False, 2, (40, 24), ["#.Hb*x@  "] * 9, [(5, 4)], [(5, 5)],
                      [(6, 6)], [("sound-1", "N", "mid")], events, events[3:], [(2, 3, "hello")], [(6, 6, 9)],
                      [(5, 5, 3)], {"N": 0.5}, "go_to:6,6", "moving", 300.0)


def test_system_prompts_and_templates_carry_no_hints():
    assert not hints(N.prompt_file.read_text())
    for cond in AI_CONDITIONS:
        text = render.system_prompt(cond, 80, 48, N)
        assert not hints(text, cond), cond
        assert ("good noise" in text) == (cond == "labels_good_bad")
    for table in (N.parts, N.trigger, N.event, N.band, N.status, N.lines):
        assert not [v for v in table.values() if hints(v)]
    for cond in AI_CONDITIONS:
        assert not hints(str(render.decision_schema(cond, N)), cond)
        for trig in TRIGGERS:
            for memory in (True, False):
                text = render.render(rich_perception(trig), render.sound_names(cond, N), N, memory=memory, talk=True,
                                     notes=["a note (3 ago)"], recalled=[(9, "a thing")])
                assert not hints(text, cond), (cond, trig, text)


class LeakSpy:
    """Records what each bee truly had in range and what it heard at home, and checks every prompt."""

    def __init__(self, sim, log):
        self.sim, self.log, self.checked, self.secret_hits = sim, log, 0, 0
        self.ok: dict[int, set] = {}

    def sense(self, bee, world, t, others, hornets, bloom, sounds):
        ok = self.ok.setdefault(bee.id, {world.home})
        ok.add(bee.pos)
        ok.update(c for c in bloom if cheb(c, bee.pos) <= BLOOM_VISION)
        ok.update((x, y) for _, x, y in hornets if cheb((x, y), bee.pos) <= VISION)
        ok.update((x, y) for i, x, y in others if i != bee.id and cheb((x, y), bee.pos) <= VISION)
        return REAL_SENSE(bee, world, t, others, hornets, bloom, sounds)

    def heard(self, bee_id: int) -> set:
        return {(int(x), int(y)) for e in self.log.events if e["kind"] == "say" and bee_id in e["heard_by"]
                for x, y in COORD.findall(e["text"])}

    def check(self, bee_id: int, text: str) -> None:
        sim = self.sim
        secret = {c for cells in sim.world.bloom.values() for c in cells} | {(h.x, h.y) for h in sim.swarm.active}
        allowed = self.ok.get(bee_id, set()) | self.heard(bee_id)
        for c in {(int(x), int(y)) for x, y in COORD.findall(text)} & secret:
            assert c in allowed, f"bee {bee_id} was told {c}, which it never perceived or heard at home"
            self.secret_hits += 1
        self.checked += 1


def run_with_spy(tmp_path, condition, seed, vocab):
    log = CaptureLog(tmp_path / f"{condition}-{seed}-{vocab}")
    params = {**SMALL, "condition": condition, "vocab": vocab}
    sim = Sim(params, seed, log, policy=AIPolicy(params, seed, client=FakeMind()))
    spy = LeakSpy(sim, log)
    inner = sim.policy.prompt
    sim.policy.prompt = lambda p, tick: (lambda text: (spy.check(p.bee_id, text), text)[1])(inner(p, tick))
    B.sense = spy.sense
    try:
        sim.run()
    finally:
        B.sense = REAL_SENSE
    return spy, log


@pytest.mark.parametrize("vocab", ["neutral", "abstract"])
@pytest.mark.parametrize("condition", ["full", "no_memory"])
def test_no_prompt_holds_coordinates_the_bee_never_perceived(tmp_path, llm_sandbox, condition, vocab):
    hits = 0
    for seed in (0, 1):
        spy, log = run_with_spy(tmp_path, condition, seed, vocab)
        assert spy.checked > 100
        hits += spy.secret_hits
        if condition == "full":
            assert any(e["kind"] == "say" and e["heard_by"] for e in log.events)
    assert hits > 0  # the check met real bloom and hornet coordinates, so it was not vacuous


def test_leak_check_catches_an_injected_leak(tmp_path, llm_sandbox):
    log = CaptureLog(tmp_path / "x")
    sim = Sim({**SMALL, "condition": "full"}, 0, log, policy=AIPolicy({**SMALL, "condition": "full"}, 0, client=FakeMind()))
    spy = LeakSpy(sim, log)
    far = max(sim.world.bloom["spring"], key=lambda c: c[0])
    with pytest.raises(AssertionError):
        spy.check(0, f"Bright cells in view: ({far[0]}, {far[1]}).")
