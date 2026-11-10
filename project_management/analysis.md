# Technical Analysis

Why the tools and the structure are what they are, and what the subject's
constraints forced.

## The binding constraint: the MLX subset

The subject allows pygame, but only the calls that have a MiniLibX
counterpart. MLX offers a window, an image buffer, per-pixel writes,
blitting, a fixed-size string, and hooks for keys and the main loop. It
has no shape primitives, no transforms, no alpha blending and no audio.

This is not a style rule we could satisfy at the end. It decides how the
game is drawn, so it was settled before any drawing code was written and
confined to one module, `pacman/gfx/gfx.py`.

### Calls used, and their counterparts

| pygame | MLX |
| --- | --- |
| `display.set_mode` | `mlx_new_window` |
| `display.set_caption` | window title argument |
| `display.flip` | end of an `mlx_loop` iteration |
| `image.load`, `convert_alpha` | `mlx_xpm_file_to_image` |
| `Surface.blit` | `mlx_put_image_to_window` |
| `Surface.fill` offscreen, then blit | `mlx_new_image` + fill + put |
| `Surface.set_at`, `get_at` | `mlx_pixel_put`, image buffer read |
| `font.Font.render` + blit | `mlx_string_put` |
| `event.get` | `mlx_hook`, `mlx_loop_hook` |
| `time.Clock.tick` | frame pacing inside `mlx_loop` |

### Calls deliberately avoided

| Not used | Why | What we do instead |
| --- | --- | --- |
| `pygame.draw.*` | MLX has no shape primitives | Fill an offscreen surface once, cache it, blit it |
| `pygame.transform.scale` | No MLX counterpart | A nearest-neighbour loop over `get_at`/`set_at`, run once per sprite at load time and cached |
| `pygame.transform.rotate`, `.flip` | Same | Quarter turns written out as index arithmetic; this is what lets three eastward player frames serve all four facings |
| `set_alpha`, blend modes | MLX has no alpha blending | The frightened state swaps in a second set of colours rather than tinting |
| `pygame.sprite`, `Rect` collision | No counterpart, and the game is grid-based anyway | Compare cell coordinates |
| `pygame.mixer` | No counterpart | No sound. `pygame.init()` is never called, because it would start the mixer |

### Two extensions we accept, and state openly

- **Text is rendered at a chosen pixel size from a chosen face.**
  `mlx_string_put` has one size and one face. We judged a game whose menus
  are unreadable to be the worse outcome, and the whole of text handling
  is in one method so it is easy to point at.
- **The frame rate is capped with `Clock.tick`.** MLX paces frames inside
  its own loop; this is the same idea reached by a different route.

Both are worth raising in review before being asked.

## Language and version

Python 3.10 or newer, for `X | Y` union syntax, `match`-free structural
clarity, and `dataclass(slots=...)`-era behaviour we rely on in the frozen
`Grid`. The school machines have 3.14, so this is a floor and not a pin.

## Why pygame and not something else

The subject names it. Had there been a choice, the argument for it is the
same one that makes it awkward here: it is a thin wrapper over SDL, so the
mapping onto MLX is almost call for call, and the subset is easy to
defend.

## Static analysis

`flake8` and `mypy --strict` both run in `make lint`, and both are a pass
condition for merging.

Two decisions came out of fighting them:

- **mypy is given package names, not `.`.** With `.` it has to guess which
  directories are package roots, and a stray copy of a module under
  `build/`, `.venv/` or `vendor/` is then found twice under two names,
  which stops the run entirely. Naming `pacman tests pac-man.py` removes
  the guess.
- **Both run through `python3 -m`.** A bare `flake8` or `mypy` resolves on
  `PATH`, which inside a virtualenv can still be the system install; it
  then cannot see the venv's pygame and reports a dozen missing-import
  errors that look like code faults. This cost an evening before it was
  understood.

`vendor/` is excluded from both. It holds the assigned maze package, which
we are told to adapt to and are not allowed to change.

## The third-party maze package

`mazegenerator` 2.1.0, received as a wheel, committed under `vendor/` so
that `make install` reinstalls the exact version the game was built
against rather than fetching whatever is current.

It is reached through one adapter, `pacman/maze_loader.py`. Nothing else
imports it. Three facts about it drove that decision:

1. It returns a grid of wall bitmasks indexed `maze[y][x]` while taking
   its size as `(width, height)` — the two orders are opposite.
2. It stamps a sealed "42" pattern into the middle of every maze large
   enough to hold one. Those cells cannot be entered, so a level that
   placed a pacgum in one could never be cleared.
3. `perfect=False` is required: a perfect maze has one route between any
   two cells, which means dead ends and a player who can be cornered.

The adapter runs a breadth-first search from the maze entry and exposes
the set of cells that are genuinely reachable. Everything above works from
that set and never from the raw dimensions. If the package changes, one
file changes.

## Packaging

PyInstaller, because the subject asks for a distributable build and it is
the path of least resistance from a pygame project. The specification file
is tracked; `build/` and `dist/` are not.

## Fonts and artwork

Both are optional by construction. Every drawable thing has a sprite path
and a fallback colour; the renderer tries the file and fills a flat colour
when it is absent. The title face ships with the game, the body face is
whichever monospace the system offers, and pygame's built-in font catches
the rest.

This was a scheduling decision as much as a technical one. Artwork is the
one task with no natural end, and this structure means an unfinished
`assets/` directory costs polish and never playability.
