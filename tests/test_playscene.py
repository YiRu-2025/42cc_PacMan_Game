from pathlib import Path

import pytest

from pacman.constants import Direction
from pacman.game import Phase
from pacman.gfx import Key
from pacman.scenes import PauseScene, PlayScene
from pacman.scenes.base import Finish, Push
from tests.helpers import down, make_context, typed, up


@pytest.fixture
def scene(tmp_path: Path) -> PlayScene:
    pytest.importorskip("mazegenerator")
    return PlayScene(make_context(tmp_path))


def test_arrow_down_and_up_hold_and_release(scene: PlayScene) -> None:
    scene.handle_event(down(Key.RIGHT))
    assert scene.game.player.wish is Direction.EAST
    scene.handle_event(up(Key.RIGHT))
    scene.game.player._tap = None
    assert scene.game.player.wish is None


def test_wasd_maps_to_the_same_keys(scene: PlayScene) -> None:
    scene.handle_event(down(Key.UP, "w"))
    assert scene.game.player.wish is Direction.NORTH


def test_escape_opens_the_pause_overlay(scene: PlayScene) -> None:
    out = scene.handle_event(down(Key.ESCAPE))
    assert isinstance(out, Push) and isinstance(out.scene, PauseScene)


def test_pause_forgets_held_keys(scene: PlayScene) -> None:
    scene.handle_event(down(Key.RIGHT))
    scene.on_exit()
    scene.on_enter()
    assert scene.game.player.wish is None


def test_letter_keys_reach_the_cheats(scene: PlayScene) -> None:
    scene.handle_event(down(Key.OTHER, "2"))
    assert scene.game.cheat.invincible


def test_ordinary_update_keeps_playing(scene: PlayScene) -> None:
    assert scene.update(0.016) is None and scene.elapsed > 0


@pytest.mark.parametrize("phase, won", [(Phase.WON, True), (Phase.LOST, False)])
def test_end_of_game_finishes_with_a_result(scene: PlayScene, phase: Phase,
                                            won: bool) -> None:
    scene.game._score = 123
    scene.game.phase = phase
    out = scene.update(0.016)
    assert isinstance(out, Finish)
    assert (out.result.score, out.result.won) == (123, won)


def test_draw_renders_a_whole_frame(scene: PlayScene) -> None:
    scene.draw()
    gfx = scene.context.gfx
    assert gfx.rects and any(t.startswith("SCORE") for t in gfx.texts)  # type: ignore[attr-defined]
    assert any(t.startswith("LEVEL 1") for t in gfx.texts)              # type: ignore[attr-defined]


def test_animation_frame_stays_in_range(scene: PlayScene) -> None:
    for t in (0.0, 0.1, 5.0, 123.4):
        scene.elapsed = t
        assert 0 <= scene._frame(3) < 3
    assert scene._frame(1) == 0