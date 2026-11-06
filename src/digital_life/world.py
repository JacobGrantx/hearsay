"""The world: a braided maze, the hive at the left edge, three seasonal bloom patches, and the calendar.

The grid is a flat bytearray, index y * width + x. Cell codes: OPEN, WALL, HIVE (hive interior) and
ENTRANCE. Entrances are hive cells too: hornets never stand on either. Everything is generated from the
seed, so the same seed always gives the same layout.
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

SEASONS = ("spring", "summer", "autumn", "winter")
OPEN, WALL, HIVE, ENTRANCE = 0, 1, 2, 3
DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
CHARS = ".#HE"


@dataclass(frozen=True)
class Calendar:
    season_length: int = 250
    years: int = 2

    @property
    def ticks(self) -> int:
        return 4 * self.season_length * self.years

    def season(self, t: int) -> int:
        return (t // self.season_length) % 4

    def year(self, t: int) -> int:
        return t // (4 * self.season_length)

    def season_name(self, t: int) -> str:
        return SEASONS[self.season(t)]


@dataclass
class World:
    width: int
    height: int
    grid: bytearray
    home: tuple[int, int]
    entrances: list[tuple[int, int]]
    bloom: dict[str, list[tuple[int, int]]]
    bloom_distance: dict[str, int]

    def code(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y * self.width + x]
        return WALL

    def open_for_bee(self, x: int, y: int) -> bool:
        return self.code(x, y) != WALL

    def open_for_hornet(self, x: int, y: int) -> bool:
        return self.code(x, y) == OPEN

    def in_hive(self, x: int, y: int) -> bool:
        return self.code(x, y) in (HIVE, ENTRANCE)

    def bloom_now(self, season: int) -> list[tuple[int, int]]:
        return self.bloom.get(SEASONS[season], [])

    def rows(self) -> list[str]:
        w = self.width
        return ["".join(CHARS[c] for c in self.grid[y * w:(y + 1) * w]) for y in range(self.height)]

    def distances(self, start: tuple[int, int], *, hornet: bool = False, max_depth: int | None = None) -> dict:
        """Shortest path length from start to every reachable cell (BFS on the true map)."""
        ok = self.open_for_hornet if hornet else self.open_for_bee
        dist = {start: 0}
        q = deque([start])
        while q:
            x, y = q.popleft()
            d = dist[(x, y)]
            if max_depth is not None and d >= max_depth:
                continue
            for dx, dy in DIRS4:
                n = (x + dx, y + dy)
                if n not in dist and ok(*n):
                    dist[n] = d + 1
                    q.append(n)
        return dist


def generate(width: int = 80, height: int = 48, seed: int = 0, *, openness: float = 0.15, rooms: int = 4,
             min_bloom_distance: int = 40, bloom_spread: float = 1.5, hive_w: int = 6, hive_h: int = 8) -> World:
    """Build the maze from the seed. `openness` is the chance that each remaining inner wall is knocked through
    (loops). Each bloom patch's centre lies between `min_bloom_distance` and `bloom_spread` times that, in path
    steps from home, so the distance knob sets how hard the bloom is to find."""
    rng = random.Random(f"world:{seed}")
    grid = bytearray([WALL]) * (width * height)

    def setc(x, y, c):
        grid[y * width + x] = c

    def getc(x, y):
        return grid[y * width + x]

    y0 = (height - hive_h) // 2
    reserved = lambda x, y: x <= hive_w + 2 and y0 - 2 <= y <= y0 + hive_h + 1  # noqa: E731
    cells = [(x, y) for y in range(1, height - 1, 2) for x in range(1, width - 1, 2) if not reserved(x, y)]
    cellset = set(cells)

    # 1. Spanning maze by randomized depth-first search over the odd-coordinate lattice.
    start = cells[rng.randrange(len(cells))]
    setc(*start, OPEN)
    seen, stack = {start}, [start]
    while stack:
        x, y = stack[-1]
        nbrs = [(x + 2 * dx, y + 2 * dy) for dx, dy in DIRS4 if (x + 2 * dx, y + 2 * dy) in cellset and (x + 2 * dx, y + 2 * dy) not in seen]
        if not nbrs:
            stack.pop()
            continue
        nx, ny = nbrs[rng.randrange(len(nbrs))]
        setc((x + nx) // 2, (y + ny) // 2, OPEN)
        setc(nx, ny, OPEN)
        seen.add((nx, ny))
        stack.append((nx, ny))

    # 2. Rooms: open rectangles on the lattice, away from the hive.
    for _ in range(rooms):
        rw, rh = rng.choice((2, 3)), rng.choice((2, 3))
        x0 = 1 + 2 * rng.randrange(max(1, (width - 3) // 2 - rw))
        ry0 = 1 + 2 * rng.randrange(max(1, (height - 3) // 2 - rh))
        if any(reserved(x, y) for x in (x0, x0 + 2 * rw) for y in (ry0, ry0 + 2 * rh)):
            continue
        for y in range(ry0, min(height - 1, ry0 + 2 * rh + 1)):
            for x in range(x0, min(width - 1, x0 + 2 * rw + 1)):
                setc(x, y, OPEN)

    # 3. Braid: knock through a share of the remaining walls between two lattice cells, making loops.
    for (x, y) in cells:
        for dx, dy in ((1, 0), (0, 1)):
            if (x + 2 * dx, y + 2 * dy) in cellset and getc(x + dx, y + dy) == WALL and rng.random() < openness:
                setc(x + dx, y + dy, OPEN)

    # 4. The hive: an open room at the left edge, walled, with three entrances (right, top, bottom).
    for y in range(y0, y0 + hive_h):
        for x in range(1, hive_w + 1):
            setc(x, y, HIVE)
    mid_x = (hive_w + 1) // 2
    entrances = [(hive_w + 1, y0 + hive_h // 2), (mid_x, y0 - 1), (mid_x, y0 + hive_h)]
    for (ex, ey), (dx, dy) in zip(entrances, ((1, 0), (0, -1), (0, 1))):
        setc(ex, ey, ENTRANCE)
        x, y = ex, ey
        while 0 < x + dx < width - 1 and 0 < y + dy < height - 1:
            x, y = x + dx, y + dy
            setc(x, y, OPEN)
            if any(getc(x + ax, y + ay) == OPEN for ax, ay in DIRS4 if (ax, ay) != (-dx, -dy)):
                break
    home = ((hive_w + 1) // 2, y0 + hive_h // 2)

    world = World(width, height, grid, home, entrances, {}, {})
    # 5. Anything not connected to home is filled in, so every open cell is reachable.
    reach = world.distances(home)
    for y in range(height):
        for x in range(width):
            if getc(x, y) != WALL and (x, y) not in reach:
                setc(x, y, WALL)

    # 6. Bloom: three 3 x 3 patches in the right half, far enough from home, apart from each other.
    # If the band is too narrow for this maze, widen its upper end rather than fail.
    sep = max(6, width // 8)
    picked: list[tuple[int, int]] = []
    for spread in (bloom_spread, 2.0, 3.0, 1e9):
        cands = sorted(c for c in cellset if c in reach and c[0] >= width // 2 and 2 <= c[0] <= width - 3
                       and 2 <= c[1] <= height - 3 and min_bloom_distance + 2 <= reach[c] <= spread * min_bloom_distance + 2)
        rng.shuffle(cands)
        picked = []
        for c in cands:
            if all(max(abs(c[0] - p[0]), abs(c[1] - p[1])) >= sep for p in picked):
                picked.append(c)
            if len(picked) == 3:
                break
        if len(picked) == 3:
            break
    if len(picked) < 3:
        raise ValueError(f"cannot place 3 bloom patches at path distance >= {min_bloom_distance} (seed {seed})")
    for season, (cx, cy) in zip(SEASONS[:3], picked):
        world.bloom[season] = [(cx + dx, cy + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
        for x, y in world.bloom[season]:
            setc(x, y, OPEN)
    reach = world.distances(home)
    world.bloom_distance = {s: min(reach[c] for c in cs) for s, cs in world.bloom.items()}
    return world
