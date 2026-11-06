# Digital Life hackathon project

Hackathon entry: build an artificial system that shows a meaningful property of life (autonomy, persistence, adaptation, interaction, emergence). Depth in one property beats coverage of five. The repo is the submission and will be public.

Judging: technical depth 30%, originality 25%, demonstrated behaviour and experimentation 20%, engineering and reproducibility 15%, effective and transparent tool use including AI 10%. Judges do not reward the biggest model, most tokens, most agents or fanciest frontend. They do reward a sound negative result over an unsupported claim of emergence.

## Everything here is published

- Every session in this repo is exported to agent_traces/ by a hook (tools/export_traces.py) and committed to a public repo. The export drops model reasoning, harness-injected context and secrets. The prompts, replies, tool calls and tool results are kept and published.
- Keep sessions on this project. Do not bring in private company material, client or investor information, or other workspaces' content. If something private comes up, add the term to agent_traces/.redact-terms.
- Never print or echo secrets. Keys live in .env (gitignored), read by name. Document new variables in .env.example.

## Evidence rules

The evidence docs (EXPERIMENTS.md, AI_DISCLOSURE.md, DECISIONS.md, agent_traces/) report what happened, including failures. The README can tell the story with energy, but every claim in it points at an experiment or a run directory.

- Run experiments only through `experiments/run.py` with a committed config and at least three seeds. Commit before a run you plan to cite.
- Never call a behaviour emergent until the controls in EXPERIMENTS.md "Protocol" have been run: ablate the credited mechanism, compare against a random or shuffled baseline, vary prompts (if an LLM is involved), and vary the setup.
- Never invent or round up a number. Quote results with n and spread, straight from experiments/results/.
- Record failed experiments the same day under "Negative results".
- When an agent proposes a design choice, log it in DECISIONS.md as an agent proposal. The human who accepts it is named only when they actually do.

## Working rules

- Commit small and often, with messages saying what changed. Never squash, amend published commits or rewrite history.
- Commit the exported agent_traces/ changes along with the work they produced.
- `make test` before each commit that touches src/, experiments/ or tools/.
- `make check` runs the submission checklist. Every FAIL must be fixed before submission.
- The humans must be able to explain every mechanism. When building something non-obvious, add a short plain explanation to ARCHITECTURE.md as you go.

## Layout

- src/digital_life/: the system. runlog.py and smoke.py are scaffold.
- experiments/: run.py, configurations/*.toml, results/ (committed, keep small), analysis/.
- agent_traces/: exported sessions, events, INDEX.md (generated); README.md and summaries/ (hand-written, labelled as such).
- tools/: trace export, presubmit check, secret patterns, git hooks.
- demo/: screenshots and recordings. `make demo` must reproduce a small version.
