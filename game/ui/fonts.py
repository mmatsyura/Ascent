from functools import lru_cache

import pygame


@lru_cache(maxsize=32)
def ui_font(size=15, bold=False):
    path = pygame.font.match_font("tahoma", bold=bold)
    if path is None:
        path = pygame.font.match_font("dejavusans,arial", bold=bold)
    return pygame.font.Font(path, max(13, round(size)))


def fit_text(font, text, width):
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "…")[0] > width:
        text = text[:-1]
    return text.rstrip() + "…"
