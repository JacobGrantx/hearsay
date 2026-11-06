"""The analysis rules the pre-registration fixes: the paired-consistency verdict and mutual information."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "analysis"))

import measures as m  # noqa: E402
from runs import describe, paired  # noqa: E402


def test_paired_needs_same_sign_and_mean_above_sd():
    assert paired({0: 5, 1: 6, 2: 7}, {0: 1, 1: 2, 2: 3})["verdict"] == "consistently higher"
    assert paired({0: 1, 1: 2, 2: 3}, {0: 5, 1: 6, 2: 7})["verdict"] == "consistently lower"
    # same sign everywhere, but the paired differences vary more than their mean
    assert paired({0: 1, 1: 1, 2: 20}, {0: 0, 1: 0, 2: 0})["verdict"] == "no consistent difference"
    # one seed the other way
    assert paired({0: 5, 1: 5, 2: 0}, {0: 1, 1: 1, 2: 1})["verdict"] == "no consistent difference"
    # a missing seed can never be consistent
    p = paired({0: 5, 1: 6, 2: None}, {0: 1, 1: 2, 2: 3})
    assert p["n"] == 2 and not p["consistent"]


def test_describe_counts_missing_as_missing_not_zero():
    d = describe({0: 2.0, 1: None, 2: 4.0})
    assert d["n"] == 2 and d["mean"] == 3.0 and d["per_seed"]["1"] is None


def test_mutual_information():
    tied = [("sound-1", "movers")] * 10 + [("sound-2", "bright")] * 10
    assert abs(m.mutual_information(tied) - 1.0) < 1e-9
    independent = [(s, c) for s in ("sound-1", "sound-2") for c in ("movers", "bright")] * 5
    assert abs(m.mutual_information(independent)) < 1e-9
    test = m.mi_test(tied, permutations=200)
    assert test["above_p95"] and test["perm_p"] < 0.05
    assert m.mi_test([("sound-1", "movers")])["mi"] is None


def test_context_classes():
    assert m.context({"movers": 2, "bright": 1}) == "both"
    assert m.context({"movers": 0, "bright": 3}) == "bright"
    assert m.context({"movers": 0, "bright": 0}) == "neither"
