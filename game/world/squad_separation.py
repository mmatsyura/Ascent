import math

import pygame

from game.world.units import detail_blend, token_rectangle


class SquadSeparation:
    def __init__(self, units, visibility=None):
        self.units = units
        self.visibility = visibility

    def update(self, screen, camera, elapsed_seconds):
        strength = 1 - detail_blend(camera.zoom)
        if strength <= 0:
            for unit in self.units:
                unit.marker_offset = (0, 0)
            return
        area = camera.visible_area.inflate(320, 320)
        units = []
        centers = []
        for unit in self.units:
            if not area.collidepoint(unit.position) or (
                unit.owner != "blue"
                and self.visibility is not None
                and not self.visibility.is_visible(unit.position)
            ):
                unit.marker_offset = (0, 0)
                continue
            units.append(unit)
            centers.append(camera.world_to_screen(unit.position))
        if not units:
            return
        recovery = math.exp(-max(0, elapsed_seconds) * 0.7)
        positions = [
            center + pygame.Vector2(unit.marker_offset) * recovery
            for unit, center in zip(units, centers)
        ]
        diameter = token_rectangle(units[0], screen, camera).w
        minimum = (diameter + 5) * strength
        minimum_squared = minimum * minimum
        cell_size = max(1, minimum)
        for _ in range(8 if len(units) < 20 else 3):
            buckets = {}
            changed = False
            for index, position in enumerate(positions):
                cell = math.floor(position.x / cell_size), math.floor(position.y / cell_size)
                for row in range(cell[1] - 1, cell[1] + 2):
                    for column in range(cell[0] - 1, cell[0] + 2):
                        for other in buckets.get((column, row), ()):
                            offset = position - positions[other]
                            distance_squared = offset.length_squared()
                            if distance_squared >= minimum_squared - 0.01:
                                continue
                            if distance_squared > 0.0001:
                                distance = math.sqrt(distance_squared)
                                normal = offset / distance
                            else:
                                distance = 0
                                normal = pygame.Vector2(0, 1).rotate(
                                    (index * 37 + other * 19) % 360
                                )
                            push = normal * (minimum - distance + 0.03) * 0.5
                            positions[index] += push
                            positions[other] -= push
                            changed = True
                buckets.setdefault(cell, []).append(index)
            if not changed:
                break
        for unit, center, position in zip(units, centers, positions):
            unit.marker_offset = tuple(position - center)


def separate_members(units, terrain, area, duration):
    actors = []
    for unit in units:
        if area is not None and not area.collidepoint(unit.position):
            continue
        if unit.is_tank:
            actors.append((unit, None, pygame.Vector2(unit.position), 23.0))
        else:
            actors.extend((unit, member, member.position.copy(), 10.5) for member in unit.members)
    maximum_push = min(3.5, max(0, duration) * 65)
    for iteration in range(2):
        buckets = {}
        for index, (unit, member, position, radius) in enumerate(actors):
            cell = math.floor(position.x / 48), math.floor(position.y / 48)
            for y in range(cell[1] - 1, cell[1] + 2):
                for x in range(cell[0] - 1, cell[0] + 2):
                    for other in buckets.get((x, y), ()):
                        other_unit, other_member, other_position, other_radius = actors[other]
                        delta = position - other_position
                        distance = delta.length()
                        minimum = radius + other_radius
                        if distance >= minimum:
                            continue
                        normal = (
                            delta / distance
                            if distance > 0.001
                            else pygame.Vector2(1, 0).rotate(index * 137.5)
                        )
                        push = normal * min(maximum_push, (minimum - distance) * 0.51)
                        for actor_unit, actor_member, actor_position, movement in (
                            (unit, member, position, push),
                            (other_unit, other_member, other_position, -push),
                        ):
                            candidate = actor_position + movement
                            allowed = terrain.can_move(actor_position, candidate, radius=4)
                            if actor_member is not None:
                                allowed = allowed and terrain.can_place_soldier(candidate, radius=4)
                            if not allowed:
                                continue
                            actor_position.update(candidate)
                            if actor_member is None:
                                actor_unit.position = tuple(candidate)
                            else:
                                actor_member.position.update(candidate)
                                if actor_member.previous_position is not None:
                                    actor_member.previous_position += movement
            buckets.setdefault(cell, []).append(index)
