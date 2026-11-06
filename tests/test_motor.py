import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_life import motor as M  # noqa: E402
from digital_life.perception import Decision  # noqa: E402
from digital_life.sim import Sim  # noqa: E402

SMALL = dict(width=40, height=24, season_length=60, years=1, min_bloom_distance=20, log_state=False)


def open_map(w=20, h=10):
    km = M.KnownMap(w, h, (1, 5))
    for x in range(w):
        km.learn(x, 0, M.KWALL)
        km.learn(x, h - 1, M.KWALL)
    return km


def test_astar_routes_through_unknown_cells_as_if_open():
    # The bee knows only the borders. A true wall it has not seen cannot affect the plan.
    km = open_map()
    path = M.astar(km, (1, 5), (18, 5))
    assert path is not None and len(path) == 17
    assert all(c[1] == 5 for c in path)  # straight through the unknown middle


def test_astar_replans_around_a_known_wall():
    km = open_map()
    for y in range(1, 8):
        km.learn(10, y, M.KWALL)
    path = M.astar(km, (1, 5), (18, 5))
    assert (10, 8) in path and not any(km.get(*c) == M.KWALL for c in path)


def test_explore_targets_a_frontier_in_the_chosen_direction():
    km = open_map()
    for y in range(1, 9):
        for x in range(0, 6):
            km.learn(x, y, M.KOPEN)
    goal, path = M.find_frontier(km, (2, 5), "E")
    assert goal[0] == 5 and km.frontier(*goal)
    assert M.find_frontier(km, (2, 5), "W") is None  # nothing unknown to the west


def test_flee_moves_away_from_the_hornet():
    km = open_map()
    for y in range(1, 9):
        for x in range(20):
            km.learn(x, y, M.KOPEN)
    ms = M.MotorState()
    nxt, status = M.step(km, (10, 5), Decision("flee"), ms, [(11, 5)])
    assert status == "moving" and nxt == (9, 5)


def test_bees_only_ever_step_onto_cells_they_have_seen():
    for cond in ("rule_bees", "random_bees", "oracle_bees"):
        sim = Sim({**SMALL, "condition": cond}, 1)
        real_step = M.step
        checked = []

        def spy(km, pos, d, ms, hornets):
            nxt, status = real_step(km, pos, d, ms, hornets)
            assert km.get(*nxt) in (M.KOPEN, M.KHIVE), f"{cond}: stepped onto an unseen cell {nxt}"
            checked.append(nxt)
            return nxt, status

        import digital_life.sim as S
        S.step = spy
        try:
            sim.run()
        finally:
            S.step = real_step
        assert len(checked) > 500
