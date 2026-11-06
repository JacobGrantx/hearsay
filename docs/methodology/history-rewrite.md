# History rewrite, 2026-11-06

**What happened.** One build session loaded a personal writing-style skill from the developer's own setup. The skill's instructions reached that session's exported trace, and earlier exports also held file paths from outside this repository. Both are private configuration that has nothing to do with this project. The exporter was fixed so this cannot recur: it redacts harness-generated messages and paths outside the repository, and project settings, a pre-commit scan and `make check` now block any recurrence. This section records how the history itself was cleaned.

**What was changed.** Only the exported trace files (`agent_traces/sessions/**.jsonl` and `agent_traces/events/**.jsonl`), in every commit, were re-redacted with the exporter's current rules (`[REDACTED:harness-meta]`, `[REDACTED:path-outside-repo]`). The tool was git-filter-repo with a file-info callback. No commit was removed, squashed, reordered or re-dated. Commit messages are unchanged, apart from git-filter-repo updating commit ids quoted inside them.

**Two passes.** The first pass handled skill instructions and outside paths. A stricter scan added afterwards (tools/private_scan.py) then found a directory listing that named other projects' scratch folders, so a second pass also applied the private-terms list and redacted those folder names.

**Checks, run on the rewritten history before pushing.** 83 commits before and after. The tree of the newest commit is byte-identical to the one before the rewrite. No commit adds or removes any of the leaked strings, and `tools/private_scan.py` finds nothing in any version of any trace file in history (`make check` runs this on every check).

**Where.** The final cleaned history was pushed to a fresh project, so the earlier objects never reach a public copy. Two earlier private projects remain: the original, and one that received the first pass. Archiving or deleting them needs owner rights the developer does not hold, so a group owner should delete both.

**Commit ids.** Rewriting gives every commit after the first changed one a new id. Docs in this repository now cite the new ids. Run records (`experiments/results/**/record.json`, `git_commit`) and exported traces keep the ids that were true when they were written. Use this table to translate them.

| Before | After |
|---|---|
| 031fb4a | 6490e17 |
| 0b7885a | 81089a6 |
| 156c703 | e386772 |
| 1abaff8 | 5c8b22f |
| 1cb3a0f | 61c072e |
| 1f0ff06 | 9f61248 |
| 2041632 | c556f89 |
| 28afa08 | 7c708e6 |
| 2b99282 | a22b780 |
| 2d4daf7 | c05d862 |
| 340763e | f33684a |
| 379d4ee | 923ea91 |
| 3e7c0b2 | a3f9f53 |
| 4081692 | e969de7 |
| 40b0b1c | bc784b2 |
| 44fe346 | 8e02908 |
| 49cf14b | 68eb5c4 |
| 4ae7686 | 511e967 |
| 4e0759e | 3dd5dfc |
| 4ebf520 | f16a1b0 |
| 4f2956c | 4a28be4 |
| 5546296 | 21886f7 |
| 5650e7b | d9535af |
| 5821f69 | 7913989 |
| 6241115 | b0e7a59 |
| 77b9422 | c172ecc |
| 7971a65 | 7467d15 |
| 7b366c3 | 0679d0e |
| 7fdfa10 | 4aacffc |
| 81d09ba | 3ee7ce4 |
| 829fc27 | f6edb31 |
| 83aba26 | fa0c2f6 |
| 8c6dda3 | 797dd11 |
| 9663aea | 0fdd622 |
| 98e8aff | 0e715a4 |
| 9c2f893 | 8e40ede |
| 9cb4e7a | 05ce2f3 |
| a431e00 | 4d52a37 |
| b1e7bb3 | 6748f58 |
| b27db86 | c230925 |
| b8039ea | c8b9884 |
| bc6073f | 83e85d8 |
| bef63ee | bd8cb66 |
| c2052a2 | 83a9b8c |
| c82f57b | cabfde0 |
| cdbd280 | d157697 |
| d259227 | 6b9f1b7 |
| d3fa660 | 568ddde |
| e2a2173 | 477919b |
| e9ba8ca | a4474f0 |
| ecff943 | cd75215 |
| efe56c4 | c71ff0c |
| f3ae5de | 9c8dedc |
| fb8bcfa | 3346361 |
