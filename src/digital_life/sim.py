"""The tick loop. Entry point for experiments/run.py: run(params, seed, log) -> run summary.

Order within a tick: season change, senses, decisions (one policy call for every bee due), bee moves
(with bloom pickup, delivery, heal and hatch on arrival), hornet moves, stings, life drain and deaths,
queen floor, hornet evolution, then the state line. Sounds made this tick are heard next tick.
"""
from __future__ import annotations

import random

from . import bees as B
from .hornets import Swarm
from .metrics import SeasonMetrics, summarise
from .motor import KnownMap, step
from .perception import TRIGGERS
from .policies import make_policy
from .simlog import SimLog
from .world import Calendar, generate

DEFAULTS = dict(
    condition="rule_bees", policy=None, width=80, height=48, season_length=250, years=2,
    openness=0.15, rooms=4, min_bloom_distance=55, bloom_spread=1.5,
    base_life=500, life_cap_factor=3, max_bees=12, start_bees=6, queen_floor=2, decide_every=5,
    sound_cost=1, newborn_hold=3, hornet_counts=[4, 6, 8, 0], evolve_every=25, mutation=0.5,
    sting_cooldown=10, hornet_spawn_distance=25, ambush_rate=0.02, ambush_wait=4, hornet_speed=0.8, smell_base=2.0, smell_step=1.0, log_state=True, log_decisions=True)
CONDITION_POLICY = {"rule_bees": "rule", "random_bees": "random", "oracle_bees": "oracle",
                    "full": "ai", "no_talk": "ai", "no_memory": "ai", "labels_good_bad": "ai", "frozen_hornets": "ai"}
PRIORITY = ("stung", "hornet", "bloom", "sound", "home", "arrived", "life25", "life50", "hatched", "timer")
assert set(PRIORITY) == set(TRIGGERS)


class Sim:
    def __init__(self, params: dict, seed: int, log=None, policy=None):
        p = self.p = {**DEFAULTS, **params}
        self.seed = seed
        self.world = generate(p["width"], p["height"], seed, openness=p["openness"], rooms=p["rooms"],
                              min_bloom_distance=p["min_bloom_distance"], bloom_spread=p["bloom_spread"])
        self.cal = Calendar(p["season_length"], p["years"])
        self.rng = random.Random(f"bees:{seed}")
        self.swarm = Swarm(self.world, random.Random(f"hornets:{seed}"), frozen=p["condition"] == "frozen_hornets",
                           mutation=p["mutation"], counts=tuple(p["hornet_counts"]), evolve_every=p["evolve_every"],
                           spawn_distance=p["hornet_spawn_distance"], cooldown=p["sting_cooldown"],
                           ambush_rate=p["ambush_rate"], ambush_wait=p["ambush_wait"], speed=p["hornet_speed"],
                           smell_base=p["smell_base"], smell_step=p["smell_step"])
        self.L, self.cap = p["base_life"], p["base_life"] * p["life_cap_factor"]
        self.bees: dict[int, B.Bee] = {}
        self.next_bee, self.t, self.sounds = 0, 0, []
        self.hive_cells = sorted((x, y) for y in range(self.world.height) for x in range(self.world.width)
                                 if self.world.in_hive(x, y))
        self.km_proto = KnownMap(self.world.width, self.world.height, self.world.home)
        self.out = SimLog(log, state=p["log_state"], decisions=p["log_decisions"])
        self.out.layout(self.world, self.cal, p, seed, (B.VISION, B.BLOOM_VISION, B.HEARING))
        name = p["policy"] or CONDITION_POLICY.get(p["condition"])
        self.policy = policy or make_policy(name, random.Random(f"policy:{seed}"), params=p, seed=seed,
                                            bloom_now=lambda: self.world.bloom_now(self.cal.season(self.t)))
        if hasattr(self.policy, "bind"):  # the AI mind needs the tick for its cache tag and the log for errors
            self.policy.bind(lambda: self.t, self.out.event)
        self.metrics = SeasonMetrics()

    # --- colony -----------------------------------------------------------------------------------
    def hatch(self, cause: str) -> B.Bee:
        x, y = self.hive_cells[self.rng.randrange(len(self.hive_cells))]
        bee = B.Bee(self.next_bee, x, y, float(self.L), self.t, self.km_proto.blank(), hold=self.p["newborn_hold"])
        bee.triggers.append("hatched")
        self.bees[bee.id] = bee
        self.next_bee += 1
        if cause == "queen":
            self.metrics.queen_hatches += 1
            self.out.event("queen_hatch", self.t, bee=bee.id, x=x, y=y, life=bee.life)
        else:
            self.metrics.hatches += cause == "delivery"
            self.out.event("hatch", self.t, bee=bee.id, x=x, y=y, life=bee.life, cause=cause)
        return bee

    def band(self, life: float) -> int:
        return 2 if life > self.L / 2 else 1 if life > self.L / 4 else 0

    def end_trip(self, bee: B.Bee, delivered: bool, outcome: str) -> None:
        if bee.trip is None:
            return
        tr, bee.trip = bee.trip, None
        reached = None if tr["bloom"] is None else tr["bloom"] - tr["start"]
        if reached is not None:
            self.metrics.to_bloom.append(reached)
        self.metrics.trips_ended += 1
        self.metrics.trips_delivered += delivered
        self.out.event("trip", self.t, bee=bee.id, start=tr["start"], ticks=self.t - tr["start"], delivered=delivered,
                       reached_bloom=reached, stings=tr["stings"], outcome=outcome)

    # --- one tick ---------------------------------------------------------------------------------
    def tick(self) -> None:
        t, cal, world, p = self.t, self.cal, self.world, self.p
        season, year = cal.season(t), cal.year(t)
        if t % cal.season_length == 0:
            self.metrics.start(t, season, year)
            self.out.event("season", t, season=cal.season_name(t), year=year)
            if season == 3:
                self.out.event("hornet_dormant", t, hornets=[[h.id, *h.genes, round(h.fitness, 4)] for h in self.swarm.active])
            for h in self.swarm.season_start(season, year):
                self.out.event("hornet_spawn", t, hornet=h.id, x=h.x, y=h.y, genes=h.genes, parent=h.parent)
        if t == 0:
            for _ in range(p["start_bees"]):
                self.hatch("start")
        bloom = world.bloom_now(season)
        bloom_set = set(bloom)
        order = sorted(self.bees.values(), key=lambda b: b.id)

        # senses and decisions
        others = [(b.id, b.x, b.y) for b in order]
        hornets = [(h.id, h.x, h.y) for h in self.swarm.active]
        for b in order:
            B.sense(b, world, t, others, hornets, bloom, self.sounds)
            if t - b.last_decided >= p["decide_every"]:
                b.triggers.append("timer")
        due = [b for b in order if b.triggers]
        decisions = self.policy.decide_many([B.perceive(b, t, min(b.triggers, key=PRIORITY.index)) for b in due]) if due else []
        sounds_now, in_hive = [], [b for b in order if world.in_hive(b.x, b.y)]
        for b, d in zip(due, decisions):
            trig = min(b.triggers, key=PRIORITY.index)
            b.decision, b.labelled, b.last_decided, b.triggers, b.unseen = d, d.label(), t, [], []
            self.out.event("decision", t, bee=b.id, trigger=trig, intent=d.intent, direction=d.direction,
                           target=list(d.target) if d.target else None, sound=d.sound, remember=d.remember, say=d.say,
                           **d.info)
            if d.sound != "none":
                b.life -= p["sound_cost"]
                sounds_now.append((b.id, b.x, b.y, d.sound))
                self.metrics.sounds[d.sound] += 1
            if d.say and p["condition"] != "no_talk" and world.in_hive(b.x, b.y):
                heard_by = [o.id for o in in_hive if o.id != b.id]
                for o in in_hive:
                    if o.id != b.id:
                        o.heard.append((t, b.id, d.say))
                self.out.event("say", t, bee=b.id, text=d.say, heard_by=heard_by)

        # bee moves
        for b in order:
            if b.stunned > 0:
                b.stunned -= 1
                continue
            if b.hold > 0:
                b.hold -= 1
                continue
            was_in = world.in_hive(b.x, b.y)
            (nx, ny), status = step(b.km, b.pos, b.decision, b.motor, b.hornets_seen)
            assert world.open_for_bee(nx, ny), "motor stepped into a wall"
            if status in ("arrived", "blocked") and b.motor_status not in ("arrived", "blocked"):
                b.triggers.append("arrived")
            b.x, b.y, b.motor_status = nx, ny, status
            now_in = world.in_hive(nx, ny)
            if was_in and not now_in:
                b.trip, b.life_left_home = {"start": t, "stings": 0, "bloom": None}, b.life
                self.metrics.trips += 1
            if not b.carrying and (nx, ny) in bloom_set:
                b.carrying = True
                if b.trip is not None and b.trip["bloom"] is None:
                    b.trip["bloom"] = t
                B.note(b, t, "picked_up")
                self.out.event("bloom", t, bee=b.id, x=nx, y=ny)
            if now_in and not was_in:
                b.triggers.append("home")
                got = B.deliver(b, self.cap)
                if got:
                    self.metrics.delivery(t)
                    B.note(b, t, "delivered")
                    self.out.event("delivery", t, bee=b.id, life_before=round(got[0], 1), life_after=round(got[1], 1))
                    if len(self.bees) < p["max_bees"]:
                        self.hatch("delivery")
                amount = B.heal(b, self.cap) if b.stung_loss > 0 else 0
                if amount:
                    self.out.event("heal", t, bee=b.id, amount=round(amount, 1), life_after=round(b.life, 1))
                self.end_trip(b, bool(got), "home")

        # hornets and stings
        outside = [(b.id, b.x, b.y, b.life) for b in order if not world.in_hive(b.x, b.y)]
        self.swarm.move(outside, [(x, y) for _, x, y, _ in self.sounds], bloom, t)
        for h, bid in self.swarm.stings(outside, t):
            b = self.bees[bid]
            before = self.band(b.life)
            amount = B.sting(b)
            self.swarm.reward(h, amount, b.pos)
            self.metrics.sting(amount)
            if b.trip is not None:
                b.trip["stings"] += 1
            b.triggers.append("stung")
            B.note(b, t, "stung", at=list(b.pos))
            self.out.event("sting", t, hornet=h.id, bee=b.id, x=b.x, y=b.y, amount=amount, life_after=round(b.life, 1))
            if self.band(b.life) < before:
                b.triggers.append("life25" if self.band(b.life) == 0 else "life50")

        # life drain, deaths, queen floor, evolution
        for b in order:
            before = self.band(b.life)
            B.drain(b, season == 3, world.in_hive(b.x, b.y))
            if b.life <= 0:
                self.end_trip(b, False, "died")
                del self.bees[b.id]
                self.policy.bee_died(b.id)
                self.metrics.deaths += 1
                self.out.event("death", t, bee=b.id, x=b.x, y=b.y, age=t - b.born, cause="life")
            elif self.band(b.life) < before:
                b.triggers.append("life25" if self.band(b.life) == 0 else "life50")
        while len(self.bees) < p["queen_floor"]:
            self.hatch("queen")
        if season != 3 and (t + 1) % p["evolve_every"] == 0:
            ev = self.swarm.evolve()
            if ev:
                self.out.event("hornet_replaced", t, **ev)
        alive = sorted(self.bees.values(), key=lambda b: b.id)
        self.metrics.sizes.append(len(alive))
        self.out.state(t, season, year, alive, self.swarm.active, sounds_now)
        if (t + 1) % cal.season_length == 0:
            self.out.metric(self.metrics.end(t, self.swarm.active))
        self.sounds = sounds_now
        self.t += 1

    def run(self) -> dict:
        while self.t < self.cal.ticks:
            self.tick()
        self.out.event("end", self.t, bees_alive=len(self.bees))
        self.out.close()
        return summarise(self.metrics.rows, self.world)


def run(params: dict, seed: int, log) -> dict:
    return Sim(params, seed, log).run()
