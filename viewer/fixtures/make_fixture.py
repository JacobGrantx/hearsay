"""Write a small synthetic run directory in the documented log format (format 1).

This is a viewer test fixture, not a result: scripted movers on a 40 x 24 map
that exercise every event kind the viewer draws. Deterministic for a given seed.

    python viewer/fixtures/make_fixture.py [OUT_DIR] [--seed N]
"""
import argparse
import gzip
import json
import random
from collections import deque
from pathlib import Path

W, H, SEASON, YEARS, BASE_LIFE, MAX_BEES = 40, 24, 40, 1, 120, 12
SEASONS = ["spring", "summer", "autumn", "winter"]
HORNETS_PER_SEASON = [3, 4, 5, 0]
DIRS = {"N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1),
        "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1)}
BELIEFS = ["bright cells lie far to the east", "the moving things wait near bright cells",
           "the upper corridor is quieter", "sound two came before the sting",
           "home is west, follow the long corridor back", "bright spot moved since last time"]
SAYS = ["bright cells east past the second room", "avoid the lower corridor, I was hit there",
        "the second sound meant danger to me", "nothing found north"]


def make_map(rng):
    g = [["#"] * W for _ in range(H)]
    stack, seen = [(9, 1)], {(9, 1)}
    g[1][9] = "."
    while stack:  # carve a maze on odd cells, x >= 9 (the hive sits to the left)
        x, y = stack[-1]
        nxt = [(x + dx, y + dy, dx, dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
               if 9 <= x + dx < W - 1 and 1 <= y + dy < H - 1 and (x + dx, y + dy) not in seen]
        if not nxt:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(nxt)
        g[y + dy // 2][x + dx // 2] = g[ny][nx] = "."
        seen.add((nx, ny))
        stack.append((nx, ny))
    for y in range(1, H - 1):  # braid: knock out walls to make loops and rooms
        for x in range(9, W - 1):
            if g[y][x] == "#" and rng.random() < 0.3:
                g[y][x] = "."
    for y in range(8, 16):
        for x in range(1, 8):
            g[y][x] = "H"
    entrances = [(8, 9), (8, 12), (8, 15)]
    for x, y in entrances:
        g[y][x] = "E"
        g[y][9] = "."
    bloom = {}
    for name, (cx, cy) in zip(SEASONS[:3], [(rng.randint(22, 27), rng.randint(3, 6)),
                                            (rng.randint(32, 36), rng.randint(10, 13)),
                                            (rng.randint(24, 30), rng.randint(17, 20))]):
        bloom[name] = [(cx + i, cy + j) for j in (-1, 0, 1) for i in (-1, 0, 1)]
        for x, y in bloom[name]:
            g[y][x] = "."
    return g, entrances, bloom


def bfs(g, start, passable):
    dist, prev, q = {start: 0}, {start: None}, deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if 0 <= n[0] < W and 0 <= n[1] < H and n not in dist and passable(g[n[1]][n[0]]):
                dist[n], prev[n] = dist[(x, y)] + 1, (x, y)
                q.append(n)
    return dist, prev


def step_toward(g, a, goals, passable):
    dist, prev = bfs(g, a, passable)
    reach = [c for c in goals if c in dist]
    if not reach:
        return a
    c = min(reach, key=dist.get)
    while prev[c] is not None and prev[c] != a:
        c = prev[c]
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(Path(__file__).parent / "synthetic-run"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    g, entrances, bloom = make_map(rng)
    home = (4, 12)
    hive = [(x, y) for y in range(H) for x in range(W) if g[y][x] in "HE"]
    open_out = [(x, y) for y in range(H) for x in range(W) if g[y][x] == "."]
    bee_ok, hornet_ok = (lambda c: c != "#"), (lambda c: c == ".")
    dist_home, _ = bfs(g, home, bee_ok)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ticks = SEASON * 4 * YEARS
    layout = {
        "format": 1, "width": W, "height": H, "rows": ["".join(r) for r in g],
        "home": list(home), "entrances": [list(e) for e in entrances],
        "bloom": {k: [list(c) for c in v] for k, v in bloom.items()},
        "bloom_distance": {k: min(dist_home[c] for c in v) for k, v in bloom.items()},
        "season_names": SEASONS, "season_length": SEASON, "years": YEARS, "ticks": ticks,
        "base_life": BASE_LIFE, "life_cap": 3 * BASE_LIFE, "max_bees": MAX_BEES,
        "vision": 4, "bloom_vision": 6, "hearing": 10, "condition": "synthetic", "seed": args.seed,
        "bee_fields": ["id", "x", "y", "life", "carrying", "stunned", "intent"],
        "hornet_fields": ["id", "x", "y", "smell", "hearing", "ambush", "target", "mode"],
        "sound_fields": ["bee", "x", "y", "sound"],
    }
    (out / "layout.json").write_text(json.dumps(layout))
    events, states, metrics = [], [], []
    ev = lambda kind, t, **kw: events.append({"kind": kind, "t": t, **kw})
    bees, hornets, next_bee, next_hornet = {}, {}, 0, 0
    season_count = {}

    def hatch(t, kind, cause=None):
        nonlocal next_bee
        x, y = rng.choice(hive)
        bees[next_bee] = {"x": x, "y": y, "life": float(BASE_LIFE), "carry": 0, "stun": 0,
                          "intent": "", "born": t, "goal": None, "cool": {}, "rest": 3}
        kw = {"cause": cause} if cause else {}
        ev(kind, t, bee=next_bee, x=x, y=y, life=float(BASE_LIFE), **kw)
        next_bee += 1

    for _ in range(4):
        hatch(0, "hatch", "start")
    for t in range(ticks):
        s, yr = (t // SEASON) % 4, t // (SEASON * 4)
        if t % SEASON == 0:
            ev("season", t, season=SEASONS[s], year=yr)
            season_count = {"stings": 0, "deliveries": 0, "hatches": 0, "deaths": 0, "s1": 0, "s2": 0}
            if s == 3:
                ev("hornet_dormant", t, hornets=[[i, *h["genes"], 0.0] for i, h in hornets.items()])
                hornets.clear()
        while s < 3 and len(hornets) < HORNETS_PER_SEASON[s]:
            x, y = rng.choice([c for c in open_out if c[0] > 20])
            genes = [rng.randint(1, 6)]
            genes += [rng.randint(0, 10 - genes[0])]
            genes.append(10 - genes[0] - genes[1])
            hornets[next_hornet] = {"x": x, "y": y, "genes": genes, "target": -1, "mode": "wander"}
            ev("hornet_spawn", t, hornet=next_hornet, x=x, y=y, genes=genes, parent=None)
            next_hornet += 1
        sounds = []
        for i, b in list(bees.items()):
            pos, in_hive = (b["x"], b["y"]), g[b["y"]][b["x"]] in "HE"
            b["life"] -= (2 if not in_hive else 0.5) if s == 3 else 1
            if b["stun"]:
                b["stun"] -= 1
            elif b["rest"]:
                b["rest"] -= 1
            else:
                goal = [home] if (b["carry"] or s == 3 or b["life"] < BASE_LIFE * 0.3) else bloom[SEASONS[s]]
                intent = "go_home" if goal == [home] else "go_to:%d,%d" % goal[4]
                if intent != b["intent"] or t % 5 == 0:
                    trig = "timer" if t % 5 == 0 else ("arrived" if b["carry"] else "home")
                    mem = rng.choice(BELIEFS) if rng.random() < 0.4 else ""
                    snd = "none"
                    ev("decision", t, bee=i, trigger=trig, intent=intent.split(":")[0], direction=None,
                       target=None if goal == [home] else list(goal[4]), sound=snd, remember=mem,
                       say=rng.choice(SAYS) if in_hive and rng.random() < 0.5 else "")
                    if in_hive and events[-1]["say"]:
                        heard = [j for j, o in bees.items() if j != i and g[o["y"]][o["x"]] in "HE"]
                        ev("say", t, bee=i, text=events[-1]["say"], heard_by=heard)
                b["intent"] = intent
                b["x"], b["y"] = step_toward(g, pos, goal, bee_ok)
            near = any(abs(h["x"] - b["x"]) + abs(h["y"] - b["y"]) <= 4 for h in hornets.values())
            if (near and rng.random() < 0.15) or (b["carry"] and rng.random() < 0.03):
                snd = "sound-2" if near else "sound-1"
                sounds.append([i, b["x"], b["y"], snd])
                season_count["s1" if snd == "sound-1" else "s2"] += 1
                b["life"] -= 1
            if not b["carry"] and s < 3 and (b["x"], b["y"]) in bloom[SEASONS[s]]:
                b["carry"] = 1
                ev("bloom", t, bee=i, x=b["x"], y=b["y"])
            if b["carry"] and g[b["y"]][b["x"]] in "HE":
                before = b["life"]
                b["life"], b["carry"], b["rest"] = min(before * 2, 3 * BASE_LIFE), 0, 2
                ev("delivery", t, bee=i, life_before=before, life_after=b["life"])
                season_count["deliveries"] += 1
                if len(bees) < MAX_BEES:
                    hatch(t, "hatch", "delivery")
                    season_count["hatches"] += 1
            if b["life"] <= 0:
                ev("death", t, bee=i, x=b["x"], y=b["y"], age=t - b["born"], cause="life")
                season_count["deaths"] += 1
                del bees[i]
        for k, h in hornets.items():
            prey = [(abs(b["x"] - h["x"]) + abs(b["y"] - h["y"]), i) for i, b in bees.items()
                    if g[b["y"]][b["x"]] == "."]
            prey = [p for p in prey if p[0] <= h["genes"][0] + 2]
            if prey:
                d, i = min(prey)
                b = bees[i]
                h["target"], h["mode"] = i, "chase"
                if d == 1 and b["life"] > 2 and t - b["cool"].get(k, -99) >= 10:
                    amt = int(b["life"] // 2)
                    b["life"] -= amt
                    b["stun"], b["cool"][k] = 2, t
                    ev("sting", t, hornet=k, bee=i, x=b["x"], y=b["y"], amount=amt, life_after=b["life"])
                    season_count["stings"] += 1
                elif d > 1:
                    h["x"], h["y"] = step_toward(g, (h["x"], h["y"]), [(b["x"], b["y"])], hornet_ok)
            else:
                h["target"], h["mode"] = -1, "wander"
                opts = [(h["x"] + dx, h["y"] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if g[h["y"] + dy][h["x"] + dx] == "."]
                h["x"], h["y"] = rng.choice(opts) if opts else (h["x"], h["y"])
        if len(bees) < 2:
            hatch(t, "queen_hatch")
        states.append({"t": t, "s": s, "y": yr,
                       "b": [[i, b["x"], b["y"], round(b["life"], 1), b["carry"], b["stun"], b["intent"]]
                             for i, b in bees.items()],
                       "h": [[k, h["x"], h["y"], *h["genes"], h["target"], h["mode"]] for k, h in hornets.items()],
                       "snd": sounds})
        if t % SEASON == SEASON - 1:
            metrics.append({"step": t, "year": yr, "season": SEASONS[s], "bees_end": len(bees),
                            "deliveries": season_count["deliveries"], "stings": season_count["stings"],
                            "hatches": season_count["hatches"], "deaths": season_count["deaths"],
                            "sounds_1": season_count["s1"], "sounds_2": season_count["s2"],
                            "hornets": len(hornets)})
    ev("end", ticks - 1, bees_alive=len(bees))
    with gzip.GzipFile(out / "state.jsonl.gz", "wb", mtime=0) as f:
        f.write("".join(json.dumps(s, separators=(",", ":")) + "\n" for s in states).encode())
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    (out / "metrics.jsonl").write_text("".join(json.dumps(m) + "\n" for m in metrics))
    (out / "record.json").write_text(json.dumps({"synthetic": True, "note": "viewer test fixture, not a result",
                                                 "seed": args.seed}, indent=1))
    print(out, len(states), "ticks,", len(events), "events")


if __name__ == "__main__":
    main()
