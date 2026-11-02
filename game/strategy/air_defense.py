from dataclasses import dataclass, field
from functools import lru_cache
import math
import random

import pygame

from game.settings import CITY_VISION_RADIUS

ENGAGEMENT_RADIUS = CITY_VISION_RADIUS * 1.15 * 1.8
RELOAD_SECONDS = 7.0
INTERCEPT_CHANCE = 0.35


@lru_cache(maxsize=128)
def vapor_puff(radius, opacity):
    image = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
    for size in range(radius, 0, -2):
        alpha = round(opacity * (1 - size / (radius + 1)) ** 0.6)
        pygame.draw.circle(image, (183, 190, 179, alpha), (radius + 1, radius + 1), size)
    return image


@dataclass
class Interceptor:
    origin: tuple
    position: pygame.Vector2
    target: object
    owner: str
    aim: pygame.Vector2
    age: float = 0
    duration: float = 1.8
    trail: list = field(default_factory=list)
    resolved: bool = False
    hit: bool = False
    accurate: bool = True
    miss_offset: tuple = (0, 0)


class AirDefense:
    def __init__(self, app):
        self.app = app
        self.elapsed = 0
        self.cooldowns = {}
        self.missiles = []
        self.bursts = []
        self.random = random.Random()
        self.shots = 0
        self.hits = 0

    def update(self, duration, fleets):
        self.elapsed += duration
        drones = [
            drone
            for fleet in fleets
            for drone in fleet.drones
            if drone.state in ("takeoff", "cruising", "diving") and drone.altitude > 4
        ]
        targets = {}
        for drone in drones:
            targets.setdefault(
                (
                    int(drone.position[0] // ENGAGEMENT_RADIUS),
                    int(drone.position[1] // ENGAGEMENT_RADIUS),
                ),
                [],
            ).append(drone)
        patriots = [unit for unit in self.app.units if unit.is_patriot]
        self.cooldowns = {unit: time for unit, time in self.cooldowns.items() if unit in patriots}
        for unit in patriots:
            if unit.route or unit.deployment < 0.95 or self.cooldowns.get(unit, 0) > self.elapsed:
                continue
            cx, cy = int(unit.position[0] // ENGAGEMENT_RADIUS), int(
                unit.position[1] // ENGAGEMENT_RADIUS
            )
            candidates = [
                drone
                for y in range(cy - 1, cy + 2)
                for x in range(cx - 1, cx + 2)
                for drone in targets.get((x, y), ())
                if drone.owner != unit.owner
                and pygame.Vector2(unit.position).distance_squared_to(drone.position)
                <= ENGAGEMENT_RADIUS**2
            ]
            if not candidates:
                continue
            target = min(
                candidates,
                key=lambda drone: (
                    not drone.definition.strike,
                    pygame.Vector2(unit.position).distance_squared_to(drone.position),
                ),
            )
            origin = (unit.position[0], unit.position[1] - 10)
            aim = pygame.Vector2(target.position) - pygame.Vector2(0, target.altitude)
            self.missiles.append(
                Interceptor(
                    origin,
                    pygame.Vector2(origin),
                    target,
                    unit.owner,
                    aim,
                    duration=max(0.8, pygame.Vector2(origin).distance_to(aim) / 210),
                    accurate=self.random.random() < INTERCEPT_CHANCE,
                    miss_offset=tuple(pygame.Vector2(40, 0).rotate(self.random.randrange(360))),
                )
            )
            self.cooldowns[unit] = self.elapsed + RELOAD_SECONDS
            self.shots += 1
        present = set(drones)
        for missile in self.missiles:
            missile.age += duration
            missile.trail.append((tuple(missile.position), missile.age))
            missile.trail[:] = [
                (point, age) for point, age in missile.trail if missile.age - age < 0.8
            ][-32:]
            if not missile.resolved:
                if missile.target in present:
                    missile.aim = pygame.Vector2(missile.target.position) - pygame.Vector2(
                        0, missile.target.altitude
                    )
                progress = min(1, missile.age / missile.duration)
                destination = missile.aim.copy()
                if not missile.accurate:
                    destination += pygame.Vector2(missile.miss_offset) * max(
                        0, (progress - 0.4) / 0.6
                    )
                missile.position = pygame.Vector2(missile.origin).lerp(destination, progress)
                missile.position.y -= math.sin(progress * math.pi) * 45
                if progress >= 1:
                    missile.resolved = True
                    missile.hit = missile.target in present and missile.accurate
                    if missile.hit:
                        target = missile.target
                        target.state, target.state_time = "falling", 0
                        target.route.clear()
                        target.attack_target = None
                        present.discard(target)
                        self.hits += 1
                        if missile.owner == "blue" or target.owner == "blue":
                            title = (
                                "Петріот: ворожий дрон збито"
                                if missile.owner == "blue"
                                else "Наш дрон збито ворожою ППО"
                            )
                            self.app.intelligence.record(
                                title, target.position, "Протиповітряна оборона"
                            )
                    self.bursts.append(
                        (tuple(missile.position), self.elapsed, missile.hit, missile.owner)
                    )
            elif not missile.hit:
                direction = missile.aim - missile.origin
                if direction.length_squared():
                    missile.position += direction.normalize() * 240 * duration
        self.missiles[:] = [
            missile
            for missile in self.missiles
            if missile.age < missile.duration + (0.15 if missile.hit else 0.65)
        ]
        self.bursts[:] = [burst for burst in self.bursts if self.elapsed - burst[1] < 1.2]

    def draw(self, screen, camera):
        for unit in self.app.unit_control.selected:
            if unit.is_patriot:
                center = camera.world_to_screen(unit.position)
                pygame.draw.circle(
                    screen,
                    (127, 160, 120),
                    (round(center.x), round(center.y)),
                    round(ENGAGEMENT_RADIUS * camera.zoom),
                    1,
                )
        for missile in self.missiles:
            if missile.owner != "blue" and not self.app.visibility.is_visible(missile.origin):
                continue
            trail = [camera.world_to_screen(point) for point, _ in missile.trail]
            for index in range(1, len(trail)):
                fade = index / max(1, len(trail) - 1)
                shade = round(80 + 100 * fade)
                pygame.draw.line(
                    screen,
                    (shade, shade, round(shade * 0.85)),
                    trail[index - 1],
                    trail[index],
                    max(1, round(2 * camera.zoom)),
                )
            point = camera.world_to_screen(missile.position)
            direction = missile.aim - missile.origin
            direction = (
                direction.normalize() if direction.length_squared() else pygame.Vector2(0, -1)
            )
            scale = max(0.65, camera.zoom)
            side = pygame.Vector2(-direction.y, direction.x)
            pygame.draw.polygon(
                screen,
                (255, 194, 77),
                [
                    point - direction * 13 * scale,
                    point - side * 3 * scale,
                    point + side * 3 * scale,
                ],
            )
            pygame.draw.line(
                screen,
                (243, 244, 221),
                point - direction * 5 * scale,
                point + direction * 4 * scale,
                max(2, round(3 * scale)),
            )
            if missile.age < 0.35:
                origin = camera.world_to_screen(missile.origin)
                pygame.draw.circle(
                    screen,
                    (255, 210, 104),
                    origin,
                    max(2, round((1 - missile.age / 0.35) * 10 * scale)),
                )
        for position, born, hit, owner in self.bursts:
            if owner != "blue" and not self.app.visibility.is_visible(position):
                continue
            progress = (self.elapsed - born) / 1.2
            point = camera.world_to_screen(position)
            scale = max(0.6, camera.zoom)
            size = max(16, round(110 * scale))
            image = pygame.Surface((size, size), pygame.SRCALPHA)
            center = pygame.Vector2(size / 2, size / 2)
            alpha = round(255 * (1 - progress))
            if hit:
                pygame.draw.circle(
                    image,
                    (255, 191, 79, alpha),
                    center,
                    max(1, round((5 + progress * 29) * scale)),
                    max(1, round(2 * scale)),
                )
                pygame.draw.circle(
                    image,
                    (255, 238, 166, alpha),
                    center,
                    max(1, round((1 - progress) * 12 * scale)),
                )
                for index in range(9):
                    direction = pygame.Vector2(1, 0).rotate(index * 137.5)
                    tip = center + direction * (9 + progress * 37) * scale
                    pygame.draw.line(
                        image,
                        (249, 145, 48, alpha),
                        tip - direction * 6 * scale,
                        tip,
                        max(1, round(2 * scale)),
                    )
            else:
                for index in range(6):
                    offset = (
                        pygame.Vector2(
                            math.sin(index * 2.4) * 9 + progress * 11,
                            math.cos(index * 1.8) * 5 - progress * (10 + index * 2),
                        )
                        * scale
                    )
                    radius = max(2, round((3 + progress * (5 + index % 3)) * scale))
                    puff = vapor_puff(radius, round(alpha * (0.18 + index * 0.035)))
                    image.blit(puff, puff.get_rect(center=center + offset))
            screen.blit(image, image.get_rect(center=point))
