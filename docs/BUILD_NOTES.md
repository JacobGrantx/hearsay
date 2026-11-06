# Build notes (handoff between build phases)

Written by the phase 1 build session (Claude Code, 2026-11-06). Phase 1 is the world with no AI: layout, seasons, evolving hornets, scripted bees, logging, tests and calibration. Later phases plug the AI mind in through the policy interface below.

## Log format

Format version 1. Every seed of every run writes one run directory:

```
experiments/results/<experiment>/<UTC stamp>[_<tag>]/seed-<n>/
    record.json        written by experiments/run.py: params, seed, provenance, final_metrics (the run summary)
    layout.json        the world, written once before tick 0
    state.jsonl.gz     gzip-compressed JSONL, one line per tick: positions and state of everything
    events.jsonl       one line per event
    metrics.jsonl      one line per season
```

Coordinates are `[x, y]` with x to the right and y downward, 0-based. Moves are 4-neighbour.

### layout.json

```json
{
  "format": 1,
  "width": 80, "height": 48,
  "rows": ["#####...", "#HHH...", "..."],
  "home": [3, 23],
  "entrances": [[7, 22], [4, 19], [4, 28]],
  "bloom": {"spring": [[x, y], ...9 cells], "summer": [...], "autumn": [...]},
  "bloom_distance": {"spring": 61, "summer": 74, "autumn": 58},
  "season_names": ["spring", "summer", "autumn", "winter"],
  "season_length": 250, "years": 2, "ticks": 2000,
  "base_life": 250, "life_cap": 750, "max_bees": 12,
  "vision": 4, "bloom_vision": 6, "hearing": 10,
  "condition": "rule_bees", "seed": 0,
  "bee_fields": ["id", "x", "y", "life", "carrying", "stunned", "intent"],
  "hornet_fields": ["id", "x", "y", "smell", "hearing", "ambush", "target", "mode"],
  "sound_fields": ["bee", "x", "y", "sound"]
}
```

- `rows`: `height` strings of `width` characters. `#` wall, `.` open, `H` hive interior, `E` hive entrance. Entrances count as hive cells: hornets never stand on `H` or `E`.
- `home`: the hive's centre cell, the position every bee is told is home.
- `bloom`: the 3 x 3 patch for each season. Winter has none. The same cells bloom every year.
- `bloom_distance`: shortest path in steps from `home` to the nearest cell of each patch.

### state.jsonl.gz

One JSON object per tick, written after the tick has resolved:

```json
{"t": 0, "s": 0, "y": 0,
 "b": [[0, 3, 23, 249.0, 0, 0, "explore:NE"], ...],
 "h": [[0, 52, 11, 4, 3, 3, -1, "wander"], ...],
 "snd": [[2, 40, 18, "sound-1"]]}
```

- `t` tick (0-based), `s` season index (0 spring, 1 summer, 2 autumn, 3 winter), `y` year (0-based).
- `b`, one array per living bee, in `bee_fields` order: id, x, y, life (1 decimal), carrying (0 or 1), stunned (ticks of stun left, 0 if not stunned), intent.
  - intent is one of `explore:<dir>` (dir is N, NE, E, SE, S, SW, W or NW), `go_to:<x>,<y>`, `go_home`, `flee`, `wait`, or `""` before the bee's first decision.
- `h`, one array per hornet on the map, in `hornet_fields` order: id, x, y, the three genes, target (bee id, or -1), mode (`chase`, `sound`, `ambush` or `wander`). Empty in winter.
- `snd`, sounds made this tick: bee id, x, y, `sound-1` or `sound-2`. Other bees and hornets hear them on the next tick.

Read it in a browser with `new Response(blob.stream().pipeThrough(new DecompressionStream("gzip"))).text()`, then split on newlines.

### events.jsonl

One object per line. Every event has `kind` and `t`.

| kind | fields |
|---|---|
| `season` | season (name), year |
| `hatch` | bee, x, y, life, cause (`start` for the founding bees, `delivery` otherwise) |
| `queen_hatch` | bee, x, y, life |
| `decision` | bee, trigger, intent, direction, target, sound, remember, say |
| `say` | bee, text, heard_by (list of bee ids) |
| `bloom` | bee, x, y (the bee picked up from bloom and is now carrying) |
| `delivery` | bee, life_before, life_after |
| `heal` | bee, amount, life_after |
| `sting` | hornet, bee, x, y, amount, life_after |
| `death` | bee, x, y, age, cause (`life`: life reached 0) |
| `trip` | bee, start, ticks, delivered, reached_bloom (ticks from leaving to reaching bloom, or null), stings, outcome (`home` or `died`) |
| `hornet_spawn` | hornet, x, y, genes ([smell, hearing, ambush]), parent (hornet id or null) |
| `hornet_replaced` | removed, removed_fitness, parent, child, genes |
| `hornet_dormant` | hornets (list of [id, smell, hearing, ambush, fitness]) |
| `end` | bees_alive |

`decision.trigger` is one of `timer`, `stung`, `hornet`, `bloom`, `sound`, `arrived`, `home`, `life50`, `life25`, `hatched`. Decision `target` is `[x, y]` or null; `direction` is a direction string or null.

### metrics.jsonl

One row per season, written at the season's last tick (`step`):

| field | meaning |
|---|---|
| `step`, `year`, `season` | last tick of the season, year (0-based), season name |
| `trips` | trips that started this season (a trip starts when a bee steps out of the hive) |
| `deliveries` | deliveries this season |
| `delivery_rate` | deliveries / trips, null if no trips |
| `stings`, `stings_per_trip` | stings this season, and stings / trips |
| `median_to_bloom` | median ticks from leaving the hive to reaching bloom, over trips that reached it; null if none |
| `first_delivery` | ticks after the season's start of its first delivery; null if none |
| `bees_end`, `bees_mean` | colony size at the season's end, and mean over its ticks |
| `hatches`, `queen_hatches`, `deaths` | counts this season |
| `sounds_1`, `sounds_2` | sounds made this season |
| `hornets`, `smell`, `hearing`, `ambush` | hornets on the map at the season's end, and their mean genes (null in winter) |
| `hornet_damage` | life removed by stings this season |
