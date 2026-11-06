"""Motor layer (no AI): turns a bee's intent into one step, using only that bee's own known map.

KnownMap holds what the bee has seen: unknown, open, wall or home. Route planning is A* over it, with
unknown cells counted as passable; a route is replanned as soon as a wall turns up on it. `explore`
heads for the nearest frontier (a known open cell beside an unknown one) within 50 degrees of the chosen
direction. `flee` steps to maximise distance from the hornets the bee can see. Nothing here reads the World.
"""
from __future__ import annotations

import heapq
import math
from collections import deque
from dataclasses import dataclass, field

from .perception import DIR_VEC, DIRECTIONS, Decision, direction_of

UNKNOWN, KOPEN, KWALL, KHIVE = 0, 1, 2, 3
DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
CONE_COS = math.cos(math.radians(50))


class KnownMap:
    def __init__(self, width: int, height: int, home: tuple[int, int]):
        self.w, self.h, self.home = width, height, home
        self.cells = bytearray(width * height)
        self.known = [0] * 8
        self.total = [0] * 8
        self.octant = bytearray(width * height)
        hx, hy = home
        for y in range(height):
            for x in range(width):
                o = DIRECTIONS.index(direction_of(x - hx, y - hy)) if (x, y) != home else 0
                self.octant[y * width + x] = o
                self.total[o] += 1

    def blank(self) -> "KnownMap":
        """An empty map of the same size, sharing the per-direction tables."""
        k = KnownMap.__new__(KnownMap)
        k.w, k.h, k.home, k.octant, k.total = self.w, self.h, self.home, self.octant, self.total
        k.cells, k.known = bytearray(self.w * self.h), [0] * 8
        return k

    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.cells[y * self.w + x]
        return KWALL

    def learn(self, x: int, y: int, kind: int) -> bool:
        i = y * self.w + x
        if self.cells[i] == UNKNOWN:
            self.cells[i] = kind
            self.known[self.octant[i]] += 1
            return True
        return False

    def passable(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h and self.cells[y * self.w + x] != KWALL

    def walkable_known(self, x: int, y: int) -> bool:
        return self.get(x, y) in (KOPEN, KHIVE)

    def frontier(self, x: int, y: int) -> bool:
        return self.walkable_known(x, y) and any(
            0 <= x + dx < self.w and 0 <= y + dy < self.h and self.cells[(y + dy) * self.w + x + dx] == UNKNOWN for dx, dy in DIRS4)

    def explored(self) -> dict[str, float]:
        return {d: round(self.known[i] / self.total[i], 3) if self.total[i] else 1.0 for i, d in enumerate(DIRECTIONS)}


@dataclass
class MotorState:
    key: str | None = None
    goal: tuple[int, int] | None = None
    path: list = field(default_factory=list)  # remaining route, next cell last


def astar(km: KnownMap, start, goal, max_nodes: int = 6000):
    """Shortest route on the known map, unknown cells passable. Returns cells goal-first (pop() = next)."""
    if start == goal:
        return []
    gx, gy = goal
    came, cost = {start: None}, {start: 0}
    heap = [(abs(start[0] - gx) + abs(start[1] - gy), 0, start)]
    expanded = 0
    while heap:
        _, neg_g, c = heapq.heappop(heap)
        if c == goal:
            path = []
            while c != start:
                path.append(c)
                c = came[c]
            return path
        g = -neg_g
        if g > cost[c]:
            continue
        expanded += 1
        if expanded > max_nodes:
            return None
        for dx, dy in DIRS4:
            n = (c[0] + dx, c[1] + dy)
            if km.passable(*n) and g + 1 < cost.get(n, 1 << 30):
                cost[n], came[n] = g + 1, c
                heapq.heappush(heap, (g + 1 + abs(n[0] - gx) + abs(n[1] - gy), -(g + 1), n))
    return None


def find_frontier(km: KnownMap, start, direction: str, max_nodes: int = 4000):
    """Nearest frontier cell (by route over known cells) inside the 50-degree cone of `direction`."""
    vx, vy = DIR_VEC[direction]
    vlen = math.hypot(vx, vy)
    came = {start: None}
    q = deque([start])
    while q and len(came) < max_nodes:
        c = q.popleft()
        if c != start:
            dx, dy = c[0] - start[0], c[1] - start[1]
            if dx * vx + dy * vy >= CONE_COS * math.hypot(dx, dy) * vlen and km.frontier(*c):
                path = []
                while c != start:
                    path.append(c)
                    c = came[c]
                return path[0], path
        for dx, dy in DIRS4:
            n = (c[0] + dx, c[1] + dy)
            if n not in came and km.walkable_known(*n):
                came[n] = c
                q.append(n)
    return None


def flee_step(km: KnownMap, pos, hornets):
    """The cell (staying put included) that maximises the nearest seen hornet's distance; ties go homeward."""
    opts = [pos] + [(pos[0] + dx, pos[1] + dy) for dx, dy in DIRS4 if km.walkable_known(pos[0] + dx, pos[1] + dy)]
    hx, hy = km.home
    return max(opts, key=lambda c: (min(abs(c[0] - a) + abs(c[1] - b) for a, b in hornets),
                                    -(abs(c[0] - hx) + abs(c[1] - hy)), c))


def step(km: KnownMap, pos, d: Decision, ms: MotorState, hornets_seen) -> tuple[tuple[int, int], str]:
    """One step for the intent. Returns (next cell, status): moving, arrived, blocked or idle."""
    if d.intent == "wait":
        return pos, "idle"
    if d.intent == "flee":
        if not hornets_seen:
            return pos, "arrived"
        return flee_step(km, pos, hornets_seen), "moving"
    label = d.label()
    if label != ms.key:
        ms.key, ms.goal, ms.path = label, None, []
    if d.intent == "go_home":
        if km.get(*pos) == KHIVE:
            return pos, "arrived"
        goal = km.home
    elif d.intent == "go_to":
        goal = tuple(d.target)
        if pos == goal:
            return pos, "arrived"
        if not km.passable(*goal):
            return pos, "blocked"
    else:  # explore
        if ms.goal is None or pos == ms.goal or not km.frontier(*ms.goal):
            found = find_frontier(km, pos, d.direction)
            if found is None:
                ms.goal, ms.path = None, []
                return pos, "arrived"
            ms.goal, ms.path = found
        goal = ms.goal
    if ms.goal != goal or not ms.path or any(km.get(*c) == KWALL for c in ms.path):
        ms.goal, ms.path = goal, astar(km, pos, goal) or []
        if not ms.path:
            return pos, "blocked"
    nxt = ms.path.pop()
    if abs(nxt[0] - pos[0]) + abs(nxt[1] - pos[1]) != 1:  # route no longer starts here (e.g. after a stun)
        ms.path = astar(km, pos, goal) or []
        if not ms.path:
            return pos, "blocked"
        nxt = ms.path.pop()
    return nxt, "moving"
