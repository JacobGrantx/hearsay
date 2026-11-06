"""Title, end and text cards, and caption overlays, drawn with Pillow in the viewer's colours.

Numbers on the cards are read from experiments/analysis/output/*.json where the JSON holds them; the
rest (E4's sound count) are copied from the summary table of EXPERIMENTS.md.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "experiments" / "analysis" / "output"
W, H = 1280, 720
PAPER, CARD, LINE = "#f7f2e8", "#fffcf5", "#e2d7c4"
INK, SOFT, BEE, ACCENT = "#2e2920", "#6f6555", "#f2c230", "#b5541b"
FONT_DIRS = [Path("/usr/share/fonts/truetype/dejavu")]


def font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in FONT_DIRS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), size)
    return ImageFont.load_default(size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=f) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def caption(text: str, out: Path, band_width: int = 968) -> None:
    """A transparent frame with a dark band over the bottom of the map (the panel stays clear)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(23)
    lines = wrap(d, text, f, band_width - 64)
    h = 26 + 33 * len(lines)
    d.rectangle([0, H - h, band_width, H], fill=(38, 33, 26, 222))
    d.rectangle([0, H - h, 6, H], fill=BEE)
    for i, line in enumerate(lines):
        d.text((30, H - h + 14 + 33 * i), line, font=f, fill="#fbf6ea")
    img.save(out)


def _base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), PAPER)
    return img, ImageDraw.Draw(img)


def _hex(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: str) -> None:
    pts = [(cx + r * c, cy + r * s) for c, s in [(1, 0), (.5, .866), (-.5, .866), (-1, 0), (-.5, -.866), (.5, -.866)]]
    d.polygon(pts, fill=fill, outline="#c9a94a")


def title_card(project: str, out: Path) -> None:
    img, d = _base()
    for i, (dx, dy) in enumerate([(0, 0), (52, 30), (52, -30), (0, 60), (-52, 30)]):
        _hex(d, 640 + dx, 210 + dy, 30, BEE if i == 0 else "#f6e3a3")
    f = font(64, True)
    d.text((W / 2, 340), project, font=f, fill=INK, anchor="mm")
    d.text((W / 2, 418), "Can knowledge outlive the one who found it?", font=font(32, True), fill=ACCENT, anchor="mm")
    sub = "Language-model bees in a maze find things, can share them only at home, and die."
    for i, line in enumerate(wrap(d, sub, font(26), 900)):
        d.text((W / 2, 480 + 38 * i), line, font=font(26), fill=SOFT, anchor="mm")
    d.text((W / 2, 640), "Every frame that follows is a replay of a logged run.", font=font(20), fill=SOFT, anchor="mm")
    img.save(out)


def end_card(project: str, repo: str, out: Path) -> None:
    img, d = _base()
    d.text((W / 2, 220), project, font=font(48, True), fill=INK, anchor="mm")
    d.text((W / 2, 320), "Every frame is a logged run. Replay it:", font=font(30), fill=INK, anchor="mm")
    d.rounded_rectangle([510, 362, 770, 422], radius=10, fill="#2e2920")
    d.text((W / 2, 392), "make demo", font=font(30, True), fill=BEE, anchor="mm")
    d.text((W / 2, 500), repo, font=font(24), fill=SOFT, anchor="mm")
    d.text((W / 2, 560), "Rendered in code from experiments/results. No generated footage.", font=font(20),
           fill=SOFT, anchor="mm")
    img.save(out)


def _num(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def hypotheses_card(out: Path) -> None:
    m = json.loads((OUT / "main_results.json").read_text())
    e5 = json.loads((OUT / "e5_results.json").read_text())
    dl = m["E1"]["by_condition"]["deliveries"]
    sc = m["E2"]["sting_change"]
    ed = e5["a"]["deliveries"]
    rows = [
        ("E1", "Memory and talk make a better gatherer.",
         f"No. {_num(dl['full']['mean'])} deliveries in 2 years (n {dl['full']['n']}), rule bees {_num(dl['rule_bees']['mean'])}."),
        ("E2", "Hornets evolve to exploit the colony.",
         f"No. Stings per trip rose {_num(sc['full']['mean'])}, and {_num(sc['frozen_hornets']['mean'])} with frozen hornets."),
        ("E3", "Talk keeps spring's place alive into year 2.",
         "No. No bee lived through both springs; nothing was carried over."),
        ("E4", "Two meaningless sounds come to mean something.",
         "Not testable. Bees made 3 sounds in 6,610 decisions."),
        ("E5", "Once bloom is reachable, talk raises gathering.",
         f"No. {_num(ed['e5_full']['mean'])} a year with talk, {_num(ed['e5_no_talk']['mean'])} without (n 5 each)."),
    ]
    img, d = _base()
    d.text((80, 70), "What we expected, and what happened", font=font(38, True), fill=INK)
    d.text((80, 126), "Registered in advance (E5 before its own runs). None was supported.", font=font(22), fill=SOFT)
    for i, (k, hyp, res) in enumerate(rows):
        y = 190 + 92 * i
        d.rounded_rectangle([80, y, 1200, y + 78], radius=10, fill=CARD, outline=LINE)
        d.text((104, y + 39), k, font=font(26, True), fill=ACCENT, anchor="lm")
        d.text((180, y + 22), hyp, font=font(21), fill=SOFT, anchor="lm")
        d.text((180, y + 54), res, font=font(23, True), fill=INK, anchor="lm")
    d.text((80, 676), "Source: experiments/analysis/output/main_results.json and e5_results.json", font=font(17), fill=SOFT)
    img.save(out)


def brief_card(out: Path) -> None:
    """The brief's five judging criteria and weights (docs/challenge-brief.txt, section 11), each with what answers it."""
    rows = [
        ("Technical depth", "30%", "Evolving hornet genomes, per-bee memory with recall, a navigation layer,",
         "a leak-tested perception boundary, byte-identical replay"),
        ("Originality and creativity", "25%", "Culture and memory in a grounded, mortal colony,",
         "not a text-only chat"),
        ("Behaviour and experimentation", "20%", "Hypotheses registered in advance, ablations and baselines,",
         "negative results reported as such"),
        ("Engineering and reproducibility", "15%", "make demo replays a logged run with no API key;",
         "fixed seeds, configs and tests"),
        ("Effective use of tools, including AI", "10%", "Every agent session's trace is in the repository;",
         "AI_DISCLOSURE.md says who did what"),
    ]
    img, d = _base()
    d.text((80, 62), "How Hearsay meets the brief", font=font(38, True), fill=INK)
    d.text((80, 116), "The five judging criteria and their weights, from the challenge brief.", font=font(22),
           fill=SOFT)
    for i, (name, weight, a, b) in enumerate(rows):
        y = 168 + 100 * i
        d.rounded_rectangle([80, y, 1200, y + 86], radius=10, fill=CARD, outline=LINE)
        d.text((104, y + 43), weight, font=font(28, True), fill=ACCENT, anchor="lm")
        d.text((210, y + 22), name, font=font(23, True), fill=INK, anchor="lm")
        d.text((210, y + 50), a, font=font(19), fill=SOFT, anchor="lm")
        d.text((210, y + 72), b, font=font(19), fill=SOFT, anchor="lm")
    d.text((80, 684), "Source: docs/challenge-brief.txt, section 11", font=font(17), fill=SOFT)
    img.save(out)
