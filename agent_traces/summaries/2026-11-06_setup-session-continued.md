# Setup session, 2026-11-05 evening to 2026-11-06 (hand-written summary, continued)

**This is a manual summary, not an original trace.** The setup session ran from a workspace outside this repository, so its log is not exported (see agent_traces/README.md, "Missing data"). It continues summaries/2026-11-05_scaffold.md. The build itself ran in headless Claude Code sessions started inside the repository, and those are exported in full.

## Jacob's instructions and approvals, in order (quoted where short)
1. Spec approved, build go: "all looks good build" (2026-11-05 evening).
2. While the build ran: change every name and label so model knowledge does not come into play; "fix the leak you have my okay, just want to make sure that this won't happen again"; "Make the runs longer too so we can learn more"; other rules may change once the names are in.
3. Jacob questioned whether the reported work was real. The agent answered by checking the main claims independently (below).
4. Round 2: "yes this works but do longer runs (still need to be done by 11)", and "make sure we are sticking to the original requirements/goals/guidance of the hackathon".
5. Decisions: "gitlab", "private is fine", name "Hearsay".
6. Round 2 amendment 1: "yes/cut".

## What the setup agent did beyond launching the build sessions
- **Orchestration:** it wrote each phase's prompt (phases 1, viewer, 2, 4, 4b, 5, 6, 7a, 7f, then 7b and the final pass), launched them headless inside the repo, watched them with a stall watchdog, and reviewed each report before starting the next.
- **Recovery:** the first phase 1 session timed out on an oversized reply (session 49412096). The agent relaunched it with a smaller output cap and one-file-per-step instructions.
- **Viewer:** it merged the viewer branch and resolved the generated trace-index conflict.
- **Leak:**
  - The phase 5 session reported private text in a trace. The agent found the cause (harness-generated skill text), fixed the exporter, and rewrote history twice with Jacob's okay. The second pass came after a stricter scan found a directory listing naming other projects' folders.
  - It pushed the clean history to a new private project and added the guards: settings deny skills and user config, a pre-commit private-text scan, and a full-history scan in make check.
  - It tested the guards: a planted leak was blocked, and a fresh session could not load skills or read user config.
- **Independent check (after Jacob's question):**
  - It cloned the repository fresh from GitLab, ran setup, tests and `make demo`, and recounted deliveries per run straight from the raw run logs, without the build sessions' analysis code. The counts matched the write-up.
  - It confirmed both pre-registrations were committed before their first AI run (by 42 s and 17 s), and confirmed the E5 transmission sequence line by line from the logs.
  - It found two of its own errors: a privacy-scan test that assumed the repository sits under the home folder, and commit ids in the docs that pointed at first-pass ids after the history rewrite. It corrected both (commit 0a616b1) and re-verified on a second fresh clone: 88 passed, replay identical, every cited id resolves.
- **Independent audit:** a read-only Claude Code subagent with no project context audited the repository against every section of the brief. It reported 11 of 13 checklist items passing (public access and the name failing, before Jacob's decisions), five risks, and ranked fixes. Phase 7f applied the fixes; the subagent changed nothing.
- **Rename of the GitLab project:** project 66 renamed to private-group/hearsay, private, on Jacob's decisions.
- **Round 2 amendment 1:** the agent proposed stopping 4 runs for throughput. Jacob agreed. The agent stopped those processes by id and committed the amendment before any round 2 result was read.
