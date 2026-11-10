"""The main menu: the first screen, and the one everything returns to."""

from pacman.constants import FALLBACK_COLORS, GAME_TITLE, Layer
from pacman.scenes.base import (
    Context,
    MenuItem,
    MenuScene,
    Push,
    Quit,
    Scene,
    Transition,
    load_optional,
)
from pacman.scenes.message import MessageScene


def _optional(context: Context, module: str, name: str, heading: str) -> Scene:
    """Return a screen if it exists, or a notice saying it does not.

    context: The shared state.
    module: Dotted module path holding the screen.
    name: Class name inside that module.
    heading: What to show if the screen is missing.

    """
    factory = load_optional(module, name)
    if factory is None:
        return MessageScene(context, heading, "not written yet")
    return factory(context)


class MainMenuScene(MenuScene):
    """Start a game, read the highscores or the instructions, or quit."""

    def __init__(self, context: Context) -> None:
        """Build the menu and its four entries."""
        super().__init__(
            context,
            GAME_TITLE,
            [
                MenuItem("Start", self._start),
                MenuItem("Highscores", self._scores),
                MenuItem("Instructions", self._instructions),
                MenuItem("Quit", self._quit),
            ],
        )

    def _start(self) -> Transition:
        """Open a fresh game."""
        return Push(self.context.start_game(self.context))

    def _scores(self) -> Transition:
        """Open the highscore table."""
        return Push(
            _optional(self.context, "pacman.scenes.scores", "ScoresScene", "Highscores")
        )

    def _instructions(self) -> Transition:
        """Open the instructions."""
        return Push(
            _optional(
                self.context,
                "pacman.scenes.instructions",
                "InstructionsScene",
                "Instructions",
            )
        )

    @staticmethod
    def _quit() -> Transition:
        """Leave the game."""
        return Quit()

    def on_cancel(self) -> Transition:
        """Escape leaves the game from the top-level menu."""
        return Quit()

    def draw(self) -> None:
        """Paper behind, then the standard title and list."""
        gfx = self.context.gfx
        width, height = gfx.screen_size()
        gfx.fill_rect(FALLBACK_COLORS[Layer.PAPER], 0, 0, width, height)
        best = self.context.highscores.best()
        if best:
            line = f"best {best}"
            line_w, _ = gfx.text_size(line, self.item_size)
            gfx.draw_text(
                line,
                (width - line_w) // 2,
                height - 70,
                self.item_size,
                FALLBACK_COLORS[Layer.TEXT_DIM],
            )
        super().draw()
