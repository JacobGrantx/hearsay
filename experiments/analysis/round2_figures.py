"""Small PNG figures from experiments/analysis/output/round2.json (run round2.py first).

Usage:
    .venv/bin/python experiments/analysis/round2_figures.py

Each seed is a dot or a thin line. A_full and N_full have one seed each (round 2 amendment 1),
so they are labelled n=1 and read as single-seed observations, not tests.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUTPUT = Path(__file__).resolve().parent / "output"
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dd"
FULL, NO_TALK, OTHER = "#c0622b", "#3b6ea5", "#7a7a72"
ARMS = ["B_full", "B_no_talk", "A_full", "N_full", "R2_rule", "R2_random"]
plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True})


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUTPUT / name, dpi=100)
    plt.close(fig)
    print(f"wrote {OUTPUT / name}")


def color(arm: str) -> str:
    return {"B_full": FULL, "B_no_talk": NO_TALK}.get(arm, OTHER)


def deliveries(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(5, 3.5))
    arms = [a for a in ARMS if a in d["per_run"]]
    for i, arm in enumerate(arms):
        vals = [m["deliveries_per_year"] for m in d["per_run"][arm].values() if m["deliveries_per_year"] is not None]
        if not vals:
            continue
        xs = [i + (j - (len(vals) - 1) / 2) * 0.06 for j in range(len(vals))]
        ax.scatter(xs, vals, s=14, color=color(arm), zorder=3)
        ax.hlines(statistics.mean(vals), i - 0.28, i + 0.28, color=INK, linewidth=1.6, zorder=4)
    ax.set_xticks(range(len(arms)), [f"{a}\nn={len(d['per_run'][a])}" for a in arms], fontsize=7)
    ax.set_ylabel("deliveries per completed year")
    ax.set_title("Deliveries per completed year by arm (dots: seeds, bar: arm mean)")
    save(fig, "round2_deliveries.png")


def first_g_reach(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(5, 3.5))
    pairs = sorted((p for p in d["H8"]["pairs"] if None not in (p["full"]["mean"], p["no_talk"]["mean"])),
                   key=lambda p: p["no_talk"]["mean"])
    last = -1e9
    for p in pairs:
        f, n = p["full"]["mean"], p["no_talk"]["mean"]
        ax.plot([0, 1], [f, n], color=MUTED, linewidth=0.8, zorder=2)
        ax.scatter([0, 1], [f, n], s=16, color=[FULL, NO_TALK], zorder=3)
        last = max(n, last + 9)  # keep labels apart when two seeds land close together
        ax.text(1.04, last, f"seed {p['seed']} ({p['years']} y)", va="center", fontsize=6.5, color=MUTED)
    ax.set_xticks([0, 1], ["B_full", "B_no_talk"])
    ax.set_xlim(-0.3, 1.5)
    ax.set_ylabel("ticks from spring start to first G pickup\n(mean over years 2 on; 250 = none)")
    ax.set_title("H8: ticks to first G pickup each spring, paired by seed")
    save(fig, "round2_first_g_reach.png")


def first_sighting(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(5, 3.5))
    by_run = d["H6"]["by_run"]
    arms = [a for a in ("B_full", "N_full") if a in by_run]
    for i, arm in enumerate(arms):
        vals = [v["away_or_zone_O_share"] for v in by_run[arm].values() if v["away_or_zone_O_share"] is not None]
        if not vals:
            continue
        xs = [i + (j - (len(vals) - 1) / 2) * 0.06 for j in range(len(vals))]
        ax.scatter(xs, vals, s=16, color=color(arm), zorder=3)
        ax.hlines(statistics.mean(vals), i - 0.25, i + 0.25, color=INK, linewidth=1.6, zorder=4)
    ax.set_xticks(range(len(arms)), [f"{a}\nn={len(by_run[a])}" for a in arms])
    ax.set_xlim(-0.6, len(arms) - 0.4)
    ax.set_ylim(0, 1)
    ax.set_ylabel("share of first sightings: away or zone O")
    ax.set_title(f"H6: first-sighting moves away or into zone O, per seed\n"
                 f"(first {d['H6']['common_years']} years of each run)")
    save(fig, "round2_first_sighting.png")


def signals(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(5, 3.5))
    for arm in ("B_full", "B_no_talk"):
        for s, rows in d["H9"].get(arm, {}).items():
            pts = [(r["season_start"], r["per_decision"]) for r in rows if r["per_decision"] is not None]
            if pts:
                ax.plot(*zip(*pts), color=color(arm), linewidth=0.8, alpha=0.8, marker="o", markersize=2)
    for arm in ("B_full", "B_no_talk"):
        ax.plot([], [], color=color(arm), label=f"{arm} (n={len(d['H9'].get(arm, {}))})")
    ax.legend(frameon=False, fontsize=7)
    ax.set_xlabel("season start (tick)")
    ax.set_ylabel("signals per decision")
    ax.set_title("H9: signals per decision by season, one line per seed")
    save(fig, "round2_signals.png")


def main() -> None:
    d = json.loads((OUTPUT / "round2.json").read_text())
    deliveries(d)
    first_g_reach(d)
    first_sighting(d)
    signals(d)


if __name__ == "__main__":
    main()
