from functools import lru_cache
import math

import pygame

from game.world.building_rendering import building_parts


@lru_cache(maxsize=64)
def outline_image(image):
    mask = pygame.mask.from_surface(image, 55)
    silhouette = mask.to_surface(setcolor=(224, 207, 144, 255), unsetcolor=(0, 0, 0, 0))
    result = pygame.Surface((image.get_width() + 6, image.get_height() + 6), pygame.SRCALPHA)
    for offset in (
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (2, 0),
        (-2, 0),
        (0, 2),
        (0, -2),
        (1, 1),
        (-1, 1),
        (1, -1),
        (-1, -1),
    ):
        result.blit(silhouette, (offset[0] + 3, offset[1] + 3))
    cutout = mask.to_surface(setcolor=(0, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
    result.blit(cutout, (3, 3), special_flags=pygame.BLEND_RGBA_SUB)
    return result


class BuildingInteraction:
    def __init__(self, buildings):
        self.buildings = buildings
        self.strengths = {}
        self.hovered = None

    def update(self, pointer, screen, camera, duration, blocked=False):
        self.hovered = None if blocked else self.buildings.interactive_at(pointer, screen, camera)
        if self.hovered is not None:
            self.strengths.setdefault(self.hovered, 0)
        for building, strength in tuple(self.strengths.items()):
            target = 1 if building is self.hovered else 0
            strength += (target - strength) * -math.expm1(-max(0, duration) / 0.13)
            if strength < 0.005 and target == 0:
                del self.strengths[building]
            else:
                self.strengths[building] = strength

    def draw(self, screen, camera):
        for building, strength in self.strengths.items():
            for part in building_parts(building, camera, workers=False):
                image = outline_image(part.image).copy()
                image.set_alpha(round(210 * strength))
                screen.blit(image, part.rectangle.move(-3, -3))
