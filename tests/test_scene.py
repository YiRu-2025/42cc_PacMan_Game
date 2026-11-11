from pathlib import Path

import pytest

from pacman.gfx import Key
from pacman.highscores import Highscores
from pacman.scenes import (InstructionsScene, MainMenuScene, MessageScene,
                           NameEntryScene, PauseScene, ScoresScene)
from pacman.scenes.base import (Finish, GameResult, MenuItem, MenuScene, Pop,
                                Push, Quit, Replace, Scene)
from tests.helpers import FakeGfx, down, make_context, typed, up

RESULT = GameResult(score=100, won=True, level_reached=3)


def draws_text(scene: Scene) -> list[str]:
    scene.draw()
    gfx = scene.context.gfx
    assert isinstance(gfx, FakeGfx) and gfx.rects
    return gfx.texts


# ---- name entry ----
@pytest.fixture
def entry(tmp_path: Path) -> NameEntryScene:
    return NameEntryScene(make_context(tmp_path), RESULT)


def type_all(scene: NameEntryScene, text: str) -> None:
    for ch in text:
        scene.handle_event(typed(ch))


def test_typing_builds_the_name(entry: NameEntryScene) -> None:
    type_all(entry, "Bob 7")
    assert entry.name == "Bob 7" and entry.saved_name == "Bob 7"


@pytest.mark.parametrize("ch", ["é", "_", "名", "", "ab", "\n"])
def test_forbidden_characters_are_ignored(entry: NameEntryScene, ch: str) -> None:
    entry.handle_event(typed(ch))
    assert entry.name == ""


def test_leading_space_is_refused(entry: NameEntryScene) -> None:
    entry.handle_event(typed(" "))
    assert entry.name == ""
    type_all(entry, "a b")
    assert entry.name == "a b"


def test_name_stops_at_ten_characters(entry: NameEntryScene) -> None:
    type_all(entry, "abcdefghijklmnop")
    assert entry.name == "abcdefghij"


def test_backspace_deletes_and_is_safe_when_empty(entry: NameEntryScene) -> None:
    entry.handle_event(down(Key.BACKSPACE))
    type_all(entry, "ab")
    entry.handle_event(down(Key.BACKSPACE))
    assert entry.name == "a"


def test_enter_with_empty_name_does_nothing(entry: NameEntryScene) -> None:
    assert entry.handle_event(down(Key.ENTER)) is None
    assert entry.context.highscores.entries == ()


def test_enter_saves_and_shows_the_table(entry: NameEntryScene) -> None:
    type_all(entry, "Ann")
    out = entry.handle_event(down(Key.ENTER))
    assert isinstance(out, Replace) and isinstance(out.scene, ScoresScene)
    assert out.scene.highlight == 1
    assert entry.context.highscores.entries[0].name == "Ann"
    assert entry.context.highscores.path.exists()


def test_enter_with_trailing_space_trims_it(entry: NameEntryScene) -> None:
    type_all(entry, "Ann ")
    entry.handle_event(down(Key.ENTER))
    assert entry.context.highscores.entries[0].name == "Ann"


def test_escape_skips_without_saving(entry: NameEntryScene) -> None:
    type_all(entry, "Ann")
    assert isinstance(entry.handle_event(down(Key.ESCAPE)), Pop)
    assert entry.context.highscores.entries == ()


def test_key_up_is_ignored(entry: NameEntryScene) -> None:
    assert entry.handle_event(up(Key.ENTER)) is None


def test_placed_reflects_the_table(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    for i in range(10):
        ctx.highscores.add("p", 1000 + i)
    assert NameEntryScene(ctx, RESULT).placed is False
    assert NameEntryScene(ctx, GameResult(5000, False, 2)).placed is True


def test_caret_blinks_and_update_never_leaves(entry: NameEntryScene) -> None:
    assert entry.update(0.3) is None and entry.elapsed == pytest.approx(0.3)


@pytest.mark.parametrize("won, word", [(True, "You win"), (False, "Game over")])
def test_verdict_is_drawn(tmp_path: Path, won: bool, word: str) -> None:
    scene = NameEntryScene(make_context(tmp_path), GameResult(5, won, 1))
    assert word in draws_text(scene)


# ---- menus ----
def test_menu_cursor_wraps(tmp_path: Path) -> None:
    menu = MainMenuScene(make_context(tmp_path))
    menu.handle_event(down(Key.UP))
    assert menu.cursor == len(menu.items) - 1
    menu.handle_event(down(Key.DOWN))
    assert menu.cursor == 0


def test_menu_escape_quits(tmp_path: Path) -> None:
    assert isinstance(MainMenuScene(make_context(tmp_path)).handle_event(
        down(Key.ESCAPE)), Quit)


def test_menu_entries(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    menu = MainMenuScene(ctx)
    assert [i.label for i in menu.items] == [
        "Start", "Highscores", "Instructions", "Quit"]
    start = menu.handle_event(down(Key.ENTER))
    assert isinstance(start, Push) and isinstance(start.scene, MessageScene)
    menu.cursor = 1
    scores = menu.handle_event(down(Key.SPACE))
    assert isinstance(scores, Push) and isinstance(scores.scene, ScoresScene)
    menu.cursor = 2
    inst = menu.handle_event(down(Key.ENTER))
    assert isinstance(inst, Push) and isinstance(inst.scene, InstructionsScene)
    menu.cursor = 3
    assert isinstance(menu.handle_event(down(Key.ENTER)), Quit)


def test_menu_shows_best_score_only_when_there_is_one(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    assert not any(t.startswith("best") for t in draws_text(MainMenuScene(ctx)))
    ctx.highscores.add("a", 321)
    assert "best 321" in draws_text(MainMenuScene(ctx))


def test_menu_ignores_key_up(tmp_path: Path) -> None:
    menu = MainMenuScene(make_context(tmp_path))
    assert menu.handle_event(up(Key.DOWN)) is None and menu.cursor == 0


def test_empty_menu_does_not_crash(tmp_path: Path) -> None:
    menu = MenuScene(make_context(tmp_path), "t", [])
    assert menu.handle_event(down(Key.DOWN)) is None
    assert menu.handle_event(down(Key.ENTER)) is None
    menu.draw()


def test_custom_menu_item_action(tmp_path: Path) -> None:
    menu = MenuScene(make_context(tmp_path), "t", [MenuItem("x", lambda: Quit())])
    assert isinstance(menu.handle_event(down(Key.ENTER)), Quit)


# ---- pause ----
def test_pause_is_an_overlay(tmp_path: Path) -> None:
    assert PauseScene(make_context(tmp_path)).transparent is True


def test_pause_choices(tmp_path: Path) -> None:
    pause = PauseScene(make_context(tmp_path))
    assert isinstance(pause.handle_event(down(Key.ESCAPE)), Pop)
    resume = pause.handle_event(down(Key.ENTER))
    assert isinstance(resume, Pop) and resume.count == 1
    pause.handle_event(down(Key.DOWN))
    abandon = pause.handle_event(down(Key.ENTER))
    assert isinstance(abandon, Pop) and abandon.count == 2


def test_pause_draws(tmp_path: Path) -> None:
    assert "Paused" in draws_text(PauseScene(make_context(tmp_path)))


# ---- scores, message, instructions ----
def test_scores_any_key_leaves(tmp_path: Path) -> None:
    s = ScoresScene(make_context(tmp_path))
    assert isinstance(s.handle_event(down(Key.OTHER, "x")), Pop)
    assert s.handle_event(up(Key.OTHER)) is None


def test_scores_empty_table_message(tmp_path: Path) -> None:
    assert "no scores yet" in draws_text(ScoresScene(make_context(tmp_path)))


def test_scores_full_table_and_highlight(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    for i in range(12):
        ctx.highscores.add(f"p{i}", i * 10)
    texts = draws_text(ScoresScene(ctx, highlight=3))
    assert "Highscores" in texts and sum(t.startswith("p") for t in texts) == 10


def test_message_scene(tmp_path: Path) -> None:
    m = MessageScene(make_context(tmp_path), "Head", "line", "", "two")
    assert m.lines == ["line", "two"]
    assert isinstance(m.handle_event(down()), Pop)
    assert {"Head", "line", "two", "press any key"} <= set(draws_text(m))


def test_instructions_show_live_configuration(tmp_path: Path) -> None:
    from pacman.config import Config
    scene = InstructionsScene(make_context(tmp_path, config=Config(lives=7)))
    texts = draws_text(scene)
    assert "7" in texts and "skip to the next level" in texts
    assert isinstance(scene.handle_event(down()), Pop)


def test_instructions_fit_a_tiny_window(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    ctx.gfx.size = (300, 200)  # type: ignore[attr-defined]
    InstructionsScene(ctx).draw()