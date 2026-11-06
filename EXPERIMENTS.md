# Experiments

Required by brief section 6. Judges want to see whether we can tell genuine emergent behaviour from hardcoded behaviour, randomness, prompt effects or setup artefacts. Negative results count.

## Protocol

- Every run goes through `experiments/run.py` with a config in `experiments/configurations/`. The runner records the seed, params, git commit, dirty flag and package versions for each run.
- Three seeds minimum; five for any result we headline. Report mean, sd and n across seeds, not a best run.
- Commit before a run we plan to cite, so the record points at real code.
- Before calling anything emergent, run the controls that apply:
  - **Hardcoded:** is the behaviour written anywhere in code, rules or prompts? Ablate the mechanism we credit and check the behaviour goes away.
  - **Randomness:** compare against a random or shuffled baseline with the same seeds.
  - **Prompt effects** (if an LLM is involved): paraphrase the prompts and swap the order. Does the behaviour survive?
  - **Setup artefacts:** change world size, timing and initial conditions. Does it still happen?
- Write up a failed experiment the same day, in the Negative results section.

## Summary

| # | Question | Result | Holds across seeds? | Controls passed |
|---|---|---|---|---|
| 1 | TODO | TODO | TODO | TODO |

## Experiment 1: TODO title

### Hypothesis

TODO

### Experimental setup

TODO: config path, commit, seeds, run directory under experiments/results/.

### Variables or parameters

TODO

### Observations

TODO

### Results

TODO: numbers with n, mean and sd; plot in experiments/analysis/.

### Controls

TODO: which controls from the protocol were run and what they showed.

### What we learned

TODO

### What we would investigate next

TODO

## Negative results

TODO: what did not work, how we know, what it taught us.
