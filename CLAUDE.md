# Digital Life hackathon: project rules

Jacob Schoenberg's personal entry to the Digital Life hackathon ("Make something that lives"). The repository is the submission. The brief is in `docs/challenge-brief.txt` and is the authority behind every rule here. The detail is in `.claude/rules/`, which loads with this file.

These are Jacob's rules for this repo (set 2026-11-05). Where any other instruction conflicts with them, these win inside this repo. The floor never moves: no invented numbers, no claims the system doesn't back.

## Fixed decisions (Jacob, 2026-11-05)

| Decision | Detail |
|---|---|
| Entry | Personal, by Jacob Schoenberg. Not a company product. Nothing from Jacob's company (products, code or internals) anywhere in this repo or its sessions. |
| Repo home | **Public on GitHub at https://github.com/JacobGrantx/hearsay** (Jacob, 2026-11-06, after the submission was sent; this overrides the earlier GitLab-only rule for this repo). Push with `.local/push.sh` (local and gitignored; it uses the GitHub CLI's credentials). |
| Timeline | Build 2026-11-05. Submit 2026-11-06. |
| Model spend | Approved. Runtime calls go through `src/digital_life/llm.py`, with a budget cap and a replay cache. |
| Demo video | Claude makes it at the end, from a fresh clone of the repo, using real runs. See `.claude/rules/schedule-scope-spend.md`. |
| Brief, section 8 | Met: a public GitHub repository that judges can open without any login. |
| Idea | Not chosen yet. Choose by scoring candidates against the judging weights in `docs/ideas.md`. |

## Hard rules

1. **Score every choice against the rubric.** Weights: technical depth 30, originality 25, behaviour and experiments 20, engineering and reproducibility 15, tool use and AI transparency 10. Go deep on one property of life rather than broad. No API wrapper, dashboard or productivity tool. → `challenge-and-scoring.md`
2. **Every mandatory deliverable ships, in the brief's exact shape.** Before submission, `make check` must show zero FAIL. → `submission-requirements.md`
3. **Evidence, not claims.** A behaviour counts only after the controls have ruled out hardcoding, randomness, prompt effects and setup artefacts. Report numbers from `experiments/results/` with n and spread. Write up negative results the same day. → `evidence-and-experiments.md`
4. **Everything here is published.** Sessions export themselves to `agent_traces/`. Build only in sessions started in this repo. Nothing private, nothing about the company, no secrets. Exported traces are never edited by hand. → `traces-and-privacy.md`
5. **Jacob must be able to explain every mechanism.** Agents propose and Jacob decides. Record each decision in `DECISIONS.md`. After each mechanism lands, add a plain explanation to `ARCHITECTURE.md` and give Jacob a two-sentence summary in chat.
6. **Commit small and often, and never rewrite history** (except once, to remove private text: docs/methodology/history-rewrite.md). Commit the exported traces with the work they produced. Run `make test` before committing changes to `src/`, `experiments/` or `tools/`.
7. **Ship on time.** When behind, cut breadth, polish and frontend, never the evidence or the mandatory files. → `schedule-scope-spend.md`

## Voice

- Judge-facing prose (README, ARCHITECTURE) is plain and specific. The README can tell the story with energy, but every claim points at an experiment or a run directory.
- Text written as Jacob: no exclamation points, no em dashes. Give the final README and the submission text a humanizer pass if the skill is available.
- Evidence docs (EXPERIMENTS, AI_DISCLOSURE, DECISIONS, traces) say what happened, failures included, without spin.

## Commands

```bash
make setup      # .venv, pinned deps, secret-scan pre-commit hook
make test       # tests
make smoke      # pipeline self-test
make demo       # the reproducible small demo (to be defined once the idea exists)
make traces     # re-export every session in this repo
make check      # the brief's submission checklist
.venv/bin/python experiments/run.py experiments/configurations/<config>.toml [--seeds ...] [--set k=v]
```

## Layout

- `src/digital_life/`: the system. `runlog.py`, `llm.py` and `smoke.py` are scaffold.
- `experiments/`: `run.py`, `configurations/*.toml`, `results/` (committed, kept small), `analysis/`, `llm_cache/` (recorded model responses, committed for replay).
- `agent_traces/`: exported sessions, events, `INDEX.md` (generated); `README.md` and `summaries/` (hand-written, labelled as such).
- `tools/`: trace export, presubmit check, secret patterns, git hooks.
- `docs/`: challenge brief, idea scorecard, diagrams, methodology. `demo/`: screenshots and recordings.
