from functools import lru_cache
import math

import pygame


FLAG_FRAMES = 32
FLAG_RATE = 12


@lru_cache(maxsize=192)
def flag_image(color, height, frame=0):
    scale = 4
    width = max(4, round(height * .85))
    image = pygame.Surface(((width + 4) * scale, (height + 4) * scale), pygame.SRCALPHA)
    phase = frame / FLAG_FRAMES * math.tau
    top, bottom = [], []
    for index in range(9):
        fraction = index / 8
        horizontal = 4 + (width - 4) * fraction
        wave = math.sin(phase - fraction * 6) * height * .05 * fraction
        top.append((horizontal, height * (.09 + fraction * .07) + wave))
        bottom.append((horizontal, height * (.5 + fraction * .1) + wave))

    def scaled(points):
        return [(round(horizontal * scale), round(vertical * scale)) for horizontal, vertical in points]

    notch = (width - height * .1, (top[-1][1] + bottom[-1][1]) / 2)
    outline = top + [notch] + list(reversed(bottom))
    pygame.draw.polygon(image, (16, 29, 26), scaled(outline), scale * 2)
    for index in range(8):
        strip = [top[index], top[index + 1], bottom[index + 1], bottom[index]]
        if index == 7:
            strip.insert(2, notch)
        brightness = .87 + .13 * math.sin(phase - index * .72)
        shade = tuple(round(channel * brightness) for channel in color)
        pygame.draw.polygon(image, shade, scaled(strip))
    highlight = tuple(min(255, channel + 50) for channel in color)
    pygame.draw.lines(image, highlight, False, scaled(top), scale)
    pygame.draw.line(image, (15, 28, 27), (4 * scale, 2 * scale), (4 * scale, height * scale), 3 * scale)
    pygame.draw.line(image, (209, 193, 145), (4 * scale, 2 * scale), (4 * scale, height * scale), scale)
    pygame.draw.circle(image, (231, 207, 144), (4 * scale, 2 * scale), scale)
    return pygame.transform.smoothscale(image, (width + 4, height + 4)).convert_alpha()
