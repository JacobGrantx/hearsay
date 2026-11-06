# Evidence and experiments

Source: docs/challenge-brief.txt sections 3 and 6. The judges' key question is whether we can tell genuine emergent behaviour from hardcoded behaviour, randomness, prompt effects or artefacts of the setup.

## Hard rules

1. **Runs go through the runner.** Run `experiments/run.py` with a committed config in `experiments/configurations/`. No ad hoc scripts produce numbers we cite.
2. **Seeds.** At least 3 per condition; 5 for anything in the README. Report mean, sd and n across seeds. Never report a best run alone.
3. **Commit before citing.** A run cited in the docs must have `git_dirty: false` in its record.json.
4. **Controls before claims.** Nothing is called emergent, learned, adaptive or alive until the applicable controls have been run and written up:
   - **Ablation:** switch off the mechanism we credit. The behaviour should go away.
   - **Baseline:** random, shuffled or no-mechanism agents run on the same seeds.
   - **Hardcoding audit:** search the code, rules and prompts for the behaviour itself. If it is written in, it is not emergent.
   - **Prompt robustness** (if an LLM is involved): paraphrase and reorder the prompts, and remove any hint of the behaviour. The behaviour should survive.
   - **Setup sensitivity:** vary world size, timing, initial conditions and population. The behaviour should not hinge on one lucky setting.
5. **Numbers come from files.** Every figure in the README or EXPERIMENTS.md is copied from `summary.json` or `metrics.jsonl` under a named run directory. No rounding up, no "about" without the exact value next to it, no invented figures.
6. **Negative results are deliverables.** A failed hypothesis gets a full write-up the same day, under "Negative results": what we expected, what happened, how we know, and what it taught us.
7. **Quantify the property.** Pick an operational measure for the primary property before the main experiment, for example diversity over time, identity retention after N steps, or protocol convergence across runs. Write it in EXPERIMENTS.md first, then run.
8. **Surprises are logged when they happen.** Use `log.event(...)` in the code and a dated note in EXPERIMENTS.md. "Something that surprises its creators" is what the brief is asking for.

## LLM-specific rules

- All runtime model calls go through `digital_life.llm.complete()`. Never call the SDK directly.
- Model outputs cannot be seeded, so the replay cache is what makes LLM runs reproducible. Commit `experiments/llm_cache/` entries for every run we cite, and confirm the cited runs replay with `LLM_MODE=replay`.
- Pass `tag=f"{seed}:{step}:{agent_id}"` (or similar) when identical prompts must get independent samples.
- Record the model ID and effort in the config. Default model `claude-opus-5-5`. Changing model or effort is a variable, so log it as one.
