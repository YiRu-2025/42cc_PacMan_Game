"""The end-of-game screen: the verdict, then the name for the table.

Shown whether the player won or lost, as the subject requires. Keys are
filtered as they arrive, so the field can never hold a character the
highscore table would later drop; a player who types an accent simply sees
nothing happen, rather than watching their name change after the fact.
"""

from pacman.constants import FALLBACK_COLORS, NAME_CHARSET, Layer
from pacman.constants import NAME_MAX_LENGTH
from pacman.gfx import Event, EventType, Key
from pacman.highscores import is_name_complete, sanitize_name
from pacman.scenes.base import Context, GameResult, Pop, Replace
from pacman.scenes.base import Scene, Transition
from pacman.scenes.scores import ScoresScene

TITLE_SIZE: int = 52
BODY_SIZE: int = 30
FIELD_SIZE: int = 40
FIELD_WIDTH: int = 360
FIELD_HEIGHT: int = 58
CARET_PERIOD: float = 1.0
"""Seconds for one full blink of the caret."""


class NameEntryScene(Scene):
    """Announce the result and take a name for the highscore table."""

    def __init__(self, context: Context, result: GameResult) -> None:
        """Build the screen.

            context: The shared state.
            result: What the finished session produced.
        """
        super().__init__(context)
        self.result = result
        self.name = ""
        self.elapsed = 0.0
        self.placed = context.highscores.qualifies(result.score)

    def update(self, dt: float) -> Transition | None:
        """Advance the caret blink.

            dt: Seconds since the previous frame.

           This screen only ends on a key press.
        """
        self.elapsed += dt
        return None

    def handle_event(self, event: Event) -> Transition | None:
        """Type a name, delete a character, confirm, or skip."""
        if event.type is not EventType.KEY_DOWN:
            return None
        if event.key is Key.ESCAPE:
            return Pop()
        if event.key is Key.BACKSPACE:
            self.name = self.name[:-1]
            return None
        if event.key is Key.ENTER:
            return self._confirm()
        if self._accepts(event.char):
            self.name += event.char
        return None

    def _accepts(self, char: str) -> bool:
        """Return True if a typed character belongs in the field.

        A leading space is refused, since it would be stripped on save and
        the field would then disagree with the table.

        """
        return (
            len(char) == 1
            and char in NAME_CHARSET
            and len(self.name) < NAME_MAX_LENGTH
            and not (char == " " and not self.name)
        )

    def _confirm(self) -> Transition | None:
        """Record the score and move to the table.

            The highscore table with the new row picked out, or None if the
            name is not usable yet.
        """
        trimmed = self.name.strip()
        if not is_name_complete(trimmed):
            return None
        rank = self.context.highscores.add(trimmed, self.result.score)
        self.context.highscores.save()
        return Replace(ScoresScene(self.context, highlight=rank))

    def draw(self) -> None:
        """Draw the verdict, the score, the field and the hints."""
        gfx = self.context.gfx
        width, height = gfx.screen_size()
        text = FALLBACK_COLORS[Layer.TEXT]
        dim = FALLBACK_COLORS[Layer.TEXT_DIM]
        gfx.fill_rect(FALLBACK_COLORS[Layer.PAPER], 0, 0, width, height)

        verdict = "You win" if self.result.won else "Game over"
        verdict_w, _ = gfx.text_size(verdict, TITLE_SIZE)
        gfx.draw_text(verdict, (width - verdict_w) // 2, height // 2 - 190,
                      TITLE_SIZE, text)

        summary = (f"score {self.result.score}    "
                   f"level {self.result.level_reached}")
        summary_w, _ = gfx.text_size(summary, BODY_SIZE)
        gfx.draw_text(summary, (width - summary_w) // 2, height // 2 - 120,
                      BODY_SIZE, dim)

        standing = ("a top ten score" if self.placed
                    else "not a top ten score")
        standing_w, _ = gfx.text_size(standing, BODY_SIZE)
        gfx.draw_text(standing, (width - standing_w) // 2,
                      height // 2 - 80, BODY_SIZE, dim)

        self._draw_field(width, height)

        hint = "enter to save, escape to skip"
        hint_w, _ = gfx.text_size(hint, BODY_SIZE)
        gfx.draw_text(hint, (width - hint_w) // 2, height // 2 + 90,
                      BODY_SIZE, dim)

    def _draw_field(self, width: int, height: int) -> None:
        """Draw the name box, the typed name and the blinking caret."""
        gfx = self.context.gfx
        text = FALLBACK_COLORS[Layer.TEXT]
        left = (width - FIELD_WIDTH) // 2
        top = height // 2 - 10

        gfx.fill_rect(FALLBACK_COLORS[Layer.BANNER], left, top,
                      FIELD_WIDTH, FIELD_HEIGHT)
        gfx.fill_rect(text, left, top + FIELD_HEIGHT - 3, FIELD_WIDTH, 3)

        shown = self.name or ""
        name_w, name_h = gfx.text_size(shown, FIELD_SIZE)
        name_x = left + (FIELD_WIDTH - name_w) // 2
        name_y = top + (FIELD_HEIGHT - name_h) // 2
        gfx.draw_text(shown, name_x, name_y, FIELD_SIZE, text)

        if self.elapsed % CARET_PERIOD < CARET_PERIOD / 2:
            gfx.fill_rect(text, name_x + name_w + 3, name_y,
                          3, max(name_h, FIELD_SIZE // 2))

    @property
    def saved_name(self) -> str:
        """The name as the table would store it. Used by the tests."""
        return sanitize_name(self.name)
