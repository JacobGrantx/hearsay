"""find_moments.py finds, from the committed run directories alone, the moments the demo video shows."""
import contextlib
import io
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parents[1] / "experiments" / "analysis"
E5 = "experiments/results/e5_full/20261106T112913Z_s0/seed-0"
MAIN = "experiments/results/full/20261106T101558Z/seed-0"


@pytest.fixture(scope="module")
def moments() -> str:
    if not (ANALYSIS.parents[0] / "results" / "e5_full").exists():
        pytest.skip("cited run directories not present")
    sys.path.insert(0, str(ANALYSIS))
    import find_moments

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        find_moments.main(["--max", "2"])
    return out.getvalue()


def test_e5_transmission(moments):
    assert f"first delivery, year 1 spring: bee 4 picked up at 60, delivered at 166  [{E5}]" in moments
    assert f"hatch from a delivery: bee 6 at tick 166  [{E5}]" in moments
    assert "hive talk passes a place: tick 167, bee 4 to bees [6], near the spring bloom" in moments


def test_main_world_moments(moments):
    assert "caution before any sting: bee 5 saw a moving thing at tick 34, chose flee" in moments
    assert f"winter of year 1: ticks 750 to 999, colony 7 -> 4 bees  [{E5}]" in moments
    line = next(x for x in moments.splitlines() if x.startswith("sting and flee: hornet 7 stung bee 1"))
    assert "tick 102, life left 199.0" in line and line.endswith(f"[{MAIN}]")
