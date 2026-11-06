# Feasibility measurements, 2026-11-05

Measured before choosing the idea, to size the system. Prompts were a realistic agent turn: system rules (~150 tokens), a 5x5 view, 10 recalled memories and 3 heard messages (~505 input tokens in total), returning one action. Models were reached through Microsoft Foundry. Costs use the list prices in `src/digital_life/llm.py`. Raw probe output is not kept; these are the printed results.

| Test | Result |
|---|---|
| Free-text JSON actions (no schema) | Haiku 5.5: 1 of 2 single calls valid, 59 of 60 in parallel. Sonnet 5.5: 0 of 2. Opus 5.5: 2 of 2. Not reliable enough. |
| Structured outputs (`schema=`) | Haiku 5.5: 80 of 80 valid. Sonnet 5.5: 2 of 2 valid. Adopted for every agent action. |
| Haiku 5.5, thinking on, effort low, 40 agents in parallel | 4.3 s for the whole batch, 2.5 s average per call, about 339 output tokens, $0.00025 per call |
| Haiku 5.5, thinking off, effort low, 40 agents in parallel | 1.6 s for the whole batch, 1.1 s average per call, about 60 output tokens, $0.00011 per call |
| Sonnet 5.5, structured | 5.4 s per call, $0.00404 per call |
| Opus 5.5, free text | 3.5 s per call, $0.00622 per call |
| Rate limits | No errors at 40 concurrent calls |
| Memory recall (BM25, rank-bm25), 10 agents with 500 memories each, top 5 | 27 ms per tick, rebuilding the index every tick |
| Frame rendering (Pillow), 150 frames at 1280x720, then ffmpeg H.264 | 4.8 s to render, 2.0 s to encode |
| Browser viewer captured headless (Playwright chrome-headless-shell) | Works. Snap Chromium cannot read /tmp, so use the headless shell with paths on /dev/shm. |

## Sizing that follows

- With thinking off, 10 agents for 300 ticks is about 3,000 calls: roughly 8 minutes and $0.33 per run. With thinking on: roughly 20 minutes and $0.75.
- Several runs can go in parallel (40 concurrent calls tested), so 3 seeds x 4 conditions is about 12 runs: around $4 to $9 on Haiku, within the $100 cap with wide margin.
- Running the agents on Opus 5.5 would cost about 56 times as much as Haiku with thinking off. Keep Opus for low-volume roles (reflection, analysis) or a comparison arm.

## Machine limits (shared VM)

- 4 CPUs, 15 GB RAM.
- The root disk was full (about 330 to 490 MB free). Write frames and scratch files to /dev/shm (about 1.4 GB free), keep committed results small, and delete intermediate frames once the video is encoded.
