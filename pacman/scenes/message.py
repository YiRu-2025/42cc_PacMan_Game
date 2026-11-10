"""A one-screen notice: a heading, a few lines, and any key to go back.

Used wherever a screen is expected but is not written yet, and for the
plain win and lose verdicts. Keeping it here means the application never
has to crash, or silently do nothing, because a scene is missing.
"""

from pacman.constants import FALLBACK_COLORS, Layer
from pacman.gfx import Event, EventType
from pacman.scenes.base import Context, Pop, Scene, Transition


class MessageScene(Scene):
    """A heading with optional body lines, dismissed by any key."""

    heading_size: int = 52
    body_size: int = 28
    line_height: int = 36

    def __init__(self, context: Context, heading: str, *lines: str) -> None:
        """Build the notice.

            context: The shared state.
            heading: The large line at the top.
            lines: Further lines, drawn under the heading.
        """
        super().__init__(context)
        self.heading = heading
        self.lines = [line for line in lines if line]

    def handle_event(self, event: Event) -> Transition | None:
        """Leave the screen on any key press."""
        if event.type is EventType.KEY_DOWN:
            return Pop()
        return None

    def draw(self) -> None:
        """Draw the heading and the body, centred."""
        gfx = self.context.gfx
        width, height = gfx.screen_size()
        gfx.fill_rect(FALLBACK_COLORS[Layer.PAPER], 0, 0, width, height)

        block = self.heading_size + len(self.lines) * self.line_height
        top = (height - block) // 2
        head_w, _ = gfx.text_size(self.heading, self.heading_size)
        gfx.draw_text(
            self.heading,
            (width - head_w) // 2,
            top,
            self.heading_size,
            FALLBACK_COLORS[Layer.TEXT],
        )

        top += self.heading_size + self.line_height // 2
        for index, line in enumerate(self.lines):
            line_w, _ = gfx.text_size(line, self.body_size)
            gfx.draw_text(
                line,
                (width - line_w) // 2,
                top + index * self.line_height,
                self.body_size,
                FALLBACK_COLORS[Layer.TEXT_DIM],
            )

        hint = "press any key"
        hint_w, _ = gfx.text_size(hint, self.body_size)
        gfx.draw_text(
            hint,
            (width - hint_w) // 2,
            height - 60,
            self.body_size,
            FALLBACK_COLORS[Layer.TEXT_DIM],
        )
