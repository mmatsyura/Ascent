from functools import lru_cache
import math

import pygame


@lru_cache(maxsize=128)
def submerged_image(image, step, depth=.52):
    strength = step / 24
    result = image.copy()
    bounds = image.get_bounding_rect(min_alpha=70 if depth <= .1 else 20)
    waterline = bounds.bottom - round(bounds.h * depth * strength)
    if waterline < result.get_height():
        result.fill((0, 0, 0, 0), (0, waterline, result.get_width(), result.get_height() - waterline))
        if waterline > 0:
            pixels = pygame.surfarray.pixels_alpha(result)
            pixels[:, waterline - 1] //= 2
            del pixels
    return result, waterline, bounds


def water_image(image, immersion, time, depth=.52):
    if immersion < .02:
        return image
    result, waterline, bounds = submerged_image(image, round(min(1, immersion) * 24), depth)
    result = result.copy()
    width = max(6, round(bounds.w * (.65 + .12 * math.sin(time * 2.5))))
    height = max(3, round(bounds.h * .12))
    area = pygame.Rect(0, 0, width, height)
    area.center = (bounds.centerx, waterline)
    opacity = round(immersion * 105)
    pygame.draw.arc(result, (164, 214, 218, opacity), area, math.pi * .05, math.pi * .94, 1)
    pygame.draw.arc(result, (107, 179, 192, opacity // 2), area.inflate(4, 2), math.pi * 1.08, math.pi * 1.9, 1)
    return result
