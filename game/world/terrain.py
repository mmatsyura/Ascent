import math

import numpy as np
import pygame

from game.settings import TERRAIN_SCALE, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome
from game.world.decoration import create_water_glints, decorate_terrain
from game.world.generation import generate_terrain
from game.world.vegetation import create_trees

BIOME_VALUES = tuple(Biome)


class Terrain:
    def __init__(self):
        self.revision = 0
        colors, self.biomes, self.forest_strength, random = generate_terrain()
        terrain_surface = pygame.surfarray.make_surface(colors.transpose(1, 0, 2))
        self.surface = pygame.transform.smoothscale(
            terrain_surface, (WORLD_WIDTH, WORLD_HEIGHT)
        ).convert()
        decorate_terrain(self.surface, self.biomes, self.forest_strength, random)
        create_water_glints(self.surface, self.biomes, random)
        self.trees = create_trees(self.surface, self.biomes, self.forest_strength, random)
        self.scenery = list(self.trees)

        self.walkable = np.isin(self.biomes, [Biome.MEADOW, Biome.FOREST, Biome.BEACH, Biome.WATER])
        self.soldier_walkable = self.walkable.copy()
        self.buildable = self.biomes == Biome.MEADOW
        self.mask_views = {
            id(mask): memoryview(mask)
            for mask in (self.walkable, self.soldier_walkable, self.buildable)
        }
        for tree in self.trees:
            column = int(tree.position[0]) // TERRAIN_SCALE
            row = int(tree.position[1]) // TERRAIN_SCALE
            self.soldier_walkable[row, column] = False

        self.detail_levels = [self.surface]

        for _ in range(4):
            previous_level = self.detail_levels[-1]
            next_size = (previous_level.get_width() // 2, previous_level.get_height() // 2)
            self.detail_levels.append(pygame.transform.smoothscale(previous_level, next_size))

        self.scenery_detail_levels = [self.surface.copy()]
        scenery_surface = self.scenery_detail_levels[0]
        for sprite in sorted(self.scenery, key=lambda item: item.position[1]):
            scenery_surface.blit(
                sprite.image,
                (
                    round(sprite.position[0] - sprite.anchor[0]),
                    round(sprite.position[1] - sprite.anchor[1]),
                ),
            )
        for level in range(1, len(self.detail_levels)):
            self.scenery_detail_levels.append(
                pygame.transform.smoothscale(
                    self.scenery_detail_levels[-1], self.detail_levels[level].get_size()
                )
            )

    def create_overview(self, size):
        level = 0
        while level + 1 < len(self.scenery_detail_levels):
            candidate = self.scenery_detail_levels[level + 1]
            if candidate.get_width() < size[0] or candidate.get_height() < size[1]:
                break
            level += 1
        return pygame.transform.smoothscale(self.scenery_detail_levels[level], size)

    def biome_at(self, position):
        world_x, world_y = position
        if not (0 <= world_x < WORLD_WIDTH and 0 <= world_y < WORLD_HEIGHT):
            return None
        return BIOME_VALUES[
            self.biomes[int(world_y) // TERRAIN_SCALE, int(world_x) // TERRAIN_SCALE]
        ]

    def _area_is_allowed(self, area, allowed_mask):
        left, top, width, height = area
        right, bottom = left + width, top + height
        if (
            width <= 0
            or height <= 0
            or left < 0
            or top < 0
            or right > WORLD_WIDTH
            or bottom > WORLD_HEIGHT
        ):
            return False

        first_column = math.floor((left + 1e-7) / TERRAIN_SCALE)
        first_row = math.floor((top + 1e-7) / TERRAIN_SCALE)
        last_column = math.ceil((right - 1e-7) / TERRAIN_SCALE)
        last_row = math.ceil((bottom - 1e-7) / TERRAIN_SCALE)
        if last_row - first_row <= 4 and last_column - first_column <= 4:
            view = self.mask_views[id(allowed_mask)]
            for row in range(first_row, last_row):
                for column in range(first_column, last_column):
                    if not view[row, column]:
                        return False
            return True
        return bool(np.all(allowed_mask[first_row:last_row, first_column:last_column]))

    def can_place_building(self, area):
        return self._area_is_allowed(area, self.buildable)

    def reserve_building(self, area):
        first_column = math.floor(area.left / TERRAIN_SCALE)
        first_row = math.floor(area.top / TERRAIN_SCALE)
        last_column = math.ceil(area.right / TERRAIN_SCALE)
        last_row = math.ceil(area.bottom / TERRAIN_SCALE)
        patches = []
        for mask in (self.walkable, self.soldier_walkable, self.buildable):
            patches.append(mask[first_row:last_row, first_column:last_column].copy())
            mask[first_row:last_row, first_column:last_column] = False
        self.revision += 1
        return (first_column, first_row, last_column, last_row), tuple(patches)

    def release_building(self, reservation):
        (left, top, right, bottom), patches = reservation
        for mask, patch in zip((self.walkable, self.soldier_walkable, self.buildable), patches):
            mask[top:bottom, left:right] = patch
        self.revision += 1

    def can_place_unit(self, position, radius=8):
        if radius <= 0:
            return False
        world_x, world_y = position
        return self._area_is_allowed(
            (world_x - radius, world_y - radius, radius * 2, radius * 2), self.walkable
        )

    def can_move(self, start, destination, radius=8):
        return self._can_move_on_mask(start, destination, radius, self.walkable)

    def can_place_soldier(self, position, radius=4):
        if radius <= 0:
            return False
        horizontal, vertical = position
        return self._area_is_allowed(
            (horizontal - radius, vertical - radius, radius * 2, radius * 2), self.soldier_walkable
        )

    def can_move_soldier(self, start, destination, radius=4):
        return self._can_move_on_mask(start, destination, radius, self.soldier_walkable)

    def _can_move_on_mask(self, start, destination, radius, allowed_mask):
        if radius <= 0:
            return False
        start = pygame.Vector2(start)
        destination = pygame.Vector2(destination)
        left = min(start.x, destination.x) - radius
        top = min(start.y, destination.y) - radius
        right = max(start.x, destination.x) + radius
        bottom = max(start.y, destination.y) + radius
        if left < 0 or top < 0 or right > WORLD_WIDTH or bottom > WORLD_HEIGHT:
            return False
        if self._area_is_allowed((left, top, right - left, bottom - top), allowed_mask):
            return True
        if not self._area_is_allowed(
            (start.x - radius, start.y - radius, radius * 2, radius * 2), allowed_mask
        ):
            return False
        if not self._area_is_allowed(
            (destination.x - radius, destination.y - radius, radius * 2, radius * 2), allowed_mask
        ):
            return False

        first_column = max(0, math.floor(left / TERRAIN_SCALE))
        first_row = max(0, math.floor(top / TERRAIN_SCALE))
        if start.distance_squared_to(destination) > 32**2:
            count = math.ceil(start.distance_to(destination) / TERRAIN_SCALE)
            fractions = np.linspace(0, 1, count + 1)
            extent = math.ceil(radius / TERRAIN_SCALE) + 1
            offsets = np.arange(-extent, extent + 1)
            offset_x, offset_y = np.meshgrid(offsets, offsets)
            center_x = np.floor(
                (start.x + (destination.x - start.x) * fractions) / TERRAIN_SCALE
            ).astype(np.int32)
            center_y = np.floor(
                (start.y + (destination.y - start.y) * fractions) / TERRAIN_SCALE
            ).astype(np.int32)
            columns = np.clip(
                center_x[:, None] + offset_x.ravel(), 0, allowed_mask.shape[1] - 1
            ).ravel()
            rows = np.clip(
                center_y[:, None] + offset_y.ravel(), 0, allowed_mask.shape[0] - 1
            ).ravel()
            blocked = ~allowed_mask[rows, columns]
            if not blocked.any():
                return True
            indices = np.unique(rows[blocked] * allowed_mask.shape[1] + columns[blocked])
            rows, columns = indices // allowed_mask.shape[1], indices % allowed_mask.shape[1]
            first_row = first_column = 0
        else:
            last_column = min(allowed_mask.shape[1], math.ceil(right / TERRAIN_SCALE))
            last_row = min(allowed_mask.shape[0], math.ceil(bottom / TERRAIN_SCALE))
            rows, columns = np.nonzero(~allowed_mask[first_row:last_row, first_column:last_column])
        entry_times = np.zeros(len(rows), dtype=np.float64)
        exit_times = np.ones(len(rows), dtype=np.float64)
        for origin, movement, coordinates, first_cell in (
            (start.x, destination.x - start.x, columns, first_column),
            (start.y, destination.y - start.y, rows, first_row),
        ):
            minimum = (coordinates + first_cell) * TERRAIN_SCALE - radius + 1e-7
            maximum = (coordinates + first_cell + 1) * TERRAIN_SCALE + radius - 1e-7
            if abs(movement) < 1e-12:
                entry_times[(origin <= minimum) | (origin >= maximum)] = 2
            else:
                first_hit = (minimum - origin) / movement
                last_hit = (maximum - origin) / movement
                np.maximum(entry_times, np.minimum(first_hit, last_hit), out=entry_times)
                np.minimum(exit_times, np.maximum(first_hit, last_hit), out=exit_times)
        return not bool(np.any(entry_times <= exit_times))
