PY := ./.venv/bin/python

.PHONY: install run check test lint autostart no-autostart

install:
	./install.sh

run:
	./run.sh

check:
	$(PY) -m sotto check

test:
	./.venv/bin/pip install -q -r requirements-dev.txt
	$(PY) -m pytest tests/ -v

lint:
	./.venv/bin/pip install -q ruff
	./.venv/bin/ruff check sotto/ tests/

autostart:
	$(PY) -m sotto install-autostart

no-autostart:
	$(PY) -m sotto uninstall-autostart
