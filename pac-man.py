
import pacman
import sys


def main() -> None:
    if sys.argv != 2:
        print("wrong usage. Should be python3 pac-man.py config.json")
        sys.exit
    filename = sys.argv[1]
    if not filename.endswith(".json"):
        print("wrong format for configuration, must be a json file.")
        sys.exit
    pacman.config
    # 逻辑先写到了usage这里 tutorial 5.1, 需要检查是否符合第二条要求
