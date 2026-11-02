from dataclasses import dataclass
import math

import pygame

from game.settings import CAPITAL_VISION_RADIUS, CITY_VISION_RADIUS
from game.world.biomes import Biome
from game.world.country import Country


@dataclass
class Observation:
    target: object
    position: tuple
    owner: str
    time: float
    strength: float = 0


def strength(unit):
    return (
        (0.5 if unit.is_patriot else 2 if unit.is_anti_tank else 2.4 if unit.is_tank else 1)
        * max(0.15, unit.health / 100)
        * (0.35 + 0.65 * unit.readiness / 100)
    )


class Knowledge:
    def __init__(self, app, owner):
        self.app = app
        self.owner = owner
        self.country = Country(app.terrain, app.city_map, owner)
        self.sources = {}
        self.cities = {}
        self.contacts = {}
        self.buildings = {}
        self.explored = set()
        self.elapsed = 0

    def refresh(self, elapsed, fleet):
        self.elapsed = elapsed
        self.country.update(self.app.city_map)
        for row in range(0, self.country.field.shape[0], 32):
            for column in range(0, self.country.field.shape[1], 32):
                if self.country.field[row, column] >= 0:
                    self.explored.add((column // 32, row // 32))
        sources = [
            (city.position, CAPITAL_VISION_RADIUS if city.capital else CITY_VISION_RADIUS, True)
            for city in self.app.city_map.cities
            if city.owner == self.owner
        ]
        sources.extend(
            (unit.position, unit.vision_radius, False)
            for unit in self.app.units
            if unit.owner == self.owner
        )
        sources.extend(
            (building.position, building.definition.vision_radius, True)
            for building in self.app.buildings.buildings
            if building.owner == self.owner and building.completed
        )
        sources.extend(
            (drone.position, drone.vision_radius, False)
            for drone in fleet.drones
            if drone.controllable
        )
        self.sources.clear()
        for point, radius, forest_blocked in sources:
            for row in range(
                math.floor((point[1] - radius) / 256), math.floor((point[1] + radius) / 256) + 1
            ):
                for column in range(
                    math.floor((point[0] - radius) / 256), math.floor((point[0] + radius) / 256) + 1
                ):
                    self.sources.setdefault((column, row), []).append(
                        (point, radius, forest_blocked)
                    )
            self.explored.add((int(point[0] // 256), int(point[1] // 256)))
        for city in self.app.city_map.cities:
            previous = self.cities.get(city)
            if (
                city.owner == self.owner
                or (previous is not None and previous.owner == self.owner)
                or self.is_visible(city.position)
            ):
                self.cities[city] = Observation(city, tuple(city.position), city.owner, elapsed)
        for unit in self.app.units:
            if unit.owner != self.owner and self.is_visible(unit.position):
                self.contacts[unit] = Observation(
                    unit, tuple(unit.position), unit.owner, elapsed, strength(unit)
                )
        for building in self.app.buildings.buildings:
            if building.owner != self.owner and self.is_visible(building.position):
                self.buildings[building] = Observation(
                    building, tuple(building.position), building.owner, elapsed
                )
        present = set(self.app.units) | set(self.app.buildings.buildings)
        for memory in (self.contacts, self.buildings):
            for target, observation in tuple(memory.items()):
                if (
                    target.owner == self.owner
                    or elapsed - observation.time > 45
                    or (
                        self.is_visible(observation.position)
                        and (target not in present or not self.is_visible(target.position))
                    )
                ):
                    del memory[target]

    def is_visible(self, point):
        x, y = int(point[0] // 8), int(point[1] // 8)
        if (
            0 <= y < self.country.vision.shape[0]
            and 0 <= x < self.country.vision.shape[1]
            and self.country.vision[y, x] >= 0
        ):
            return True
        for origin, radius, forest_blocked in self.sources.get(
            (int(point[0] // 256), int(point[1] // 256)), ()
        ):
            offset = pygame.Vector2(point) - origin
            if offset.length_squared() > radius**2:
                continue
            if forest_blocked:
                steps = max(1, int(offset.length() / 24))
                forest = 0
                for index in range(1, steps + 1):
                    sample = pygame.Vector2(origin) + offset * (index / steps)
                    forest = forest + 24 if self.app.terrain.biome_at(sample) == Biome.FOREST else 0
                    if forest > 24:
                        break
                if forest > 24:
                    continue
            return True
        return False

    def threat(self, point, radius=440):
        return sum(
            contact.strength * max(0, 1 - (self.elapsed - contact.time) / 45)
            for contact in self.contacts.values()
            if pygame.Vector2(point).distance_squared_to(contact.position) < radius**2
        )
