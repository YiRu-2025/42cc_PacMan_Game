"""The in-game manual: controls, scoring and the cheat keys.

The cheat keys are read from ``constants.CHEAT_BINDINGS`` rather than
written out here, so a binding added to the cheat module appears on this
screen without anyone remembering to update it.
"""

from pacman.constants import CHEAT_BINDINGS, FALLBACK_COLORS, Color, Layer
from pacman.gfx import Event, EventType, Gfx
from pacman.scenes.base import Pop, Scene, Transition

TITLE_SIZE: int = 48
HEADING_SIZE: int = 30
ROW_SIZE: int = 26
ROW_HEIGHT: int = 32
SECTION_GAP: int = 20
KEY_COLUMN: int = 200
TOP_MARGIN: int = 36
BOTTOM_MARGIN: int = 44
"""Width of the key column, in pixels, before the description starts."""

CONTROLS: tuple[tuple[str, str], ...] = (
    ("arrows / WASD", "move"),
    ("escape", "pause, or go back"),
    ("enter / space", "choose"),
)


class InstructionsScene(Scene):
    """How to play, dismissed by any key."""

    def handle_event(self, event: Event) -> Transition | None:
        """Leave on any key press.

            event: The input event.
            A ``Pop`` on a key press, otherwise None.
        """
        if event.type is EventType.KEY_DOWN:
            return Pop()
        return None

    def draw(self) -> None:
        """Draw the title and the three sections, fitted to the window.

        The window is sized for the maze, which the configuration controls,
        so this screen cannot assume any particular height. Row spacing is
        computed from what is available and the sections are compressed
        rather than allowed to run off the bottom.
        """
        gfx = self.context.gfx
        config = self.context.config
        width, height = gfx.screen_size()
        text = FALLBACK_COLORS[Layer.TEXT]
        dim = FALLBACK_COLORS[Layer.TEXT_DIM]
        gfx.fill_rect(FALLBACK_COLORS[Layer.PAPER], 0, 0, width, height)

        scoring = (
            ("pacgum", str(config.points_per_pacgum)),
            ("super-pacgum", str(config.points_per_super_pacgum)),
            ("ghost", str(config.points_per_ghost)),
            ("lives", str(config.lives)),
            ("time per level", f"{config.level_max_time}s"),
        )
        sections = (
            ("Controls", CONTROLS),
            ("Scoring", scoring),
            ("Cheats", tuple(CHEAT_BINDINGS.items())),
        )

        title = "How to play"
        title_w, _ = gfx.text_size(title, TITLE_SIZE)
        gfx.draw_text(title, (width - title_w) // 2, TOP_MARGIN,
                      TITLE_SIZE, text)

        top = TOP_MARGIN + TITLE_SIZE + SECTION_GAP
        available = height - top - BOTTOM_MARGIN
        rows = sum(len(body) for _, body in sections)
        fixed = len(sections) * (HEADING_SIZE + 8 + SECTION_GAP)
        row_height = ROW_HEIGHT
        if rows and available < fixed + rows * ROW_HEIGHT:
            row_height = max(ROW_SIZE, (available - fixed) // rows)

        left = max(40, (width - 620) // 2)
        for heading, body in sections:
            top = self._section(gfx, heading, body, left, top,
                                row_height, text, dim)

        hint = "press any key"
        hint_w, _ = gfx.text_size(hint, ROW_SIZE)
        gfx.draw_text(hint, (width - hint_w) // 2,
                      height - BOTTOM_MARGIN + 8, ROW_SIZE, dim)

    @staticmethod
    def _section(gfx: Gfx, heading: str,
                 rows: tuple[tuple[str, str], ...], left: int, top: int,
                 row_height: int, text: Color, dim: Color) -> int:
        """Draw one heading and its key/description rows.

            gfx: The graphics layer.
            heading: The section title.
            rows: Pairs of key and description.
            left: Left edge in pixels.
            top: Top edge in pixels.
            row_height: Vertical step between rows, already fitted.
            text: Colour for keys and headings.
            dim: Colour for descriptions.

        Returns:
            The vertical position just below the section.
        """
        gfx.draw_text(heading, left, top, HEADING_SIZE, text)
        top += HEADING_SIZE + 8
        for key, description in rows:
            gfx.draw_text(key, left + 16, top, ROW_SIZE, text)
            gfx.draw_text(description, left + KEY_COLUMN, top,
                          ROW_SIZE, dim)
            top += row_height
        return top + SECTION_GAP
