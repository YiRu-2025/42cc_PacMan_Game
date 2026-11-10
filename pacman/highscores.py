"""Persistent top-ten highscore table."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pacman.constants import HIGHSCORE_LIMIT, NAME_CHARSET, NAME_MAX_LENGTH

PLACEHOLDER_NAME = "PLAYER"


def warn(message: str) -> None:
    """Report a recoverable problem to the player."""
    print(f"[highscores] {message}", file=sys.stderr)


def sanitize_name(raw: str) -> str:
    """Reduce arbitrary input to an acceptable player name.

    Characters outside the whitelist are dropped rather than rejected, so a
    player who types an accent still gets a name. Surrounding spaces go, runs
    of spaces collapse, and the result is cut to ``NAME_MAX_LENGTH``. Input
    that leaves nothing usable becomes ``PLAYER``.

    """
    kept = "".join(c for c in raw if c in NAME_CHARSET)
    collapsed = " ".join(kept.split())
    trimmed = collapsed[:NAME_MAX_LENGTH].strip()
    return trimmed or PLACEHOLDER_NAME


def is_name_complete(raw: str) -> bool:
    """Return True if ``raw`` is already a valid name, needing no repair.

    Used by the name-entry scene to decide whether to accept a keystroke, so
    that the field never shows a character the table would later drop.

    """
    return (
        0 < len(raw) <= NAME_MAX_LENGTH
        and all(c in NAME_CHARSET for c in raw)
        and raw == raw.strip()
    )


@dataclass(frozen=True)
class Entry:
    """One row of the table.

    Attributes:
        name: An already-sanitized player name.
        score: A non-negative score.
    """

    name: str
    score: int


def _valid_score(value: Any) -> int | None:
    """Return ``value`` as a non-negative int, or None if it is not one.

    ``bool`` is a subclass of ``int`` in Python, so ``True`` would otherwise
    pass as the score 1.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


class Highscores:
    """The top-ten table, backed by one JSON file."""

    def __init__(self, path: str | Path) -> None:
        """Create a table bound to a file, without reading it yet."""
        self._path = Path(path)
        self._entries: list[Entry] = []

    @property
    def path(self) -> Path:
        """The file this table reads and writes."""
        return self._path

    @property
    def entries(self) -> tuple[Entry, ...]:
        """The table, best score first, at most ``HIGHSCORE_LIMIT`` long."""
        return tuple(self._entries)

    def best(self) -> int:
        """Return the highest score on the table, or 0 if it is empty."""
        return self._entries[0].score if self._entries else 0

    def qualifies(self, score: int) -> bool:
        """Return True if ``score`` would earn a place on the table.

        A table with room always accepts; a full one accepts anything that
        beats its last row. Ties do not displace an existing entry.

        """
        if score < 0:
            return False
        if len(self._entries) < HIGHSCORE_LIMIT:
            return True
        return score > self._entries[-1].score

    def rank_of(self, score: int) -> int:
        """Return the 1-based position ``score`` would take."""
        if not self.qualifies(score):
            return 0
        position = sum(1 for e in self._entries if e.score >= score)
        return position + 1

    def add(self, name: str, score: int) -> int:
        """Insert a result and trim the table to the top ten.

        Equal scores keep their arrival order, so an earlier player is not
        pushed down by a later tie.

        """
        clean_score = max(0, score)
        if not self.qualifies(clean_score):
            return 0
        entry = Entry(sanitize_name(name), clean_score)
        position = sum(1 for e in self._entries if e.score >= clean_score)
        self._entries.insert(position, entry)
        del self._entries[HIGHSCORE_LIMIT:]
        return position + 1

    def load(self) -> None:
        """Read the table, falling back to an empty one on any problem.

        Handled: the file is absent, unreadable, not UTF-8, not JSON, not a
        list, holds rows that are not objects, rows missing a key, rows with
        a name or score of the wrong type, and more rows than the limit.

        """
        self._entries = []
        if not self._path.exists():
            return
        try:
            text = self._path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            warn(f"cannot read '{self._path}': {exc}. Starting empty.")
            return
        if not text.strip():
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            warn(f"'{self._path}' is not valid JSON: {exc.msg}. " f"Starting empty.")
            return
        if not isinstance(data, list):
            warn(f"'{self._path}' must contain a JSON array. Starting empty.")
            return

        kept: list[Entry] = []
        dropped = 0
        for row in data:
            if not isinstance(row, dict):
                dropped += 1
                continue
            score = _valid_score(row.get("score"))
            name = row.get("name")
            if score is None or not isinstance(name, str):
                dropped += 1
                continue
            kept.append(Entry(sanitize_name(name), score))
        if dropped:
            warn(
                f"ignored {dropped} unusable entr"
                f"{'y' if dropped == 1 else 'ies'} in '{self._path}'."
            )

        kept.sort(key=lambda e: -e.score)
        self._entries = kept[:HIGHSCORE_LIMIT]

    def save(self) -> bool:
        """Write the table, reporting failure instead of raising.

        The file is written through a temporary sibling and then moved into
        place, so an interrupted save cannot leave a half-written table.


        """
        payload = [{"name": e.name, "score": e.score} for e in self._entries]
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            parent = self._path.parent
            if str(parent):
                parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=True)
                handle.write("\n")
            temporary.replace(self._path)
        except OSError as exc:
            warn(
                f"cannot save to '{self._path}': {exc}. " f"This run's scores are lost."
            )
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        return True
