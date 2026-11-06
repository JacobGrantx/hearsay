PY := .venv/bin/python
DEMO_AI_RUN ?= experiments/results/full/20261106T101558Z/seed-0

.PHONY: setup test smoke demo replay traces check analysis

setup:            ## create .venv, install pinned deps, enable the secret-scan pre-commit hook
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
	git config core.hooksPath tools/githooks

test:             ## run the test suite
	$(PY) -m pytest -q

smoke:            ## prove the experiment pipeline works end to end
	$(PY) experiments/run.py experiments/configurations/smoke.toml

demo:             ## the reproducible small-scale demonstration judges can run (no key needed)
	$(PY) experiments/run.py experiments/configurations/demo_small.toml
	$(PY) experiments/replay_check.py $(DEMO_AI_RUN)

replay:           ## replay a recorded AI run offline and check it is identical: make replay RUN=<seed dir>
	$(PY) experiments/replay_check.py $(RUN)

traces:           ## re-export every Claude Code session for this repo into agent_traces/
	python3 tools/export_traces.py --all

check:            ## presubmit check against the brief
	$(PY) tools/presubmit.py

analysis:         ## recompute every pre-registered measure and the figures from the run directories
	$(PY) experiments/analysis/main_results.py
	$(PY) experiments/analysis/figures.py
