"""The pause overlay, drawn on top of a game that stays frozen underneath."""

from pacman.constants import FALLBACK_COLORS, Layer
from pacman.scenes.base import (
    Context,
    MenuItem,
    MenuScene,
    Pop,
    Transition,
)

BAND_PADDING: int = 28
"""Space left around the menu inside its band, in pixels."""


class PauseScene(MenuScene):
    """Resume the game, or abandon it and return to the main menu.

    Being transparent is what makes this an overlay rather than a screen:
    the application draws the game underneath first and then this on top,
    and the game receives no ticks while it is covered.
    """

    transparent = True

    def __init__(self, context: Context) -> None:
        """Build the overlay.

            context: The shared state.
        """
        super().__init__(context, "Paused", [
            MenuItem("Resume", self._resume),
            MenuItem("Main menu", self._abandon),
        ])

    @staticmethod
    def _resume() -> Transition:
        """Drop the overlay and hand control back to the game."""
        return Pop()

    @staticmethod
    def _abandon() -> Transition:
        """Leave the overlay and the game beneath it.

        Two scenes rather than one: the game is abandoned, not paused
        indefinitely. An abandoned session records no score, because the
        subject asks for a name only when a game is won or lost.
        """
        return Pop(2)

    def on_cancel(self) -> Transition:
        """Escape resumes, which is what pressing it again should mean."""
        return Pop()

    def draw(self) -> None:
        """Lay a band over the frozen game, then the usual title and list.

        The band is measured from the menu itself rather than from a fixed
        height, so the title can never end up outside it and unreadable
        against whatever the game was drawing.
        """
        gfx = self.context.gfx
        width, height = gfx.screen_size()
        top, band = self.content_bounds()
        band_top = max(0, top - BAND_PADDING)
        band_height = min(height - band_top, band + BAND_PADDING * 2)
        gfx.fill_rect(FALLBACK_COLORS[Layer.PAPER], 0, band_top,
                      width, band_height)
        super().draw()
