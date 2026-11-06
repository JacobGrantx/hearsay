"""Round 2: every pre-registered measure (EXPERIMENTS.md, "Round 2"), from run directories, finished or not.

A run's completed years: record.json's stopped_at_tick if it stopped on the wall clock, else its whole length if
it finished, else (still running, or crashed) the seasons written to metrics.jsonl. Each comparison cuts every run
it compares to the years all of them completed, and reports that number. Names are the sim's: go_home is go_to_O,
carrying is flag F, a bloom event is a G pickup.

Usage: .venv/bin/python experiments/analysis/round2.py [--results DIR] [--arm B_full=r2_b_full ...] [--out FILE]
--arm maps an arm to another experiment name, to test this on earlier runs (e5_full, pilot_abstract_e5_spring).
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from first_sighting import classify  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ARMS = {"B_full": "r2_b_full", "B_no_talk": "r2_b_no_talk", "A_full": "r2_a_full", "N_full": "r2_n_full",
        "R2_rule": "r2_rule", "R2_random": "r2_random"}
ABOUT_G_OR_O = re.compile(r"\b[GO]\b")
YEAR = 1000


class Run:
    def __init__(self, d: Path):
        self.dir, self.seed = d, int(d.name.split("-")[1])
        rec = d / "record.json"
        self.record = json.loads(rec.read_text()) if rec.exists() else None
        lay = json.loads((d / "layout.json").read_text())
        self.season_length, self.ticks = lay["season_length"], lay["ticks"]
        seasons = len((d / "metrics.jsonl").read_text().splitlines()) if (d / "metrics.jsonl").exists() else 0
        if self.record and self.record.get("stopped_at_tick") is not None:
            self.done_ticks, self.status = self.record["stopped_at_tick"], "stopped"
        elif self.record and not self.record.get("error"):
            self.done_ticks, self.status = min(self.ticks, self.record["params"].get("stop_after") or self.ticks), "finished"
        else:
            self.done_ticks, self.status = seasons * self.season_length, "error" if self.record else "running"
        self.years = self.done_ticks // YEAR
        self.events = []
        with (d / "events.jsonl").open() as f:
            for line in f:
                try:
                    self.events.append(json.loads(line))
                except ValueError:  # a running run's last line may be half written
                    break
        self._states = None

    def states(self) -> list[dict]:
        if self._states is None:
            self._states = []
            with gzip.open(self.dir / "state.jsonl.gz", "rt") as f:
                try:
                    for line in f:
                        self._states.append(json.loads(line))
                except (EOFError, ValueError, OSError):  # a running run's gzip stream is unfinished
                    pass
        return self._states

    def until(self, cut: int, kind: str | None = None) -> list[dict]:
        return [e for e in self.events if e["t"] < cut and (kind is None or e["kind"] == kind)]

    def carrying(self, e: dict) -> bool:
        """Flag F at decision time: the AI mind logs it in ctx; for scripted bees, the state line of the tick before."""
        if "ctx" in e:
            return bool(e["ctx"]["carrying"])
        if e["t"] == 0:
            return False
        line = self.states()[e["t"] - 1]
        return any(b[0] == e["bee"] and b[4] for b in line["b"])


def gof(run: Run, e: dict) -> bool:
    return e["kind"] == "decision" and e["intent"] == "go_home" and run.carrying(e)


def delivery_measures(run: Run, cut: int) -> dict:
    ev = run.until(cut)
    last_decision, delivered_at, heard_g_o = {}, defaultdict(list), defaultdict(list)
    dd = first_dd = talk_first_dd = 0
    repeat, repeat_ended_in_delivery, pending_repeat, repeat_units = 0, 0, {}, set()
    for e in ev:
        k = e["kind"]
        if k == "decision":
            last_decision[e["bee"]] = e
            if gof(run, e) and delivered_at[e["bee"]]:
                repeat += 1
                repeat_units.add(e["bee"])
                pending_repeat[e["bee"]] = True
            else:
                pending_repeat.pop(e["bee"], None)
        elif k == "say" and ABOUT_G_OR_O.search(e["text"] or ""):
            for b in e["heard_by"]:
                heard_g_o[b].append(e["t"])
        elif k == "delivery":
            b = e["bee"]
            deliberate = b in last_decision and gof(run, last_decision[b])
            if deliberate:
                dd += 1
                if not delivered_at[b]:
                    first_dd += 1
                    talk_first_dd += any(t < e["t"] for t in heard_g_o[b])
            repeat_ended_in_delivery += bool(pending_repeat.pop(b, None))
            delivered_at[b].append(e["t"])
    years = cut // YEAR
    deliveries = sum(len(v) for v in delivered_at.values())
    return {"cut_years": years, "deliveries": deliveries, "deliveries_per_year": round(deliveries / years, 4) if years else None,
            "deliberate_deliveries": dd, "first_dd": first_dd, "talk_informed_first_dd": talk_first_dd,
            "repeat_choices": repeat, "units_with_repeat_choice": len(repeat_units),
            "repeat_choices_ended_in_delivery": repeat_ended_in_delivery,
            "broadcasts": len(run.until(cut, "say")),
            "broadcasts_about_G_or_O": sum(bool(ABOUT_G_OR_O.search(e["text"] or "")) for e in run.until(cut, "say"))}


def spring_first_reach(run: Run, cut: int) -> dict:
    """Ticks from each spring's start (years 2 on, 1-based) to its first G pickup; 250 if none (censored)."""
    out = {}
    for y in range(1, cut // YEAR):
        start = y * YEAR
        first = [e["t"] for e in run.events if e["kind"] == "bloom" and start <= e["t"] < start + run.season_length]
        out[y + 1] = (min(first) - start) if first else run.season_length
    return {"by_year": out, "mean": round(st.mean(out.values()), 2) if out else None,
            "censored": sum(v == run.season_length for v in out.values())}


def first_sightings(run: Run, cut: int) -> dict:
    ev = run.until(cut)
    stung = {}
    for e in ev:
        if e["kind"] == "sting":
            stung.setdefault(e["bee"], e["t"])
    first = {}
    for e in ev:
        if e["kind"] == "decision" and e["trigger"] == "hornet" and e["t"] < stung.get(e["bee"], 10**9):
            first.setdefault(e["bee"], e)
    return classify(list(first.values()), run.states())


def signals(run: Run, cut: int) -> list[dict]:
    rows = []
    for s0 in range(0, cut, run.season_length):
        dec = [e for e in run.events if e["kind"] == "decision" and s0 <= e["t"] < s0 + run.season_length]
        sig = [e for e in dec if e.get("sound", "none") != "none"]
        ctx = [e for e in sig if e.get("ctx", {}).get("movers", 0) > 0 or e.get("ctx", {}).get("carrying", 0)]
        rows.append({"season_start": s0, "decisions": len(dec), "signals": len(sig),
                     "per_decision": round(len(sig) / len(dec), 4) if dec else None, "with_K_or_F": len(ctx)})
    return rows


def stats(xs: list) -> dict:
    xs = [x for x in xs if x is not None]
    return {"n": len(xs), "mean": round(st.mean(xs), 4) if xs else None, "sd": round(st.stdev(xs), 4) if len(xs) > 1 else None,
            "min": min(xs) if xs else None, "max": max(xs) if xs else None}


def find_runs(results: Path, arms: dict) -> dict[str, dict[int, Run]]:
    out = {}
    for arm, name in arms.items():
        runs = {}
        for d in sorted((results / name).glob("*/seed-*")):
            if "calib" in d.parent.name or not (d / "layout.json").exists() or not (d / "events.jsonl").exists():
                continue  # the 2-year scripted calibration is reported apart (EXPERIMENTS.md, "Setup calibration")
            r = Run(d)
            runs.setdefault(r.seed, r)  # one run per seed: the earliest stamp
        out[arm] = runs
    return out


def paired(a: dict, b: dict, measure, key) -> list[dict]:
    rows = []
    for s in sorted(set(a) & set(b)):
        cut = min(a[s].years, b[s].years) * YEAR
        ma, mb = measure(a[s], cut), measure(b[s], cut)
        rows.append({"seed": s, "years": cut // YEAR, "a": key(ma), "b": key(mb)})
    return rows


def analyse(runs: dict) -> dict:
    B, NT, A, N = (runs.get(k, {}) for k in ("B_full", "B_no_talk", "A_full", "N_full"))
    out = {"runs": {arm: {s: {"dir": str(r.dir), "status": r.status, "done_ticks": r.done_ticks, "years": r.years}
                          for s, r in rs.items()} for arm, rs in runs.items()}}
    out["per_run"] = {arm: {s: delivery_measures(r, r.years * YEAR) for s, r in rs.items()} for arm, rs in runs.items()}
    # H10: discovery in B_full, each run over its own completed years
    disc = {s: m["repeat_choices"] > 0 for s, m in out["per_run"].get("B_full", {}).items()}
    out["H10"] = {"seeds_with_discovery": sum(disc.values()), "of": len(disc), "by_seed": disc,
                  "supported": sum(disc.values()) >= 3 if len(disc) == 5 else None}
    # H7: talk-informed first DDs in B_full against first DDs in B_no_talk, paired by seed
    h7 = paired(B, NT, delivery_measures, lambda m: m)
    rows = [{"seed": r["seed"], "years": r["years"], "talk_informed_first_dd_full": r["a"]["talk_informed_first_dd"],
             "first_dd_full": r["a"]["first_dd"], "first_dd_no_talk": r["b"]["first_dd"]} for r in h7]
    wins = sum(r["years"] > 0 and r["talk_informed_first_dd_full"] > r["first_dd_no_talk"] for r in rows)
    out["H7"] = {"pairs": rows, "seeds_full_more": wins, "supported": wins >= 4 if len(rows) == 5 else None}
    # H8: first G reach each spring from year 2, paired
    rows = [{"seed": r["seed"], "years": r["years"], "full": r["a"], "no_talk": r["b"]}
            for r in paired(B, NT, spring_first_reach, lambda m: m)]
    testable = [r for r in rows if r["years"] >= 2]
    wins = sum(r["full"]["mean"] < r["no_talk"]["mean"] for r in testable)
    out["H8"] = {"pairs": rows, "testable_pairs": len(testable), "seeds_full_earlier": wins,
                 "supported": wins >= 4 if len(testable) == 5 else None}
    # H6: first sighting before any halving, B_full against N_full, cut to the years every run of both completed
    common = min([r.years for r in [*B.values(), *N.values()]] or [0]) * YEAR
    h6 = {arm: {s: first_sightings(r, common) for s, r in rs.items()} for arm, rs in (("B_full", B), ("N_full", N))}
    share = {arm: stats([v["away_or_zone_O_share"] for v in d.values()]) for arm, d in h6.items()}
    verdict = None
    if share["B_full"]["n"] and share["N_full"]["n"]:
        lower = share["B_full"]["mean"] < share["N_full"]["mean"]
        apart = share["B_full"]["max"] < share["N_full"]["min"]
        verdict = "supported" if lower and apart else "direction only" if lower else "not supported"
    out["H6"] = {"common_years": common // YEAR, "common_ticks": common, "by_run": h6, "share": share, "verdict": verdict}
    # H11: deliveries per completed year, A_full against B_full paired on seeds 0 to 2, and arm summaries
    rows = [{"seed": r["seed"], "years": r["years"], "a_full": r["a"], "b_full": r["b"]}
            for r in paired(A, B, delivery_measures, lambda m: m["deliveries_per_year"])]
    ok = [r for r in rows if r["years"] > 0]
    v = None
    if len(ok) == 3:
        v = ("knowing raises deliveries" if all(r["a_full"] > r["b_full"] for r in ok) else
             "knowing lowers deliveries" if all(r["a_full"] < r["b_full"] for r in ok) else "no difference shown")
    out["H11"] = {"pairs": rows, "verdict": v, "arms": {arm: stats([m["deliveries_per_year"] for m in out["per_run"].get(arm, {}).values()])
                                                       for arm in runs}}
    out["H9"] = {arm: {s: signals(r, r.years * YEAR) for s, r in rs.items()} for arm, rs in runs.items() if arm != "R2_random"}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--results", type=Path, default=REPO / "experiments" / "results")
    ap.add_argument("--arm", action="append", default=[], metavar="ARM=EXPERIMENT")
    ap.add_argument("--out", type=Path, default=REPO / "experiments" / "analysis" / "output" / "round2.json")
    a = ap.parse_args()
    arms = dict(ARMS)
    for kv in a.arm:
        k, _, v = kv.partition("=")
        arms[k] = v
    res = analyse(find_runs(a.results, arms))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    for arm, rs in res["runs"].items():
        print(arm, {s: f"{r['status']} {r['years']}y" for s, r in rs.items()})
    for h in ("H10", "H7", "H8", "H6", "H11"):
        print(h, {k: v for k, v in res[h].items() if k in ("supported", "verdict", "seeds_with_discovery", "seeds_full_more",
                                                             "seeds_full_earlier", "testable_pairs", "common_years", "share")})
    print(f"written: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
