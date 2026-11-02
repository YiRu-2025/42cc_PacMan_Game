"""Tests for pacman.level.
python -m pytest tests/level_test.py -v
"""

import pytest

from pacman.level import Level, Pickup, build_level
from pacman.maze_loader_2 import Cell, Grid, MazeLoader

N, E, S, W = 1, 2, 4, 8


def open_grid(width: int, height: int) -> Grid:
    """A maze with no inner walls: every cell walkable, border closed."""
    cells = tuple(
        tuple(
            (N if y == 0 else 0)
            | (S if y == height - 1 else 0)
            | (W if x == 0 else 0)
            | (E if x == width - 1 else 0)
            for x in range(width)
        )
        for y in range(height)
    )
    walkable = frozenset((x, y) for y in range(height) for x in range(width))
    return Grid(width, height, cells, walkable)


@pytest.fixture
def small() -> Level:
    return build_level(open_grid(5, 5))


@pytest.fixture(scope="module")
def real() -> Level:
    return build_level(MazeLoader(21, 15).generate(42))


# ---------- exact values on a hand-built 5x5 grid ----------

def test_players_in_the_middle(small: Level) -> None:
    assert small.player == (2, 2)


def test_supgums_are_the_four_corners(small: Level) -> None:
    assert small.supgums == {(0, 0), (4, 0), (0, 4), (4, 4)}


def test_ghosts_start_beside_each_corner(small: Level) -> None:
    # neighbours are tried in N, E, S, W order, so the result is fixed
    assert small.ghosts == [(1, 0), (4, 1), (0, 3), (4, 3)]


def test_pacgum_count(small: Level) -> None:
    # 25 cells - 4 super - 1 player start
    assert len(small.pacgums) == 20


# ---------- invariants on a real generated maze ----------

def test_four_ghosts_and_four_supgums(real: Level) -> None:
    assert len(real.ghosts) == 4
    assert len(real.supgums) == 4


def test_player_start_is_walkable_and_has_no_pickup(real: Level) -> None:
    assert real.player in real.grid.walkable
    assert real.player not in real.pacgums
    assert real.player not in real.supgums


def test_pickups_only_on_walkable_cells(real: Level) -> None:
    assert real.pacgums <= real.grid.walkable
    assert real.supgums <= real.grid.walkable


def test_no_pickup_inside_the_42_pattern(real: Level) -> None:
    sealed = {
        (x, y)
        for y in range(real.grid.height)
        for x in range(real.grid.width)
        if real.grid.is_sealed(x, y)
    }
    assert sealed, "seed 42 on 21x15 should contain the 42 pattern"
    assert not sealed & (real.pacgums | real.supgums)


def test_pacgums_and_supgums_do_not_overlap(real: Level) -> None:
    assert not real.pacgums & real.supgums


def test_ghosts_are_beside_a_corner(real: Level) -> None:
    for ghost, corner in zip(real.ghosts, real.grid.corners()):
        assert ghost != corner
        assert ghost in real.grid.neighbours(*corner)


def test_spawns_are_distinct(real: Level) -> None:
    assert len(set(real.ghosts)) == 4
    assert real.player not in real.ghosts


# ---------- determinism ----------

def test_same_seed_gives_same_layout() -> None:
    loader = MazeLoader(21, 15)
    a = build_level(loader.generate(42))
    b = build_level(loader.generate(42))
    assert a.player == b.player
    assert a.ghosts == b.ghosts
    assert a.pacgums == b.pacgums
    assert a.supgums == b.supgums


# ---------- eating ----------

def test_eat_pacgum_then_nothing(small: Level) -> None:
    cell: Cell = next(iter(small.pacgums))
    assert small.eat(cell) is Pickup.PACGUM
    assert small.eat(cell) is Pickup.NONE


def test_eat_SUPGUM(small: Level) -> None:
    assert small.eat((0, 0)) is Pickup.SUPGUM
    assert (0, 0) not in small.supgums


def test_eat_empty_cell(small: Level) -> None:
    assert small.eat(small.player) is Pickup.NONE


def test_remain_and_cleared(small: Level) -> None:
    assert small.remain == 24
    assert not small.cleared
    for cell in list(small.pacgums | small.supgums):
        small.eat(cell)
    assert small.remain == 0
    assert small.cleared


# ---------- edge cases ----------

def test_tiny_maze_does_not_crash() -> None:
    # one walkable cell: every corner snaps to it, no free neighbour exists
    grid = Grid(3, 3, tuple((0,) * 3 for _ in range(3)),
                frozenset({(1, 1)}))
    level = build_level(grid)
    assert len(level.ghosts) == 4