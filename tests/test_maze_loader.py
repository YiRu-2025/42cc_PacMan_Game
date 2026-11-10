"""Tests for pacman.maze_loader.

Most tests use a hand-built maze and a fake ``mazegenerator`` module, so they
run without the real package and are fully deterministic. The last section
runs against the real generator and is skipped if it is not installed.

Run from the project root:  python -m pytest tests/ -v
"""

import dataclasses
import sys
import types

import pytest

from pacman.constants import WALL_ORDER, Direction
from pacman.maze_loader import (
    SEALED,
    WALL_BIT,
    Cell,
    Grid,
    MazeError,
    MazeLoader,
    _flood,
)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

# 3x3 maze, '#' is a sealed cell (like the generator's '42' pattern):
#
#   (0,0)-(1,0)-(2,0)
#     |
#   (0,1)  #   (2,1)
#     |           |
#   (0,2)-(1,2)-(2,2)
#
# (2,0) and (2,1) are NOT connected, so the walkable ring is open.
PASSAGES: list[tuple[Cell, Cell]] = [
    ((0, 0), (1, 0)),
    ((1, 0), (2, 0)),
    ((0, 0), (0, 1)),
    ((0, 1), (0, 2)),
    ((0, 2), (1, 2)),
    ((1, 2), (2, 2)),
    ((2, 2), (2, 1)),
]
EXPECTED_WALKABLE = frozenset(
    {(0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)}
)


def make_cells(
    width: int, height: int, passages: list[tuple[Cell, Cell]]
) -> tuple[tuple[int, ...], ...]:
    """Build a symmetric wall grid: everything sealed, then open passages."""
    rows = [[SEALED] * width for _ in range(height)]
    for (ax, ay), (bx, by) in passages:
        d = Direction((bx - ax, by - ay))
        rows[ay][ax] &= ~WALL_BIT[d]
        rows[by][bx] &= ~WALL_BIT[d.opposite()]
    return tuple(tuple(r) for r in rows)


@pytest.fixture
def cells() -> tuple[tuple[int, ...], ...]:
    return make_cells(3, 3, PASSAGES)


@pytest.fixture
def grid(cells: tuple[tuple[int, ...], ...]) -> Grid:
    return Grid(3, 3, cells, EXPECTED_WALKABLE)


class FakeGenerator:
    """Stand-in for mazegenerator.MazeGenerator."""

    instances: list["FakeGenerator"] = []
    maze: object = None
    maze_entry: object = (0, 0)
    init_error: Exception | None = None
    generate_error: Exception | None = None

    def __init__(self, size: tuple[int, int], perfect: bool, seed: int):
        if type(self).init_error:
            raise type(self).init_error
        self.size = size
        self.perfect = perfect
        self.seed = seed
        self.generate_calls: list[int] = []
        self.maze = type(self).maze
        self.maze_entry = type(self).maze_entry
        type(self).instances.append(self)

    def generate(self, seed: int) -> None:
        if type(self).generate_error:
            raise type(self).generate_error
        self.generate_calls.append(seed)


@pytest.fixture
def fake_generator(monkeypatch: pytest.MonkeyPatch) -> type[FakeGenerator]:
    """Install a fake 'mazegenerator' module returning the 3x3 test maze."""
    FakeGenerator.instances = []
    FakeGenerator.init_error = None
    FakeGenerator.generate_error = None
    FakeGenerator.maze = [list(r) for r in make_cells(3, 3, PASSAGES)]
    FakeGenerator.maze_entry = (0, 0)
    module = types.ModuleType("mazegenerator")
    module.MazeGenerator = FakeGenerator  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mazegenerator", module)
    return FakeGenerator


# --------------------------------------------------------------------------
# Wall encoding
# --------------------------------------------------------------------------


def test_wall_bit_covers_every_direction_once() -> None:
    assert set(WALL_BIT) == set(Direction)
    assert sorted(WALL_BIT.values()) == [1, 2, 4, 8]
    assert sum(WALL_BIT.values()) == SEALED


# --------------------------------------------------------------------------
# Grid
# --------------------------------------------------------------------------


def test_grid_is_immutable(grid: Grid) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        grid.width = 99  # type: ignore[misc]


def test_contains(grid: Grid) -> None:
    assert grid.contains(0, 0)
    assert grid.contains(2, 2)
    assert not grid.contains(3, 0)
    assert not grid.contains(0, 3)
    assert not grid.contains(-1, 0)
    assert not grid.contains(0, -1)


def test_is_open_follows_passages(grid: Grid) -> None:
    assert grid.is_open(0, 0, Direction.EAST)
    assert grid.is_open(1, 0, Direction.WEST)  # symmetric
    assert grid.is_open(0, 0, Direction.SOUTH)
    assert not grid.is_open(2, 0, Direction.SOUTH)  # wall between


def test_is_open_blocked_by_outer_border(grid: Grid) -> None:
    assert not grid.is_open(0, 0, Direction.NORTH)
    assert not grid.is_open(0, 0, Direction.WEST)


def test_is_open_out_of_bounds_is_false(grid: Grid) -> None:
    assert not grid.is_open(-1, 0, Direction.EAST)
    assert not grid.is_open(5, 5, Direction.NORTH)


def test_is_open_requires_walkable_target(cells) -> None:
    lonely = Grid(3, 3, cells, frozenset({(0, 0)}))
    # the wall bit is clear, but the target is not walkable
    assert not lonely.is_open(0, 0, Direction.EAST)


def test_neighbours_order_is_north_east_south_west(grid: Grid) -> None:
    assert grid.neighbours(0, 0) == [(1, 0), (0, 1)]
    assert grid.neighbours(1, 0) == [(2, 0), (0, 0)]
    assert grid.neighbours(1, 2) == [(2, 2), (0, 2)]


def test_neighbours_of_dead_end(grid: Grid) -> None:
    assert grid.neighbours(2, 0) == [(1, 0)]


def test_neighbours_never_leave_walkable_set(grid: Grid) -> None:
    for x, y in grid.walkable:
        assert set(grid.neighbours(x, y)) <= grid.walkable


def test_walls_at(grid: Grid) -> None:
    assert grid.walls_at(0, 0) == frozenset({Direction.NORTH, Direction.WEST})
    assert grid.walls_at(1, 1) == frozenset(WALL_ORDER)


def test_walls_at_out_of_bounds_counts_as_walled(grid: Grid) -> None:
    # needs the bounds check suggested in the review
    assert grid.walls_at(-1, 0) == frozenset(WALL_ORDER)
    assert grid.walls_at(9, 9) == frozenset(WALL_ORDER)


def test_is_sealed(grid: Grid) -> None:
    assert grid.is_sealed(1, 1)
    assert not grid.is_sealed(0, 0)


def test_is_sealed_out_of_bounds_is_false(grid: Grid) -> None:
    # needs the bounds check suggested in the review
    assert not grid.is_sealed(-1, -1)
    assert not grid.is_sealed(9, 9)


def test_all_walls_symmetric(grid: Grid) -> None:
    for y in range(grid.height):
        for x in range(grid.width):
            for d in WALL_ORDER:
                nx, ny = x + d.dx, y + d.dy
                if grid.contains(nx, ny):
                    assert (d in grid.walls_at(x, y)) == (
                        d.opposite() in grid.walls_at(nx, ny)
                    )


# --------------------------------------------------------------------------
# Spawn helpers
# --------------------------------------------------------------------------


def test_nearest_walkable_returns_same_cell_when_walkable(grid: Grid) -> None:
    assert grid.nearest_walkable(2, 2) == (2, 2)


def test_nearest_walkable_snaps_out_of_sealed_cell(grid: Grid) -> None:
    assert grid.nearest_walkable(1, 1) in grid.walkable


def test_nearest_walkable_tie_break_is_deterministic(grid: Grid) -> None:
    # (0,1), (1,0), (1,2), (2,1) are all at distance 1: smallest tuple wins
    assert grid.nearest_walkable(1, 1) == (0, 1)
    assert all(grid.nearest_walkable(1, 1) == (0, 1) for _ in range(20))


def test_nearest_walkable_empty_grid_raises(cells) -> None:
    empty = Grid(3, 3, cells, frozenset())
    with pytest.raises(MazeError):
        empty.nearest_walkable(0, 0)


def test_corners_order_and_walkable(grid: Grid) -> None:
    assert grid.corners() == [(0, 0), (2, 0), (0, 2), (2, 2)]


def test_corners_snap_when_corner_is_sealed() -> None:
    # remove the top-right corner from the maze
    passages = [p for p in PASSAGES if (2, 0) not in p]
    cells = make_cells(3, 3, passages)
    walkable = EXPECTED_WALKABLE - {(2, 0)}
    g = Grid(3, 3, cells, walkable)
    corners = g.corners()
    assert len(corners) == 4
    assert all(c in walkable for c in corners)
    assert corners[1] != (2, 0)


def test_centre_snaps_to_walkable(grid: Grid) -> None:
    assert grid.centre() in grid.walkable
    assert grid.centre() == (0, 1)


# --------------------------------------------------------------------------
# _flood
# --------------------------------------------------------------------------


def test_flood_reaches_every_connected_cell(cells) -> None:
    assert _flood(cells, 3, 3, (0, 0)) == EXPECTED_WALKABLE


def test_flood_from_sealed_cell_stays_put(cells) -> None:
    assert _flood(cells, 3, 3, (1, 1)) == frozenset({(1, 1)})


def test_flood_does_not_cross_walls() -> None:
    # two separate rooms: left column and right column
    passages = [((0, 0), (0, 1)), ((2, 0), (2, 1))]
    cells = make_cells(3, 2, passages)
    assert _flood(cells, 3, 2, (0, 0)) == frozenset({(0, 0), (0, 1)})


# --------------------------------------------------------------------------
# MazeLoader: construction
# --------------------------------------------------------------------------


@pytest.mark.parametrize("w, h", [(2, 10), (10, 2), (0, 0), (-5, 5)])
def test_loader_rejects_too_small_sizes(w: int, h: int) -> None:
    with pytest.raises(MazeError, match="too small"):
        MazeLoader(w, h)


def test_loader_reports_missing_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "mazegenerator", None)
    with pytest.raises(MazeError, match="not installed"):
        MazeLoader(5, 5)


def test_loader_wraps_generator_init_failure(fake_generator) -> None:
    fake_generator.init_error = RuntimeError("boom")
    with pytest.raises(MazeError, match="failed to start"):
        MazeLoader(3, 3)


def test_loader_passes_size_to_generator(fake_generator) -> None:
    MazeLoader(7, 5)
    assert fake_generator.instances[0].size == (7, 5)
    assert fake_generator.instances[0].perfect is False


# --------------------------------------------------------------------------
# MazeLoader: generate
# --------------------------------------------------------------------------


def test_generate_returns_expected_grid(fake_generator) -> None:
    g = MazeLoader(3, 3).generate(5)
    assert (g.width, g.height) == (3, 3)
    assert g.walkable == EXPECTED_WALKABLE
    assert g.cells == make_cells(3, 3, PASSAGES)
    assert isinstance(g.cells, tuple)
    assert all(isinstance(r, tuple) for r in g.cells)


def test_generate_passes_seed(fake_generator) -> None:
    loader = MazeLoader(3, 3)
    loader.generate(42)
    assert fake_generator.instances[0].generate_calls == [42]


def test_generate_clamps_negative_seed_to_zero(fake_generator) -> None:
    loader = MazeLoader(3, 3)
    loader.generate(-7)
    assert fake_generator.instances[0].generate_calls == [0]


def test_generate_masks_values_to_four_bits(fake_generator) -> None:
    fake_generator.maze = [
        [v | 0x10 for v in row] for row in make_cells(3, 3, PASSAGES)
    ]
    g = MazeLoader(3, 3).generate(1)
    assert g.cells == make_cells(3, 3, PASSAGES)


def test_generate_wraps_generator_failure(fake_generator) -> None:
    loader = MazeLoader(3, 3)
    fake_generator.generate_error = RuntimeError("boom")
    with pytest.raises(MazeError, match="generation failed"):
        loader.generate(1)


@pytest.mark.parametrize(
    "bad_maze",
    [
        None,
        [],
        [[15, 15, 15], [15, 15, 15]],  # too few rows
        [[15, 15], [15, 15], [15, 15]],  # rows too short
        [[15, 15, 15], [15, 15, 15], [15, 15]],  # one short row
    ],
)
def test_generate_rejects_malformed_grid(fake_generator, bad_maze) -> None:
    fake_generator.maze = bad_maze
    with pytest.raises(MazeError, match="malformed"):
        MazeLoader(3, 3).generate(1)


def test_generate_rejects_maze_without_corridors(fake_generator) -> None:
    fake_generator.maze = [[SEALED] * 3 for _ in range(3)]
    with pytest.raises(MazeError, match="no usable corridors"):
        MazeLoader(3, 3).generate(1)


def test_generate_can_be_called_repeatedly(fake_generator) -> None:
    loader = MazeLoader(3, 3)
    assert loader.generate(1) == loader.generate(2)


# --------------------------------------------------------------------------
# Real generator (skipped when the package is missing)
# --------------------------------------------------------------------------


@pytest.fixture
def real_loader() -> MazeLoader:
    pytest.importorskip("mazegenerator")
    return MazeLoader(20, 15)


def test_real_same_seed_same_maze(real_loader: MazeLoader) -> None:
    other = MazeLoader(20, 15)
    assert real_loader.generate(42).cells == other.generate(42).cells


def test_real_maze_is_usable(real_loader: MazeLoader) -> None:
    g = real_loader.generate(42)
    assert len(g.cells) == 15
    assert all(len(row) == 20 for row in g.cells)
    assert len(g.walkable) > 4
    assert all(c in g.walkable for c in g.corners())
    assert g.centre() in g.walkable


def test_real_walls_are_symmetric(real_loader: MazeLoader) -> None:
    g = real_loader.generate(42)
    for y in range(g.height):
        for x in range(g.width):
            for d in WALL_ORDER:
                nx, ny = x + d.dx, y + d.dy
                if g.contains(nx, ny):
                    assert (d in g.walls_at(x, y)) == (
                        d.opposite() in g.walls_at(nx, ny)
                    ), f"asymmetric wall at {(x, y)} {d.name}"


def test_real_sealed_cells_are_not_walkable(real_loader: MazeLoader) -> None:
    g = real_loader.generate(42)
    for y in range(g.height):
        for x in range(g.width):
            if g.is_sealed(x, y):
                assert (x, y) not in g.walkable


def test_real_every_walkable_cell_has_a_neighbour(
    real_loader: MazeLoader,
) -> None:
    g = real_loader.generate(42)
    assert all(g.neighbours(x, y) for x, y in g.walkable)
