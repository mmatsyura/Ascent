import math

import pygame

from game.aircraft.drone_types import (
    BURN_DURATION,
    FALL_DURATION,
    FLIGHT_ALTITUDE,
    TAKEOFF_DURATION,
)
from game.settings import WORLD_HEIGHT, WORLD_WIDTH


def turn_towards(current, target, duration):
    difference = (target - current + 180) % 360 - 180
    change = min(abs(difference), 30 * duration)
    return (current + math.copysign(change, difference)) % 360


def fly_towards(drone, target, duration):
    position = pygame.Vector2(drone.position)
    offset = pygame.Vector2(target) - position
    distance = offset.length()
    if distance < 5:
        return True
    target_heading = math.degrees(math.atan2(offset.x, -offset.y)) % 360
    drone.heading = turn_towards(drone.heading, target_heading, duration)
    difference = abs((target_heading - drone.heading + 180) % 360 - 180)
    speed = drone.definition.speed * max(0.3, math.cos(math.radians(min(90, difference))))
    movement = min(distance, speed * duration)
    if distance <= movement + 0.001 and difference < 10:
        position.update(target)
        arrived = True
    else:
        position += pygame.Vector2(0, -movement).rotate(drone.heading)
        arrived = False
    position.x = max(8, min(WORLD_WIDTH - 8, position.x))
    position.y = max(8, min(WORLD_HEIGHT - 8, position.y))
    drone.position = tuple(position)
    return arrived


def cruise(drone, duration):
    if drone.route:
        if fly_towards(drone, drone.route[0], duration):
            drone.route.pop(0)
        return
    position = pygame.Vector2(drone.position)
    radial = position - drone.orbit_center
    if radial.length_squared() < 1:
        radial = pygame.Vector2(0, -1).rotate(drone.heading)
    distance = radial.length()
    outward = radial.normalize()
    tangent = outward.rotate(90)
    correction = max(-1.6, min(1.6, (drone.orbit_radius - distance) / 55))
    direction = tangent + outward * correction
    fly_towards(drone, position + direction.normalize() * 60, duration)


def advance_drone(drone, duration):
    remaining = duration
    lifetime = drone.definition.flight_lifetime
    transitions = []
    while remaining > 1e-8 and drone.state != "finished":
        if drone.state == "takeoff":
            available = min(TAKEOFF_DURATION - drone.state_time, lifetime - drone.flight_age)
        elif drone.state == "cruising":
            available = lifetime - drone.flight_age
        elif drone.state == "falling":
            available = FALL_DURATION - drone.state_time
        else:
            available = BURN_DURATION - drone.state_time
        step = min(remaining, max(0, available))
        drone.state_time += step
        drone.animation_time += step
        remaining -= step
        if drone.state in ("takeoff", "cruising"):
            drone.flight_age = min(lifetime, drone.flight_age + step)
        if drone.state == "takeoff":
            progress = min(1, drone.state_time / TAKEOFF_DURATION)
            drone.altitude = FLIGHT_ALTITUDE * progress * progress * (3 - 2 * progress)
            direction = pygame.Vector2(0, -drone.definition.speed * 0.3 * step).rotate(
                drone.heading
            )
            drone.position = tuple(pygame.Vector2(drone.position) + direction)
            if drone.state_time >= TAKEOFF_DURATION - 1e-8:
                drone.state, drone.state_time = "cruising", 0
                transitions.append("cruising")
        elif drone.state == "cruising":
            cruise(drone, step)
            if drone.flight_age >= lifetime - 1e-8:
                drone.state, drone.state_time = "falling", 0
                transitions.append("falling")
        elif drone.state == "falling":
            progress = min(1, drone.state_time / FALL_DURATION)
            drone.altitude = FLIGHT_ALTITUDE * (1 - progress**1.5)
            drone.heading = (drone.heading + step * 25) % 360
            drone.position = tuple(
                pygame.Vector2(drone.position)
                + pygame.Vector2(0, -drone.definition.speed * 0.35 * step).rotate(drone.heading)
            )
            if drone.state_time >= FALL_DURATION - 1e-8:
                drone.state, drone.state_time, drone.altitude = "burning", 0, 0
                transitions.append("burning")
        elif drone.state_time >= BURN_DURATION - 1e-8:
            drone.state, drone.state_time = "finished", 0
            transitions.append("finished")
    drone.position = (
        max(8, min(WORLD_WIDTH - 8, drone.position[0])),
        max(8, min(WORLD_HEIGHT - 8, drone.position[1])),
    )
    return transitions
