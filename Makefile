NAME     := pac-man
MAIN	 := pac-man.py
CONFIG   ?= config.json
PYTHON   := python3
PLATFORM := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCHIVE  := $(NAME)-$(PLATFORM).zip
ITCH     ?=
CHANNEL  ?= $(PLATFORM)
SOURCES := pacman tests pac-man.py
# one wheel, newest name wins, instead of passing a whole glob to pip
VENDOR := $(lastword $(sort $(wildcard vendor/mazegenerator-*.whl)))

.PHONY: all install run debug clean lint lint-strict test re help package package-check itch clean-build

all: help

install:
	@test -n "$(VENDOR)" || { echo "error: no mazegenerator wheel in vendor/" >&2; exit 1; }
	$(PYTHON) -m pip install --prefer-binary -r requirements.txt
	$(PYTHON) -m pip install --force-reinstall $(VENDOR)

run:
	${PYTHON} ${MAIN} ${CONFIG}

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

clean-build:
	rm -rf build dist

# Build dist/pac-man and dist/pac-man-<platform>.zip
package: clean-build
	$(PYTHON) -m PyInstaller --noconfirm --clean pacman.spec
	@test -f dist/$(NAME) || { echo "error: dist/$(NAME) was not built" >&2; exit 1; }
	cd dist && $(PYTHON) -m zipfile -c $(ARCHIVE) $(NAME)
	@echo "built dist/$(ARCHIVE)"

# Run the build from an empty directory, so nothing is found by accident
package-check:
	@rm -rf /tmp/pacman-check && mkdir /tmp/pacman-check
	cp dist/$(NAME) /tmp/pacman-check/
	cd /tmp/pacman-check && ./$(NAME)

# make itch ITCH=user/game      (needs butler; upload, then set the page to
# draft / restricted in the itch.io dashboard)
itch: package
	@test -n "$(ITCH)" || { echo "usage: make itch ITCH=user/game" >&2; exit 1; }
	butler push dist/$(ARCHIVE) $(ITCH):$(CHANNEL)

help:
	@echo "make install      install dependencies and the vendored maze wheel"
	@echo "make run          run the game      (override: make run CONFIG=x.json)"
	@echo "make debug        run the game under pdb"
	@echo "make lint         flake8 + mypy"
	@echo "make lint-strict  flake8 + mypy --strict"
	@echo "make test         run the unit tests"
	@echo "make clean        remove caches and build output"