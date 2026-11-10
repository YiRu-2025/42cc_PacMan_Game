"""player's operation: set direction, buffer
    current position: direction
    target position: buffered
    the priority of step:
        - able to go target direction -> take it and store as current direction
        - or able to go current direction -> keep on going
        - or stop (will crash the wall)
    check if eat the gums
"""
from pacman.entities.base import Entity
from pacman.maze_loader import Cell
from pacman.constants import Direction
from pacman.level import Level, Pickup


class Player(Entity):
    def __init__(self, cell: Cell, speed: float = 8.0) -> None:
        super().__init__(cell, speed)
        self.buffered: Direction | None = None

    def set_direction(self, d: Direction) -> None:
        """called on key press: only remember the wish."""
        self.buffered = d

    def step(self, level: Level) -> Pickup:
        grid = level.grid
        if self.can_move(grid, self.buffered):
            self.move(self.buffered)
        elif self.can_move(grid, self.direction):
            self.move(self.direction)
        else:
            self.direction = None  # blocked: stay at current place
        return level.eat(self.cell)
