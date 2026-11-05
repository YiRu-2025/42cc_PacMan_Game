"""Turns game state into pixels.

The renderer owns the art policy: which sprite belongs to what, where a cell
lands on screen, and what to draw when a sprite has not been painted yet.
Every missing sprite degrades to a flat colour from
``constants.FALLBACK_COLORS``, so the game is playable and legible with an
empty ``assets/`` directory and improves one file at a time.

It reads game state and never writes to it. The protocols below are the
contract with the gameplay modules: anything satisfying them can be drawn,
which also makes the renderer testable without a running game.
"""

from typing import Final, Protocol, Sequence

from pacman import maze_loader
from pacman.constants import (
    FALLBACK_COLORS,
    FORCE_PLACEHOLDERS,
    HUD_HEIGHT,
    PLACEHOLDER_INSET,
    SPRITE_PATHS,
    WALL_ORDER,
    Color,
    Direction,
    Layer,
    cell_size_for,
    ghost_sprite,
    player_sprite,
    wall_sprite,
)
from pacman.gfx import Gfx
from pacman.maze_loader import Grid

Cell = tuple[int, int]

WALL_THICKNESS_RATIO: Final[float] = 0.18
"""How thick a placeholder wall edge is, as a fraction of the cell size."""

HUD_PADDING: Final[int] = 12
HUD_TEXT_SIZE: Final[int] = 28

_WALL_CODE: Final[dict[Direction, int]] = {
    Direction.NORTH: maze_loader.NORTH,
    Direction.EAST: maze_loader.EAST,
    Direction.SOUTH: maze_loader.SOUTH,
    Direction.WEST: maze_loader.WEST,
}
"""The only place that bridges Direction and the maze package's bit codes."""

_GHOST_LAYERS: Final[tuple[Layer, ...]] = (
    Layer.GHOST_0,
    Layer.GHOST_1,
    Layer.GHOST_2,
    Layer.GHOST_3,
)


# --------------------------------------------------------------------------
# What the renderer needs to be given. Read-only by construction: these
# declare attributes, never methods that change anything.
# --------------------------------------------------------------------------


class PlayerView(Protocol):
    """The player, as the renderer sees it."""

    x: int
    y: int
    facing: Direction
    frame: int


class GhostView(Protocol):
    """One ghost, as the renderer sees it.

    ``state`` is ``"normal"``, ``"frightened"`` or ``"dead"``, matching the
    sprite naming in ``pacman.constants``.
    """

    x: int
    y: int
    index: int
    state: str
    frame: int


class LevelView(Protocol):
    """One level's maze and remaining pickups."""

    grid: Grid
    pacgums: frozenset[Cell]
    super_pacgums: frozenset[Cell]


class GameView(Protocol):
    """The scoreboard state shown in the HUD."""

    score: int
    lives: int
    level_number: int
    time_left: float
    frightened: bool


class Renderer:
    """Draws a level, its entities and the HUD into a window."""

    def __init__(self, gfx: Gfx) -> None:
        """Create a renderer bound to one window.

        Args:
            gfx: The graphics layer to draw through.
        """
        self._gfx = gfx
        self._cell = 0
        self._origin = (0, 0)

    # ---------------------------------------------------------------- layout

    def layout(self, grid: Grid) -> tuple[int, int]:
        """Work out the cell size and maze origin for a maze.

        Call once per level, before drawing. The maze is centred in the area
        below the HUD, so a maze smaller than the window is framed rather
        than pinned to a corner.


        """
        self._cell = cell_size_for(grid.width, grid.height)
        maze_w = grid.width * self._cell
        maze_h = grid.height * self._cell
        screen_w, screen_h = self._gfx.screen_size()
        free_w = max(screen_w, maze_w)
        free_h = max(screen_h - HUD_HEIGHT, maze_h)
        self._origin = (
            (free_w - maze_w) // 2,
            HUD_HEIGHT + (free_h - maze_h) // 2,
        )
        return maze_w, maze_h + HUD_HEIGHT

    def cell_rect(self, x: int, y: int) -> tuple[int, int, int]:
        """Return the pixel position and size of one grid cell."""

        return (
            self._origin[0] + x * self._cell,
            self._origin[1] + y * self._cell,
            self._cell,
        )

    # --------------------------------------------------------------- drawing

    def draw(
        self,
        level: LevelView,
        player: PlayerView,
        ghosts: Sequence[GhostView],
        game: GameView,
    ) -> None:
        """Draw one complete frame.

        Args:
            level: The maze and its remaining pickups.
            player: The player's position and animation state.
            ghosts: Every ghost, in any order.
            game: The values shown in the HUD.
        """
        if self._cell < 1:
            self.layout(level.grid)
        self._draw_background(game.frightened)
        self._draw_maze(level.grid, game.frightened)
        self._draw_pickups(level)
        self._draw_ghosts(ghosts)
        self._draw_player(player)
        self._draw_hud(game)

    def _draw_background(self, frightened: bool) -> None:
        """Fill the window with the paper ground.

        A sprite cannot be tinted without alpha blending, which MLX has no
        counterpart for, so the frightened state swaps in a second, darker
        sheet of paper instead of overlaying a mask.
        """
        layer = Layer.PAPER_INVERTED if frightened else Layer.PAPER
        width, height = self._gfx.screen_size()
        self._fill(layer, 0, 0, width, height)
        path = SPRITE_PATHS.get(layer)
        if path is None or FORCE_PLACEHOLDERS:
            return
        tile = max(self._cell, 1)
        for top in range(0, height, tile):
            for left in range(0, width, tile):
                if not self._gfx.draw_sprite(path, left, top, tile):
                    return

    def _draw_maze(self, grid: Grid, frightened: bool) -> None:
        """Draw every cell: floor first, then its wall tile.

        The floor follows the frightened state for the same reason the
        background does: without alpha blending there is no way to tint the
        corridors, so a second floor is swapped in instead. Drawing the
        normal floor here would paint over the darkened background and the
        power-pellet effect would be invisible.
        """
        floor_layer = Layer.FLOOR_INVERTED if frightened else Layer.FLOOR
        floor_path = SPRITE_PATHS.get(floor_layer)
        for y in range(grid.height):
            for x in range(grid.width):
                left, top, size = self.cell_rect(x, y)
                walls = self._walls_at(grid, x, y)
                if (x, y) in grid.walkable:
                    if not self._sprite(floor_path, left, top, size):
                        self._fill(floor_layer, left, top, size, size)
                if self._sprite(wall_sprite(walls), left, top, size):
                    continue
                self._draw_wall_edges(walls, left, top, size)

    @staticmethod
    def _walls_at(grid: Grid, x: int, y: int) -> frozenset[Direction]:
        """Return the sides of a cell that a mover cannot cross."""
        return frozenset(d for d in WALL_ORDER if not grid.is_open(x, y, _WALL_CODE[d]))

    def _draw_wall_edges(
        self, walls: frozenset[Direction], left: int, top: int, size: int
    ) -> None:
        """Draw a cell's walls as flat bars, one per blocked side.

        This is the placeholder path. Bars rather than a filled cell keep the
        maze readable before any artwork exists: corridors stay open and
        walls read as lines, the way an arcade maze does.
        """
        if len(walls) == 4:
            self._fill(Layer.WALL, left, top, size, size)
            return
        thickness = max(2, int(size * WALL_THICKNESS_RATIO))
        for side in walls:
            if side is Direction.NORTH:
                self._fill(Layer.WALL, left, top, size, thickness)
            elif side is Direction.SOUTH:
                self._fill(Layer.WALL, left, top + size - thickness, size, thickness)
            elif side is Direction.WEST:
                self._fill(Layer.WALL, left, top, thickness, size)
            else:
                self._fill(Layer.WALL, left + size - thickness, top, thickness, size)

    def _draw_pickups(self, level: LevelView) -> None:
        """Draw the remaining pacgums and super-pacgums."""
        for layer in (Layer.PACGUM, Layer.SUPER_PACGUM):
            cells = level.pacgums if layer is Layer.PACGUM else level.super_pacgums
            path = SPRITE_PATHS.get(layer)
            for x, y in cells:
                left, top, size = self.cell_rect(x, y)
                if not self._sprite(path, left, top, size):
                    self._inset_fill(layer, left, top, size)

    def _draw_ghosts(self, ghosts: Sequence[GhostView]) -> None:
        """Draw every ghost in its current state."""
        for ghost in ghosts:
            left, top, size = self.cell_rect(ghost.x, ghost.y)
            index = ghost.index % len(_GHOST_LAYERS)
            path = ghost_sprite(index, ghost.frame, ghost.state)
            if self._sprite(path, left, top, size):
                continue
            if ghost.state == "frightened":
                layer = Layer.GHOST_FRIGHTENED
            elif ghost.state == "dead":
                layer = Layer.GHOST_DEAD
            else:
                layer = _GHOST_LAYERS[index]
            self._inset_fill(layer, left, top, size)

    def _draw_player(self, player: PlayerView) -> None:
        """Draw the player at its current facing and frame."""
        left, top, size = self.cell_rect(player.x, player.y)
        path = player_sprite(player.facing, player.frame)
        if not self._sprite(path, left, top, size):
            self._inset_fill(Layer.PLAYER, left, top, size)

    def _draw_hud(self, game: GameView) -> None:
        """Draw the banner across the top: score, lives, level and time."""
        width, _ = self._gfx.screen_size()
        banner = SPRITE_PATHS.get(Layer.BANNER)
        if not self._sprite(banner, 0, 0, HUD_HEIGHT):
            self._fill(Layer.BANNER, 0, 0, width, HUD_HEIGHT)

        seconds = max(0, int(game.time_left))
        left_text = f"SCORE {game.score}"
        mid_text = f"LEVEL {game.level_number}"
        right_text = f"LIVES {game.lives}   TIME {seconds // 60}:" f"{seconds % 60:02d}"
        color = FALLBACK_COLORS[Layer.TEXT]
        top = (HUD_HEIGHT - HUD_TEXT_SIZE) // 2

        self._gfx.draw_text(left_text, HUD_PADDING, top, HUD_TEXT_SIZE, color)
        mid_w, _ = self._gfx.text_size(mid_text, HUD_TEXT_SIZE)
        self._gfx.draw_text(mid_text, (width - mid_w) // 2, top, HUD_TEXT_SIZE, color)
        right_w, _ = self._gfx.text_size(right_text, HUD_TEXT_SIZE)
        self._gfx.draw_text(
            right_text, width - right_w - HUD_PADDING, top, HUD_TEXT_SIZE, color
        )

    # ---------------------------------------------------------------- helpers

    def _sprite(self, path: str | None, x: int, y: int, size: int) -> bool:
        """Try to draw a sprite, honouring the placeholder override."""
        if FORCE_PLACEHOLDERS or path is None:
            return False
        return self._gfx.draw_sprite(path, x, y, size)

    def _fill(self, layer: Layer, x: int, y: int, width: int, height: int) -> None:
        """Fill a rectangle with a layer's fallback colour."""
        self._gfx.fill_rect(self._color(layer), x, y, width, height)

    def _inset_fill(self, layer: Layer, left: int, top: int, size: int) -> None:
        """Fill a layer's placeholder, shrunk by its inset.

        Insets are what keep placeholder mode legible: pickups stay small
        dots, entities nearly fill their cell, and nothing touches the walls.
        """
        inset = PLACEHOLDER_INSET.get(layer, 0.0)
        margin = int(size * inset)
        side = max(2, size - 2 * margin)
        self._fill(layer, left + margin, top + margin, side, side)

    @staticmethod
    def _color(layer: Layer) -> Color:
        """Return a layer's fallback colour, defaulting to the text colour."""
        return FALLBACK_COLORS.get(layer, FALLBACK_COLORS[Layer.TEXT])
