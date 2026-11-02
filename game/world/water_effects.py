from functools import lru_cache
import math
import random

import pygame

from game.settings import MAP_SEED, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome


@lru_cache(maxsize=128)
def submerged_image(image, step, depth=0.52):
    strength = step / 24
    result = image.copy()
    bounds = image.get_bounding_rect(min_alpha=70 if depth <= 0.1 else 20)
    waterline = bounds.bottom - round(bounds.h * depth * strength)
    if waterline < result.get_height():
        result.fill(
            (0, 0, 0, 0), (0, waterline, result.get_width(), result.get_height() - waterline)
        )
        if waterline > 0:
            pixels = pygame.surfarray.pixels_alpha(result)
            pixels[:, waterline - 1] //= 2
            del pixels
    return result, waterline, bounds


def water_image(image, immersion, time, depth=0.52):
    if immersion < 0.02:
        return image
    result, waterline, bounds = submerged_image(image, round(min(1, immersion) * 24), depth)
    result = result.copy()
    width = max(6, round(bounds.w * (0.65 + 0.12 * math.sin(time * 2.5))))
    height = max(3, round(bounds.h * 0.12))
    area = pygame.Rect(0, 0, width, height)
    area.center = (bounds.centerx, waterline)
    opacity = round(immersion * 105)
    pygame.draw.arc(result, (164, 214, 218, opacity), area, math.pi * 0.05, math.pi * 0.94, 1)
    pygame.draw.arc(
        result, (107, 179, 192, opacity // 2), area.inflate(4, 2), math.pi * 1.08, math.pi * 1.9, 1
    )
    return result


@lru_cache(maxsize=128)
def glint_image(width, phase):
    image = pygame.Surface((width + 6, 10), pygame.SRCALPHA)
    strength = math.sin(phase / 23 * math.pi) ** 2
    center = image.get_width() // 2
    reach = max(1, round(width * (0.3 + strength * 0.2)))
    pygame.draw.line(
        image, (158, 213, 204, round(21 * strength)), (center - reach, 4), (center + reach, 4), 3
    )
    pygame.draw.line(
        image, (200, 232, 215, round(60 * strength)), (center - reach, 4), (center + reach, 4)
    )
    pygame.draw.line(
        image,
        (161, 211, 206, round(30 * strength)),
        (center - reach // 2, 7),
        (center + reach // 2, 7),
    )
    return image


class WaterLight:
    def __init__(self, terrain):
        self.chunks = {}
        randomizer = random.Random(MAP_SEED + 925)
        for _ in range(3400):
            x = randomizer.randrange(60, WORLD_WIDTH - 60)
            y = randomizer.randrange(30, WORLD_HEIGHT - 30)
            if not all(
                terrain.biome_at((x + dx, y + dy)) == Biome.WATER
                for dx, dy in ((0, 0), (-40, 0), (40, 0), (0, 12), (0, -12))
            ):
                continue
            point = (x, y, randomizer.random() * 8, randomizer.randrange(14, 30))
            self.chunks.setdefault((x // 512, y // 512), []).append(point)

    def draw(self, screen, camera, elapsed, visibility):
        if camera.zoom < 0.32:
            return
        area = camera.visible_area.inflate(80, 40)
        blits = []
        for row in range(max(0, area.top // 512), min(WORLD_HEIGHT // 512, area.bottom // 512) + 1):
            for column in range(
                max(0, area.left // 512), min(WORLD_WIDTH // 512, area.right // 512) + 1
            ):
                for x, y, offset, width in self.chunks.get((column, row), ()):
                    if not area.collidepoint(x, y) or not visibility.is_visible((x, y)):
                        continue
                    phase = int(((elapsed + offset) % 8) * 3)
                    image = glint_image(max(6, round(width * camera.zoom / 2) * 2), phase)
                    point = camera.world_to_screen((x + math.sin((elapsed + offset) * 0.35) * 2, y))
                    blits.append((image, image.get_rect(center=(round(point.x), round(point.y)))))
        screen.blits(blits, doreturn=False)
