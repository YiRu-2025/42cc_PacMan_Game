"""Adapter around the assigned A-Maze-ing package.

The generator returns a grid of wall bitmasks; this module wraps it so the
rest of the game never imports the third-party package directly and never
has to know about its bit encoding.
"""

from collections import deque
from dataclasses import dataclass
from typing import Final

NORTH: Final[int] = 1
EAST: Final[int] = 2
SOUTH: Final[int] = 4
WEST: Final[int] = 8

SEALED: Final[int] = 15
"""A cell with all four walls up: part of the generator's '42' pattern."""

DIRECTIONS: Final[tuple[tuple[int, int, int], ...]] = (
    (0, -1, NORTH),
    (1, 0, EAST),
    (0, 1, SOUTH),
    (-1, 0, WEST),
)

Cell = tuple[int, int]


class MazeError(Exception):
    """Raised when the external generator cannot produce a usable maze."""


@dataclass(frozen=True)
class Grid:
    """An immutable maze: wall bitmasks plus the set of walkable cells."""

    width: int
    height: int
    walkable: frozenset[Cell]

    def is_open(self, x: int, y: int, direction: int) -> bool:
        """Return True if a mover can leave ``(x, y)`` in ``direction``."""

        if not self.contains(x, y):
            return False
        if self.cells[y][x] & direction:
            return False
        for dx, dy, code in DIRECTIONS:
            if code == direction:
                return (x + dx, y + dy) in self.walkable
        return False

    def neighbours(self, x: int, y: int) -> list[Cell]:
        """Return every walkable cell directly reachable from ``(x, y)``."""
        result: list[Cell] = []
        for dx, dy, code in DIRECTIONS:
            if self.is_open(x, y, code):
                result.append((x + dx, y + dy))
        return result

    def contains(self, x: int, y: int) -> bool:
        """Return True if ``(x, y)`` lies inside the grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def nearest_walkable(self, x: int, y: int) -> Cell:
        """Return the walkable cell closest to ``(x, y)``.

        The geometric centre and the four corners can fall inside the
        generator's sealed '42' pattern, so spawn points are snapped to the
        nearest cell a mover can actually occupy.

        """
        if not self.walkable:
            raise MazeError("maze has no walkable cells")
        if (x, y) in self.walkable:
            return (x, y)
        return min(
            self.walkable,
            key=lambda c: (c[0] - x) ** 2 + (c[1] - y) ** 2,
        )

    def corners(self) -> list[Cell]:
        """Return the four corner cells, snapped to walkable ones."""
        raw = [
            (0, 0),
            (self.width - 1, 0),
            (0, self.height - 1),
            (self.width - 1, self.height - 1),
        ]
        return [self.nearest_walkable(x, y) for x, y in raw]

    def centre(self) -> Cell:
        """Return the walkable cell closest to the middle of the maze."""
        return self.nearest_walkable(self.width // 2, self.height // 2)


def _flood(
    cells: tuple[tuple[int, ...], ...], width: int, height: int, start: Cell
) -> frozenset[Cell]:
    """Breadth-first search over open walls from ``start``."""
    seen: set[Cell] = {start}
    queue: deque[Cell] = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy, code in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < width
                and 0 <= ny < height
                and not cells[y][x] & code
                and (nx, ny) not in seen
            ):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return frozenset(seen)


class MazeLoader:
    """Builds Grid objects from the assigned A-Maze-ing package."""

    def __init__(self, width: int, height: int) -> None:
        """Create a loader for mazes of a fixed size."""
        if width < 3 or height < 3:
            raise MazeError(f"maze size {width}x{height} is too small")
        self._width = width
        self._height = height
        try:
            from mazegenerator import MazeGenerator
        except ImportError as exc:
            raise MazeError(
                "the mazegenerator package is not installed; " "run 'make install'"  # noqa
            ) from exc
        try:
            self._generator = MazeGenerator(
                size=(width, height),
                perfect=False,
                seed=1,
            )
        except Exception as exc:
            raise MazeError(f"maze generator failed to start: {exc}") from exc

    def generate(self, seed: int = 0) -> Grid:
        """Generate one maze."""
        try:
            self._generator.generate(max(seed, 0))
            raw = self._generator.maze
            entry = self._generator.maze_entry
        except Exception as exc:
            raise MazeError(f"maze generation failed: {exc}") from exc

        if (
            not raw
            or len(raw) != self._height
            or any(len(row) != self._width for row in raw)
        ):
            raise MazeError("maze generator returned a malformed grid")

        cells = tuple(tuple(int(v) & 0xF for v in row) for row in raw)
        walkable = _flood(cells, self._width, self._height, entry)
        if len(walkable) < 4:
            raise MazeError("generated maze has no usable corridors")
        return Grid(self._width, self._height, cells, walkable)
