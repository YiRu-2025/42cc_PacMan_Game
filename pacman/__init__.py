"""Pac-Man on a maze supplied by an external generator.

The package is split into layers. A layer may import from the layers below
it and never from the ones above, which is what keeps the rules testable
without a window and the drawing testable without a game.

Top: the application
    ``app``
        Wires everything together and runs the frame loop over a stack of
        scenes. The only module that knows the whole program, and so the
        only place where the menus and the gameplay meet: the menu is
        handed a callable that builds a game, and a finished game answers
        with a ``Finish`` transition the application turns into the name
        prompt. Neither side imports the other.

Screens: ``scenes``
    One screen per module — ``menu``, ``play``, ``pause``, ``scores``,
    ``name_entry``, ``message`` — over the ``Scene`` interface in
    ``scenes.base``. A scene answers an event or a tick with a
    ``Transition`` and never drives the window. They are kept on a stack
    rather than in a single slot, so the pause overlay can sit on a
    running game and leave it untouched underneath.

Rules: ``game``, ``level``, ``entities``
    Movement, pickups, ghost states and pathfinding, scoring, lives and
    level flow. No pygame, no drawing, no files: all of it runs headless,
    which is what ``tests/test_game.py`` and its neighbours rely on.
    ``cheats`` sits here too, as state the gameplay reads rather than a
    set of shortcuts bolted onto the input handler.

Drawing: ``gfx``
    ``gfx.gfx`` is the only module in the project that imports pygame, and
    only calls with an MLX counterpart; its docstring carries the mapping
    the subject asks for. ``gfx.renderer`` turns grid coordinates into
    pixels and chooses a sprite or, when the artwork for it does not exist
    yet, a flat fallback colour. It reads game state and never writes it,
    through the view protocols the package re-exports.

Edges: ``config``, ``highscores``, ``maze_loader``
    The configuration file, the score file, and the third-party maze
    package. Each absorbs bad input and reports it in one readable line,
    so nothing above them has to cope with a malformed file, a missing
    key or a failed import. No traceback reaches the player from here.

Foundation: ``constants``
    Values with no dependencies: directions, timing, layout, and the
    sprite-path and fallback-colour tables that make the artwork optional.

Anything the configuration file can set lives in ``config``; anything it
cannot lives in ``constants``. A value kept in both would eventually
disagree with itself.
"""

__version__ = "1.0.0"
