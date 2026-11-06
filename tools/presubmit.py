#!/usr/bin/env python3
"""Check the repository against the Digital Life brief before submitting.

    python3 tools/presubmit.py              full check (brief sections 4 to 13); exit 1 on any FAIL
    python3 tools/presubmit.py --no-tests   skip running the test suite
    python3 tools/presubmit.py --secrets    secret scan of tracked files only
    python3 tools/presubmit.py --staged     secret scan of staged files (used by the pre-commit hook)

Template text is marked TODO. Any TODO left in a judge-facing doc is a FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import secret_patterns  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

JUDGE_DOCS = ["README.md", "AI_DISCLOSURE.md", "EXPERIMENTS.md", "ARCHITECTURE.md", "agent_traces/README.md", "docs/submission.md"]
REQUIRED_FILES = JUDGE_DOCS + ["LICENSE", ".env.example", ".gitignore", "requirements.txt"]
README_SECTIONS = [
    "The idea", "Why digital life", "Demonstration", "Technical architecture", "How it works",
    "Getting started", "Experiments and findings", "AI usage", "Agent traces", "Team", "Future directions",
]
DISCLOSURE_ITEMS = 8
EXPERIMENT_PARTS = ["Hypothesis", "Experimental setup", "Variables or parameters", "Observations", "Results", "What we learned", "What we would investigate next"]
FORBIDDEN_TRACKED = re.compile(r"(^|/)(\.env(\..+)?|.*\.pem|.*\.key|id_rsa.*|credentials.*\.json)$")

results: list[tuple[str, str, str]] = []  # (status, check, detail)


def report(status: str, check: str, detail: str = "") -> None:
    results.append((status, check, detail))


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout


def read(rel: str) -> str:
    p = REPO / rel
    return p.read_text(errors="replace") if p.exists() else ""


def sections(md: str, level: int = 2) -> dict[str, str]:
    """Map heading text -> body for headings of exactly this level."""
    out, cur, buf = {}, None, []
    for line in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m and len(m.group(1)) <= level:
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            cur, buf = (m.group(2).strip() if len(m.group(1)) == level else None), []
        else:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()
    return out


def scan_secrets(paths: list[str], label: str) -> bool:
    env_values = secret_patterns.load_env_values()
    bad = []
    for rel in paths:
        p = REPO / rel
        if FORBIDDEN_TRACKED.search(rel) and not rel.endswith(".env.example"):
            bad.append(f"{rel}: file type should never be committed")
            continue
        if not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        try:
            text = p.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        hits = secret_patterns.find(text, env_values)
        if hits:
            bad.append(f"{rel}: {', '.join(sorted(set(hits)))}")
    if bad:
        report("FAIL", f"No secrets ({label})", "; ".join(bad[:10]) + (f" (+{len(bad) - 10} more)" if len(bad) > 10 else ""))
        return False
    report("PASS", f"No secrets ({label})", f"{len(paths)} files scanned")
    return True


def check_docs() -> None:
    missing = [f for f in REQUIRED_FILES if not (REPO / f).exists()]
    report("FAIL" if missing else "PASS", "Required files present", ", ".join(missing))
    for doc in JUDGE_DOCS:
        n = read(doc).count("TODO")
        if n:
            report("FAIL", f"{doc} completed", f"{n} TODO markers left")

    readme = read("README.md")
    first = next((l for l in readme.splitlines() if l.startswith("# ")), "")
    report("FAIL" if not first or "TODO" in first else "PASS", "README: project name", first[2:].strip())
    secs = sections(readme)
    absent = [s for s in README_SECTIONS if not any(k.lower().startswith(s.lower()) for k in secs)]
    empty = [k for k, v in secs.items() if any(k.lower().startswith(s.lower()) for s in README_SECTIONS) and len(v) < 20]
    report("FAIL" if absent or empty else "PASS", "README: required sections", ("missing " + ", ".join(absent) if absent else "") + (" thin: " + ", ".join(empty) if empty else ""))
    demo = next((v for k, v in secs.items() if k.lower().startswith("demonstration")), "")
    has_media = bool(re.search(r"https?://|\]\((demo|assets)/|<video|\.gif|\.mp4|\.png|\.webm", demo))
    report("PASS" if has_media else "FAIL", "Demonstration provided", "README Demonstration section links a video, GIF, screenshot or live demo" if has_media else "no link or media in the Demonstration section")
    team = next((v for k, v in secs.items() if k.lower().startswith("team")), "")
    report("PASS" if team and "TODO" not in team else "FAIL", "Team and contributors identified")

    disc = sections(read("AI_DISCLOSURE.md"))
    numbered = [k for k in disc if re.match(r"^\d+\.", k)]
    report("PASS" if len(numbered) >= DISCLOSURE_ITEMS else "FAIL", "AI_DISCLOSURE.md: all 8 items", f"{len(numbered)} of {DISCLOSURE_ITEMS} numbered sections")

    exp = read("EXPERIMENTS.md")
    blocks = re.split(r"^## Experiment\b", exp, flags=re.M)[1:]
    if not blocks:
        report("FAIL", "EXPERIMENTS.md: experiments documented", "no '## Experiment' sections")
    for i, b in enumerate(blocks, 1):
        b = re.split(r"^## (?!#)", b, flags=re.M)[0]
        miss = [p for p in EXPERIMENT_PARTS if not re.search(rf"\*\*{re.escape(p)}\.?\*\*|^###\s+{re.escape(p)}", b, re.M)]
        report("FAIL" if miss else "PASS", f"EXPERIMENTS.md: experiment {i} complete", "missing " + ", ".join(miss) if miss else "")
    neg = sections(exp).get("Negative results", "")
    report("PASS" if len(neg) > 40 and "TODO" not in neg else "FAIL", "EXPERIMENTS.md: negative results recorded")

    arch = read("ARCHITECTURE.md")
    report("PASS" if len(arch) > 400 and "TODO" not in arch else "FAIL", "Architecture documented")


def check_traces() -> None:
    sessions = sorted((REPO / "agent_traces" / "sessions").glob("*/manifest.json"))
    if not sessions:
        report("FAIL", "Agent traces included", "no exported sessions; run: python3 tools/export_traces.py --all")
        return
    bad = 0
    for f in (REPO / "agent_traces").rglob("*.jsonl"):
        for line in f.read_text(errors="replace").splitlines():
            if line.strip():
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
    report("FAIL" if bad else "PASS", "Agent traces included", f"{len(sessions)} sessions" + (f", {bad} invalid JSONL lines" if bad else ""))
    tracked = set(git("ls-files", "agent_traces").split())
    untracked = [str(s.parent.relative_to(REPO)) for s in sessions if str(s.relative_to(REPO)) not in tracked]
    if untracked:
        report("WARN", "Agent traces committed", f"{len(untracked)} exported sessions not committed yet")


def check_repro() -> None:
    req = [l.strip() for l in read("requirements.txt").splitlines() if l.strip() and not l.startswith("#")]
    unpinned = [l for l in req if "==" not in l]
    report("WARN" if unpinned else "PASS", "Dependencies pinned", ", ".join(unpinned))
    configs = list((REPO / "experiments" / "configurations").glob("*.toml"))
    noseed = [c.name for c in configs if "seeds" not in c.read_text()]
    report("WARN" if noseed or not configs else "PASS", "Experiment configs with fixed seeds", ", ".join(noseed) or f"{len(configs)} configs")
    readme = read("README.md")
    gs = next((v for k, v in sections(readme).items() if k.lower().startswith("getting started")), "")
    report("PASS" if "```" in gs else "FAIL", "Installation and execution instructions", "" if "```" in gs else "no commands in Getting started")
    mk = read("Makefile")
    if "TODO" in mk:
        report("FAIL", "make demo works", "Makefile still has a TODO (demo target)")
    empty = [str(d.relative_to(REPO)) for d in REPO.rglob("*") if d.is_dir() and ".git" not in d.parts and ".venv" not in d.parts
             and [x.name for x in d.iterdir()] == [".gitkeep"]]
    if empty:
        report("WARN", "No empty placeholder folders", ", ".join(sorted(empty)))


def check_git(run_tests: bool) -> None:
    n = int(git("rev-list", "--count", "HEAD").strip() or 0)
    report("PASS" if n >= 10 else "WARN", "History shows real development", f"{n} commits")
    if git("status", "--porcelain").strip():
        report("WARN", "Working tree clean", "uncommitted changes")
    src = [f for f in git("ls-files", "src").split() if f.endswith(".py") and not f.endswith(("__init__.py", "smoke.py", "runlog.py", "llm.py"))]
    report("PASS" if src else "FAIL", "Source code committed", f"{len(src)} project source files beyond the scaffold")
    url = git("remote", "get-url", "origin").strip()
    m = re.search(r"https?://([^/]+)/(.+?)(\.git)?$", url) or re.search(r"git@([^:]+):(.+?)(\.git)?$", url)
    if not m:
        report("FAIL", "Public repository created", "no origin remote")
    else:
        host, path = m.group(1), m.group(2)
        if host != "github.com":
            report("WARN", "Brief asks for a GitHub URL", f"origin is {host}; confirm the organisers accept it (Jacob's rule: no GitHub)")
        page = f"https://{host}/{path}"

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None

        try:
            code = urllib.request.build_opener(NoRedirect).open(urllib.request.Request(page, method="GET"), timeout=15).status
        except Exception as ex:
            code = getattr(ex, "code", str(ex))
        report("PASS" if code == 200 else "FAIL", "Repository accessible without permissions", f"{page} -> {code} (anonymous; a redirect to sign-in means private)")
        ahead = git("rev-list", "--count", "@{u}..HEAD").strip()
        if ahead and ahead != "0":
            report("WARN", "Pushed", f"{ahead} local commits not pushed")
    if run_tests and (REPO / "tests").exists():
        py = REPO / ".venv" / "bin" / "python"
        r = subprocess.run([str(py if py.exists() else sys.executable), "-m", "pytest", "-q"], cwd=REPO, capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or [""])[-1]
        report("PASS" if r.returncode == 0 else "FAIL", "Tests pass", tail)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--secrets", action="store_true")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--no-tests", action="store_true")
    a = ap.parse_args()

    if a.staged:
        files = [f for f in git("diff", "--cached", "--name-only", "--diff-filter=ACM").splitlines() if f]
        ok = scan_secrets(files, "staged")
        if not ok:
            print("pre-commit: possible secret in staged files. Nothing was committed.\n  " + results[-1][2])
        return 0 if ok else 1

    scan_secrets(git("ls-files").split(), "tracked files")
    if not a.secrets:
        check_docs()
        check_traces()
        check_repro()
        check_git(not a.no_tests)

    width = max(len(c) for _, c, _ in results)
    for status, check, detail in results:
        print(f"{status:4}  {check:<{width}}  {detail}")
    fails = sum(1 for s, _, _ in results if s == "FAIL")
    warns = sum(1 for s, _, _ in results if s == "WARN")
    print(f"\n{fails} FAIL, {warns} WARN")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
