"""CheatMode: persistent / one-shot
Persistant toggles(invincible, freeze, speed): booleans that stay
    on until switched off again.
One shot request(skip, extra life): stored until Game consumes them,
    so one key press has an effect exactly once instead of every frame.
"""
from dataclasses import dataclass, field
from enum import Enum


class CheatMode(Enum):
    SKIP = "skip"
    INVINCIBLE = "invincible"
    FREEZE = "freeze"
    LIFE = "life"
    SPEED = "speed"


Cheat_KEYS: dict[str, tuple[CheatMode, str]] = {
    "1": (CheatMode.SKIP, "1: skip level (win it immediately)"),
    "2": (CheatMode.INVINCIBLE, "2: toggle invincibility"),
    "3": (CheatMode.FREEZE, "3: toggle ghost freeze"),
    "4": (CheatMode.LIFE, "4: add one life"),
    "5": (CheatMode.SPEED, "5: toggle speed boost"),
}


@dataclass
class Cheat:
    enabled: bool = False
    invincible: bool = False
    freeze: bool = False
    speed: bool = False

    # pending one-shot requests, init=False keep them out of constructor
    # only handle_key may create them
    _skip: bool = field(default=False, init=False, repr=False)
    _lives: int = field(default=0, init=False, repr=False)

    def set_enabled(self, value: bool) -> None:
        """switch cheat mode on/off"""
        self.enabled = value
        if not value:
            self.invincible = False
            self.freeze = False
            self.speed = False
            self._skip = False
            self._lives = 0

    def toggle_enabled(self) -> None:
        self.set_enabled(not self.enabled)

    def handle_key(self, character: str) -> bool:
        """apply the cheat bound to a typed character.
        args:
            character: the character of a key press
        returns:
            ture if cheat mode is on and character is a cheat key,
            so the caller knows the key was consumed.
        """
        if not self.enabled or character not in Cheat_KEYS:
            return False
        cheat = Cheat_KEYS[character][0]
        if cheat is CheatMode.SKIP:
            self._skip = True
        elif cheat is CheatMode.LIFE:
            self._lives += 1
        elif cheat is CheatMode.INVINCIBLE:
            self.invincible = not self.invincible
        elif cheat is CheatMode.FREEZE:
            self.freeze = not self.freeze
        elif cheat is CheatMode.SPEED:
            self.speed = not self.speed
        return True

    def consume_skip(self) -> bool:
        """Return True once per skip request, then clear it."""
        skip, self._skip = self._skip, False
        return skip

    def consume_lives(self) -> int:
        """Return the extra lives requested since the last call."""
        lives, self._lives = self._lives, 0
        return lives

    def active_labels(self) -> list[str]:
        """Return names of the toggles currently on, for the HUD."""
        if not self.enabled:
            return []
        labels = []
        if self.invincible:
            labels.append("INVINCIBLE")
        if self.freeze:
            labels.append("FREEZE")
        if self.speed:
            labels.append("SPEED")
        return labels
