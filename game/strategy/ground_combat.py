from collections import defaultdict
import math

import pygame

from game.world.battle_art import condition_bars, impact_image, muzzle_image
from game.world.units import detail_blend, token_rectangle
from game.world.tank_geometry import TankCanvas, TANK_RENDER_SIZE
from game.world.soldier_art import rifle_muzzle


class GroundCombat:
    def __init__(self, app):
        self.app = app
        self.accumulator = 0
        self.tracers = []
        self.elapsed = 0
        self.losses = defaultdict(int)
        self.engagements = {}

    def update(self, duration):
        self.elapsed += duration
        self.accumulator += duration
        self.tracers[:] = [trace for trace in self.tracers if self.elapsed - trace[2] < trace[5]]
        if self.accumulator < 0.2:
            return
        step = self.accumulator
        self.accumulator = 0
        buckets = defaultdict(list)
        present = set(self.app.units)
        for pair, state in tuple(self.engagements.items()):
            if not pair <= present or self.elapsed - state[1] > 12:
                del self.engagements[pair]
        for unit in self.app.units:
            buckets[(int(unit.position[0] // 240), int(unit.position[1] // 240))].append(unit)
        damage = defaultdict(float)
        fighting = set()
        for unit in self.app.units:
            if unit.is_patriot or self.elapsed < unit.next_shot:
                continue
            reach = min(
                unit.vision_radius, 220 if unit.is_anti_tank else 180 if unit.is_tank else 105
            )
            x, y = int(unit.position[0] // 240), int(unit.position[1] // 240)
            nearby = [
                other
                for row in range(y - 1, y + 2)
                for col in range(x - 1, x + 2)
                for other in buckets.get((col, row), ())
                if other.owner != unit.owner
                and pygame.Vector2(unit.position).distance_squared_to(other.position) <= reach**2
            ]
            if not nearby:
                continue
            candidates = sorted(
                nearby,
                key=lambda other: other.health
                + pygame.Vector2(unit.position).distance_to(other.position) * 0.25
                - (85 if unit.is_anti_tank and other.is_tank else 0),
            )
            target = next(
                (
                    other
                    for other in candidates
                    if self.app.terrain.can_move(unit.position, other.position, radius=1)
                ),
                None,
            )
            if target is None:
                continue
            pair = frozenset((unit, target))
            if pair not in self.engagements:
                aggressor = (
                    unit
                    if bool(unit.route) != bool(target.route) and unit.route
                    else target if target.route and not unit.route else unit
                )
                self.engagements[pair] = (aggressor, self.elapsed)
            aggressor, _ = self.engagements[pair]
            self.engagements[pair] = (aggressor, self.elapsed)
            interval = 3.2 if unit.is_tank else 3.8 if unit.is_anti_tank else 0.8
            power = (
                (13 if target.is_tank else 1.6) if unit.is_anti_tank else 5 if unit.is_tank else 2.8
            )
            if target.is_tank and not unit.is_tank and not unit.is_anti_tank:
                power *= 0.28
            if unit.is_tank and target.is_anti_tank:
                power *= 0.65
            if target.in_forest:
                power *= 0.7
            if target is aggressor:
                power *= 1.25
            power *= 0.25 + 0.75 * unit.readiness / 100
            damage[target] += power * interval
            fighting.update((unit, target))
            unit.next_shot = self.elapsed + interval
            unit.recoil = 1
            unit.last_combat = target.last_combat = self.elapsed
            unit.readiness = max(0, unit.readiness - power * interval * 0.8)
            kind = "tank" if unit.is_tank else "rocket" if unit.is_anti_tank else "rifle"
            vector = pygame.Vector2(target.position) - unit.position
            direction = vector.normalize() if vector.length_squared() else pygame.Vector2(0, 1)
            if unit.is_tank:
                unit.turret_angle = unit.turret_target = (
                    math.degrees(math.atan2(direction.x, -direction.y)) % 360
                )
                unit.scanning = False
                canvas = TankCanvas()
                muzzle = canvas.project(
                    canvas.transform((0, -75.2, 26.6), round(unit.turret_angle / 2) * 2 % 360)
                )
                offset = (pygame.Vector2(muzzle) - (256, 256)) * (
                    TANK_RENDER_SIZE * unit.visual_scale / 512
                )
                recoil = pygame.Vector2(0, -1).rotate(unit.turret_angle) * unit.recoil * 2.5
                origins = [pygame.Vector2(unit.position) + offset - recoil]
            else:
                for member in unit.members:
                    member.facing = direction.copy()
                origins = []
                for member in unit.members[::3]:
                    position = (
                        member.previous_position.lerp(member.position, unit.member_blend)
                        if member.previous_position is not None
                        else member.position
                    )
                    phase = int(member.phase) % 16 if member.walking else 0
                    facing = (
                        "back"
                        if member.facing.y < -0.4
                        else "left" if member.facing.x < -0.25 else "front"
                    )
                    offset = rifle_muzzle(phase, facing, member.pose, unit.is_anti_tank)
                    if member.pose_blend < 1 and not unit.is_anti_tank:
                        previous = rifle_muzzle(phase, facing, member.previous_pose)
                        offset = previous.lerp(offset, member.pose_blend)
                    origins.append(position + offset * 26 * unit.visual_scale)
                if not origins:
                    origins = [pygame.Vector2(unit.position)]
            for index, origin in enumerate(origins):
                self.tracers.append(
                    (
                        tuple(origin),
                        tuple(target.position),
                        self.elapsed + index * 0.025,
                        unit.owner,
                        kind,
                        0.65 if kind != "rifle" else 0.18,
                    )
                )
            if len(self.tracers) > 768:
                del self.tracers[:-768]
        for unit, amount in damage.items():
            unit.health = max(0, unit.health - amount)
            unit.readiness = max(0, unit.readiness - amount * 2.5)
        for unit in tuple(self.app.units):
            if unit.health <= 0:
                self.app.units.remove(unit)
                self.losses[unit.owner] += 1
                if unit.owner == "blue":
                    self.app.intelligence.record(
                        f"Втрачено підрозділ: {unit.name}", unit.position, "Бойове донесення"
                    )
        cities = [city for city in self.app.city_map.cities if city.owner]
        for unit in self.app.units:
            if self.elapsed - unit.last_combat < 6:
                continue
            unit.readiness = min(100, unit.readiness + step * 4.3)
            base = unit.source_barracks
            supplied = base is None or (
                base in self.app.buildings.buildings and base.owner == unit.owner
            )
            if supplied:
                city_bonus = (
                    1.5
                    if any(
                        city.owner == unit.owner
                        and pygame.Vector2(unit.position).distance_squared_to(city.position)
                        < 210**2
                        for city in cities
                    )
                    else 1
                )
                unit.health = min(100, unit.health + step * 2.4 * city_bonus)

    def draw(self, screen, camera):
        for start, end, born, owner, kind, lifetime in self.tracers:
            if owner != "blue" and not self.app.visibility.is_visible(start):
                continue
            if self.elapsed < born:
                continue
            origin, destination = camera.world_to_screen(start), camera.world_to_screen(end)
            progress = max(0, min(1, (self.elapsed - born) / lifetime))
            tip = origin.lerp(destination, progress)
            direction = destination - origin
            direction = (
                direction.normalize() if direction.length_squared() else pygame.Vector2(0, -1)
            )
            scale = max(0.65, camera.zoom)
            color = (255, 208, 114) if kind != "rocket" else (245, 219, 167)
            pygame.draw.line(
                screen,
                color,
                origin.lerp(destination, max(0, progress - 0.18)),
                tip,
                max(1, round(scale * (2 if kind != "rifle" else 1))),
            )
            if progress < 0.35:
                size = (9 if kind == "tank" else 5) * scale * (1 - progress / 0.35)
                flash = muzzle_image(
                    max(2, round(size)),
                    round(math.degrees(math.atan2(direction.y, direction.x)) / 15) % 24,
                )
                screen.blit(flash, flash.get_rect(center=(round(origin.x), round(origin.y))))
            if kind == "rocket":
                pygame.draw.line(screen, (130, 137, 122), origin, tip, max(1, round(scale)))
                pygame.draw.circle(screen, (255, 189, 85), tip, max(1, round(2 * scale)))
            if kind != "rifle" and progress > 0.65:
                impact = impact_image(
                    max(18, round(52 * scale / 4) * 4),
                    min(23, round((progress - 0.65) / 0.35 * 23)),
                )
                screen.blit(
                    impact, impact.get_rect(center=(round(destination.x), round(destination.y)))
                )
        for unit in self.app.units:
            if (unit.health >= 99.9 and unit.readiness >= 99.9 and not unit.selected) or (
                unit.owner != "blue" and not self.app.visibility.is_visible(unit.position)
            ):
                continue
            point = camera.world_to_screen(unit.position)
            if detail_blend(camera.zoom) < 0.5:
                badge = token_rectangle(unit, screen, camera)
                point = pygame.Vector2(badge.centerx, badge.top - 3)
            else:
                point.y -= (34 if unit.is_tank else 28) * camera.zoom
            rectangle = pygame.Rect(round(point.x - 18), round(point.y - 9), 36, 4)
            if not screen.get_rect().colliderect(rectangle):
                continue
            image = condition_bars(round(unit.health), round(unit.readiness))
            screen.blit(image, (rectangle.x - 2, rectangle.y - 2))
