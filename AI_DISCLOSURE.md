# AI disclosure

Required by brief section 4.1. Each item is filled from the record: agent_traces/INDEX.md and each session's manifest.json (tools, models, dates, token counts, taken from the original logs), DECISIONS.md (who decided what), the run directories and `.llm_spend.json` (runtime model use).

## 1. AI systems and models used

| Where | Model | How | Record |
|---|---|---|---|
| Development | Claude Opus 5.5 (`claude-opus-5-5`) | Through Claude Code, 2026-11-05 and 2026-11-06 | Per-session model IDs in agent_traces/INDEX.md. One session (`49412096`) also lists `<synthetic>`, which is how Claude Code labels a message it writes itself, here the "Request timed out" error that ended that session. |
| Feasibility probes, before the spec | Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5 | 67 free-text and 82 structured calls through Microsoft Foundry, about $0.05 | docs/methodology/feasibility-2026-11-05.md |
| Runtime: the bee minds | Claude Haiku 5.5 (`claude-haiku-5-5`), effort low, thinking disabled, structured output | Through Microsoft Foundry, only via `src/digital_life/llm.py`, which records every request and response in the replay cache | Token counts per decision in each run's `events.jsonl` (`decision` events, `usage`); totals per run in experiments/analysis/output/main_results.md ("Model health"); spend in `.llm_spend.json` |

The hornets, the world and the scripted bees use no model.

The demo video's narration is synthesised locally with Kokoro-82M (kokoro-onnx, Apache 2.0 open weights, voice af_heart), in phase 7n; the narration script is in demo/video/storyboard.py.

No other AI system appears in the record. Every exported session lists only Claude Opus 5.5 (agent_traces/INDEX.md). The setup session's summary lists Claude Code with Claude Opus 5.5, plus the feasibility probes above (agent_traces/summaries/2026-11-05_scaffold.md). Use of any other AI tool outside these sessions is not recorded in this repository.

## 2. Coding agents and autonomous tools used

- **Claude Code 2.1.296** (CLI), the only coding agent. The version is recorded per session in agent_traces/sessions/*/manifest.json.
- How it was run: a setup session, started by Jacob Schoenberg in a private workspace, wrote the scaffold, the rules and the spec with him. On his go it launched each build phase as a headless Claude Code session started inside this repository, so each phase is captured in agent_traces/sessions/. The prompts of those sessions were written by the setup agent, which is why they show as unmarked prompts rather than human ones.
- No exported session launched subagents (the Subagents column in agent_traces/INDEX.md is 0 for every session).
- **Setup-session work that is not in the exported traces.** The setup session also ran the feasibility probes (item 1), an independent check of the repository from a fresh clone (it found the wrong commit-id map in item 8), and an independent read-only audit of the repository against the brief by a Claude Code subagent (its fixes are the phase 7f session in item 3). None of these is in agent_traces/. The setup session was started from a private workspace outside this repository, and only sessions started in this repository are exported. Its log is not published because it also covered unrelated private work (agent_traces/README.md, "Missing data").

## 3. What each tool was used for

| Session | When (UTC) | Used for |
|---|---|---|
| Setup session (private workspace, hand-written summary in agent_traces/summaries/2026-11-05_scaffold.md) | 2026-11-05 and 2026-11-06 | Reading the brief; the repo scaffold (trace exporter, runner, model wrapper, presubmit check, doc templates); the project rules; feasibility probes; explaining the five properties, proposing and researching candidate ideas; writing docs/spec.md from Jacob's mechanics and decisions; launching the build sessions; the fresh-clone check and the read-only audit (item 2) |
| `c859337b`, `71fd6e83` | 2026-11-06 01:39, 01:53 | Two one-line checks that session capture works and that a fresh session loads the project rules |
| `49412096` | 2026-11-06 07:54 to 09:07 | First attempt at phase 1. It died on a timed-out reply after 8 tool calls and made no commits (item 8) |
| `c9529ee6` | 2026-11-06 09:09 to 09:47 | Phase 1: the world, hornets, seasons, scripted bees, logging, tests, setup calibration |
| `f67417d9` | 2026-11-06 09:13 to 09:35 | The viewer (in parallel, on a branch in a worktree): static page, bundler, headless frame capture, viewer tests |
| `9ea8a272` | 2026-11-06 09:49 to 10:13 | Phase 2: the AI bee mind, prompt and renderer, memory, condition switches, leak and no-hints tests, the pre-registration, the pilot |
| `6c051b77` | 2026-11-06 from 10:14 | Phase 4: the main runs, the replay cache packer and replay check, the analysis scripts and figures, EXPERIMENTS.md results, README, ARCHITECTURE, this file |
| `3859069f` | 2026-11-06 from 11:20 | Phase 4b, the post-hoc follow-up E5: the trip diagnosis, the E5 world calibration with scripted bees, the E5 pre-registration, runs and analysis, the run-order cache packing, and the E5 updates to EXPERIMENTS.md, README and this file |
| `954b5b7b` | 2026-11-06 from 12:03 | Phase 5, the demo video: the moment finder (experiments/analysis/find_moments.py), the storyboard, cards, charts and renderer in demo/video/, the render from a fresh clone, the stills, and the final submission pass |
| `d0a4cfdf` | 2026-11-06 15:36 | A guard check (2 tool calls): in a fresh session in this repository the Skill tool is unavailable and reading the user's Claude Code configuration is denied |
| `c34f9a85` | 2026-11-06 15:38 to 16:07 | Phase 6, abstract vocabulary: the `vocab` switch (src/digital_life/vocab.py, prompts/abstract_system.txt) with abstract as the default, the viewer and README line on what the agents read, the phase 6 pilot, and the vocabulary decisions |
| `176af22d` | 2026-11-06 16:47 to 17:06 | Phase 7a, round 2: the round 2 switches with tests, the round 2 pre-registration and configs, the scripted calibration in the round 2 world, the analysis script and progress tool, launching the round 2 runs, and the ten-minute check |
| `16bcb907` | 2026-11-06 from 17:07 | Phase 7f: fixes from an independent audit against the brief (wording of claims, history notes, disclosure, project name) |
| `2464b67d` | 2026-11-06 from 17:23 | Phase 7v: the demo video re-rendered with the final name (Hearsay) and corrected captions |
| `195b10ac` | 2026-11-06 from 17:42 | Phase 7n: spoken narration for the demo video (Kokoro-82M, local) and a card on how the entry meets the brief |
| Phase 7b session | 2026-11-06 from 18:09 | Phase 7b: collecting round 2, amendment 1 exclusions in round2.py, the round 2 figures, replay packs and replay check, the Round 2 results in EXPERIMENTS.md, the README round 2 paragraph, this file's round 2 figures |
| Claude Haiku 5.5 at runtime | main runs, E5, phase 6 pilot and round 2 | Every decision of every AI bee: intent, sound, a note to remember, words to say at home |

## 4. Components primarily AI-generated

All of the code and the first drafts of all of the documents were written by Claude Code:

- `src/digital_life/` (world, hornets, bees, motor, policies, sim, metrics, logging, the AI mind, render, memory, llm, and `vocab.py`, which holds both vocabularies), `prompts/bee_system.txt` (round 1's neutral system prompt) and `prompts/abstract_system.txt` (the abstract-vocabulary system prompt, the default from phase 6). Jacob set the abstract word list (item 5); the prompt text around it was written by Claude Code;
- `experiments/` (runner, replay check, configs, analysis scripts), `tools/` (trace exporter, cache packer, presubmit, secret scan), `viewer/`, `tests/`; `demo/video/` and the demo video it renders (demo/recordings/demo.mp4, every frame replayed from logged runs, no generated footage), and the stills in demo/screenshots/;
- README.md, ARCHITECTURE.md, EXPERIMENTS.md (including the pre-registration), DECISIONS.md, docs/spec.md, docs/BUILD_NOTES.md, this file.

The bee minds' behaviour in every AI run is generated by Claude Haiku 5.5 at runtime. That is the subject of the experiments, not a development aid.

## 5. Components primarily written or designed by the participants

Jacob Schoenberg, as recorded in DECISIONS.md:

- the decision to enter, and the constraints: a personal entry, GitLab not GitHub, the timeline, model spend, a demo video made from real runs;
- **the core game mechanics**: a maze world, life measured in steps, a goal across the map that brings a life bonus and an offspring, roaming threats that drain life on contact, information shared only at home, stings that take half a life with one heal per life at home, threats drawn to bees in proportion to their life, a colony size cap, seasons with different challenges, two sounds heard within 10 steps, and a map 3 to 5 times larger than first proposed;
- the review that shaped the spec: he asked for an audit of achievability, gaming and overcomplication, and approved the spec on 2026-11-05;
- **the vocabulary request** (2026-11-06): he asked for the names and labels (bees, hornets, seasons, hives and the rest) to be replaced so the model's real-world knowledge cannot come into play, set the abstract word list, made abstract the default, and decided that the abstract vocabulary has no `flee`;
- **his round 2 choices**: longer runs that must finish by 11:00 PT ("yes this works but do longer runs (still need to be done by 11)"), which set 8 years with every run ending at the first season boundary after 10:05 PT; the arms (B_full and B_no_talk, 5 seeds; A_full and N_full, 3 seeds; scripted rule and random, 3 seeds); and, in his round 2 brief, steady hatching, the reward rule told to arm A only, the wall-clock stop and the cap of 6 model calls in flight per run. During the runs he decided "yes/cut" to stopping A_full and N_full seeds 1 and 2, so the B arms could reach a second year (docs/methodology/round2-amendment-1.md);
- his decisions of 2026-11-06, about 09:00 PT: the project name, Hearsay; and the repository stays on GitLab and private, with judges' access arranged by him;
- accepting or changing each agent proposal marked "accepted by Jacob Schoenberg" in DECISIONS.md.

## 6. How generated code was reviewed, tested and modified

- **Tests** (tests/, 66 at the end of phase 4, 67 after phase 4b and 69 after phase 5, run before every code commit): world generation, hornet genetics, life rules, motor layer, determinism of whole runs, the runner's reproducibility, trace redaction, and for the AI mind: the **leak test** (no prompt holds a bloom or hornet coordinate the bee never perceived, with a check that the test catches an injected leak), the **no-hints test** (19 banned words absent from the system prompt, templates, schema and every rendered prompt), replay identity, what each condition switch removes, and the packed replay cache.
- **Calibration with scripted bees** before any AI run (EXPERIMENTS.md, "Setup calibration"). It exposed four bugs in the first build of the world, which were fixed in visible commits (item 8).
- **Pre-registration** of every hypothesis, measure and decision rule before the first real bee-mind call (commit db1db0f), so the analysis could not be fitted to the results.
- **Controls** in every experiment: ablations, scripted baselines, frozen hornets, relabelled sounds, a hardcoding audit (EXPERIMENTS.md).
- **Replay check**: experiments/replay_check.py re-runs a recorded AI run offline and compares every output file.
- Human review: Jacob reviewed and approved the spec and the design proposals listed as accepted in DECISIONS.md. Proposals made during the build are marked "awaiting Jacob" there. A line-by-line human review of the code is not recorded in the traces.

## 7. Whether AI was used to design the architecture or research the concepts

Yes, in part, and DECISIONS.md records who decided each item.

- **From Jacob:** the game mechanics listed in item 5.
- **Agent proposals Jacob accepted with the spec:** the bee and hornet framing, the capped life bonus, the queen floor, three hive entrances, the hornet genome and its evolution, the neutral prompt world and neutral sounds, AI decisions every 5 ticks over a navigation layer, cutting bee inheritance and seasonal gates, the 80 x 48 map, and Claude Haiku 5.5 for the bee minds.
- **Agent proposals awaiting Jacob:** the calibration changes (no chase during the sting cooldown, 80% hornet speed, the ambush rate, L = 500), smaller interpretations of the spec, what each ablation removes, memory details, the neutral wording of experiences, the handling of model failures.
- **Research:** in the setup session the agent explained the five properties with examples from nature, proposed and researched candidate ideas (one, prompt soup, was rejected because prior work exists), and ran the feasibility probes.

## 8. Limitations, mistakes or unexpected behaviours introduced by AI assistance

- **A lost session.** The first phase 1 session (`49412096`) produced one reply too large for the API, which timed out and ended the session after 8 tool calls, with no commits. Phase 1 was restarted (`c9529ee6`), and later sessions were told to keep replies small.
- **Bugs in the first build of the world**, found by the scripted calibration, not by the tests: a hornet that stung a bee chased it at equal speed and stung it every 10 ticks until it died; every hornet re-rolled its ambush gene each tick, so they all camped on the bloom; rule bees got stuck when nothing was left to explore in their direction; deliveries and trips were counted in different seasons. Fixed in commits 2e19f63 to 128e459.
- **A false secret hit.** The secret scanner read JSON-escaped newlines in exported traces as part of a token-like value and blocked a commit. Fixed in commit 05909c4, with a test both ways.
- **Private text in exported traces, and one history rewrite.** The phase 5 session (`954b5b7b`) loaded a personal writing-style skill from the developer's own setup, and its instructions reached that session's exported trace. Earlier exports also held file paths from outside this repository. The exporter was fixed (commit ca93bc5), and project settings, a pre-commit scan and `make check` now block a recurrence (commit ba3c214). The history was rewritten once, in two passes, with git-filter-repo: only the exported trace files were re-redacted, in every commit. No commit was removed, squashed, reordered or re-dated, and the tree of the newest commit was byte-identical before and after. The cleaned history went to a fresh project. Two earlier private projects remain, and the record says a group owner should delete them. This breaks the project's rule never to rewrite history, so docs/methodology/history-rewrite.md records what changed, how it was checked, and an old-to-new commit-id table.
- **A wrong commit-id map.** The first version of that table, and the commit ids written into the docs after the second pass, gave first-pass ids that the second pass had replaced, so they did not resolve. The independent fresh-clone check (item 2) found this, along with a privacy-scan test that assumed the repository sits under the home folder. Both were fixed in commit 0a616b1. The table now maps each original id to its final id, paired by position in the history and checked against author and commit dates (77 of 83 commits matched uniquely by date, and all 77 agree with the positional pairing).
- **A near-empty commit with a misleading message.** The message of commit 2d07df7 describes a caption fix (the summer stings were beside the old spring patch), SOURCES.md recording the render commit, and removing the empty placeholder folders. Its `git add` failed on a removed path, so the commit holds only the deletion of four empty `.gitkeep` files. The caption and SOURCES.md changes landed in the next commit, 4d59b6f, whose message says so. The message of 2d07df7 is unchanged.
- **Unexpected runtime behaviour** (the model, not a bug): bees almost never make a sound, and they write a note at every decision, so their 12-note store only covers the last minute or so. Neither was tuned away, because both follow from the world rules as stated. See EXPERIMENTS.md, Pilot and E4.
- **Runtime reproducibility depends on the cache.** Model outputs cannot be seeded, so a run is reproducible only through its recorded responses. Which runs' responses are committed is listed in agent_traces/README.md, "Missing data".
- **A measure too narrow for its question (E5).** The agent wrote E5's stricter "acted on talk" rule to count only a `go_to` toward the bloom. In the one seed where talk carried a place, a newborn followed what it heard with `explore NE` and named the heard coordinate as its target in its notes, so the rule scored it 0. This was found by reading the notes after the results; it is reported, not counted (EXPERIMENTS.md, E5). Separately, `min_bloom_distance`, the knob the plan named first for E5, turned out to do nothing below 55 on the full map, which the calibration showed before any AI run.

## Usage information

- **Development:** token counts per session are in agent_traces/INDEX.md, summed from the usage record of each API response in the original logs. The setup session's usage is not available (its log is private).
- **Runtime:** the 19 main AI runs made 26,093 bee decisions with 45,674,885 input and 1,769,083 output tokens (summed from the decision events, experiments/analysis/output/main_results.md, "Model health"), 25,738 of them live calls costing $5.3665 at list price. At the end of phase 4 the project ledger `.llm_spend.json` stood at $5.5084 over 26,242 calls, of which $0.1419 over 504 calls was spent before phase 4 (the pilot and its plumbing check, and earlier checks through `llm.py`). The 10 E5 runs (phase 4b) made 12,686 decisions, all live calls, with 24,953,842 input and 972,531 output tokens (experiments/analysis/output/e5_results.md, "Model health"), costing $2.9816 at list price; after E5 the ledger stood at $8.49 over 38,928 calls. As of 2026-11-06 09:11 PT it reads $8.5732 over 39,261 calls (the phase 6 pilot came after E5). Round 2 ran in a separate clone with one spend file per run (`spend.json` beside each run's cache): its 16 AI runs made 50,092 live calls costing $11.1510 at list price, and logged 50,054 decisions with 92,683,861 input and 3,745,946 output tokens (summed from the `usage` of the `decision` events in experiments/results/r2_*; the 38 calls without a decision event were in flight when runs stopped). Adding those spend files, the ledger reads $19.7242 over 89,353 calls (phase 7b, 2026-11-06 10:18 PT). Where a figure is unavailable it is marked missing, not estimated.
