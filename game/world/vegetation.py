import pygame

from game.rendering import WorldSprite
from game.settings import TERRAIN_SCALE, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome
from game.world.decoration import contains_biome


def create_tree_images(random):
    images = []

    for style in range(32):
        radius = int(random.integers(13, 23))
        image = pygame.Surface((72, 100), pygame.SRCALPHA)
        base_x, base_y = 36, 88
        shade = int(random.integers(-7, 8))
        pygame.draw.line(image, (87, 79, 54), (base_x, base_y - 24), (base_x, base_y), 4)

        if style % 3 == 0:
            for spread, rise in [(radius, -12), (radius * .8, -25), (radius * .55, -37)]:
                points = [(base_x - spread, base_y + rise), (base_x, base_y + rise - 27), (base_x + spread, base_y + rise)]
                pygame.draw.polygon(image, (39 + shade, 76 + shade, 59 + shade), points)
                pygame.draw.polygon(image, (59 + shade, 99 + shade, 67 + shade), [points[0], points[1], (base_x, base_y + rise)])
        else:
            for offset_x, offset_y, size in [(0, -23, radius), (-8, -30, radius - 3), (7, -31, radius - 4), (-3, -40, radius - 6)]:
                center = (base_x + offset_x, base_y + offset_y)
                pygame.draw.circle(image, (44 + shade, 80 + shade, 55 + shade), center, size)
                pygame.draw.circle(image, (61 + shade, 101 + shade, 65 + shade), (center[0] - 3, center[1] - 4), size - 3)
                pygame.draw.circle(image, (77 + shade, 115 + shade, 72 + shade), (center[0] - 5, center[1] - 6), max(3, size // 3))

        images.append(image.convert_alpha())

    return images


def create_trees(ground_surface, biomes, forest_strength, random):
    images = create_tree_images(random)
    trees = []
    occupied_cells = set()
    shadow = pygame.Surface((70, 35), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (25, 45, 29, 25), (3, 3, 64, 29))
    pygame.draw.ellipse(shadow, (25, 45, 29, 25), (10, 7, 50, 21))

    for world_x, world_y in random.integers((80, 100), (WORLD_WIDTH - 80, WORLD_HEIGHT - 80), size=(72000, 2)):
        world_x, world_y = int(world_x), int(world_y)
        row, column = world_y // TERRAIN_SCALE, world_x // TERRAIN_SCALE
        strength = forest_strength[row, column]
        cell = (world_x // 28, world_y // 28)

        if cell in occupied_cells or random.random() > strength * .72:
            continue
        if biomes[row, column] != Biome.FOREST:
            continue
        if not contains_biome(biomes, world_x, world_y - 28, 39, Biome.FOREST):
            continue

        image = images[int(random.integers(len(images)))]
        trees.append(WorldSprite(image, (world_x, world_y), (36, 88)))
        occupied_cells.add(cell)
        ground_surface.blit(shadow, (world_x - 22, world_y - 10))

    return trees
