"""Project-wide constants: directions, timing, layout and the art contract.

Nothing here depends on pygame or on the external maze package, so every
other module can import it freely.


The art contract at the bottom is deliberately tolerant. Every drawable
names a sprite file and a fallback colour; a missing or unreadable file
degrades to a flat coloured cell instead of an error. The game is therefore
fully playable with an empty ``assets/`` directory, and artwork can be
dropped in one file at a time.
"""

from enum import Enum
from typing import Final

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

GAME_TITLE: Final[str] = "Pac-Man"


# --------------------------------------------------------------------------
# Directions
# --------------------------------------------------------------------------


class Direction(Enum):
    """The four moves available on the grid.

    Each member carries its own ``(dx, dy)`` step. ``y`` grows downwards,
    matching the row-major maze layout.
    """
    NORTH = (0, -1)
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)

    @property
    def dx(self) -> int:
        """Horizontal step, in cells."""
        return self.value[0]

    @property
    def dy(self) -> int:
        """Vertical step, in cells."""
        return self.value[1]

    def opposite(self) -> "Direction":
        """Return the direction pointing the other way."""
        return _OPPOSITES[self]


_OPPOSITES: Final[dict[Direction, Direction]] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
}

WALL_ORDER: Final[tuple[Direction, ...]] = (
    Direction.NORTH,
    Direction.EAST,
    Direction.SOUTH,
    Direction.WEST,
)
"""Fixed order used to build wall-tile filenames, so names are stable."""


# --------------------------------------------------------------------------
# Timing (seconds unless stated otherwise)
# --------------------------------------------------------------------------

FPS: Final[int] = 60
PLAYER_STEPS_PER_SECOND: Final[float] = 6.0
GHOST_STEPS_PER_SECOND: Final[float] = 5.0
FRIGHTENED_DURATION: Final[float] = 7.0
GHOST_RESPAWN_DELAY: Final[float] = 5.0
DEATH_PAUSE: Final[float] = 1.5
CHEAT_SPEED_MULTIPLIER: Final[float] = 2.0

PLAYER_FRAME_COUNT: Final[int] = 3
GHOST_FRAME_COUNT: Final[int] = 2
ANIMATION_FPS: Final[float] = 6.0


# --------------------------------------------------------------------------
# Layout
#
# The cell size is computed at runtime, never hard-coded: the configuration
# file may ask for a 100x100 maze, which no screen can show at a readable
# cell size. Sprites are authored at TARGET_CELL_SIZE and scaled down when
# the maze is large; scaling down degrades far better than scaling up.
# --------------------------------------------------------------------------

MIN_CELL_SIZE: Final[int] = 16
TARGET_CELL_SIZE: Final[int] = 48
MAX_WINDOW_WIDTH: Final[int] = 1600
MAX_WINDOW_HEIGHT: Final[int] = 900
HUD_HEIGHT: Final[int] = 56
WINDOW_MARGIN: Final[int] = 16


def cell_size_for(width: int, height: int) -> int:
    """Return the largest readable cell size that fits a maze on screen.

    Args:
        width: Maze width, in cells.
        height: Maze height, in cells.

    Returns:
        A cell size in pixels, between MIN_CELL_SIZE and TARGET_CELL_SIZE.
        A maze too large to fit even at MIN_CELL_SIZE still returns
        MIN_CELL_SIZE; the caller is expected to scroll or letterbox rather
        than refuse to draw.
    """
    if width <= 0 or height <= 0:
        return TARGET_CELL_SIZE
    usable_w = MAX_WINDOW_WIDTH - 2 * WINDOW_MARGIN
    usable_h = MAX_WINDOW_HEIGHT - 2 * WINDOW_MARGIN - HUD_HEIGHT
    fit = min(usable_w // width, usable_h // height)
    return max(MIN_CELL_SIZE, min(TARGET_CELL_SIZE, fit))


# --------------------------------------------------------------------------
# Highscores
# --------------------------------------------------------------------------

HIGHSCORE_LIMIT: Final[int] = 10
NAME_MAX_LENGTH: Final[int] = 10

NAME_CHARSET: Final[frozenset[str]] = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789 "
)
"""Characters allowed in a player name.

An explicit whitelist, not ``str.isalnum()``: that method accepts accented
letters and CJK characters, which the subject's "alphanumeric" does not.
"""


# --------------------------------------------------------------------------
# Art contract
#
# One table, two columns: where a sprite lives, and what to draw when it is
# not there. Renaming or reorganising artwork means editing this section and
# nothing else.
# --------------------------------------------------------------------------

ASSETS_DIR: Final[str] = "assets"

FORCE_PLACEHOLDERS: Final[bool] = False
"""Set True to draw the whole game as flat colour, ignoring every sprite.

Useful while tuning gameplay, and as a last resort if the artwork fails to
load during the defense.
"""


class Layer(Enum):
    """Every kind of thing the renderer can draw.

    Used as the key for fallback colours, so an unfinished sprite still has
    a defined appearance.
    """

    PAPER = "paper"
    PAPER_INVERTED = "paper_inverted"
    WALL = "wall"
    FLOOR = "floor"
    FLOOR_INVERTED = "floor_inverted"
    PACGUM = "pacgum"
    PACGUM_EATEN = "pacgum_eaten"
    SUPER_PACGUM = "super_pacgum"
    PLAYER = "player"
    GHOST_0 = "ghost_0"
    GHOST_1 = "ghost_1"
    GHOST_2 = "ghost_2"
    GHOST_3 = "ghost_3"
    GHOST_FRIGHTENED = "ghost_frightened"
    GHOST_DEAD = "ghost_dead"
    BANNER = "banner"
    TEXT = "text"
    TEXT_DIM = "text_dim"


Color = tuple[int, int, int]

FALLBACK_COLORS: Final[dict[Layer, Color]] = {
    Layer.PAPER: (232, 220, 192),
    Layer.PAPER_INVERTED: (120, 52, 44),
    Layer.WALL: (38, 32, 28),
    Layer.FLOOR: (240, 230, 205),
    Layer.FLOOR_INVERTED: (138, 66, 54),
    Layer.PACGUM: (176, 134, 56),
    Layer.PACGUM_EATEN: (214, 202, 178),
    Layer.SUPER_PACGUM: (212, 166, 62),
    Layer.PLAYER: (226, 182, 72),
    Layer.GHOST_0: (158, 48, 42),
    Layer.GHOST_1: (176, 110, 138),
    Layer.GHOST_2: (70, 96, 128),
    Layer.GHOST_3: (178, 118, 56),
    Layer.GHOST_FRIGHTENED: (72, 68, 62),
    Layer.GHOST_DEAD: (198, 190, 172),
    Layer.BANNER: (198, 178, 144),
    Layer.TEXT: (42, 34, 28),
    Layer.TEXT_DIM: (126, 112, 92),
}
"""Flat colour drawn when a layer's sprite is missing.

Chosen to stay legible together: dark walls on pale paper, warm metallic
pickups, desaturated ghosts. A partially illustrated game still reads.
"""

PLACEHOLDER_INSET: Final[dict[Layer, float]] = {
    Layer.PACGUM: 0.38,
    Layer.PACGUM_EATEN: 0.40,
    Layer.SUPER_PACGUM: 0.22,
    Layer.PLAYER: 0.10,
    Layer.GHOST_0: 0.12,
    Layer.GHOST_1: 0.12,
    Layer.GHOST_2: 0.12,
    Layer.GHOST_3: 0.12,
    Layer.GHOST_FRIGHTENED: 0.12,
    Layer.GHOST_DEAD: 0.30,
}
"""How far a placeholder shrinks inside its cell, as a fraction of the size.

A layer absent from this table fills its cell completely. This is what keeps
colour-block mode readable: dots stay small, walls stay solid.
"""


# --------------------------------------------------------------------------
# Sprite paths, relative to ASSETS_DIR.
#
# These are pure string builders, not file lookups: they define the naming
# convention in one place. gfx.py is responsible for loading, caching, and
# falling back when a path does not exist.
# --------------------------------------------------------------------------

PAPER_TILE_SIZE: Final[int] = 256
"""Side of one paper tile, in pixels.

The background texture is tiled at its own scale rather than at the cell
size, so a seamless sheet does not repeat once per corridor cell.
"""

WALL_BLOCK_SPRITE: Final[str] = "walls/block.png"
"""Fully enclosed cell, used for the generator's sealed '42' pattern."""


SPRITE_PATHS: Final[dict[Layer, str]] = {
    Layer.PAPER: "paper/bg_paper.png",
    Layer.PAPER_INVERTED: "paper/bg_inverted.png",
    Layer.FLOOR: "paper/floor.png",
    Layer.FLOOR_INVERTED: "paper/floor_inverted.png",
    Layer.PACGUM: "pickups/pacgum.png",
    Layer.PACGUM_EATEN: "pickups/pacgum_eaten.png",
    Layer.SUPER_PACGUM: "pickups/super_pacgum.png",
    Layer.BANNER: "ui/banner.png",
}
"""Single-file sprites. Animated and parameterised ones use the builders."""


def wall_sprite(walls: frozenset[Direction]) -> str:
    """Return the whole-cell tile path for a cell's wall combination.

    Args:
        walls: The sides that are blocked.

    Returns:
        A path such as ``walls/wall_1010.png``, the four digits being
        north, east, south and west in that order.

    Drawing all sixteen gives the best joins, but none of them is required:
    the renderer falls back to the four edge pieces below, and then to flat
    bars, so artwork can stop at any of the three levels.
    """
    bits = "".join("1" if d in walls else "0" for d in WALL_ORDER)
    return f"walls/wall_{bits}.png"


def wall_edge_sprite(side: Direction) -> str:
    """Return the path for one wall edge, drawn along a single side.

    Four of these cover every maze: the renderer draws one per blocked
    side. This is the cheapest art level that still looks drawn rather than
    filled.

    Args:
        side: Which side of the cell the edge runs along.

    Returns:
        A path such as ``walls/edge_n.png``.
    """
    return f"walls/edge_{side.name[0].lower()}.png"


def player_sprite(facing: Direction, frame: int) -> str:
    """Return the path for a player frame drawn for a specific facing.

    Optional: when this file is absent the renderer derives the facing from
    ``player_base_sprite`` by rotating or mirroring, so three eastward
    frames cover all four directions.

    Args:
        facing: Direction the player is moving in.
        frame: Frame index, wrapped into ``range(PLAYER_FRAME_COUNT)``.

    Returns:
        A path such as ``player/player_e_0.png``.
    """
    letter = facing.name[0].lower()
    return f"player/player_{letter}_{frame % PLAYER_FRAME_COUNT}.png"


def player_base_sprite(frame: int) -> str:
    """Return the path for a player frame drawn facing east.

    Args:
        frame: Frame index, wrapped into ``range(PLAYER_FRAME_COUNT)``.

    Returns:
        A path such as ``player/player_0.png``.
    """
    return f"player/player_{frame % PLAYER_FRAME_COUNT}.png"


PLAYER_TRANSFORM: Final[dict[Direction, tuple[int, bool]]] = {
    Direction.EAST: (0, False),
    Direction.WEST: (0, True),
    Direction.NORTH: (3, False),
    Direction.SOUTH: (1, False),
}
"""How to derive each facing from the eastward frames: quarter turns
clockwise, then a horizontal mirror.

West is mirrored rather than turned so that a face stays upright. North and
south are turned, which suits a radially symmetric design; for a portrait
that must stay upright in every direction, draw the per-facing files that
``player_sprite`` names and these transforms are skipped.
"""


def ghost_sprite(index: int, frame: int, state: str = "normal") -> str:
    """Return the path for one ghost drawn as a single finished image.

    Optional: when absent the renderer composes the ghost from a shared
    body plus a per-ghost hat, or from a shared state sprite.

    Args:
        index: Ghost number, 0 to 3.
        frame: Frame index, wrapped into ``range(GHOST_FRAME_COUNT)``.
        state: ``"normal"``, ``"frightened"`` or ``"dead"``.

    Returns:
        A path such as ``ghosts/ghost_2_frightened_1.png``.
    """
    return (f"ghosts/ghost_{index}_{state}_"
            f"{frame % GHOST_FRAME_COUNT}.png")


def ghost_body_sprite(frame: int) -> str:
    """Return the path for the body all four ghosts share.

    Args:
        frame: Frame index, wrapped into ``range(GHOST_FRAME_COUNT)``.

    Returns:
        A path such as ``ghosts/body_1.png``.
    """
    return f"ghosts/body_{frame % GHOST_FRAME_COUNT}.png"


def ghost_hat_sprite(index: int) -> str:
    """Return the path for the overlay that identifies one ghost.

    Drawn on top of the shared body, so four small images give four
    distinguishable ghosts. Colour has to come from this overlay: tinting
    the body would need alpha blending, which MLX has no counterpart for.

    Args:
        index: Ghost number, 0 to 3.

    Returns:
        A path such as ``ghosts/hat_2.png``.
    """
    return f"ghosts/hat_{index}.png"


def ghost_state_sprite(state: str, frame: int) -> str:
    """Return the path for the frightened or dead form shared by all ghosts.

    Args:
        state: ``"frightened"`` or ``"dead"``.
        frame: Frame index, wrapped into ``range(GHOST_FRAME_COUNT)``.

    Returns:
        A path such as ``ghosts/frightened_0.png``.
    """
    return f"ghosts/{state}_{frame % GHOST_FRAME_COUNT}.png"


def digit_sprite(character: str) -> str:
    """Return the path for one HUD glyph drawn as an image.

    Args:
        character: A single character to render.

    Returns:
        A path such as ``ui/glyph_7.png``. Glyphs are optional; when the
        file is missing, gfx.py draws the character with a font instead.
    """
    return f"ui/glyph_{character.lower()}.png"
