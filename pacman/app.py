"""Application wiring and the main loop.

This module is the only one that knows the whole program: it reads the
configuration, opens the window, loads the highscore table, and runs the
scene stack until it empties. It is also the only place where the menu and
the gameplay package meet, through the two callables it puts in the
``Context``, so neither of those imports the other.

Start-up order matters. The window is sized for the largest level in the
configuration before any scene exists, so the window never changes size
mid-game; and the highscore table is loaded before the menu appears, so the
menu can show it immediately.
"""

import sys

from pacman.config import Config, load_config
from pacman.constants import (
    GAME_TITLE,
    HUD_HEIGHT,
    MAX_FRAME_DT,
    MIN_CELL_SIZE,
    cell_size_for,
)
from pacman.gfx import EventType, Gfx, GfxError
from pacman.highscores import Highscores
from pacman.gfx import Renderer
from pacman.scenes.base import (
    Context,
    Finish,
    GameResult,
    Pop,
    Push,
    Quit,
    Replace,
    Scene,
    Transition,
    load_optional,
)
from pacman.scenes.menu import MainMenuScene
from pacman.scenes.message import MessageScene


def window_size(config: Config) -> tuple[int, int]:
    """Return a window that fits every level in the configuration.

    Levels may differ in size, so the window is sized once for the largest
    of them and smaller mazes are centred inside it. Resizing between levels
    would flicker and, on some window managers, move the window.
        config: The validated configuration.
        ``(width, height)`` in pixels, including the HUD band.
    """
    width = height = 0
    for level in config.levels:
        cell = cell_size_for(level.width, level.height)
        width = max(width, level.width * cell)
        height = max(height, level.height * cell)
    if width < 1 or height < 1:
        width = height = MIN_CELL_SIZE * 10
    return width, height + HUD_HEIGHT


class App:
    """Owns the scene stack and the frame loop."""

    def __init__(self, context: Context, first: Scene) -> None:
        """Prepare the loop.

        Args:
            context: The shared state handed to every scene.
            first: The scene to show on start-up.
        """
        self.context = context
        self._stack: list[Scene] = [first]
        first.on_enter()

    @property
    def current(self) -> Scene | None:
        """The scene receiving input, or None once the stack is empty."""
        return self._stack[-1] if self._stack else None

    def apply(self, transition: Transition | None) -> None:
        """Carry out what a scene asked for.
        transition: The scene's answer, or None to change nothing.
        """
        if transition is None:
            return
        if isinstance(transition, Quit):
            while self._stack:
                self._stack.pop().on_exit()
            return
        if isinstance(transition, Push):
            if self._stack:
                self._stack[-1].on_exit()
            self._stack.append(transition.scene)
            transition.scene.on_enter()
            return
        if isinstance(transition, Finish):
            if self._stack:
                self._stack.pop().on_exit()
            follow = _finish_game(self.context, transition.result)
            self._stack.append(follow)
            follow.on_enter()
            return
        if isinstance(transition, Replace):
            if self._stack:
                self._stack.pop().on_exit()
            self._stack.append(transition.scene)
            transition.scene.on_enter()
            return
        if isinstance(transition, Pop):
            for _ in range(max(1, transition.count)):
                if not self._stack:
                    break
                self._stack.pop().on_exit()
            if self._stack:
                self._stack[-1].on_enter()

    def step(self, dt: float) -> bool:
        """Run one frame: input, then logic, then drawing.

        A transition stops the rest of the frame, so a scene that has just
        been left never sees the remaining events or gets an extra tick.
            dt: Seconds since the previous frame.
            True if the application should keep running.
        """
        scene = self.current
        if scene is None:
            return False

        for event in self.context.gfx.poll_events():
            if event.type is EventType.QUIT:
                self.apply(Quit())
                return False
            transition = scene.handle_event(event)      # KEY_DOWN and KEY_UP
            if transition is not None:
                self.apply(transition)
                self._draw()
                return bool(self._stack)

        transition = scene.update(min(dt, MAX_FRAME_DT))
        if transition is not None:
            self.apply(transition)
        self._draw()
        return bool(self._stack)

    def _draw(self) -> None:
        """Draw the stack, starting below any overlays on top."""
        if not self._stack:
            return
        first = len(self._stack) - 1
        while first > 0 and self._stack[first].transparent:
            first -= 1
        for scene in self._stack[first:]:
            scene.draw()

    def run(self) -> None:
        """Loop until the stack empties or the window closes."""
        dt = 0.0
        while self.step(dt):
            dt = self.context.gfx.present()
        self.context.gfx.present()


def _start_game(context: Context) -> Scene:
    """Build a gameplay scene.

    Imported here rather than at module level so that a missing or
    half-finished gameplay package cannot stop the menus from running, and
    so that the menu never imports the game.
        context: The shared state.
        The gameplay scene, or a message scene explaining what is missing.
    """
    factory = load_optional("pacman.scenes.play", "PlayScene")
    if factory is None:
        return MessageScene(
            context, "Not playable yet", "pacman/scenes/play.py is missing"
        )
    return factory(context)


def _finish_game(context: Context, result: GameResult) -> Scene:
    """Build the scene that follows a finished game.
    context: The shared state.
    result: What the session produced.
    The name prompt, or a message scene if it is not written yet.
    """
    factory = load_optional("pacman.scenes.name_entry", "NameEntryScene")
    if factory is None:
        verdict = "You win" if result.won else "Game over"
        return MessageScene(
            context,
            verdict,
            f"Score {result.score}",
            f"Reached level {result.level_reached}",
        )
    return factory(context, result)


def run(config_path: str) -> int:
    """Start the game and run it to completion.

    Every failure is reported as one readable line, never a traceback: the
    configuration is already forgiving, and the window is the only thing
    left that can refuse outright.

        config_path: Path to the JSON configuration file.
        0 on a clean exit, 1 if the game could not start.
    """
    config = load_config(config_path)
    highscores = Highscores(config.highscore_filename)
    highscores.load()

    width, height = window_size(config)
    try:
        gfx = Gfx(width, height, GAME_TITLE)
    except GfxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        context = Context(
            gfx=gfx,
            renderer=Renderer(gfx),
            config=config,
            highscores=highscores,
            start_game=_start_game,
        )
        App(context, MainMenuScene(context)).run()
    finally:
        gfx.close()
        highscores.save()
    return 0
