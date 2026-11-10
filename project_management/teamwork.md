# Team

Two people: **sluyu** and **yru**.

## How the work was split

By what each part talks to, rather than by file count: one owns everything
inside a round of play, the other owns everything outside it.

| | yru | sluyu |
| --- | --- | --- |
| Rules | `level.py`, `entities/`, `game.py`, `cheat.py` | |
| Scenes | `play.py` | `menu.py`, `pause.py`, `scores.py`, `instructions.py`, `name_entry.py`, `message.py`, `base.py` |
| Edges | `config.py` | `maze_loader.py`, `highscores.py` |
| Drawing | | `gfx/gfx.py`, `gfx/renderer.py`, `constants.py` |
| Wiring | | `app.py` |
| Build | | `Makefile`, `setup.cfg`, packaging, artwork |

The split is not even in lines. It is even in what has to be understood:
the ghost state machine and the breadth-first pathfinding are the hardest
part of the project and sit on one side, so the drawing layer, the window
sizing and the asset fallback sit on the other.

## The interfaces

Agreed before parallel work started, and the reason the two halves could
be written at the same time:

1. **`Config` and `Grid`** — handed from the edges to the rules.
2. **`GameResult`** — handed back from a finished run.
3. **The renderer's view protocols** — what the rules must expose to be
   drawable: `LevelView`, `PlayerView`, `GhostView`, `GameView`.

`app.py` is the only module that knows about both ends. The menu is given
a callable that builds a game; a finished game answers with a `Finish`
transition. Neither imports the other.

## How decisions were made

Anything inside one person's modules is that person's call. Anything that
crosses the boundary is discussed, and if it stays unresolved it goes into
`issues.md` with the reasoning, rather than one of us changing the other's
file quietly.

Two decisions went the "leave it as recorded debt" way, both in
`issues.md`: the duplicated cheat-key table, and the digit cheat keys on an
AZERTY keyboard.

## Before the defence

The subject allows a reviewer to ask for a change anywhere in the project,
so each of us has to be able to explain the other's modules. Two days are
reserved for reading each other's code and for rewriting, unaided, two of
the shorter modules each.
