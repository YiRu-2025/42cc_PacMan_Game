"""The base of entity: Direction, Entity, Update"""
from abc import ABC, abstractmethod
from pacman.maze_loader import Cell, Grid
from pacman.constants import Direction
from pacman.level import Level
from typing import Any


class Entity(ABC):
    """Grid-based mover. Advances one cell every 1/speed seconds"""
    def __init__(self, cell: Cell, speed: float) -> None:
        self.cell = cell
        self.prev = cell
        self.direction: Direction | None = None
        self.speed = speed
        self._cooldown = 0.0

    def can_move(self, grid: Grid, d: Direction | None) -> bool:
        return d is not None and grid.is_open(*self.cell, d)

    def move(self, d: Direction) -> None:
        self.cell = self.cell[0] + d.dx, self.cell[1] + d.dy
        self.direction = d

    def reset(self, cell: Cell) -> None:
        self.cell = self.prev = cell
        self.direction = None
        self._cooldown = 0.0

    def update(self, dt: float, level: Level, *ctx: Any) -> list[Any]:
        """Run as many steps as dt allows, return each step's result."""
        results: list[Any] = []
        self._cooldown -= dt
        while self._cooldown <= 0:
            self._cooldown += 1 / self.speed
            self.prev = self.cell
            results.append(self.step(level, *ctx))
        return results

    @abstractmethod
    def step(self, level: Level, *ctx: Any) -> Any: ...
    """ *ctx make the distance table accessible to ghost but not to player"""
