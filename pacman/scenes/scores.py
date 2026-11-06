"""The highscore table, shown from the main menu and after a game."""

from pacman.constants import FALLBACK_COLORS, HIGHSCORE_LIMIT, Color, Layer
from pacman.gfx import Event, EventType, Gfx
from pacman.scenes.base import Context, Pop, Scene, Transition

TITLE_SIZE: int = 52
ROW_SIZE: int = 30
ROW_HEIGHT: int = 40
TABLE_WIDTH: int = 420
"""Width of the rank/name/score columns taken together, in pixels."""


class ScoresScene(Scene):
    """Ten rows of rank, name and score, dismissed by any key.

        highlight: A 1-based rank to pick out, used right after a game so
            the player can see where their score landed. 0 highlights
            nothing.
    """

    def __init__(self, context: Context, highlight: int = 0) -> None:
        """Build the screen.

            context: The shared state.
            highlight: The rank to emphasise, or 0 for none.
        """
        super().__init__(context)
        self.highlight = highlight

    def handle_event(self, event: Event) -> Transition | None:
        """Leave on any key press.

            event: The input event.
            A ``Pop`` on a key press, otherwise None.
        """
        if event.type is EventType.KEY_DOWN:
            return Pop()
        return None

    def draw(self) -> None:
        """Draw the heading and the rows, names left, scores right."""
        gfx = self.context.gfx
        entries = self.context.highscores.entries
        width, height = gfx.screen_size()
        text = FALLBACK_COLORS[Layer.TEXT]
        dim = FALLBACK_COLORS[Layer.TEXT_DIM]

        gfx.fill_rect(FALLBACK_COLORS[Layer.PAPER], 0, 0, width, height)

        title = "Highscores"
        title_w, _ = gfx.text_size(title, TITLE_SIZE)
        rows = max(len(entries), 1)
        top = max(TITLE_SIZE * 2,
                  (height - rows * ROW_HEIGHT) // 2)
        gfx.draw_text(title, (width - title_w) // 2, top - TITLE_SIZE * 2,
                      TITLE_SIZE, text)

        if not entries:
            empty = "no scores yet"
            empty_w, _ = gfx.text_size(empty, ROW_SIZE)
            gfx.draw_text(empty, (width - empty_w) // 2, top, ROW_SIZE, dim)
            self._draw_hint(gfx, width, height, dim)
            return

        left = (width - TABLE_WIDTH) // 2
        right = left + TABLE_WIDTH
        for index, entry in enumerate(entries[:HIGHSCORE_LIMIT]):
            rank = index + 1
            colour = text if rank == self.highlight else dim
            row_top = top + index * ROW_HEIGHT
            gfx.draw_text(f"{rank:>2}", left, row_top, ROW_SIZE, colour)
            gfx.draw_text(entry.name, left + 56, row_top, ROW_SIZE, colour)
            score = str(entry.score)
            score_w, _ = gfx.text_size(score, ROW_SIZE)
            gfx.draw_text(score, right - score_w, row_top, ROW_SIZE, colour)

        self._draw_hint(gfx, width, height, dim)

    @staticmethod
    def _draw_hint(gfx: Gfx, width: int, height: int,
                   colour: Color) -> None:
        """Draw the "press any key" line along the bottom."""
        hint = "press any key"
        hint_w, _ = gfx.text_size(hint, ROW_SIZE)
        gfx.draw_text(hint, (width - hint_w) // 2, height - 60,
                      ROW_SIZE, colour)
