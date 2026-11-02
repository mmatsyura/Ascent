import heapq
import math

import pygame

from game.settings import WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome


class AirRoutes:
    def __init__(self, terrain):
        self.terrain = terrain
        self.step = 96
        self.cache = {}
        self.edges = {}

    def dry(self, point):
        return self.terrain.biome_at(point) not in (None, Biome.WATER)

    def clear(self, start, end):
        first = pygame.Vector2(start)
        distance = first.distance_to(end)
        count = max(1, math.ceil(distance / 24))
        return all(self.dry(first.lerp(end, index / count)) for index in range(count + 1))

    def point(self, cell):
        return ((cell[0] + 0.5) * self.step, (cell[1] + 0.5) * self.step)

    def route(self, start, end):
        if not self.dry(end):
            return []
        if self.clear(start, end):
            return [tuple(end)]
        source = (int(start[0] // self.step), int(start[1] // self.step))
        destination = (int(end[0] // self.step), int(end[1] // self.step))
        key = (source, destination)
        if key in self.cache:
            path = self.cache[key]
            if not path:
                if self.clear(start, self.point(source)) and self.clear(
                    end, self.point(destination)
                ):
                    return []
            elif self.clear(start, path[0]):
                updated = path[:-1] + [tuple(end)]
                previous = updated[-2] if len(updated) > 1 else start
                if self.clear(previous, end):
                    return updated
        queue = [(0, source)]
        cost = {source: 0}
        parents = {}
        found = None
        while queue:
            _, cell = heapq.heappop(queue)
            point = start if cell == source else self.point(cell)
            if (
                abs(cell[0] - destination[0]) <= 1
                and abs(cell[1] - destination[1]) <= 1
                and self.clear(point, end)
            ):
                found = cell
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                other = (cell[0] + dx, cell[1] + dy)
                if not (
                    0 <= other[0] < WORLD_WIDTH // self.step
                    and 0 <= other[1] < WORLD_HEIGHT // self.step
                ):
                    continue
                target = self.point(other)
                new = cost[cell] + (1.414 if dx and dy else 1)
                if new >= cost.get(other, 1e10):
                    continue
                edge = tuple(sorted((cell, other)))
                if cell == source:
                    allowed = self.clear(point, target)
                else:
                    if edge not in self.edges:
                        self.edges[edge] = self.clear(point, target)
                    allowed = self.edges[edge]
                if not allowed:
                    continue
                cost[other] = new
                parents[other] = cell
                score = new + math.hypot(other[0] - destination[0], other[1] - destination[1])
                heapq.heappush(queue, (score, other))
        if found is None:
            if self.clear(start, self.point(source)) and self.clear(end, self.point(destination)):
                self.cache[key] = []
                if len(self.cache) > 128:
                    self.cache.pop(next(iter(self.cache)))
            return []
        path = [tuple(end)]
        while found != source:
            path.append(self.point(found))
            found = parents[found]
        path.reverse()
        simplified = []
        origin = start
        index = 0
        while index < len(path):
            far = index
            for candidate in range(index + 1, len(path)):
                if not self.clear(origin, path[candidate]):
                    break
                far = candidate
            simplified.append(path[far])
            origin = path[far]
            index = far + 1
        self.cache[key] = simplified
        if len(self.cache) > 128:
            self.cache.pop(next(iter(self.cache)))
        return simplified.copy()
