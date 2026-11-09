"""Scene framework and concrete screen implementations for Pac-Man.

Exports the base Scene classes, transitions, shared context, helper factories,
and all concrete scene types (including the core gameplay scene).
"""

from pacman.scenes.base import (
    Context,
    Finish,
    GameResult,
    MenuItem,
    MenuScene,
    Pop,
    Push,
    Quit,
    Replace,
    Scene,
    Transition,
    load_optional,
)
from pacman.scenes.instructions import InstructionsScene
from pacman.scenes.menu import MainMenuScene
from pacman.scenes.message import MessageScene
from pacman.scenes.name_entry import NameEntryScene
from pacman.scenes.pause import PauseScene
from pacman.scenes.play import PlayScene
from pacman.scenes.scores import ScoresScene

__all__ = [
    # Base framework & State
    "Scene",
    "Context",
    "GameResult",
    "MenuItem",
    "MenuScene",
    "load_optional",
    # Transitions
    "Transition",
    "Push",
    "Pop",
    "Replace",
    "Finish",
    "Quit",
    # Concrete Scenes
    "PlayScene",
    "MainMenuScene",
    "PauseScene",
    "ScoresScene",
    "NameEntryScene",
    "MessageScene",
    "InstructionsScene",
]
