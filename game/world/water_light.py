from functools import lru_cache
import math
import random

import pygame

from game.settings import MAP_SEED, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome


@lru_cache(maxsize=128)
def glint_image(width, phase):
    image = pygame.Surface((width + 6, 10), pygame.SRCALPHA)
    strength = math.sin(phase / 23 * math.pi) ** 2
    center = image.get_width() // 2
    reach = max(1, round(width * (.3 + strength * .2)))
    pygame.draw.line(image, (158, 213, 204, round(21 * strength)), (center - reach, 4), (center + reach, 4), 3)
    pygame.draw.line(image, (200, 232, 215, round(60 * strength)), (center - reach, 4), (center + reach, 4))
    pygame.draw.line(image, (161, 211, 206, round(30 * strength)), (center - reach // 2, 7), (center + reach // 2, 7))
    return image


class WaterLight:
    def __init__(self, terrain):
        self.chunks = {}
        randomizer = random.Random(MAP_SEED + 925)
        for _ in range(3400):
            x = randomizer.randrange(60, WORLD_WIDTH - 60)
            y = randomizer.randrange(30, WORLD_HEIGHT - 30)
            if not all(terrain.biome_at((x + dx, y + dy)) == Biome.WATER for dx, dy in ((0, 0), (-40, 0), (40, 0), (0, 12), (0, -12))):
                continue
            point = (x, y, randomizer.random() * 8, randomizer.randrange(14, 30))
            self.chunks.setdefault((x // 512, y // 512), []).append(point)

    def draw(self, screen, camera, elapsed, visibility):
        if camera.zoom < .32:
            return
        area = camera.visible_area.inflate(80, 40)
        blits = []
        for row in range(max(0, area.top // 512), min(WORLD_HEIGHT // 512, area.bottom // 512) + 1):
            for column in range(max(0, area.left // 512), min(WORLD_WIDTH // 512, area.right // 512) + 1):
                for x, y, offset, width in self.chunks.get((column, row), ()):
                    if not area.collidepoint(x, y) or not visibility.is_visible((x, y)):
                        continue
                    phase = int(((elapsed + offset) % 8) * 3)
                    image = glint_image(max(6, round(width * camera.zoom / 2) * 2), phase)
                    point = camera.world_to_screen((x + math.sin((elapsed + offset) * .35) * 2, y))
                    blits.append((image, image.get_rect(center=(round(point.x), round(point.y)))))
        screen.blits(blits, doreturn=False)
