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

- **Main runs** at commit ec521ca, from a clean git worktree on /dev/shm, one process per arm with its own cache folder (`LLM_CACHE_DIR`) and spend ledger (`LLM_SPEND_FILE`), so later commits could not touch a running experiment. Run directories, model health and spend: EXPERIMENTS.md, "Main runs: shared setup".
- **Replay cache** is packed per run: `tools/pack_llm_cache.py <seed dir> --source <loose cache>` writes `experiments/llm_cache/<arm>_<stamp>_seed-<n>.jsonl.gz`, and `llm.py` reads packs in auto and replay mode (it indexes every pack on first use). The pilot's entries stay loose.
- **Replay check:** `make replay RUN=<seed dir>` (experiments/replay_check.py). `make demo` replays `full` seed 0.
- **Analysis:** `make analysis`. `experiments/analysis/runs.py` names the main batch (`MAIN_STAMP`) and the amendment-1 batches (`EXTENSIONS`); `DL_RESULTS` points it at another results folder.
- **For the video:** the README still is `viewer/capture.py` on `full` seed 0 at tick 1053 following bee 9 (the winter forager, EXPERIMENTS.md E3). Other moments worth showing: the "Bright cells near (41,29) still dangerous" talk in `full` seed 0 (tick 214), and the one "bad noise" in `labels_good_bad` seed 2 (tick 1026).

## Phase 4b: E5, a post-hoc follow-up

Written by the phase 4b build session (Claude Code, 2026-11-06). E5 asks whether talk at home carries knowledge once there is knowledge to carry. It is post hoc, motivated by E1 and E3; the main negative results stand as they are.

- **Diagnosis first:** `experiments/analysis/trip_diagnosis.py` (EXPERIMENTS.md, "Why trips failed"). In the main world, bees rarely found the bloom; once found, it mostly got home.
- **The E5 world** is the main world at scale s = 0.7: 56 x 34, `min_bloom_distance` 38, `hornet_spawn_distance` 18, `hornet_counts` [2, 3, 4, 0], 1 year. Chosen with scripted bees only (`calibrate_e5.toml`, EXPERIMENTS.md, "E5 world"). `min_bloom_distance` alone does nothing below 55 on the 80 x 48 map, because bloom must lie in the right half and the placer widens the band.
- **Runs:** `e5_full.toml` and `e5_no_talk.toml`, seeds 0 to 4, one process per seed (tags `s0` to `s4`, batch stamp `20261106T112913Z`), from a clean worktree at commit 15c2ca1 on /dev/shm, each with its own `LLM_CACHE_DIR`, `LLM_SPEND_FILE` and `LLM_BUDGET_USD` 0.90.
- **Analysis:** `experiments/analysis/e5_results.py` (also run by `make analysis`); `DL_E5_STAMP` picks another batch.
- **Packs:** E5 caches are packed with `tools/pack_llm_cache.py --order run` (entries by bee and tick), about half the size of key order. The main runs' packs are unchanged.
- **Result:** both E5 hypotheses unsupported (EXPERIMENTS.md, E5). Replay: `make replay RUN=experiments/results/e5_full/20261106T112913Z_s0/seed-0` (about 11 s); all 10 checked identical (experiments/analysis/output/replay_e5.log).

### E5 moments for the video

All in `e5_full` seed 0 (`experiments/results/e5_full/20261106T112913Z_s0/seed-0`), spring of year 1. Bundle with `viewer/bundle.py` (203 KB page); the 56 x 34 map renders as is. Still: `demo/screenshots/e5_full_seed0_t172_bee6.png` (tick 172, following bee 6).

| Ticks | Moment | Follow |
|---|---|---|
| 55 to 170 | **A first finder delivers.** Bee 4 picks up bloom at tick 60, carries it home and delivers at tick 166; bee 6 hatches from it the same tick. Bees 3, 0, 1 and 2 pick up at ticks 69, 70, 76 and 140 and deliver at 169, 170, 180 and 198 | bee 4 |
| 166 to 172 | **Hive talk passes the place.** Tick 167, bee 4 to bee 6: "Back home carrying a bright thing from around (36,3), found in the east. Members should know it is there. Waiting here to report." Tick 170, bee 3 to bee 7: "Bright spot seen near (37,3)". At tick 172 bee 6 notes "Heard the valuable thing was found near (37,3) in the east; explore east next" and repeats it at home | bee 6 |
| 172 to 330 | **A talk-informed bee delivers.** Bee 6 explores NE with (37,3) as its stated target, comes within sight of the bloom at tick 216, picks up at 224 and delivers at 330. Bee 7 does the same: sighting 218, pickup 226, delivery 332 | bee 6 (or 7) |
| any | **The control.** `e5_no_talk` seed 0 has the same maze, bloom and first hornets and made 3 deliveries in the year against `e5_full`'s 15; but over 5 seeds no_talk delivered more (8.2 against 5.2), so show it as "talk helped here, not in general" | |

The honest caption for the video: talk carried a place in one seed of five, and colonies with talk spent more time at home and gathered no more.

### Round 2 moments for the video

Written by the phase 7b session (Claude Code, 2026-11-06). All in `r2_b_full` seed 0 (`experiments/results/r2_b_full/20261106T165608Z_s0/seed-0`, abstract words, rule not told) unless named. Lines copied from `events.jsonl`.

| Ticks | Moment | Follow |
|---|---|---|
| 5 | **A broadcast that preceded a delivery.** Unit 2 says "Unit at (3,14) exploring north from zone O. Nothing notable yet. Will report any object sighting.", heard by units 0, 1, 3, 4 and 5. This is the last broadcast about G or O unit 3 heard before its delivery, so the pre-registered measure counts that delivery as talk-informed; the broadcast names only zone O, not G | unit 2, then unit 3 |
| 121 | **First sighting under abstract words.** Unit 7's first decision triggered by a K entity: intent `explore`, direction N, note "K entity seen at (5, 9) near zone O north passage". It keeps exploring; B_full units moved away or went to O at 0.1472 of first sightings (sd 0.0851, n 5) against 0.8929 in `r2_n_full` seed 0 (one seed, amendment 1) | unit 7 |
| 190 to 194 | **A deliberate delivery.** Unit 3 decides `go_home` at tick 190 (timer, flag F set) and delivers at tick 194; counter C goes 298 to 596. It never chooses go_to_O with F again in the 3 completed years: the H10 result in one unit | unit 3 |
| any | **The control.** `r2_a_full` seed 0, told the rule in one sentence, made 59 repeat choices (3 units) in 2 years; random bees made no delivery in 8 years | |

The honest caption: units never told what delivery does reached zone O with G, saw counter C double, and did not go back for more, in 5 of 5 seeds.

## Phase 5: the demo video and the final pass

Written by the phase 5 build session (Claude Code, 2026-11-06).

- **Fresh clone first.** `git clone` of origin main (commit 712e0a9) into /dev/shm, then `make setup` (35 s), `make test` (67 passed, 75 s) and `make demo` (10 s, ends `REPLAY IDENTICAL`). Nothing needed fixing. The video was rendered in that clone after pulling each later commit, and copied into the checkout.
- **Moments:** `experiments/analysis/find_moments.py` prints, for every cited `full`, `no_talk`, `e5_full` and `e5_no_talk` run, the first year-1 spring delivery, hatches from deliveries, caution at a first sighting before any sting, stings followed by talk at home, hive talk naming a place near a bloom, go_to targets at a patch that is out of season, colony size across each winter, and year-2 spring. In the main world every colony is at the 2-bee floor through both winters, so the winter and old-route moments come from `e5_full` seed 0.
- **Renderer:** `demo/video/` holds the storyboard (segments, run directories, ticks, captions), `cards.py` and `charts.py` (drawn from experiments/analysis/output/*.json), and `make_video.py`, which bundles each run with the project name, captures map segments with `viewer/capture.py` (two at a time), overlays captions with ffmpeg, concatenates everything at CRF 24 and writes `demo/recordings/SOURCES.md` and four stills. `make video` takes about 3 minutes on the build VM; `TITLE=` and `REPO=` override the title and the end card's repository line.
- **After a rename or the move to a public namespace:** run `make video TITLE="<name>" REPO="<public path>"` (or update the README H1 first, which is the default title) and commit the new demo.mp4, SOURCES.md and stills.

## Phase 6: abstract vocabulary

Written by the phase 6 build session (Claude Code, 2026-11-06). Jacob asked for names the model's real-world knowledge cannot use.

| Module or file | Owns |
|---|---|
| `src/digital_life/vocab.py` | `Vocab` and the two vocabularies, `NEUTRAL` (round 1, word for word) and `ABSTRACT`: system prompt file, the parts conditions remove, sound names, intents (model word to sim intent), schema keys for sound and say, view symbols, trigger, event, band, status and line templates. `get(name)`; `DEFAULT = "abstract"`. |
| `prompts/abstract_system.txt` | The abstract system prompt. `prompts/bee_system.txt` is unchanged and is the neutral one. |
| `render.py`, `memory.py`, `mind.py` | Take a `Vocab`. `AIPolicy` reads `params["vocab"]` (default abstract, also in `sim.DEFAULTS`). `parse` maps the reply back to the sim's terms, so events, state lines, metrics and the viewer use the same names under both. |
| `experiments/analysis/first_sighting.py` | First move at a hornet sighting before any sting, classified as away, toward, hold or home, for either vocabulary (abstract has no flee). `--until T` cuts a full run to its first T ticks. |

- **Choosing it:** `vocab = "abstract"` or `"neutral"` in a config's params. Every AI config must name it (tests/test_vocab.py), because `experiments/replay_check.py` reads a record without `vocab` as a round 1 run and replays it as neutral. The round 1 configs now say `vocab = "neutral"`. Checked: `e5_full` seed 0 replays identical after the change.
- **What the model sees under abstract:** units, zone O, counter C, flag F, G cells, K entities, signals A and B; intents explore, go_to, go_to_O, hold (no flee); schema keys `signal` and `broadcast`. Map symbols `#` `.` `O` `G` `U` `K` `@`. Wording that differs from Jacob's list, and why, is in DECISIONS.md (drain and delivery stated without numbers, no hatch message).
- **Tests:** `test_vocab.py` (55 banned stems with regular endings plus 13 irregular forms, over the abstract prompt, templates, schema and every prompt of two whole runs; exceptions listed in its docstring; no flee in the abstract schema; reply mapping; every AI config names its vocab). The round 1 no-hints test is unchanged and points at `NEUTRAL`. The leak test, the replay test and the condition tests run under both vocabularies. `make test`: 88 tests, all passing.
- **Viewer:** the bundle carries the run's vocab (from record.json; a missing one on an AI run means neutral), and the colony panel shows "Agents see: units, zone O, K entities, G cells, signals A and B." under the key. The README has the same line. Re-render the video only if a round 2 run goes in it.
- **Pilot:** `pilot_abstract_e5_spring.toml` (E5 world, `full`, seed 0, first spring), EXPERIMENTS.md "Pilot (phase 6)". 0 model errors; 194.3 s and $0.0832 for 251 ticks (0.774 s and $0.00033 per tick, 2,109 input tokens per decision). Ledger cap during the run: $9.49 (ledger $8.49 plus $1); ledger after: $8.5732.

### For round 2

- **Units find G but do not bring it back.** In the pilot all 6 units set flag F and none went to zone O (0 `go_to_O` decisions in 333). Several kept looking "for the hidden object". The abstract prompt says nothing about what flag F or zone O does; round 1's "carrying" and "home" may have carried that link. Whether to keep it that way (delivery becomes something to discover) or add one neutral fact is open for Jacob (DECISIONS.md). Either way, round 2 should run a full E5 year, since a spring is too short to see a chance delivery spread by broadcast.
- **First sightings changed form.** 4 units saw a K entity before any halving: 2 held, 2 kept exploring toward it, none moved away. Notes still read as caution ("holding to assess", "still a threat"). A pilot observation, n = 1 seed.
- **Rough cost of a full E5 year under abstract:** if the pilot's rate held, 1,000 ticks would take about 13 minutes and $0.33 per seed. Colony size changes the decision rate, so treat this as an order of magnitude.

## Round 2 runs

Written by the phase 7a session (Claude Code, 2026-11-06). Design, hypotheses and decision rules: EXPERIMENTS.md, "Round 2 (pre-registered ...)", committed as 5dec2ff before any round 2 AI run.

- **Code** (commit 9de87f7, all off by default, so round 1 configs replay unchanged): `shared_clock`, `steady_hatch`, `tell_reward` (render.REWARD_TOLD; abstract only; allowed by tests/test_vocab.py), `stop_wallclock_utc` (checked at season boundaries with an injectable clock; record.json gets `stopped_at_tick` and `stopped_reason`; `experiments/replay_check.py` replays a stopped run with `stop_after=<stopped_at_tick>` and the stop switched off). Tests: tests/test_round2.py. The in-flight cap is the existing `mind_workers`, set to 6 in the round 2 configs.
- **Shared clock timing** (`tools/clock_timing.py`, fake model sleeping 0.5 s per call, E5 world with steady hatching, 6 calls in flight, 250 ticks, seed 0): 0.916 s per tick with each unit on its own clock, 0.772 s with the shared clock. The fake mind triggers decisions on almost every tick (250 and 249 of 250 ticks had one), so this understates the gain with the real model, whose units decide less often.
- **Clone:** `/dev/shm/dl-r2`, a `git clone` of this checkout at 5dec2ff (`git_dirty` false; results are untracked, which the dirty check ignores). Python: this checkout's `.venv` (run.py puts the clone's `src` first on the path).
- **Launch** (16:56 UTC): one process per AI run, `LLM_CACHE_DIR=/dev/shm/dl-r2-cache/<config>_s<seed>`, `LLM_SPEND_FILE=<that folder>/spend.json`, `LLM_BUDGET_USD=4.15` each, so the ledger ($8.5732 at launch) plus 16 x $4.15 stays at or below $75. Command per run: `experiments/run.py experiments/configurations/<config>.toml --seeds <n> --tag s<n>`. Logs: `/dev/shm/dl-r2-logs/<config>_s<seed>.log`. PIDs: `/dev/shm/dl-r2-pids.txt`. Run directories: `/dev/shm/dl-r2/experiments/results/r2_{b_full,b_no_talk,a_full,n_full}/<stamp>_s<n>/seed-<n>`.
- **Scripted arms:** `r2_rule` and `r2_random`, seeds 0 to 2, run to the same stop (stamp 20261106T165720Z), plus the 2-year calibration (`--set years=2`, tag `calib2y`, stamp 20261106T165550Z). `round2.py` skips `calib` directories.
- **Progress:** `.venv/bin/python tools/round2_progress.py` (last tick, ticks per second, spend and calls per run, total run spend). In the first minutes all 16 runs stalled together for about a minute at a time and then went on, which looks like a shared API rate limit, not a fault: no `mind_error` events.
- **Stop rule:** each run ends at the first season boundary after 18:05 UTC and writes record.json with `stopped_at_tick`. A season takes a few minutes, so all should end by about 18:15 UTC. A run still going later can be killed; `round2.py` cuts it to its last completed season (seasons in metrics.jsonl).
- **Collect** (after every run has record.json): copy `/dev/shm/dl-r2/experiments/results/r2_*` into `experiments/results/`; pack each AI run's cache with `tools/pack_llm_cache.py <seed dir> --source /dev/shm/dl-r2-cache/<config>_s<n> --order run`; add each run's `spend.json` (usd and calls) to `.llm_spend.json`; then check one run per arm with `make replay RUN=<seed dir>`.
- **Analysis:** `.venv/bin/python experiments/analysis/round2.py` (default: `experiments/results`; `--results /dev/shm/dl-r2/experiments/results` reads the clone in place). Writes `experiments/analysis/output/round2.json` and prints each hypothesis's verdict under the pre-registered rule. Tested on the pilot and the E5 runs (`--arm B_full=e5_full --arm B_no_talk=e5_no_talk --arm A_full=pilot_abstract_e5_spring --arm N_full=e5_full`).
- **For the analysis phase:** repeat choices are counted per decision (a unit re-decides go_to_O every few ticks while flag F is set), so H10 uses whether any occur, and `units_with_repeat_choice` is the count to quote. Steady hatches log `hatch` with `cause` "steady" and are not counted in `hatches`. Under neutral words (N_full) the sim names are the same, so every measure applies; broadcasts "about G or O" only make sense in abstract arms, which is all H7 uses.
- **Ten-minute check (17:05:29 UTC, 9.4 minutes after launch):** total run spend $1.544 (ledger $8.5732 before), so about $0.16 a minute and about $12 more by 18:05; the $75 limit is far off, so no seeds were stopped. Ticks reached: 205 to 243 in B_full, A_full and N_full, 270 to 292 in B_no_talk (0.37 to 0.52 ticks per second per run). Calls finish in bursts: about 1,300 in 35 s, then none for about 85 s, every 2 minutes for all 16 runs together (cache file times), about 665 calls a minute overall. That is a shared rate limit at the model endpoint, not the code: there are no `mind_error` events. The per-run cap of 6 calls in flight does not bind.
- **Projection at that rate:** B_full about 1,700 ticks by 18:05, B_no_talk about 2,100, A_full and N_full about 1,600 to 1,900; colonies grow under steady hatching, so expect fewer. Most runs will complete 1 year; pairs are cut to the shorter run, so H8 (which needs 2) may not be testable. Stopping A_full and N_full seeds 1 and 2 would give the other 12 runs about a third more ticks each; that is Jacob's call, and is not done.
- **Collected (phase 7b, 18:09 UTC):** every AI run outside amendment 1 had record.json with `stopped_reason` "wallclock 2026-11-06T18:05:00Z"; no process was left running and none crashed. The four amendment-1 runs have no record.json (last ticks 275, 278, 290, 295). All `r2_*` directories copied into `experiments/results/` (`du`: 22 MB for the AI arms; 30 MB for `r2_rule` and `r2_random`, which include the 2-year calibration committed earlier); caches packed into `experiments/llm_cache/r2_*.jsonl.gz` (16 packs, 11 MB); spend files added to `.llm_spend.json` ($11.1510 over 50,092 calls). Analysis: `round2.py --exclude A_full:1 --exclude A_full:2 --exclude N_full:1 --exclude N_full:2`.
