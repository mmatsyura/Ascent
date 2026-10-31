from dataclasses import dataclass, field
import math
import random

import pygame

from game.world.navigation import Navigation
from game.world.biomes import Biome
from game.world.squad_navigation import advance_member


@dataclass
class SquadMember:
    position: pygame.Vector2
    offset: pygame.Vector2
    facing: pygame.Vector2
    random: random.Random
    phase: float = 0
    walking: bool = False
    immersion: float = 0
    previous_position: pygame.Vector2 | None = None
    direct_goal: pygame.Vector2 | None = None
    direct_clear: bool = False
    direct_remaining: float = 0
    direct_revision: int = -1
    wander: pygame.Vector2 = field(default_factory=pygame.Vector2)
    next_wander: float = 0
    next_pose: float = 0
    pose: str = "stand"
    previous_pose: str = "stand"
    pose_blend: float = 1
    detour: list = field(default_factory=list)
    retry_time: float = 0
    detour_goal: pygame.Vector2 | None = None
    blocked_seconds: float = 0
    idle_target_key: tuple | None = None
    idle_target: pygame.Vector2 = field(default_factory=pygame.Vector2)


OFFSETS = ((-.42, -.61), (.32, -.39), (-.73, .04), (.66, .16), (-.29, .58), (.38, .77))
SQUAD_RADIUS = 62


def safe_position(point, origin, terrain):
    if terrain.can_place_soldier(point, radius=4):
        return pygame.Vector2(point)
    displacement = pygame.Vector2(point) - origin
    for fraction in (.8, .6, .4, .2, 0):
        candidate = pygame.Vector2(origin) + displacement * fraction
        if terrain.can_place_soldier(candidate, radius=4):
            return candidate
    for distance in (8, 16, 24, 32):
        for angle in range(0, 360, 30):
            candidate = pygame.Vector2(origin) + pygame.Vector2(distance, 0).rotate(angle)
            if terrain.can_place_soldier(candidate, radius=4):
                return candidate
    return pygame.Vector2(origin)


def initialize_squad(unit, terrain, navigation=None, placement_allowed=None):
    navigation = navigation or Navigation(terrain, None, avoid_trees=True)
    seed = int(unit.position[0] * 17 + unit.position[1] * 31)
    unit.members = []
    origin = pygame.Vector2(unit.position)
    anchor = safe_position(origin, origin, terrain)
    angle = random.Random(seed).uniform(-15, 15)
    for index, offset in enumerate(OFFSETS):
        randomizer = random.Random(seed + index * 7919)
        offset = pygame.Vector2(offset).rotate(angle) * SQUAD_RADIUS
        position = anchor.copy()
        candidates = [origin + offset.rotate(turn) * fraction for fraction in (1, .75, .5, .25) for turn in (0, 25, -25, 55, -55, 95, -95, 145, -145, 180)]
        candidates.extend(origin + pygame.Vector2(distance, 0).rotate(turn) for distance in (12, 24, 36, 48, 60) for turn in range(0, 360, 30))
        for candidate in candidates:
            separated = all(candidate.distance_to(other.position) >= 12 for other in unit.members)
            city_clearance = unit.home_city is None or candidate.distance_to(unit.home_city) >= 44
            in_deployment = placement_allowed is None or placement_allowed(candidate)
            reachable = separated and city_clearance and in_deployment and terrain.can_place_soldier(candidate, 4)
            if reachable and navigation.find_path(anchor, candidate, navigation.allowed_cells()) is not None:
                position = candidate
                break
        offset = position - origin
        member = SquadMember(position, offset, pygame.Vector2(unit.facing), randomizer)
        member.phase = randomizer.random() * 16
        member.next_wander = randomizer.uniform(2, 8)
        member.next_pose = randomizer.uniform(4, 10)
        unit.members.append(member)


def update_pose(member, pose):
    if pose != member.pose:
        member.previous_pose = member.pose
        member.pose = pose
        member.pose_blend = 0


def update_squad(unit, elapsed_seconds, terrain, navigation):
    if not unit.members:
        initialize_squad(unit, terrain, navigation)
    unit.squad_time += elapsed_seconds
    unit.idle_time = 0 if unit.route else unit.idle_time + elapsed_seconds
    center = pygame.Vector2(unit.position)
    for member in unit.members:
        member.previous_position = member.position.copy()
        in_water = terrain.biome_at(member.position) == Biome.WATER
        member.immersion += ((1 if in_water else 0) - member.immersion) * -math.expm1(-max(0, elapsed_seconds) / .65)
        member.pose_blend = min(1, member.pose_blend + elapsed_seconds / .55)
        member.retry_time = max(0, member.retry_time - elapsed_seconds)
        formation_target = center + member.offset
        in_position = member.position.distance_to(formation_target) < 12 and member.position.distance_to(center) < SQUAD_RADIUS + 15
        resting = not unit.route and in_position
        if resting and member.pose == "stand" and unit.squad_time >= member.next_wander:
            member.next_wander = unit.squad_time + member.random.uniform(6, 12)
            angle = member.random.uniform(0, math.tau)
            member.wander = pygame.Vector2(math.cos(angle), math.sin(angle)) * member.random.uniform(0, 8)
        if not resting:
            member.wander *= math.exp(-elapsed_seconds * 3)
            update_pose(member, "stand")
        elif not member.walking and unit.squad_time >= member.next_pose:
            member.next_pose = unit.squad_time + member.random.uniform(7, 14)
            choices = ("stand", "stand", "kneel", "prone") if unit.idle_time > 22 and not unit.in_water else ("stand", "stand", "kneel")
            update_pose(member, member.random.choice(choices) if not unit.in_water else "stand")
            if member.pose != "stand":
                member.wander = member.position - center - member.offset
            direction = pygame.Vector2(1, 0).rotate(member.random.uniform(0, 360))
            member.facing = direction

        target = center + member.offset + member.wander
        if resting:
            key = (unit.position, tuple(member.wander))
            if key != member.idle_target_key:
                member.idle_target = safe_position(target, center, terrain)
                member.idle_target_key = key
            target = member.idle_target
        elif not navigation.can_place(target, radius=4):
            nearby = navigation.nearest_destination(target)
            target = nearby if nearby is not None else center
        delta = target - member.position
        distance = delta.length()
        walking = distance > (.7 if unit.route else 1.8)
        if walking:
            update_pose(member, "stand")
            regrouping = bool(unit.route) or distance > 20
            speed = min(65 / 1.3 if regrouping else 4.5 / 1.3, distance * (3 if regrouping else .9))
            if in_water:
                speed *= .45
            travelled, direction = advance_member(member, target, center, speed, elapsed_seconds, navigation)
            member.phase = (member.phase + travelled * .42) % 16
            if travelled > .002:
                member.facing = member.facing.lerp(direction, -math.expm1(-elapsed_seconds * 7))
            walking = travelled > .002
        else:
            member.detour.clear()
            member.detour_goal = None
        member.walking = walking


def update_squad_timed(unit, duration, terrain, navigation, interval):
    if not unit.squad_schedule_started:
        unit.squad_accumulator = ((unit.position[0] * .137 + unit.position[1] * .173) % 1) * interval
        unit.squad_schedule_started = True
    unit.squad_accumulator += max(0, duration)
    steps = 0
    while unit.squad_accumulator >= interval and steps < 3:
        unit.squad_accumulator -= interval
        update_squad(unit, interval, terrain, navigation)
        steps += 1
    unit.squad_accumulator = min(unit.squad_accumulator, interval)
    unit.member_blend = min(1, unit.squad_accumulator / interval)


def cohesion_speed(unit):
    if not unit.members:
        return 1
    distance = max(member.position.distance_to(unit.position) for member in unit.members)
    return max(0, min(1, (140 - distance) / 50))
