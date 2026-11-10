# Progress: plan against actual

Dates from the commit history.

## By phase

| Phase | Planned | Actual | Notes |
| --- | --- | --- | --- |
| 1. Scaffolding, Makefile, repository | day 1 | before 2 Nov | Went to plan |
| 2. Data layer: `config.py`, `maze_loader.py` | days 2–3 | 2–3 Nov | The adapter took longer than planned; the sealed "42" pattern was not anticipated |
| 3. Rules: `level.py`, `entities/`, `game.py` | days 3–5 | 2–5 Nov | `level.py` finished 2 Nov, entities 4 Nov, `game.py` 5 Nov |
| 4. Graphics and scenes | days 5–7 | 5–6 Nov | `gfx` 5 Nov, scenes 6 Nov. The menus were runnable before the gameplay existed, as designed |
| 5. Highscores and cheats | days 6–8 | 3–5 Nov | Ran early: `highscores.py` 3 Nov, `cheat.py` 5 Nov |
| 6. Integration and debugging | days 8–9 | 7–10 Nov | **Overran.** Four days against a planned two |
| 7. Artwork | last | 10 Nov | Placeholder set in place; final art outstanding |
| 8. Documentation and packaging | last | 10 Nov onwards | README written; `project_management/` written; packaging outstanding |

## Where the estimate was wrong

**Integration was planned as two days and took four.** Not because the
interfaces disagreed — those held — but because of a class of defect we
had not planned for: code that passes `flake8` and `mypy --strict` and the
whole unit test suite, and still does not run. Two indentation bugs and
one unimplemented abstract method cost most of 7–10 November.

The response is in `test_plan.md`: `make run` and watching a window appear
is now the first acceptance check, before any of the detailed ones.

**The phases were not as sequential as planned.** Highscores and cheats
both landed during phase 3 because they have no dependencies, and that was
right — the plan should have had them as "whenever blocked" rather than
fixed at phase 5.

## Outstanding

- Apply `config.pacgum` to the board
- Final artwork; ghost sprites are 32×32 and should be 48×48
- Packaging: exercise `pacman.spec` end to end, and practise rebuilding
- Run the broken-configuration set on a school machine
- Settle the maze size ceiling
- Each of us to rewrite two modules unaided, for the defence
