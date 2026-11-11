"""Entry point: python3 pac-man.py config.json

From source it only checks the number of arguments, then hands over to
pacman.app. The file is called pac-man.py (not pacman.py) so it cannot
shadow the ``pacman`` package.

In a PyInstaller build, double-clicking passes no argument: use a
config.json placed beside the executable if there is one, otherwise the
default one bundled inside.
"""

import sys
from pacman.app import run
from pacman.constants import data_path, is_frozen, resource_path

USAGE = "usage: python3 pac-man.py <config.json>"


def pick_config(argv: list[str]) -> str | None:
    """Return the configuration path to use, or None for a usage error."""
    if len(argv) == 2:
        return argv[1]
    if len(argv) == 1 and is_frozen():
        beside = data_path("config.json")
        return str(beside if beside.is_file() else resource_path("config.json"))
    return None


if __name__ == "__main__":
    chosen = pick_config(sys.argv)
    if chosen is None:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    sys.exit(run(chosen))
