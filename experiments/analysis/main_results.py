"""Compute every pre-registered measure of the main runs, from the run directories alone.

Usage:
    .venv/bin/python experiments/analysis/main_results.py

Writes experiments/analysis/output/main_results.json (every per-seed value, mean, sd, n and paired
comparison) and main_results.md (the tables EXPERIMENTS.md quotes). The pre-registration is in
EXPERIMENTS.md; the paired-consistency rule is runs.paired().
"""
from __future__ import annotations

import json
from collections import Counter

import measures as m
from runs import AI, CONDITIONS, EXTENDED_SEEDS, OUTPUT, PAIRED_SEEDS, describe, fmt, paired, runs

E1_MEASURES = ["deliveries", "delivery_rate", "median_to_bloom", "stings_per_trip", "bees_mean",
               "spring_deliveries", "summer_deliveries", "autumn_deliveries",
               "spring_rate", "summer_rate", "autumn_rate"]


def collect() -> dict:
    R = {c: runs(c) for c in CONDITIONS}
    out = {"runs": {c: {s: r.name for s, r in rs.items()} for c, rs in R.items()},
           "provenance": {c: sorted({(r.record["provenance"]["git_commit"], r.record["provenance"]["git_dirty"]) for r in rs.values()})
                          for c, rs in R.items()},
           "errors": {c: {s: r.record.get("error") for s, r in rs.items() if r.record.get("error")} for c, rs in R.items()},
           "health": {c: {s: m.mind_health(r) for s, r in rs.items()} for c, rs in R.items() if c in AI}}

    def seeds(c, fn):
        return {s: fn(r) for s, r in R[c].items()}

    # E1: learning and culture
    e1 = {"by_condition": {}, "paired": {}}
    for k in E1_MEASURES:
        vals = {c: seeds(c, lambda r: r.final.get(k)) for c in CONDITIONS}
        e1["by_condition"][k] = {c: describe(v) for c, v in vals.items()}
        e1["paired"][k] = {f"full - {c}": paired(vals["full"], vals[c]) for c in ("no_talk", "no_memory", "rule_bees", "random_bees")}
        e1.setdefault("paired_extended", {})[k] = {f"full - {c}": paired(vals["full"], vals[c], EXTENDED_SEEDS) for c in ("no_talk", "rule_bees", "random_bees")}
    e1["deliveries_by_season"] = {c: seeds(c, m.deliveries_by_season) for c in CONDITIONS}
    out["E1"] = e1

    # E2: arms race
    change = {c: seeds(c, m.sting_change) for c in CONDITIONS}
    out["E2"] = {
        "sting_change": {c: describe(v) for c, v in change.items()},
        "stings_per_trip_y1": {c: describe(seeds(c, lambda r: m.stings_per_trip_by_year(r)[0])) for c in CONDITIONS},
        "stings_per_trip_y2": {c: describe(seeds(c, lambda r: m.stings_per_trip_by_year(r)[1])) for c in CONDITIONS},
        "paired": {"full - frozen_hornets": paired(change["full"], change["frozen_hornets"])},
        "damage_per_bee_tick_outside": {c: seeds(c, m.damage_per_bee_tick_outside) for c in CONDITIONS},
        "gene_means": {c: seeds(c, m.gene_means) for c in ("full", "frozen_hornets")},
    }

    # E3: seasonal memory
    gain = {c: seeds(c, m.spring_gain) for c in CONDITIONS}
    out["E3"] = {
        "first_delivery_y1": {c: describe(seeds(c, lambda r: m.first_spring_delivery(r, 0))) for c in CONDITIONS},
        "first_delivery_y2": {c: describe(seeds(c, lambda r: m.first_spring_delivery(r, 1))) for c in CONDITIONS},
        "gain": {c: describe(v) for c, v in gain.items()},
        "paired": {"full - no_talk": paired(gain["full"], gain["no_talk"])},
        "paired_extended": {"full - no_talk": paired(gain["full"], gain["no_talk"], EXTENDED_SEEDS)},
        "carryover": {c: seeds(c, m.carryover) for c in AI},
    }

    # E4: signals
    e4 = {"all": {}, "full_y1": {}, "full_y2": {}, "first_spring": {}, "listener": {}}
    for c in AI:
        e4["all"][c] = seeds(c, lambda r: m.mi_test(m.sound_decisions(r)))
        e4["listener"][c] = seeds(c, m.listener_response)
    for c in ("full", "labels_good_bad"):
        e4["first_spring"][c] = seeds(c, lambda r: m.mi_test(m.sound_decisions(r, 0, 250)))
    e4["full_y1"] = seeds("full", lambda r: m.mi_test(m.sound_decisions(r, 0, 1000)))
    e4["full_y2"] = seeds("full", lambda r: m.mi_test(m.sound_decisions(r, 1000, 2000)))
    above = sum(bool(v.get("above_p95")) for s, v in e4["all"]["full"].items() if s in PAIRED_SEEDS)
    e4["supported"] = above >= 2
    e4["full_seeds_above_p95"] = above
    out["E4"] = e4

    # Further measures
    claims = {c: seeds(c, lambda r: dict(m.talk_claims(r))) for c in AI}
    out["further"] = {
        "talk_claims": claims,
        "talk_claims_pooled": {c: dict(sum((Counter(v) for v in claims[c].values()), Counter())) for c in AI},
        "naive_avoidance": {c: seeds(c, m.naive_avoidance) for c in AI},
        "naive_avoidance_share": {c: describe(seeds(c, lambda r: m.naive_avoidance(r)["flee_or_home"])) for c in AI},
    }
    hw = {c: seeds(c, m.harm_words) for c in AI}
    out["exploratory"] = {"harm_words": hw,
                          "harm_note_share": {c: describe({s: v["note_share"] for s, v in hw[c].items()}) for c in AI},
                          "harm_say_share": {c: describe({s: v["say_share"] for s, v in hw[c].items()}) for c in AI},
                          "says_heard_by_anyone": {c: describe({s: v["says_heard_by_anyone"] for s, v in hw[c].items()}) for c in AI}}
    return out


def table(title: str, block: dict, conds=CONDITIONS, digits=3) -> list[str]:
    lines = [f"**{title}**", "", "| condition | mean (sd, n) | per seed |", "|---|---|---|"]
    for c in conds:
        if c in block:
            lines.append(f"| {c} | {fmt(block[c], digits)} | {block[c]['per_seed']} |")
    return lines + [""]


def pair_lines(title: str, block: dict) -> list[str]:
    lines = [f"**{title}** (paired by seed)", "", "| comparison | n | per-seed differences | mean | sd | verdict |", "|---|---|---|---|---|---|"]
    for name, p in block.items():
        lines.append(f"| {name} | {p['n']} | {p['diffs']} | {p['mean']} | {p['sd']} | {p['verdict']} |")
    return lines + [""]


def markdown(r: dict) -> str:
    L = ["# Main results (generated by experiments/analysis/main_results.py; do not edit)", "",
         "Run directories:", ""] + [f"- {c}: {sorted(set(n.rsplit('/', 1)[0] for n in v.values()))}, seeds {sorted(v)}" for c, v in r["runs"].items()]
    L += ["", f"Provenance (commit, dirty): {r['provenance']}", f"Crashed seeds: {r['errors']}", "",
          "## Model health", "", "| condition | seed | decisions | mind_error | fallbacks | share | flagged | input tokens | output tokens |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c, seeds in r["health"].items():
        for s, h in seeds.items():
            L.append(f"| {c} | {s} | {h['decisions']} | {h['mind_errors']} | {h['fallbacks']} | {h['fallback_share']} | {h['flagged']} | {h['input_tokens']} | {h['output_tokens']} |")
    L += ["", "## E1: learning and culture", ""]
    for k in E1_MEASURES:
        L += table(k, r["E1"]["by_condition"][k])
    L += pair_lines("E1 primary: deliveries", r["E1"]["paired"]["deliveries"])
    L += pair_lines("E1 primary, extended to seeds 0 to 4 (amendment 1)", r["E1"]["paired_extended"]["deliveries"]).copy()
    L += pair_lines("E1 secondary: delivery_rate", r["E1"]["paired"]["delivery_rate"])
    L += pair_lines("E1 secondary: stings_per_trip", r["E1"]["paired"]["stings_per_trip"])
    L += ["## E2: arms race", ""] + table("stings per trip, year 1", r["E2"]["stings_per_trip_y1"])
    L += table("stings per trip, year 2", r["E2"]["stings_per_trip_y2"]) + table("change, year 2 minus year 1", r["E2"]["sting_change"])
    L += pair_lines("E2 primary", r["E2"]["paired"])
    L += ["## E3: seasonal memory", ""] + table("first spring delivery, year 1 (censored at 250)", r["E3"]["first_delivery_y1"], digits=1)
    L += table("first spring delivery, year 2", r["E3"]["first_delivery_y2"], digits=1) + table("gain (year 1 minus year 2)", r["E3"]["gain"], digits=1)
    L += pair_lines("E3 primary", r["E3"]["paired"])
    L += pair_lines("E3 primary, extended to seeds 0 to 4 (amendment 1)", r["E3"]["paired_extended"])
    L += ["**Carryover**", ""] + [f"- {c} seed {s}: {v}" for c, sv in r["E3"]["carryover"].items() for s, v in sv.items()]
    L += ["", "## E4: signals", "", f"Supported (full above its permutation 95th percentile in at least 2 of 3 seeds): {r['E4']['supported']} ({r['E4']['full_seeds_above_p95']} of 3)", "",
          "| condition | seed | sounds | by sound | MI (bits) | perm p95 | perm p | note |", "|---|---|---|---|---|---|---|---|"]
    for c, sv in r["E4"]["all"].items():
        for s, v in sv.items():
            L.append(f"| {c} | {s} | {v['n_sounds']} | {v['by_sound']} | {v['mi']} | {v.get('perm_p95')} | {v.get('perm_p')} | {v['note']} |")
    L += ["", "**Listener response** (share of flee or go_home)", ""] + [f"- {c} seed {s}: {v}" for c, sv in r["E4"]["listener"].items() for s, v in sv.items()]
    L += ["", "## Further measures", "", "**Coordinates in hive talk** (pooled over seeds)", ""] + [f"- {c}: {v}" for c, v in r["further"]["talk_claims_pooled"].items()]
    L += [""] + table("naive avoidance: share of flee or go_home at a bee's first sighting, before any sting", r["further"]["naive_avoidance_share"], AI)
    L += ["## Exploratory (not pre-registered)", ""]
    L += table("share of notes using a word of harm or caution (" + ", ".join(m.HARM_WORDS) + ")", r["exploratory"]["harm_note_share"], AI)
    L += table("share of words said at home using one", r["exploratory"]["harm_say_share"], AI)
    L += table("share of words said at home that another bee heard", r["exploratory"]["says_heard_by_anyone"], AI)
    return "\n".join(L) + "\n"


def main() -> None:
    r = collect()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "main_results.json").write_text(json.dumps(r, indent=1, default=str) + "\n")
    (OUTPUT / "main_results.md").write_text(markdown(r))
    print(f"wrote {OUTPUT / 'main_results.md'}")


if __name__ == "__main__":
    main()
