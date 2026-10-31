import os
import gc

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from game.application import Application


if __name__ == "__main__":
    restarting=False
    display_preferences=None
    while True:
        application=Application(start_immediately=restarting,display_preferences=display_preferences)
        restarting=application.run()
        display_preferences=(application.fullscreen,application.window_size)
        if not restarting:break
        del application
        gc.collect()