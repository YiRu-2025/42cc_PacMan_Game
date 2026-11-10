PYTHON  := python3
ENTRY   := pac-man.py
CONFIG  ?= config.json
SOURCES := pacman tests pac-man.py
VENDOR  := $(wildcard vendor/mazegenerator-*.whl)

.PHONY: all install run debug clean lint lint-strict test re help

all: help

install:
	@test -n "$(VENDOR)" || { \
		echo "error: no mazegenerator wheel found in vendor/" >&2; \
		exit 1; }
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install --force-reinstall $(VENDOR)

run:
	$(PYTHON) $(ENTRY) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(ENTRY) $(CONFIG)

lint:
	$(PYTHON) -m flake8 $(SOURCES)
	$(PYTHON) -m mypy --strict --explicit-package-bases pacman pac-man.py

lint-strict: lint

test:
	$(PYTHON) -m pytest -q

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache build dist
	find . -type f -name '*.py[cod]' -delete

re: clean all

help:
	@echo "make install      install dependencies and the vendored maze wheel"
	@echo "make run          run the game      (override: make run CONFIG=x.json)"
	@echo "make debug        run the game under pdb"
	@echo "make lint         flake8 + mypy"
	@echo "make lint-strict  flake8 + mypy --strict"
	@echo "make test         run the unit tests"
	@echo "make clean        remove caches and build output"
