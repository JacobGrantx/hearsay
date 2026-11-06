"""Exported traces must keep the development record and drop what the brief says not to publish."""
import json

import export_traces as et

FAKE_KEY = "sk-ant-api03-" + "x1" * 20


def write_log(path, entries):
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")


def sample_log():
    ts = "2026-11-06T10:00:0{}Z"
    return [
        {"type": "attachment", "attachment": {"type": "instructions", "content": "private user config"}, "timestamp": ts.format(0), "uuid": "a0"},
        {"type": "user", "uuid": "u1", "timestamp": ts.format(1), "sessionId": "s", "origin": {"kind": "human"},
         "message": {"role": "user", "content": "<system-reminder>global CLAUDE.md here</system-reminder>Build the organism grid"}},
        {"type": "assistant", "uuid": "a1", "timestamp": ts.format(2), "sessionId": "s",
         "message": {"role": "assistant", "model": "claude-opus-5-5", "id": "m1", "usage": {"input_tokens": 10, "output_tokens": 5},
                     "content": [{"type": "thinking", "thinking": "secret reasoning", "signature": "zzz"},
                                 {"type": "text", "text": "Writing it now."},
                                 {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": f"git commit -m 'grid' && echo ANTHROPIC_API_KEY={FAKE_KEY}", "description": "Commit grid"}}]}},
        {"type": "user", "uuid": "u2", "timestamp": ts.format(3), "sessionId": "s", "permissionDecision": {"decision": "allow", "source": "user"},
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                                  "content": [{"type": "text", "text": "[main abc1234] grid\n 1 file changed"},
                                                              {"type": "image", "source": {"data": "AAAA"}}]}]}},
        {"type": "api-request-blob", "uuid": "r1", "timestamp": ts.format(4)},
    ]


def test_export_keeps_record_and_strips_private(tmp_path, monkeypatch):
    monkeypatch.setattr(et, "OUT", tmp_path / "agent_traces")
    monkeypatch.setattr(et, "RAW_ARCHIVE", tmp_path / "raw")
    log = tmp_path / "s.jsonl"
    write_log(log, sample_log())
    m = et.export_session(log)

    text = (tmp_path / "agent_traces" / "sessions" / "2026-11-06_s" / "main.jsonl").read_text()
    assert "Build the organism grid" in text           # human prompt kept
    assert "global CLAUDE.md" not in text              # injected config removed
    assert "[REDACTED:harness-context]" in text
    assert "secret reasoning" not in text              # thinking removed
    assert "[OMITTED:model-reasoning]" in text
    assert FAKE_KEY not in text                        # secret removed
    assert "AAAA" not in text                          # image data removed
    assert "private user config" not in text           # attachment entries omitted
    assert m["omitted_entries"]["attachment"] == 1
    assert m["human_prompts"] == 1
    assert m["usage_main_agent"]["output_tokens"] == 5
    assert m["commits_made_in_session"][0]["commit"] == "abc1234"
    assert (tmp_path / "raw" / "s" / "s.jsonl").read_text() == log.read_text()   # original kept unmodified

    events = [json.loads(l) for l in (tmp_path / "agent_traces" / "events" / "2026-11-06_s.events.jsonl").read_text().splitlines()]
    kinds = [e["event_type"] for e in events]
    assert kinds == ["human_prompt", "assistant_message", "tool_call", "permission_decision", "tool_result"]
    assert events[3]["human_intervention"] is True
    assert events[4]["commit"] == "abc1234"
    assert all(FAKE_KEY not in json.dumps(e) for e in events)


def test_assignment_check_reads_json_escapes_as_line_ends():
    import secret_patterns as sp

    code_in_trace = r'"usage=SimpleNamespace(input_tokens=1, cache_creation_input_tokens=0))\nreturn x2\n"'
    assert not sp.find(code_in_trace)
    leaked = r'"export MY_API' + r'_KEY=abcd1234efgh5678\nnext line"'  # split so the hook does not flag this file
    assert sp.find(leaked)


def test_harness_meta_and_outside_paths_are_redacted(tmp_path, monkeypatch):
    monkeypatch.setattr(et, "OUT", tmp_path / "agent_traces")
    monkeypatch.setattr(et, "RAW_ARCHIVE", tmp_path / "raw")
    from pathlib import Path as P
    home = str(P.home())
    entries = [
        {"type": "user", "uuid": "u1", "timestamp": "2026-11-06T10:00:01Z", "sessionId": "m", "origin": {"kind": "human"},
         "message": {"role": "user", "content": "run the thing"}},
        {"type": "user", "uuid": "u2", "timestamp": "2026-11-06T10:00:02Z", "sessionId": "m", "isMeta": True,
         "message": {"role": "user", "content": [{"type": "text", "text": "Base directory for this skill: " + home + "/.claude/skills/x  secret playbook"}]}},
        {"type": "assistant", "uuid": "a1", "timestamp": "2026-11-06T10:00:03Z", "sessionId": "m",
         "message": {"role": "assistant", "model": "m", "id": "x", "content": [{"type": "tool_use", "id": "t1", "name": "Bash",
                     "input": {"command": "cat " + home + "/.config/other/.env; ls " + home + "/work/hackathons/digital-life/src"}}]}},
    ]
    log = tmp_path / "m.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    et.export_session(log)
    text = (tmp_path / "agent_traces" / "sessions" / "2026-11-06_m" / "main.jsonl").read_text()
    assert "secret playbook" not in text and "[REDACTED:harness-meta]" in text
    assert "/.config/other" not in text and "[REDACTED:path-outside-repo]" in text
    assert "digital-life/src" in text          # paths inside the repo stay
    assert "run the thing" in text             # the human prompt stays


def test_private_scan_catches_leaks_and_spares_the_repo(tmp_path, monkeypatch):
    import private_scan as ps
    from pathlib import Path as P
    home, repo_rel = str(P.home()), ps.REPO_REL
    terms = [__import__("re").compile("acme-secret-project", __import__("re").I)]
    assert ps.find_private("notes about acme-secret-project", "README.md", terms) == ["private term #1"]
    assert "skill instructions" in ps.find_private("Base directory for this skill: x", "agent_traces/events/a.jsonl", [])
    assert "path outside the repository" in ps.find_private(f"cat {home}/.config/x/.env", "agent_traces/sessions/a/main.jsonl", [])
    assert ps.find_private(f"ls {ps.REPO}/src", "agent_traces/sessions/a/main.jsonl", []) == []
    if repo_rel:  # only meaningful when the repo sits under the home folder
        assert ps.find_private(f"cd {home}/{repo_rel[:10]}…", "agent_traces/events/a.jsonl", []) == []
    assert ps.find_private(f"cat {home}/.config/x/.env", "README.md", []) == []   # paths are only checked in traces


def test_private_scan_scratch_folders():
    import private_scan as ps
    assert ps.find_private("ls /dev/shm/other-project", "agent_traces/events/a.jsonl", []) == ["another project's scratch folder"]
    assert ps.find_private("cd /dev/shm/dl-r2/x", "agent_traces/events/a.jsonl", []) == []
    assert ps.find_private("round2.py > /dev/shm/d…", "agent_traces/events/a.jsonl", []) == []   # cut-short dl- path
