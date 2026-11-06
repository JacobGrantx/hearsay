# Bee colony (working title)

A colony of language-model bees that has to work out, from nothing, where the flowers are, what keeps hurting it, and how to tell its young, while the hornets evolve to hunt it.

<!-- Judges read this first. Every claim below points at an experiment in EXPERIMENTS.md or a run in experiments/results/. -->

## The idea

A maze, 80 by 48 cells. On the left edge is the hive. Far away on the right are three patches of bloom, one for spring, one for summer, one for autumn, in the same places every year. In winter nothing blooms and a bee caught outside burns life twice as fast.

Each bee is a small mind running on Claude Haiku 5.5. It is never told it is a bee. It is told only that its life is a number that falls each moment and ends at zero, that something worth finding exists in this place, and that it is one of many identical members of a home. It sees 4 cells around it, notices bright cells from 6, hears two sounds called `sound-1` and `sound-2`, and keeps its own memories. It can talk, but only inside the hive.

A bee that carries bloom home doubles its life, and, if the colony has room, a new bee hatches with no memories at all. So whatever one bee learns dies with it, unless it says it at home before it goes.

Hornets roam the maze. They are not AI. Each carries 10 points spread over three genes (smell, hearing, ambush), and every 25 ticks the least successful hornet is replaced by a mutated copy of a successful one. A sting takes half a bee's life. The bees are never told what a hornet is: a sting reaches the model as "lost half your life in an instant", with no cause named. A test checks that the words bee, hive, flower, bloom, hornet, danger, season, food, good, bad and nine others never appear in any prompt.

So everything the colony comes to know (where the bloom is, that moving things hurt, which way to go in spring) it has to find out itself, and keep alive by talking.

## Why digital life?

The property we go deep on is **adaptation, at three speeds**, under seasonal change:

| Speed | Mechanism | Ablation that removes it |
|---|---|---|
| Within one life | each bee's episodes, notes and recall | `no_memory` |
| Across bee generations | hive talk: the only way knowledge can outlive the bee that found it | `no_talk` |
| Across hornet generations | selection and mutation of hornet genomes | `frozen_hornets` |

Persistence (knowledge outliving every bee that gained it), interaction (talk, sounds, predator and prey) and emergence (whether two meaningless sounds come to mean something; `labels_good_bad` is its control) are studied as parts of that one question, not as separate features. Each speed has its own switch, so each claim can be tested by turning it off.

## Demonstration

Video to come. A still from the viewer, from a recorded run of the `full` condition:

RESULTS PENDING: still

Run a small version yourself, no key needed:

```bash
make demo
```

It runs scripted bees in a small world for one short year (3 seeds, a few seconds), then replays a recorded AI run offline from its saved model responses and checks every output file is identical to the original. The viewer (`viewer/`) turns any run directory into one HTML page you can open from disk: `.venv/bin/python viewer/bundle.py <seed dir> -o run.html`.

## Technical architecture

```
   seed -> World (maze, hive, bloom, calendar)
             |
   tick loop (src/digital_life/sim.py), one tick at a time:
     senses (bees.py)       what each bee perceives, from its own position only
     mind (mind.py)         one Claude Haiku 5.5 call per deciding bee, in parallel
       render.py            perception -> neutral text; reply -> decision (structured output)
       memory.py            each bee's episodes, notes, recall (BM25)
     motor (motor.py)       intent -> one step, by A* over the bee's own map
     hornets (hornets.py)   smell, hear, ambush, sting, evolve
             |
   run directory: layout.json, state.jsonl.gz, events.jsonl, metrics.jsonl, record.json
             |                      |                         |
   viewer/ replays it    experiments/analysis/ measures it   llm.py's replay cache reproduces it
```

Full detail, with the design choices and the alternatives rejected, in [ARCHITECTURE.md](ARCHITECTURE.md).

## How it works

- **Decisions.** A bee decides every 5 ticks, and at once when it is stung, newly sees a moving thing, sees bloom, hears a sound, arrives, gets home, or its life crosses half or a quarter. A decision is an intent (`explore` a direction, `go_to` x, y, `go_home`, `flee`, `wait`), a sound or none (each costs 1 life, and hornets can hear it), a note to remember, and up to 30 words to say at home.
- **Body.** A motor layer with no AI walks the intent: A* over the cells this bee has seen, unknown cells assumed open, replanning when a wall appears. The mind chooses where to go, not each step.
- **Memory.** Every bee keeps episodes scored by importance (a sting or a delivery 5, bloom 4, a moving thing 3, talk heard 2, a sound 1), up to 12 notes it chose to write, and recall of the 6 best episodes by recency, importance and text relevance. Memory dies with the bee.
- **Culture.** Words said at home reach every bee at home that tick and are stored as things heard. That is the only channel between bees.
- **Evolution.** Hornet fitness is life removed per tick alive. Steady-state selection every 25 ticks outside winter; after winter, spring's hornets are bred from the fittest of autumn.
- **Reproducibility.** Every model call goes through `src/digital_life/llm.py`, which records request and response. A seed fixes the maze, the bloom and the first hornets; the cache fixes the minds. Replay is exact, file for file.

## Getting started

Requires Python 3.11 or later and `make`. No GPU, no API key for anything below.

```bash
git clone <public repository URL, at submission>
cd digital-life
make setup        # .venv, pinned dependencies, secret-scan pre-commit hook
make test         # 62 tests, about a minute
make demo         # small scripted world, then an offline replay of a recorded AI run
```

Reproduce the main results offline, from the recorded model responses:

```bash
make replay RUN=experiments/results/full/20261106T101558Z/seed-0   # re-runs a 2-year AI run, checks every file
make analysis     # every pre-registered measure and figure, into experiments/analysis/output/
```

RESULTS PENDING: replay timing and expected output

Run a new experiment live (needs `ANTHROPIC_API_KEY` in `.env`, see `.env.example`):

```bash
.venv/bin/python experiments/run.py experiments/configurations/full.toml --seeds 5
```

RESULTS PENDING: cost and time per run

## Experiments and findings

RESULTS PENDING

## AI usage

All of the code was written by Claude Code (Claude Opus 5.5); the core game mechanics and every accepted design decision are Jacob Schoenberg's. At runtime the bee minds are Claude Haiku 5.5. Details, item by item: [AI_DISCLOSURE.md](AI_DISCLOSURE.md).

## Agent traces

The project was built in headless Claude Code sessions, one per phase (world and calibration, viewer, AI mind and pre-registration, main runs and analysis), each launched from a setup session where Jacob and the agent wrote the spec. Every session started in this repository was exported automatically from its original log into [agent_traces/](agent_traces/); see [agent_traces/README.md](agent_traces/README.md) for what was kept, what was redacted and why, and what is missing (including a phase 1 session that died on a timeout), and [agent_traces/INDEX.md](agent_traces/INDEX.md) for the session list with models, token usage and commits.

## Team

Jacob Schoenberg, solo entry. Jacob designed the core mechanics (maze, life as steps, a distant goal that brings life and offspring, life-draining threats drawn to the strongest bees, knowledge shared only at home, half-life stings with one heal, seasons, two sounds, the colony cap), set the constraints, and approved the spec and the design proposals marked as accepted in [DECISIONS.md](DECISIONS.md). Claude Code wrote the code and the documents, and proposed the rest of the design; who decided what is in DECISIONS.md and [AI_DISCLOSURE.md](AI_DISCLOSURE.md).

## Future directions

With another month:

- **Ten seeds per arm, not three.** The world is noisy by design, and with n = 3 only large, consistent differences can be told from chance. Every number in EXPERIMENTS.md says how many seeds it rests on.
- **A free-sound arm.** Sounds cost 1 life and attract hornets, and bees almost never make them. A pre-registered arm with free sounds would tell "no meaning emerges" apart from "sounds are too expensive to try".
- **Follow knowledge through the colony.** Trace each coordinate from the bee that saw it, through every retelling at home, to the bee that acts on it, and measure how far and how long true and false claims travel.
- **The prompt-robustness arm** the spec lists as a stretch: a paraphrased and reordered system prompt with the same facts, to show that what the colony does comes from the world, not from the wording.
- **Bigger colonies.** Colonies spend much of their time near the 2-bee floor, so few bees are at home to hear anything. A world with more bloom would give culture more carriers.
- **Walls that block sight**, and hornets that remember places within a life as well as evolving across lives, so both sides of the arms race can learn at two speeds.

## Licence

MIT. See [LICENSE](LICENSE).
