# Agent traces

Development provenance for brief section 5. Everything under `sessions/` and `events/` was exported by a program from the original Claude Code session logs. Nothing was written or reconstructed by hand. Hand-written material lives only in `summaries/` and says so at the top.

## How traces are captured

Claude Code writes a JSONL log of every session. `tools/export_traces.py` runs from the `Stop` and `SessionEnd` hooks in `.claude/settings.json`, so each session is re-exported after every turn and once more when it ends. It can also be run by hand: `python3 tools/export_traces.py --all`.

## What is here

| Path | What it is |
|---|---|
| `INDEX.md` | One row per session: start time, models, human prompts, tool calls, subagents, token usage, commits made. Generated. |
| `sessions/<date>_<session-id>/main.jsonl` | The session's original log entries after the filtering below. Original field names and order. |
| `sessions/<date>_<session-id>/subagents/*.jsonl` | Same, for each subagent the session launched. |
| `sessions/<date>_<session-id>/manifest.json` | Provenance: SHA-256 and line count of the original log, Claude Code version, models, token usage, permission decisions, tool-call counts, subagent tasks, commits, and counts of everything omitted or redacted. |
| `events/<date>_<session-id>.events.jsonl` | The same session normalised to the brief's suggested schema, one event per line: `timestamp, session_id, agent_id, model, event_type, task, tool, input_summary, output_summary, human_intervention`, plus `source_uuid` pointing back to the original entry and `commit` where a tool call made one. |
| `summaries/` | Hand-written summaries, labelled as such. |

Event types: `human_prompt` (the log marks it as typed by a person), `prompt` (the log does not say who wrote it, e.g. headless `claude -p` runs; `human_intervention` is null), `assistant_message`, `tool_call`, `agent_spawn`, `tool_result`, `tool_error`, `permission_decision`, `agent_to_agent`, `harness_message`, `error`, `system:<subtype>`.

## What was changed from the originals, and why

| Change | Marker | Why |
|---|---|---|
| Model reasoning blocks removed | `[OMITTED:model-reasoning]` | The brief asks for execution traces, not hidden chain-of-thought. |
| Context the harness injects into prompts (the developer's private global configuration and memory) removed | `[REDACTED:harness-context]` | Private material unrelated to this project. This project's own agent instructions are public in `CLAUDE.md`. |
| Editor selections removed | `[REDACTED:ide-selection]` | May contain content from outside this repo. |
| Secrets removed, by pattern and by exact match against local env files | `[REDACTED:secret]` | The brief forbids credentials. |
| Listed private terms removed | `[REDACTED:private]` | Personal or third-party information. |
| Harness-generated messages (skill instructions, command output, reminders) emptied; the entry is kept | `[REDACTED:harness-meta]` | They carry the developer's private configuration, not the human's or the agent's words. |
| File paths outside this repository removed | `[REDACTED:path-outside-repo]` | They name the developer's private setup and other projects. |
| Names of other projects' scratch folders removed | `/dev/shm/[REDACTED:other-scratch]` | A directory listing named other projects' scratch folders. |
| Inline images removed | `[OMITTED:image]` | Size. Screenshots that matter are in `demo/`. |
| Unrecognised content blocks replaced, for example `tool_reference` blocks from tool search | `[OMITTED:unrecognised-block]` | Harness-internal block types that are not development activity. Counted in `manifest.json` → `transformations`. |
| Only a fixed list of entry fields is kept (`ENTRY_KEYS` in tools/export_traces.py: type, ids, timestamps, origin, permission decisions, message, and since 2026-11-06 the API error and retry fields) | (fields absent) | The other fields are harness bookkeeping. Field names and values that are kept are unchanged from the original log. |
| Tool results over 40,000 characters truncated | `[TRUNCATED: n more characters]` | Size. |
| Harness bookkeeping entries dropped (request blobs, file snapshots, titles, queue records, attachments) | counted per type in `manifest.json` → `omitted_entries` | Not development activity. Several duplicate the full request, including the private context above. |

Every count (including omitted images, since 2026-11-06) is in each `manifest.json` under `redactions`, `transformations` and `omitted_entries`. The manifest's `source.sha256` is the hash of the unmodified original log. The exporter keeps a private copy of every original outside the repository, so the export can be checked against it on request.

## Linking agent work to code

- `commits_made_in_session` in each manifest, and the `commit` field on events, come from `git commit` tool calls whose output printed a hash.
- `commits_in_time_window` lists every commit made between the session's first and last timestamp.

## Missing data

- **The repository scaffold and project rules** (trace exporter, experiment runner, model wrapper, presubmit check, doc templates, CLAUDE.md and .claude/rules/) were generated by Claude Code on 2026-11-05, in a session started from a private workspace before this repo existed. That session also covered unrelated private work, so its log is not included. A hand-written summary is in `summaries/2026-11-05_scaffold.md`.
- **The setup session's later turns.** The same private-workspace session discussed the idea and the spec with Jacob, then wrote the prompts for every headless build session and launched them (phase 1 twice, the viewer, phase 2, phase 4, phase 4b and phase 5, the demo video). Those prompts are in the build sessions' own logs (as unmarked prompts, since no human typed them), but the setup session's log is not included, for the reason above. The summary covers it up to the first build launch.
- **The failed first phase 1 session** (`49412096`, 2026-11-06 07:54 to 09:07 UTC) is included as exported. It made 8 tool calls and no commits, then one reply was too large and the request timed out, which ended the session. Its last reply never arrived, so it is not in the log; Claude Code's own "Request timed out" message is. Phase 1 was restarted from scratch as `c9529ee6`.
- **Commit links.** The build sessions committed with `git commit -q`, which prints no hash, so `commits_made_in_session` is empty for them. Their commits are listed under `commits_in_time_window` in each manifest, and every commit message names what it contains.
- **Model reasoning** is omitted by design (see above), so where an agent's choice is not explained in its messages, the explanation is in DECISIONS.md or not available.
- **Runtime model calls** are not agent traces, but the same rule applies: the bee minds' requests and responses are kept in `experiments/llm_cache/`. Which runs' responses are committed, and which are not, is listed in EXPERIMENTS.md, "Replay and reproducibility".
- Large tool outputs that Claude Code stores outside the session log are not exported. Each manifest counts them under `missing`.
- **Phase 5 session (`954b5b7b`), a skill's text.** The session loaded a writing-style skill from the developer's private setup (for the README prose pass). Its instructions name the developer's company products, internal tools and a colleague, so those terms are `[REDACTED:private]` in the export. One earlier export of this session, in commit 3e5d4e3, was committed before the terms were listed. The history was then rewritten once to remove that text and the outside paths from every trace file in every commit; what was changed, how it was checked, and a table translating old commit ids to new ones are in [docs/methodology/history-rewrite.md](../docs/methodology/history-rewrite.md). The id 3e5d4e3 is the one after the rewrite.
- No other AI tools or chat assistants were used in sessions recorded here. What is known about AI use outside these sessions is in AI_DISCLOSURE.md, item 1.
