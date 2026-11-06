# Spec: a bee colony against evolving hornets (working title)

Approved by Jacob Schoenberg on 2026-11-05. Numbers marked (tune) are starting values, calibrated with scripted bees before any AI run. Every calibration is recorded in EXPERIMENTS.md under "Setup calibration".

**Primary property: adaptation, at three speeds,** under seasonal change:
- individual memory, within one bee's life;
- colony knowledge passed on inside the hive, across bee generations;
- genetic evolution, in the hornets.

Supporting properties: persistence (knowledge outliving every bee that gained it), interaction (two sounds, talk inside the hive) and emergence (whether the sounds come to mean something).

## World

- **Grid:** 80 x 48 cells, 4-neighbour moves. Walls are generated from the seed as a braided maze: corridors, rooms and loops, with several routes between any two areas. The layout stays fixed for the whole run.
- **Hive:** a room at the left edge, about 6 x 8 inside, with 3 entrances. Hornets cannot enter hive cells.
- **Bloom sites:**
  - Three sites in the right half, one each for spring, summer and autumn. Each is a 3 x 3 patch, placed from the seed with a minimum path distance from the hive (tune).
  - The sites repeat every year, so year 2's spring bloom is where year 1's was.
- **Time:**
  - Ticks. Four seasons of 250 ticks each (spring, summer, autumn, winter), and 2 years, so 2,000 ticks per run. Both lengths are configurable; the demo uses a smaller map and one short year.
  - Seasons are never named to the bees. Bees only experience their effects.
- **Winter:**
  - There is no bloom.
  - A bee outside the hive loses 2 life per tick; inside, 0.5 per tick (fractions accumulate).
  - Hornets are dormant and off the map.

## Bees

- **Colony size:** at most 12 alive. The colony starts with 6.
- **Queen floor:** whenever fewer than 2 bees are alive, the queen (not an agent) hatches a blank bee in the hive. Logged as `queen_hatch`.
- **Life:** base L = 250 (tune). One unit is lost per tick, at winter rates in winter. A bee dies at 0.
- **Delivery:**
  - Reaching any bloom cell sets `carrying`.
  - Entering the hive while carrying doubles the bee's life, capped at 3 x L, and clears `carrying`.
  - If fewer than 12 bees are alive, a new bee hatches with life L and no memories.
- **Sting:**
  - A hornet adjacent to a bee (Manhattan distance 1) can sting it.
  - A sting removes half the bee's current life (rounded down) and stuns the bee for 2 ticks.
  - The same hornet cannot sting the same bee again for 10 ticks, so a bee can't be stung into a lock.
  - The hornet's reward is the life it removed.
- **Healing:** once per life, a stung bee that enters the hive recovers half of the life it lost to stings. This happens automatically.
- **Senses:**
  - Vision radius 4 (square): walls, open cells, other bees, hornets.
  - Bloom cells are visible from 6.
  - Sounds are heard within 10 (Euclidean), reported as which sound, an 8-way direction and a distance band.
  - Each bee knows its own position, its home's position, its life left and whether it is carrying.
- **Sounds:**
  - Two neutral sounds, `sound-1` and `sound-2`. Under the `labels_good_bad` condition they are called "good noise" and "bad noise".
  - A bee makes a sound as part of a decision, and it costs 1 extra life.

## Bee mind (AI)

- **Model:** `claude-haiku-5-5`, effort low, thinking disabled, structured output. All calls go through `digital_life.llm.complete` with `tag = f"{seed}:{tick}:{bee_id}:{condition}"`.
- **When a bee decides:** every 5 ticks, and immediately on an event:
  - it is stung;
  - it newly sees a hornet;
  - it sees bloom;
  - it hears a sound;
  - it arrives at its target;
  - it enters the hive;
  - its life crosses 50% or 25%.
- **Decision (schema):**
  - `intent`: one of `explore` (with an 8-way direction), `go_to` (with x, y), `go_home`, `flee` or `wait`;
  - `sound`: `none`, `sound-1` or `sound-2`;
  - `remember`: a short belief, or empty;
  - `say`: up to 30 words, used only inside the hive, and heard by every bee in the hive that tick.
- **Motor layer (no AI):** executes the intent using only that bee's own known map, meaning cells it has seen.
  - Movement uses A* over known cells. Unknown cells count as passable, and the route is replanned when a wall turns up.
  - `explore` heads for the nearest unexplored frontier in the chosen direction.
  - `flee` moves to maximise distance from the hornets the bee can see.
- **Neutral prompt:**
  - The system prompt lives in one file, `prompts/bee_system.txt`. It says only that:
    - your life is a number that falls each moment and ends at zero;
    - something worth finding exists in this place;
    - you are one of many identical members of your home;
    - here is what you can perceive and do.
  - It never mentions bees, hives, flowers, hornets, food, danger or seasons. The viewer draws bees and hornets; the model never hears those words.
- **Perception text:**
  - own position, home position, life left, carrying;
  - the local view as symbols;
  - moving things and bright cells in view;
  - sounds heard;
  - recalled memories;
  - things heard at home;
  - landmarks from the bee's known map: home, bright spots seen, where moving things were seen, and how much has been explored in each direction.
- **Memory (local, free):**
  - **Short-term:** the last 8 events.
  - **Episodes:** a log with rule-based importance (sting 5, delivery 5, bloom seen 4, hornet seen 3, sound heard 1).
  - **Beliefs:** up to 12 short texts written through `remember`; the oldest is evicted.
  - **Recall:** the top 6 by recency, importance and BM25 relevance to the current situation.
- **Hive talk:**
  - `say` inside the hive is heard by every bee in the hive that tick, and stored as "heard at home".
  - Newborns stay inside for their first 3 ticks.
  - There is no separate reflection call. Arriving home triggers a decision, and `say` is available then.

## Hornets (no AI)

- **Count:** 4 in spring, 6 in summer, 8 in autumn, 0 in winter (dormant).
- **Genome:** 10 points spread over 3 genes:
  - `smell`: the range at which it detects bees;
  - `hearing`: how strongly it is drawn to bee sounds, and from how far;
  - `ambush`: how much it waits at places where it stung before, or near bloom, instead of roaming.
- **Behaviour each tick:**
  - If a bee is within smell range, pick a target with probability proportional to the bee's life, and step toward it. Hornets path on the true map, since they are part of the environment.
  - Otherwise, if a sound is within hearing range, move toward it with a probability set by the gene.
  - Otherwise, ambush or wander as the genes set.
- **Fitness:** life removed per tick alive.
- **Evolution:**
  - Every 25 ticks outside winter, the least fit hornet is replaced by a copy of a hornet chosen in proportion to fitness. The copy is mutated: with probability 0.5, one point moves between genes.
  - At the end of winter, the spring hornets are bred from the fittest hornets of the previous autumn.
- **`frozen_hornets` condition:** genes stay at their initial random draw (same seed).

## Conditions

| Condition | What changes |
|---|---|
| `full` | Everything above, neutral sounds |
| `no_talk` | `say` disabled; nothing is heard at home |
| `no_memory` | No episodes, beliefs or recall; the bee decides from current perception only |
| `frozen_hornets` | No hornet evolution |
| `rule_bees` | Scripted bees: explore at random, go home at half life, never share. No AI |
| `random_bees` | Random intents. No AI |
| `labels_good_bad` | The sounds are called "good noise" and "bad noise" |
| `oracle_bees` | Calibration only, never reported as a result: scripted bees told where the bloom is |

## Logging

- **Per tick:** every bee's position, life, carrying, stunned and intent; every hornet's position, genes and target; sounds made.
- **Events:** sting, delivery, hatch, queen_hatch, death, heal, say, decision.
- **Per run:** the world layout (walls, hive, entrances, bloom sites), plus per-season metrics and a run summary.
- Writes go through `RunLog`. Per-tick state goes to a compact JSONL file that the viewer reads.

## Measures (pre-registered in EXPERIMENTS.md before any AI run)

- deliveries per season;
- median ticks from leaving the hive to reaching bloom;
- stings per trip;
- colony size;
- tick of the first delivery in each spring, comparing year 2 with year 1;
- hornet gene means over time;
- how strongly each sound is tied to its context (made near hornets or near bloom), with mutual information;
- false location claims in hive talk;
- naive avoidance: how newborns respond to their first hornet sighting, before any sting.

## Experiments

- **E1, learning and culture:** `full` against `no_talk`, `no_memory`, `rule_bees` and `random_bees`, 3 seeds each.
- **E2, arms race:** `full` against `frozen_hornets`.
- **E3, seasonal memory:** first-delivery tick in year 2 spring against year 1, `full` against `no_talk`.
- **E4, signals:** whether meaning emerges with neutral sounds, against `labels_good_bad`.
- **Stretch:** a paraphrased system prompt, to test prompt robustness.

## Acceptance tests

- **Leak test:** no prompt contains the coordinates of a bloom cell or a hornet unless that bee saw it or heard it at home.
- **No-hints test:** `prompts/bee_system.txt` and the perception templates contain none of these words: bee, hive, flower, bloom, nectar, hornet, wasp, predator, danger, avoid, enemy, season, winter, summer, spring, autumn, food, good, bad. The only exception is the sound names under `labels_good_bad`.
- **Determinism:** the same seed and replay cache give an identical run.

## Viewer and video

- **Viewer:** a static `viewer/` page (HTML, canvas, JS) that loads a run directory. It shows:
  - a top-down map with a seasonal tint;
  - bees in yellow, with a ring showing life left;
  - hornets in orange-brown;
  - the bloom;
  - sound ripples of radius 10 (sound-1 teal, sound-2 magenta);
  - sting flashes and hatch sparkles;
  - a timeline slider and play/pause;
  - a selected bee's recent memories and intents, when clicked.
- **Video:** frames captured headless from the viewer (Playwright chrome-headless-shell, files on /dev/shm), then encoded with ffmpeg. The video is made last, from a fresh clone.

## Demo

`make demo` runs a small map (about 40 x 24, one short year) with rule bees, which needs no key. It also replays one recorded AI run from `experiments/llm_cache/`.
