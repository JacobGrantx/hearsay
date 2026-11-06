"""Wall time per tick with and without the shared decision clock, using the tests' fake model with a fixed delay.

A speed check for round 2, not a result: the fake mind's replies stand in for the model, and each call sleeps
--latency seconds (the pilot's real calls ran in parallel, so a tick costs about one call's latency when any bee
decides). Usage: .venv/bin/python tools/clock_timing.py [--ticks 250] [--latency 0.5]
"""
import argparse
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

from conftest import FakeMind  # noqa: E402

from digital_life import llm  # noqa: E402
from digital_life.mind import AIPolicy  # noqa: E402
from digital_life.sim import Sim  # noqa: E402

E5 = dict(condition="full", vocab="abstract", width=56, height=34, season_length=250, years=1, base_life=500,
          min_bloom_distance=38, hornet_spawn_distance=18, hornet_counts=[2, 3, 4, 0], log_state=False,
          steady_hatch=60, mind_workers=6)


class SlowMind(FakeMind):
    def __init__(self, latency):
        super().__init__()
        self.latency = latency

    def create(self, **kw):
        time.sleep(self.latency)
        return super().create(**kw)


def timed(ticks: int, latency: float, shared: bool) -> dict:
    params = {**E5, "shared_clock": shared, "stop_after": ticks}
    sim = Sim(params, 0, None, policy=AIPolicy(params, 0, client=SlowMind(latency)))
    counts = {"decision_ticks": 0, "calls": 0}
    decide = sim.policy.decide_many

    def counted(perceptions):
        counts["decision_ticks"] += 1
        counts["calls"] += len(perceptions)
        return decide(perceptions)
    sim.policy.decide_many = counted
    t0 = time.perf_counter()
    while sim.t < ticks:
        sim.tick()
    return {"shared_clock": shared, "ticks": ticks, "seconds": round(time.perf_counter() - t0, 2),
            "s_per_tick": round((time.perf_counter() - t0) / ticks, 3), **counts, "bees_at_end": len(sim.bees)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=250)
    ap.add_argument("--latency", type=float, default=0.5)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="dl-clock-", dir="/dev/shm") as d:
        llm.CACHE_DIR, llm.SPEND_FILE = Path(d) / "cache", Path(d) / "spend.json"
        for shared in (False, True):
            print(timed(a.ticks, a.latency, shared), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
