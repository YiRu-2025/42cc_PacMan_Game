import pytest

from pacman.constants import Direction
from pacman.entities.player import Player
from pacman.level import Level, Pickup, build_level
from tests.helpers import open_grid

E, S, N = Direction.EAST, Direction.SOUTH, Direction.NORTH


@pytest.fixture
def level() -> Level:
    return build_level(open_grid(5, 5))          # player starts at (2, 2)


@pytest.fixture
def player(level: Level) -> Player:
    return Player(level.player, 6.0)


def test_idle_player_never_moves(player: Player, level: Level) -> None:
    for _ in range(20):
        assert player.update(0.1, level) == []
    assert player.cell == (2, 2)


def test_idle_keeps_prev_equal_to_cell(player: Player, level: Level) -> None:
    player.press(E)
    player.update(0.1, level)
    player.release(E)
    player.update(0.1, level)
    assert player.prev == player.cell


def test_press_moves_at_once_and_eats(player: Player, level: Level) -> None:
    player.press(E)
    assert player.update(0.016, level) == [Pickup.PACGUM]
    assert player.cell == (3, 2)


def test_tap_moves_exactly_one_cell(player: Player, level: Level) -> None:
    player.press(E)
    player.release(E)                    # released before any step ran
    for _ in range(5):
        player.update(0.016, level)
    assert player.cell == (3, 2)


def test_repeated_taps_each_move_one_cell(player: Player, level: Level) -> None:
    for expected in [(3, 2), (4, 2)]:
        player.press(E)
        player.release(E)
        player.update(0.001, level)
        assert player.cell == expected


def test_hold_keeps_moving_until_the_wall(player: Player, level: Level) -> None:
    player.press(E)
    for _ in range(6):
        player.update(0.1, level)
    assert player.cell == (4, 2)
    assert player.direction is E          # still facing the wall


def test_release_stops_the_player(player: Player, level: Level) -> None:
    player.press(E)
    player.update(0.1, level)
    player.release(E)
    for _ in range(5):
        player.update(0.1, level)
    assert player.cell == (3, 2)


def test_blocked_direction_does_not_move(level: Level) -> None:
    p = Player((0, 0), 6.0)
    p.press(N)
    p.update(0.1, level)
    assert p.cell == (0, 0) and p.direction is None


def test_last_pressed_key_wins(player: Player, level: Level) -> None:
    player.press(E)
    player.press(S)
    player.update(0.016, level)
    assert player.cell == (2, 3)


def test_releasing_newer_key_falls_back_to_older(player: Player,
                                                 level: Level) -> None:
    player.press(E)
    player.press(S)
    player.release(S)
    player.update(0.016, level)
    assert player.cell == (3, 2)


def test_pressing_twice_does_not_duplicate(player: Player, level: Level) -> None:
    player.press(E)
    player.press(E)
    player.release(E)
    player.update(0.1, level)
    player.update(0.1, level)
    assert player.cell == (3, 2)          # only the tap, nothing held


def test_release_of_unheld_key_is_harmless(player: Player) -> None:
    player.release(N)
    assert player.wish is None


def test_release_all_forgets_everything(player: Player, level: Level) -> None:
    player.press(E)
    player.release_all()
    player.update(0.1, level)
    assert player.cell == (2, 2)


def test_copy_input_keeps_held_keys(level: Level) -> None:
    old, new = Player((2, 2)), Player((2, 2))
    old.press(E)
    new.copy_input(old)
    new.update(0.016, level)
    assert new.cell == (3, 2)


def test_super_pacgum_is_reported(player: Player, level: Level) -> None:
    level.pacgums.discard((3, 2))
    level.supgums.add((3, 2))
    player.press(E)
    assert player.update(0.016, level) == [Pickup.SUPGUM]


def test_empty_cell_reports_none(player: Player, level: Level) -> None:
    level.pacgums.clear()
    player.press(E)
    assert player.update(0.016, level) == [Pickup.NONE]