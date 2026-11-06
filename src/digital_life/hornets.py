"""Hornets: no AI. A 10-point genome over smell, hearing and ambush, steady-state evolution on sting reward.

Genes to behaviour:
    smell s    detects bees within Manhattan distance smell_base + smell_step * s
    hearing h  hears bee sounds within 2 * h cells (Euclidean) and follows one with probability h / 10
    ambush a   when free, each tick with probability ambush_rate * a / 10 heads for a spot where it stung
               before or a bloom cell, and waits there for ambush_wait * a ticks
Hornets path on the true map (they are part of the environment) and never enter hive cells. They move
on a share `speed` of ticks (bees move every tick).
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from .world import DIRS4, World

GENES = ("smell", "hearing", "ambush")
POINTS = 10


def random_genome(rng) -> list[int]:
    g = [0, 0, 0]
    for _ in range(POINTS):
        g[rng.randrange(3)] += 1
    return g


def mutate(genes: list[int], rng, p: float = 0.5) -> list[int]:
    """With probability p, one point moves from one gene to another."""
    g = list(genes)
    if rng.random() < p:
        src = rng.choice([i for i in range(3) if g[i] > 0])
        dst = rng.choice([i for i in range(3) if i != src])
        g[src] -= 1
        g[dst] += 1
    return g


@dataclass
class Hornet:
    id: int
    x: int
    y: int
    genes: list[int]
    parent: int | None = None
    removed: float = 0.0
    ticks: int = 0
    target: int = -1
    mode: str = "wander"
    goal: tuple[int, int] | None = None
    goal_ttl: int = 0
    waited: int = 0
    heading: tuple[int, int] = (1, 0)
    spots: list = field(default_factory=list)

    @property
    def fitness(self) -> float:
        return self.removed / max(1, self.ticks)


    @property
    def hearing_range(self) -> int:
        return 2 * self.genes[1]


def step_toward(world: World, start: tuple[int, int], goal: tuple[int, int], max_depth: int):
    """First step of a shortest hornet path from start to goal (or to a cell next to it), or None."""
    if start == goal:
        return None
    prev = {start: None}
    q = deque([(start, 0)])
    while q:
        c, d = q.popleft()
        if c == goal or (abs(c[0] - goal[0]) + abs(c[1] - goal[1]) == 1 and not world.open_for_hornet(*goal)):
            while prev[c] != start and prev[c] is not None:
                c = prev[c]
            return c if c != start else None
        if d >= max_depth:
            continue
        for dx, dy in DIRS4:
            n = (c[0] + dx, c[1] + dy)
            if n not in prev and world.open_for_hornet(*n):
                prev[n] = c
                q.append((n, d + 1))
    return None


class Swarm:
    def __init__(self, world: World, rng, *, frozen: bool = False, mutation: float = 0.5,
                 counts=(4, 6, 8, 0), evolve_every: int = 25, spawn_distance: int = 25, cooldown: int = 10,
                 ambush_rate: float = 0.05, ambush_wait: int = 4, speed: float = 0.8,
                 smell_base: float = 2.0, smell_step: float = 1.0):
        self.smell_base, self.smell_step = smell_base, smell_step
        self.ambush_rate, self.ambush_wait, self.speed = ambush_rate, ambush_wait, speed
        self.world, self.rng, self.frozen, self.mutation = world, rng, frozen, mutation
        self.counts, self.evolve_every, self.cooldown_ticks = counts, evolve_every, cooldown
        self.pool = [random_genome(rng) for _ in range(max(counts))]  # the initial draw; frozen hornets keep it
        dist = world.distances(world.home)
        self.spawn_cells = sorted(c for c, d in dist.items() if d >= spawn_distance and world.open_for_hornet(*c))
        self.active: list[Hornet] = []
        self.autumn: list[Hornet] = []
        self.next_id = 0
        self.cooldown: dict[tuple[int, int], int] = {}

    def _spawn(self, genes, parent=None) -> Hornet:
        x, y = self.spawn_cells[self.rng.randrange(len(self.spawn_cells))]
        h = Hornet(self.next_id, x, y, list(genes), parent, heading=DIRS4[self.rng.randrange(4)])
        self.next_id += 1
        self.active.append(h)
        return h

    def _pick_parent(self, pool: list[Hornet]) -> Hornet:
        total = sum(h.fitness for h in pool)
        if total <= 0:
            return pool[self.rng.randrange(len(pool))]
        r, acc = self.rng.random() * total, 0.0
        for h in pool:
            acc += h.fitness
            if acc >= r:
                return h
        return pool[-1]

    def season_start(self, season: int, year: int) -> list[Hornet]:
        """Bring hornets up to this season's count. Returns the new hornets. Winter makes them dormant."""
        if season == 3:
            self.autumn, self.active = list(self.active), []
            return []
        want, born = self.counts[season], []
        if season == 0 and year > 0:
            self.active = []
            parents = sorted(self.autumn, key=lambda h: (-h.fitness, h.id))[:want]
            for i in range(want):
                if self.frozen or not parents:
                    born.append(self._spawn(self.pool[i]))
                else:
                    p = parents[i % len(parents)]
                    born.append(self._spawn(mutate(p.genes, self.rng, self.mutation), p.id))
            return born
        while len(self.active) < want:
            i = len(self.active)
            if self.frozen or not self.active:
                born.append(self._spawn(self.pool[i]))
            else:
                p = self._pick_parent(self.active)
                born.append(self._spawn(mutate(p.genes, self.rng, self.mutation), p.id))
        return born

    def evolve(self) -> dict | None:
        """Replace the least fit hornet with a mutated copy of one chosen in proportion to fitness."""
        if self.frozen or len(self.active) < 2:
            return None
        worst = min(self.active, key=lambda h: (h.fitness, -h.ticks, h.id))
        self.active.remove(worst)
        parent = self._pick_parent(self.active)
        child = self._spawn(mutate(parent.genes, self.rng, self.mutation), parent.id)
        return {"removed": worst.id, "removed_fitness": round(worst.fitness, 4), "parent": parent.id,
                "child": child.id, "genes": child.genes, "x": child.x, "y": child.y}

    def move(self, bees: list[tuple[int, int, int, float]], sounds: list[tuple[int, int]], bloom: list[tuple[int, int]],
             t: int = 0) -> None:
        """One step for every hornet. bees: (id, x, y, life) for bees outside the hive; sounds: last tick's.
        A hornet does not pursue a bee it stung while the sting cooldown runs, so it cannot lock onto it."""
        rng, world = self.rng, self.world
        for h in self.active:
            h.ticks += 1
            if rng.random() >= self.speed:
                continue  # hornets are a little slower than bees, so a bee that flees can get away
            smell = self.smell_base + self.smell_step * h.genes[0]
            near = [b for b in bees if abs(b[1] - h.x) + abs(b[2] - h.y) <= smell
                    and self.cooldown.get((h.id, b[0]), -1) <= t]
            if near:
                tgt = next((b for b in near if b[0] == h.target), None)
                if tgt is None:
                    r, acc = rng.random() * sum(max(b[3], 1e-9) for b in near), 0.0
                    for tgt in near:
                        acc += max(tgt[3], 1e-9)
                        if acc >= r:
                            break
                h.target, h.mode, h.goal = tgt[0], "chase", None
                nxt = step_toward(world, (h.x, h.y), (tgt[1], tgt[2]), int(3 * smell) + 4)
                if nxt or abs(tgt[1] - h.x) + abs(tgt[2] - h.y) <= 1:
                    if nxt and abs(tgt[1] - h.x) + abs(tgt[2] - h.y) > 1:
                        h.x, h.y = nxt
                    continue
            h.target = -1
            heard = [s for s in sounds if math.dist(s, (h.x, h.y)) <= h.hearing_range]
            if heard and rng.random() < h.genes[1] / 10:
                h.goal = min(heard, key=lambda s: (math.dist(s, (h.x, h.y)), s))
                h.goal_ttl, h.mode = 2 * h.hearing_range, "sound"
            elif h.goal is None and rng.random() < self.ambush_rate * h.genes[2] / 10:
                spots = h.spots + ([bloom[rng.randrange(len(bloom))]] if bloom else [])
                if spots:
                    h.goal, h.goal_ttl, h.mode = spots[rng.randrange(len(spots))], 80, "ambush"
                    h.waited = 0
            if h.goal is not None:
                h.goal_ttl -= 1
                if (h.x, h.y) == h.goal and h.mode == "ambush" and h.waited < self.ambush_wait * h.genes[2]:
                    h.waited += 1
                    continue  # wait in ambush
                nxt = step_toward(world, (h.x, h.y), h.goal, 120) if (h.x, h.y) != h.goal else None
                if nxt is None or h.goal_ttl <= 0:
                    h.goal = None
                else:
                    h.x, h.y = nxt
                    continue
            self._wander(h)

    def _wander(self, h: Hornet) -> None:
        h.mode = "wander"
        opts = [d for d in DIRS4 if self.world.open_for_hornet(h.x + d[0], h.y + d[1])]
        if not opts:
            return
        ahead = [d for d in opts if d != (-h.heading[0], -h.heading[1])]
        if h.heading in opts and self.rng.random() < 0.8:
            d = h.heading
        else:
            d = (ahead or opts)[self.rng.randrange(len(ahead or opts))]
        h.heading = d
        h.x, h.y = h.x + d[0], h.y + d[1]

    def stings(self, bees: list[tuple[int, int, int, float]], t: int) -> list[tuple[Hornet, int]]:
        """Each hornet stings at most one adjacent bee outside the hive per tick, respecting the cooldown."""
        out = []
        for h in self.active:
            adj = [b for b in bees if abs(b[1] - h.x) + abs(b[2] - h.y) == 1 and self.cooldown.get((h.id, b[0]), -1) <= t]
            if not adj:
                continue
            b = next((b for b in adj if b[0] == h.target), max(adj, key=lambda b: (b[3], -b[0])))
            self.cooldown[(h.id, b[0])] = t + self.cooldown_ticks
            out.append((h, b[0]))
        return out

    def reward(self, h: Hornet, amount: float, where: tuple[int, int]) -> None:
        h.removed += amount
        h.spots = (h.spots + [where])[-3:]
