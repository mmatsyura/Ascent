from functools import lru_cache
import math

import pygame


@lru_cache(maxsize=1)
def badge_background():
    image = pygame.Surface((160, 160), pygame.SRCALPHA)
    pygame.draw.circle(image, (7, 15, 23, 100), (80, 84), 75)
    pygame.draw.circle(image, (26, 33, 36), (80, 78), 74)
    pygame.draw.circle(image, (175, 165, 123), (80, 78), 72)
    pygame.draw.circle(image, (61, 71, 66), (80, 79), 70)
    pygame.draw.circle(image, (13, 29, 41), (80, 78), 67)
    for radius in range(64, 0, -1):
        progress = 1 - radius / 64
        color = (round(30 + progress * 12), round(61 + progress * 24), round(82 + progress * 29))
        pygame.draw.circle(image, color, (80, 76), radius)
    pygame.draw.arc(image, (231, 216, 165), (9, 7, 142, 142), .3, 2.8, 2)
    pygame.draw.arc(image, (91, 122, 136), (17, 13, 126, 126), .35, 2.7, 2)
    for angle in (45, 135, 225, 315):
        horizontal = round(80 + math.cos(math.radians(angle)) * 70)
        vertical = round(78 + math.sin(math.radians(angle)) * 70)
        pygame.draw.circle(image, (26, 33, 33), (horizontal, vertical + 1), 3)
        pygame.draw.circle(image, (205, 188, 141), (horizontal, vertical), 2)
    return image
