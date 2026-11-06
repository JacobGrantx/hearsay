import gzip
import json
import sys
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_life import bees as B  # noqa: E402
from digital_life.bees import BLOOM_VISION, VISION  # noqa: E402
from digital_life.perception import Perception  # noqa: E402
from digital_life.runlog import RunLog  # noqa: E402
from digital_life.sim import Sim  # noqa: E402

SMALL = dict(width=40, height=24, season_length=60, years=2, min_bloom_distance=20)
REAL_SENSE = B.sense
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))  # noqa: E731


class Spy:
    """Wraps a policy and checks every Perception it is given."""

    def __init__(self, sim):
        self.sim, self.inner, self.n = sim, sim.policy, 0
        self.bloom_ok: dict[int, set] = {}
        self.hornet_ok: dict[int, set] = {}

    def sense(self, bee, world, t, others, hornets, bloom, sounds):
        """Wraps bees.sense: record what is truly in range of the bee when it senses."""
        self.bloom_ok.setdefault(bee.id, set()).update(c for c in bloom if cheb(c, bee.pos) <= BLOOM_VISION)
        self.hornet_ok.setdefault(bee.id, set()).update((x, y) for _, x, y in hornets if cheb((x, y), bee.pos) <= VISION)
        return REAL_SENSE(bee, world, t, others, hornets, bloom, sounds)

    def decide_many(self, ps):
        sim = self.sim
        bloom_now = set(sim.world.bloom_now(sim.cal.season(sim.t)))
        hornets_now = {(h.x, h.y) for h in sim.swarm.active}
        for p in ps:
            assert isinstance(p, Perception)
            for f in fields(p):  # nothing in a perception is a live simulation object
                v = getattr(p, f.name)
                assert type(v).__module__ in ("builtins",), f"{f.name} is {type(v)}"
            for c in p.bloom_seen:
                assert c in bloom_now and cheb(c, p.position) <= BLOOM_VISION
            for c in p.hornets_seen:
                assert c in hornets_now and cheb(c, p.position) <= VISION
            for x, y, _ in p.bloom_remembered:
                assert (x, y) in self.bloom_ok[p.bee_id]
            for x, y, _ in p.hornets_remembered:
                assert (x, y) in self.hornet_ok[p.bee_id]
            for e in p.recent_events + p.new_events:
                if e["what"] == "saw_bright":
                    assert tuple(e["at"]) in self.bloom_ok[p.bee_id]
                if e["what"] == "saw_mover":
                    assert all(tuple(c) in self.hornet_ok[p.bee_id] for c in e["at"])
            self.n += 1
        return self.inner.decide_many(ps)

    def bee_died(self, bee_id):
        self.inner.bee_died(bee_id)


def test_perception_never_contains_unseen_bloom_or_hornet_coordinates():
    for cond in ("rule_bees", "random_bees"):
        for seed in (0, 1):
            sim = Sim({**SMALL, "condition": cond, "log_state": False}, seed)
            spy = sim.policy = Spy(sim)
            B.sense = spy.sense
            try:
                sim.run()
            finally:
                B.sense = REAL_SENSE
            assert spy.n > 200


def _read(d: Path):
    with gzip.open(d / "state.jsonl.gz", "rt") as f:
        state = f.read()
    return state, (d / "events.jsonl").read_text(), (d / "metrics.jsonl").read_text()


def _run(params, seed, d: Path):
    log = RunLog(d)
    out = Sim(params, seed, log).run()
    log.close()
    return out


def test_same_seed_gives_an_identical_run(tmp_path):
    for cond in ("rule_bees", "random_bees", "oracle_bees"):
        a = _run({**SMALL, "condition": cond}, 3, tmp_path / f"{cond}-a")
        b = _run({**SMALL, "condition": cond}, 3, tmp_path / f"{cond}-b")
        c = _run({**SMALL, "condition": cond}, 4, tmp_path / f"{cond}-c")
        assert a == b and _read(tmp_path / f"{cond}-a") == _read(tmp_path / f"{cond}-b")
        assert _read(tmp_path / f"{cond}-a") != _read(tmp_path / f"{cond}-c")


def test_full_run_directory_matches_the_log_format_and_stays_small(tmp_path):
    d = tmp_path / "full"
    summary = _run({"condition": "random_bees"}, 0, d)
    layout = json.loads((d / "layout.json").read_text())
    assert layout["format"] == 1 and layout["ticks"] == 2000 and len(layout["rows"]) == layout["height"] == 48
    assert all(len(r) == 80 for r in layout["rows"]) and len(layout["entrances"]) == 3
    state, events, metrics = _read(d)
    lines = state.splitlines()
    assert len(lines) == 2000
    first = json.loads(lines[0])
    assert set(first) == {"t", "s", "y", "b", "h", "snd"}
    assert all(len(b) == len(layout["bee_fields"]) for b in first["b"])
    assert all(len(h) == len(layout["hornet_fields"]) for h in first["h"])
    assert len(metrics.splitlines()) == 8
    kinds = {json.loads(e)["kind"] for e in events.splitlines()}
    assert {"season", "hatch", "decision", "trip", "death", "hornet_spawn", "end"} <= kinds
    size = sum(f.stat().st_size for f in d.iterdir())
    assert size < 5_000_000, size
    assert summary["trips"] > 0
