"""Find the moments the demo video shows, from the cited run directories alone.

    .venv/bin/python experiments/analysis/find_moments.py [--max 3]

Prints tick ranges with run directories for: the first delivery of year 1 spring, hatches from
deliveries, caution at a first sighting of a moving thing (before any sting), a sting and what
the stung bee says at home afterwards, hive talk that passes a bloom location, bees heading for
last season's bloom after it moves, winter shrinkage, and year 2 spring against no_talk.
Nothing here is chosen by hand: every line is computed from events.jsonl and state.jsonl.gz.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runs import EXTENSIONS, MAIN_STAMP, RESULTS, Run  # noqa: E402
from e5_results import STAMP as E5_STAMP  # noqa: E402

COORD = re.compile(r"\((\d+)\s*,\s*(\d+)\)")
SEASONS = ["spring", "summer", "autumn", "winter"]


def cited_runs() -> list[Run]:
    dirs = []
    for arm in ["full", "no_talk"]:
        for stamp in [MAIN_STAMP] + EXTENSIONS.get(arm, []):
            dirs += sorted((RESULTS / arm / stamp).glob("seed-*"))
    for arm in ["e5_full", "e5_no_talk"]:
        dirs += sorted((RESULTS / arm).glob(f"{E5_STAMP}_s*/seed-*"))
    return [Run(d) for d in dirs if (d / "state.jsonl.gz").exists()]


def label(run: Run) -> str:
    return str(run.path.relative_to(RESULTS.parent.parent))


def season_of(t: int, lay: dict) -> tuple[int, str]:
    n = t // lay["season_length"]
    return n // 4, SEASONS[n % 4]


def near(x: int, y: int, cells, r: int = 2) -> bool:
    return any(abs(x - cx) <= r and abs(y - cy) <= r for cx, cy in cells)


def first_spring_delivery(run, ev, lay, out):
    pickups = {}
    for e in ev:
        if e["kind"] == "bloom":
            pickups.setdefault(e["bee"], e["t"])
        if e["kind"] == "delivery" and season_of(e["t"], lay) == (0, "spring"):
            out.append(f"first delivery, year 1 spring: bee {e['bee']} picked up at {pickups.get(e['bee'])}, "
                       f"delivered at {e['t']}  [{label(run)}]")
            return


def hatches(run, ev, out, cap):
    hs = [e for e in ev if e["kind"] == "hatch" and e.get("cause") == "delivery"][:cap]
    for e in hs:
        out.append(f"hatch from a delivery: bee {e['bee']} at tick {e['t']}  [{label(run)}]")


def caution(run, ev, out, cap):
    stung, n = set(), 0
    for e in ev:
        if e["kind"] == "sting":
            stung.add(e["bee"])
        if (e["kind"] == "decision" and e["trigger"] == "hornet" and e["bee"] not in stung
                and e["intent"] in ("flee", "go_home") and n < cap):
            n += 1
            out.append(f"caution before any sting: bee {e['bee']} saw a moving thing at tick {e['t']}, chose "
                       f"{e['intent']}, never stung yet; note {e['remember']!r}  [{label(run)}]")


def sting_then_talk(run, ev, out, cap):
    n = 0
    for i, e in enumerate(ev):
        if e["kind"] != "sting" or n >= cap:
            continue
        b = e["bee"]
        nxt = next((d for d in ev[i:] if d["kind"] == "decision" and d["bee"] == b and d["t"] >= e["t"]), None)
        said = next((s for s in ev[i:] if s["kind"] == "say" and s["bee"] == b and s["t"] > e["t"]
                     and s["heard_by"] and s["t"] - e["t"] <= 150), None)
        if nxt and nxt["intent"] in ("flee", "go_home") and said:
            n += 1
            out.append(f"sting and flee: hornet {e['hornet']} stung bee {b} at ({e['x']},{e['y']}) tick {e['t']}, "
                       f"life left {e['life_after']}; next decision {nxt['intent']} at {nxt['t']}; said at home "
                       f"tick {said['t']}: {said['text']!r}  [{label(run)}]")


def talk_passes_place(run, ev, lay, out, cap):
    n = 0
    for e in ev:
        if e["kind"] != "say" or not e["heard_by"] or n >= cap:
            continue
        for x, y in COORD.findall(e["text"]):
            hit = [s for s, cells in lay["bloom"].items() if near(int(x), int(y), cells)]
            if hit:
                n += 1
                out.append(f"hive talk passes a place: tick {e['t']}, bee {e['bee']} to bees {e['heard_by']}, "
                           f"near the {hit[0]} bloom: {e['text']!r}  [{label(run)}]")
                break


def outdated_route(run, ev, lay, out, cap):
    """Decisions in a season that target a patch that is no longer in bloom."""
    n = 0
    for e in ev:
        if e["kind"] != "decision" or e["intent"] != "go_to" or not e["target"] or n >= cap:
            continue
        year, season = season_of(e["t"], lay)
        for old, cells in lay["bloom"].items():
            if old != season and near(e["target"][0], e["target"][1], cells, 1):
                n += 1
                out.append(f"bloom moved, old route: {season} of year {year + 1}, tick {e['t']}, bee {e['bee']} "
                           f"goes to {tuple(e['target'])}, the {old} patch  [{label(run)}]")
                break


def winter(run, lay, out):
    L, size = lay["season_length"], {}
    for s in run.states:
        size[s["t"]] = len(s["b"])
    for year in range(lay["years"]):
        t0 = (4 * year + 3) * L
        t1 = t0 + L - 1
        if t0 in size and t1 in size:
            out.append(f"winter of year {year + 1}: ticks {t0} to {t1}, colony {size[t0]} -> {size[t1]} bees  "
                       f"[{label(run)}]")


def year2_spring(run, met, out):
    rows = [m for m in met if m["year"] == 1 and m["season"] == "spring"]
    for m in rows:
        out.append(f"year 2 spring ({run.condition}, seed {run.seed}): deliveries {m['deliveries']}, first delivery "
                   f"{m['first_delivery']} ticks in, bees at end {m['bees_end']}  [{label(run)}]")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Find the moments the demo video shows.")
    ap.add_argument("--max", type=int, default=2, help="examples per kind per run (default 2)")
    args = ap.parse_args(argv)
    sections = {k: [] for k in ["first delivery", "hatch", "caution", "sting", "talk", "old route",
                                "winter", "year 2 spring"]}
    for run in cited_runs():
        ev, lay, met = run.events, run.layout, run.metrics
        first_spring_delivery(run, ev, lay, sections["first delivery"])
        hatches(run, ev, sections["hatch"], args.max)
        caution(run, ev, sections["caution"], args.max)
        sting_then_talk(run, ev, sections["sting"], args.max)
        talk_passes_place(run, ev, lay, sections["talk"], args.max)
        outdated_route(run, ev, lay, sections["old route"], args.max)
        winter(run, lay, sections["winter"])
        year2_spring(run, met, sections["year 2 spring"])
    for name, lines in sections.items():
        print(f"## {name} ({len(lines)})")
        print("\n".join(lines) if lines else "none found")
        print()


if __name__ == "__main__":
    main()
