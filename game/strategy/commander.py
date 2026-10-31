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
from game.strategy.doctrine import Doctrine
from game.strategy.air_routes import AirRoutes
from game.strategy.air_missions import AirMissions


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
        self.doctrine = Doctrine(self)
        if not hasattr(app,"air_routes"):
            app.air_routes=AirRoutes(app.terrain)
        self.air_routes = app.air_routes
        self.fleet.air_routes = self.air_routes
        self.air_missions = AirMissions(self)
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
            self.next_think = self.elapsed + 1.25
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
        self.doctrine.army()

    def command_aircraft(self):
        self.air_missions.command()
