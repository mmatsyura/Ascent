from collections import deque
from dataclasses import replace
import math

import pygame

from game.aircraft.photography import take_photo


class AerialReconnaissance:
    def __init__(self, fleet, units, buildings, terrain, intelligence, notify, cities=None):
        self.fleet = fleet
        self.units = units
        self.buildings = buildings
        self.terrain = terrain
        self.intelligence = intelligence
        self.notify = notify
        self.cities = cities
        self.scan_time = 0
        self.detected = {}
        self.reported_cities = set()
        self.in_sight = set()
        self.previous_sight = set()
        self.photo_jobs = deque(maxlen=24)

    def report(self, drone, target, kind):
        identity = (kind, target)
        if kind == "city":
            if target.owner in (None, "blue", "neutral") or target.position in self.reported_cities:
                return
            self.reported_cities.add(target.position)
        scanned = identity in self.in_sight
        self.in_sight.add(identity)
        previous = self.detected.get(identity)
        if previous is not None:
            time, _, owner = previous
            if owner == target.owner:
                if scanned or (identity in self.previous_sight and self.fleet.elapsed - time < 20):
                    return
        self.detected[identity] = (self.fleet.elapsed, tuple(target.position), target.owner)
        if kind == "city":
            title = f"Виявлено {'столицю' if target.capital else 'місто'} · {target.name}"
        elif kind == "building":
            title = f"Ворожа споруда · {target.definition.name}"
        else:
            title = f"{'Ворожа техніка' if target.is_tank else 'Ворожа піхота'} · {target.name}"
        report = self.intelligence.record(
            title, target.position, f"БПЛА {drone.definition.name}", elapsed=self.fleet.elapsed
        )
        snapshot = replace(target)
        if kind == "unit":
            snapshot.members = [
                replace(member, position=member.position.copy()) for member in target.members
            ]
        elif kind == "city" and target.capital and self.cities is not None:
            snapshot.remembered_frame = self.cities.flag_frame(target)
        self.photo_jobs.append((report, snapshot, kind, replace(drone)))
        drone.photographed += 1
        self.notify(f"БПЛА {drone.definition.name}: {title.lower()}")

    def city_discovered(self, city):
        for drone in self.fleet.drones:
            if (
                drone.state in ("cruising", "takeoff")
                and drone.altitude >= 20
                and pygame.Vector2(city.position).distance_squared_to(drone.position)
                <= drone.vision_radius**2
            ):
                self.report(drone, city, "city")
                break

    def update(self, elapsed_seconds):
        self.process_photo()
        for drone, state in self.fleet.events:
            if state == "burning":
                self.intelligence.record(
                    f"Дрон втрачено: {drone.definition.name}",
                    drone.position,
                    "Ресурс вичерпано · бортовий звіт",
                    elapsed=self.fleet.elapsed,
                )
        self.fleet.events.clear()
        self.scan_time += elapsed_seconds
        if self.scan_time < 0.75:
            return
        self.scan_time %= 0.75
        self.in_sight = set()
        buckets = {}
        present = set(self.units) | set(self.buildings.buildings)
        if self.cities is not None:
            present.update(self.cities.cities)
        self.detected = {
            identity: value for identity, value in self.detected.items() if identity[1] in present
        }
        for kind, targets in (("unit", self.units), ("building", self.buildings.buildings)):
            for target in targets:
                if target.owner != "blue":
                    cell = math.floor(target.position[0] / 256), math.floor(
                        target.position[1] / 256
                    )
                    buckets.setdefault(cell, []).append((kind, target))
        for drone in self.fleet.drones:
            if drone.state not in ("cruising", "takeoff") or drone.altitude < 20:
                continue
            radius_squared = drone.vision_radius**2
            x, y = drone.position
            radius = drone.vision_radius
            for row in range(math.floor((y - radius) / 256), math.floor((y + radius) / 256) + 1):
                for column in range(
                    math.floor((x - radius) / 256), math.floor((x + radius) / 256) + 1
                ):
                    for kind, target in buckets.get((column, row), ()):
                        if (target.position[0] - x) ** 2 + (
                            target.position[1] - y
                        ) ** 2 <= radius_squared:
                            self.report(drone, target, kind)
        self.previous_sight = self.in_sight.copy()

    def process_photo(self):
        while self.photo_jobs:
            report, target, kind, drone = self.photo_jobs.popleft()
            if not any(current is report for current in self.intelligence.reports):
                continue
            photo = take_photo(self.terrain, target, kind, drone, self.cities)
            self.intelligence.attach_photo(report, photo)
            break
