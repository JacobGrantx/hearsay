# Agent traces, privacy and secrets

Source: docs/challenge-brief.txt section 5. Traces are mandatory. Originals must be preserved. Invented or reconstructed traces are forbidden. Redacted and summarised material must be labelled. Missing data must be documented.

## Hard rules

1. **Build only in sessions started in this repo.** Hooks in `.claude/settings.json` export each session after every turn, so only sessions rooted here are captured. Work done on this repo from a session started elsewhere gets a hand-written summary in `agent_traces/summaries/`, labelled as a manual summary, and an entry under "Missing data" in `agent_traces/README.md`.
2. **Never edit exported traces by hand.** Files under `agent_traces/sessions/`, `agent_traces/events/` and `agent_traces/INDEX.md` are written only by `tools/export_traces.py`. To change what an export contains, change the exporter in a visible commit and re-export.
3. **Commit traces with the work.** Each commit that lands agent-made work includes the updated `agent_traces/`.
4. **Nothing private enters a session.** The repo and every prompt, tool call and tool result in it are public. Keep out:
   - anything about Durable Intelligence's products, Nenya, customers, investors, pipeline, finances or internal tools (this is a personal entry);
   - other repositories' or workspaces' content;
   - personal information about anyone.

   If something private comes up anyway, add the term to `agent_traces/.redact-terms` (gitignored) and re-export before committing.
5. **Secrets.** Never print, echo, cat or log a credential or an env file. Read keys by name only. Runtime credentials come from the environment or `.env` (gitignored). The pre-commit hook and `make check` scan for secrets, and the exporter redacts by pattern and by exact value. A hit is fixed, never bypassed: no `--no-verify`.
6. **No hidden reasoning in traces.** The exporter drops model reasoning blocks, as the brief asks. The decisions themselves go in DECISIONS.md.
7. **Human oversight is visible.** Jacob's prompts and approvals show in the traces. Agent proposals go in DECISIONS.md as proposals until Jacob accepts them.
