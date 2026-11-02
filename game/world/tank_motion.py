import math

import pygame

from game.world.biomes import Biome


def angle_difference(target, current):
    return (target - current + 180) % 360 - 180


def rotate_towards(current, target, speed, elapsed_seconds):
    difference = angle_difference(target, current)
    change = min(abs(difference), speed * elapsed_seconds)
    return (current + math.copysign(change, difference)) % 360


def tank_drive_factor(unit, elapsed_seconds):
    if not unit.route:
        return 1
    direction = pygame.Vector2(unit.route[0]) - unit.position
    if direction.length_squared() < 0.001:
        return 1
    target = math.degrees(math.atan2(direction.x, -direction.y)) % 360
    unit.hull_angle = rotate_towards(
        unit.hull_angle, target, 36 if unit.is_patriot else 48, elapsed_seconds
    )
    difference = abs(angle_difference(target, unit.hull_angle))
    return max(0, min(1, (65 - difference) / 50))


def update_tank(unit, elapsed_seconds, terrain, previous_position):
    unit.squad_time += elapsed_seconds
    start, end = pygame.Vector2(previous_position), pygame.Vector2(unit.position)
    distance = start.distance_to(end)
    unit.travelled += distance
    if unit.is_patriot:
        return
    if unit.route or distance > 0.001:
        if unit.idle_elapsed > 0 or unit.scanning:
            unit.next_scan = unit.randomizer.uniform(11, 19)
        unit.idle_elapsed = 0
        unit.scanning = False
        unit.turret_target = unit.hull_angle
        turret_speed = 24
    else:
        unit.idle_elapsed += elapsed_seconds
        if unit.idle_elapsed >= unit.next_scan:
            unit.scanning = not unit.scanning
            if unit.scanning:
                deviation = unit.randomizer.uniform(9, 17) * unit.randomizer.choice((-1, 1))
                unit.turret_target = (unit.hull_angle + deviation) % 360
                unit.next_scan = unit.idle_elapsed + unit.randomizer.uniform(5, 8)
            else:
                unit.turret_target = unit.hull_angle
                unit.next_scan = unit.idle_elapsed + unit.randomizer.uniform(12, 20)
        turret_speed = 4
    unit.turret_angle = rotate_towards(
        unit.turret_angle, unit.turret_target, turret_speed, elapsed_seconds
    )
    for mark in unit.tracks:
        mark[2] += elapsed_seconds
    unit.tracks[:] = [mark for mark in unit.tracks if mark[2] < 20]
    if distance > 0.001:
        remaining = 4 - unit.track_distance
        while remaining <= distance + 1e-7:
            position = start.lerp(end, min(1, remaining / distance))
            if terrain.biome_at(position) != Biome.WATER:
                unit.tracks.append([tuple(position), unit.hull_angle, 0.0])
                unit.track_revision += 1
            remaining += 4
        unit.track_distance = (unit.track_distance + distance) % 4
        if unit.track_distance < 1e-6 or unit.track_distance > 4 - 1e-6:
            unit.track_distance = 0
    if len(unit.tracks) > 144:
        del unit.tracks[:-144]
