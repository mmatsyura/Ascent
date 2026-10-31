from collections import OrderedDict
import math

import numpy as np

from game.settings import FOG_EDGE_WIDTH, TERRAIN_SCALE
from game.world.biomes import Biome


class ForestVisibility:
    def __init__(self, terrain, grid_size):
        self.grid_size = grid_size
        stride = grid_size // TERRAIN_SCALE
        forest = terrain.biomes == Biome.FOREST
        rows, columns = forest.shape
        self.forest = forest.reshape(rows // stride, stride, columns // stride, stride).any(axis=(1, 3))
        self.cache = OrderedDict()

    def field(self, source, bounds):
        key = (source.position, source.radius, tuple(bounds))
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        grid = self.grid_size
        horizontal = np.arange(bounds.left, bounds.right, dtype=np.float32)[None, :] * grid - source.position[0]
        vertical = np.arange(bounds.top, bounds.bottom, dtype=np.float32)[:, None] * grid - source.position[1]
        distance = np.hypot(horizontal, vertical)
        divisor = np.maximum(distance, 1)
        direction_x, direction_y = horizontal / divisor, vertical / divisor
        entry = np.full(distance.shape, np.inf, dtype=np.float32)
        for travel in range(grid, math.ceil(distance.max()) + grid, grid):
            active = (travel <= distance + grid * .5) & np.isinf(entry)
            if not active.any():
                break
            columns = np.clip(((source.position[0] + direction_x * travel) / grid).astype(np.int32), 0, self.forest.shape[1] - 1)
            rows = np.clip(((source.position[1] + direction_y * travel) / grid).astype(np.int32), 0, self.forest.shape[0] - 1)
            hit = active & self.forest[rows, columns]
            entry[hit] = travel
        forest_limit = (entry + 16 - distance) * (FOG_EDGE_WIDTH / 24)
        result = np.minimum(source.radius - distance, forest_limit)
        self.cache[key] = result
        if len(self.cache) > 64:
            self.cache.popitem(last=False)
        return result
