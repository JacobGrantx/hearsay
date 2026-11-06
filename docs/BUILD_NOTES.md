# Build notes (handoff between build phases)

Written by the phase 1 build session (Claude Code, 2026-11-06). Phase 1 is the world with no AI: layout, seasons, evolving hornets, scripted bees, logging, tests and calibration. Later phases plug the AI mind in through the policy interface below.

## Log format

Format version 1. Every seed of every run writes one run directory:

```
experiments/results/<experiment>/<UTC stamp>[_<tag>]/seed-<n>/
    record.json        written by experiments/run.py: params, seed, provenance, final_metrics (the run summary)
    layout.json        the world, written once before tick 0
    state.jsonl.gz     gzip-compressed JSONL, one line per tick: positions and state of everything
    events.jsonl       one line per event
    metrics.jsonl      one line per season
```

Coordinates are `[x, y]` with x to the right and y downward, 0-based. Moves are 4-neighbour.

### layout.json

```json
{
  "format": 1,
  "width": 80, "height": 48,
  "rows": ["#####...", "#HHH...", "..."],
  "home": [3, 23],
  "entrances": [[7, 22], [4, 19], [4, 28]],
  "bloom": {"spring": [[x, y], ...9 cells], "summer": [...], "autumn": [...]},
  "bloom_distance": {"spring": 61, "summer": 74, "autumn": 58},
  "season_names": ["spring", "summer", "autumn", "winter"],
  "season_length": 250, "years": 2, "ticks": 2000,
  "base_life": 250, "life_cap": 750, "max_bees": 12,
  "vision": 4, "bloom_vision": 6, "hearing": 10,
  "condition": "rule_bees", "seed": 0,
  "bee_fields": ["id", "x", "y", "life", "carrying", "stunned", "intent"],
  "hornet_fields": ["id", "x", "y", "smell", "hearing", "ambush", "target", "mode"],
  "sound_fields": ["bee", "x", "y", "sound"]
}
```

- `rows`: `height` strings of `width` characters. `#` wall, `.` open, `H` hive interior, `E` hive entrance. Entrances count as hive cells: hornets never stand on `H` or `E`.
- `home`: the hive's centre cell, the position every bee is told is home.
- `bloom`: the 3 x 3 patch for each season. Winter has none. The same cells bloom every year.
- `bloom_distance`: shortest path in steps from `home` to the nearest cell of each patch.

### state.jsonl.gz

One JSON object per tick, written after the tick has resolved:

```json
{"t": 0, "s": 0, "y": 0,
 "b": [[0, 3, 23, 249.0, 0, 0, "explore:NE"], ...],
 "h": [[0, 52, 11, 4, 3, 3, -1, "wander"], ...],
 "snd": [[2, 40, 18, "sound-1"]]}
```

- `t` tick (0-based), `s` season index (0 spring, 1 summer, 2 autumn, 3 winter), `y` year (0-based).
- `b`, one array per living bee, in `bee_fields` order: id, x, y, life (1 decimal), carrying (0 or 1), stunned (ticks of stun left, 0 if not stunned), intent.
  - intent is one of `explore:<dir>` (dir is N, NE, E, SE, S, SW, W or NW), `go_to:<x>,<y>`, `go_home`, `flee`, `wait`, or `""` before the bee's first decision.
- `h`, one array per hornet on the map, in `hornet_fields` order: id, x, y, the three genes, target (bee id, or -1), mode (`chase`, `sound`, `ambush` or `wander`). Empty in winter.
- `snd`, sounds made this tick: bee id, x, y, `sound-1` or `sound-2`. Other bees and hornets hear them on the next tick.

Read it in a browser with `new Response(blob.stream().pipeThrough(new DecompressionStream("gzip"))).text()`, then split on newlines.

### events.jsonl

One object per line. Every event has `kind` and `t`.

| kind | fields |
|---|---|
| `season` | season (name), year |
| `hatch` | bee, x, y, life, cause (`start` for the founding bees, `delivery` otherwise) |
| `queen_hatch` | bee, x, y, life |
| `decision` | bee, trigger, intent, direction, target, sound, remember, say. AI bees add `usage` ({input_tokens, output_tokens}), `prompt_key` (first 12 hex digits of the replay-cache key, so the exact prompt can be found in `experiments/llm_cache/`), `ctx` ({movers, bright, carrying, home}: moving things and bright cells in view, 0/1 flags) and, on a fallback, `fallback` (`error` or `parse`) |
| `mind_error` | bee, error, and for a bad reply stop_reason and prompt_key. The bee's decision that tick is `wait` |
| `say` | bee, text, heard_by (list of bee ids) |
| `bloom` | bee, x, y (the bee picked up from bloom and is now carrying) |
| `delivery` | bee, life_before, life_after |
| `heal` | bee, amount, life_after |
| `sting` | hornet, bee, x, y, amount, life_after |
| `death` | bee, x, y, age, cause (`life`: life reached 0) |
| `trip` | bee, start, ticks, delivered, reached_bloom (ticks from leaving to reaching bloom, or null), stings, outcome (`home` or `died`) |
| `hornet_spawn` | hornet, x, y, genes ([smell, hearing, ambush]), parent (hornet id or null) |
| `hornet_replaced` | removed, removed_fitness, parent, child, genes |
| `hornet_dormant` | hornets (list of [id, smell, hearing, ambush, fitness]) |
| `end` | bees_alive |

`decision.trigger` is one of `timer`, `stung`, `hornet`, `bloom`, `sound`, `arrived`, `home`, `life50`, `life25`, `hatched`. Decision `target` is `[x, y]` or null; `direction` is a direction string or null.

### metrics.jsonl

One row per season, written at the season's last tick (`step`):

| field | meaning |
|---|---|
| `step`, `year`, `season` | last tick of the season, year (0-based), season name |
| `trips` | trips that started this season (a trip starts when a bee steps out of the hive) |
| `trips_ended`, `trips_delivered` | trips that ended this season (home or death), and how many of those delivered |
| `deliveries` | deliveries this season |
| `delivery_rate` | trips_delivered / trips_ended, null if no trip ended. A trip counts in the season it ends. |
| `stings`, `stings_per_trip` | stings this season, and stings / trips_ended |
| `median_to_bloom` | median ticks from leaving the hive to reaching bloom, over trips that reached it; null if none |
| `first_delivery` | ticks after the season's start of its first delivery; null if none |
| `bees_end`, `bees_mean` | colony size at the season's end, and mean over its ticks |
| `hatches`, `queen_hatches`, `deaths` | counts this season |
| `sounds_1`, `sounds_2` | sounds made this season |
| `hornets`, `smell`, `hearing`, `ambush` | hornets on the map at the season's end, and their mean genes (null in winter) |
| `hornet_damage` | life removed by stings this season |

The run summary (`final_metrics` in record.json, and `per_seed` and `across_seeds` in summary.json) is a flat dict built by `metrics.summarise`: totals (`trips`, `deliveries`, `stings`, `delivery_rate`, `stings_per_trip`), the same per season name (`spring_rate`, `spring_trips`, `spring_stings_per_trip`, and so on, summed over both years), `first_delivery_y1_spring` and `first_delivery_y2_spring`, `median_to_bloom`, `hatches`, `queen_hatches`, `deaths`, `bees_mean`, `bees_final`, hornet gene means in the first and last season with hornets (`smell_first`, `smell_last`, ...), and `bloom_distance_<season>`. Null values are left out.

## Module map (src/digital_life/)

| Module | Owns |
|---|---|
| `world.py` | `generate()`: seeded braided maze (spanning DFS maze, rooms, walls knocked through at rate `openness`), the hive (6 x 8 at the left edge, entrances right, top and bottom), three 3 x 3 bloom patches in the right half whose centres lie between `min_bloom_distance` and 1.5 times that in path steps from home. `Calendar` for seasons and years. |
| `hornets.py` | `Swarm`: genome (10 points over smell, hearing and ambush), per-tick movement, stings with the per-pair cooldown, steady-state evolution every 25 ticks, season changes (4, 6, 8, 0 hornets; spring of year 2 bred from the fittest autumn hornets). |
| `bees.py` | `Bee` state; the life rules `drain`, `sting`, `heal`, `deliver`; `sense()` (the only bee-side code that reads the World) and `perceive()` (builds a Perception from the bee's own state). |
| `perception.py` | `Perception` and `Decision` dataclasses, direction and distance-band helpers. |
| `motor.py` | `KnownMap` (the bee's own map: unknown, open, wall, home), A* with unknown cells passable, frontier search for `explore`, `flee`, and `step()`. |
| `policies.py` | `Policy` base class and the scripted `RandomPolicy`, `RulePolicy`, `OraclePolicy`; `make_policy()`. |
| `sim.py` | `Sim` (the tick loop), `DEFAULTS` (every parameter and its calibrated value), `run(params, seed, log)` for experiments/run.py. |
| `metrics.py` | Per-season accumulators and the run summary. |
| `simlog.py` | Writes the run directory (layout.json, state.jsonl.gz, events through RunLog, metrics rows). |

Order inside one tick (`Sim.tick`): season change (hornets spawn or go dormant) → senses for every bee → one `policy.decide_many()` call for every bee due to decide → sounds and hive talk → bee moves (bloom pickup, then delivery, hatch and heal on entering the hive) → hornet moves → stings → life drain and deaths → queen floor → hornet evolution every 25 ticks outside winter → state line → season metrics row at the season's last tick. Sounds made in a tick are heard by bees and hornets on the next tick.

## Policy interface (where phase 2 plugs in the AI mind)

```python
class Policy:
    def decide_many(self, perceptions: list[Perception]) -> list[Decision]: ...  # one call per tick
    def bee_died(self, bee_id: int) -> None: ...                                 # optional clean-up
```

- Pass the mind in with `Sim(params, seed, log, policy=MyMind(...))`, or register a name in `policies.make_policy` and set `policy = "<name>"` in the config's params (any condition except the three scripted ones reads `params["policy"]`). sim.py needs no change.
- `decide_many` gets every due bee at once, so the AI mind can run the model calls for one tick in parallel.
- A bee decides when it hatches, every `decide_every` (5) ticks, and immediately on: stung, newly sees a hornet, bloom comes into view, hears a sound, the motor reports arrived or blocked, enters the hive, life falls below 50% or 25% of base life L. `Perception.trigger` is the most urgent one (order: stung, hornet, bloom, sound, home, arrived, life25, life50, hatched, timer).
- Memory belongs to the mind. The sim keeps only the bee's short-term events (the last 8), the events since its last decision, the last 6 things heard at home, and its known map. Episodes, beliefs (`remember`) and recall are for phase 2 to keep per bee id. `Decision.remember` is only logged by the sim.
- Hive talk: a `say` from a bee inside the hive goes to every other bee inside the hive that tick (into its `heard_at_home`), except under `condition = "no_talk"`. `say` is cut to 30 words.
- Sounds cost 1 life each (`sound_cost`).

## Perception fields

| Field | Content |
|---|---|
| `bee_id`, `trigger` | who is deciding and why now |
| `position`, `home`, `grid_size` | own cell, the hive centre, map size |
| `life`, `carrying`, `at_home`, `stunned` | own state (life rounded to 1 decimal; stunned = ticks left) |
| `view` | 9 strings of 9 symbols centred on the bee: `#` wall, `.` open, `H` home, `*` bloom, `b` other bee, `x` hornet, `@` self, space for off the map |
| `bees_seen`, `hornets_seen` | absolute cells within vision 4 (square) |
| `bloom_seen` | this season's bloom cells within 6 (square) |
| `sounds` | `(sound, direction, band)` heard this tick within 10 (Euclidean); band is near (<= 3), mid (<= 6) or far |
| `recent_events`, `new_events` | the last 8 events, and all events since the previous decision: dicts with `what` (`saw_mover`, `saw_bright`, `heard`, `picked_up`, `delivered`, `stung`) and `ago` in ticks |
| `heard_at_home` | `(ago, speaker id, text)`, newest last, up to 6 |
| `bloom_remembered`, `hornets_remembered` | `(x, y, ago)`: bloom cells this bee has seen in its life, and its last 6 hornet sightings |
| `explored` | share of cells known in each of 8 directions from home |
| `intent`, `motor_status` | current intent label; `moving`, `arrived`, `blocked` or `idle` |
| `life_when_left_home` | life when the bee last stepped out of the hive |

Field names are code, not prompt text. Phase 2 renders them with neutral words (the no-hints test applies to the prompt and its templates). Under `no_memory`, phase 2 should decide which of `recent_events`, `bloom_remembered`, `hornets_remembered` and `heard_at_home` count as memory and drop them in its rendering.

## Phase 2: the AI bee mind

Written by the phase 2 build session (Claude Code, 2026-11-06).

| Module or file | Owns |
|---|---|
| `prompts/bee_system.txt` | The system prompt template. Placeholders: grid size, the two sound names, and the parts that `no_memory` and `no_talk` remove. |
| `render.py` | Every fixed piece of prompt text (`SYSTEM_PARTS`, `TRIGGER_TEXT`, `EVENT_TEXT`, ...), `system_prompt(condition, w, h)`, `render(perception, ...)` (the user message), `decision_schema(condition)` and `parse(reply)`. |
| `memory.py` | `BeeMemory` per bee: episodes with importance (sting 5, delivery 5, bloom seen or touched 4, hornet seen 3, talk heard at home 2, sound heard 1), up to 12 beliefs, recall of the top 6 by recency + importance + BM25. |
| `mind.py` | `AIPolicy`: renders prompts in bee-id order, runs the calls of one tick in a thread pool (16), applies replies in bee-id order, falls back to `wait` on failure. Registered as policy `ai`; conditions `full`, `no_talk`, `no_memory`, `labels_good_bad` and `frozen_hornets` use it by default. |

- **Model settings** come from params: `mind_model` (claude-haiku-5-5), `mind_effort` (low), `mind_max_tokens` (400), `mind_retries` (2), `mind_workers` (16). Thinking is always disabled. The cache tag is `f"{seed}:{tick}:{bee_id}:{condition}"`.
- **The sim binds the mind** after the log exists: `policy.bind(clock, emit)` gives it the tick (for the tag) and the event log (for `mind_error`). It never gets the World.
- **Replay:** with `LLM_MODE=replay` a run whose calls are all cached is identical, file for file (tests/test_mind_conditions.py). Decision events log token counts but not cost or the cached flag, which differ between a live run and its replay.
- **`stop_after`** ends a run early at that tick (pilot runs). The world rules are unchanged.
- **Configs:** `full`, `no_talk`, `no_memory`, `labels_good_bad`, `frozen_hornets` (full size, seeds 0 to 2), and `pilot_full_spring` (first spring of seed 0).
- **Tests (no network, fake client in tests/conftest.py):** `test_mind_prompt.py` (no banned words in the system prompt, templates, schema or any rendered prompt; no prompt holds a bloom or hornet coordinate the bee never had in range or heard at home, with a check that the test catches an injected leak), `test_mind_conditions.py` (replay identity, what each condition removes, fallbacks), `test_memory.py`.

## Conditions in phase 1

`rule_bees`, `random_bees` and `oracle_bees` run now. `frozen_hornets` is wired (no evolution; the hornets use the seed's initial draw of 8 genomes in every season and year), and `no_talk` blocks hive talk in the sim. `full`, `no_memory` and `labels_good_bad` need the AI mind; with a scripted `policy` they run but are not meaningful. The seed gives the same layout and the same initial hornet genomes in every condition.

## Calibration (summary; full table in EXPERIMENTS.md, "Setup calibration")

Final values: base life L = 500, `min_bloom_distance` = 55, `openness` = 0.15, plus hornet constants the spec left open: `ambush_rate` = 0.02, `ambush_wait` = 4, `hornet_speed` = 0.8, smell range 2 + smell gene. At that point, over 3 seeds, the spring delivery rate (trips that delivered / trips that ended in spring) is 0.708 for oracle bees, 0.024 for rule bees and 0.000 for random bees.

## Changes from the spec (agent proposals awaiting Jacob, also in DECISIONS.md)

1. **No chasing during the sting cooldown.** A hornet does not pursue a bee it stung until the 10-tick cooldown ends. Without this, a hornet moving at bee speed followed its victim and stung every 10 ticks until it died, which is the lock the cooldown was meant to prevent.
2. **Hornets move on 80% of ticks** (`hornet_speed`). At equal speed a fleeing bee could never gain distance, so `flee` was useless.
3. **Ambush rate.** A free hornet heads for an ambush spot with probability 0.02 x ambush/10 per tick and waits 4 x ambush ticks there. Choosing every tick sent all hornets to camp on the bloom.
4. **Base life L = 500** (spec start value 250). At 250, oracle bees delivered on 0.524 of spring trips (sd 0.272), and one sting near the bloom usually meant death on the way home.
5. **Bees inside the hive cannot be stung** (entrances included). The spec says hornets cannot enter hive cells but not whether they can sting across the boundary.
6. **`explore` falls back to 90 degrees.** If no frontier lies within 50 degrees of the chosen direction, the bee takes the nearest frontier within 90 degrees; if there is none, the motor reports `arrived`.
7. **Oracle flee reflex.** The calibration-only oracle flees when a hornet is within 3 cells.
8. **Life thresholds** (the 50% and 25% decision triggers) are fractions of base life L, since life can rise to 3L.
9. **`min_bloom_distance` is a band.** Patch centres lie between the minimum and 1.5 times it (widened if the maze has too few such cells), so the knob sets difficulty rather than only a floor. On the full map, distances under about 45 cannot be placed in the right half.

## Known issues and notes for the later phases

- The world is hard: even oracle bees average about 1.2 stings per spring trip, and every scripted colony falls to the 2-bee queen floor for long stretches (mean colony size 2.5 to 4.3). Hornets learn to wait at their old sting spots, which are on the bees' route home. An AI colony that avoids those spots, or warns others, has room to do better than the oracle on stings.
- Hornet evolution is fast. In two exploratory runs (oracle bees, seeds 0 and 1, not recorded), all four spring hornets shared one genome by the end of the first spring (10 replacements per 250 ticks).
- Spring delivery rates are noisy across 3 seeds (oracle sd 0.191). Use 5 seeds for anything in the README.
- Scripted bees ignore winter (rule bees keep exploring and die outside at 2 life per tick). That is expected and part of the baseline.
- Baseline run directories for E1 (`rule_bees`, `random_bees`, 5 seeds each) are not committed yet. Run them at the same commit as the AI runs: about 6 s per seed.
- Calibration result directories hold no state file (`log_state = false`) and no decision events, to keep them small. A full 2,000-tick run directory is about 300 KB.
- The test suite takes about 15 to 30 s; the leak and determinism tests run whole small worlds.

## Known issues after phase 2 (for the main runs)

- **Sounds are almost never made.** In the pilot, 1 of 355 decisions made a sound (EXPERIMENTS.md, "Pilot"). Nothing was changed, since the cost is a world rule and the prompt states it truthfully. If the main runs look the same, E4 is a pre-registered negative result. Whether to test a free-sound variant is Jacob's call, and it would be a new arm, not a fix.
- **Run time and cost.** The pilot spring took 166 s and $0.0856. Projected: about 22 minutes and $0.70 per 2,000-tick run, so run the 15 AI runs in parallel processes (one config per process; the runner runs a config's seeds one after another). The thread pool allows 16 calls at once per process; 40 concurrent calls were tested without rate-limit errors.
- **Replay cache size.** About 7 KB per call, so the main runs would add roughly 300 MB. Compress the cache entries (in `llm.py`, keeping old entries readable) before the main runs, or keep only the cited runs' entries.
- **Notes churn.** Bees write a note at every decision, so the 12 notes cover about the last 60 ticks.
- **API errors are not cached.** A live run where a call failed after its retries replays with a cache miss at that call. None occurred in the pilot. If one does in a main run, re-run that seed.
- **`make demo`** still runs rule bees only. The spec also wants it to replay one recorded AI run; the pilot (`pilot_full_spring.toml`, seed 0) replays offline with `LLM_MODE=replay` (checked: identical files) and could be that run.

## Phase 4: main runs, analysis, docs

Written by the phase 4 build session (Claude Code, 2026-11-06).

- **Main runs** at commit 9cb4e7a, from a clean git worktree on /dev/shm, one process per arm with its own cache folder (`LLM_CACHE_DIR`) and spend ledger (`LLM_SPEND_FILE`), so later commits could not touch a running experiment. Run directories, model health and spend: EXPERIMENTS.md, "Main runs: shared setup".
- **Replay cache** is packed per run: `tools/pack_llm_cache.py <seed dir> --source <loose cache>` writes `experiments/llm_cache/<arm>_<stamp>_seed-<n>.jsonl.gz`, and `llm.py` reads packs in auto and replay mode (it indexes every pack on first use). The pilot's entries stay loose.
- **Replay check:** `make replay RUN=<seed dir>` (experiments/replay_check.py). `make demo` replays `full` seed 0.
- **Analysis:** `make analysis`. `experiments/analysis/runs.py` names the main batch (`MAIN_STAMP`) and the amendment-1 batches (`EXTENSIONS`); `DL_RESULTS` points it at another results folder.
- **For the video:** the README still is `viewer/capture.py` on `full` seed 0 at tick 1053 following bee 9 (the winter forager, EXPERIMENTS.md E3). Other moments worth showing: the "Bright cells near (41,29) still dangerous" talk in `full` seed 0 (tick 214), and the one "bad noise" in `labels_good_bad` seed 2 (tick 1026).
