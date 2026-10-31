from pathlib import Path

import pygame


def create_mine_sounds():
    path = Path(__file__).resolve().parents[1] / "assets" / "audio" / "zavod.mp3"
    if not path.is_file():
        return ()
    return (pygame.mixer.Sound(str(path)),)
