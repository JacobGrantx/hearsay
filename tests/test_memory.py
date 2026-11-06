"""A bee's memory: beliefs evict the oldest, recall ranks by importance and relevance and skips what is already shown."""
from digital_life.memory import MAX_BELIEFS, BeeMemory
from digital_life.perception import Perception
from digital_life.vocab import NEUTRAL

NAMES = ("sound-1", "sound-2")


def perception(position=(10, 10), new_events=(), recent=(), heard=(), hornets=(), at_home=False) -> Perception:
    return Perception(0, "timer", position, (2, 2), 100.0, False, at_home, 0, (40, 24), [" " * 9] * 9, [], list(hornets), [],
                      [], list(recent), list(new_events), list(heard), [], [], {}, "", "idle", None)


def test_beliefs_keep_the_latest_twelve():
    m = BeeMemory(NEUTRAL)
    for i in range(MAX_BELIEFS + 3):
        m.remember(i, f"note {i}")
    m.remember(99, "   ")
    notes = m.notes(20)
    assert len(notes) == MAX_BELIEFS and notes[0].startswith("note 3") and notes[-1] == "note 14 (6 ago)"


def test_recall_prefers_important_and_relevant_episodes_and_skips_recent_ones():
    m = BeeMemory(NEUTRAL)
    old = [{"what": "heard", "sounds": [["sound-1", "N", "far"]], "ago": 100 - i} for i in range(20)]
    sting = {"what": "stung", "at": [30, 5], "ago": 95}
    m.observe(perception(new_events=old + [sting]), 100, NAMES)
    near_sting = perception(position=(31, 6), hornets=[(32, 6)])
    got = m.recall(near_sting, 200)
    assert len(got) == 6 and any("lost half your life" in text for _, text in got)
    assert got == sorted(got, key=lambda r: -r[0])  # oldest first
    shown = perception(position=(31, 6), recent=[{**sting, "ago": 195}])
    assert not any("lost half your life" in text for _, text in m.recall(shown, 200))


def test_talk_heard_at_home_is_stored_once():
    m = BeeMemory(NEUTRAL)
    heard = [(3, 7, "bright at (30, 5)")]
    m.observe(perception(heard=heard, at_home=True), 50, NAMES)
    m.observe(perception(heard=[(8, 7, "bright at (30, 5)")], at_home=True), 55, NAMES)
    assert [e.kind for e in m.episodes] == ["heard_home"] and "r3_0" in m.episodes[0].tokens
