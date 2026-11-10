# Issues and disagreements

Blocking points, and the decisions taken to get past them.

## Resolved

### The cheat key table existed twice

`constants.CHEAT_BINDINGS` held key-to-description for the instructions
screen; `cheat.CHEAT_ACTIONS` held key-to-behaviour for the dispatcher.
They drifted, and the in-game manual told the player to press keys that
did nothing.

Two options: make the two tables agree, or merge them into one.

**Decision: make them agree, and record the merge as debt.** The merge was
the better design but it crossed the boundary between our two modules, and
rewriting a teammate's file to fix a problem that a five-character edit
also fixes is not worth the friction. `tests/cheat_test.py` now asserts
that what the instructions screen shows is what the keys do, so the two
cannot drift again unnoticed.

### Who owns `renderer.py`

It was originally on the gameplay side with `gfx.py`. It moved to the
other side because the artwork, the sprite-path table and the fallback
colours are all there, and splitting "draws the art" from "places the art"
between two people would have meant constant back-and-forth over tile
seams and colour matching.

### `is_open` took a bit code

The adapter exposed the maze package's wall bitmask; the entities passed a
`Direction`. The first movement attempt was a type error.

**Decision: the adapter changes, not the entities.** The bit encoding
belongs to the third-party package and should stop at its boundary.
`WALL_BIT` is now the only place in the project that knows about it.

### `mypy --strict .` refused to run

It found `maze_loader.py` under two module names and stopped. Giving mypy
the package names instead of `.` removes the guess about package roots and
also keeps `vendor/` out.

## Open

### The `pacgum` configuration key is not applied

The subject's configuration has `pacgum: 42` and the text says pacgums go
in "most corridors". `build_level()` fills every walkable cell instead —
277 on a 20×15 maze.

This is both a specification gap and the reason the board looks crowded.
Fixing it means `build_level` taking a count and spreading that many
pacgums along the maze rather than flooding it. Documented in the README's
Known Limitations until it is done.

### Maze size ceiling

`cell_size_for` scales the cell down to fit, with a floor of 16px. A
100×100 maze is legible at that floor but 1656px tall, which no laptop
shows. Either the configuration's size range comes down to something that
always fits, or the view scrolls. The first is simpler and we lean towards
it, but it has not been agreed.

### Cheat keys on AZERTY

The cheats are bound to the digits 1 to 5. On a French layout the number
row needs Shift, so `event.char` for the unshifted key is `&`, not `1`.
Review is likely to happen on such a machine. Letters would avoid this;
the change is small but touches a teammate's module, so it waits on a test
on a school keyboard.

### Explaining AI-assisted code

Substantial parts of the graphics layer and the scene framework were
written with AI assistance. The subject requires that we can explain
everything we submit. The plan is for each of us to rewrite two of the
shorter modules from scratch and to be able to give the reasoning behind
the decisions that would be asked about: the scene stack rather than a
single slot, the `Finish` transition, hand-written rotation instead of
`pygame.transform`, and the three-tier sprite fallback.

This is the largest remaining risk in the project.

### Git identity

Commits appear under three names — `yru`, `sin song` and
`sinxyz1984@gmail.com` — for two people. `git config user.name` should be
set consistently before submission, or the contribution history reads as
three contributors.
