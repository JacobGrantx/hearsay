# Submission package (brief section 13)

Draft, written by the phase 4 build session (Claude Code) for Jacob Schoenberg to check and send through the organisers' form. Items marked "waiting on Jacob" cannot be filled by an agent.

1. **Public repository URL.** Waiting on Jacob. The project is `private-group/digital-life` on a self-managed GitLab and is private while building. At submission it moves to a public namespace Jacob chooses, and `make check` must show the anonymous access check passing. The brief asks for a GitHub URL; whether the organisers accept GitLab is Jacob's question to settle (DECISIONS.md).
2. **Project name.** Waiting on Jacob. Working title: "Bee colony (working title)".
3. **Short project description.** A colony of language-model bees in a maze must find seasonal bloom while hornets that evolve by natural selection hunt them. The bees are told nothing about bees, flowers, hornets or seasons, only that their life falls and that something is worth finding; they keep their own memories and can talk only inside the hive. We test, against pre-registered controls, whether the colony learns, whether knowledge outlives the bees that found it, whether the hornets adapt to the colony, and whether two meaningless sounds come to mean something.
4. **Team members.** Jacob Schoenberg (solo entry). Development assisted by Claude Code; see AI_DISCLOSURE.md.
5. **Demonstration link.** Video to come (made from a fresh clone and real runs, linked from the README's Demonstration section). Until then: the README still, and `make demo`, which runs a small world and replays a recorded AI run offline.
6. **Additional infrastructure or execution requirements.**
   - Python 3.11 or later, `make setup` (pinned dependencies in requirements.txt). No GPU.
   - No API key is needed to reproduce the results: every cited AI run replays offline from the recorded responses in `experiments/llm_cache/` with `LLM_MODE=replay` (`make replay RUN=<seed dir>`).
   - New live AI runs need `ANTHROPIC_API_KEY` in `.env` (see `.env.example`) and cost about $0.37 per 2-year run with Claude Haiku 5.5, taking 15 to 25 minutes each.
