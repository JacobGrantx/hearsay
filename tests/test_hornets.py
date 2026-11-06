import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_life.hornets import POINTS, Swarm, mutate, random_genome  # noqa: E402
from digital_life.sim import Sim  # noqa: E402
from digital_life.world import generate  # noqa: E402

SMALL = dict(width=40, height=24, season_length=60, years=2, min_bloom_distance=20, log_state=False)


def test_genomes_always_hold_ten_points():
    rng = random.Random(1)
    g = random_genome(rng)
    for _ in range(500):
        g = mutate(g, rng, p=1.0)
        assert sum(g) == POINTS and min(g) >= 0


def test_evolution_changes_genes_and_frozen_does_not():
    w = generate(40, 24, 0, min_bloom_distance=20)
    for frozen in (False, True):
        s = Swarm(w, random.Random(3), frozen=frozen, mutation=1.0)
        s.season_start(0, 0)
        before = sorted(map(tuple, (h.genes for h in s.active)))
        reward = random.Random(9)
        for _ in range(20):
            for h in s.active:
                h.ticks += 25
                h.removed += reward.choice((0, 50, 100))
            s.evolve()
        after = sorted(map(tuple, (h.genes for h in s.active)))
        assert (after != before) is (not frozen)
        assert (s.next_id > 4) is (not frozen)


def test_frozen_hornets_keep_the_initial_draw_across_years():
    sim = Sim({**SMALL, "condition": "frozen_hornets", "policy": "rule"}, 4)
    pool = [list(g) for g in sim.swarm.pool]
    seen = set()
    while sim.t < sim.cal.ticks:
        sim.tick()
        seen.update(tuple(h.genes) for h in sim.swarm.active)
    assert seen <= set(map(tuple, pool))


def test_same_seed_draws_the_same_initial_genomes_in_both_conditions():
    a = Sim({**SMALL, "condition": "frozen_hornets", "policy": "rule"}, 5).swarm.pool
    b = Sim({**SMALL, "condition": "rule_bees"}, 5).swarm.pool
    assert a == b


def test_hornets_never_enter_hive_cells_and_sleep_in_winter():
    sim = Sim({**SMALL, "condition": "random_bees"}, 2)
    while sim.t < sim.cal.ticks:
        sim.tick()
        assert not any(sim.world.in_hive(h.x, h.y) for h in sim.swarm.active)
        assert all(sim.world.open_for_hornet(h.x, h.y) for h in sim.swarm.active)
        if sim.cal.season(sim.t - 1) == 3:
            assert sim.swarm.active == []
