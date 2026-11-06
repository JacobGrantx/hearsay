# Decisions

Each design decision: what, who decided (a person, or an agent proposal a person accepted), alternatives, why. This is the record of what the team investigated and chose (brief section 4.2).

| Date | Decision | Decided by | Alternatives considered | Why |
|---|---|---|---|---|
| 2026-11-05 | Enter the Digital Life hackathon | Jacob Schoenberg | | |
| 2026-11-05 | Build with Claude Code. Capture every session automatically from its original log, rather than writing summaries afterwards | Agent proposal (Claude Code, setup session); accepted by Jacob Schoenberg 2026-11-05 | Manual summaries; no traces | The brief makes traces mandatory and forbids reconstructed ones. Capturing from the start is the only way to have complete originals. |
| 2026-11-05 | Python, with a seeded experiment runner and a cross-seed summary | Agent proposal (Claude Code, setup session); accepted by Jacob Schoenberg 2026-11-05 | Notebook-only experiments | The brief weighs reproducibility and asks us to tell real emergence from randomness, which needs seeds and multiple runs. |
| 2026-11-05 | Personal entry by Jacob Schoenberg (not a company project) | Jacob Schoenberg | Company entry | |
| 2026-11-05 | Host the repo in a durable-intelligence GitHub org (superseded below) | Jacob Schoenberg | Personal account | |
| 2026-11-05 | GitLab, never GitHub: the repo is its own project on the company's self-managed GitLab, private while building | Jacob Schoenberg | GitHub (the brief's wording) | Jacob's standing rule. Whether the organisers accept a GitLab URL is still open. |
| 2026-11-05 | Build on 2026-11-05, submit on 2026-11-06 | Jacob Schoenberg | | |
| 2026-11-05 | Runtime model calls allowed | Jacob Schoenberg | No model in the system | |
| 2026-11-05 | All runtime model calls go through one wrapper with a replay cache and a $100 default spend cap | Agent proposal (Claude Code, setup session); Jacob to confirm the cap | Direct SDK calls | Model outputs can't be seeded, so recorded responses are the only way a judge can reproduce an LLM run without a key. |
| 2026-11-05 | Demo video made by Claude at the end, from a fresh clone and real runs | Jacob Schoenberg | | |
| 2026-11-05 | Project rules in CLAUDE.md and .claude/rules/, drawn from the brief | Jacob Schoenberg (asked for them); written by Claude Code | | So every agent session works to the brief's requirements and scoring. |
| TODO | The project idea | | | |
