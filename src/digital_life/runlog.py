"""Seeding, provenance and logging for experiment runs.

An experiment entrypoint receives a RunLog and uses it to record what happened:
    log.metric(step, population=..., diversity=...)   time series -> metrics.jsonl
    log.event("speciation", step=..., detail=...)     notable behaviour -> events.jsonl
    log.path("snapshot.json")                         where to write any artefact
"""
from __future__ import annotations

import json
import os
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def seed_everything(seed: int) -> None:
    """Seed every random source we know about. Add new libraries here when they come in."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)  # affects subprocesses, not this process
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass


def provenance() -> dict:
    """Everything needed to tell which code and environment produced a result."""

    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""

    packages = {}
    for name in ("numpy", "scipy", "torch", "networkx", "matplotlib", "anthropic"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    return {
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": packages,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunLog:
    def __init__(self, out_dir: Path) -> None:
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._metrics = (self.dir / "metrics.jsonl").open("a")
        self._events = (self.dir / "events.jsonl").open("a")

    def metric(self, step: int, **values) -> None:
        self._metrics.write(json.dumps({"step": step, **values}) + "\n")

    def event(self, kind: str, **data) -> None:
        self._events.write(json.dumps({"kind": kind, **data}) + "\n")

    def path(self, name: str) -> Path:
        return self.dir / name

    def close(self) -> None:
        self._metrics.close()
        self._events.close()
