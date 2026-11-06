# Round 2, amendment 1 (made during the runs, before any round 2 result was read)

**When:** 2026-11-06T17:08:39Z (UTC).

**What:** four runs were stopped by hand: A_full seeds 1 and 2, and N_full seeds 1 and 2 (process ids 708357, 708361, 708359 and 708363). The other 12 AI runs continue under the pre-registered stop rule.

**Why:** a rate limit on the model endpoint, shared by all 16 runs, paced them so that most would complete only about one simulated year by the 10:05 PT stop. Stopping 4 runs gives the remaining 12 about a third more throughput. That should let B_full and B_no_talk complete two years, which H8 (seasonal memory) needs. The trade-off was put to Jacob Schoenberg, and he decided: "yes/cut".

**What it changes:**
- H6 (labels and prior) and H11 (knowing the rule) now have 1 seed in N_full and A_full, so they are reported as single-seed observations, not hypothesis tests.
- H10, H7 and H8 keep 5 paired seeds per B arm.
- The stopped runs' partial logs are kept and reported as stopped by this amendment. They are excluded from every hypothesis test.

**Why this is not outcome-driven:** the decision was made on throughput (the pace from the progress tool and the run logs). No round 2 measure had been computed or read. The original pre-registration allowed cutting these seeds only if spend ran high; spend was low (about $1.5 at the ten-minute check), so this is a deviation, recorded here and in DECISIONS.md.
