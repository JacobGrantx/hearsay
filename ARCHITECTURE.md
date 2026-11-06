# Architecture

TODO: Fill once the system exists. Keep it explainable by every team member (brief section 4.2).

## Components

TODO: Each major component, what it owns, where it lives in src/.

## How they interact

TODO: Data and control flow per step or tick. Diagram in docs/diagrams/.

## Key mechanisms

TODO: The mechanisms the life-like behaviour depends on. These are what the ablations in EXPERIMENTS.md switch off.

## Design choices and alternatives rejected

TODO: Why this architecture. What else we considered and why we dropped it. Who decided (see DECISIONS.md).

## Limits

TODO: What it cannot do, scale limits, known failure modes.

## Supporting tooling

- `experiments/run.py`: runs a config across seeds. Records params, seed, git commit and versions per run. Writes metrics, events and a cross-seed summary to experiments/results/.
- `tools/export_traces.py`: exports each Claude Code session's original log into agent_traces/, with the redactions listed in agent_traces/README.md. It runs from hooks in .claude/settings.json.
- `tools/presubmit.py`: checks the repository against the brief's submission checklist. A git pre-commit hook runs its secret scan.
