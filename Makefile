PYTHON   := python3
ENTRY    := pac-man.py
CONFIG   ?= config.json
SOURCES  := pacman tests pac-man.py
NAME     := pac-man
PLATFORM := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCHIVE  := $(NAME)-$(PLATFORM).zip
ITCH     ?= https://yiru-2025.itch.io/pacman
CHANNEL  ?= $(PLATFORM)
VENDOR   := $(lastword $(sort $(wildcard vendor/mazegenerator-*.whl)))

.PHONY: all install run debug clean lint lint-strict test test-v cov check \
        package package-check itch itch-check re help

all: help

install:
	@test -n "$(VENDOR)" || { \
		echo "error: no mazegenerator wheel found in vendor/" >&2; \
		exit 1; }
	$(PYTHON) -m pip install --prefer-binary -r requirements.txt
	$(PYTHON) -m pip install --force-reinstall $(VENDOR)

run:
	$(PYTHON) $(ENTRY) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(ENTRY) $(CONFIG)

lint:
	$(PYTHON) -m flake8 $(SOURCES)
	$(PYTHON) -m mypy --explicit-package-bases --warn-return-any \
		--warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs pacman pac-man.py

lint-strict:
	$(PYTHON) -m flake8 $(SOURCES)
	$(PYTHON) -m mypy --strict --explicit-package-bases pacman pac-man.py

test:
	$(PYTHON) -m pytest -q

test-v:
	$(PYTHON) -m pytest -v

cov:
	$(PYTHON) -m pytest --cov=pacman --cov-report=term-missing

check: lint-strict test

package:
	rm -rf build dist
	$(PYTHON) -m PyInstaller --noconfirm --clean pacman.spec
	@test -f dist/$(NAME) || { echo "error: dist/$(NAME) was not built" >&2; exit 1; }
	cd dist && $(PYTHON) -m zipfile -c $(ARCHIVE) $(NAME)
	@echo "built dist/$(ARCHIVE)"

package-check:
	@test -f dist/$(NAME) || { echo "error: run 'make package' first" >&2; exit 1; }
	@dir=$$(mktemp -d) && cp dist/$(NAME) $$dir/ \
		&& echo "running from $$dir (no assets/, no config.json)" \
		&& cd $$dir && ./$(NAME)

itch-check:
	@test -n "$(ITCH)" || { echo "usage: make itch ITCH=user/game" >&2; exit 1; }
	@command -v butler >/dev/null || { echo "error: butler not installed" >&2; exit 1; }

itch: itch-check package
	butler push dist/$(ARCHIVE) $(ITCH):$(CHANNEL)

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache build dist
	find . -type f -name '*.py[cod]' -delete

re: clean all

help:
	@echo "make install        dependencies (prebuilt wheels preferred) + vendored maze wheel"
	@echo "make run            run the game      (override: make run CONFIG=x.json)"
	@echo "make debug          run the game under pdb"
	@echo "make lint           flake8 + mypy"
	@echo "make lint-strict    flake8 + mypy --strict"
	@echo "make test           run all unit tests"
	@echo "make cov            tests with coverage"
	@echo "make check          lint-strict + test"
	@echo "make package        build dist/pac-man and the zip"
	@echo "make package-check  run the build from an empty directory"
	@echo "make itch ITCH=u/g  push the zip with butler"
	@echo "make clean          remove caches and build output"