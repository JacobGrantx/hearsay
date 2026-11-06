"""Private-text guard.

The trace exporter redacts private material. This module checks that nothing
private reaches a commit anyway: the pre-commit hook scans staged files, and
`make check` scans the tracked files plus every trace file in the whole history.

What counts as private:
  * terms listed in agent_traces/.redact-terms (gitignored; names from the
    developer's other work), anywhere in the repository;
  * in exported traces only: a harness skill-loading marker, and file paths
    outside this repository (home folders, user config, other projects).

Hits are reported by kind and file, never with the matched text.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TERMS_FILE = REPO / "agent_traces" / ".redact-terms"
HOME = str(Path.home())
REPO_REL = str(REPO.relative_to(HOME)) if REPO.is_relative_to(HOME) else ""

SKILL_MARKER = re.compile(r"Base directory for this skill")
OTHER_SCRATCH = re.compile(r"/dev/shm/(?!dl)[A-Za-z0-9][A-Za-z0-9._-]*")
OUTSIDE_PATH = re.compile(r"(?:" + re.escape(HOME) + r"|~|\$HOME)/([^\s\"'`),;\]]*)")


def load_terms() -> list[re.Pattern]:
    if not TERMS_FILE.exists():
        return []
    terms = []
    for line in TERMS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(line) + r"(?![A-Za-z0-9])", re.I))
    return terms


def _outside_path(rest: str) -> bool:
    """True if a path under the home folder points outside this repository."""
    if REPO_REL and re.match(re.escape(REPO_REL) + r"(?![A-Za-z0-9_.])", rest):
        return False  # this repo or a worktree of it (a following / - \\ or quote ends the name)
    if rest.endswith("…") and REPO_REL.startswith(rest[:-1]):
        return False  # this repo's path, cut short in an event summary
    return True


def find_private(text: str, path: str, terms: list[re.Pattern]) -> list[str]:
    hits = [f"private term #{i + 1}" for i, rx in enumerate(terms) if rx.search(text)]
    if path.startswith("agent_traces/"):
        if SKILL_MARKER.search(text):
            hits.append("skill instructions")
        if any(_outside_path(m.group(1)) for m in OUTSIDE_PATH.finditer(text)):
            hits.append("path outside the repository")
        if OTHER_SCRATCH.search(text):
            hits.append("another project's scratch folder")
    return hits


def scan_files(paths: list[str], read) -> list[str]:
    """read(path) -> text or None. Returns 'path: kinds' lines."""
    terms, out = load_terms(), []
    for p in paths:
        text = read(p)
        if text is None:
            continue
        hits = find_private(text, p, terms)
        if hits:
            out.append(f"{p}: {', '.join(sorted(set(hits)))}")
    return out


def scan_history() -> list[str]:
    """Every version of every trace file in every commit reachable from any ref."""
    objs = subprocess.run(["git", "-C", str(REPO), "rev-list", "--objects", "--all"], capture_output=True, text=True).stdout.splitlines()
    seen, targets = set(), []
    for line in objs:
        sha, _, path = line.partition(" ")
        if path.startswith("agent_traces/") and path.endswith((".jsonl", ".json", ".md")) and sha not in seen:
            seen.add(sha)
            targets.append((sha, path))
    if not targets:
        return []
    proc = subprocess.run(["git", "-C", str(REPO), "cat-file", "--batch"], input=("\n".join(s for s, _ in targets) + "\n").encode(),
                          capture_output=True)
    data, pos, terms, out = proc.stdout, 0, load_terms(), []
    for sha, path in targets:
        header_end = data.index(b"\n", pos)
        size = int(data[pos:header_end].split()[2])
        body = data[header_end + 1: header_end + 1 + size].decode("utf-8", "replace")
        pos = header_end + 1 + size + 1
        hits = find_private(body, path, terms)
        if hits:
            out.append(f"{path} (blob {sha[:7]}): {', '.join(sorted(set(hits)))}")
    return out
