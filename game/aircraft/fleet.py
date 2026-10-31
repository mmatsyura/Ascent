from collections import defaultdict

import pygame

from game.aircraft.definitions import DRONES_BY_KEY
from game.aircraft.models import Drone
from game.aircraft.motion import advance_drone
from game.aircraft.production import DroneProduction
from game.settings import WORLD_HEIGHT, WORLD_WIDTH
from game.world.building_art import building_layout, building_point
from game.world.visibility import VisionSource


class DroneFleet:
    def __init__(self, kingdom, buildings, owner="blue"):
        self.owner = owner
        self.kingdom = kingdom
        self.buildings = buildings
        self.stock = defaultdict(lambda: defaultdict(int))
        self.drones = []
        self.revision = 0
        self.elapsed = 0
        self.next_identity = 1
        self.events = []
        self.production = DroneProduction(self)
        self.combat = None

    def valid_airport(self, airport):
        return airport in self.buildings.buildings and airport.owner == self.owner and airport.completed and airport.definition.key == "airport"

    def purchase(self, airport, key):
        if not self.valid_airport(airport) or key not in DRONES_BY_KEY:
            return False, "Аеропорт недоступний."
        definition = DRONES_BY_KEY[key]
        if not self.kingdom.spend({"gold": definition.price}):
            return False, "Недостатньо золота."
        self.production.enqueue(airport, definition)
        self.revision += 1
        return True, ""

    def launch(self, airport, key):
        if not self.valid_airport(airport) or self.stock[airport][key] <= 0:
            return None, "Спочатку дочекайтеся виготовлення дрона."
        _, anchor, _ = building_layout("airport")
        apron = pygame.Vector2(building_point("airport", (30, 83))) / 2 - anchor
        position = pygame.Vector2(airport.position) + apron
        center = (max(180, min(WORLD_WIDTH - 180, airport.position[0])), max(180, min(WORLD_HEIGHT - 180, airport.position[1])))
        drone = Drone(DRONES_BY_KEY[key], airport, tuple(position), self.next_identity, orbit_center=center)
        self.next_identity += 1
        self.stock[airport][key] -= 1
        self.drones.append(drone)
        self.revision += 1
        return drone, ""

    def update(self, elapsed_seconds):
        remaining = max(0, elapsed_seconds)
        self.elapsed += remaining
        self.production.update(remaining)
        if self.combat is not None:
            self.combat.update(remaining)
        if not self.drones:
            return
        while remaining > 1e-8:
            step = min(.1, remaining)
            for drone in tuple(self.drones):
                handled = self.combat.advance(drone, step) if self.combat is not None else False
                transitions = [] if handled else advance_drone(drone, step)
                if transitions:
                    self.revision += 1
                    self.events.extend((drone, state) for state in transitions)
                if drone.state == "finished":
                    self.drones.remove(drone)
            remaining -= step
            if not self.drones:
                break

    def vision_sources(self):
        return [VisionSource(drone.position, drone.vision_radius, territorial=False, records_exploration=drone.definition.records_exploration)
                for drone in self.drones if drone.state in ("takeoff", "cruising", "diving", "falling") and drone.altitude > 1]

    def assign_route(self, drone, points, append=False):
        if drone not in self.drones or not drone.controllable or not points:
            return False
        drone.attack_target = None
        drone.attack_position = None
        route = [tuple(pygame.Vector2(max(16, min(WORLD_WIDTH - 16, point[0])), max(16, min(WORLD_HEIGHT - 16, point[1])))) for point in points]
        if append:
            drone.route.extend(route)
        else:
            drone.route = route
        destination = drone.route[-1]
        drone.orbit_center = (max(96, min(WORLD_WIDTH - 96, destination[0])), max(96, min(WORLD_HEIGHT - 96, destination[1])))
        drone.orbit_radius = 80
        return True

    def hold(self, drone):
        if drone in self.drones and drone.controllable:
            drone.attack_target = None
            drone.attack_position = None
            drone.route.clear()
            drone.orbit_center = drone.position
            drone.orbit_radius = 80
