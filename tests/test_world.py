import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from digital_life.world import ENTRANCE, HIVE, Calendar, generate  # noqa: E402


def test_generation_is_deterministic():
    a, b = generate(80, 48, 7), generate(80, 48, 7)
    assert a.rows() == b.rows() and a.bloom == b.bloom and a.entrances == b.entrances
    assert generate(80, 48, 8).rows() != a.rows()


def test_hive_has_three_entrances_and_hornets_cannot_enter():
    w = generate(80, 48, 3)
    assert len(w.entrances) == 3
    assert all(w.code(*e) == ENTRANCE for e in w.entrances)
    hive = [(x, y) for y in range(w.height) for x in range(w.width) if w.code(x, y) in (HIVE, ENTRANCE)]
    assert len(hive) == 6 * 8 + 3
    assert not any(w.open_for_hornet(*c) for c in hive)
    assert w.in_hive(*w.home)


def test_every_open_cell_and_bloom_is_reachable_from_home():
    w = generate(80, 48, 5, min_bloom_distance=55)
    reach = w.distances(w.home)
    open_cells = [(x, y) for y in range(w.height) for x in range(w.width) if w.open_for_bee(x, y)]
    assert all(c in reach for c in open_cells)
    assert set(w.bloom) == {"spring", "summer", "autumn"}
    for cells in w.bloom.values():
        assert len(cells) == 9 and all(c[0] >= w.width // 2 for c in cells)
    assert min(w.bloom_distance.values()) >= 40


def test_entrances_connect_to_the_maze():
    w = generate(40, 24, 2, min_bloom_distance=20)
    for ex, ey in w.entrances:
        assert any(w.open_for_hornet(ex + dx, ey + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def test_calendar():
    c = Calendar(season_length=250, years=2)
    assert c.ticks == 2000
    assert [c.season_name(t) for t in (0, 249, 250, 500, 750, 999, 1000)] == ["spring", "spring", "summer", "autumn", "winter", "winter", "spring"]
    assert c.year(999) == 0 and c.year(1000) == 1
