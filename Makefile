.PHONY: install tour quickstart test build
PYTHON ?= python3
NODE ?= node

install:
	$(PYTHON) -m pip install -e .

tour:
	$(PYTHON) -m scopedact tour

quickstart:
	$(PYTHON) examples/quickstart.py

test:
	$(PYTHON) tools/check_repository.py
	$(PYTHON) -W error::ResourceWarning tools/check_sqlite_resources.py
	$(NODE) tests/test_console_actions.cjs

build:
	$(PYTHON) -m build
