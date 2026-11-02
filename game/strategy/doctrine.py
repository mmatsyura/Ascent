from collections import Counter
import math

import pygame

from game.strategy.knowledge import strength
from game.world.biomes import Biome


class Doctrine:
    def __init__(self, leader):
        self.leader = leader
        self.target = None
        self.target_since = 0
        self.wave_started = 0
        self.air_hotspots = {}
        self.squad_targets = {}

    def army(self):
        leader = self.leader
        app = leader.app
        troops = [unit for unit in app.units if unit.owner == leader.owner]
        cities = [city for city in app.city_map.cities if city.owner == leader.owner]
        if not troops:
            return
        active = set(troops)
        leader.orders = {unit: order for unit, order in leader.orders.items() if unit in active}
        self.squad_targets = {
            unit: target for unit, target in self.squad_targets.items() if unit in active
        }
        contacts = [
            contact
            for contact in leader.knowledge.contacts.values()
            if leader.elapsed - contact.time < 12
        ]
        aircraft = [
            drone
            for fleet in app.strategy.fleets
            for drone in fleet.drones
            if drone.owner != leader.owner
            and drone.controllable
            and leader.knowledge.is_visible(drone.position)
        ]
        for drone in aircraft:
            cell = (int(drone.position[0] // 320), int(drone.position[1] // 320))
            count, _ = self.air_hotspots.get(cell, (0, 0))
            self.air_hotspots[cell] = (min(20, count + 1), leader.elapsed)
        self.air_hotspots = {
            cell: state
            for cell, state in self.air_hotspots.items()
            if leader.elapsed - state[1] < 120
        }
        objectives = [
            memory for memory in leader.knowledge.cities.values() if memory.owner != leader.owner
        ]
        center = sum((pygame.Vector2(unit.position) for unit in troops), pygame.Vector2()) / len(
            troops
        )
        current = leader.knowledge.cities.get(self.target)
        if not current or current.owner == leader.owner or leader.elapsed - self.target_since > 90:
            if objectives:

                def score(memory):
                    danger = leader.knowledge.threat(memory.position, 600)
                    city_value = 450 if memory.target.capital else 150
                    return center.distance_to(memory.position) + danger * 110 - city_value

                self.target = min(objectives, key=score).target
                self.target_since = leader.elapsed
                self.wave_started = 0
            else:
                self.target = None
        reserve = set()
        assigned = Counter()
        endangered = sorted(cities, key=lambda city: -leader.knowledge.threat(city.position, 520))
        for city in endangered:
            if len(reserve) >= max(2, len(troops) // 3):
                break
            danger = leader.knowledge.threat(city.position, 520)
            if danger < 1:
                continue
            candidates = sorted(
                (
                    unit
                    for unit in troops
                    if not unit.is_patriot
                    and unit not in reserve
                    and unit.health > 45
                    and unit.readiness > 30
                ),
                key=lambda unit: pygame.Vector2(unit.position).distance_squared_to(city.position),
            )
            total = 0
            for unit in candidates[: max(3, min(10, math.ceil(danger * 1.5)))]:
                leader.order(unit, city.position, "defend")
                reserve.add(unit)
                total += strength(unit)
                if total > danger * 1.4:
                    break
        ppo = [unit for unit in troops if unit.is_patriot]
        bases = [building for building in app.buildings.buildings if building.owner == leader.owner]
        guard_points = []
        for cell, (count, time) in self.air_hotspots.items():
            point = ((cell[0] + 0.5) * 320, (cell[1] + 0.5) * 320)
            guard_points.append((count * 8, point))
        for base in bases:
            concentration = sum(
                pygame.Vector2(base.position).distance_squared_to(other.position) < 600**2
                for other in bases
            )
            value = (
                concentration * 2
                + (7 if base.definition.key == "airport" else 3)
                + leader.knowledge.threat(base.position)
            )
            guard_points.append((value, base.position))
        if self.target is not None:
            guard_points.append((12, self.staging(self.target.position, cities)))
        guarded = []
        for unit in ppo:
            options = [
                (value / (1 + pygame.Vector2(unit.position).distance_to(point) / 2200), point)
                for value, point in guard_points
                if not any(
                    pygame.Vector2(point).distance_squared_to(previous) < 550**2
                    for previous in guarded
                )
            ]
            if not options:
                continue
            _, point = max(options, key=lambda item: item[0])
            point = self.safe(point)
            guarded.append(point)
            if pygame.Vector2(unit.position).distance_to(point) > 140:
                leader.order(unit, point, "air_defense")
        push = [unit for unit in troops if unit not in reserve and not unit.is_patriot]
        rally = self.staging(self.target.position, cities) if self.target is not None else None
        if rally is not None:
            ready = [
                unit
                for unit in push
                if pygame.Vector2(unit.position).distance_squared_to(rally) < 420**2
                and unit.health > 45
                and unit.readiness > 35
            ]
            local = leader.knowledge.threat(self.target.position, 650)
            required = max(4, min(12, math.ceil(local * 1.5)))
            if len(ready) >= required or (
                len(ready) >= 3 and leader.elapsed - self.target_since > 70
            ):
                self.wave_started = leader.elapsed if not self.wave_started else self.wave_started
        for unit in push:
            neighbors = [
                other
                for other in troops
                if pygame.Vector2(unit.position).distance_squared_to(other.position) < 440**2
            ]
            support = sum(strength(other) for other in neighbors)
            nearby = [
                contact
                for contact in contacts
                if pygame.Vector2(unit.position).distance_squared_to(contact.position) < 500**2
            ]
            tanks = [
                contact
                for contact in nearby
                if contact.target.is_tank and not contact.target.is_patriot
            ]
            counter_support = any(
                (other.is_tank and not other.is_patriot) or other.is_anti_tank
                for other in neighbors
            )
            retreat = (
                unit.health < 38
                or unit.readiness < 20
                or leader.knowledge.threat(unit.position) > support * 1.2
            )
            retreat = retreat or (
                bool(tanks) and not unit.is_tank and not unit.is_anti_tank and not counter_support
            )
            old = leader.orders.get(unit)
            if old and old[1] == "retreat" and (unit.health < 75 or unit.readiness < 65):
                retreat = True
            if retreat and cities:
                refuge = min(
                    cities,
                    key=lambda city: pygame.Vector2(unit.position).distance_to(city.position)
                    + leader.knowledge.threat(city.position) * 500,
                )
                leader.order(
                    unit,
                    self.safe(pygame.Vector2(refuge.position) + pygame.Vector2(100, 65)),
                    "retreat",
                )
                continue
            operations = app.strategy.operations
            near = [
                building
                for building in app.buildings.buildings
                if building.owner != leader.owner
                and leader.knowledge.is_visible(building.position)
                and pygame.Vector2(unit.position).distance_squared_to(building.position) < 165**2
            ]
            if near:
                building = min(
                    near,
                    key=lambda building: pygame.Vector2(unit.position).distance_squared_to(
                        building.position
                    ),
                )
                if operations.entitled(building, leader.owner):
                    operations.demolish(building, leader.owner)
                elif building not in operations.orders:
                    operations.start(building, leader.owner, "destroy", [unit])
                continue
            if any(unit in order.participants for order in operations.orders.values()):
                continue
            targets = [
                contact for contact in nearby if leader.knowledge.is_visible(contact.position)
            ]
            if targets and support >= leader.knowledge.threat(unit.position) * 1.1:
                target = min(
                    targets,
                    key=lambda contact: pygame.Vector2(unit.position).distance_to(contact.position)
                    - (200 if unit.is_anti_tank and contact.target.is_tank else 0),
                )
                reach = 80 if unit.is_anti_tank else 65 if unit.is_tank else 48
                vector = pygame.Vector2(unit.position) - target.position
                point = pygame.Vector2(target.position) + (
                    vector.normalize() * reach
                    if vector.length_squared()
                    else pygame.Vector2(reach, 0)
                )
                leader.order(unit, self.safe(point), "attack")
                continue
            cleanup = [
                memory
                for memory in leader.knowledge.buildings.values()
                if memory.owner != leader.owner and leader.elapsed - memory.time < 45
            ]
            cleanup = [
                memory for memory in cleanup if operations.entitled(memory.target, leader.owner)
            ]
            if cleanup:
                building = min(
                    cleanup,
                    key=lambda memory: pygame.Vector2(unit.position).distance_squared_to(
                        memory.position
                    ),
                ).target
                if building in app.buildings.buildings:
                    operations.demolish(building, leader.owner)
            if self.target is not None:
                if not self.wave_started:
                    index = push.index(unit)
                    point = pygame.Vector2(rally) + pygame.Vector2(75, 0).rotate(index * 137.5)
                    leader.order(unit, self.safe(point), "rally")
                else:
                    index = push.index(unit)
                    point = (
                        self.target.position
                        if index < 3
                        else pygame.Vector2(self.target.position)
                        + pygame.Vector2(60 + index % 3 * 25, 0).rotate(index * 137.5)
                    )
                    leader.order(unit, self.safe(point), "capture")
            elif not unit.route and unit.planning_target is None:
                point = leader.explore(unit.position, set())
                if point:
                    leader.order(unit, point, "explore")

    def safe(self, point):
        app = self.leader.app
        origin = pygame.Vector2(point)
        for radius in (0, 32, 64, 100, 160, 230):
            for angle in range(0, 360, 45):
                candidate = origin + pygame.Vector2(radius, 0).rotate(angle)
                if app.terrain.biome_at(candidate) != Biome.WATER and app.terrain.can_place_unit(
                    candidate, 8
                ):
                    return tuple(candidate)
        return tuple(origin)

    def staging(self, target, cities):
        if not cities:
            return self.safe(target)
        city = min(
            cities,
            key=lambda city: pygame.Vector2(target).distance_squared_to(city.position)
            + self.leader.knowledge.threat(city.position) * 150000,
        )
        origin = pygame.Vector2(city.position)
        offset = pygame.Vector2(target) - origin
        return (
            self.safe(origin + offset.normalize() * min(350, offset.length() * 0.35))
            if offset.length_squared()
            else tuple(origin)
        )
