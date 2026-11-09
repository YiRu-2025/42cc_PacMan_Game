"""The only module that touches pygame.

Everything the rest of the game needs from the graphics layer goes through
``Gfx``: a window, image blitting, text, event polling and frame pacing.
Events are translated into this module's own ``Event`` and ``Key`` types, so
no other module imports pygame, directly or indirectly.


"""

import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final

import pygame

from pacman.constants import ASSETS_DIR, FPS, GAME_TITLE

Color = tuple[int, int, int]


class Key(Enum):
    """A keyboard key, named independently of pygame's constants."""

    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    ENTER = auto()
    ESCAPE = auto()
    SPACE = auto()
    BACKSPACE = auto()
    TAB = auto()
    OTHER = auto()


class EventType(Enum):
    """The kinds of input the game reacts to."""

    QUIT = auto()
    KEY_DOWN = auto()
    KEY_UP = auto()


@dataclass(frozen=True)
class Event:
    """One input event.

    Attributes:
        type: What happened.
        key: Which named key, or ``Key.OTHER`` for anything unnamed.
        char: The printable character the key produced, or ``""``. Used for
            name entry and for letter-keyed cheats, so that callers never
            map key codes themselves.
    """

    type: EventType
    key: Key = Key.OTHER
    char: str = ""


_KEY_MAP: Final[dict[int, Key]] = {
    pygame.K_UP: Key.UP,
    pygame.K_w: Key.UP,
    pygame.K_DOWN: Key.DOWN,
    pygame.K_s: Key.DOWN,
    pygame.K_LEFT: Key.LEFT,
    pygame.K_a: Key.LEFT,
    pygame.K_RIGHT: Key.RIGHT,
    pygame.K_d: Key.RIGHT,
    pygame.K_RETURN: Key.ENTER,
    pygame.K_KP_ENTER: Key.ENTER,
    pygame.K_ESCAPE: Key.ESCAPE,
    pygame.K_SPACE: Key.SPACE,
    pygame.K_BACKSPACE: Key.BACKSPACE,
    pygame.K_TAB: Key.TAB,
}


class GfxError(Exception):
    """Raised when the display itself cannot be created."""


def _scale_nearest(source: pygame.Surface, size: int) -> pygame.Surface:
    """Resize a square sprite with a nearest-neighbour loop.

    ``pygame.transform.scale`` has no MLX counterpart, so the resampling is
    written out here. It runs once per sprite per size, at load time, and the
    result is cached, so the cost never reaches the frame loop.

    Args:
        source: The loaded sprite.
        size: Target width and height, in pixels.

    Returns:
        A new surface of ``size`` by ``size`` pixels, alpha preserved.
    """
    src_w, src_h = source.get_size()
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    if src_w == 0 or src_h == 0:
        return out
    for y in range(size):
        sy = min(src_h - 1, y * src_h // size)
        for x in range(size):
            sx = min(src_w - 1, x * src_w // size)
            out.set_at((x, y), source.get_at((sx, sy)))
    return out


class Gfx:
    """Window, drawing primitives, input and frame pacing."""

    def __init__(self, width: int, height: int,
                 title: str = GAME_TITLE) -> None:
        """Open the window.

        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            title: Window caption.

        Raises:
            GfxError: If pygame cannot initialise a display.
        """
        try:
            # Only the two subsystems in use. pygame.init() would also start
            # pygame.mixer, which the subject forbids, and which prints audio
            # driver errors on machines with no sound card.
            pygame.display.init()
            pygame.font.init()
            self._screen = pygame.display.set_mode((width, height))
        except pygame.error as exc:
            raise GfxError(f"cannot open a window: {exc}") from exc
        pygame.display.set_caption(title)
        self._clock = pygame.time.Clock()
        self._sprites: dict[tuple[str, int], pygame.Surface | None] = {}
        self._fills: dict[tuple[Color, int, int], pygame.Surface] = {}
        self._fonts: dict[int, pygame.font.Font] = {}
        self._closed = False

    # ---------------------------------------------------------------- window

    def screen_size(self) -> tuple[int, int]:
        """Return the window size in pixels."""
        width, height = self._screen.get_size()
        return width, height

    def resize(self, width: int, height: int) -> None:
        """Change the window size, keeping every cache.

        Args:
            width: New width in pixels.
            height: New height in pixels.
        """
        self._screen = pygame.display.set_mode((width, height))

    # --------------------------------------------------------------- drawing

    def fill_rect(self, color: Color, x: int, y: int,
                  width: int, height: int) -> None:
        """Fill a rectangle with a flat colour.

        Implemented as an offscreen surface that is filled once and then
        blitted, which is what ``mlx_new_image`` plus
        ``mlx_put_image_to_window`` does. ``pygame.draw.rect`` is not used.

        Args:
            color: RGB triple.
            x: Left edge in pixels.
            y: Top edge in pixels.
            width: Width in pixels; values below 1 draw nothing.
            height: Height in pixels; values below 1 draw nothing.
        """
        if width < 1 or height < 1:
            return
        key = (color, width, height)
        surface = self._fills.get(key)
        if surface is None:
            surface = pygame.Surface((width, height))
            surface.fill(color)
            self._fills[key] = surface
        self._screen.blit(surface, (x, y))

    def draw_sprite(self, rel_path: str, x: int, y: int, size: int) -> bool:
        """Draw a sprite, reporting whether it was available.

        The caller never holds an image object: it asks for a path and finds
        out whether anything was drawn. A missing, unreadable or corrupt file
        is remembered as absent, so a half-finished ``assets/`` directory
        costs one failed open per sprite for the whole run.

        Args:
            rel_path: Path below ``assets/``, as built by the helpers in
                ``pacman.constants``.
            x: Left edge in pixels.
            y: Top edge in pixels.
            size: Width and height in pixels.

        Returns:
            True if the sprite was drawn, False if the caller should draw its
            own fallback.
        """
        if size < 1:
            return False
        key = (rel_path, size)
        if key not in self._sprites:
            self._sprites[key] = self._load(rel_path, size)
        surface = self._sprites[key]
        if surface is None:
            return False
        self._screen.blit(surface, (x, y))
        return True

    def has_sprite(self, rel_path: str, size: int) -> bool:
        """Return True if a sprite can be drawn at this size.

        Args:
            rel_path: Path below ``assets/``.
            size: Width and height in pixels.
        """
        key = (rel_path, size)
        if key not in self._sprites:
            self._sprites[key] = self._load(rel_path, size)
        return self._sprites[key] is not None

    def _load(self, rel_path: str, size: int) -> pygame.Surface | None:
        """Load and scale one sprite, or return None if unavailable."""
        full = os.path.join(ASSETS_DIR, rel_path)
        if not os.path.isfile(full):
            return None
        try:
            raw = pygame.image.load(full).convert_alpha()
        except pygame.error:
            return None
        if raw.get_size() == (size, size):
            return raw
        return _scale_nearest(raw, size)

    # ------------------------------------------------------------------ text

    def _font(self, size: int) -> pygame.font.Font:
        """Return a cached font of the given pixel size."""
        font = self._fonts.get(size)
        if font is None:
            font = pygame.font.Font(None, size)
            self._fonts[size] = font
        return font

    def draw_text(self, text: str, x: int, y: int,
                  size: int, color: Color) -> None:
        """Draw a line of text with its top-left corner at ``(x, y)``.

        Args:
            text: The string to draw; an empty string draws nothing.
            x: Left edge in pixels.
            y: Top edge in pixels.
            size: Font size in pixels.
            color: RGB triple.
        """
        if not text:
            return
        surface = self._font(size).render(text, True, color)
        self._screen.blit(surface, (x, y))

    def text_size(self, text: str, size: int) -> tuple[int, int]:
        """Return the pixel width and height a string would occupy.

        Needed to centre menu entries and to place the name-entry caret.

        Args:
            text: The string to measure.
            size: Font size in pixels.
        """
        width, height = self._font(size).size(text)
        return width, height

    # ----------------------------------------------------------------- input

    def poll_events(self) -> list[Event]:
        """Drain the input queue, translated out of pygame's vocabulary.

        Returns:
            The events since the previous call, oldest first.
        """
        events: list[Event] = []
        for raw in pygame.event.get():
            if raw.type == pygame.QUIT:
                events.append(Event(EventType.QUIT))
            elif raw.type in (pygame.KEYDOWN, pygame.KEYUP):
                kind = (
                    EventType.KEY_DOWN
                    if raw.type == pygame.KEYDOWN
                    else EventType.KEY_UP
                )
                char = getattr(raw, "unicode", "")
                if not char.isprintable():
                    char = ""
                events.append(
                    Event(
                        kind,
                        _KEY_MAP.get(raw.key, Key.OTHER),
                        char,
                    )
                )
        return events

    # ------------------------------------------------------------- the frame

    def present(self) -> float:
        """Show the finished frame and wait for the next one.

        Returns:
            Seconds elapsed since the previous call, capped at a tenth of a
            second so that a stall cannot teleport entities through walls.
        """
        pygame.display.flip()
        return min(self._clock.tick(FPS) / 1000.0, 0.1)

    def close(self) -> None:
        """Shut the window down. Safe to call more than once."""
        if not self._closed:
            self._closed = True
            pygame.quit()

    def __enter__(self) -> "Gfx":
        """Allow use as a context manager, so the window always closes."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the window on leaving the ``with`` block."""
        self.close()
