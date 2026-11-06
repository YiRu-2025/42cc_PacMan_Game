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

from pacman.constants import (
    FALLBACK_COLORS,
    FORCE_PLACEHOLDERS,
    HUD_HEIGHT,
    PAPER_TILE_SIZE,
    PLACEHOLDER_INSET,
    PLAYER_TRANSFORM,
    SPRITE_PATHS,
    WALL_BLOCK_SPRITE,
    Color,
    Direction,
    Layer,
    cell_size_for,
    ghost_body_sprite,
    ghost_hat_sprite,
    ghost_sprite,
    ghost_state_sprite,
    player_base_sprite,
    player_sprite,
    wall_edge_sprite,
    wall_sprite,
)
from pacman.gfx import Gfx
from pacman.maze_loader import Grid

Cell = tuple[int, int]

WALL_THICKNESS_RATIO: Final[float] = 0.18
"""How thick a placeholder wall edge is, as a fraction of the cell size."""

HUD_PADDING: Final[int] = 12
HUD_TEXT_SIZE: Final[int] = 28

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
    """The player, as the renderer sees it.

    Declared as read-only properties, not plain attributes: the renderer
    never writes to what it draws, and a Protocol with writable members
    would reject the frozen snapshots the play scene hands it.
    """

    @property
    def x(self) -> int:
        """Column the player occupies."""

    @property
    def y(self) -> int:
        """Row the player occupies."""

    @property
    def facing(self) -> Direction:
        """Direction the player is moving in."""

    @property
    def frame(self) -> int:
        """Animation frame index."""


class GhostView(Protocol):
    """One ghost, as the renderer sees it."""

    @property
    def x(self) -> int:
        """Column the ghost occupies."""

    @property
    def y(self) -> int:
        """Row the ghost occupies."""

    @property
    def index(self) -> int:
        """Which of the four ghosts this is, counting from 0."""

    @property
    def state(self) -> str:
        """``"normal"``, ``"frightened"`` or ``"dead"``, matching the
        sprite naming in ``pacman.constants``."""

    @property
    def frame(self) -> int:
        """Animation frame index."""


class LevelView(Protocol):
    """One level's maze and remaining pickups."""

    @property
    def grid(self) -> Grid:
        """The maze being played."""

    @property
    def pacgums(self) -> frozenset[Cell]:
        """Cells still holding an ordinary pickup."""

    @property
    def super_pacgums(self) -> frozenset[Cell]:
        """Cells still holding a power pellet."""


class GameView(Protocol):
    """The scoreboard state shown in the HUD."""

    @property
    def score(self) -> int:
        """Points so far."""

    @property
    def lives(self) -> int:
        """Lives remaining."""

    @property
    def level_number(self) -> int:
        """Current level, counting from 1."""

    @property
    def time_left(self) -> float:
        """Seconds left on the level timer."""

    @property
    def frightened(self) -> bool:
        """True while a power pellet is in effect, which recolours the
        whole sheet rather than tinting the ghosts alone."""


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

        Args:
            grid: The maze about to be drawn.

        Returns:
            The window size, in pixels, that suits this maze. The caller may
            pass it to ``Gfx.resize``; drawing is correct either way, because
            the origin is recomputed from the window actually in use.
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
        """Return the pixel position and size of one grid cell.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            ``(left, top, size)`` in pixels.
        """
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

        The texture is tiled at ``PAPER_TILE_SIZE`` rather than at the cell
        size, so a seamless sheet reads as one sheet instead of repeating
        once per corridor cell.
        """
        layer = Layer.PAPER_INVERTED if frightened else Layer.PAPER
        width, height = self._gfx.screen_size()
        self._fill(layer, 0, 0, width, height)
        path = SPRITE_PATHS.get(layer)
        if path is None or FORCE_PLACEHOLDERS:
            return
        for top in range(0, height, PAPER_TILE_SIZE):
            for left in range(0, width, PAPER_TILE_SIZE):
                if not self._gfx.draw_sprite(
                    path, left, top, PAPER_TILE_SIZE, PAPER_TILE_SIZE
                ):
                    return

    def _draw_maze(self, grid: Grid, frightened: bool) -> None:
        """Draw every cell: floor first, then its walls.

        The floor follows the frightened state for the same reason the
        background does: without alpha blending there is no way to tint the
        corridors, so a second floor is swapped in instead.

        When a paper texture exists but no floor sprite does, the floor is
        skipped entirely and the paper shows through the corridors. That is
        the usual case for a drawn game: one background texture, no second
        image repeated in every cell.
        """
        floor_layer = Layer.FLOOR_INVERTED if frightened else Layer.FLOOR
        floor_path = SPRITE_PATHS.get(floor_layer)
        paper_path = SPRITE_PATHS.get(
            Layer.PAPER_INVERTED if frightened else Layer.PAPER
        )
        skip_floor = (
            not FORCE_PLACEHOLDERS
            and floor_path is not None
            and paper_path is not None
            and not self._gfx.has_sprite(floor_path, self._cell)
            and self._gfx.has_sprite(paper_path, PAPER_TILE_SIZE, PAPER_TILE_SIZE)
        )
        for y in range(grid.height):
            for x in range(grid.width):
                left, top, size = self.cell_rect(x, y)
                walls = grid.walls_at(x, y)
                if (x, y) in grid.walkable and not skip_floor:
                    if not self._sprite(floor_path, left, top, size):
                        self._fill(floor_layer, left, top, size, size)
                if self._sprite(wall_sprite(walls), left, top, size):
                    continue
                self._draw_wall_edges(walls, left, top, size)

    def _draw_wall_edges(
        self, walls: frozenset[Direction], left: int, top: int, size: int
    ) -> None:
        """Draw a cell's walls one side at a time.

        The second of three art levels. A whole-cell tile from
        ``wall_sprite`` wins when it exists; failing that, each blocked side
        is drawn with its own edge sprite, which needs four images for the
        entire maze; failing that, flat bars.

        Bars rather than a filled cell keep the maze readable before any
        artwork exists: corridors stay open and walls read as lines.
        """
        if len(walls) == 4:
            if self._sprite(WALL_BLOCK_SPRITE, left, top, size):
                return
            self._fill(Layer.WALL, left, top, size, size)
            return
        thickness = max(2, int(size * WALL_THICKNESS_RATIO))
        for side in walls:
            if self._sprite(wall_edge_sprite(side), left, top, size):
                continue
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
        """Draw every ghost in its current state.

        Three art levels, cheapest last. A finished per-ghost image wins;
        failing that, a shared body with a per-ghost overlay on top, which
        is why the overlay must carry the colour: tinting the shared body
        would need alpha blending; failing that, a coloured block.

        Frightened and dead forms are shared by all four ghosts, so two
        small sets cover both states.
        """
        for ghost in ghosts:
            left, top, size = self.cell_rect(ghost.x, ghost.y)
            index = ghost.index % len(_GHOST_LAYERS)
            if self._sprite(
                ghost_sprite(index, ghost.frame, ghost.state), left, top, size
            ):
                continue
            if ghost.state in ("frightened", "dead"):
                if self._sprite(
                    ghost_state_sprite(ghost.state, ghost.frame), left, top, size
                ):
                    continue
                layer = (
                    Layer.GHOST_FRIGHTENED
                    if ghost.state == "frightened"
                    else Layer.GHOST_DEAD
                )
                self._inset_fill(layer, left, top, size)
                continue
            if self._sprite(ghost_body_sprite(ghost.frame), left, top, size):
                self._sprite(ghost_hat_sprite(index), left, top, size)
                continue
            self._inset_fill(_GHOST_LAYERS[index], left, top, size)

    def _draw_player(self, player: PlayerView) -> None:
        """Draw the player at its current facing and frame.

        A file drawn for this exact facing wins. Failing that, the eastward
        frames are turned or mirrored by ``PLAYER_TRANSFORM``, so three
        drawn images cover all four directions instead of twelve.
        """
        left, top, size = self.cell_rect(player.x, player.y)
        if self._sprite(player_sprite(player.facing, player.frame), left, top, size):
            return
        turns, flip_x = PLAYER_TRANSFORM.get(player.facing, (0, False))
        base = player_base_sprite(player.frame)
        if not FORCE_PLACEHOLDERS and self._gfx.draw_sprite(
            base, left, top, size, size, turns, flip_x
        ):
            return
        self._inset_fill(Layer.PLAYER, left, top, size)

    def _draw_hud(self, game: GameView) -> None:
        """Draw the banner across the top: score, lives, level and time."""
        width, _ = self._gfx.screen_size()
        banner = SPRITE_PATHS.get(Layer.BANNER)
        if (
            FORCE_PLACEHOLDERS
            or banner is None
            or not self._gfx.draw_sprite(banner, 0, 0, width, HUD_HEIGHT)
        ):
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
