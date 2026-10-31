from functools import lru_cache

import numpy as np
import pygame
from game.sprite_cache import prepared_sprite


FACTION_COLORS = {"red": (192, 76, 59), "green": (71, 151, 91), "purple": (149, 92, 175)}


@lru_cache(maxsize=128)
def faction_image(image, owner):
    if owner == "blue":
        return image
    color = FACTION_COLORS.get(owner, FACTION_COLORS["red"])
    tinted = image.copy()
    pixels = pygame.surfarray.pixels3d(tinted)
    original = pixels.astype(np.float32)
    blue = (original[..., 2] > original[..., 0] * 1.15) & (original[..., 2] > original[..., 1] * 1.06)
    brightness = np.max(original, axis=2) / max(color)
    for channel in range(3):
        values = np.minimum(255, np.rint(brightness * color[channel])).astype(np.uint8)
        pixels[..., channel][blue] = values[blue]
    del pixels
    return prepared_sprite(tinted)
