from collections import Counter

import pygame

from game.world.building_manager import BuildingManager
from game.world.buildings import BUILDINGS_BY_KEY


class Development:
    def __init__(self, commander):
        self.commander = commander
        self.site_index = 0
        self.failed_until = 0

    def construct(self, key):
        leader = self.commander
        app = leader.app
        definition = BUILDINGS_BY_KEY[key]
        if not leader.kingdom.can_afford(definition.cost) or leader.elapsed < self.failed_until:
            return False
        cities = [city for city in app.city_map.cities if city.owner == leader.owner]
        cities.sort(key=lambda city: (leader.knowledge.threat(city.position), not city.capital))
        if not cities:
            return False
        manager = BuildingManager(app.terrain, leader.kingdom, app.city_map, app.units)
        manager.buildings = app.buildings.buildings
        manager.reservations = app.buildings.reservations
        for attempt in range(48):
            index = self.site_index + attempt
            city = cities[(index//12) % len(cities)]
            radius = 120 + ((index//len(cities)) % 5) * 48
            angle = index * 137.508
            position = pygame.Vector2(city.position) + pygame.Vector2(radius, 0).rotate(angle)
            building, _ = manager.place(definition, position, leader.knowledge)
            if building is None:
                continue
            building.owner = leader.owner
            app.buildings.revision += 1
            self.site_index = index + 1
            leader.statistics['constructed'] += 1
            return True
        self.site_index += 48
        self.failed_until = leader.elapsed + 8
        return False

    def think(self):
        leader = self.commander
        own = [building for building in leader.app.buildings.buildings if building.owner == leader.owner]
        counts = Counter(building.definition.key for building in own)
        troops = [unit for unit in leader.app.units if unit.owner == leader.owner]
        danger = max((leader.knowledge.threat(city.position) for city in leader.app.city_map.cities if city.owner == leader.owner), default=0)
        if len(troops) < 8 or danger > 5:
            for building in own:
                if leader.recruitment.valid_barracks(building) and not leader.recruitment.garrison(building).queue:
                    leader.recruitment.recruit(building, 'tank' if len(troops) >= 4 and sum(unit.is_tank for unit in troops) < 2 else 'infantry')
        if counts['mine'] == 0:
            self.construct('mine')
            return
        if counts['barracks'] == 0:
            self.construct('barracks')
            return
        if counts['mine'] < 4 and danger < 5:
            if self.construct('mine'):
                return
        if counts['airport'] == 0 and counts['mine'] >= 3:
            if self.construct('airport'):
                return
        if counts['mine'] < 7 and counts['airport'] and leader.kingdom.gold > 900:
            if self.construct('mine'):
                return
        if counts['barracks'] < 3 and len(troops) >= 20 + 12*(counts['barracks']-1):
            if self.construct('barracks'):
                return
        desired_army = min(28, 12 + sum(city.owner == leader.owner for city in leader.app.city_map.cities))
        reserve = 500 if counts['mine'] < 4 and danger < 5 else 0
        if counts['airport'] and counts['mine'] >= 4 and danger < 7 and len(troops) >= desired_army:
            reserve = 3000 if leader.knowledge.buildings or leader.knowledge.contacts else 1500
        for building in own:
            if building.definition.key != 'barracks' or not building.completed:
                continue
            state = leader.recruitment.garrison(building)
            if state.queue or len(troops) >= 48 or leader.kingdom.gold < reserve + 110:
                continue
            air_threat = any(drone.owner != leader.owner and leader.knowledge.is_visible(drone.position)
                             for fleet in leader.app.strategy.fleets for drone in fleet.drones)
            key = 'patriot' if sum(unit.is_patriot for unit in troops) < (3 if air_threat else 1) else ('tank' if sum(unit.is_tank for unit in troops) < len(troops)*.3 else 'infantry')
            leader.recruitment.recruit(building, key)
        for airport in own:
            if not leader.fleet.valid_airport(airport):
                continue
            for key, count in tuple(leader.fleet.stock[airport].items()):
                if count:
                    leader.fleet.launch(airport, key)
            queue = leader.fleet.production.queues.get(airport)
            if queue and queue.jobs:
                continue
            if len(leader.fleet.drones) >= 8 or len(troops) < 10:
                continue
            strike = bool(leader.knowledge.contacts or leader.knowledge.buildings)
            scouts = sum(not drone.definition.strike for drone in leader.fleet.drones)
            if scouts >= 2 and not strike:
                continue
            key = 'flamingo' if strike and scouts else ('aviamen' if scouts and leader.kingdom.gold >= 2500 else 'kamikaze')
            leader.fleet.purchase(airport, key)
