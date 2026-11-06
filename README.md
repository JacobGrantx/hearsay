# TODO: Project name

TODO: One line. What did we build?

<!-- Judges read this first. Every claim below should point at an experiment in EXPERIMENTS.md or a run in experiments/results/. -->

## The idea

TODO: The concept and what makes it interesting.

## Why digital life?

TODO: Which property of life this explores (autonomy, persistence, adaptation, interaction, emergence) and why we went deep on it rather than wide.

## Demonstration

TODO: Video, GIF or screenshots (demo/), or a live link. Then the one command that reproduces a small version:

```bash
make demo
```

## Technical architecture

TODO: Major components and how they interact. Diagram in docs/diagrams/. Full detail in [ARCHITECTURE.md](ARCHITECTURE.md).

## How it works

TODO: The mechanisms, algorithms and models underneath.

## Getting started

Requires Python 3.11+.

```bash
git clone TODO: repo URL
cd TODO: repo folder
make setup        # .venv, pinned dependencies, secret-scan pre-commit hook
cp .env.example .env   # only if the system needs API keys
make test
make demo
```

Run any experiment with its config and seeds:

```bash
.venv/bin/python experiments/run.py experiments/configurations/<config>.toml
```

TODO: Expected output, runtime and hardware notes, known limitations.

## Experiments and findings

TODO: The most interesting observations, with numbers across seeds, and the most useful negative result. Full record in [EXPERIMENTS.md](EXPERIMENTS.md).

## AI usage

How AI was used and what we built ourselves: [AI_DISCLOSURE.md](AI_DISCLOSURE.md).

## Agent traces

TODO: One paragraph on how agents were used. Every Claude Code session in this repo was exported automatically from its original log into [agent_traces/](agent_traces/); see [agent_traces/README.md](agent_traces/README.md) for what was kept, what was redacted and why, and [agent_traces/INDEX.md](agent_traces/INDEX.md) for the session list with models, token usage and the commits each session made.

## Team

TODO: Name, role, what each person built or decided.

## Future directions

TODO: What we would investigate with another month.

## Licence

MIT. See [LICENSE](LICENSE).
