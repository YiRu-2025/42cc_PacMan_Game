"""
Set the generated Grid with pacgums, super-pacgums and ghost, player

structure:

Pickup (Enum)       None/PACGUM/SUPER_PACGUM
Level (dataclass)   grid, player, ghost, pacums, super_pacgums
    - eat(cell)     delete and return Pickup
    - remain        the remaining amount
    - cleared       all eat?
_beside(grid, corner, taken) -> Cell
build_level(grid) -> Level
"""


from pacman.maze_loader import Grid, Cell
from dataclasses import dataclass, field
from enum import Enum


class Pickup(Enum):
    """The collecting type of a cell"""

    NONE = "none"
    PACGUM = "pacgum"
    SUPGUM = "super_pacgum"


@dataclass
class Level:
    """
    starting layout of the maze plus the pickups still on the board.

    ghosts[i] is both the starting cell and the respawn cell of ghost i.
    """

    grid: Grid
    player: Cell
    ghosts: list[Cell]
    pacgums: set[Cell] = field(default_factory=set)
    supgums: set[Cell] = field(default_factory=set)

    def eat(self, cell: Cell) -> Pickup:
        """ Remove and report whatever pickup lies on "cell" ."""
        if cell in self.pacgums:
            self.pacgums.remove(cell)
            return Pickup.PACGUM
        if cell in self.supgums:
            self.supgums.remove(cell)
            return Pickup.SUPGUM
        return Pickup.NONE

    @property
    def remain(self) -> int:
        "number of pickups left on the board"
        return len(self.pacgums) + len(self.supgums)

    @property
    def cleared(self) -> bool:
        "if all pickup are eaten, return true"
        return self.remain == 0


def _beside(grid: Grid, corner: Cell, taken: set[Cell]) -> Cell:
    """ return a free walkable neighbour of corner.
    falls back to the corner itself if every neighbour is taken
    """
    for cell in grid.neighbours(*corner):
        if cell not in taken:
            return cell
    return corner


def build_level(grid: Grid) -> Level:
    "lay out pickups and spawn point on a generated maze."
    corners = grid.corners()
    player = grid.centre()

    taken = set(corners) | {player}
    ghosts: list[Cell] = []
    for corner in corners:
        spawn = _beside(grid, corner, taken)
        taken.add(spawn)
        ghosts.append(spawn)
    supgums = set(corners) - {player}
    pacgums = set(grid.walkable) - supgums - {player}
    return Level(grid=grid, player=player, ghosts=ghosts, pacgums=pacgums, supgums=supgums) # noqa
