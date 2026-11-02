"""Load and validate the game configuration.

Contract: load_config() never raises for bad user input. Any problem
(missing file, bad JSON, bad value) prints a message to stderr and falls
back to the default value.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("config.json")


# --------------------------------------------------------------------------
# 1. Data model: the ONLY thing the rest of the game sees
# --------------------------------------------------------------------------
# frozen=True: nobody can modify the config at runtime by accident.
# The default for `levels` is a tuple (immutable). A list would be a shared
# mutable default, which dataclasses refuse for good reason.
@dataclass(frozen=True)
class LevelConfig:
    width: int = 20
    height: int = 15


@dataclass(frozen=True)
class Config:
    highscore_filename: str = "highscore.json"
    lives: int = 3
    pacgum: int = 42
    points_per_pacgum: int = 10
    points_per_super_pacgum: int = 50
    points_per_ghost: int = 200
    seed: int = 42
    level_max_time: int = 90
    levels: tuple[LevelConfig, ...] = (LevelConfig(),)


# --------------------------------------------------------------------------
# 2. Validation rules, kept as DATA, not as a pile of if-statements
# --------------------------------------------------------------------------
# key -> (min, max). Adding a key later = adding one line here.
# TODO: review these bounds and justify them in your README.
# (e.g. why is lives max 99? what is the smallest maze you can generate?)
INT_RULES: dict[str, tuple[int, int]] = {
    "lives": (1, 99),
    "pacgum": (1, 10_000),
    "points_per_pacgum": (0, 10_000),
    "points_per_super_pacgum": (0, 10_000),
    "points_per_ghost": (0, 10_000),
    "seed": (0, 2**32 - 1),
    "level_max_time": (1, 3600),
}
LEVEL_SIZE_RULE = (5, 200)  # TODO: minimum maze size your generator can handle


def warn(message: str) -> None:
    """One place for all user-facing hints (easy to test with capsys)."""
    print(f"[config] {message}", file=sys.stderr)


# --------------------------------------------------------------------------
# 3. Step A: comment stripping  (pure function: str -> str)
# --------------------------------------------------------------------------
def strip_comments(text: str) -> str:
    """Drop empty lines and lines starting with # or //."""
    kept = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "//")):
            continue
        kept.append(line)
    return "\n".join(kept)


# --------------------------------------------------------------------------
# 4. Step B: reading and parsing  (all failures -> warning + empty dict)
# --------------------------------------------------------------------------
def read_raw_config(path: Path) -> dict[str, Any]:
    """Return the parsed top-level dict, or {} if anything goes wrong."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        warn(f"can't read '{path}': {e}. Using defaults.")
        return {}

    cleaned = strip_comments(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        warn(f"invalid JSON in '{path}': {e.msg}. Using defaults.")
        return {}

    if not isinstance(data, dict):
        warn(f"'{path}' must contain a JSON objet. Using defaults.")
        return {}

    return data


# ---------------------------------------------------------------------------
# Step C: validators (invalid -> message + default)
# ---------------------------------------------------------------------------
def validated_int(data: dict[str, Any], key: str, default: int,
                  low: int, high: int) -> int:
    """Return data[key] if it is an int in [low, high], else default."""
    if key not in data:
        return default                      # missing: silent default
    value = data[key]
    # bool is a subclass of int in Python, so reject it explicitly
    if isinstance(value, bool) or not isinstance(value, int):
        warn(f"'{key}' must be an integer, got {value!r}. "
             f"Using default {default}.")
        return default
    if not low <= value <= high:
        warn(f"'{key}'={value} is outside [{low}, {high}]."
             f"Using default {default}.")
        return default
    return value


def validated_str(data: dict[str, Any], key: str, default: str) -> str:
    """Return data[key] if it is a non-empty string, else default."""
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        warn(f"'{key}' must be a non-empty string, got {value!r}. "
             f"Using default {default!r}.")
        return default
    return value.strip()


def validated_levels(data: dict[str, Any],
                     default: tuple[LevelConfig, ...]) -> tuple[LevelConfig, ...]: # noqa 
    """Build the tuple of LevelConfig from data["levels"]."""
    raw = data.get("levels")
    if raw is None:
        return default
    if not isinstance(raw, list) or not raw:
        warn("'levels' must be a non-empty list. Using default levels.")
        return default

    base = LevelConfig()
    levels = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            warn(f"levels[{i}] must be an object. Level skipped.")
            continue
        levels.append(LevelConfig(
            width=validated_int(item, "width", base.width, *LEVEL_SIZE_RULE),
            height=validated_int(item, "height", base.height, *LEVEL_SIZE_RULE), # noqa 
        ))
    return tuple(levels) or default         # never return an empty tuple


# ---------------------------------------------------------------------------
# Step D: public entry point
# ---------------------------------------------------------------------------
def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    """Always returns a valid Config, whatever the file contains."""
    defaults = Config()
    data = read_raw_config(Path(path))

    values: dict[str, Any] = {}
    for key, (low, high) in INT_RULES.items():
        values[key] = validated_int(data, key, getattr(defaults, key), low, high) # noqa 

    values["highscore_filename"] = validated_str(
        data, "highscore_filename", defaults.highscore_filename
    )
    values["levels"] = validated_levels(data, defaults.levels)

    # Unknown keys are ignored, but we hint about them (catches typos)
    known = set(INT_RULES) | {"highscore_filename", "levels"}
    for key in sorted(data.keys() - known):
        warn(f"unknown key '{key}' ignored.")

    return Config(**values)


if __name__ == "__main__":
    # Manual smoke test: python -m pacman.config
    print(load_config())
