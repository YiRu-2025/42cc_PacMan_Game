"""Graphics and rendering subsystem for Pac-Man.

Exports the display engine, window abstraction, event types and high-level
game renderer so that other modules only need to import from `pacman.gfx`.
"""

from pacman.gfx.gfx import (
    Color,
    Event,
    EventType,
    Gfx,
    GfxError,
    Key,
)
from pacman.gfx.renderer import (
    GameView,
    GhostView,
    LevelView,
    PlayerView,
    Renderer,
)

__all__ = [
    # Engine & Window primitives
    "Gfx",
    "GfxError",
    "Event",
    "EventType",
    "Key",
    "Color",
    # Renderer & View Protocols
    "Renderer",
    "PlayerView",
    "GhostView",
    "LevelView",
    "GameView",
]
