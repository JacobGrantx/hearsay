# History rewrite, 2026-11-06

**What happened.** One build session loaded a personal writing-style skill from the developer's own setup. The skill's instructions reached that session's exported trace, and earlier exports also held file paths from outside this repository. Both are private configuration that has nothing to do with this project. The exporter was fixed so this cannot recur: it redacts harness-generated messages and paths outside the repository, and project settings, a pre-commit scan and `make check` now block any recurrence. This section records how the history itself was cleaned.

**What was changed.** Only the exported trace files (`agent_traces/sessions/**.jsonl` and `agent_traces/events/**.jsonl`), in every commit, were re-redacted with the exporter's current rules (`[REDACTED:harness-meta]`, `[REDACTED:path-outside-repo]`). The tool was git-filter-repo with a file-info callback. No commit was removed, squashed, reordered or re-dated. Commit messages are unchanged, apart from git-filter-repo updating commit ids quoted inside them.

**Two passes.** The first pass handled skill instructions and outside paths. A stricter scan added afterwards (tools/private_scan.py) then found a directory listing that named other projects' scratch folders, so a second pass also applied the private-terms list and redacted those folder names.

**Checks, run on the rewritten history before pushing.** 83 commits before and after. The tree of the newest commit is byte-identical to the one before the rewrite. No commit adds or removes any of the leaked strings, and `tools/private_scan.py` finds nothing in any version of any trace file in history (`make check` runs this on every check).

**Where.** The final cleaned history was pushed to a fresh project, so the earlier objects never reach a public copy. Two earlier private projects remain: the original, and one that received the first pass. Archiving or deleting them needs owner rights the developer does not hold, so a group owner should delete both.

**Commit ids.** Rewriting gives every commit after the first changed one a new id. Docs in this repository now cite the new ids. Run records (`experiments/results/**/record.json`, `git_commit`) and exported traces keep the ids that were true when they were written. Use this table to translate them.

**Correction (2026-11-06, about 08:20 PT).** The first version of this table, and the commit ids written into the docs after the second pass, gave first-pass ids that the second pass then replaced, so they did not resolve. An independent check against a fresh clone found this. The table below maps each original id to its final id, pairing commits by their position in the history and confirming every pair against author and commit dates (77 of 83 matched uniquely by date; all 77 agree with the positional pairing). Doc references were corrected the same way.

## Second rewrite: the publication scrub (2026-11-06, about 11:45 PT)

**Why.** Jacob moved the repository to public GitHub. The history still named the internal GitLab host and group the project was built on, in exported traces, docs and summaries. Earlier renders of the demo video also showed that address on their end card. Jacob's rule is that nothing public names the company's former name or its internal hosts. He chose "Scrub, then publish".

**What changed:**
- **Text, in every file and every commit message:** git-filter-repo `--replace-text` swapped the internal GitLab host for `private-gitlab.example` and the group name for `private-group`.
- **Video:** every earlier render of `demo/recordings/demo.mp4` was removed from history (`--invert-paths`). The final render, whose end card shows the GitHub address, was committed afterwards.
- **What did not change:** no commit was removed, squashed, reordered or re-dated (`--prune-empty never`). The only change to commit messages is that git-filter-repo updated the commit ids quoted inside them.

**Checks, run before pushing:**
- 144 commits before and after.
- Pairing old and new commits by position, every pair has the same author date and the same title once quoted ids are masked.
- No commit adds or removes the company's former name, in any letter case.
- No `demo.mp4` blob is left from before the scrub.
- `tools/private_scan.py` finds nothing in any trace file anywhere in history.

**Commit ids.** The table below maps each original id (from before the first rewrite) to its final id after both rewrites. Commits the first rewrite left alone, but which the scrub changed, map through the scrub alone. Docs cite the final ids. Run records (`git_commit`) and exported traces keep the ids that were true when they were written, so translate those through this table and the scrub's position map (old commit n is new commit n, in `git rev-list --reverse` order).

| Before | After |
|---|---|
| 7b366c3 | c8b3f17 |
| c82f57b | c5f6a0f |
| 1abaff8 | 429c78e |
| 031fb4a | ac4f7c5 |
| 28afa08 | a01bb5d |
| c2052a2 | 8da23dd |
| 156c703 | 44ab897 |
| 4ae7686 | 1069767 |
| 81d09ba | fb69a55 |
| 5650e7b | 6e8eb37 |
| 9cb4e7a | ec521ca |
| 9c2f893 | 36e7be0 |
| b8039ea | 7479bb1 |
| 6241115 | 3bf4460 |
| 49cf14b | 93e682f |
| 340763e | 105b2ba |
| 3e7c0b2 | d96ef3c |
| 1f0ff06 | bb87679 |
| fb8bcfa | 118889e |
| e9ba8ca | 0da2fb8 |
| f3ae5de | c08f141 |
| 4e0759e | 94f8f58 |
| 2d4daf7 | 47ad0ee |
| 4f2956c | 62d7d1c |
| 44fe346 | 18bc9b8 |
| 5821f69 | 39c0996 |
| d259227 | 5e575ed |
| 7fdfa10 | 7c179c6 |
| b27db86 | 6e49a7e |
| 4ebf520 | 06599d5 |
| cdbd280 | 72fbf8f |
| b1e7bb3 | 56593f9 |
| 2b99282 | 15c2ca1 |
| 1cb3a0f | 25d8f65 |
| e2a2173 | bbe7c2e |
| 7971a65 | 90ebbe9 |
| 40b0b1c | 5cfd87b |
| 98e8aff | df7b319 |
| bef63ee | 799aed0 |
| 83aba26 | f00a681 |
| 829fc27 | 0ab1857 |
| 5546296 | 712e0a9 |
| a431e00 | 29dc364 |
| 77b9422 | fd63717 |
| bc6073f | 5dbf4ca |
| 379d4ee | 42fa410 |
| 9663aea | fac5cdb |
| d3fa660 | 0da290b |
| 2041632 | ab2cdc7 |
| efe56c4 | c06ab0f |
| 4081692 | 5d08e80 |
| 0b7885a | 0979c9a |
| 8c6dda3 | 230b224 |
| ecff943 | f263522 |
