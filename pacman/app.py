"""Application wiring and the main loop.

This module is the only one that knows the whole program: it reads the
configuration, opens the window, loads the highscore table, and runs the
scene stack until it empties. It is also the only place where the menu and
the gameplay package meet, through the two callables it puts in the
``Context``, so neither of those imports the other.

Start-up order matters. The window is sized for the largest level in the
configuration before any scene exists, so the window never changes size
mid-game; and the highscore table is loaded before the menu appears, so the
menu can show it immediately.

"""
import sys
from typing import Final

from pacman.config import Config, load_config


