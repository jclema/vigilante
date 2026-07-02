PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_UVICORN := $(VENV)/bin/uvicorn
RUFF_TARGETS := app scripts tests

.PHONY: setup run test lint format build compile smoke check clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"

run:
	$(VENV_UVICORN) app.main:app --reload

test:
	$(VENV_PYTHON) -m pytest

lint:
	$(VENV_PYTHON) -m ruff check $(RUFF_TARGETS)

format:
	$(VENV_PYTHON) -m ruff format $(RUFF_TARGETS)
	$(VENV_PYTHON) -m ruff check --fix $(RUFF_TARGETS)

build:
	rm -rf build dist
	$(VENV_PYTHON) -m build

compile:
	$(VENV_PYTHON) -m compileall -q app scripts

smoke:
	@set -eu; \
	$(VENV_UVICORN) app.main:app --host 127.0.0.1 --port 8765 >/tmp/vigilante-smoke.log 2>&1 & \
	pid=$$!; \
	trap 'kill $$pid 2>/dev/null || true' EXIT INT TERM; \
	ready=0; \
	for attempt in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -fsS -o /dev/null http://127.0.0.1:8765/login; then ready=1; break; fi; \
		sleep 1; \
	done; \
	test "$$ready" -eq 1

check: lint test build compile

clean:
	rm -rf build dist .pytest_cache .ruff_cache
	find app scripts tests -type d -name __pycache__ -prune -exec rm -rf {} +

