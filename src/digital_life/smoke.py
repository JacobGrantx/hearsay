"""Pipeline self-test: a tiny seeded random-walk population.

This is not the project. It exists so `make smoke` and the tests can prove the
runner, seeding and logging work end to end before the real system exists.
"""
from __future__ import annotations

import random


def run(params: dict, seed: int, log) -> dict:
    rng = random.Random(seed)
    n, steps = int(params.get("population", 20)), int(params.get("steps", 50))
    pos = [0.0] * n
    for step in range(steps):
        pos = [p + rng.gauss(0, 1) for p in pos]
        mean = sum(pos) / n
        log.metric(step, mean_position=mean, spread=max(pos) - min(pos))
    log.event("finished", steps=steps)
    return {"final_mean": sum(pos) / n, "final_spread": max(pos) - min(pos)}
