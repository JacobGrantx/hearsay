# Contributing

## Setup

```bash
make setup   # .venv, pinned deps, secret-scan pre-commit hook
make test
```

## Working rules

- Commit small and often, with messages that say what changed. Never squash or rewrite history, except once, to remove private text (docs/methodology/history-rewrite.md). The brief asks for a history that shows real development.
- Run experiments only through `experiments/run.py` with a committed config. See the protocol in EXPERIMENTS.md.
- Record design decisions in DECISIONS.md: what was decided, who decided, and why.
- Agent sessions export themselves to agent_traces/. Commit the exported traces with the work they produced.
- Secrets go in `.env` (gitignored). Document new variables in `.env.example`.
- Before submitting, run `make check` and fix every FAIL.
