from functools import lru_cache

import pygame


@lru_cache(maxsize=1)
def badge_background():
    image = pygame.Surface((160, 160), pygame.SRCALPHA)
    pygame.draw.circle(image, (7, 15, 23, 100), (80, 84), 75)
    pygame.draw.circle(image, (177, 174, 140), (80, 78), 73)
    pygame.draw.circle(image, (24, 41, 53), (80, 78), 69)
    pygame.draw.circle(image, (39, 83, 119), (80, 76), 64)
    pygame.draw.arc(image, (112, 159, 184), (19, 15, 122, 122), .35, 2.7, 2)
    return image
