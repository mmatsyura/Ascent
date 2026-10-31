from collections import deque
from dataclasses import dataclass, field

import pygame

from game.world.biomes import Biome
from game.world.squad_motion import initialize_squad
from game.world.tanks import TankUnit
from game.world.units import UnitToken
from game.world.patriots import PatriotUnit


GARRISON_LIMIT = 15
DISBAND_RADIUS = 230


@dataclass(frozen=True)
class RecruitDefinition:
    key: str
    name: str
    price: int
    duration: float


RECRUITS = (
    RecruitDefinition("infantry", "Солдати", 60, 20),
    RecruitDefinition("tank", "Танк", 110, 35),
    RecruitDefinition("patriot", "Петріот", 200, 60),
)
RECRUITS_BY_KEY = {definition.key: definition for definition in RECRUITS}


@dataclass
class Garrison:
    units: list = field(default_factory=list)
    queue: deque = field(default_factory=deque)
    progress: float = 0


class Recruitment:
    def __init__(self, kingdom, buildings, control, notify, owner="blue"):
        self.owner = owner
        self.kingdom = kingdom
        self.buildings = buildings
        self.control = control
        self.notify = notify
        self.garrisons = {}
        self.revision = 0
        self.next_number = sum(not unit.is_tank for unit in control.units) + 1

    def valid_barracks(self, building):
        return building in self.buildings.buildings and building.owner == self.owner and building.completed and building.definition.key == "barracks"

    def garrison(self, building):
        state = self.garrisons.setdefault(building, Garrison())
        state.units[:] = [unit for unit in state.units if unit in self.control.units and unit.owner == self.owner]
        return state

    def recruit(self, building, key):
        if not self.valid_barracks(building) or key not in RECRUITS_BY_KEY:
            return False, "Казарми недоступні."
        state = self.garrison(building)
        if len(state.units) + len(state.queue) >= GARRISON_LIMIT:
            return False, "Ліміт казарм: 15 бойових підрозділів разом із чергою."
        definition = RECRUITS_BY_KEY[key]
        if not self.kingdom.spend({"gold": definition.price}):
            return False, "Недостатньо золота."
        state.queue.append(definition)
        if len(state.queue) == 1:
            self.buildings.set_training(building, True)
        self.revision += 1
        return True, ""

    def spawn_position(self, building):
        origin = pygame.Vector2(building.position)
        terrain = self.buildings.terrain
        for radius in (100, 130, 165, 200):
            for angle in range(45, 405, 30):
                point = origin + pygame.Vector2(radius, 0).rotate(angle)
                if terrain.biome_at(point) == Biome.WATER or not terrain.can_place_soldier(point, 8):
                    continue
                if any(other.area.inflate(24, 24).collidepoint(point) for other in self.buildings.buildings):
                    continue
                if any(point.distance_to(unit.position) < 80 for unit in self.control.units):
                    continue
                return tuple(point)
        return None

    def update(self, duration):
        for building, state in tuple(self.garrisons.items()):
            if not self.valid_barracks(building):
                if state.queue:
                    self.kingdom.gold += sum(definition.price for definition in state.queue)
                    state.queue.clear()
                    self.revision += 1
                building.training_active = False
                continue
            self.garrison(building)
            if not state.queue:
                continue
            remaining = max(0, duration)
            while state.queue:
                definition = state.queue[0]
                previous_step = int(state.progress * 12)
                elapsed = min(remaining, definition.duration - state.progress)
                state.progress += elapsed
                remaining -= elapsed
                if int(state.progress * 12) != previous_step:
                    self.revision += 1
                if state.progress < definition.duration:
                    break
                position = self.spawn_position(building)
                if position is None:
                    break
                unit_type = {"infantry": UnitToken, "tank": TankUnit, "patriot": PatriotUnit}[definition.key]
                name = f"{self.next_number}-й піхотний загін" if definition.key == "infantry" else f"{definition.name} №{self.next_number}"
                unit = unit_type(position, name=name, owner=self.owner)
                unit.update_environment(self.buildings.terrain.biome_at(position), 0)
                if not unit.is_tank:
                    initialize_squad(unit, self.buildings.terrain, self.control.soldier_navigation)
                self.next_number += 1
                self.control.units.append(unit)
                state.units.append(unit)
                state.queue.popleft()
                state.progress = 0
                self.buildings.set_training(building, bool(state.queue))
                self.revision += 1
                self.notify(f"Підрозділ готовий: {unit.name}")

    def can_disband(self, building, unit):
        return (self.valid_barracks(building) and unit in self.garrison(building).units
                and pygame.Vector2(unit.position).distance_to(building.position) <= DISBAND_RADIUS
                and all(member.position.distance_to(building.position) <= DISBAND_RADIUS for member in unit.members))

    def disband(self, building, unit):
        if not self.can_disband(building, unit):
            return False, "Для розпуску поверніть увесь підрозділ до казарм (230 м)."
        self.control.cancel()
        unit.selected = False
        self.control.units.remove(unit)
        self.garrison(building)
        self.revision += 1
        return True, ""

    def cancel_last(self, building):
        if not self.valid_barracks(building):
            return
        state = self.garrison(building)
        if not state.queue:
            return
        self.kingdom.gold += state.queue.pop().price
        if not state.queue:
            state.progress = 0
            self.buildings.set_training(building, False)
        self.revision += 1
