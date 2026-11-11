"""The player: moves only while a key is held, or once per tap.

Input model
    _held   direction keys currently down, oldest first; the last one wins.
    _tap    the most recent press, kept until one step has consumed it, so
            a key released before the next step still moves one cell.
The player never carries on by itself: no held key and no pending tap
means no movement.
"""
from typing import Any

from pacman.constants import Direction
from pacman.entities.base import Entity
from pacman.level import Level, Pickup
from pacman.maze_loader import Cell


class Player(Entity):
    def __init__(self, cell: Cell, speed: float = 8.0) -> None:
        super().__init__(cell, speed)
        self._held: list[Direction] = []
        self._tap: Direction | None = None

    # ---- input (called by the play scene) ----
    def press(self, d: Direction) -> None:
        """A direction key went down."""
        if d in self._held:
            self._held.remove(d)
        self._held.append(d)
        self._tap = d

    def release(self, d: Direction) -> None:
        """A direction key came up."""
        if d in self._held:
            self._held.remove(d)

    def release_all(self) -> None:
        """Forget all input (pause, focus loss)."""
        self._held.clear()
        self._tap = None

    def copy_input(self, other: "Player") -> None:
        """Keep held keys across a respawn or a new level."""
        self._held = list(other._held)

    # ---- simulation ----
    @property
    def wish(self) -> Direction | None:
        """Where the player wants to go right now, if anywhere."""
        return self._held[-1] if self._held else self._tap

    def update(self, dt: float, level: Level, *ctx: Any) -> list[Any]:
        if self.wish is None:
            # Idle: stay "ready", so the next press moves at once.
            self._cooldown = 0.0
            self.prev = self.cell
            return []
        return super().update(dt, level, *ctx)

    def step(self, level: Level) -> Pickup:
        d = self.wish
        self._tap = None
        if d is not None and self.can_move(level.grid, d):
            self.move(d)
            return level.eat(self.cell)
        return Pickup.NONE      # blocked: stay, keep facing
