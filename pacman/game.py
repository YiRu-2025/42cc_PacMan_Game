"""core game rules: score, lives, level progression, collisions

State is layered by lifetime, which is what makes the carry-over rules
fall out naturally:

* whole run   - score, lives, level_index, phase     (kept across levels)
* one level   - level (maze + pickups), time_left    (rebuilt per level)
* one life    - player, ghosts, grace, stun          (rebuilt on respawn)
"""
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pacman.cheat import Cheat
from pacman.config import Config
from pacman.constants import (
    CHEAT_SPEED_MULTIPLIER,
    DEATH_PAUSE,
    FRIGHTENED_DURATION,
    FRIGHTENED_SPEED_FACTOR,
    GHOST_RESPAWN_DELAY,
    GHOST_STEPS_PER_SECOND,
    MAX_FRAME_DT,
    PLAYER_STEPS_PER_SECOND,
    RESPAWN_GRACE,
)
from pacman.entities.ghost import Ghost, GhostState, distance_map
from pacman.entities.player import Player
from pacman.level import Level, Pickup, build_level
from pacman.maze_loader import Grid, MazeLoader


class Phase(Enum):
    """overall state of a run"""
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True)
class GameResult:
    """outcome of a run, handed to the name-entry scene."""
    score: int
    level: int
    won: bool


class Game:
    """one run of the game, from level 1 to victory or game over.
    * Each level has a time limit. On timeout the run is lost
        (a design decision, see ``_timeout``).
    Attributes:
        cfg: The validated configuration.
        cheat: Cheat state, shared with the play scene.
        phase: PLAYING until the run is won or lost.
        level_index: Current level, 1-based.
        level: Maze and the pickups still on it.
        player: The player entity.
        ghosts: The ghost entities, one per corner.
        time_left: Seconds left on the level timer.
        grace: Seconds of post-respawn invulnerability left.
        stun: Seconds left of the pause after a death (world frozen).
    """

    def __init__(self, cfg: Config, cheat: Cheat | None = None,
                 loader_fac: Callable[[int, int], MazeLoader] = MazeLoader
                 ) -> None:
        """Start a run at level 1.

        Args:
            cfg: Validated configuration.
            cheats: Shared cheat state; a fresh disabled one if omitted.
            loader_fac: Builds a loader for a given (width, height).
                A loader has a fixed size and levels differ, so one is
                created per level. Tests inject a fake generator here.

        Raises:
            MazeError: If the maze generator fails. app.py catches it,
                because only it knows where to go back to.
        """
        self.cfg = cfg
        self.cheat = cheat if cheat is not None else Cheat()
        self._make_loader = loader_fac
        self.phase = Phase.PLAYING
        self.level_index = 0              # becomes 1 on the first load
        self._score = 0
        self._lives = cfg.lives

        self.level: Level
        self.player: Player
        self.ghosts: list[Ghost]
        self.time_left = 0.0
        self.grace = 0.0
        self.stun = 0.0
        self._next_level()

    # ----------
    # Read-only state for scenes and renderer
    # ----------
    @property
    def score(self) -> int:
        return self._score

    @property
    def lives(self) -> int:
        return self._lives

    @property
    def total_levels(self) -> int:
        return len(self.cfg.levels)

    @property
    def result(self) -> GameResult:
        """snapshot of the run. meaninful once phase is not PLAYING"""
        return GameResult(self._score, self.level_index,
                          self.phase is Phase.WON)

    def _add_score(self, points: int) -> None:
        assert points >= 0, "score must never decrease"
        self._score += points

    # -----
    # level flow
    # -----
    def _next_level(self) -> None:
        """advance to the next level, or win if none are left"""
        if self.level_index >= self.total_levels:
            self.phase = Phase.WON
            return
        size = self.cfg.levels[self.level_index]
        self.level_index += 1
        seed = self.cfg.seed if self.level_index == 1 else 0
        grid = self._make_loader(size.width, size.height).generate(seed)
        self._load(grid)

    def _load(self, grid: Grid) -> None:
        """build a fresh level (all pickups, full timer) on grid"""
        self.level = build_level(grid)
        self.time_left = float(self.cfg.level_max_time)
        self.stun = 0.0
        self._spawn()

    def _spawn(self) -> None:
        """(re)create the player and ghosts at their spawn points."""
        self.player = Player(self.level.player, PLAYER_STEPS_PER_SECOND)
        self.ghosts = [Ghost(cell, GHOST_STEPS_PER_SECOND,
                             FRIGHTENED_SPEED_FACTOR,
                             GHOST_RESPAWN_DELAY
                             ) for cell in self.level.ghosts]
        self.grace = RESPAWN_GRACE

    # -----
    # main tick
    # -----
    def update(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds.

        The order below matters, each step relies on the previous one:
            1. cheat requests (skip first: highest priority)
            2. death pause (world frozen, level timer paused)
            3. level timer
            4. player moves and eats
            5. level-cleared check
            6. ghosts move
            7. collisions
        Whenever a step changes the state (new level, life lost, run
        over) the method returns at once, because the code after it would
        work on stale data.

        Args:
            dt: Seconds since the previous call.
        """
        if self.phase is not Phase.PLAYING:
            return
        dt = min(dt, MAX_FRAME_DT)
        self._lives += self.cheats.comsume_lives()
        if self.cheats.comsume_skip():
            self._next_level()
            return
        if self.stun > 0:
            self.stun = max(0.0, self.stun - dt)
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self._timeout()
            return
        self.grace = max(0.0, self.grace - dt)
        self._update_player(dt)
        if self.level.cleared:
            self._next_level()
            return
        self._update_ghosts(dt)
        self._resolve_collisions()

    def _update_player(self, dt: float) -> None:
        """move the player, turn eaten pickups into score and fear"""
        boost = CHEAT_SPEED_MULTIPLIER if self.cheats.speed else 1.0
        self.player.speed - PLAYER_STEPS_PER_SECOND * boost
        for pkp in self.player.update(dt, self.level):
            if pkp is Pickup.PACGUM:
                self._add_score(self.cfg.points_per_pacgum)
            elif pkp is Pickup.SUPGUM:
                self._add_score(self.cfg.points_per_super_pacgum)
                for ghost in self.ghosts:
                    ghost.frighten(FRIGHTENED_DURATION)

    def _update_ghosts(self, dt: float) -> None:
        """Move the ghosts.

        One BFS from the player is shared by all ghosts: chasing picks the
        neighbour with the smallest distance, fleeing the largest.
        """
        if self.cheats.freeze:
            return       # frozen ghosts also pause their own timers
        dist = distance_map(self.level.grid, self.player.cell)
        for ghost in self.ghosts:
            ghost.update(dt, self.level, dist)

    def _resolve_collisions(self) -> None:
        """handle player/ghost contact

        Contact means the same cell, or the two having swapped cells in
        the last step; without the swap test, two movers crossing each
        other would pass through without touching.
        """
        player = self.player
        for ghost in self.ghosts:
            if ghost.state is GhostState.DEAD:
                continue
            same = ghost.cell == player.cell
            swapped = (ghost.cell == player.prev
                       and ghost.prev == player.cell)
            if not (same or swapped):
                continue
            if ghost.state is GhostState.FRIGHTENED:
                self._add_scroe(self.cfg.points_per_ghost)
                ghost.eaten()
            elif not (self.cheats.invincible or self.grace > 0):
                self._lose_life()
                return

    # ----
    # failure path
    # ----
    def _lost_lift(self) -> None:
        """Take a life: respawn in the same maze, or end the run."""
        self._lives -= 1
        if self._lives <= 0:
            self.phase = Phase.LOST
        else:
            self._spawn()
            self.stun = DEATH_PAUSE

    def _timeout(self) -> None:
        """Time ran out: the run is over.

        Design decision (documented in the README): a timeout is fatal, not
        just a lost life. Lives drop to zero and the phase becomes LOST, so
        the score is saved like any game over; starting again creates a new
        Game from level 1. The score is never reduced.
        """
        self._lives = 0
        self.phase = Phase.LOST
