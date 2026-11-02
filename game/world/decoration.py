import numpy as np
import pygame

from game.settings import TERRAIN_SCALE, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome


def contains_biome(biomes, world_x, world_y, margin, biome):
    left = max(0, (world_x - margin) // TERRAIN_SCALE)
    right = min(biomes.shape[1], (world_x + margin) // TERRAIN_SCALE + 1)
    top = max(0, (world_y - margin) // TERRAIN_SCALE)
    bottom = min(biomes.shape[0], (world_y + margin) // TERRAIN_SCALE + 1)
    return np.all(biomes[top:bottom, left:right] == biome)


def decorate_terrain(surface, biomes, forest_strength, random):
    positions = random.integers((30, 30), (WORLD_WIDTH - 30, WORLD_HEIGHT - 30), size=(45000, 2))

    for world_x, world_y in positions:
        world_x, world_y = int(world_x), int(world_y)
        row, column = world_y // TERRAIN_SCALE, world_x // TERRAIN_SCALE
        biome = biomes[row, column]

        if biome in (Biome.MEADOW, Biome.FOREST):
            if not contains_biome(biomes, world_x, world_y, 7, biome):
                continue
            woodland = forest_strength[row, column]
            grass_color = (110, 130, 79) if woodland < 0.5 else (96, 118, 76)
            for offset in [-3, 0, 3]:
                height = int(random.integers(2, 5))
                lean = (world_x + world_y + offset) % 5 - 2
                tone = tuple(channel + (offset + 3) * 2 for channel in grass_color)
                pygame.draw.line(
                    surface,
                    tone,
                    (world_x + offset // 2, world_y + 2),
                    (world_x + offset + lean, world_y - height),
                    1,
                )
            if random.random() < 0.07 * (1 - woodland):
                pygame.draw.circle(surface, (205, 200, 147), (world_x - 2, world_y - 4), 2)
            if random.random() < woodland * 0.4:
                pygame.draw.line(
                    surface, (122, 116, 76), (world_x - 3, world_y), (world_x + 2, world_y + 2), 2
                )

        elif biome == Biome.BEACH and random.random() < 0.28:
            if contains_biome(biomes, world_x, world_y, 9, Biome.BEACH):
                pygame.draw.arc(
                    surface, (182, 176, 133), (world_x - 7, world_y - 2, 15, 5), 0.1, 2.9, 1
                )


def create_water_glints(surface, biomes, random):
    glint = pygame.Surface((32, 3), pygame.SRCALPHA)
    pygame.draw.line(glint, (164, 209, 207, 24), (0, 1), (24, 1), 1)

    for _ in range(3200):
        world_x = int(random.integers(24, WORLD_WIDTH - 24))
        world_y = int(random.integers(24, WORLD_HEIGHT - 24))
        if contains_biome(biomes, world_x, world_y, 32, Biome.WATER):
            surface.blit(glint, (world_x, world_y))
