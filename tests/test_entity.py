from typing import Any

import pytest

from pacman.constants import Direction
from pacman.entities.base import Entity
from pacman.level import Level
from tests.helpers import open_grid


class Counter(Entity):
    def step(self, level: Level, *ctx: Any) -> int:
        return 1


class Walker(Entity):
    def step(self, level: Level, *ctx: Any) -> None:
        self.move(Direction.EAST)


@pytest.fixture
def level() -> Level:
    return Level(grid=open_grid(5, 5), player=(2, 2), ghosts=[])


def test_entity_is_abstract() -> None:
    with pytest.raises(TypeError):
        Entity((0, 0), 1.0)  # type: ignore[abstract]


def test_initial_state() -> None:
    e = Counter((1, 1), 4.0)
    assert e.cell == e.prev == (1, 1)
    assert e.direction is None


def test_move_updates_cell_and_direction() -> None:
    e = Counter((1, 1), 4.0)
    e.move(Direction.EAST)
    assert e.cell == (2, 1) and e.direction is Direction.EAST


def test_can_move(level: Level) -> None:
    e = Counter((0, 0), 4.0)
    assert not e.can_move(level.grid, None)
    assert not e.can_move(level.grid, Direction.NORTH)   # border
    assert not e.can_move(level.grid, Direction.WEST)
    assert e.can_move(level.grid, Direction.EAST)


def test_reset_clears_everything() -> None:
    e = Counter((1, 1), 4.0)
    e.move(Direction.EAST)
    e._cooldown = 5.0
    e.reset((0, 0))
    assert e.cell == e.prev == (0, 0)
    assert e.direction is None and e._cooldown == 0.0


def test_first_update_steps_at_once(level: Level) -> None:
    assert len(Counter((0, 0), 4.0).update(0.01, level)) == 1


def test_step_boundary_is_exact(level: Level) -> None:
    # speed 4 = one step per 0.25 s. With "<= 0" this took two steps.
    assert len(Counter((0, 0), 4.0).update(0.25, level)) == 1


def test_steps_follow_the_cooldown(level: Level) -> None:
    e = Counter((0, 0), 4.0)
    counts = [len(e.update(0.1, level)) for _ in range(3)]
    assert counts == [1, 0, 1]


def test_long_frame_runs_catch_up_steps(level: Level) -> None:
    assert len(Counter((0, 0), 4.0).update(1.0, level)) == 4


def test_update_records_previous_cell(level: Level) -> None:
    w = Walker((0, 0), 4.0)
    w.update(0.01, level)
    assert w.prev == (0, 0) and w.cell == (1, 0)


def test_ctx_is_forwarded(level: Level) -> None:
    class Echo(Entity):
        def step(self, level: Level, *ctx: Any) -> Any:
            return ctx
    assert Echo((0, 0), 4.0).update(0.01, level, "dist") == [("dist",)]