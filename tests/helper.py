"""Shared test doubles: hand-built mazes, a fake Gfx, a Context factory."""
from pathlib import Path
from typing import Any, Callable

from pacman.config import Config
from pacman.gfx import Event, EventType, Key, Renderer
from pacman.highscores import Highscores
from pacman.maze_loader import Grid
from pacman.scenes.base import Context
from pacman.scenes.message import MessageScene

N, E, S, W = 1, 2, 4, 8


def open_grid(width: int, height: int) -> Grid:
    """No inner walls, closed border, every cell walkable."""
    cells = tuple(
        tuple(
            (N if y == 0 else 0) | (S if y == height - 1 else 0)
            | (W if x == 0 else 0) | (E if x == width - 1 else 0)
            for x in range(width)
        )
        for y in range(height)
    )
    walkable = frozenset((x, y) for y in range(height) for x in range(width))
    return Grid(width, height, cells, walkable)


def make_factory(seeds: list[int], sizes: list[tuple[int, int]] | None = None,
                 grid: Callable[[], Grid] = lambda: open_grid(5, 5)) -> Any:
    """A loader factory for Game that records sizes and seeds."""
    def factory(width: int, height: int) -> Any:
        if sizes is not None:
            sizes.append((width, height))

        class Loader:
            def generate(self, seed: int = 0) -> Grid:
                seeds.append(seed)
                return grid()
        return Loader()
    return factory


class FakeGfx:
    """Just enough of Gfx for scenes and the renderer; records the output."""

    def __init__(self, size: tuple[int, int] = (800, 600)) -> None:
        self.size = size
        self.texts: list[str] = []
        self.rects: list[tuple[Any, ...]] = []
        self.queue: list[Event] = []
        self.closed = False

    def screen_size(self) -> tuple[int, int]:
        return self.size

    def fill_rect(self, color: Any, x: int, y: int, w: int, h: int) -> None:
        self.rects.append((color, x, y, w, h))

    def draw_text(self, text: str, x: int, y: int, size: int, color: Any) -> None:
        self.texts.append(text)

    def text_size(self, text: str, size: int) -> tuple[int, int]:
        return len(text) * size // 2, size

    def draw_sprite(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def has_sprite(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def poll_events(self) -> list[Event]:
        events, self.queue = self.queue, []
        return events

    def present(self) -> float:
        return 0.016

    def close(self) -> None:
        self.closed = True


def make_context(tmp_path: Path, config: Config | None = None,
                 start_game: Callable[[Context], Any] | None = None) -> Context:
    gfx = FakeGfx()
    return Context(
        gfx=gfx,  # type: ignore[arg-type]
        renderer=Renderer(gfx),  # type: ignore[arg-type]
        config=config or Config(),
        highscores=Highscores(tmp_path / "hs.json"),
        start_game=start_game or (lambda c: MessageScene(c, "game")),
    )


def down(key: Key = Key.OTHER, char: str = "") -> Event:
    return Event(EventType.KEY_DOWN, key, char)


def up(key: Key = Key.OTHER) -> Event:
    return Event(EventType.KEY_UP, key)


def typed(char: str) -> Event:
    return down(Key.OTHER, char)