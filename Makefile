PY := .venv/bin/python

.PHONY: setup test smoke demo traces check

setup:            ## create .venv, install pinned deps, enable the secret-scan pre-commit hook
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
	git config core.hooksPath tools/githooks

test:             ## run the test suite
	$(PY) -m pytest -q

smoke:            ## prove the experiment pipeline works end to end
	$(PY) experiments/run.py experiments/configurations/smoke.toml

demo:             ## the reproducible small-scale demonstration judges can run
	@echo "TODO: point this at the real demo config once the system exists"; exit 1

traces:           ## re-export every Claude Code session for this repo into agent_traces/
	python3 tools/export_traces.py --all

check:            ## presubmit check against the brief
	$(PY) tools/presubmit.py
