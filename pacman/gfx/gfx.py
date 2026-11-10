"""The only module that touches pygame.

Everything the rest of the game needs from the graphics layer goes through
``Gfx``: a window, image blitting, text, event polling and frame pacing.
Events are translated into this module's own ``Event`` and ``Key`` types, so
no other module imports pygame, directly or indirectly.

MLX equivalence
---------------
The subject allows only pygame functions that have an MLX counterpart. The
calls used here, and their equivalents:

====================================  =====================================
pygame                                MLX
====================================  =====================================
``display.set_mode``                  ``mlx_new_window``
``display.set_caption``               window title argument
``display.flip``                      end of ``mlx_loop`` iteration
``image.load`` / ``convert_alpha``    ``mlx_xpm_file_to_image``
``Surface.blit``                      ``mlx_put_image_to_window``
``Surface.fill`` on an offscreen
  surface, then blit                  ``mlx_new_image`` + pixel fill + put
``Surface.set_at`` / ``get_at``       ``mlx_pixel_put`` / image buffer read
``font.Font.render`` + blit           ``mlx_string_put``
``event.get``                         ``mlx_hook`` / ``mlx_loop_hook``
``time.Clock.tick``                   frame pacing inside ``mlx_loop``
====================================  =====================================
"""

import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final

import pygame

from pacman.constants import (
    ASSETS_DIR,
    BODY_FONT,
    BODY_FONT_FAMILIES,
    BODY_FONT_SCALE,
    FONT_DIR,
    FPS,
    GAME_TITLE,
    MAX_FRAME_DT,
    TITLE_FONT,
    TITLE_FONT_MIN_SIZE,
    TITLE_FONT_SCALE,
)

Color = tuple[int, int, int]

SpriteKey = tuple[str, int, int, int, bool]
"""Path, width, height, quarter turns, mirrored.

Every part has to be in the key: the same file is wanted at several sizes
and several orientations, and a key that left any of them out would hand
back the player facing the wrong way.
"""


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


def _resample(source: pygame.Surface, width: int, height: int) -> pygame.Surface:
    """Resize a sprite with a nearest-neighbour loop.

    ``pygame.transform.scale`` has no MLX counterpart, so the resampling is
    written out here. It runs once per sprite per size, at load time, and the
    result is cached, so the cost never reaches the frame loop.

    Width and height are separate because not every sprite is a cell: the
    HUD banner is stretched the full width of the window at the height of
    the band.

        source: The loaded sprite.
        width: Target width in pixels.
        height: Target height in pixels.

        A new surface of the requested size, alpha preserved.
    """
    src_w, src_h = source.get_size()
    out = pygame.Surface((width, height), pygame.SRCALPHA)
    if src_w == 0 or src_h == 0:
        return out
    for y in range(height):
        sy = min(src_h - 1, y * src_h // height)
        for x in range(width):
            sx = min(src_w - 1, x * src_w // width)
            out.set_at((x, y), source.get_at((sx, sy)))
    return out


def _transform(source: pygame.Surface, turns: int, flip_x: bool) -> pygame.Surface:
    """Rotate by quarter turns and optionally mirror, without pygame.

    ``pygame.transform.rotate`` and ``.flip`` have no MLX counterpart, but a
    quarter turn is pure index arithmetic over an image buffer, which is
    exactly what one would write in C against ``mlx_new_image``. No pixel is
    interpolated, so the result is exact rather than resampled.

    This is what lets one set of eastward frames serve all four facings:
    three drawn images instead of twelve.

        source: The sprite to transform.
        turns: Quarter turns clockwise, 0 to 3.
        flip_x: Mirror horizontally, applied after the rotation.

        The transformed sprite, or ``source`` itself when nothing changes.
    """
    turns %= 4
    if turns == 0 and not flip_x:
        return source
    width, height = source.get_size()
    out_w, out_h = (height, width) if turns % 2 else (width, height)
    out = pygame.Surface((out_w, out_h), pygame.SRCALPHA)
    for y in range(out_h):
        for x in range(out_w):
            ox = out_w - 1 - x if flip_x else x
            if turns == 0:
                sx, sy = ox, y
            elif turns == 1:
                sx, sy = y, height - 1 - ox
            elif turns == 2:
                sx, sy = width - 1 - ox, height - 1 - y
            else:
                sx, sy = width - 1 - y, ox
            out.set_at((x, y), source.get_at((sx, sy)))
    return out


class Gfx:
    """Window, drawing primitives, input and frame pacing."""

    def __init__(self, width: int, height: int, title: str = GAME_TITLE) -> None:
        """Open the window.

        width: Window width in pixels.
        height: Window height in pixels.
        title: Window caption.

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
        self._sprites: dict[SpriteKey, pygame.Surface | None] = {}
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

        width: New width in pixels.
        height: New height in pixels.
        """
        self._screen = pygame.display.set_mode((width, height))

    # --------------------------------------------------------------- drawing

    def fill_rect(self, color: Color, x: int, y: int, width: int, height: int) -> None:
        """Fill a rectangle with a flat colour.

        Implemented as an offscreen surface that is filled once and then
        blitted, which is what ``mlx_new_image`` plus
        ``mlx_put_image_to_window`` does. ``pygame.draw.rect`` is not used.

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

    def draw_sprite(
        self,
        rel_path: str,
        x: int,
        y: int,
        width: int,
        height: int | None = None,
        turns: int = 0,
        flip_x: bool = False,
    ) -> bool:
        """Draw a sprite, reporting whether it was available.

        The caller never holds an image object: it asks for a path and finds
        out whether anything was drawn. A missing, unreadable or corrupt file
        is remembered as absent, so a half-finished ``assets/`` directory
        costs one failed open per sprite for the whole run.

            rel_path: Path below ``assets/``, as built by the helpers in
                ``pacman.constants``.
            x: Left edge in pixels.
            y: Top edge in pixels.
            width: Target width in pixels.
            height: Target height in pixels; defaults to ``width``, which
                suits the square sprites that sit in one grid cell.
            turns: Quarter turns clockwise to apply before drawing.
            flip_x: Mirror horizontally before drawing.

            True if the sprite was drawn, False if the caller should draw its
            own fallback.
        """
        surface = self._get(rel_path, width, height, turns, flip_x)
        if surface is None:
            return False
        self._screen.blit(surface, (x, y))
        return True

    def has_sprite(self, rel_path: str, width: int, height: int | None = None) -> bool:
        """Return True if a sprite file exists and can be drawn.

        Lets the renderer choose between art and placeholder paths once per
        level instead of once per cell.

            rel_path: Path below ``assets/``.
            width: Target width in pixels.
            height: Target height in pixels; defaults to ``width``.
        """
        return self._get(rel_path, width, height, 0, False) is not None

    def _get(
        self, rel_path: str, width: int, height: int | None, turns: int, flip_x: bool
    ) -> pygame.Surface | None:
        """Return a cached, transformed, resized sprite, or None."""
        tall = width if height is None else height
        if width < 1 or tall < 1:
            return None
        key: SpriteKey = (rel_path, width, tall, turns % 4, flip_x)
        if key not in self._sprites:
            self._sprites[key] = self._load(rel_path, width, tall, turns, flip_x)
        return self._sprites[key]

    def _load(
        self, rel_path: str, width: int, height: int, turns: int, flip_x: bool
    ) -> pygame.Surface | None:
        """Load, transform and scale one sprite, or None if unavailable."""
        full = os.path.join(ASSETS_DIR, rel_path)
        if not os.path.isfile(full):
            return None
        try:
            raw = pygame.image.load(full).convert_alpha()
        except pygame.error:
            return None
        raw = _transform(raw, turns, flip_x)
        if raw.get_size() == (width, height):
            return raw
        return _resample(raw, width, height)

    # ------------------------------------------------------------------ text

    def _font(self, size: int) -> pygame.font.Font:
        """Return a cached font of the given pixel size."""
        font = self._fonts.get(size)
        if font is None:
            font = self._load_font(size)
            self._fonts[size] = font
        return font

    def _load_font(self, size: int) -> pygame.font.Font:
        """Pick a face by size and correct for how it is cut.

        Titles take the arcade face, everything smaller the terminal one,
        so no scene has to know which font it wants. The scale factors are
        there because the two faces disagree about what a pixel size looks
        like; correcting here keeps every scene's numbers unchanged.

        A missing file is not an error: the built-in font is always there,
        the same way a missing sprite falls back to a flat colour.

            size: The size the caller asked for, before correction.
        """
        if size >= TITLE_FONT_MIN_SIZE:
            name, scale = TITLE_FONT, TITLE_FONT_SCALE
        else:
            name, scale = BODY_FONT, BODY_FONT_SCALE
        path = os.path.join(ASSETS_DIR, FONT_DIR, name)
        if os.path.isfile(path):
            try:
                return pygame.font.Font(path, max(8, round(size * scale)))
            except (pygame.error, OSError):
                pass
        if size < TITLE_FONT_MIN_SIZE:
            system = pygame.font.match_font(BODY_FONT_FAMILIES)
            if system is not None:
                return pygame.font.Font(system, size)
        return pygame.font.Font(None, size)

    def draw_text(self, text: str, x: int, y: int, size: int, color: Color) -> None:
        """Draw a line of text with its top-left corner at ``(x, y)``.

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

            text: The string to measure.
            size: Font size in pixels.
        """
        width, height = self._font(size).size(text)
        return width, height

    # ----------------------------------------------------------------- input

    def poll_events(self) -> list[Event]:
        """Drain the input queue, translated out of pygame's vocabulary.

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
            Seconds elapsed since the previous call, capped at
            ``MAX_FRAME_DT`` so that a stall cannot teleport entities
            through walls. The same cap is applied again inside the game,
            which is deliberate: this one protects the loop, that one
            protects the simulation if it is ever driven from elsewhere.
        """
        pygame.display.flip()
        return min(self._clock.tick(FPS) / 1000.0, MAX_FRAME_DT)

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
