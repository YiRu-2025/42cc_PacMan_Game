"""The scene framework: what a screen is, and how screens hand over.

A scene is one screen — the main menu, a running game, the pause overlay,
the name prompt. Scenes never call one another directly and never drive the
window; they answer an event or a tick with a ``Transition`` and let
``pacman.app`` carry it out. That keeps every screen independently testable
and stops the menu and the game from importing each other.

Screens are kept on a stack rather than in a single slot, so the pause
overlay can sit on top of a running game and leave it untouched underneath.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from pacman.config import Config
from pacman.constants import FALLBACK_COLORS, Layer
from gfx.gfx import Event, EventType, Gfx, Key
from pacman.highscores import Highscores
from gfx.renderer import Renderer


@dataclass(frozen=True)
class GameResult:
    """What one play session produced.

    The contract between the gameplay modules and everything downstream:
    the game hands this back, and the name prompt and highscore table work
    from it alone.

    Attributes:
        score: Final score, never negative.
        won: True if every level was cleared.
        level_reached: The level the player was on when the game ended,
            counting from 1.
    """

    score: int
    won: bool
    level_reached: int


class Transition:
    """What a scene asks the application to do next."""


@dataclass(frozen=True)
class Push(Transition):
    """Put a scene on top, keeping the current one underneath."""

    scene: "Scene"


@dataclass(frozen=True)
class Replace(Transition):
    """Swap the current scene for another at the same depth."""

    scene: "Scene"


@dataclass(frozen=True)
class Pop(Transition):
    """Leave the current scene and return to the one underneath.

    Popping the last scene ends the game, which is what makes "back" work
    all the way out of the main menu.
    """


@dataclass(frozen=True)
class Finish(Transition):
    """End the game session and show what follows it.

    The gameplay scene returns this instead of building the next screen
    itself. The application replaces the gameplay scene rather than
    stacking on top of it, so dismissing the result returns to the menu and
    never to a game that has already ended. Getting that wrong by hand is
    the obvious mistake, so the transition exists to make it unavailable.
    """

    result: "GameResult"


@dataclass(frozen=True)
class Quit(Transition):
    """Close the window and exit, whatever is on the stack."""


@dataclass
class Context:
    """Everything every scene needs, assembled once at start-up.

    ``start_game`` is supplied by ``pacman.app`` so that the menu does not
    import the gameplay package. What follows a finished game is handled by
    the ``Finish`` transition for the same reason, so the gameplay package
    never imports the name prompt either. The only module that knows about
    both ends is the application itself.

    Attributes:
        gfx: The graphics layer.
        renderer: Draws levels and the HUD.
        config: The validated configuration.
        highscores: The loaded highscore table.
        start_game: Builds a fresh gameplay scene.
    """

    gfx: Gfx
    renderer: Renderer
    config: Config
    highscores: Highscores
    start_game: Callable[["Context"], "Scene"] = field(repr=False)


class Scene(ABC):
    """One screen.

    Subclasses answer events and ticks with a ``Transition`` or ``None``.
    ``None`` means "stay as you are", which is the common case.
    """

    transparent: bool = False
    """True if the scene below should be drawn first, as for an overlay."""

    def __init__(self, context: Context) -> None:
        """Bind the scene to the shared context."""
        self.context = context

    def on_enter(self) -> None:
        """Called when the scene becomes the top of the stack."""

    def on_exit(self) -> None:
        """Called when the scene leaves the top of the stack."""

    @abstractmethod
    def handle_event(self, event: Event) -> Transition | None:
        """React to one input event."""

    def update(self, dt: float) -> Transition | None:
        """Advance time by one frame."""
        return None

    @abstractmethod
    def draw(self) -> None:
        """Paint the scene. The caller has already drawn anything below."""


def load_optional(module: str, name: str) -> Callable[..., Scene] | None:
    """Return a scene class that may not be written yet.

    Screens arrive over several weeks and two people write them. Importing
    them by name at the moment of use keeps the rest of the game runnable
    while any one of them is missing, and keeps the menu from importing the
    gameplay package.

    """
    try:
        loaded = __import__(module, fromlist=[name])
        factory = getattr(loaded, name)
    except (ImportError, AttributeError):
        return None
    if not callable(factory):
        return None
    result: Callable[..., Scene] = factory
    return result


@dataclass(frozen=True)
class MenuItem:
    """One selectable line.

    Attributes:
        label: The text shown.
        action: What to do when it is chosen.
    """

    label: str
    action: Callable[[], Transition | None]


class MenuScene(Scene):
    """A vertical list of choices, moved through with the arrow keys.

    Shared by the main menu, the pause overlay and anything else that is a
    title plus a list, so those screens hold their items and nothing else.
    """

    title_size: int = 56
    item_size: int = 34
    line_height: int = 48

    def __init__(self, context: Context, title: str, items: list[MenuItem]) -> None:
        """Build a menu."""
        super().__init__(context)
        self.title = title
        self.items = items
        self.cursor = 0

    def handle_event(self, event: Event) -> Transition | None:
        """Move the cursor, choose an item, or go back."""
        if event.type is not EventType.KEY_DOWN:
            return None
        if event.key is Key.ESCAPE:
            return self.on_cancel()
        if not self.items:
            return None
        if event.key is Key.UP:
            self.cursor = (self.cursor - 1) % len(self.items)
        elif event.key is Key.DOWN:
            self.cursor = (self.cursor + 1) % len(self.items)
        elif event.key in (Key.ENTER, Key.SPACE):
            return self.items[self.cursor].action()
        return None

    def on_cancel(self) -> Transition | None:
        """What escape does. Leaving the screen by default."""
        return Pop()

    def draw(self) -> None:
        """Draw the title and the list, centred, cursor marked."""
        gfx = self.context.gfx
        width, height = gfx.screen_size()
        text = FALLBACK_COLORS[Layer.TEXT]
        dim = FALLBACK_COLORS[Layer.TEXT_DIM]

        block = len(self.items) * self.line_height
        top = max(self.title_size * 2, (height - block) // 2)

        title_w, _ = gfx.text_size(self.title, self.title_size)
        gfx.draw_text(
            self.title,
            (width - title_w) // 2,
            top - self.title_size * 2,
            self.title_size,
            text,
        )

        for index, item in enumerate(self.items):
            label = f"> {item.label}" if index == self.cursor else item.label
            item_w, _ = gfx.text_size(label, self.item_size)
            gfx.draw_text(
                label,
                (width - item_w) // 2,
                top + index * self.line_height,
                self.item_size,
                text if index == self.cursor else dim,
            )
