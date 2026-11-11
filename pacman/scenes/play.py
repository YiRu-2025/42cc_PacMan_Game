"""The gameplay screen: keys in, one tick of the simulation, one frame out.

This scene holds no game rules. It owns a ``Game``, forwards input to it,
advances it once per frame, and hands its state to the renderer. Everything
that decides what happens — movement, scoring, collisions, level flow —
lives in ``pacman.game`` and the entity classes, where it can be unit
tested without a window.


"""

from dataclasses import dataclass

from pacman.constants import (
    ANIMATION_FPS,
    GHOST_FRAME_COUNT,
    PLAYER_FRAME_COUNT,
    Direction,
)
from pacman.entities.ghost import Ghost, GhostState
from pacman.entities.player import Player
from pacman.game import Game, Phase
from pacman.gfx import Event, EventType, Key
from pacman.level import Level
from pacman.maze_loader import Grid
from pacman.scenes.base import (
    Context,
    Finish,
    GameResult,
    Push,
    Scene,
    Transition,
)
from pacman.scenes.pause import PauseScene

ARROW_KEYS: dict[Key, Direction] = {
    Key.UP: Direction.NORTH,
    Key.RIGHT: Direction.EAST,
    Key.DOWN: Direction.SOUTH,
    Key.LEFT: Direction.WEST,
}

GHOST_STATE_NAMES: dict[GhostState, str] = {
    GhostState.CHASE: "normal",
    GhostState.FRIGHTENED: "frightened",
    GhostState.DEAD: "dead",
}

# --------------------------------------------------------------------------
# Views: the simulation's state in the shape the renderer asked for.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LevelFrame:
    """One level as the renderer sees it."""

    grid: Grid
    pacgums: frozenset[tuple[int, int]]
    super_pacgums: frozenset[tuple[int, int]]


@dataclass(frozen=True)
class PlayerFrame:
    """The player as the renderer sees it."""

    x: int
    y: int
    facing: Direction
    frame: int


@dataclass(frozen=True)
class GhostFrame:
    """One ghost as the renderer sees it."""

    x: int
    y: int
    index: int
    state: str
    frame: int


@dataclass(frozen=True)
class GameFrame:
    """The HUD values as the renderer sees them."""

    score: int
    lives: int
    level_number: int
    time_left: float
    frightened: bool


class PlayScene(Scene):
    """Runs one game, from level 1 until it is won or lost."""

    def __init__(self, context: Context) -> None:
        """Start a game.

        Args:
            context: The shared state.

        Raises:
            MazeError: If the first maze cannot be generated. The caller in
                ``pacman.app`` catches it, because only the application
                knows what to show instead.
        """
        super().__init__(context)
        self.game = Game(context.config)
        self.elapsed = 0.0
        self._laid_out = -1

    # ----------------------------------------------------------------- input
    def handle_event(self, event: Event) -> Transition | None:
        direction = ARROW_KEYS.get(event.key)
        if event.type is EventType.KEY_UP:
            if direction is not None:
                self.game.player.release(direction)
            return None
        if event.type is not EventType.KEY_DOWN:
            return None
        if event.key is Key.ESCAPE:
            return Push(PauseScene(self.context))
        if direction is not None:
            self.game.player.press(direction)
            return None
        if event.char:
            self.game.cheat.handle_key(event.char)
        return None

    def on_enter(self) -> None:
        # a key released while paused is never seen by this scene
        self.game.player.release_all()

    def on_exit(self) -> None:
        self.game.player.release_all()

    # ------------------------------------------------------------- the frame

    def update(self, dt: float) -> Transition | None:
        """Advance the simulation and report the end of the game.

            dt: Seconds since the previous frame.
            A ``Finish`` once the game is won or lost, otherwise None.
        """
        self.elapsed += dt
        self.game.update(dt)
        if self.game.phase is Phase.PLAYING:
            return None
        return Finish(GameResult(
            score=self.game.score,
            won=self.game.phase is Phase.WON,
            level_reached=self.game.level_index,
        ))

    def draw(self) -> None:
        """Lay out the maze if it changed, then draw one frame."""
        if self._laid_out != self.game.level_index:
            self.context.renderer.layout(self.game.level.grid)
            self._laid_out = self.game.level_index
        self.context.renderer.draw(
            self._level_frame(self.game.level),
            self._player_frame(self.game.player),
            [self._ghost_frame(i, g)
             for i, g in enumerate(self.game.ghosts)],
            self._game_frame(),
        )

    # ----------------------------------------------------------------- views

    @staticmethod
    def _level_frame(level: Level) -> LevelFrame:
        """Translate a Level into what the renderer reads."""
        return LevelFrame(
            grid=level.grid,
            pacgums=frozenset(level.pacgums),
            super_pacgums=frozenset(level.supgums),
        )

    def _player_frame(self, player: Player) -> PlayerFrame:
        """Translate the player, inventing the animation frame.

        A player with no direction yet faces east, which is what the
        artwork is drawn for; the other three facings are derived from it.
        """
        x, y = player.cell
        return PlayerFrame(
            x=x,
            y=y,
            facing=player.direction or Direction.EAST,
            frame=self._frame(PLAYER_FRAME_COUNT),
        )

    def _ghost_frame(self, index: int, ghost: Ghost) -> GhostFrame:
        """Translate one ghost, including its sprite-state name."""
        x, y = ghost.cell
        return GhostFrame(
            x=x,
            y=y,
            index=index,
            state=GHOST_STATE_NAMES.get(ghost.state, "normal"),
            frame=self._frame(GHOST_FRAME_COUNT),
        )

    def _game_frame(self) -> GameFrame:
        """Translate the HUD values.

        ``frightened`` drives the whole-screen colour change, so it is true
        while any ghost is still frightened rather than only at the moment
        the pellet is eaten.
        """
        return GameFrame(
            score=self.game.score,
            lives=self.game.lives,
            level_number=self.game.level_index,
            time_left=self.game.time_left,
            frightened=any(g.state is GhostState.FRIGHTENED
                           for g in self.game.ghosts),
        )

    def _frame(self, count: int) -> int:
        """Return the current animation frame for a cycle of ``count``.

            count: How many frames the cycle has.
            An index in ``range(count)``.
        """
        if count < 2:
            return 0
        return int(self.elapsed * ANIMATION_FPS) % count
