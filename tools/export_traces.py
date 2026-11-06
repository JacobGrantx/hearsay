#!/usr/bin/env python3
"""Export Claude Code session logs for this repository into agent_traces/.

Runs automatically from the Stop and SessionEnd hooks in .claude/settings.json.
By hand:
    python3 tools/export_traces.py --all            every session run in this repo
    python3 tools/export_traces.py --transcript F   one session log file

What happens to the original logs (and nothing else):
  kept       user, assistant and system entries: prompts, replies, tool calls,
             tool results, permission decisions, API errors, compaction marks;
             subagent logs with their launch metadata
  omitted    harness bookkeeping entries (attachments, request blobs, file
             snapshots, queue and title records), counted per type in manifest.json
  replaced   model reasoning ("thinking" blocks), per brief section 5
             <system-reminder> blocks (harness-injected private user config and memory)
             IDE selections, inline images
             secrets (patterns and exact values from local env files)
             terms listed in agent_traces/.redact-terms
             each with a visible [REDACTED:<reason>] or [OMITTED:<reason>] marker
  truncated  tool results longer than MAX_RESULT_CHARS, with a visible marker

Outputs per session:
  agent_traces/sessions/<date>_<session-id>/main.jsonl          filtered original entries
  agent_traces/sessions/<date>_<session-id>/subagents/*.jsonl   same, per subagent
  agent_traces/sessions/<date>_<session-id>/manifest.json       provenance, usage, redaction counts, commits
  agent_traces/events/<date>_<session-id>.events.jsonl          one event per line, brief's suggested schema
and agent_traces/INDEX.md across sessions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import secret_patterns  # noqa: E402

EXPORTER_VERSION = 1
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "agent_traces"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
# Unmodified originals are copied here, outside the repo, so the hashes in each
# manifest can be checked later (Claude Code deletes old logs on its own).
RAW_ARCHIVE = Path(os.environ.get("DL_RAW_TRACE_ARCHIVE", Path.home() / "work" / "hackathons" / ".digital-life-raw-logs"))
MAX_RESULT_CHARS = 40_000
SUMMARY_CHARS = 280

KEEP_TYPES = {"user", "assistant", "system"}
ENTRY_KEYS = [
    "type", "subtype", "level", "uuid", "parentUuid", "sessionId", "agentId",
    "timestamp", "isSidechain", "isMeta", "entrypoint", "gitBranch", "version", "origin", "promptSource",
    "permissionMode", "permissionDecision", "content",
]
MESSAGE_KEYS = ["role", "model", "id", "content", "stop_reason", "usage"]
SUBAGENT_META_KEYS = ["agentType", "description", "toolUseId", "spawnDepth", "pickedEffortModel"]

REMINDER_RE = re.compile(r"<system-reminder>[\s\S]*?</system-reminder>")
IDE_SELECTION_RE = re.compile(r"<ide_selection>[\s\S]*?</ide_selection>")
COMMIT_RE = re.compile(r"^\[[^\]\n]*?\b([0-9a-f]{7,40})\]", re.M)
# Paths outside this repository (home folders, user config, other projects) say nothing about
# this project and can reveal private setup, so they are redacted. /tmp and /dev/shm stay.
PRIVATE_PATH_RE = re.compile(
    r"(?:" + re.escape(str(Path.home())) + r"|~|\$HOME)/(?!work/hackathons/digital-life\b)[^\s\"'`),;\]]+"
)


def encode_project_path(p: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(p))


class Redactor:
    def __init__(self) -> None:
        self.env_values = secret_patterns.load_env_values()
        terms_file = OUT / ".redact-terms"
        self.terms = []
        if terms_file.exists():
            for line in terms_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self.terms.append(re.compile(re.escape(line), re.I))
        self.counts: Counter = Counter()

    def text(self, s: str, harness: bool = True) -> str:
        """harness=False for agent-authored text (tool inputs), where tags are code, not injections."""
        if harness:
            s, n = REMINDER_RE.subn("[REDACTED:harness-context]", s)
            self.counts["harness-context"] += n
            s, n = IDE_SELECTION_RE.subn("[REDACTED:ide-selection]", s)
            self.counts["ide-selection"] += n
        s, n = secret_patterns.redact(s, self.env_values)
        self.counts["secret"] += n
        s, n = PRIVATE_PATH_RE.subn("[REDACTED:path-outside-repo]", s)
        self.counts["path-outside-repo"] += n
        for rx in self.terms:
            s, n = rx.subn("[REDACTED:private]", s)
            self.counts["private"] += n
        return s

    def deep(self, obj):
        """Redact secrets and private terms in every string of a JSON-like value (tool inputs)."""
        if isinstance(obj, str):
            return self.text(obj, harness=False)
        if isinstance(obj, list):
            return [self.deep(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.deep(v) for k, v in obj.items()}
        return obj


def _truncate(s: str, stats: Counter) -> str:
    if len(s) > MAX_RESULT_CHARS:
        stats["truncated"] += 1
        return s[:MAX_RESULT_CHARS] + f"\n[TRUNCATED: {len(s) - MAX_RESULT_CHARS} more characters in the original]"
    return s


def clean_blocks(content, red: Redactor, stats: Counter):
    if isinstance(content, str):
        return _truncate(red.text(content), stats)
    if not isinstance(content, list):
        return content
    out = []
    for b in content:
        if not isinstance(b, dict):
            out.append(b)
            continue
        t = b.get("type")
        if t in ("thinking", "redacted_thinking"):
            stats["thinking_omitted"] += 1
            out.append({"type": "thinking", "omitted": "[OMITTED:model-reasoning]"})
        elif t == "text":
            txt = red.text(b.get("text", ""))
            if txt.strip() and txt.strip() != "[REDACTED:harness-context]":
                out.append({"type": "text", "text": _truncate(txt, stats)})
            else:
                stats["harness_only_blocks"] += 1
        elif t == "image":
            out.append({"type": "image", "omitted": "[OMITTED:image]"})
        elif t == "tool_use":
            out.append({"type": "tool_use", "id": b.get("id"), "name": b.get("name"), "input": red.deep(b.get("input"))})
        elif t == "tool_result":
            nb = {"type": "tool_result", "tool_use_id": b.get("tool_use_id"), "content": clean_blocks(b.get("content"), red, stats)}
            if b.get("is_error"):
                nb["is_error"] = True
            out.append(nb)
        else:
            stats[f"block_omitted:{t}"] += 1
            out.append({"type": t, "omitted": "[OMITTED:unrecognised-block]"})
    return out


def clean_entry(e: dict, red: Redactor, stats: Counter) -> dict | None:
    out = {k: e[k] for k in ENTRY_KEYS if k in e}
    m = e.get("message")
    if e.get("type") == "user" and e.get("isMeta") and isinstance(m, dict):
        # Harness-generated messages (skill instructions, command output, reminders) carry the
        # developer's private configuration, not the human or the agent. Keep the entry, drop the text.
        stats["harness_meta_redacted"] += 1
        red.counts["harness-meta"] += 1
        out["message"] = {"role": m.get("role", "user"), "content": [{"type": "text", "text": "[REDACTED:harness-meta]"}]}
        return out
    if isinstance(out.get("content"), str):
        out["content"] = _truncate(red.text(out["content"]), stats)
    m = e.get("message")
    if isinstance(m, dict):
        nm = {k: m[k] for k in MESSAGE_KEYS if k in m}
        nm["content"] = clean_blocks(m.get("content"), red, stats)
        if nm["content"] == [] or nm["content"] == "[REDACTED:harness-context]":
            return None  # entry carried nothing but injected harness context
        out["message"] = nm
    return out


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    parts.append(b.get("text", ""))
                elif b.get("type") == "tool_result":
                    parts.append(_text_of(b.get("content")))
        return "\n".join(parts)
    return ""


def _short(s: str) -> str:
    s = " ".join(s.split())
    return s if len(s) <= SUMMARY_CHARS else s[: SUMMARY_CHARS - 1] + "…"


def to_events(entries: list[dict], session_id: str, agent_id: str) -> tuple[list[dict], dict]:
    """Normalise cleaned entries into the brief's suggested event schema."""
    events, tool_names, tool_inputs = [], {}, {}
    facts = {"human_prompts": 0, "unmarked_prompts": 0, "tool_calls": Counter(), "commits": [], "models": Counter(), "permission_decisions": Counter()}
    model = None
    for e in entries:
        base = {"timestamp": e.get("timestamp"), "session_id": session_id, "agent_id": agent_id, "source_uuid": e.get("uuid")}
        t = e.get("type")
        msg = e.get("message") or {}
        content = msg.get("content")
        if t == "assistant":
            model = msg.get("model") or model
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "text":
                    events.append({**base, "model": model, "event_type": "assistant_message", "output_summary": _short(b["text"]), "human_intervention": False})
                elif b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    tool_names[b.get("id")] = b.get("name")
                    tool_inputs[b.get("id")] = inp
                    facts["tool_calls"][b.get("name")] += 1
                    kind = "agent_spawn" if b.get("name") in ("Agent", "Task") else "tool_call"
                    task = inp.get("description") if isinstance(inp, dict) else None
                    events.append({**base, "model": model, "event_type": kind, "task": task, "tool": b.get("name"), "tool_use_id": b.get("id"), "input_summary": _short(json.dumps(inp, ensure_ascii=False)), "human_intervention": False})
            if model:
                facts["models"][model] += 1
        elif t == "user":
            origin = (e.get("origin") or {}).get("kind") if isinstance(e.get("origin"), dict) else None
            pd = e.get("permissionDecision")
            if isinstance(pd, dict):
                facts["permission_decisions"][f"{pd.get('decision')}/{pd.get('source')}"] += 1
                human = "user" in str(pd.get("source", "")).lower()
                events.append({**base, "model": model, "event_type": "permission_decision", "decision": pd.get("decision"), "decided_by": pd.get("source"), "human_intervention": human})
            results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] if isinstance(content, list) else []
            if results:
                for b in results:
                    name = tool_names.get(b.get("tool_use_id"))
                    out = _text_of(b.get("content"))
                    ev = {**base, "model": model, "event_type": "tool_error" if b.get("is_error") else "tool_result", "tool": name, "tool_use_id": b.get("tool_use_id"), "output_summary": _short(out), "human_intervention": False}
                    cmd = (tool_inputs.get(b.get("tool_use_id")) or {}).get("command", "") if name == "Bash" else ""
                    if "git commit" in cmd and not b.get("is_error"):
                        m = COMMIT_RE.search(out)
                        if m:
                            ev["commit"] = m.group(1)
                            facts["commits"].append({"commit": m.group(1), "tool_use_id": b.get("tool_use_id"), "timestamp": e.get("timestamp")})
                    events.append(ev)
            else:
                txt = _text_of(content)
                if origin == "human":
                    facts["human_prompts"] += 1
                    events.append({**base, "event_type": "human_prompt", "input_summary": _short(txt), "human_intervention": True})
                elif origin == "peer":
                    events.append({**base, "event_type": "agent_to_agent", "input_summary": _short(txt), "human_intervention": False})
                elif origin is None and not e.get("isMeta") and txt.strip():
                    # A prompt the log does not attribute: headless runs (claude -p) and some older entries.
                    # Who wrote it is not recorded, so it is not claimed as human.
                    facts["unmarked_prompts"] += 1
                    events.append({**base, "event_type": "prompt", "prompt_origin": "unmarked", "input_summary": _short(txt), "human_intervention": None})
                elif txt.strip():
                    events.append({**base, "event_type": "harness_message", "origin": origin or "meta", "input_summary": _short(txt), "human_intervention": False})
        elif t == "system":
            sub = e.get("subtype") or "system"
            events.append({**base, "event_type": "error" if "error" in sub else f"system:{sub}", "output_summary": _short(str(e.get("content", ""))), "human_intervention": False})
    return events, facts


def _read_jsonl(path: Path) -> tuple[list[dict], int]:
    rows, bad = [], 0
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1
    return rows, bad


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ""


def _usage(rows: list[dict]) -> dict:
    by_id = {}
    for e in rows:
        m = e.get("message")
        if e.get("type") == "assistant" and isinstance(m, dict) and isinstance(m.get("usage"), dict):
            by_id[m.get("id") or e.get("uuid")] = m["usage"]
    keys = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]
    tot = {k: sum(int(u.get(k) or 0) for u in by_id.values()) for k in keys}
    tot["api_responses"] = len(by_id)
    tot["note"] = "Summed from the usage field of each API response in the original log, one count per response id. Not estimated."
    return tot


def _clean_log(rows: list[dict], red: Redactor, stats: Counter) -> tuple[list[dict], Counter]:
    omitted, kept = Counter(), []
    for e in rows:
        t = e.get("type")
        if t not in KEEP_TYPES:
            omitted[str(t)] += 1
            continue
        c = clean_entry(e, red, stats)
        if c is None:
            omitted[f"{t}:harness-context-only"] += 1
            continue
        kept.append(c)
    return kept, omitted


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def export_session(transcript: Path) -> dict | None:
    rows, bad = _read_jsonl(transcript)
    session_id = transcript.stem
    stamps = [e.get("timestamp") for e in rows if e.get("timestamp")]
    if not stamps or not any(e.get("type") in ("user", "assistant") for e in rows):
        return None
    first, last = min(stamps), max(stamps)
    name = f"{first[:10]}_{session_id}"
    sdir = OUT / "sessions" / name
    archive_raw(transcript)

    red, stats = Redactor(), Counter()
    kept, omitted = _clean_log(rows, red, stats)
    events, facts = to_events(kept, session_id, "main")
    _write_jsonl(sdir / "main.jsonl", kept)

    subagents = []
    sub_dir = transcript.parent / session_id / "subagents"
    for sf in sorted(sub_dir.glob("*.jsonl")) if sub_dir.exists() else []:
        srows, sbad = _read_jsonl(sf)
        skept, somitted = _clean_log(srows, red, stats)
        sevents, sfacts = to_events(skept, session_id, sf.stem)
        _write_jsonl(sdir / "subagents" / sf.name, skept)
        events.extend(sevents)
        meta = {}
        mf = sf.with_suffix(".meta.json")
        if mf.exists():
            try:
                raw = json.loads(mf.read_text())
                meta = red.deep({k: raw[k] for k in SUBAGENT_META_KEYS if k in raw})
            except json.JSONDecodeError:
                pass
        stamps_s = [e.get("timestamp") for e in srows if e.get("timestamp")]
        subagents.append({
            "agent_id": sf.stem, **meta,
            "source_sha256": _sha256(sf), "source_lines": len(srows), "unparseable_lines": sbad,
            "first_timestamp": min(stamps_s) if stamps_s else None, "last_timestamp": max(stamps_s) if stamps_s else None,
            "usage": _usage(srows), "tool_calls": dict(sfacts["tool_calls"]), "omitted_entries": dict(somitted),
            "commits": sfacts["commits"],
        })
        for k in ("tool_calls", "models", "permission_decisions"):
            facts[k].update(sfacts[k])
        facts["commits"].extend(sfacts["commits"])

    events.sort(key=lambda ev: ev.get("timestamp") or "")
    _write_jsonl(OUT / "events" / f"{name}.events.jsonl", events)

    window = _git("log", f"--since={first}", f"--until={last}", "--format=%H %s").strip().splitlines()
    ext_results = transcript.parent / session_id / "tool-results"
    manifest = {
        "session_id": session_id,
        "exporter_version": EXPORTER_VERSION,
        "agent_tool": "Claude Code",
        "claude_code_versions": sorted({e.get("version") for e in rows if e.get("version")}),
        "models": dict(facts["models"]),
        "first_timestamp": first,
        "last_timestamp": last,
        "source": {"file": transcript.name, "sha256": _sha256(transcript), "lines": len(rows), "unparseable_lines": bad},
        "usage_main_agent": _usage(rows),
        "human_prompts": facts["human_prompts"],
        "unmarked_prompts": facts["unmarked_prompts"],
        "permission_decisions": dict(facts["permission_decisions"]),
        "tool_calls": dict(facts["tool_calls"]),
        "subagents": subagents,
        "commits_made_in_session": facts["commits"],
        "commits_in_time_window": window,
        "kept_entries": len(kept),
        "omitted_entries": dict(omitted),
        "redactions": {k: v for k, v in red.counts.items() if v},
        "transformations": dict(stats),
        "missing": {
            "tool_results_stored_outside_log": len(list(ext_results.glob("*"))) if ext_results.exists() else 0,
            "note": "Large tool outputs that Claude Code stored outside the session log are not exported; the log keeps its reference to them.",
        },
    }
    (sdir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def archive_raw(transcript: Path) -> None:
    """Keep a private, unmodified copy of the session log and its subagent logs (never committed)."""
    try:
        dest = RAW_ARCHIVE / transcript.stem
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(transcript, dest / transcript.name)
        sub = transcript.parent / transcript.stem / "subagents"
        if sub.exists():
            shutil.copytree(sub, dest / "subagents", dirs_exist_ok=True)
    except OSError:
        pass


def write_index() -> None:
    rows = []
    manifests = [(mf, json.loads(mf.read_text())) for mf in (OUT / "sessions").glob("*/manifest.json")]
    for mf, m in sorted(manifests, key=lambda x: x[1].get("first_timestamp", "")):
        u = m.get("usage_main_agent", {})
        sub_in = sum(s.get("usage", {}).get("input_tokens", 0) + s.get("usage", {}).get("cache_read_input_tokens", 0) + s.get("usage", {}).get("cache_creation_input_tokens", 0) for s in m.get("subagents", []))
        sub_out = sum(s.get("usage", {}).get("output_tokens", 0) for s in m.get("subagents", []))
        tin = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + sub_in
        tout = u.get("output_tokens", 0) + sub_out
        commits = [c["commit"][:7] for c in m.get("commits_made_in_session", [])]
        rows.append(
            f"| {m['first_timestamp'][:16].replace('T', ' ')} | [{m['session_id'][:8]}](sessions/{mf.parent.name}/) "
            f"| {', '.join(m.get('models', {})) or '-'} | {m.get('human_prompts', 0)} | {sum(m.get('tool_calls', {}).values())} "
            f"| {len(m.get('subagents', []))} | {tin:,} / {tout:,} | {', '.join(commits) or '-'} |"
        )
    body = [
        "# Agent session index",
        "",
        "Generated by `tools/export_traces.py` from the original Claude Code logs. Do not edit by hand.",
        "Tokens are summed from the API usage records in each log (input includes cache reads and writes).",
        "",
        "| Started (UTC) | Session | Models | Human prompts | Tool calls | Subagents | Tokens in / out | Commits made |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    (OUT / "INDEX.md").write_text("\n".join(body))


def project_logs() -> list[Path]:
    enc = encode_project_path(REPO)
    files = []
    if CLAUDE_PROJECTS.exists():
        for d in CLAUDE_PROJECTS.iterdir():
            if d.is_dir() and (d.name == enc or d.name.startswith(enc + "-")):
                files.extend(sorted(d.glob("*.jsonl")))
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hook", action="store_true", help="read the hook payload on stdin and export that session")
    ap.add_argument("--all", action="store_true", help="export every session log for this repo")
    ap.add_argument("--transcript", type=Path, help="export one session log file")
    a = ap.parse_args()

    if a.hook:
        try:
            payload = json.load(sys.stdin)
            tp = Path(payload["transcript_path"]).expanduser()
            if tp.exists():
                export_session(tp)
                write_index()
        except Exception:
            # A hook must never break the session. Log and move on.
            with (OUT / ".export.log").open("a") as f:
                f.write(traceback.format_exc() + "\n")
        return 0

    targets = [a.transcript] if a.transcript else project_logs() if a.all else []
    if not targets:
        ap.print_help()
        return 1
    n = 0
    for t in targets:
        if export_session(t):
            n += 1
    write_index()
    print(f"exported {n} session(s) to {OUT.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
