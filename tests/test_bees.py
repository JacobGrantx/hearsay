import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_life import bees as B  # noqa: E402
from digital_life.hornets import Hornet, Swarm  # noqa: E402
from digital_life.motor import KnownMap  # noqa: E402
from digital_life.sim import Sim  # noqa: E402
from digital_life.world import generate  # noqa: E402

SMALL = dict(width=40, height=24, season_length=60, years=1, min_bloom_distance=20, log_state=False)


def bee(life=200.0):
    return B.Bee(0, 10, 10, life, 0, KnownMap(40, 24, (3, 12)))


def test_sting_halves_life_rounded_down_and_stuns_for_two_ticks():
    b = bee(201.0)
    assert B.sting(b) == 100
    assert b.life == 101.0 and b.stunned == 2 and b.stung_loss == 100


def test_sting_cooldown_is_ten_ticks_per_hornet_and_bee():
    w = generate(40, 24, 0, min_bloom_distance=20)
    s = Swarm(w, random.Random(0), cooldown=10)
    h = Hornet(0, 20, 10, [4, 3, 3])
    s.active = [h]
    near = [(7, 21, 10, 100.0)]
    assert [b for _, b in s.stings(near, t=5)] == [7]
    assert s.stings(near, t=14) == []
    assert [b for _, b in s.stings(near, t=15)] == [7]


def test_stunned_bee_does_not_move_for_two_ticks():
    sim = Sim(SMALL, 0)
    sim.tick()
    b = next(iter(sim.bees.values()))
    b.hold, b.stunned = 0, 2
    start = b.pos
    sim.tick()
    sim.tick()
    assert b.pos == start and b.stunned == 0


def test_heal_once_per_life():
    b = bee(200.0)
    B.sting(b)
    B.sting(b)  # lost 100 + 50
    assert B.heal(b, 750) == 75 and b.life == 125
    B.sting(b)
    assert B.heal(b, 750) == 0


def test_delivery_doubles_life_capped_at_three_times_base():
    b = bee(200.0)
    assert B.deliver(b, 750) is None
    b.carrying = True
    assert B.deliver(b, 750) == (200.0, 400.0) and not b.carrying
    b.carrying = True
    B.deliver(b, 750)
    assert b.life == 750


def test_winter_drain_rates():
    b = bee(100.0)
    B.drain(b, winter=False, in_hive=False)
    assert b.life == 99
    B.drain(b, winter=True, in_hive=False)
    assert b.life == 97
    B.drain(b, winter=True, in_hive=True)
    assert b.life == 96.5


def _deliver_once(sim, carrying_bee):
    carrying_bee.carrying = True
    carrying_bee.hold = 0
    ex, ey = sim.world.entrances[0]
    carrying_bee.x, carrying_bee.y = ex + 1, ey  # just outside the right entrance
    from digital_life.perception import Decision
    carrying_bee.decision = Decision("go_home")
    carrying_bee.last_decided = sim.t
    sim.tick()


def test_hatch_only_below_the_cap():
    sim = Sim({**SMALL, "max_bees": 7}, 0)
    sim.tick()
    assert len(sim.bees) == 6
    _deliver_once(sim, sim.bees[0])
    assert len(sim.bees) == 7
    _deliver_once(sim, sim.bees[1])
    assert len(sim.bees) == 7


def test_queen_floor_hatches_up_to_two():
    sim = Sim(SMALL, 0)
    sim.tick()
    for b in list(sim.bees.values())[:5]:
        b.life = 0.5
    sim.tick()
    assert len(sim.bees) == 2
    assert sim.metrics.queen_hatches == 1
