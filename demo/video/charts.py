"""Three result charts for the video, 1280 x 720, drawn from experiments/analysis/output/*.json.

Bars are seed means, dots are single seeds, and every bar carries its value and n, so the numbers
on screen are the ones in EXPERIMENTS.md. Colours are the analysis figures' (runs.COLORS).
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments" / "analysis"))
from runs import COLORS  # noqa: E402

OUT = REPO / "experiments" / "analysis" / "output"
PAPER, INK, SOFT, GRID = "#f7f2e8", "#2e2920", "#6f6555", "#e2d7c4"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": SOFT,
                     "xtick.color": SOFT, "ytick.color": SOFT, "axes.edgecolor": GRID})


def _fig(title: str, subtitle: str):
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=PAPER)
    fig.text(0.0625, 0.9, title, fontsize=30, fontweight="bold", color=INK)
    fig.text(0.0625, 0.855, subtitle, fontsize=17, color=SOFT, va="top", linespacing=1.5)
    return fig


def _bars(ax, names, stats, colors, fmt="strip", label_names=None):
    xs = range(len(names))
    means = [stats[n]["mean"] for n in names]
    ax.bar(xs, means, width=0.62, color=colors, edgecolor=PAPER, linewidth=2, zorder=2)
    for x, n in zip(xs, names):
        seeds = list(stats[n]["per_seed"].values())
        ax.scatter([x] * len(seeds), seeds, s=46, color=INK, alpha=0.55, zorder=3, edgecolors=PAPER, linewidths=1)
        top = max([stats[n]["mean"]] + seeds)
        v = stats[n]["mean"]
        shown = f"{v:.3f}".rstrip("0").rstrip(".") if fmt == "strip" else fmt.format(v)  # as in EXPERIMENTS.md
        ax.text(x, top + ax.get_ylim()[1] * 0.03, f"{shown}\nn {stats[n]['n']}",
                ha="center", va="bottom", fontsize=15, color=INK)
    ax.set_xticks(list(xs), label_names or names, fontsize=15)
    ax.set_facecolor(PAPER)
    ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", labelsize=13, length=0)


def _footer(fig, text: str):
    fig.text(0.0625, 0.035, text, fontsize=13, color=SOFT)


def chart_e1(out: Path) -> None:
    m = json.loads((OUT / "main_results.json").read_text())
    st = m["E1"]["by_condition"]["deliveries"]
    names = ["full", "no_talk", "no_memory", "rule_bees", "random_bees"]
    fig = _fig("AI bees gathered no more than rule bees",
               "E1: deliveries per 2-year run. Bars are seed means, dots single seeds.")
    ax = fig.add_axes([0.08, 0.15, 0.88, 0.62])
    ax.set_ylim(0, 8.5)
    _bars(ax, names, st, [COLORS[n] for n in names], fmt="strip",
          label_names=["full\n(memory + talk)", "no_talk", "no_memory", "rule bees\n(scripted)", "random bees"])
    _footer(fig, "Source: experiments/analysis/output/main_results.json (E1). 2 years, 80 x 48 world.")
    fig.savefig(out, facecolor=PAPER)
    plt.close(fig)


def chart_caution(out: Path) -> None:
    m = json.loads((OUT / "main_results.json").read_text())
    st = m["further"]["naive_avoidance_share"]
    timer = [v["timer"]["flee_or_home"] for arm in m["E4"]["listener"].values() for v in arm.values()
             if v.get("timer", {}).get("flee_or_home") is not None]
    lo, hi = min(timer), max(timer)
    names = ["full", "no_talk", "no_memory", "frozen_hornets", "labels_good_bad"]
    fig = _fig("Caution came before any sting",
               "At a bee's first sight of a moving thing, before any sting: the share that fled or went home.\n"
               f"Grey band: the same share at routine timer decisions, {lo:.3f} to {hi:.3f} across seeds.")
    ax = fig.add_axes([0.08, 0.15, 0.88, 0.56])
    ax.set_ylim(0, 1.3)
    ax.axhspan(lo, hi, color="#d8ccb6", alpha=0.8, zorder=1)
    _bars(ax, names, st, [COLORS[n] for n in names], fmt="{:.3f}",
          label_names=["full", "no_talk", "no_memory\n(no memory at all)", "frozen_hornets", "labels_good_bad"])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    _footer(fig, "Source: experiments/analysis/output/main_results.json (naive avoidance; E4 listener timer rows, "
                 "per-seed range).")
    fig.savefig(out, facecolor=PAPER)
    plt.close(fig)


def chart_e5(out: Path) -> None:
    e5 = json.loads((OUT / "e5_results.json").read_text())
    dl, home = e5["a"]["deliveries"], e5["exploratory"]["home_share"]
    names = ["e5_full", "e5_no_talk"]
    colors = [COLORS["full"], COLORS["no_talk"]]
    fig = _fig("With talk, bees stayed home more",
               "And gathered no more. E5, the smaller world: 5 paired seeds, 1 year each.\n"
               "Bars are seed means, dots single seeds.")
    ax1 = fig.add_axes([0.08, 0.13, 0.38, 0.56])
    ax1.set_ylim(0, 22)
    _bars(ax1, names, dl, colors, fmt="strip", label_names=["with talk", "no talk"])
    ax1.set_title("Deliveries per year", fontsize=17, color=INK, loc="left", pad=14)
    ax2 = fig.add_axes([0.58, 0.13, 0.38, 0.56])
    ax2.set_ylim(0, 0.8)
    _bars(ax2, names, home, colors, fmt="{:.3f}", label_names=["with talk", "no talk"])
    ax2.set_title("Share of bee-ticks at home (exploratory)", fontsize=17, color=INK, loc="left", pad=14)
    _footer(fig, "Source: experiments/analysis/output/e5_results.json. Talk-informed deliveries: 2, both in seed 0 "
                 "(1 of 5 seeds; 2 were required).")
    fig.savefig(out, facecolor=PAPER)
    plt.close(fig)


if __name__ == "__main__":
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "/dev/shm/dlv")
    for fn in (chart_e1, chart_caution, chart_e5):
        fn(dest / f"{fn.__name__}.png")
        print(dest / f"{fn.__name__}.png")
