import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from game.application import Application


if __name__ == "__main__":
    Application().run()