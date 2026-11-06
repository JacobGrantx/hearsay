"""Small PNG figures from experiments/analysis/output/main_results.json (run main_results.py first).

Usage:
    .venv/bin/python experiments/analysis/figures.py

Every figure shows each seed as a dot or thin line, with the mean across seeds on top.
"""
from __future__ import annotations

import json
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from runs import AI, COLORS, CONDITIONS, OUTPUT  # noqa: E402

INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dd"
SEASON_LABELS = ["Y1 spr", "Y1 sum", "Y1 aut", "Y1 win", "Y2 spr", "Y2 sum", "Y2 aut", "Y2 win"]
HORNET_LABELS = ["Y1 spr", "Y1 sum", "Y1 aut", "Y2 spr", "Y2 sum", "Y2 aut"]
plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True})


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUTPUT / name, dpi=110)
    plt.close(fig)
    print(f"wrote {OUTPUT / name}")


def dots(ax, conds, per_cond: dict, ylabel: str) -> None:
    """Per-seed dots and a mean tick for each condition."""
    for i, c in enumerate(conds):
        vals = [v for v in per_cond.get(c, {}).values() if v is not None]
        if not vals:
            ax.text(i, 0, "no data", ha="center", va="bottom", color=MUTED, fontsize=7)
            continue
        ax.scatter([i] * len(vals), vals, s=22, color=COLORS[c], alpha=0.8, zorder=3, edgecolor="white", linewidth=0.8)
        ax.hlines(statistics.fmean(vals), i - 0.28, i + 0.28, color=INK, linewidth=2, zorder=4)
    ax.set_xticks(range(len(conds)), [c.replace("_", "\n") for c in conds])
    ax.set_ylabel(ylabel)


def deliveries_by_season(r: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for c in CONDITIONS:
        seeds = list(r["E1"]["deliveries_by_season"].get(c, {}).values())
        if not seeds:
            continue
        mean = [statistics.fmean(s[i] for s in seeds) for i in range(len(seeds[0]))]
        ax.plot(range(len(mean)), mean, marker="o", markersize=4, linewidth=2, color=COLORS[c], label=f"{c} (n {len(seeds)})")
    ax.set_xticks(range(8), SEASON_LABELS)
    ax.set_ylabel("deliveries (mean over seeds)")
    ax.set_title("Deliveries per season", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=7, ncol=2)
    save(fig, "fig_deliveries_by_season.png")


def stings_per_trip(r: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    dots(ax, CONDITIONS, {c: v["per_seed"] for c, v in r["E1"]["by_condition"]["stings_per_trip"].items()}, "stings per trip")
    ax.set_title("Stings per trip, both years (dots: seeds; bar: mean)", loc="left", color=INK)
    save(fig, "fig_stings_per_trip.png")


def first_spring_delivery(r: dict) -> None:
    conds = AI + ["rule_bees"]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    y1, y2 = r["E3"]["first_delivery_y1"], r["E3"]["first_delivery_y2"]
    for i, c in enumerate(conds):
        for s, a in y1[c]["per_seed"].items():
            b = y2[c]["per_seed"].get(s)
            ax.plot([i - 0.18, i + 0.18], [a, b], color=COLORS[c], marker="o", markersize=4, linewidth=1.2, alpha=0.85)
    ax.axhline(250, color=MUTED, linewidth=0.8, linestyle=":")
    ax.text(len(conds) - 0.5, 250, "no delivery (censored)", color=MUTED, fontsize=7, ha="right", va="bottom")
    ax.set_xticks(range(len(conds)), [c.replace("_", "\n") for c in conds])
    ax.set_ylabel("ticks into spring")
    ax.set_title("First spring delivery: year 1 (left dot) to year 2 (right dot), one line per seed", loc="left", color=INK)
    save(fig, "fig_first_spring_delivery.png")


def hornet_genes(r: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, gene in zip(axes, ("smell", "hearing", "ambush")):
        for c in ("full", "frozen_hornets"):
            seeds = list(r["E2"]["gene_means"].get(c, {}).values())
            for rows in seeds:
                ax.plot(range(len(rows)), [x[gene] for x in rows], color=COLORS[c], linewidth=0.8, alpha=0.45)
            if seeds and all(len(s) == len(seeds[0]) for s in seeds):
                mean = [statistics.fmean(s[i][gene] for s in seeds) for i in range(len(seeds[0]))]
                ax.plot(range(len(mean)), mean, color=COLORS[c], linewidth=2.2, label=f"{c} (n {len(seeds)})")
        ax.set_title(gene, loc="left", color=INK)
        ax.set_xticks(range(6), HORNET_LABELS, rotation=45)
    axes[0].set_ylabel("mean gene value (points of 10)")
    axes[0].legend(frameon=False, fontsize=7)
    save(fig, "fig_hornet_genes.png")


def sound_context(r: dict) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.8))
    rate = {c: {s: v["n_sounds"] / max(1, r["health"][c][s]["decisions"]) * 1000 for s, v in r["E4"]["all"].get(c, {}).items()} for c in AI}
    dots(a1, AI, rate, "sounds per 1,000 decisions")
    a1.set_title("How often bees make a sound", loc="left", color=INK)
    for i, c in enumerate(AI):
        for v in r["E4"]["all"].get(c, {}).values():
            if v["mi"] is None:
                a2.scatter([i], [0], marker="x", color=MUTED, s=20, zorder=3)
                continue
            a2.scatter([i], [v["mi"]], color=COLORS[c], s=22, zorder=3, edgecolor="white", linewidth=0.8)
            a2.scatter([i + 0.15], [v["perm_p95"]], marker="_", color=INK, s=60, zorder=3)
    a2.set_xticks(range(len(AI)), [c.replace("_", "\n") for c in AI])
    a2.set_ylabel("MI(sound; context), bits")
    a2.set_title("MI per seed (dot), permutation p95 (dash), x: < 2 sounds", loc="left", color=INK, fontsize=7.5)
    save(fig, "fig_sound_context.png")


def main() -> None:
    r = json.loads((OUTPUT / "main_results.json").read_text())
    deliveries_by_season(r)
    stings_per_trip(r)
    first_spring_delivery(r)
    hornet_genes(r)
    sound_context(r)


if __name__ == "__main__":
    main()
