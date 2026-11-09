"""Application wiring and the main loop.

This module is the only one that knows the whole program: it reads the
configuration, opens the window, loads the highscore table, and runs the
scene stack until it empties. It is also the only place where the menu, the
gameplay scene and the name prompt meet, so none of them import each other.

Start-up order matters. The window is sized for the largest level in the
configuration before any scene exists, so it never changes size mid-game;
and the highscore table is loaded before the menu appears, so the menu can
show the best score immediately.
"""

import sys
from pathlib import Path

from pacman.config import Config, load_config
from pacman.constants import (
    HUD_HEIGHT,
    MAX_WINDOW_HEIGHT,
    MAX_WINDOW_WIDTH,
    cell_size_for,
)
from pacman.gfx import EventType, Gfx, GfxError, Renderer
from pacman.highscores import Highscores
from pacman.maze_loader import MazeError
from pacman.scenes.base import (
    Context,
    Finish,
    Pop,
    Push,
    Quit,
    Replace,
    Scene,
    Transition,
)
from pacman.scenes.menu import MainMenuScene
from pacman.scenes.message import MessageScene
from pacman.scenes.name_entry import NameEntryScene
from pacman.scenes.play import PlayScene

MIN_WINDOW_WIDTH: int = 640
MIN_WINDOW_HEIGHT: int = 520
"""Menus and the name prompt need this much room, whatever the maze."""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def window_size(config: Config) -> tuple[int, int]:
    """Return a window size that fits the largest configured level.

    Args:
        config: The validated configuration.

    Returns:
        ``(width, height)`` in pixels, never below the menu minimum and
        never above the maximum window size.
    """
    width = MIN_WINDOW_WIDTH
    height = MIN_WINDOW_HEIGHT
    for level in config.levels:
        cell = cell_size_for(level.width, level.height)
        width = max(width, level.width * cell)
        height = max(height, level.height * cell + HUD_HEIGHT)
    return min(width, MAX_WINDOW_WIDTH), min(height, MAX_WINDOW_HEIGHT)


def data_path(name: str) -> Path:
    """Return where a writable file (the highscores) should live.

    A PyInstaller build unpacks read-only resources into a temporary
    folder, which is deleted on exit, so writable data goes next to the
    executable instead. Run from source, it is simply relative to the
    current directory.

    Args:
        name: File name from the configuration.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / name
    return Path(name)


def start_game(context: Context) -> Scene:
    """Build a fresh gameplay scene, or a notice if the maze fails.

    This is the callable stored in ``Context.start_game``. ``PlayScene``
    generates its first maze in its constructor, so a generator failure
    surfaces here, and only the application knows what to show instead.

    Args:
        context: The shared state.
    """
    try:
        return PlayScene(context)
    except MazeError as exc:
        return MessageScene(context, "Cannot start", str(exc))


# --------------------------------------------------------------------------
# Scene stack
# --------------------------------------------------------------------------


class SceneManager:
    """The stack of screens, and the code that obeys ``Transition``s.

    The top scene receives input and ticks. Scenes below it are only drawn,
    and only when everything above them is transparent (the pause overlay).
    """

    def __init__(self, context: Context) -> None:
        """Create an empty stack.

        Args:
            context: The shared state, needed to build the result screen.
        """
        self.context = context
        self.stack: list[Scene] = []

    @property
    def top(self) -> Scene:
        """The scene that currently owns input."""
        return self.stack[-1]

    # ------------------------------------------------------------ primitives

    def push(self, scene: Scene) -> None:
        """Put a scene on top, keeping the current one underneath."""
        if self.stack:
            self.top.on_exit()
        self.stack.append(scene)
        scene.on_enter()

    def pop(self, count: int = 1) -> None:
        """Remove ``count`` scenes from the top.

        Popping more scenes than exist simply empties the stack, which ends
        the program.
        """
        for _ in range(max(count, 1)):
            if not self.stack:
                break
            self.stack.pop().on_exit()
        if self.stack:
            self.top.on_enter()

    def replace(self, scene: Scene) -> None:
        """Swap the top scene for another, at the same depth."""
        if self.stack:
            self.stack.pop().on_exit()
        self.stack.append(scene)
        scene.on_enter()

    def clear(self) -> None:
        """Remove every scene, which ends the main loop."""
        while self.stack:
            self.stack.pop().on_exit()

    # ----------------------------------------------------------- transitions

    def apply(self, transition: Transition | None) -> None:
        """Carry out whatever a scene asked for.

        Args:
            transition: The scene's answer, or None for "stay as you are".
        """
        if transition is None:
            return
        if isinstance(transition, Push):
            self.push(transition.scene)
        elif isinstance(transition, Replace):
            self.replace(transition.scene)
        elif isinstance(transition, Pop):
            self.pop(transition.count)
        elif isinstance(transition, Finish):
            # Replace, never push: dismissing the result must return to the
            # menu, not to a game that has already ended.
            self.replace(NameEntryScene(self.context, transition.result))
        elif isinstance(transition, Quit):
            self.clear()

    # --------------------------------------------------------------- drawing

    def draw(self) -> None:
        """Draw the top scene, and any scenes it is an overlay on.

        Walk down from the top while scenes are transparent, then draw
        from that scene upwards, so a pause overlay lands on a game frame.
        """
        start = len(self.stack) - 1
        while start > 0 and self.stack[start].transparent:
            start -= 1
        for scene in self.stack[start:]:
            scene.draw()


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------


def run(context: Context) -> None:
    """Run the scene stack until it is empty or the window is closed.

    Args:
        context: The shared state, with a window already open.
    """
    gfx = context.gfx
    manager = SceneManager(context)
    manager.push(MainMenuScene(context))
    dt = 0.0

    while manager.stack:
        for event in gfx.poll_events():
            if not manager.stack:
                break
            if event.type is EventType.QUIT:
                manager.clear()
                break
            manager.apply(manager.top.handle_event(event))
        if not manager.stack:
            break

        try:
            manager.apply(manager.top.update(dt))
        except MazeError as exc:
            # A later level failed to generate mid-game. Drop the game and
            # explain, rather than crash; any key returns to the menu.
            manager.replace(MessageScene(context, "Maze error", str(exc)))
        if not manager.stack:
            break

        manager.draw()
        dt = gfx.present()


def main(config_path: str) -> None:
    """Start the game.

    Args:
        config_path: Path to the JSON configuration file. A missing or
            broken file is reported and replaced by the defaults.
    """
    config = load_config(config_path)
    highscores = Highscores(data_path(config.highscore_filename))
    highscores.load()
    width, height = window_size(config)
    try:
        with Gfx(width, height) as gfx:
            context = Context(
                gfx=gfx,
                renderer=Renderer(gfx),
                config=config,
                highscores=highscores,
                start_game=start_game,
            )
            run(context)
    except GfxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
