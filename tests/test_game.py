import pytest

from pacman.config import Config, LevelConfig
from pacman.constants import (CHEAT_SPEED_MULTIPLIER, DEATH_PAUSE,
                              MAX_FRAME_DT, PLAYER_STEPS_PER_SECOND,
                              RESPAWN_GRACE)
from pacman.entities.ghost import GhostState
from pacman.game import Game, GameResult, Phase
from pacman.maze_loader import MazeError
from tests.helpers import make_factory

EAST = __import__("pacman.constants", fromlist=["Direction"]).Direction.EAST


def make_game(levels: int = 3, **kwargs: int) -> tuple[Game, list[int]]:
    seeds: list[int] = []
    cfg = Config(levels=tuple(LevelConfig(5, 5) for _ in range(levels)),
                 **kwargs)
    return Game(cfg, loader_fac=make_factory(seeds)), seeds


def catch_player(game: Game, index: int = 0) -> None:
    """Freeze the world and put a ghost on the player."""
    game.cheat.freeze = True
    game.grace = 0.0
    game.ghosts[index].cell = game.player.cell


# ---- start ----
def test_starts_on_level_one() -> None:
    game, seeds = make_game(seed=7)
    assert (game.level_index, game.score, game.lives) == (1, 0, 3)
    assert game.phase is Phase.PLAYING and seeds == [7]
    assert game.total_levels == 3


def test_loader_gets_each_levels_size() -> None:
    sizes: list[tuple[int, int]] = []
    cfg = Config(levels=(LevelConfig(7, 6), LevelConfig(9, 8)))
    game = Game(cfg, loader_fac=make_factory([], sizes))
    game.cheat.handle_key("1")
    game.update(0.016)
    assert sizes == [(7, 6), (9, 8)]


def test_maze_error_propagates() -> None:
    def broken(w: int, h: int) -> object:
        raise MazeError("no generator")
    with pytest.raises(MazeError):
        Game(Config(), loader_fac=broken)  # type: ignore[arg-type]


# ---- levels ----
def test_first_level_is_seeded_later_ones_are_random() -> None:
    game, seeds = make_game(seed=42)
    game.cheat.handle_key("1")
    game.update(0.016)
    assert seeds == [42, 0] and game.level_index == 2


def test_skip_works_during_the_death_pause() -> None:
    game, _ = make_game()
    game.stun = 1.0
    game.cheat.handle_key("1")
    game.update(0.016)
    assert game.level_index == 2 and game.stun == 0.0


def test_clearing_the_level_advances_and_keeps_score_and_lives() -> None:
    game, _ = make_game()
    game.player.press(EAST)
    game.update(0.016)                         # eats one pacgum
    assert game.score == 10
    game.level.pacgums.clear()
    game.level.supgums.clear()
    game.update(0.016)
    assert game.level_index == 2
    assert game.score == 10 and game.lives == 3
    assert game.time_left == float(game.cfg.level_max_time)
    assert len(game.level.pacgums) > 0         # a fresh board


def test_clearing_the_last_level_wins() -> None:
    game, _ = make_game(levels=1)
    game.level.pacgums.clear()
    game.level.supgums.clear()
    game.update(0.016)
    assert game.phase is Phase.WON
    assert game.result == GameResult(0, 1, True)


def test_skipping_past_the_last_level_wins() -> None:
    game, _ = make_game(levels=2)
    for _ in range(2):
        game.cheat.handle_key("1")
        game.update(0.016)
    assert game.phase is Phase.WON and game.level_index == 2


def test_held_key_survives_a_level_change() -> None:
    game, _ = make_game()
    game.player.press(EAST)
    game.cheat.handle_key("1")
    game.update(0.016)
    assert game.player.wish is EAST


# ---- score ----
def test_pacgum_scores_configured_points() -> None:
    game, _ = make_game(points_per_pacgum=7)
    game.player.press(EAST)
    game.update(0.016)
    assert game.score == 7


def test_super_pacgum_scores_and_frightens_every_ghost() -> None:
    game, _ = make_game(points_per_super_pacgum=55)
    game.level.pacgums.discard((3, 2))
    game.level.supgums.add((3, 2))
    game.player.press(EAST)
    game.update(0.016)
    assert game.score == 55
    assert all(g.state is GhostState.FRIGHTENED for g in game.ghosts)


def test_score_cannot_decrease() -> None:
    game, _ = make_game()
    with pytest.raises(AssertionError):
        game._add_score(-1)


def test_eating_a_frightened_ghost_scores_and_sends_it_home() -> None:
    game, _ = make_game(points_per_ghost=250)
    catch_player(game)
    game.ghosts[0].frighten(7.0)
    game.update(0.016)
    assert game.score == 250 and game.lives == 3
    assert game.ghosts[0].state is GhostState.DEAD
    assert game.ghosts[0].cell == game.ghosts[0].home


def test_swapping_cells_counts_as_contact() -> None:
    game, _ = make_game()
    game.cheat.freeze = True
    game.grace = 0.0
    ghost, player = game.ghosts[0], game.player
    player.prev, ghost.prev = (2, 3), player.cell
    ghost.cell, player.prev = (2, 3), (2, 3)
    ghost.prev = player.cell
    game.update(0.016)
    assert game.lives == 2


# ---- dying ----
def test_chasing_ghost_costs_a_life_and_respawns() -> None:
    game, _ = make_game()
    catch_player(game)
    game.update(0.016)
    assert game.lives == 2 and game.phase is Phase.PLAYING
    assert game.stun == DEATH_PAUSE and game.grace == RESPAWN_GRACE
    assert game.player.cell == game.level.player


def test_grace_period_protects_the_player() -> None:
    game, _ = make_game()
    catch_player(game)
    game.grace = 1.0
    game.update(0.016)
    assert game.lives == 3


def test_invincible_cheat_protects_the_player() -> None:
    game, _ = make_game()
    catch_player(game)
    game.cheat.invincible = True
    game.update(0.016)
    assert game.lives == 3


def test_dead_ghost_is_harmless() -> None:
    game, _ = make_game()
    catch_player(game)
    game.ghosts[0].eaten()
    game.ghosts[0].cell = game.player.cell
    game.update(0.016)
    assert game.lives == 3


def test_world_is_frozen_during_the_death_pause() -> None:
    game, _ = make_game()
    game.stun = 0.5
    before = game.time_left
    game.update(0.1)
    assert game.time_left == before and game.stun == pytest.approx(0.4)


def test_last_life_ends_the_run() -> None:
    game, _ = make_game(lives=1)
    catch_player(game)
    game.update(0.016)
    assert game.phase is Phase.LOST and game.lives == 0
    assert game.result.won is False


def test_extra_life_cheat() -> None:
    game, _ = make_game()
    game.cheat.handle_key("4")
    game.update(0.016)
    assert game.lives == 4


# ---- time ----
def test_timer_counts_down() -> None:
    game, _ = make_game(level_max_time=90)
    game.update(0.05)
    assert game.time_left == pytest.approx(89.95)


def test_timeout_is_fatal_and_keeps_the_score() -> None:
    game, _ = make_game()
    game.player.press(EAST)
    game.update(0.016)
    game.time_left = 0.01
    game.update(0.1)
    assert game.phase is Phase.LOST and game.lives == 0 and game.score == 10


def test_frame_time_is_capped() -> None:
    game, _ = make_game(level_max_time=90)
    game.update(10.0)
    assert game.time_left == pytest.approx(90 - MAX_FRAME_DT)


def test_nothing_runs_after_the_run_is_over() -> None:
    game, _ = make_game()
    game.time_left = 0.01
    game.update(0.1)
    before = game.time_left
    game.update(0.1)
    assert game.time_left == before


# ---- cheats ----
def test_speed_cheat_doubles_player_speed() -> None:
    game, _ = make_game()
    game.cheat.handle_key("5")
    game.update(0.016)
    assert game.player.speed == PLAYER_STEPS_PER_SECOND * CHEAT_SPEED_MULTIPLIER
    game.cheat.handle_key("5")
    game.update(0.016)
    assert game.player.speed == PLAYER_STEPS_PER_SECOND


def test_freeze_cheat_stops_the_ghosts() -> None:
    game, _ = make_game()
    game.cheat.freeze = True
    homes = [g.cell for g in game.ghosts]
    for _ in range(10):
        game.update(0.1)
    assert [g.cell for g in game.ghosts] == homes