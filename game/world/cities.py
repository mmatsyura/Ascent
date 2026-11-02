from dataclasses import dataclass, replace
from functools import lru_cache
import math

import numpy as np
import pygame

from game.rendering import RenderPart
from game.settings import MAP_SEED, MAX_ZOOM, PLAYER_COLOR, TERRAIN_SCALE, WORLD_HEIGHT, WORLD_WIDTH
from game.strategy.balance import balance_territories
from game.world.biomes import Biome
from game.world.faction_visuals import FACTION_COLORS, FLAG_FRAMES, FLAG_RATE, flag_image
from game.world.names import CITY_NAMES
from game.world.reveals import faded_parts


@dataclass(eq=False)
class City:
    position: tuple[int, int]
    capital: bool = False
    flag_color: tuple[int, int, int] | None = None
    owner: str | None = None
    name: str = ""
    influence_weight: float = 1.0
    remembered_frame: int | None = None


@lru_cache(maxsize=256)
def marker_scale(viewport_size, zoom, minimum_zoom):
    resolution_scale = max(0.85, viewport_size[1] / 900)
    zoom_ratio = max(1, zoom / minimum_zoom)
    maximum_ratio = max(1, MAX_ZOOM / minimum_zoom)
    progress = min(1, math.log(zoom_ratio) / math.log(maximum_ratio)) if maximum_ratio > 1 else 0
    return resolution_scale * zoom_ratio / (1.5 * 1.7**progress)


def marker_radius(capital, size_scale):
    return max(1, round((20 if capital else 8) * size_scale))


def city_color(city):
    return PLAYER_COLOR if city.owner == "blue" else FACTION_COLORS.get(city.owner)


@lru_cache(maxsize=192)
def marker_image(capital, radius, color=None):
    scale = 4
    size = radius * 2 + 6
    image = pygame.Surface((size * scale, size * scale), pygame.SRCALPHA)
    center = size * scale // 2
    if capital:
        points = []
        for step in range(10):
            angle = -math.pi / 2 + step * math.pi / 5
            length = radius * scale * (1 if step % 2 == 0 else 0.43)
            points.append(
                (round(center + math.cos(angle) * length), round(center + math.sin(angle) * length))
            )
        pygame.draw.polygon(image, (18, 33, 30), points, scale * 3)
        base = color or (235, 200, 112)
        pygame.draw.polygon(image, base, points)
        for step in range(10):
            factor = 1.18 if step % 2 == 0 else 0.76
            face = tuple(min(255, round(channel * factor)) for channel in base)
            pygame.draw.polygon(
                image, face, [(center, center), points[step], points[(step + 1) % 10]]
            )
        highlight = tuple(min(255, channel + 65) for channel in color) if color else (255, 236, 178)
        pygame.draw.lines(image, highlight, False, points[:4], scale)
    else:
        base = color or (211, 207, 174)
        pygame.draw.circle(
            image, (8, 19, 23, 100), (center, center + scale * 2), (radius + 1) * scale
        )
        pygame.draw.circle(image, (20, 29, 29), (center, center), (radius + 1) * scale)
        pygame.draw.circle(image, (188, 179, 138), (center, center), radius * scale)
        for ring in range(max(1, radius * scale - scale), 0, -1):
            light = 0.8 + 0.4 * (1 - ring / max(1, radius * scale))
            shade = tuple(min(255, round(channel * light)) for channel in base)
            pygame.draw.circle(image, shade, (center, center), ring)
        highlight = tuple(min(255, round(channel * 0.5 + 127)) for channel in base)
        pygame.draw.circle(
            image, highlight, (center - scale, center - scale), max(2, radius * scale // 5)
        )
    return pygame.transform.smoothscale(image, (size, size)).convert_alpha()


class CityMap:
    def __init__(self, terrain):
        random = np.random.default_rng(MAP_SEED + 221)
        grid_step = 24
        rows, columns = np.where(terrain.biomes[::grid_step, ::grid_step] == Biome.MEADOW)
        candidates = []
        for row, column in zip(rows, columns):
            point = (int(column) * grid_step * TERRAIN_SCALE, int(row) * grid_step * TERRAIN_SCALE)
            if terrain.can_place_building((point[0] - 28, point[1] - 28, 56, 56)):
                candidates.append(point)

        self.cities = []
        self.visibility = None
        self.animation_time = 0
        self.revision = 0
        self.reconnaissance = None
        self.reveals = None
        capital_colors = ((193, 68, 57), (64, 124, 202), (64, 153, 96), (151, 91, 183))
        capital_owners = dict(zip(capital_colors, ("red", "blue", "green", "purple")))
        capital_locations = ((0.28, 0.22), (0.64, 0.28), (0.23, 0.86), (0.72, 0.84))
        for (horizontal, vertical), color in zip(capital_locations, capital_colors):
            target = pygame.Vector2(horizontal * WORLD_WIDTH, vertical * WORLD_HEIGHT)
            available = [point for point in candidates if self.spaced(point, 900)]
            if not available:
                raise ValueError("Недостатньо вільної землі для чотирьох столиць")
            point = min(available, key=lambda candidate: target.distance_squared_to(candidate))
            self.cities.append(City(point, True, color, owner=capital_owners[color]))

        for index in random.permutation(len(candidates)):
            point = candidates[index]
            if self.spaced(point, 410):
                self.cities.append(City(point))
            if len(self.cities) == 48:
                break

        self.cities = [
            replace(city, name=CITY_NAMES[index]) for index, city in enumerate(self.cities)
        ]
        for capital in (city for city in self.cities if city.capital):
            nearest = sorted(
                (city for city in self.cities if city.owner is None),
                key=lambda city: pygame.Vector2(capital.position).distance_squared_to(
                    city.position
                ),
            )[:3]
            for city in nearest:
                city.owner = capital.owner
        balance_territories(terrain, self.cities)
        self.player_capital = next(
            city for city in self.cities if city.capital and city.owner == "blue"
        )
        self.player_cities = [
            city for city in self.cities if city.owner == "blue" and not city.capital
        ]

    def spaced(self, point, minimum_distance):
        return all(
            (point[0] - city.position[0]) ** 2 + (point[1] - city.position[1]) ** 2
            >= minimum_distance**2
            for city in self.cities
        )

    def update(self, elapsed_seconds, units):
        self.animation_time += elapsed_seconds
        layout = tuple((city.position, city.capital) for city in self.cities)
        if getattr(self, "capture_layout", None) != layout:
            self.capture_layout = layout
            self.capture_cells = {}
            for city in self.cities:
                radius = 26 if city.capital else 18
                x, y = city.position
                for row in range(
                    math.floor((y - radius) / 128), math.floor((y + radius) / 128) + 1
                ):
                    for column in range(
                        math.floor((x - radius) / 128), math.floor((x + radius) / 128) + 1
                    ):
                        self.capture_cells.setdefault((column, row), []).append(
                            (city, radius * radius)
                        )
        occupants = {}
        for unit in units:
            for point in (unit.position, *(member.position for member in unit.members)):
                cell = int(point[0] // 128), int(point[1] // 128)
                for city, radius_squared in self.capture_cells.get(cell, ()):
                    if (point[0] - city.position[0]) ** 2 + (
                        point[1] - city.position[1]
                    ) ** 2 <= radius_squared:
                        occupants.setdefault(city, set()).add(unit.owner)
        captured = []
        self.capture_events = []
        for city in self.cities:
            owners = occupants.get(city, ())
            if len(owners) != 1:
                continue
            owner = owners.pop()
            if owner == city.owner:
                continue
            self.capture_events.append((city, city.owner, owner))
            city.owner = owner
            if city.capital:
                city.flag_color = PLAYER_COLOR if owner == "blue" else FACTION_COLORS[owner]
            captured.append(city)
        if captured:
            self.player_cities = [
                city for city in self.cities if city.owner == "blue" and not city.capital
            ]
            self.revision += 1
        return captured

    def flag_frame(self, city):
        if city.remembered_frame is not None:
            return city.remembered_frame
        offset = (city.position[0] * 0.013 + city.position[1] * 0.017) % 1
        return int((self.animation_time + offset) * FLAG_RATE) % FLAG_FRAMES

    def displayed_cities(self):
        if self.reconnaissance is not None:
            return self.reconnaissance.displayed_cities()
        return tuple(
            city
            for city in self.cities
            if self.visibility is None or self.visibility.is_visible(city.position)
        )

    def known_city(self, position):
        if self.reconnaissance is not None:
            return self.reconnaissance.known_city(position)
        return next((city for city in self.displayed_cities() if city.position == position), None)

    def city_at(self, position, screen, camera):
        scale = marker_scale(screen.get_size(), camera.zoom, camera.minimum_zoom)
        matches = []
        for city in self.displayed_cities():
            center = camera.world_to_screen(city.position)
            radius = max(10, marker_radius(city.capital, scale) + 3)
            over_marker = center.distance_squared_to(position) <= radius * radius
            flag_area = pygame.Rect(
                round(center.x - 6),
                round(center.y - 44 * scale),
                max(10, round(40 * scale)),
                max(10, round(44 * scale)),
            )
            if over_marker or (city.capital and flag_area.collidepoint(position)):
                matches.append((center.distance_squared_to(position), city))
        return min(matches, key=lambda item: item[0])[1] if matches else None

    def draw_parts(self, screen, camera):
        size_scale = marker_scale(screen.get_size(), camera.zoom, camera.minimum_zoom)
        margin = math.ceil(52 * size_scale)
        visible = screen.get_rect().inflate(margin * 2, margin * 2)
        for city in self.displayed_cities():
            point = camera.world_to_screen(city.position)
            if visible.collidepoint(point):
                reveals = getattr(self, "reveals", None)
                opacity = reveals.city_opacity(city) if reveals is not None else 255
                if opacity <= 0:
                    continue
                radius = marker_radius(city.capital, size_scale)
                image = marker_image(city.capital, radius, city_color(city))
                parts = [
                    RenderPart(
                        -math.inf, image, image.get_rect(center=(round(point.x), round(point.y)))
                    )
                ]
                if city.capital and city.flag_color is not None:
                    height = round(44 * size_scale)
                    flag = flag_image(city.flag_color, height, self.flag_frame(city))
                    parts.append(
                        RenderPart(
                            -math.inf,
                            flag,
                            flag.get_rect(topleft=(round(point.x) - 4, round(point.y) - height)),
                        )
                    )
                yield from faded_parts(parts, opacity)

    def draw(self, screen, camera):
        for part in self.draw_parts(screen, camera):
            screen.blit(part.image, part.rectangle)

    def draw_minimap(self, screen, map_area):
        for city in self.displayed_cities():
            point = (
                round(map_area.x + city.position[0] / WORLD_WIDTH * map_area.w),
                round(map_area.y + city.position[1] / WORLD_HEIGHT * map_area.h),
            )
            reveals = getattr(self, "reveals", None)
            opacity = reveals.city_opacity(city) if reveals is not None else 255
            if opacity <= 0:
                continue
            target = screen if opacity == 255 else pygame.Surface((32, 32), pygame.SRCALPHA)
            center = point if opacity == 255 else (8, 20)
            if city.capital:
                image = marker_image(True, 5, city_color(city))
                target.blit(image, image.get_rect(center=center))
                if city.flag_color is not None:
                    height = 15
                    flag = flag_image(city.flag_color, height, self.flag_frame(city))
                    target.blit(flag, (center[0] - 4, center[1] - height))
            else:
                pygame.draw.circle(target, (23, 37, 31), center, 2)
                pygame.draw.circle(target, city_color(city) or (233, 225, 190), center, 1)
            if opacity < 255:
                target.set_alpha(opacity)
                screen.blit(target, (point[0] - 8, point[1] - 20))
