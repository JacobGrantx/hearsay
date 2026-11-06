# Mandatory deliverables (hard requirements)

Source: docs/challenge-brief.txt, sections 4 to 10, 12 and 13. Each one is enforced by `make check` (tools/presubmit.py). Zero FAIL before submission. If a check is wrong, fix the check in a visible commit. Never weaken it to pass.

## Repository (section 8)

- The brief says "public GitHub repository". Jacob's rule is GitLab, never GitHub. The repo lives on GitLab, and whether the organisers accept that is Jacob's question to settle before submission. Never create, mirror or push to GitHub.
- Meaningful project name. Judges must be able to open it without any login or group access. `make check` verifies this with an anonymous request; a redirect to sign-in means it is still private.
- Real source code committed. Licence included (MIT, copyright Jacob Schoenberg).
- History shows real development: meaningful commits throughout. No squashing, no rewriting history, no amending published commits.
- No credentials or sensitive information anywhere in the tree or the history.

## README.md (section 9), in this order

Project name (give the creation an identity), one-line description, The idea, Why digital life?, Demonstration (video, GIF, screenshots or live link), Technical architecture, How it works, Getting started (install and run commands), Experiments and findings, AI usage (link to AI_DISCLOSURE.md), Agent traces (how agents were used, with a link), Team (contributors and roles), Future directions (what we would do with another month).

## AI_DISCLOSURE.md (section 4.1), all eight items

1. AI systems and models used. 2. Coding agents and autonomous tools used. 3. What each was used for. 4. Components primarily AI-generated. 5. Components primarily written or designed by the participants. 6. How generated code was reviewed, tested and modified. 7. Whether AI designed the architecture or researched the concepts. 8. Limitations, mistakes or unexpected behaviour introduced by AI.

Give model versions and dates where possible. Never fabricate token counts or usage figures. Use the logged ones (agent_traces/INDEX.md for development, the `llm_call` events and `.llm_spend.json` for runtime), or say a figure is unavailable.

## agent_traces/ (section 5), mandatory

Session logs, prompts, tool calls and results, model versions, agent-to-agent messages, human interventions and approvals, errors and recovery, and links to the commits produced. JSONL with timestamps and session IDs. Rules for this are in `traces-and-privacy.md`.

## EXPERIMENTS.md (section 6)

For each significant experiment, under these exact headings: Hypothesis, Experimental setup, Variables or parameters, Observations, Results, What we learned, What we would investigate next. Add Controls. Include negative results. Method in `evidence-and-experiments.md`.

## Reproducibility (section 7)

Install instructions, dependencies and versions (pinned in requirements.txt), environment requirements, configuration, model/API requirements, example commands, a reproducible demo, expected outputs, known limitations. Where practical: fixed seeds, example data, config files, tests, evaluation scripts, Docker or equivalent. Document required variables in `.env.example`, never with real values. LLM runs must replay offline from `experiments/llm_cache/` (`LLM_MODE=replay`), so a judge without a key can reproduce them.

## ARCHITECTURE.md

Components, how they interact, key mechanisms, design choices and rejected alternatives, limits. Every team member must be able to explain it (section 4.2).

## Demonstration (section 10)

Show the system doing something: a live system, recording, simulation, visualisation, real-time experiment or CLI demo. A presentation of what it could do does not count. If the full system is expensive, provide a recording plus a reproducible small-scale run. `make demo` is that small run.

## Final submission package (section 13)

Public repo URL, project name, short description, team members, demo link, any extra infrastructure or execution requirements. Draft it in `docs/submission.md` before submitting.
