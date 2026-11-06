"""The experiment runner must be reproducible: same seed, same numbers."""
import json
from pathlib import Path

from experiments.run import run

SMOKE = Path(__file__).resolve().parent.parent / "experiments" / "configurations" / "smoke.toml"


def metrics(run_dir: Path, seed: int) -> list[dict]:
    return [json.loads(l) for l in (run_dir / f"seed-{seed}" / "metrics.jsonl").read_text().splitlines()]


def test_same_seed_same_result(tmp_path):
    a = run(SMOKE, seeds=[7], results_root=tmp_path / "a")
    b = run(SMOKE, seeds=[7], results_root=tmp_path / "b")
    assert metrics(a, 7) == metrics(b, 7)


def test_different_seeds_differ(tmp_path):
    out = run(SMOKE, seeds=[1, 2], results_root=tmp_path)
    assert metrics(out, 1) != metrics(out, 2)


def test_run_record_has_provenance(tmp_path):
    out = run(SMOKE, seeds=[0], results_root=tmp_path, overrides=["steps=5"])
    rec = json.loads((out / "seed-0" / "record.json").read_text())
    assert rec["params"]["steps"] == 5
    assert rec["error"] is None
    assert {"git_commit", "git_dirty", "python"} <= rec["provenance"].keys()
    summary = json.loads((out / "summary.json").read_text())
    assert summary["across_seeds"]["final_mean"]["n"] == 1
