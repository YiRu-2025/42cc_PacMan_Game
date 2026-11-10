# Risks

Written at the start and revisited as each one either materialised or
stopped mattering. Status is as of the current commit.

| # | Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- |
| 1 | The assigned maze package behaves differently from what we assume, or changes | The whole data layer is wrong | Every call goes through one adapter, `maze_loader.py`; the wheel is committed so the version cannot move under us | **Happened, contained.** Its grid is `[y][x]` while its size is `(w, h)`, and it seals a "42" into the middle. One file absorbed both |
| 2 | We use pygame calls with no MLX counterpart and fail review | Failed project | The subset was decided before any drawing code; all pygame lives in one module with a mapping table in its docstring | **Avoided.** Cost us hand-written scaling and rotation |
| 3 | Artwork has no natural end and eats the schedule | Nothing else gets finished | Every sprite has a fallback colour; the game is playable with an empty `assets/` | **Held.** Art was last and could have been dropped entirely |
| 4 | The two halves do not fit together at integration | Days lost near the deadline | Three interfaces agreed before parallel work: `Config`/`Grid` in, `GameResult` out, the renderer's view protocols | **Mostly held.** The one real mismatch was `is_open` taking a bit code while the entities passed a `Direction` |
| 5 | The configuration is replaced at review and something crashes | Failed demo | The parser never raises; a dedicated set of broken files in the test plan | **Open.** The broken-file set needs running on the review machine |
| 6 | A large maze from the configuration does not fit the screen | Unplayable at review | Cell size is computed from maze and screen rather than fixed | **Partly open.** 100×100 is legible but does not fit; the size ceiling needs agreeing |
| 7 | One person's module blocks the other | Idle time | Missing scenes degrade to a message screen, so the menus run before the gameplay exists | **Held.** The menus were testable days before `play.py` |
| 8 | AI-written code we cannot explain | Failed review — the subject requires it | Everything read line by line; several suggestions rejected; the README records which parts | **Open and the largest remaining risk.** See `issues.md` |
| 9 | Packaging fails or is left to the last day | No deliverable | Specification file tracked early | **Open.** Not yet exercised end to end |
| 10 | Review happens on an AZERTY keyboard where the digit cheat keys need Shift | Reviewer cannot trigger the cheats | Known; letters were considered | **Open.** Needs testing on a school machine |
