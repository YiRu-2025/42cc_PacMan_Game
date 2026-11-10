"""Entry point: python3 pac-man.py config.json

Only checks the number of arguments, then hands over to pacman.app.
The file is called pac-man.py (not pacman.py) so it cannot shadow the
``pacman`` package.
"""

import sys

from pacman.app import run

USAGE = "usage: python3 pac-man.py <config.json>"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
        sys.exit(run(sys.argv[1]))