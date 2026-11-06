"""The AI bee mind: a Policy that asks a language model what each bee does next.

Per decision: store what happened since the bee last decided as episodes, recall the most useful ones,
render the Perception as neutral text, call digital_life.llm.complete with structured output, parse the
reply into a Decision and store any `remember` note. The calls of one tick run in parallel, but memory is
read before and written after them in the sim's fixed bee-id order, so a replayed run is identical.

A model error, a refusal or a malformed reply makes the bee `wait` and is logged as a `mind_error` event.
A replay cache miss or the budget cap stops the run instead: those mean the run is not what it claims.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from . import llm
from .memory import BeeMemory
from .perception import Decision, Perception
from .policies import Policy
from .render import decision_schema, parse, render, sound_names, system_prompt

AI_CONDITIONS = ("full", "no_talk", "no_memory", "labels_good_bad", "frozen_hornets")
STOP = (llm.CacheMiss, llm.BudgetExceeded)


class AIPolicy(Policy):
    name = "ai"

    def __init__(self, params: dict, seed: int, client=None):
        self.condition = params.get("condition", "full")
        self.seed, self.client = seed, client
        self.model = params.get("mind_model", "claude-haiku-5-5")
        self.effort = params.get("mind_effort", "low")
        self.max_tokens = params.get("mind_max_tokens", 400)
        self.retries = params.get("mind_retries", 2)
        self.memory_on, self.talk_on = self.condition != "no_memory", self.condition != "no_talk"
        self.names = sound_names(self.condition)
        self.system = system_prompt(self.condition, params.get("width", 80), params.get("height", 48))
        self.schema = decision_schema(self.condition)
        self.pool = ThreadPoolExecutor(max_workers=params.get("mind_workers", 16))
        self.mem: dict[int, BeeMemory] = {}
        self.last: dict[int, int] = {}
        self.clock = lambda: 0
        self.emit = lambda kind, t, **data: None

    def bind(self, clock, emit) -> None:
        """Called by the sim: the current tick (for the cache tag) and its event log (for mind_error)."""
        self.clock, self.emit = clock, emit

    def prompt(self, p: Perception, tick: int) -> str:
        since = tick - self.last.get(p.bee_id, tick)
        notes, recalled = [], []
        if self.memory_on:
            mem = self.mem.setdefault(p.bee_id, BeeMemory())
            mem.observe(p, tick, self.names)
            notes, recalled = mem.notes(tick), mem.recall(p, tick)
        return render(p, self.names, memory=self.memory_on, talk=self.talk_on, notes=notes, recalled=recalled, since=since)

    def call(self, bee_id: int, tick: int, text: str) -> llm.Completion:
        for attempt in range(self.retries + 1):
            try:
                return llm.complete(text, system=self.system, model=self.model, max_tokens=self.max_tokens,
                                    effort=self.effort, tag=f"{self.seed}:{tick}:{bee_id}:{self.condition}",
                                    schema=self.schema, thinking={"type": "disabled"}, client=self.client)
            except STOP:
                raise
            except Exception:
                if attempt == self.retries:
                    raise
                time.sleep(2 ** attempt)

    def decide_many(self, perceptions: list[Perception]) -> list[Decision]:
        tick = self.clock()
        prompts = [self.prompt(p, tick) for p in perceptions]
        futures = [self.pool.submit(self.call, p.bee_id, tick, text) for p, text in zip(perceptions, prompts)]
        return [self.finish(p, tick, f) for p, f in zip(perceptions, futures)]

    def finish(self, p: Perception, tick: int, future) -> Decision:
        try:
            c = future.result()
        except STOP:
            raise
        except Exception as e:
            self.emit("mind_error", tick, bee=p.bee_id, error=f"{type(e).__name__}: {str(e)[:200]}")
            self.last[p.bee_id] = tick
            return Decision("wait", info={"fallback": "error"})
        try:
            if c.stop_reason == "refusal":
                raise ValueError("refusal")
            d = parse(c.text, self.condition, p.grid_size)
        except (ValueError, TypeError, KeyError) as e:
            self.emit("mind_error", tick, bee=p.bee_id, error=f"{type(e).__name__}: {str(e)[:200]}",
                      stop_reason=c.stop_reason, prompt_key=c.key[:12])
            d = Decision("wait", info={"fallback": "parse"})
        d.info.update(usage={k: c.usage.get(k, 0) for k in ("input_tokens", "output_tokens")}, prompt_key=c.key[:12],
                      ctx={"movers": len(p.hornets_seen), "bright": len(p.bloom_seen), "carrying": int(p.carrying), "home": int(p.at_home)})
        if self.memory_on and d.remember:
            self.mem[p.bee_id].remember(tick, d.remember)
        self.last[p.bee_id] = tick
        return d

    def bee_died(self, bee_id: int) -> None:
        self.mem.pop(bee_id, None)
        self.last.pop(bee_id, None)
