# Schedule, scope, spend, repo and demo video

## Schedule (Jacob: build 2026-11-05, submit 2026-11-06)

| When | Exit condition |
|---|---|
| 2026-11-05 evening | Idea chosen, scored in docs/ideas.md, recorded in DECISIONS.md. Primary property and its measure written in EXPERIMENTS.md. |
| 2026-11-05 night | The core system runs end to end through `experiments/run.py`, logs per-step state, and has tests. `make demo` defined. |
| 2026-11-06 morning | Main experiment plus controls (ablation, baseline, seeds) run and written up, negative results included. |
| 2026-11-06 midday | README, ARCHITECTURE and AI_DISCLOSURE filled in. Demo video made. `make check` at zero FAIL. |
| 2026-11-06, before the deadline | Submission sent to the judge by email (11:04 PT); afterwards the repo moved to public GitHub on Jacob's instruction. |

Get the exact submission deadline from Jacob. Plan backwards from it with two hours of slack.

**Scope rule:** when behind, cut in this order: frontend polish, secondary properties, extra experiments beyond the main one plus its controls, then README flourish. Never cut the mandatory files, the controls, the negative results, the traces or `make demo`.

## Spend (approved by Jacob 2026-11-05)

- Runtime model calls are allowed. They all go through `digital_life.llm.complete()`, which enforces `LLM_BUDGET_USD` (default $100 total, tracked in `.llm_spend.json`). Raising the cap is Jacob's call.
- Default model `claude-opus-5-5`. Bee minds run on `claude-haiku-5-5` (effort low, thinking off, structured output), as Jacob approved with the spec on 2026-11-05. Set effort explicitly per use. Any other change of model or effort is Jacob's call, and is recorded as a variable.
- Development credentials are the Microsoft Foundry ones already in the session environment. Never copy them into files.
- Cached replays cost nothing. Prefer replay when re-running cited results.

## Repo home

- **Public on GitHub:** https://github.com/JacobGrantx/hearsay (Jacob, 2026-11-06). The repo was built privately on the company's GitLab, then moved here and made public after the submission was sent; the GitLab copy is to be deleted.
- Remote: GitHub `JacobGrantx/hearsay`. Push with `.local/push.sh` (local, gitignored), which takes the same arguments as `git push`.
- The repository is public: everything committed is published at once, so the private-text guards (traces-and-privacy.md items 8 and 9) matter on every commit.
- The project name is Hearsay.

## Demo video (Jacob: Claude makes it when we are done)

- Made from a fresh clone of the repo: clone, `make setup`, `make demo`. It shows real runs of the real system. No AI-generated footage and no mock-ups. Rendered in code from the system's logged output, plus real terminal capture.
- **Design rule this creates now:** the system must log enough per-step state (positions, genomes, messages, memories, whatever the idea needs) to `metrics.jsonl` and `events.jsonl`, or to snapshots via `log.path()`, that a renderer can replay any run frame by frame. Build the renderer so it reads run directories, not live state.
- Length: short enough to watch in full (aim for 60 to 120 seconds). It shows the behaviour, the control that rules out the boring explanation, and one surprise.
- Save it in `demo/recordings/` if small, otherwise upload it, and link it from the README's Demonstration section.
