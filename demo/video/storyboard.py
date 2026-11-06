"""The demo video's storyboard: every segment, the run it comes from, its ticks, captions and narration.

Map segments are real runs replayed by viewer/capture.py. The moments were found by
experiments/analysis/find_moments.py and checked against each run's events.jsonl; every tick, life
value and quote in a caption or a narration line is copied from those events, and every result from
EXPERIMENTS.md. narrate.py speaks the `narration` lines; make_video.py stretches each segment to fit its
line, renders this list and writes demo/recordings/SOURCES.md from it, so the three cannot drift apart.
"""
import math

FPS = 30
SIZE = (1280, 720)
LEAD, TAIL = 0.25, 0.6  # seconds of quiet before and after each spoken line

MAIN = "experiments/results/full/20261106T101558Z/seed-0"
E5 = "experiments/results/e5_full/20261106T112913Z_s0/seed-0"

# kind "map": capture ticks t0..t1 over `seconds` (step = (t1 - t0) / (seconds * FPS)), following `bee`,
# framed on `view` (x0,y0,x1,y1 in cells, or None for the whole map). Captions are (start s, end s, text).
# `seconds` is the shortest the segment may be; fit() lengthens it to its spoken line, slowing the capture.
SEGMENTS = [
    dict(id="01_open", kind="card", card="title", seconds=3.0,
         narration="Hearsay asks one question of digital life: can knowledge outlive the one who found it? "
                   "It is a colony of language-model agents in a maze. They find things, can share them only "
                   "at home, and die."),
    dict(id="02_world", kind="map", run=MAIN, t0=0, t1=80, seconds=8.0, bee=None, view=None,
         beat="The world", captions=[
             (0.0, 4.0, "An 80 by 48 maze. Home on the left, bloom far right."),
             (4.0, 8.0, "Each bee: a Claude Haiku 5.5 mind, never told what anything is.")],
         narration="Each bee is a Claude Haiku 5.5 mind. It sees only nearby cells, keeps its own memories, "
                   "and can talk only at home. Hornets evolve by selection and mutation. Seasons move the "
                   "bloom. The bees are never told what the hornets or the bloom are; they get only plain "
                   "words like moving thing and bright cell."),
    dict(id="03_first_sight", kind="map", run=MAIN, t0=28, t1=44, seconds=5.0, bee=5, view="8,5,42,29",
         beat="Danger: caution before any sting", captions=[
             (0.0, 2.6, "Tick 34. Bee 5's first moving thing. Never stung. It flees."),
             (2.6, 5.0, "Not learned: the model's prior, the word flee in its prompt, or both.")],
         narration="Tick 34. Bee 5 sees a moving thing for the first time, and flees. It has never been "
                   "stung, so this caution was not learned. It came from the model's prior, the word flee "
                   "in its prompt, or both."),
    dict(id="04_stung", kind="map", run=MAIN, t0=98, t1=183, seconds=6.0, bee=1, view=None,
         beat="Danger: a sting", captions=[
             (0.0, 3.0, "Tick 100: bloom. Two stings: life 199, then 94."),
             (3.0, 6.0, "Home at tick 183 with 23 life left.")],
         narration="Bee 1 picks up bloom at tick 100. A hornet stings it twice. It carries the bloom home "
                   "anyway, and arrives with 23 life left."),
    dict(id="05_warns", kind="map", run=MAIN, t0=183, t1=190, seconds=3.5, bee=1, view="0,13,30,35",
         beat="Danger: what the bee says at home", captions=[
             (0.0, 3.5, "Tick 184, to newborn bee 6: \"Bright cells there are dangerous.\"")],
         narration="At home it tells newborn bee 6: bright cells there are dangerous. No prompt contains "
                   "the word danger."),
    dict(id="06_e5_finder", kind="map", run=E5, t0=55, t1=166, seconds=7.0, bee=4, view=None,
         beat="E5: a first finder", captions=[
             (0.0, 3.5, "Experiment E5: bloom within reach. Seed 0 of 5."),
             (3.5, 7.0, "Bee 4: bloom at tick 60, delivered at 166. Bee 6 hatches.")],
         narration="Experiment five: a smaller world, with the bloom in reach. Bee 4 finds it at tick 60 "
                   "and delivers at tick 166, and bee 6 hatches."),
    dict(id="07_e5_tells", kind="map", run=E5, t0=166, t1=170, seconds=4.5, bee=4, view="0,7,26,27",
         beat="E5: hive talk passes the place", captions=[
             (0.0, 4.5, "Tick 167, bee 4: \"...from around (36,3), found in the east. "
                        "Members should know it is there.\"")],
         narration="At home, bee 4 says: back home carrying a bright thing from around 36, 3, found in the "
                   "east. Members should know it is there."),
    dict(id="08_e5_hears", kind="map", run=E5, t0=171.5, t1=174.5, seconds=4.5, bee=6, view="0,7,26,27",
         beat="E5: the newborn keeps the place", captions=[
             (0.0, 4.5, "Tick 172, bee 6: \"Heard the valuable thing was found near (37,3) in the east; "
                        "explore east next.\"")],
         narration="Bee 6, six ticks old, writes: heard the valuable thing was found near 37, 3, in the "
                   "east. Explore east next."),
    dict(id="09_e5_delivers", kind="map", run=E5, t0=174.5, t1=332, seconds=8.0, bee=6, view=None,
         beat="E5: a talk-informed delivery", captions=[
             (0.0, 4.0, "Bee 6 reaches the bloom at tick 224."),
             (4.0, 8.0, "Delivers at tick 330. Seen in 1 of 5 seeds; the bar set in advance was 2.")],
         narration="It reaches the bloom at tick 224 and delivers at tick 330. Talk carried a place, in one "
                   "seed of five. The bar we set in advance was two."),
    dict(id="10_summer", kind="map", run=E5, t0=298, t1=440, seconds=8.0, bee=1, view=None,
         beat="Seasons: the bloom moves", captions=[
             (0.0, 3.0, "Summer. Bee 1 heads back to spring's place, (37,3)."),
             (3.0, 5.4, "Ticks 355 and 357: two stings at the empty old place."),
             (5.4, 8.0, "Fleeing home, it finds the summer bloom. Delivered, tick 436.")],
         narration="Summer. The bloom has moved. Bee 1 goes back to spring's old place, and is stung twice "
                   "there. Fleeing home, it finds the summer bloom and delivers."),
    dict(id="11_winter", kind="map", run=E5, t0=740, t1=1000, seconds=4.5, bee=None, view=None,
         beat="Seasons: winter", captions=[
             (0.0, 4.5, "Winter. The colony falls from 7 to 4.")],
         narration="Winter. Nothing blooms. Bees run out of life, and the colony falls from 7 to 4."),
    dict(id="12_hypotheses", kind="card", card="hypotheses", seconds=6.0,
         narration="We registered every hypothesis in advance. None was supported. Stings rose in year two "
                   "even with hornets that could not evolve. No bee lived through both springs. And the "
                   "bees made 3 sounds in 6,610 decisions."),
    dict(id="13_chart_e1", kind="card", card="chart_e1", seconds=5.0,
         narration="With memory and talk, bees made 1.8 deliveries in two years, the same as scripted rule "
                   "bees."),
    dict(id="14_chart_caution", kind="card", card="chart_caution", seconds=5.0,
         narration="At a first sight of a moving thing, bees fled or went home 0.857 of the time, and 1.000 "
                   "of the time with no memory at all, against 0.110 to 0.282 at routine decisions."),
    dict(id="15_chart_e5", kind="card", card="chart_e5", seconds=5.5,
         narration="In experiment five, talk did not pay: 5.2 deliveries a year with talk, 8.2 without. And "
                   "colonies that could talk stayed home more."),
    dict(id="16_brief", kind="card", card="brief", seconds=5.0,
         narration="How Hearsay meets the brief. Technical depth: evolving hornet genomes, memory with "
                   "recall, a navigation layer, a leak-tested perception boundary, and byte-identical "
                   "replay. Originality: culture and memory in a grounded, mortal colony, not a text-only "
                   "chat. Behaviour and experiments: pre-registered hypotheses, ablations and baselines, "
                   "and negative results reported as such. Engineering: make demo replays a logged run with "
                   "no API key, with seeds and tests. Tool use: every agent session's trace is in the "
                   "repository, and the AI disclosure says who did what."),
    dict(id="17_end", kind="card", card="end", seconds=5.0,
         narration="A second round, with abstract words that carry no real-world meaning, ran on the "
                   "morning of the deadline. Its results are in the read-me. Every frame here is a logged "
                   "run. Replay it with make demo."),
]


def fit(seg: dict, spoken: float) -> dict:
    """The segment lengthened (to whole frames) to hold LEAD + its spoken line + TAIL, captions scaled."""
    need = math.ceil((LEAD + spoken + TAIL) * FPS) / FPS if spoken else 0.0
    seconds = max(seg["seconds"], need)
    k = seconds / seg["seconds"]
    caps = [(round(a * k, 2), round(b * k, 2), text) for a, b, text in seg.get("captions", [])]
    return dict(seg, seconds=seconds, captions=caps)


def step(seg: dict) -> float:
    return (seg["t1"] - seg["t0"]) / (seg["seconds"] * FPS)


def total_seconds(segments: list = SEGMENTS) -> float:
    return sum(s["seconds"] for s in segments)
