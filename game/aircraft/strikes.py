import math
import random

import pygame

from game.aircraft.drone_types import FLIGHT_ALTITUDE
from game.aircraft.explosions import Explosion, draw_explosions
from game.world.building_rendering import building_parts
from game.world.units import selection_rectangle


class DroneStrikes:
    def __init__(self, fleet, units, buildings, visibility, intelligence, notify):
        self.fleet = fleet
        self.units = units
        self.buildings = buildings
        self.visibility = visibility
        self.intelligence = intelligence
        self.notify = notify
        self.random = random.Random()
        self.present = set()
        self.explosions = []
        self.on_explosion = None
        self.on_impact = None

    @staticmethod
    def chance(target):
        if hasattr(target, "definition"):
            return 0.9
        return 0.2 if target.is_tank and not target.is_patriot else 0.8

    def valid(self, target):
        return (
            target is not None
            and target.owner not in (self.fleet.owner, None, "neutral")
            and (target in self.units or target in self.buildings.buildings)
        )

    def target_at(self, pointer, camera):
        candidates = []
        world = camera.screen_to_world(pointer)
        screen = pygame.display.get_surface()
        reach = max(180, 50 / camera.zoom)
        for target in self.units:
            if (
                target.owner == self.fleet.owner
                or abs(target.position[0] - world.x) > reach
                or abs(target.position[1] - world.y) > reach
            ):
                continue
            if (
                self.valid(target)
                and self.visibility.is_visible(target.position)
                and selection_rectangle(target, screen, camera).collidepoint(pointer)
            ):
                candidates.append(target)
        for target in self.buildings.buildings:
            if not self.valid(target) or not self.visibility.is_visible(target.position):
                continue
            if abs(target.position[0] - world.x) > 200 or abs(target.position[1] - world.y) > 200:
                continue
            if any(
                part.rectangle.inflate(4, 4).collidepoint(pointer)
                for part in building_parts(target, camera, workers=False)
            ):
                candidates.append(target)
        return min(
            candidates,
            key=lambda target: pygame.Vector2(target.position).distance_squared_to(world),
            default=None,
        )

    def assign(self, drone, target):
        if (
            drone not in self.fleet.drones
            or not drone.controllable
            or not drone.definition.strike
            or not self.valid(target)
            or not self.visibility.is_visible(target.position)
        ):
            return False
        drone.attack_target = target
        drone.attack_position = tuple(target.position)
        drone.route = [drone.attack_position]
        self.notify(f"Фламінго: ціль прийнято · шанс знищення {round(self.chance(target) * 100)}%")
        return True

    def update(self, duration):
        if not self.fleet.drones and not self.explosions:
            self.present.clear()
            return
        self.present = set(self.units) | set(self.buildings.buildings)
        for explosion in self.explosions:
            explosion.age += max(0, duration)
        self.explosions[:] = [explosion for explosion in self.explosions if explosion.age < 20]

    def advance(self, drone, duration):
        if drone.state == "diving":
            if drone.flight_age + duration >= drone.definition.flight_lifetime:
                drone.state, drone.state_time = "falling", 0
                drone.attack_target = None
                drone.route.clear()
                return False
            drone.flight_age += duration
            drone.animation_time += duration
            drone.state_time += duration
            progress = min(1, drone.state_time / 1.5)
            smooth = progress * progress * (3 - 2 * progress)
            drone.position = tuple(
                pygame.Vector2(drone.dive_origin).lerp(drone.attack_position, smooth)
            )
            drone.altitude = FLIGHT_ALTITUDE * (1 - smooth)
            if progress >= 1:
                self.impact(drone)
            return True
        if drone.attack_target is None or drone.state not in ("takeoff", "cruising"):
            return False
        if drone.attack_target not in self.present or drone.attack_target.owner in (
            self.fleet.owner,
            None,
            "neutral",
        ):
            drone.attack_target = None
            drone.attack_position = None
            drone.route.clear()
            return False
        if self.visibility.is_visible(drone.attack_target.position):
            drone.attack_position = tuple(drone.attack_target.position)
        if self.fleet.air_routes is not None:
            if (
                not drone.route
                or self.visibility.is_visible(drone.attack_target.position)
                and pygame.Vector2(drone.route[-1]).distance_squared_to(drone.attack_position)
                > 96**2
            ):
                drone.route = self.fleet.air_routes.route(drone.position, drone.attack_position)
        else:
            drone.route = [drone.attack_position]
        if self.fleet.air_routes is not None and not self.fleet.air_routes.dry(
            drone.attack_position
        ):
            drone.attack_target = None
            drone.route.clear()
            return False
        offset = pygame.Vector2(drone.attack_position) - drone.position
        if drone.state == "cruising" and offset.length_squared() <= 24**2:
            if offset.length_squared() > 25:
                desired = math.degrees(math.atan2(offset.x, -offset.y)) % 360
                if abs((desired - drone.heading + 180) % 360 - 180) > 45:
                    return False
            drone.state = "diving"
            drone.state_time = 0
            drone.dive_origin = drone.position
            drone.route.clear()
            self.fleet.revision += 1
            return True
        return False

    def impact(self, drone):
        target = drone.attack_target
        hit = (
            target in self.present
            and target.owner not in (self.fleet.owner, None, "neutral")
            and pygame.Vector2(target.position).distance_squared_to(drone.position) <= 48**2
        )
        destroyed = hit and self.random.random() < self.chance(target)
        name = target.definition.name if hasattr(target, "definition") else target.name
        if destroyed:
            if target in self.units:
                self.units.remove(target)
                recon = self.buildings.reconnaissance
                if recon is not None:
                    recon.contacts.pop(target, None)
                    recon.visible_enemies.discard(target)
                    recon.hidden_contacts.discard(target)
            else:
                self.buildings.destroy(target)
            self.present.discard(target)
        outcome = (
            f"Ціль знищено: {name}"
            if destroyed
            else (f"Ціль уціліла: {name}" if hit else "Ціль залишила зону удару")
        )
        self.intelligence.record(
            outcome, drone.position, "Фламінго · ударний звіт", elapsed=self.fleet.elapsed
        )
        self.notify(f"Фламінго: {outcome.lower()}")
        if self.on_impact is not None:
            self.on_impact(drone, target, outcome)
        self.explosions.append(Explosion(tuple(drone.position), drone.identity % 3))
        if len(self.explosions) > 24:
            del self.explosions[:-24]
        if self.on_explosion is not None:
            self.on_explosion(drone.position)
        drone.state = "finished"
        drone.state_time = drone.altitude = 0
        drone.attack_target = None
        drone.attack_position = None
        drone.route.clear()
        self.fleet.revision += 1

    def draw(self, screen, camera):
        draw_explosions(screen, camera, self.explosions)
