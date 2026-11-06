"""Round 2 switches: the shared decision clock, steady hatching, the told reward rule and the wall-clock stop.
Each is off by default, so round 1 runs replay unchanged."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from conftest import CaptureLog, FakeMind

from digital_life import render
from digital_life.mind import AIPolicy
from digital_life.sim import Sim
from digital_life.vocab import ABSTRACT, NEUTRAL
from experiments.run import run

SMALL = dict(width=40, height=24, season_length=30, years=1, min_bloom_distance=20, log_state=False)
DEADLINE = "2026-11-06T18:05:00Z"
AT = datetime(2026, 11, 6, 18, 5, tzinfo=timezone.utc)


def events(log, kind):
    return [e for e in log.events if e["kind"] == kind]


def sim_run(tmp_path, name, seed=0, **extra):
    log = CaptureLog(tmp_path / name)
    sim = Sim({**SMALL, "condition": "rule_bees", **extra}, seed, log, now=extra.pop("_now", None))
    sim.run()
    return sim, log


def test_shared_clock_puts_every_timer_decision_on_the_shared_tick(tmp_path):
    _, own = sim_run(tmp_path, "own")
    _, shared = sim_run(tmp_path, "shared", shared_clock=True)
    assert [e for e in events(own, "decision") if e["trigger"] == "timer" and e["t"] % 5]  # off: own clocks
    timers = [e for e in events(shared, "decision") if e["trigger"] == "timer"]
    assert timers and all(e["t"] % 5 == 0 for e in timers)


def test_steady_hatching_adds_one_blank_bee_on_schedule_outside_winter(tmp_path):
    _, off = sim_run(tmp_path, "off")
    assert not [e for e in events(off, "hatch") if e["cause"] == "steady"]
    sim, log = sim_run(tmp_path, "on", steady_hatch=20)
    steady = [e for e in events(log, "hatch") if e["cause"] == "steady"]
    assert steady and all(e["t"] % 20 == 0 and e["t"] > 0 for e in steady)
    assert all(sim.cal.season(e["t"]) != 3 for e in steady)
    assert sim.metrics.rows and sum(r["hatches"] for r in sim.metrics.rows) <= len(events(log, "delivery"))  # steady hatches are not delivery hatches


def test_reward_rule_is_one_sentence_for_arm_a_only():
    plain = render.system_prompt("full", 56, 34, ABSTRACT)
    told = render.system_prompt("full", 56, 34, ABSTRACT, tell_reward=True)
    assert render.REWARD_TOLD.strip() not in plain
    assert told.replace(render.REWARD_TOLD, "") == plain
    with pytest.raises(ValueError):
        render.system_prompt("full", 56, 34, NEUTRAL, tell_reward=True)
    params = {**SMALL, "condition": "full", "vocab": "abstract", "tell_reward": True}
    assert render.REWARD_TOLD in AIPolicy(params, 0, client=FakeMind()).system


def test_wallclock_stop_ends_at_the_first_season_boundary_after_the_deadline(tmp_path):
    holder = {}
    clock = lambda: AT + timedelta(seconds=1) if holder["sim"].t >= 40 else AT - timedelta(seconds=1)  # noqa: E731
    log = CaptureLog(tmp_path / "stop")
    sim = holder["sim"] = Sim({**SMALL, "condition": "rule_bees", "years": 2, "stop_wallclock_utc": DEADLINE}, 0, log, now=clock)
    sim.run()
    assert sim.t == 60 and events(log, "end")[0]["t"] == 60
    assert log.record_extra == {"stopped_at_tick": 60, "stopped_reason": f"wallclock {DEADLINE}"}
    assert len(sim.metrics.rows) == 2  # two whole seasons, both written
    # a replay stops at the recorded tick, whatever the time is now
    again = CaptureLog(tmp_path / "again")
    Sim({**SMALL, "condition": "rule_bees", "years": 2, "stop_after": 60, "stop_wallclock_utc": None}, 0, again).run()
    assert again.events == log.events


def test_runner_records_the_stop_and_the_stopped_run_replays_identically(tmp_path):
    cfg = tmp_path / "stop.toml"
    cfg.write_text('[experiment]\nname = "stop"\nentrypoint = "digital_life.sim:run"\nseeds = [3]\n\n[params]\n'
                   'condition = "rule_bees"\nwidth = 40\nheight = 24\nseason_length = 30\nyears = 2\n'
                   'min_bloom_distance = 20\nstop_wallclock_utc = "2000-01-01T00:00:00Z"\n')
    out = run(cfg, results_root=tmp_path / "a")
    rec = json.loads((out / "seed-3" / "record.json").read_text())
    assert rec["error"] is None and rec["stopped_at_tick"] == 30 and rec["stopped_reason"].startswith("wallclock")
    rep = run(cfg, overrides=[f"stop_after={rec['stopped_at_tick']}", "stop_wallclock_utc=None"], results_root=tmp_path / "b")
    for name in ("events.jsonl", "metrics.jsonl", "state.jsonl.gz", "layout.json"):
        assert (out / "seed-3" / name).read_bytes() == (rep / "seed-3" / name).read_bytes(), name
    assert "stopped_at_tick" not in json.loads((rep / "seed-3" / "record.json").read_text())
