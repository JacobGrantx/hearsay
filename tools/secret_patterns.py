"""Secret detection shared by the trace exporter and the presubmit check.

Two layers:
  1. Pattern match for common credential formats.
  2. Exact match for values found in local env files (the repo's .env plus any
     file listed in agent_traces/.redact-env-files). Values are read into memory
     only to find them; they are never printed or written.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Each entry: (compiled pattern, replacement). Replacements keep the key name
# where there is one, so the redacted text still reads sensibly.
_PATTERNS = [
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    r"sk-ant-[A-Za-z0-9_\-]{20,}",
    r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}",
    r"\bgh[pousr]_[A-Za-z0-9]{30,}",
    r"\bgithub_pat_[A-Za-z0-9_]{30,}",
    r"\bglpat-[A-Za-z0-9_\-]{20,}",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bAIza[0-9A-Za-z_\-]{35}",
    r"\bxox[abprs]-[A-Za-z0-9\-]{10,}",
    r"\bya29\.[0-9A-Za-z_\-]{20,}",
    r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
    r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}",
]
SECRET_RES = [re.compile(p) for p in _PATTERNS]

# KEY=value / "key": "value" where the key name says secret and the value looks
# like one (8+ chars with at least one letter and one digit). Keeps the key.
ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Za-z0-9_\-]*(?:api[_\-]?key|secret|token|passw(?:or)?d|private[_\-]?key|access[_\-]?key)[A-Za-z0-9_\-]*)"
    r"([\"']?\s*[=:]\s*[\"']?)"
    r"((?=[^\s\"']*[A-Za-z])(?=[^\s\"']*\d)[^\s\"',;]{8,})"
)

MARK = "[REDACTED:secret]"


def _env_files() -> list[Path]:
    files = [REPO / ".env"]
    listing = REPO / "agent_traces" / ".redact-env-files"
    if listing.exists():
        for line in listing.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                files.append(Path(os.path.expanduser(line)))
    return files


def load_env_values(min_len: int = 8) -> list[str]:
    """Values from local env files, longest first, so they can be matched exactly."""
    values: set[str] = set()
    for f in _env_files():
        try:
            text = f.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            _, _, v = line.partition("=")
            v = v.strip().strip("\"'")
            if len(v) >= min_len:
                values.add(v)
    secret_name = re.compile(r"(?i)(key|token|secret|passw|credential|auth|foundry)")
    for k, v in os.environ.items():
        if secret_name.search(k) and v and len(v) >= min_len:
            values.add(v)
    return sorted(values, key=len, reverse=True)


def redact(text: str, env_values: list[str] | None = None) -> tuple[str, int]:
    """Return (redacted text, number of redactions)."""
    n = 0
    for v in env_values or []:
        if v in text:
            n += text.count(v)
            text = text.replace(v, MARK)
    for rx in SECRET_RES:
        text, k = rx.subn(MARK, text)
        n += k
    text, k = ASSIGNMENT_RE.subn(lambda m: m.group(1) + m.group(2) + MARK, text)
    n += k
    return text, n


def find(text: str, env_values: list[str] | None = None) -> list[str]:
    """Names of the patterns that match, for reporting (never the matched value)."""
    hits = []
    for v in env_values or []:
        if v in text:
            hits.append("value from a local env file")
            break
    for rx in SECRET_RES:
        if rx.search(text):
            hits.append(f"pattern {rx.pattern[:32]}")
    for m in ASSIGNMENT_RE.finditer(text):
        if m.group(3) != MARK and not m.group(3).startswith("[REDACTED"):
            hits.append(f"assignment to {m.group(1)}")
            break
    return hits
