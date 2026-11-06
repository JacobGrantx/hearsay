# Viewer

**Commands:** `python viewer/bundle.py RUN_DIR -o run.html` writes one self-contained page you open from file://; `python viewer/capture.py run.html out.mp4 --from 0 --to 400 --step 0.5 --fps 30 [--bee ID]` renders it to video headless.

The viewer replays any run directory written by `experiments/run.py` (log format 1, described in `docs/BUILD_NOTES.md`). It reads only the logs, so what you see is what the run recorded.

## What the page shows

- The maze, the hive with its entrances, and the bloom. The patch in season is drawn in flower; the other sites are faint dashed outlines.
- A light colour wash for the season, with the season and year in the top right.
- Bees in warm yellow. The thin ring around each bee is its life left, out of the life cap (3 x base life). The ring turns red below a quarter of base life. A green dot means the bee is carrying from bloom. A stunned bee has a red edge.
- Hornets as orange-brown diamonds with a dark band. A dashed line joins a chasing hornet to its target.
- Sound ripples spreading to the hearing radius (10 cells): sound 1 in teal, sound 2 in magenta.
- A red flash on each sting, a gold sparkle on each hatching, a gold pulse on each delivery, and a grey fade where a bee died.
- The side panel. With nothing selected it shows the colony now and this season's deliveries, stings, hatchings and deaths, plus a key. Select a bee to see its life, what it is doing, its recent decisions (trigger, intent, sound, remember, say), what it has written to memory, and what it heard at home. Select a hornet to see its genes.

Positions are interpolated between ticks, so playback is smooth at any speed.

## Controls

- Play or pause with the button or the space bar. Left and right arrows step one tick.
- Drag the timeline to scrub. The speed menu sets ticks per second.
- Click or tap a bee or hornet to select it. Selection hit-tests the position it is drawn at. Click empty ground or press Escape to clear.
- Wheel or pinch to zoom around the pointer, drag to pan, double-click to fit the map again.
- Link to a moment with `#t=TICK&bee=ID` after the file name.

## Capture mode and video

`capture.py` loads the page with `#capture&from=T0&to=T1&step=S[&bee=ID][&view=x0,y0,x1,y1]`. In this mode the controls are hidden, nothing animates on its own, and the page exposes `window.__capture.count` and `window.__capture.frame(i)`, which draws tick `T0 + i * S`. Every effect is a function of the gap between the frame's tick and the event's tick, so a frame looks the same whatever order frames are drawn in. The test suite checks that the same frame gives byte-identical screenshots.

```bash
# a still of one moment, following bee 3
python viewer/capture.py run.html still.png --from 98 --bee 3
# video of ticks 0 to 400, 2 frames per tick at 30 fps (about 27 seconds), zoomed on part of the map
python viewer/capture.py run.html out.mp4 --from 0 --to 400 --step 0.5 --fps 30 --view 0,10,40,40
```

Capture drives Playwright's `chrome-headless-shell` through the DevTools protocol over a pipe (`--remote-debugging-pipe`), so it needs no Python packages beyond the standard library. It looks for the shell in `$VIEWER_CHROME`, then in `~/.cache/ms-playwright/chromium_headless_shell-*`. Frames are written to a scratch directory on `/dev/shm` and deleted once ffmpeg (libx264, yuv420p) has encoded them. On the shared 4-core build VM, under load from other jobs, capture ran at 5 to 8 frames per second.

## Files

| File | Role |
|---|---|
| `bundle.py` | Inlines `src/` and the run's logs into one HTML page. State and events are gzip-compressed and base64-encoded; the browser decompresses them with `DecompressionStream`. |
| `capture.py`, `cdp.py` | Headless capture to PNG or MP4, and a minimal DevTools client. |
| `src/data.js` | Decodes the run and builds the indices: ticks, sounds, effects, and each bee's history. |
| `src/draw_map.js`, `src/draw_live.js` | The fixed world, and the moving things and effects at a fractional tick. |
| `src/panel.js`, `src/input.js`, `src/app.js` | The side panel, pointer input, and playback, controls and capture mode. |
| `fixtures/make_fixture.py` | Writes `fixtures/synthetic-run/`, a small scripted run in the log format used for development and tests. It is a test fixture, not a result. |
| `test_viewer.py` | Smoke tests: bundling, loading from file://, rendering a frame, click selection, and deterministic capture. |

## Tests

```bash
.venv/bin/python -m pytest viewer/test_viewer.py -q
VIEWER_RUNS_ROOT=experiments/results .venv/bin/python -m pytest viewer/test_viewer.py -q   # also loads real runs
```

The browser tests are skipped when the headless shell is not installed. By default they also load up to three real runs found under `experiments/results/`.

## Limits

- One run per page. Comparing conditions side by side means opening two pages.
- The page needs a browser with `DecompressionStream` (Chrome 80+, Firefox 113+, Safari 16.4+).
- A full 2,000-tick run bundles to about 130 KB for scripted bees. AI runs carry more decision text, so their pages will be larger.
