# History rewrite, 2026-11-06

**What happened.** One build session loaded a personal writing-style skill from the developer's own setup. The skill's instructions reached that session's exported trace, and earlier exports also held file paths from outside this repository. Both are private configuration that has nothing to do with this project. The exporter was fixed so this cannot recur: it redacts harness-generated messages and paths outside the repository, and project settings, a pre-commit scan and `make check` now block any recurrence. This section records how the history itself was cleaned.

**What was changed.** Only the exported trace files (`agent_traces/sessions/**.jsonl` and `agent_traces/events/**.jsonl`), in every commit, were re-redacted with the exporter's current rules (`[REDACTED:harness-meta]`, `[REDACTED:path-outside-repo]`). The tool was git-filter-repo with a file-info callback. No commit was removed, squashed, reordered or re-dated. Commit messages are unchanged, apart from git-filter-repo updating commit ids quoted inside them.

**Two passes.** The first pass handled skill instructions and outside paths. A stricter scan added afterwards (tools/private_scan.py) then found a directory listing that named other projects' scratch folders, so a second pass also applied the private-terms list and redacted those folder names.

**Checks, run on the rewritten history before pushing.** 83 commits before and after. The tree of the newest commit is byte-identical to the one before the rewrite. No commit adds or removes any of the leaked strings, and `tools/private_scan.py` finds nothing in any version of any trace file in history (`make check` runs this on every check).

**Where.** The final cleaned history was pushed to a fresh project, so the earlier objects never reach a public copy. Two earlier private projects remain: the original, and one that received the first pass. Archiving or deleting them needs owner rights the developer does not hold, so a group owner should delete both.

**Commit ids.** Rewriting gives every commit after the first changed one a new id. Docs in this repository now cite the new ids. Run records (`experiments/results/**/record.json`, `git_commit`) and exported traces keep the ids that were true when they were written. Use this table to translate them.

**Correction (2026-11-06, about 08:20 PT).** The first version of this table, and the commit ids written into the docs after the second pass, gave first-pass ids that the second pass then replaced, so they did not resolve. An independent check against a fresh clone found this. The table below maps each original id to its final id, pairing commits by their position in the history and confirming every pair against author and commit dates (77 of 83 matched uniquely by date; all 77 agree with the positional pairing). Doc references were corrected the same way.

| Before | After |
|---|---|
| 7b366c3 | f31e176 |
| c82f57b | 75d2b17 |
| 1abaff8 | 05909c4 |
| 031fb4a | a636587 |
| 28afa08 | 7086be9 |
| c2052a2 | db1db0f |
| 156c703 | 9b07ee1 |
| 4ae7686 | 8a99c4a |
| 81d09ba | 1600600 |
| 5650e7b | b396baf |
| 9cb4e7a | 663d562 |
| 9c2f893 | 1f27f13 |
| b8039ea | 3e79084 |
| 6241115 | c20485f |
| 49cf14b | 2c467e8 |
| 340763e | fce57aa |
| 3e7c0b2 | e51ec8c |
| 1f0ff06 | 99c8c57 |
| fb8bcfa | 2dd1799 |
| e9ba8ca | 913e3a1 |
| f3ae5de | 0cec37d |
| 4e0759e | 22a8f12 |
| 2d4daf7 | cdeb49f |
| 4f2956c | 2af735b |
| 44fe346 | cc73404 |
| 5821f69 | dd50b2b |
| d259227 | fcfbb4e |
| 7fdfa10 | 4ad9213 |
| b27db86 | 3f85e5b |
| 4ebf520 | cf328d9 |
| cdbd280 | 155f669 |
| b1e7bb3 | 97ff46a |
| 2b99282 | 0056c1a |
| 1cb3a0f | 4132e0c |
| e2a2173 | e76039a |
| 7971a65 | 8499bd0 |
| 40b0b1c | a2b2c61 |
| 98e8aff | 7678cae |
| bef63ee | cd52fc5 |
| 83aba26 | e28baf2 |
| 829fc27 | 7157cff |
| 5546296 | c39a419 |
| a431e00 | 23bd5ea |
| 77b9422 | 75a0b32 |
| bc6073f | 9407b04 |
| 379d4ee | 3f370ae |
| 9663aea | 2d07df7 |
| d3fa660 | 4d59b6f |
| 2041632 | 265f6be |
| efe56c4 | ec01c3b |
| 4081692 | 1a8a766 |
| 0b7885a | 3e5d4e3 |
| 8c6dda3 | 9cdc81f |
| ecff943 | ca93bc5 |
