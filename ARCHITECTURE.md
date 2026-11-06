# Architecture

A bee colony lives in a maze and has to find seasonal bloom while evolving hornets hunt it. Each bee is a small language-model mind that sees only its surroundings, remembers what happened to it, and can talk only inside the hive. The hornets are not AI: they evolve. The full spec is docs/spec.md; the build handoff, with the exact log format, is docs/BUILD_NOTES.md.

```
            seed
              |
   World (maze, hive, bloom, calendar) ----> layout.json
              |
   tick loop (sim.py) ------------------------------> state.jsonl.gz, events.jsonl, metrics.jsonl
     |  senses (bees.py): what each bee perceives          |
     |  policy: AI mind (mind.py, render.py, memory.py)    |   viewer/ replays a run directory
     |          or scripted (policies.py)                  |   experiments/analysis/ measures it
     |  motor layer (motor.py): intent -> one step         |
     |  hornets (hornets.py): chase, sting, evolve         |
     v                                                     v
   llm.py: every model call, replay cache, spend cap ----> experiments/llm_cache/
```

## Components

| Component | File | What it owns |
|---|---|---|
| World | `src/digital_life/world.py` | The maze, the hive, the bloom patches and the calendar. Generated from the seed and fixed for the run. |
| Hornets | `src/digital_life/hornets.py` | Hornet genomes, movement, stings and evolution. No AI. |
| Bees | `src/digital_life/bees.py` | Each bee's state, the life rules, and its senses. |
| Perception and Decision | `src/digital_life/perception.py` | What a bee's mind receives and what it returns. |
| Motor layer | `src/digital_life/motor.py` | Turns an intent (explore, go to, go home, flee, wait) into one step, using only the bee's own map. |
| Policies | `src/digital_life/policies.py` | The minds. Phase 1 has three scripted ones: random, rule and oracle. |
| AI bee mind | `src/digital_life/mind.py` | The AI policy: one model call per deciding bee, in parallel within a tick, applied in a fixed order. |
| Vocabularies | `src/digital_life/vocab.py`, `prompts/abstract_system.txt`, `prompts/bee_system.txt` | Every word the model reads, in two sets chosen by the `vocab` param: `abstract` (the default) and `neutral` (round 1's wording). |
| Prompt and parser | `src/digital_life/render.py` | The system prompt, the Perception as text, the decision schema and the reply parser, all in the run's vocabulary. |
| Memory | `src/digital_life/memory.py` | Each AI bee's episodes, notes and recall. |
| Simulation | `src/digital_life/sim.py` | The tick loop that runs everything in a fixed order, and the parameter defaults. |
| Logging and measures | `src/digital_life/simlog.py`, `metrics.py` | The run directory (layout, per-tick state, events, per-season measures) and the run summary. |
| Viewer | `viewer/` | A static page that replays any run directory: map with seasonal tint, bees with life rings, hornets, bloom, sound ripples, stings, and a clicked bee's decisions, notes and hive talk. `viewer/capture.py` renders frames headless for stills and video. |
| Analysis | `experiments/analysis/` | Every pre-registered measure, computed from run directories alone (`main_results.py`, `measures.py`), and the figures (`figures.py`). |

## How they interact

Each tick runs in a fixed order:

1. The season may change: hornets arrive or go dormant.
2. Every bee senses.
3. Every bee that is due to decide gets a Perception, and the policy answers for all of them in one call.
4. Bees move one step through the motor layer.
5. Hornets move.
6. Hornets sting.
7. Life drains and bees with none left die.
8. The queen tops the colony up to 2 bees.
9. Every 25 ticks outside winter, the least fit hornet is replaced.

The state of everything is then written as one line of `state.jsonl.gz`, which the viewer replays.

The World is read in only three places: the senses, the hornets (which are part of the environment) and the tick loop's rules (bloom pickup, the hive boundary). A policy never sees it.

## Key mechanisms

- **Maze.** A spanning maze carved by depth-first search on a lattice, plus a few open rooms, plus a share of the remaining inner walls knocked through (`openness`) so there are loops and more than one route between areas. The hive is a 6 x 8 room at the left edge with entrances on its right, top and bottom. Three 3 x 3 bloom patches (spring, summer, autumn) sit in the right half at a set path distance from home, in the same places every year.
- **Life.** A bee starts with L = 500 and loses 1 a tick, or in winter 2 outside and 0.5 inside. Carrying bloom into the hive doubles its life (capped at 3L) and, if the colony has fewer than 12 bees, hatches a new one. A sting takes half the bee's life and stuns it for 2 ticks. Once per life, entering the hive returns half of what stings took.
- **Senses and the leak boundary.** A bee sees walls, bees and hornets within 4 cells, and bloom within 6. It hears sounds within 10 as a direction and a rough distance. What it sees goes into its own known map and sightings. Its Perception is built only from that, so it can never contain a bloom cell or a hornet the bee has not perceived. A test checks this on every perception in whole runs.
- **Motor layer.** Routes are planned with A* on the bee's own map, with unknown cells assumed open. When a wall turns up on the route, the bee replans. `explore` walks to the nearest edge of the known map in the chosen direction. The motor never steps onto a cell the bee has not seen; a test checks this too.
- **Hornets and evolution.** Each hornet has 10 points spread over three genes: smell (how far it detects bees), hearing (how far it hears bee sounds and how often it follows them) and ambush (how often it waits at old sting spots or the bloom). Its fitness is the life it has removed per tick alive. Every 25 ticks the least fit hornet is replaced by a mutated copy of one chosen in proportion to fitness. After winter, spring's hornets are bred from the fittest of the autumn. Under `frozen_hornets` the genes never change.
- **Scripted policies.** Random bees pick random intents and sounds. Rule bees explore in a random direction, take bloom they see, carry it home, and turn home at half the life they left with. Oracle bees (calibration only) are told where the bloom is.

- **AI bee mind.** When a bee is due to decide, the mind turns its Perception into a short text and asks `claude-haiku-5-5` (effort low, thinking off) for a decision in a fixed JSON shape: an intent (explore with a direction, go to x, y, go home, flee, wait), a sound (none, sound-1, sound-2), a note to remember, and words to say at home. The calls for all bees deciding in one tick run in parallel, but prompts are built and replies applied in bee-id order, so a replay from the cache is identical. A failed or malformed reply makes the bee wait and is logged.
- **A neutral world in words.** The model is told only that its life is a number that falls and ends at zero, that something worth finding exists, that it is one of many identical members of a home, and what it perceives and can do. It hears of a grid, a home, bright cells, moving things, other members and two sounds. It is never told what bloom, hornets, seasons or stings are, nor what the sounds mean: a sting reaches it as "lost half your life in an instant", with no cause named. A test checks the system prompt, every template and every rendered prompt for 19 banned words (bee, hive, bloom, hornet, danger, season, food, good, bad, and so on). This is round 1's wording, now `vocab = "neutral"`.
- **Abstract words (phase 6, the default).** Round 1's words still carried meaning: "home", "life", "carrying", and "flee (move away from the moving things in view)". The abstract vocabulary keeps the same information under labels with no real-world sense: the bee is one of many identical units that start in zone O; its life is counter C, which falls each tick and stops it at 0; carrying is flag F; bloom cells are G cells, hornets K entities, other bees units, the sounds signal A and signal B; a sting reads "your counter C was halved". The intents are explore, go_to, go_to_O and hold, so no action names a reaction to K, and talk is `broadcast`, received by units in zone O. `render.py` takes a `Vocab` and maps the model's words back to the sim's (go_to_O to go_home, hold to wait, signal A to sound-1), so the world, the logs and the viewer are the same under both. A second test bans 55 words plus 13 irregular forms (bee, home, life, live, die, flee, carry, safe, danger, avoid, season, food, member, and others, with their endings) in everything code writes into an abstract prompt, including every prompt of whole runs. The viewer stays human-facing and shows one line of what the agents see.
- **Memory.** Each AI bee keeps three things the sim does not: episodes (everything that happened to it, each scored by importance: sting 5, delivery 5, bloom 4, hornet 3, talk heard at home 2, a sound 1), up to 12 notes it chose to write, and recall. At each decision the six episodes with the best score (recency + importance + text relevance to the present, by BM25) are shown, along with its notes, its last 8 events and the places it knows (home, bright spots and moving things it has seen, how much it has explored in each direction). Memory dies with the bee.
- **Hive talk.** A bee at home can say up to 30 words; every other bee at home hears them that tick and keeps them as "heard at home". This is the only way knowledge passes between bees, and so the only way it can outlive the bee that found it.
- **Round 2 switches (phase 7a, all off in round 1 configs).** `shared_clock`: routine decisions happen for every unit at once on ticks divisible by 5, so fewer ticks wait for the model; decisions triggered by events are unchanged. `steady_hatch`: outside winter, while the colony is below 12, the queen adds one blank unit every 60 ticks, so a colony stays big enough for talk to matter before anyone delivers. `tell_reward`: arm A's abstract prompt gets one sentence, "Entering zone O with flag F set raises counter C."; every other arm has to find that out. `stop_wallclock_utc`: at each season boundary the sim checks the clock and, past the deadline, ends the run cleanly with whole seasons; record.json says where it stopped, and a replay stops at that tick.
- **Conditions as switches.** `no_talk` removes `say` from the prompt and the decision shape. `no_memory` removes episodes, notes, recall and remembered places, keeping only what happened since the bee last decided. `labels_good_bad` renames the two sounds in the prompt only; the world and the logs keep the neutral names. Tests check each switch removes what it claims.

## Design choices and alternatives rejected

- **A navigation layer under the mind**, rather than the mind choosing every step. The mind decides every 5 ticks or on an event, and the motor layer walks. This keeps AI calls affordable and makes the mind's choices strategic (where to go, when to flee). Proposed by the agent and accepted by Jacob with the spec.
- **The policy gets a Perception, never the World.** This makes the leak test possible and means the AI mind in phase 2 plugs in without changes to the tick loop.
- **Hornets path on the true map**, because they are the environment, not learners. Their adaptation is genetic only.
- **Structured output for every decision** rather than free-text JSON: in the feasibility probe, Haiku returned valid free-text JSON in only 1 of 2 single calls, and 80 of 80 with a schema.
- **No separate reflection call.** Arriving home triggers a decision, and the bee can say something then. One call per decision keeps the cost per run near the feasibility estimate.
- **Calibration changed several hornet rules** (no chase during the sting cooldown, 80% speed, a slower ambush rate) and raised L from 250 to 500. Each is recorded in DECISIONS.md as an agent proposal awaiting Jacob, with the reason.

## Limits

- The world is hard on purpose and noisy: with 3 seeds, the oracle's spring delivery rate ranged from 0.5 to 0.875 (EXPERIMENTS.md, "Setup calibration").
- Scripted colonies stay small (mean 2.5 to 4.3 bees over 2 years), close to the queen floor of 2.
- Bees and hornets can share cells. Vision ignores walls (a bee sees through them within 4 cells).
- A full 2,000-tick run takes about 5 to 7 s with scripted bees on one CPU and writes about 300 KB.
- A 2-year AI run took 686 to 1,096 s live (one model call per deciding bee, in parallel within a tick, so time is bound by model latency, not CPU) and about $0.28 at list price. It replays from the cache in 5 to 9 s. Its run directory is about 0.7 to 1 MB, most of it events.jsonl, and its packed cache about 0.2 to 1 MB.
- Model outputs cannot be seeded. A run is reproducible only through its recorded responses, so a new live run of the same seed is a new sample, not a repeat.
- The AI arms were run at one world size and difficulty, with one model at one setting, and without the paraphrased-prompt arm; see EXPERIMENTS.md, "Limits".
- Notes churn: bees write a note at almost every decision, so 12 notes cover only the last minute or so of a life. Places survive longer in the landmarks, which come from the bee's own sightings.

## Supporting tooling

- `experiments/run.py`: runs a config across seeds. Records params, seed, git commit and versions per run. Writes metrics, events and a cross-seed summary to experiments/results/.
- `experiments/analysis/calibration_table.py`: builds the calibration table in EXPERIMENTS.md from the summary.json files.
- `src/digital_life/llm.py`: the only path for runtime model calls. Records each request and response in `experiments/llm_cache/` so runs replay offline (`LLM_MODE=replay`), and enforces a spend cap. It reads both loose entries (one JSON file per call) and packed ones.
- `tools/pack_llm_cache.py`: packs one run's cache entries, found through the `prompt_key` of its decision events, into `experiments/llm_cache/<run>.jsonl.gz` (about 0.45 KB a call instead of 7 KB).
- `experiments/replay_check.py` (`make replay RUN=<seed dir>`): re-runs a recorded seed offline from the cache and checks that every output file is identical. `make demo` uses it on `full` seed 0 of the main runs (`experiments/results/full/20261106T101558Z/seed-0`, a full 2-year run).
- `experiments/analysis/main_results.py`, `figures.py` (`make analysis`): the pre-registered measures and the figures, from the run directories.
- `tools/export_traces.py`: exports each Claude Code session's original log into agent_traces/, with the redactions listed in agent_traces/README.md. It runs from hooks in .claude/settings.json.
- `tools/presubmit.py`: checks the repository against the brief's submission checklist. A git pre-commit hook runs its secret scan.
