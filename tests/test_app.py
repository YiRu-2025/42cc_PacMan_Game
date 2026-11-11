from pathlib import Path

import pytest

import pacman.app as app
from pacman.config import Config, LevelConfig
from pacman.constants import HUD_HEIGHT, cell_size_for
from pacman.gfx import Event, EventType, GfxError, Key
from pacman.scenes import MessageScene, NameEntryScene
from pacman.scenes.base import (Finish, GameResult, Pop, Push, Quit, Replace,
                                Scene)
from tests.helpers import FakeGfx, down, make_context, up


class Recorder(Scene):
    def __init__(self, context: app.Context) -> None:
        super().__init__(context)
        self.events: list[Event] = []
        self.entered = self.exited = 0

    def handle_event(self, event: Event) -> None:
        self.events.append(event)
        return None

    def on_enter(self) -> None:
        self.entered += 1

    def on_exit(self) -> None:
        self.exited += 1

    def draw(self) -> None:
        pass


def make_app(tmp_path: Path) -> tuple[app.App, Recorder, app.Context]:
    ctx = make_context(tmp_path)
    first = Recorder(ctx)
    return app.App(ctx, first), first, ctx


# ---- window_size ----
def test_window_fits_the_largest_level() -> None:
    cfg = Config(levels=(LevelConfig(10, 10), LevelConfig(30, 20)))
    w, h = app.window_size(cfg)
    cell = cell_size_for(30, 20)
    assert (w, h) == (30 * cell, 20 * cell + HUD_HEIGHT)


def test_window_for_no_levels_is_still_valid() -> None:
    w, h = app.window_size(Config(levels=()))
    assert w > 0 and h > HUD_HEIGHT


# ---- transitions ----
def test_first_scene_is_entered(tmp_path: Path) -> None:
    _, first, _ = make_app(tmp_path)
    assert first.entered == 1


def test_push_keeps_the_scene_below(tmp_path: Path) -> None:
    a, first, ctx = make_app(tmp_path)
    top = Recorder(ctx)
    a.apply(Push(top))
    assert a.current is top and len(a._stack) == 2
    assert first.exited == 1 and top.entered == 1


def test_replace_swaps_the_top(tmp_path: Path) -> None:
    a, first, ctx = make_app(tmp_path)
    new = Recorder(ctx)
    a.apply(Replace(new))
    assert a._stack == [new] and first.exited == 1


def test_pop_returns_and_re_enters_the_scene_below(tmp_path: Path) -> None:
    a, first, ctx = make_app(tmp_path)
    a.apply(Push(Recorder(ctx)))
    a.apply(Pop())
    assert a.current is first and first.entered == 2


def test_pop_two_drops_two_scenes(tmp_path: Path) -> None:
    a, first, ctx = make_app(tmp_path)
    a.apply(Push(Recorder(ctx)))
    a.apply(Push(Recorder(ctx)))
    a.apply(Pop(2))
    assert a._stack == [first]


def test_popping_the_last_scene_empties_the_stack(tmp_path: Path) -> None:
    a, _, _ = make_app(tmp_path)
    a.apply(Pop(5))
    assert a.current is None and a.step(0.0) is False


def test_quit_empties_the_stack(tmp_path: Path) -> None:
    a, first, ctx = make_app(tmp_path)
    a.apply(Push(Recorder(ctx)))
    a.apply(Quit())
    assert a.current is None and first.exited == 1


def test_none_changes_nothing(tmp_path: Path) -> None:
    a, first, _ = make_app(tmp_path)
    a.apply(None)
    assert a._stack == [first]


def test_finish_replaces_the_game_with_the_name_prompt(tmp_path: Path) -> None:
    a, _, ctx = make_app(tmp_path)
    game = Recorder(ctx)
    a.apply(Push(game))
    a.apply(Finish(GameResult(10, False, 2)))
    assert len(a._stack) == 2 and game.exited >= 1
    assert isinstance(a.current, NameEntryScene)


# ---- the frame ----
def test_key_down_and_key_up_both_reach_the_scene(tmp_path: Path) -> None:
    a, first, ctx = make_app(tmp_path)
    ctx.gfx.queue = [down(Key.LEFT), up(Key.LEFT)]  # type: ignore[attr-defined]
    a.step(0.016)
    assert [e.type for e in first.events] == [EventType.KEY_DOWN, EventType.KEY_UP]


def test_quit_event_ends_the_loop(tmp_path: Path) -> None:
    a, _, ctx = make_app(tmp_path)
    ctx.gfx.queue = [Event(EventType.QUIT)]  # type: ignore[attr-defined]
    assert a.step(0.016) is False and a.current is None


def test_transition_stops_the_rest_of_the_frame(tmp_path: Path) -> None:
    class Leaver(Recorder):
        def handle_event(self, event: Event) -> Pop:
            super().handle_event(event)
            return Pop()
    ctx = make_context(tmp_path)
    leaver = Leaver(ctx)
    a = app.App(ctx, leaver)
    ctx.gfx.queue = [down(), down()]  # type: ignore[attr-defined]
    a.step(0.016)
    assert len(leaver.events) == 1


def test_transparent_scene_draws_the_one_below(tmp_path: Path) -> None:
    drawn: list[str] = []

    class Named(Recorder):
        def __init__(self, ctx: app.Context, name: str, transparent: bool) -> None:
            super().__init__(ctx)
            self.name, self.transparent = name, transparent

        def draw(self) -> None:
            drawn.append(self.name)
    ctx = make_context(tmp_path)
    a = app.App(ctx, Named(ctx, "game", False))
    a.apply(Push(Named(ctx, "pause", True)))
    a._draw()
    assert drawn == ["game", "pause"]
    drawn.clear()
    a.apply(Push(Named(ctx, "screen", False)))
    a._draw()
    assert drawn == ["screen"]


# ---- run ----
def test_run_starts_quits_and_saves(tmp_path: Path,
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    fake = FakeGfx()
    fake.queue = [Event(EventType.QUIT)]
    monkeypatch.setattr(app, "Gfx", lambda w, h, t: fake)
    assert app.run(str(tmp_path / "missing.json")) == 0
    assert fake.closed and (tmp_path / "highscore.json").exists()


def test_run_reports_a_window_failure(tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch,
                                      capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)

    def boom(w: int, h: int, t: str) -> None:
        raise GfxError("no display")
    monkeypatch.setattr(app, "Gfx", boom)
    assert app.run("none.json") == 1
    assert "no display" in capsys.readouterr().err