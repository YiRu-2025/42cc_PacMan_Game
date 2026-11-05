"""three states machine of chase/frightened/dead, add timer
on each frame, only run once BFS from player's position, getting the dist disctionary shared by all ghosts. # noqa
for chase mode, choose the closest cell
for frightened, choose the longest cell
use one table for recording the distance
"""

from enum import Enum
from typing import Any
from pacman.entities.base import Entity
from pacman.maze_loader_2 import Cell, Grid
from pacman.level import Level
from collections import deque


class GhostState(Enum):
    CHASE = "chase"
    FRIGHTENED = "frightened"
    DEAD = "dead"


def distance_map(grid: Grid, start: Cell) -> dict[Cell, int]:
    """Return the BFS step count from ``start`` to every reachable cell.

    One call per frame is shared by all ghosts: chasing picks the
    neighbour with the smallest value, fleeing the largest.
    """
    dist = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for nxt in grid.neighbours(*cell):
            if nxt not in dist:
                dist[nxt] = dist[cell] + 1
                queue.append(nxt)
    return dist


class Ghost(Entity):
    def __init__(self, home: Cell, speed: float,
                 fright_factor: float, respawn_delay: float) -> None:
        super().__init__(home, speed)
        self.home = home
        self._base_speed = speed
        self._fright_factor = fright_factor
        self._respawn_delay = respawn_delay
        self.state = GhostState.CHASE
        self.timer = 0.0

    # state change: called by Game
    def frighten(self, duration: float) -> None:
        if self.state is GhostState.DEAD:
            return
        self.state = GhostState.FRIGHTENED
        self.timer = duration
        self.speed = self._base_speed * self._fright_factor

    def eaten(self) -> None:
        """after being eaten, the player is dead once
        the ghost should reset to home position."""
        self.state = GhostState.DEAD
        self.timer = self._respawn_delay
        self.reset(self.home)

    def _recover(self) -> None:
        self.state = GhostState.CHASE
        self.speed = self._base_speed

    # each frame
    def update(self, dt: float, level: Level, *ctx: Any) -> list[Any]:
        if self.state is not GhostState.CHASE:  # dead or frightened
            self.timer -= dt
            if self.timer <= 0:
                self._recover()  # -> chase
        if self.state is GhostState.DEAD:  # still dead: stay put
            return []
        return super().update(dt, level, *ctx)
