"""The demo video's storyboard: every segment, the run it comes from, its ticks and its captions.

Map segments are real runs replayed by viewer/capture.py. The moments were found by
experiments/analysis/find_moments.py and checked against each run's events.jsonl; every tick, life
value and quote in a caption is copied from those events. make_video.py renders this list and
writes demo/recordings/SOURCES.md from it, so the two cannot drift apart.
"""
FPS = 30
SIZE = (1280, 720)

MAIN = "experiments/results/full/20261106T101558Z/seed-0"
E5 = "experiments/results/e5_full/20261106T112913Z_s0/seed-0"

# kind "map": capture ticks t0..t1 over `seconds` (step = (t1 - t0) / (seconds * FPS)), following `bee`,
# framed on `view` (x0,y0,x1,y1 in cells, or None for the whole map). Captions are (start s, end s, text).
SEGMENTS = [
    dict(id="01_title", kind="card", card="title", seconds=3.0),
    dict(id="02_world", kind="map", run=MAIN, t0=0, t1=80, seconds=8.0, bee=None, view=None,
         beat="The world", captions=[
             (0.0, 4.0, "The main world: an 80 by 48 maze. Home is on the left, the bloom far to the right."),
             (4.0, 8.0, "Each bee is a Claude Haiku 5.5 mind. It is never told it is a bee, or what anything is.")]),
    dict(id="03_first_sight", kind="map", run=MAIN, t0=28, t1=44, seconds=5.0, bee=5, view="8,5,42,29",
         beat="Danger: caution before any sting", captions=[
             (0.0, 2.6, "Tick 34. Bee 5 sees a moving thing for the first time. It has never been stung. It flees."),
             (2.6, 5.0, "Nobody told it moving things hurt. This caution is the model's prior, not learning.")]),
    dict(id="04_stung", kind="map", run=MAIN, t0=98, t1=183, seconds=6.0, bee=1, view=None,
         beat="Danger: a sting", captions=[
             (0.0, 3.0, "Bee 1 picks up bloom at tick 100. A hornet stings it twice: life 199, then 94."),
             (3.0, 6.0, "It carries the bloom home anyway, and arrives at tick 183 with 23 life left.")]),
    dict(id="05_warns", kind="map", run=MAIN, t0=183, t1=190, seconds=3.5, bee=1, view="0,13,30,35",
         beat="Danger: what the bee says at home", captions=[
             (0.0, 3.5, "Tick 184. At home it tells newborn bee 6: \"Bright cells there are dangerous.\"")]),
    dict(id="06_e5_finder", kind="map", run=E5, t0=55, t1=166, seconds=7.0, bee=4, view=None,
         beat="E5: a first finder", captions=[
             (0.0, 3.5, "Experiment E5: a smaller world where the bloom is within reach. Seed 0 of 5."),
             (3.5, 7.0, "Bee 4 finds the spring bloom at tick 60. At tick 166 it delivers, and bee 6 hatches.")]),
    dict(id="07_e5_tells", kind="map", run=E5, t0=166, t1=170, seconds=4.5, bee=4, view="0,7,26,27",
         beat="E5: hive talk passes the place", captions=[
             (0.0, 4.5, "Tick 167. Bee 4 at home: \"Back home carrying a bright thing from around (36,3), "
                        "found in the east. Members should know it is there.\"")]),
    dict(id="08_e5_hears", kind="map", run=E5, t0=170, t1=174, seconds=4.5, bee=6, view="0,7,26,27",
         beat="E5: the newborn keeps the place", captions=[
             (0.0, 4.5, "Tick 172. Bee 6, six ticks old, writes: \"Heard the valuable thing was found "
                        "near (37,3) in the east; explore east next.\"")]),
    dict(id="09_e5_delivers", kind="map", run=E5, t0=174, t1=332, seconds=8.0, bee=6, view=None,
         beat="E5: a talk-informed delivery", captions=[
             (0.0, 4.0, "Bee 6 heads northeast toward (37,3), and reaches the bloom at tick 224."),
             (4.0, 8.0, "It delivers at tick 330. Talk carried a place, in 1 of 5 seeds. The bar we set in advance was 2.")]),
    dict(id="10_summer", kind="map", run=E5, t0=298, t1=440, seconds=8.0, bee=1, view=None,
         beat="Seasons: the bloom moves", captions=[
             (0.0, 3.0, "Summer. The bloom has moved. Bee 1 heads back to (37,3), where spring's bloom was."),
             (3.0, 5.4, "Ticks 355 and 357: two stings at the old spring place, now empty."),
             (5.4, 8.0, "Fleeing home, it sees the summer bloom, takes it, and delivers at tick 436.")]),
    dict(id="11_winter", kind="map", run=E5, t0=740, t1=1000, seconds=4.5, bee=None, view=None,
         beat="Seasons: winter", captions=[
             (0.0, 4.5, "Winter. Nothing blooms. Bees run out of life, and the colony falls from 7 to 4.")]),
    dict(id="12_hypotheses", kind="card", card="hypotheses", seconds=6.0),
    dict(id="13_chart_e1", kind="card", card="chart_e1", seconds=5.0),
    dict(id="14_chart_caution", kind="card", card="chart_caution", seconds=5.0),
    dict(id="15_chart_e5", kind="card", card="chart_e5", seconds=5.5),
    dict(id="16_end", kind="card", card="end", seconds=5.0),
]


def step(seg: dict) -> float:
    return (seg["t1"] - seg["t0"]) / (seg["seconds"] * FPS)


def total_seconds() -> float:
    return sum(s["seconds"] for s in SEGMENTS)
