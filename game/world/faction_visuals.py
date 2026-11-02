from functools import lru_cache
import math

import numpy as np
import pygame

from game.rendering import prepared_sprite

FLAG_FRAMES = 32


FLAG_RATE = 12


@lru_cache(maxsize=192)
def flag_image(color, height, frame=0):
    scale = 4
    width = max(4, round(height * 0.85))
    image = pygame.Surface(((width + 4) * scale, (height + 4) * scale), pygame.SRCALPHA)
    phase = frame / FLAG_FRAMES * math.tau
    top, bottom = [], []
    for index in range(9):
        fraction = index / 8
        horizontal = 4 + (width - 4) * fraction
        wave = math.sin(phase - fraction * 6) * height * 0.05 * fraction
        top.append((horizontal, height * (0.09 + fraction * 0.07) + wave))
        bottom.append((horizontal, height * (0.5 + fraction * 0.1) + wave))

    def scaled(points):
        return [
            (round(horizontal * scale), round(vertical * scale)) for horizontal, vertical in points
        ]

    notch = (width - height * 0.1, (top[-1][1] + bottom[-1][1]) / 2)
    outline = top + [notch] + list(reversed(bottom))
    pygame.draw.polygon(image, (16, 29, 26), scaled(outline), scale * 2)
    for index in range(8):
        strip = [top[index], top[index + 1], bottom[index + 1], bottom[index]]
        if index == 7:
            strip.insert(2, notch)
        brightness = 0.87 + 0.13 * math.sin(phase - index * 0.72)
        shade = tuple(round(channel * brightness) for channel in color)
        pygame.draw.polygon(image, shade, scaled(strip))
    highlight = tuple(min(255, channel + 50) for channel in color)
    pygame.draw.lines(image, highlight, False, scaled(top), scale)
    pygame.draw.line(
        image, (15, 28, 27), (4 * scale, 2 * scale), (4 * scale, height * scale), 3 * scale
    )
    pygame.draw.line(
        image, (209, 193, 145), (4 * scale, 2 * scale), (4 * scale, height * scale), scale
    )
    pygame.draw.circle(image, (231, 207, 144), (4 * scale, 2 * scale), scale)
    return pygame.transform.smoothscale(image, (width + 4, height + 4)).convert_alpha()


FACTION_COLORS = {"red": (192, 76, 59), "green": (71, 151, 91), "purple": (149, 92, 175)}


@lru_cache(maxsize=128)
def faction_image(image, owner):
    if owner == "blue":
        return image
    color = FACTION_COLORS.get(owner, FACTION_COLORS["red"])
    tinted = image.copy()
    pixels = pygame.surfarray.pixels3d(tinted)
    original = pixels.astype(np.float32)
    blue = (original[..., 2] > original[..., 0] * 1.15) & (
        original[..., 2] > original[..., 1] * 1.06
    )
    brightness = np.max(original, axis=2) / max(color)
    for channel in range(3):
        values = np.minimum(255, np.rint(brightness * color[channel])).astype(np.uint8)
        pixels[..., channel][blue] = values[blue]
    del pixels
    return prepared_sprite(tinted)
