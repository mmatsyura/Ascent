from dataclasses import dataclass, field
import math
import random

import pygame

from game.settings import UNIT_FOREST_VISION_RADIUS, UNIT_VISION_RADIUS, WATER_ENTRY_DURATION
from game.world.biomes import Biome
from game.world.cities import marker_scale
from game.world.soldier_art import military_badge
from game.world.tank_geometry import TANK_RENDER_SIZE


@dataclass(eq=False)
class UnitToken:
    position: tuple[float, float]
    owner: str = "blue"
    vision_radius: float = UNIT_VISION_RADIUS
    movable: bool = True
    selected: bool = False
    route: list[tuple[float, float]] = field(default_factory=list)
    in_water: bool = False
    in_forest: bool = False
    immersion: float = 0
    water_entry_time: float | None = None
    visual_scale: float = 1.0
    animation_time: float = 0.0
    facing: tuple[float, float] = (0, 1)
    members: list = field(default_factory=list)
    squad_time: float = 0.0
    idle_time: float = 0.0
    home_city: tuple[float, float] | None = None
    name: str = "Піхотний загін"
    marker_offset: tuple[float, float] = (0, 0)
    squad_accumulator: float = 0
    squad_schedule_started: bool = False
    squad_interval: float = 0
    member_blend: float = 1
    planning_target: tuple[float, float] | None = None
    health: float = 100
    readiness: float = 100
    source_barracks: object = None
    last_combat: float = -100
    next_shot: float = 0
    recoil: float = 0
    profile_anchor: tuple[float, float] | None = None

    @property
    def is_anti_tank(self):
        return False

    @property
    def is_tank(self):
        return False

    @property
    def is_patriot(self):
        return False

    @property
    def icon_key(self):
        return "army"

    @property
    def speed_factor(self):
        return 1.0

    @property
    def detail_label(self):
        return "6 бійців"

    def update_environment(self, biome, elapsed_seconds):
        entering_water = biome == Biome.WATER and not self.in_water
        self.in_water = biome == Biome.WATER
        self.in_forest = biome == Biome.FOREST
        self.immersion += ((1 if self.in_water else 0) - self.immersion) * -math.expm1(
            -max(0, elapsed_seconds) / 0.65
        )
        self.vision_radius = UNIT_FOREST_VISION_RADIUS if self.in_forest else UNIT_VISION_RADIUS
        if entering_water and self.water_entry_time is None:
            self.water_entry_time = 0.0
        if self.water_entry_time is not None:
            self.water_entry_time += elapsed_seconds
            progress = min(1, self.water_entry_time / WATER_ENTRY_DURATION)
            self.visual_scale = 1 - 0.14 * math.sin(progress * math.pi) ** 2
            if progress >= 1:
                self.water_entry_time = None
                self.visual_scale = 1.0


def token_image(size, selected=False):
    return military_badge(size, selected)


def token_rectangle(unit, screen, camera):
    size_scale = marker_scale(screen.get_size(), camera.zoom, camera.minimum_zoom)
    size = max(22, round(max(22, 29 * size_scale) * 1.3))
    point = camera.world_to_screen(unit.position) + pygame.Vector2(unit.marker_offset)
    return pygame.Rect(round(point.x - size / 2), round(point.y - size / 2), size, size)


def detail_blend(zoom):
    progress = max(0, min(1, (zoom - 0.8) / 0.25))
    return progress * progress * (3 - 2 * progress)


def selection_rectangle(unit, screen, camera):
    rectangle = token_rectangle(unit, screen, camera)
    if detail_blend(camera.zoom) > 0.1:
        if unit.is_tank:
            size = max(24, round(TANK_RENDER_SIZE * camera.zoom * unit.visual_scale))
            center = camera.world_to_screen(unit.position)
            return pygame.Rect(round(center.x - size / 2), round(center.y - size / 2), size, size)
        size = round(max(rectangle.w * 2.2, 145 * camera.zoom))
        rectangle = pygame.Rect(0, 0, size, size)
        rectangle.center = token_rectangle(unit, screen, camera).center
        if unit.members:
            for member in unit.members:
                point = camera.world_to_screen(member.position)
                height = max(12, round(26 * camera.zoom * unit.visual_scale))
                area = pygame.Rect(
                    round(point.x - height / 2), round(point.y - height), height, height + 4
                )
                rectangle.union_ip(area)
    return rectangle


def draw_tokens(screen, camera, units):
    from game.world.unit_visuals import unit_parts

    parts = [part for unit in units for part in unit_parts(unit, screen, camera)]
    for part in sorted(parts, key=lambda item: item.depth):
        screen.blit(part.image, part.rectangle)


@dataclass(eq=False)
class TankUnit(UnitToken):
    hull_angle: float = 180
    turret_angle: float = 180
    turret_target: float = 180
    travelled: float = 0
    idle_elapsed: float = 0
    next_scan: float = 12
    scanning: bool = False
    track_distance: float = 0
    tracks: list = field(default_factory=list)
    track_revision: int = 0
    trail_cache_key: tuple | None = None
    trail_cache: object = None
    randomizer: object = field(default_factory=lambda: random.Random(8743))

    @property
    def is_tank(self):
        return True

    @property
    def icon_key(self):
        return "tank"

    @property
    def speed_factor(self):
        return 1 / 1.8

    @property
    def detail_label(self):
        return "Бойовий танк"

    def update_environment(self, biome, elapsed_seconds):
        super().update_environment(biome, elapsed_seconds)
        if not self.is_patriot:
            self.visual_scale = 1.0


@dataclass(eq=False)
class PatriotUnit(TankUnit):
    deployment: float = 0
    deployment_delay: float = 0.7

    @property
    def is_patriot(self):
        return True

    @property
    def icon_key(self):
        return "patriot"

    @property
    def speed_factor(self):
        return 1 / (1.8 * 1.3)

    @property
    def detail_label(self):
        return "ППО · перезаряджання 7 с · шанс 35%"

    def update_environment(self, biome, elapsed_seconds):
        super().update_environment(biome, elapsed_seconds)
        self.vision_radius *= 0.85

    def update_deployment(self, duration):
        duration = max(0, duration)
        if self.route:
            self.deployment_delay = 0.7
            self.deployment = max(0, self.deployment - duration / 2.6)
        else:
            self.deployment_delay = max(0, self.deployment_delay - duration)
            if self.deployment_delay == 0:
                self.deployment = min(1, self.deployment + duration / 3.8)


@dataclass(eq=False)
class AntiTankUnit(UnitToken):
    @property
    def is_anti_tank(self):
        return True

    @property
    def speed_factor(self):
        return 0.76

    @property
    def detail_label(self):
        return "Протитанковий загін · 6 бійців"
