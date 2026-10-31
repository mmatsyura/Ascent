from dataclasses import dataclass

import pygame

from game.world.visibility import VisionSource
from game.world.buildings import BuildingDefinition
from game.world.building_rendering import building_parts
from game.world.building_art import building_layout


def building_area(definition, position):
    rectangle = pygame.Rect(0, 0, *definition.footprint)
    rectangle.center = (round(position[0]), round(position[1]))
    return rectangle


@dataclass(eq=False)
class PlacedBuilding:
    definition: BuildingDefinition
    position: tuple[float, float]
    animation_time: float = 0
    training_active: bool = False
    training_time: float = 0
    owner: str = "blue"
    construction_elapsed: float | None = None
    builder_departure: float = 0

    @property
    def completed(self):
        return self.construction_elapsed is None or self.construction_elapsed >= self.definition.construction_duration

    @property
    def construction_progress(self):
        return 1.0 if self.completed else self.construction_elapsed / self.definition.construction_duration

    @property
    def construction_remaining(self):
        return 0.0 if self.completed else self.definition.construction_duration - self.construction_elapsed

    @property
    def area(self):
        return building_area(self.definition, self.position)


class BuildingManager:
    def __init__(self, terrain, kingdom, cities, units):
        self.terrain = terrain
        self.kingdom = kingdom
        self.cities = cities
        self.units = units
        self.buildings = []
        self.revision = 0
        self.reconnaissance = None
        self.reservations = {}
        self.on_completed = None

    @property
    def income_per_second(self):
        return sum(building.definition.income_per_second for building in self.buildings if building.owner == "blue" and building.completed)

    def vision_sources(self):
        return [VisionSource(building.position, building.definition.vision_radius) for building in self.buildings if building.owner == "blue" and building.completed]

    def income_schedule(self, duration):
        mines = [building for building in self.buildings if building.owner == "blue" and building.definition.income_per_second > 0]
        active = [building for building in mines if building.completed]
        completions = sorted(((building.construction_remaining, index, building) for index, building in enumerate(mines)
                              if not building.completed and building.construction_remaining <= duration), key=lambda item: item[:2])
        schedule = []
        previous = 0
        for time, _, building in completions:
            if time > previous:
                schedule.append((time - previous, tuple(active)))
            active.append(building)
            previous = time
        if duration > previous:
            schedule.append((duration - previous, tuple(active)))
        return schedule

    def displayed_buildings(self):
        if self.reconnaissance is not None:
            return self.reconnaissance.displayed_buildings()
        return self.buildings

    def interactive_at(self, pointer, screen, camera):
        world = camera.screen_to_world(pointer)
        for building in reversed(self.buildings):
            if building.owner != "blue" or (building.completed and building.definition.key not in ("airport", "barracks")):
                continue
            size, anchor, _ = building_layout(building.definition.key)
            left = building.position[0] - anchor[0]
            top = building.position[1] - anchor[1]
            if not (left - 2 <= world.x < left + size[0] + 2 and top - 2 <= world.y < top + size[1] + 2):
                continue
            for part in building_parts(building, camera, workers=False):
                if part.rectangle.collidepoint(pointer):
                    point = (int(pointer[0] - part.rectangle.x), int(pointer[1] - part.rectangle.y))
                    if part.image.get_at(point).a > 40:
                        return building
        return None

    def validation(self, definition, position, visibility):
        if not self.kingdom.can_afford(definition.cost):
            return "Недостатньо золота."
        area = building_area(definition, position)
        samples = (area.topleft, (area.right - 1, area.top), (area.right - 1, area.bottom - 1), (area.left, area.bottom - 1), area.center)
        if not all(visibility.is_visible(point) for point in samples):
            return "Оберіть місце у видимій частині території."
        if any(area.inflate(16, 16).colliderect(building.area) for building in self.buildings):
            return "Тут уже є споруда."
        if not self.terrain.can_place_building(area):
            return "Потрібна рівна ділянка суші без дерев."
        for city in self.cities.cities:
            closest = (max(area.left, min(area.right, city.position[0])), max(area.top, min(area.bottom, city.position[1])))
            radius = 42 if city.capital else 24
            if pygame.Vector2(closest).distance_squared_to(city.position) < radius * radius:
                return "Залиште місце навколо міста."
        safety_area = area.inflate(16, 16)
        for unit in self.units:
            if safety_area.collidepoint(unit.position) or any(safety_area.collidepoint(member.position) for member in unit.members):
                return "Спочатку відведіть бійців із ділянки."
        return ""

    def place(self, definition, position, visibility):
        error = self.validation(definition, position, visibility)
        if error:
            return None, error
        if not self.kingdom.spend(definition.cost):
            return None, "Недостатньо золота."
        building = PlacedBuilding(definition, tuple(position), len(self.buildings) * .73, construction_elapsed=0)
        self.reservations[building] = self.terrain.reserve_building(building.area)
        self.buildings.append(building)
        self.revision += 1
        return building, ""

    def cancel_construction(self, building):
        if building not in self.buildings or building.owner != "blue" or building.completed:
            return False
        self.buildings.remove(building)
        reservation = self.reservations.pop(building, None)
        if reservation is not None:
            self.terrain.release_building(reservation)
        self.kingdom.gold += building.definition.gold_cost
        if self.reconnaissance is not None:
            self.reconnaissance.building_memory.pop(building, None)
        self.revision += 1
        return True

    def destroy(self, building):
        if building not in self.buildings:
            return False
        self.buildings.remove(building)
        reservation = self.reservations.pop(building, None)
        if reservation is not None:
            self.terrain.release_building(reservation)
        if self.reconnaissance is not None:
            self.reconnaissance.building_memory.pop(building, None)
        self.revision += 1
        return True

    def update(self, elapsed_seconds, construction_seconds=None):
        construction_seconds = elapsed_seconds if construction_seconds is None else construction_seconds
        for building in self.buildings:
            building.animation_time += elapsed_seconds
            building.builder_departure = max(0, building.builder_departure - elapsed_seconds)
            if not building.completed:
                building.construction_elapsed = min(building.definition.construction_duration, building.construction_elapsed + max(0, construction_seconds))
                if building.completed:
                    building.builder_departure = 1.8
                    self.revision += 1
                    if self.on_completed is not None:
                        self.on_completed(building)
            if building.completed and building.training_active:
                building.training_time += elapsed_seconds

    def set_training(self, building, active):
        if building not in self.buildings or not building.completed or building.definition.key != "barracks":
            return False
        building.training_active = bool(active)
        building.training_time = 0
        return True
