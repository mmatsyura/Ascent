import math

import numpy as np
import pygame

from game.settings import CITY_VISION_RADIUS, FOG_EDGE_WIDTH, MAP_SEED, TERRAIN_SCALE, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome
from game.world.noise import smooth_noise
from game.world.fog_geometry import border_distance, city_connected_mask


class Country:
    def __init__(self, terrain, cities, owner="blue"):
        self.owner = owner
        self.step = 32
        self.grid_size = 8
        self.revision = 0
        self.key = None
        self.geometry_key = None
        self.distances = None
        self.links = []
        self.fraction = 0.0
        self.area = 0
        self.control_revision = -1
        stride = self.step // TERRAIN_SCALE
        land = terrain.biomes != Biome.WATER
        rows, columns = land.shape
        self.land_weights = land.reshape(rows // stride, stride, columns // stride, stride).sum(axis=(1, 3))
        self.land_total = int(self.land_weights.sum())
        forest_stride = self.grid_size // TERRAIN_SCALE
        forest = terrain.biomes == Biome.FOREST
        self.forest = forest.reshape(rows // forest_stride, forest_stride, columns // forest_stride, forest_stride).any(axis=(1, 3))
        interior = self.forest.copy()
        depth = np.zeros(self.forest.shape, dtype=np.float32)
        for _ in range(7):
            depth += interior * self.grid_size
            padded = np.pad(interior, 1, mode='edge')
            interior = (padded[1:-1, 1:-1] & padded[:-2, 1:-1] & padded[2:, 1:-1]
                        & padded[1:-1, :-2] & padded[1:-1, 2:])
        self.forest_limit = (16 - depth) * (FOG_EDGE_WIDTH / 24)
        self.horizontal = (np.arange(WORLD_WIDTH // self.step, dtype=np.float32)[None, :] + .5) * self.step
        self.vertical = (np.arange(WORLD_HEIGHT // self.step, dtype=np.float32)[:, None] + .5) * self.step
        random = np.random.default_rng(MAP_SEED + 513)
        self.border_noise = np.zeros(self.land_weights.shape, dtype=np.float32)
        for columns, rows, amplitude in ((22, 15, 26), (64, 44, 13), (128, 88, 5)):
            self.border_noise += (smooth_noise(self.land_weights.shape[1], self.land_weights.shape[0], columns, rows, random) * 2 - 1) * amplitude
        self.update(cities)

    def enlarge(self, values):
        reach = FOG_EDGE_WIDTH * 2
        encoded = np.rint((np.clip(values, -reach, reach) + reach) * (255 / (reach * 2))).astype(np.uint8)
        colors = np.repeat(encoded.T[..., None], 3, axis=2)
        source = pygame.surfarray.make_surface(colors)
        scaled = pygame.transform.smoothscale(source, (WORLD_WIDTH // self.grid_size, WORLD_HEIGHT // self.grid_size))
        values = pygame.surfarray.array3d(scaled)[..., 0].T.astype(np.float32)
        return values * (reach * 2 / 255) - reach

    def update(self, cities):
        key = tuple((tuple(city.position), city.owner==self.owner) for city in cities.cities)
        if key == self.key:
            return False
        self.key = key
        self.control_revision = -1
        self.prepare_geometry(cities)
        owners = np.array([city.owner == self.owner for city in cities.cities], dtype=bool)
        shape = (WORLD_HEIGHT // self.step, WORLD_WIDTH // self.step)
        own_distance = self.distances[owners].min(axis=0) if owners.any() else np.full(shape, 1e12, dtype=np.float32)
        other_distance = self.distances[~owners].min(axis=0) if (~owners).any() else np.full(shape, 1e12, dtype=np.float32)
        field = (np.sqrt(other_distance) - np.sqrt(own_distance)) * .5
        corridor = np.full(shape, -1e6, dtype=np.float32)
        for first, second, bounds, connection, forest_connection in self.links:
            if not owners[first] or not owners[second]:
                continue
            left, top, right, bottom = bounds
            np.maximum(field[top:bottom, left:right], connection, out=field[top:bottom, left:right])
            np.maximum(corridor[top:bottom, left:right], forest_connection, out=corridor[top:bottom, left:right])
        if not owners.any():
            field.fill(-1e6)
        field += self.border_noise * np.clip(1 - np.abs(field) / 240, 0, 1)
        controlled = city_connected_mask(field>=0,[city.position for city in cities.cities if city.owner==self.owner],self.step)
        land_owned = int(self.land_weights[controlled].sum())
        self.fraction = land_owned / max(1, self.land_total)
        self.area = round(land_owned * TERRAIN_SCALE ** 2 / 4096)
        field=border_distance(controlled,self.step,FOG_EDGE_WIDTH*2+self.step)
        self.field = self.enlarge(field)
        self.vision = self.field.copy()
        forest_limit = self.forest_limit.copy()
        np.maximum(forest_limit, self.enlarge(corridor) * (FOG_EDGE_WIDTH / 24), out=forest_limit)
        np.minimum(self.vision, forest_limit, out=self.vision, where=self.forest)
        rows = np.flatnonzero(np.any(self.field >= -FOG_EDGE_WIDTH, axis=1))
        columns = np.flatnonzero(np.any(self.field >= -FOG_EDGE_WIDTH, axis=0))
        self.bounds = (pygame.Rect(int(columns[0]), int(rows[0]), int(columns[-1] - columns[0] + 1), int(rows[-1] - rows[0] + 1))
                       if len(rows) and len(columns) else pygame.Rect(0, 0, 0, 0))
        self.revision += 1
        return True

    def update_control(self, territory_field, revision):
        if revision == self.control_revision:
            return
        self.control_revision = revision
        stride = self.step // self.grid_size
        controlled = territory_field[stride // 2::stride, stride // 2::stride] >= 0
        land_owned = int(self.land_weights[controlled].sum())
        self.fraction = land_owned / max(1, self.land_total)
        self.area = round(land_owned * TERRAIN_SCALE ** 2 / 4096)

    def prepare_geometry(self, cities):
        positions = tuple(tuple(city.position) for city in cities.cities)
        if positions == self.geometry_key:
            return
        self.geometry_key = positions
        shape = (WORLD_HEIGHT // self.step, WORLD_WIDTH // self.step)
        self.distances = np.stack([((self.horizontal - city.position[0]) ** 2 + (self.vertical - city.position[1]) ** 2) / city.influence_weight ** 2 for city in cities.cities]) if positions else np.empty((0, *shape), dtype=np.float32)
        self.links = []
        maximum = CITY_VISION_RADIUS * 3.6
        for index, (x, y) in enumerate(positions):
            for other in range(index + 1, len(positions)):
                dx, dy = positions[other][0] - x, positions[other][1] - y
                length_squared = dx * dx + dy * dy
                if length_squared <= 1 or length_squared > maximum * maximum:
                    continue
                width = min(145, max(65, (maximum - math.sqrt(length_squared)) * .25 + 55))
                blocked = False
                for candidate, (city_x, city_y) in enumerate(positions):
                    if candidate in (index, other):
                        continue
                    t = max(0, min(1, ((city_x - x) * dx + (city_y - y) * dy) / length_squared))
                    if (city_x - x - t * dx) ** 2 + (city_y - y - t * dy) ** 2 < (width + 75) ** 2:
                        blocked = True
                        break
                if blocked:
                    continue
                left = max(0, math.floor((min(x, x + dx) - width - self.step) / self.step))
                right = min(shape[1], math.ceil((max(x, x + dx) + width + self.step) / self.step))
                top = max(0, math.floor((min(y, y + dy) - width - self.step) / self.step))
                bottom = min(shape[0], math.ceil((max(y, y + dy) + width + self.step) / self.step))
                horizontal, vertical = self.horizontal[:, left:right], self.vertical[top:bottom]
                fraction = np.clip(((horizontal - x) * dx + (vertical - y) * dy) / length_squared, 0, 1)
                distance = np.hypot(horizontal - x - fraction * dx, vertical - y - fraction * dy)
                self.links.append((index, other, (left, top, right, bottom), width - distance, width * .32 - distance))
