from collections import Counter
import random

import pygame

from game.aircraft.fleet import DroneFleet
from game.aircraft.strikes import DroneStrikes
from game.kingdom import Kingdom
from game.settings import WORLD_WIDTH, WORLD_HEIGHT
from game.world.biomes import Biome
from game.world.intelligence import Intelligence
from game.world.recruitment import Recruitment
from game.strategy.economy import Development
from game.strategy.knowledge import Knowledge, strength


class Commander:
    def __init__(self, app, owner, index):
        self.app = app
        self.owner = owner
        self.kingdom = Kingdom()
        self.elapsed = 0
        self.income_credit = 0
        self.next_think = .5 + index * .6
        self.random = random.Random(913 + index)
        self.knowledge = Knowledge(app, owner)
        self.fleet = DroneFleet(self.kingdom, app.buildings, owner)
        self.fleet.combat = DroneStrikes(self.fleet, app.units, app.buildings, self.knowledge, Intelligence(), lambda message: None)
        self.fleet.combat.on_impact = self.report_strike
        self.fleet.combat.on_explosion = lambda point: app.soundscape.explode(point, app.camera) if app.focused and app.visibility.is_visible(point) else None
        self.recruitment = Recruitment(self.kingdom, app.buildings, app.unit_control, lambda message: None, owner)
        self.development = Development(self)
        self.orders = {}
        self.retreat_until = {}
        self.statistics = Counter()
        self.knowledge.refresh(0, self.fleet)

    def report_strike(self, drone, target, outcome):
        if target.owner == "blue" or self.app.visibility.is_visible(drone.position):
            self.app.intelligence.record(outcome, drone.position, "Удар ворожого дрона")

    def update(self, duration):
        self.elapsed += duration
        income = 1 + sum(building.definition.income_per_second for building in self.app.buildings.buildings
                         if building.owner == self.owner and building.completed)
        self.income_credit += duration * income
        paid = int(self.income_credit)
        self.kingdom.gold += paid
        self.income_credit -= paid
        self.recruitment.update(duration)
        self.fleet.update(duration)
        self.fleet.events.clear()
        if self.elapsed >= self.next_think:
            self.next_think = self.elapsed + 2.0
            self.knowledge.refresh(self.elapsed, self.fleet)
            self.development.think()
            self.command_army()
            self.command_aircraft()

    def order(self, unit, point, mode):
        old = self.orders.get(unit)
        if old and old[1] == mode and pygame.Vector2(old[0]).distance_squared_to(point) < 120**2:
            if unit.route or unit.planning_target or pygame.Vector2(unit.position).distance_squared_to(point) < 55**2:
                return
            if self.elapsed - old[2] < 12:
                return
        self.orders[unit] = (tuple(point), mode, self.elapsed)
        self.app.unit_control.path_planner.submit(((unit, [tuple(point)]),))
        self.statistics[mode] += 1

    def explore(self, origin, reserved):
        options = []
        for _ in range(36):
            distance = self.random.uniform(400, 1050)
            point = pygame.Vector2(origin) + pygame.Vector2(distance, 0).rotate(self.random.randrange(360))
            if not (160 < point.x < WORLD_WIDTH-160 and 160 < point.y < WORLD_HEIGHT-160):
                continue
            cell = (int(point.x//256), int(point.y//256))
            if cell in self.knowledge.explored or cell in reserved:
                continue
            if self.app.terrain.biome_at(point) == Biome.WATER or not self.app.terrain.can_place_soldier(point, 4):
                continue
            options.append((distance, tuple(point), cell))
        if not options:
            return None
        _, point, cell = min(options)
        reserved.add(cell)
        return point

    def command_army(self):
        troops = [unit for unit in self.app.units if unit.owner == self.owner]
        present = set(troops)
        self.orders = {unit: order for unit, order in self.orders.items() if unit in present}
        self.retreat_until = {unit: until for unit, until in self.retreat_until.items() if unit in present}
        cities = [city for city in self.app.city_map.cities if city.owner == self.owner]
        reserved = set()
        assigned = Counter()
        for unit in troops:
            nearby = [other for other in troops if pygame.Vector2(unit.position).distance_squared_to(other.position) < 460**2]
            support = sum(strength(other) for other in nearby)
            threat = self.knowledge.threat(unit.position)
            if unit.health < 28 or threat > support * 1.35:
                self.retreat_until[unit] = self.elapsed + 12
            if self.retreat_until.get(unit, 0) > self.elapsed and cities:
                refuge = min(cities, key=lambda city: pygame.Vector2(unit.position).distance_to(city.position) + self.knowledge.threat(city.position)*450)
                offset = pygame.Vector2(unit.position) - refuge.position
                destination = pygame.Vector2(refuge.position) + (offset.normalize()*110 if offset.length_squared() else pygame.Vector2(110,0))
                self.order(unit, destination, 'retreat')
                continue
            if unit.is_patriot:
                protected = [building for building in self.app.buildings.buildings if building.owner == self.owner and building.definition.key == 'airport']
                anchor = min(protected or cities, key=lambda item: pygame.Vector2(unit.position).distance_squared_to(item.position), default=None)
                if anchor and pygame.Vector2(unit.position).distance_to(anchor.position) > 180:
                    self.order(unit, pygame.Vector2(anchor.position)+pygame.Vector2(95,70), 'air_defense')
                continue
            threats = [contact for contact in self.knowledge.contacts.values() if self.elapsed-contact.time < 6
                       and pygame.Vector2(unit.position).distance_to(contact.position) < 620]
            if threats and support > threat * 1.15:
                target = min(threats, key=lambda contact: contact.strength*80 + pygame.Vector2(unit.position).distance_to(contact.position))
                self.order(unit, target.position, 'attack')
                continue
            endangered = [city for city in cities if self.knowledge.threat(city.position) > 1.5]
            if endangered:
                city = min(endangered, key=lambda city: pygame.Vector2(unit.position).distance_to(city.position) + assigned[city]*220)
                if assigned[city] < 4:
                    assigned[city] += 1
                    self.order(unit, city.position, 'defend')
                    continue
            objectives = []
            for city, memory in self.knowledge.cities.items():
                if memory.owner == self.owner or assigned[city] >= 3:
                    continue
                danger = self.knowledge.threat(memory.position)
                if danger > support*1.1:
                    continue
                distance = pygame.Vector2(unit.position).distance_to(memory.position)
                score = distance + danger*240 + assigned[city]*160 - (150 if city.capital else 0)
                objectives.append((score, city))
            if objectives:
                city = min(objectives, key=lambda item: item[0])[1]
                assigned[city] += 1
                self.order(unit, city.position, 'capture')
            elif not unit.route and unit.planning_target is None:
                point = self.explore(unit.position, reserved)
                if point:
                    self.order(unit, point, 'explore')

    def command_aircraft(self):
        assigned = Counter(drone.attack_target for drone in self.fleet.drones if drone.attack_target is not None)
        reserved = set()
        for drone in self.fleet.drones:
            if not drone.controllable:
                continue
            if drone.definition.strike and drone.attack_target is None:
                contacts = [*self.knowledge.contacts.values(), *self.knowledge.buildings.values()]
                contacts = [contact for contact in contacts if self.knowledge.is_visible(contact.position)
                            and self.fleet.combat.valid(contact.target) and assigned[contact.target] < 2]
                if contacts:
                    def score(contact):
                        value = 3 if getattr(contact.target, 'is_patriot', False) else 2 if hasattr(contact.target, 'definition') else 1
                        return pygame.Vector2(drone.position).distance_to(contact.position) / (value * self.fleet.combat.chance(contact.target))
                    target = min(contacts, key=score).target
                    if self.fleet.combat.assign(drone, target):
                        assigned[target] += 1
                        self.statistics['air_strike'] += 1
                        continue
            if not drone.route and drone.attack_target is None:
                point = self.explore(drone.position, reserved)
                if point:
                    self.fleet.assign_route(drone, [point])
