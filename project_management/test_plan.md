# Test Plan

What is tested automatically, what has to be checked by hand, and the
defects found along the way.

## Automated tests

`make test` runs 73 tests. They cover the layers that have no window:

| File | Covers |
| --- | --- |
| `tests/test_config.py` | Parsing, defaults, range clamping, bad input |
| `tests/test_maze_loader.py` | The adapter around the maze package |
| `tests/level_test.py` | Pickup layout and spawn points |
| `tests/cheat_test.py` | Cheat bindings and one-shot requests |

Two decisions make these tests worth having:

**No test touches the real maze generator except where that is the point.**
Its mazes are random and its "42" pattern moves with the maze size, so a
failing test would say nothing about the code under test. Instead a `Grid`
is built from an ASCII drawing of a maze, and the expected answer can be
worked out by eye.

**`Game` takes a maze-loader factory.** That is what lets a test inject a
fixed maze and assert on the seeds the game asked for, which is how the
"level 1 is reproducible, later levels are not" rule is checked.

### Not covered automatically

Anything that needs a window: the renderer, the scenes, the input
handling. These are covered by the manual checks below. The renderer's
view protocols mean it *could* be driven with hand-built fakes, which is
the obvious next step if time allows.

## Manual acceptance checks

Run before any submission. The first one exists because of a defect we
shipped past `make lint` and `make test` — see below.

| # | Check | Expected |
| --- | --- | --- |
| 1 | `make run` | A window opens and the main menu is drawn |
| 2 | Arrow keys and WASD | The player turns; a blocked turn keeps the old heading |
| 3 | Walk over a pacgum | Score rises, pacgum disappears |
| 4 | Eat a super-pacgum | Whole screen changes palette; ghosts change form |
| 5 | Eat a frightened ghost | Score rises; ghost becomes eyes and returns to its corner |
| 6 | Be caught by a chasing ghost | One life lost; brief freeze; respawn |
| 7 | Lose every life | Game over, name prompt, highscore table |
| 8 | Escape during play | Pause overlay; the game underneath is frozen and still visible |
| 9 | Pause → Resume | Position unchanged |
| 10 | Pause → Main menu | Back at the menu; no score recorded |
| 11 | Cheat `1` ten times | Reaches level 10 and the victory screen |
| 12 | Cheats `2` `3` `4` `5` | Invincible, frozen ghosts, extra life, double speed |
| 13 | Instructions screen | The keys shown are the keys that work |
| 14 | Enter a name with an accent or a symbol | The character is simply not accepted |
| 15 | Enter a name of 10+ characters | Stops at 10 |
| 16 | Two runs with the same score | The earlier one stays higher |
| 17 | Quit and restart | Highscores survive |
| 18 | `python3 pac-man.py` | Usage message, exit 1, no traceback |
| 19 | `python3 pac-man.py a.json b.json` | Same |
| 20 | `python3 pac-man.py config.txt` | Error about the extension, exit 1 |
| 21 | Ctrl+C during play | One line, no traceback |
| 22 | Delete the highscore file and restart | Empty table, game runs |
| 23 | Corrupt the highscore file and restart | Message, empty table, game runs |

### Configuration checks

The configuration is replaced at review time, so this set is run with
deliberately broken files. None may stop the game.

| File | Expected |
| --- | --- |
| Missing file | All defaults, message, game runs |
| Empty file | Same |
| Comments only | Same |
| Malformed JSON (missing brace) | Message, all defaults |
| Top-level array instead of object | Message, all defaults |
| `"lives": -5` | Clamped, message |
| `"lives": "abc"` | Default, message |
| `"lives": true` | Default, message — `bool` must not pass as `int` |
| `"levels": []` | Default ten levels |
| `"levels"` entry missing `width` | That entry's default used |
| Unknown key | Ignored, message |
| Fewer than ten levels | Padded to ten |
| Very large maze (100×100) | Starts and is legible at a smaller cell size |
| Very small maze (9×9) | Starts; the generator declines to stamp a "42" |

## Defects found and fixed

| Defect | How it was found | Fix |
| --- | --- | --- |
| `game.py`: everything after the constructor was indented one level too deep, so `Game` had no methods at all | Trying to construct a `Game` | Dedent (commit "fix indentention error in game.py") |
| `Ghost.step()` was never implemented, so `Ghost` could not be instantiated | Same | Implemented the chase/flee choice |
| `_add_scroe`, `_lose_live` — two misspelled call sites | `mypy --strict`, then a crash on first ghost contact | Renamed to match |
| `pac-man.py`: the call to `run()` was indented inside the argument check, so with correct arguments the script did nothing and exited 0 | `make run` printed the pygame banner and returned to the prompt | Dedent by one level |
| `app.py` imported `from gfx.renderer`, which does not resolve | Import error on start-up | `from pacman.gfx import Renderer` |
| Cheat keys: the instructions screen showed `i n f l b` while the dispatcher answered to `1 2 3 4 5` | `tests/cheat_test.py` | Made the two agree; the test now asserts it |
| `Entity.update`: `while cooldown <= 0` took an extra step whenever the cooldown landed exactly on zero, which it does on the first frame and after every respawn | A test asserting one step for one step's worth of time | `< 0` |
| `Grid.is_open` took a bit code while the entities passed a `Direction` | Type error at first movement | `is_open` now speaks `Direction`; the bit codes stay inside the adapter |
| `nearest_walkable` broke ties by set iteration order, so the same maze could place spawns differently between runs | Noticed while comparing two runs of the same seed | Tie broken by coordinate |
| The instructions screen's two columns overlapped after the body font changed | Looking at the screen | The key column is measured from the text rather than fixed |
| `mypy --strict .` found `maze_loader.py` twice under two module names and refused to run | `make lint` | mypy is given package names, not `.` |

## What this taught us about the plan

Three of the defects above — the two indentation bugs and the missing
`Ghost.step` — passed `flake8` cleanly, and two of them passed
`mypy --strict` as well. The `pac-man.py` one also passed every unit test,
because nothing in the test suite starts the program.

That is why check #1 exists and is first. A green `make lint && make test`
is not evidence that the game runs.
