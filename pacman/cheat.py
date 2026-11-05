"""CheatMode: persistent / one-shot
Persistant toggles(invincible, freeze, speed): booleans that stay
    on until switched off again.
One shot request(skip, extra life): stored until Game consumes them,
    so one key press has an effect exactly once instead of every frame.
"""
from  dataclasses import dataclass, field
from enum import Enum


class CheatMode(Enum):
    SKIP = "skip"
    INVINCIBLE = "invincible"
    FREEZE = "freeze"
    LIFE = "life"
    SPEED = "speed"


CheatMode_KEYS: dict[str, tuple[CheatMode, str]] = {
    "1": (CheatMode.SKIP, "1: skip level (win it immediately)"),
    "2": (CheatMode.INVINCIBLE, "2: toggle invincibility"),
    "3": (CheatMode.FREEZE, "3: toggle ghost freeze"),
    "4": (CheatMode.LIFE, "4: add one life"),
    "5": (CheatMode.SPEED, "5: toggle speed boost"),
}

