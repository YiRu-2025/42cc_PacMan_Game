import pytest

from pacman.constants import Direction
from pacman.entities.ghost import Ghost, GhostState, distance_map
from pacman.level import Level
from pacman.maze_loader import Grid
from tests.helpers import open_grid


def corridor(length: int) -> Grid:
    return open_grid(length, 1)


def level_for(grid: Grid) -> Level:
    return Level(grid=grid, player=(0, 0), ghosts=[])


def ghost(home: tuple[int, int], delay: float = 0.25) -> Ghost:
    return Ghost(home, speed=5.0, fright_factor=0.5, respawn_delay=delay)


# ---- distance_map ----
def test_distance_map_on_a_corridor() -> None:
    assert distance_map(corridor(5), (0, 0)) == {(i, 0): i for i in range(5)}


def test_distance_map_covers_open_grid() -> None:
    d = distance_map(open_grid(4, 4), (0, 0))
    assert len(d) == 16 and d[(3, 3)] == 6


def test_distance_map_skips_unreachable_cells() -> None:
    g = open_grid(3, 1)
    g = Grid(3, 1, g.cells, frozenset({(0, 0), (1, 0)}))
    assert set(distance_map(g, (0, 0))) == {(0, 0), (1, 0)}


# ---- state machine ----
def test_new_ghost_chases_from_home() -> None:
    g = ghost((3, 0))
    assert g.state is GhostState.CHASE and g.cell == g.home == (3, 0)


def test_chase_steps_toward_the_player() -> None:
    grid = corridor(5)
    g = ghost((4, 0))
    g.step(level_for(grid), distance_map(grid, (0, 0)))
    assert g.cell == (3, 0) and g.direction is Direction.WEST


def test_frightened_steps_away_from_the_player() -> None:
    grid = corridor(5)
    g = ghost((2, 0))
    g.frighten(5.0)
    g.step(level_for(grid), distance_map(grid, (0, 0)))
    assert g.cell == (3, 0)


def test_chase_ties_go_to_the_first_neighbour() -> None:
    grid = open_grid(3, 3)
    g = ghost((1, 1))
    g.step(level_for(grid), distance_map(grid, (0, 0)))
    assert g.cell == (1, 0)               # north before west, both distance 1


def test_ghost_with_no_exits_stays_put() -> None:
    cells = tuple((0,) * 3 for _ in range(3))
    grid = Grid(3, 3, cells, frozenset({(1, 1)}))
    g = ghost((1, 1))
    g.step(level_for(grid), {(1, 1): 0})
    assert g.cell == (1, 1)


def test_chasing_ghost_reaches_a_still_player() -> None:
    grid = open_grid(5, 5)
    g = ghost((4, 4))
    lvl = level_for(grid)
    dist = distance_map(grid, (0, 0))
    for _ in range(8):
        g.step(lvl, dist)
    assert g.cell == (0, 0)


def test_frighten_sets_timer_and_slows_down() -> None:
    g = ghost((1, 0))
    g.frighten(7.0)
    assert g.state is GhostState.FRIGHTENED
    assert g.timer == 7.0 and g.speed == pytest.approx(2.5)


def test_frightened_wears_off() -> None:
    grid = corridor(5)
    g = ghost((2, 0))
    lvl, dist = level_for(grid), distance_map(grid, (0, 0))
    g.frighten(0.15)
    g.update(0.1, lvl, dist)
    assert g.state is GhostState.FRIGHTENED
    g.update(0.1, lvl, dist)
    assert g.state is GhostState.CHASE and g.speed == 5.0


def test_refrighten_restarts_the_timer() -> None:
    g = ghost((2, 0))
    g.frighten(1.0)
    g.timer = 0.2
    g.frighten(7.0)
    assert g.timer == 7.0


def test_eaten_ghost_goes_home_and_waits() -> None:
    g = ghost((1, 0), delay=3.0)
    g.move(Direction.EAST)
    g.eaten()
    assert g.state is GhostState.DEAD
    assert g.cell == (1, 0) and g.direction is None and g.timer == 3.0


def test_dead_ghost_cannot_be_frightened() -> None:
    g = ghost((1, 0))
    g.eaten()
    g.frighten(7.0)
    assert g.state is GhostState.DEAD


def test_dead_ghost_does_not_move_then_respawns() -> None:
    grid = corridor(5)
    g = ghost((4, 0), delay=0.25)
    lvl, dist = level_for(grid), distance_map(grid, (0, 0))
    g.eaten()
    assert g.update(0.1, lvl, dist) == []
    assert g.update(0.1, lvl, dist) == []
    assert g.cell == (4, 0) and g.state is GhostState.DEAD
    g.update(0.1, lvl, dist)
    assert g.state is GhostState.CHASE and g.speed == 5.0