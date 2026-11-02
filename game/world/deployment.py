import pygame

from game.settings import WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome
from game.world.units import TankUnit, UnitToken


def group_positions(terrain, country, cities, territory_field):
    locations = [cities.player_capital, *cities.player_cities]
    center = sum((pygame.Vector2(city.position) for city in locations), pygame.Vector2()) / len(
        locations
    )
    triangle = ((-86, -50), (86, -50), (0, 99))
    layouts = (triangle, triangle, triangle, ((-80, 0), (80, 0)))
    for separation in (320, 280, 240):
        positions = []
        for city, layout in zip(locations, layouts):
            direction = center - city.position
            angle = direction.as_polar()[1] if direction.length_squared() > 1 else 35
            chosen = None
            for distance in (210, 250, 170, 290, 330):
                for turn in (0, 45, -45, 90, -90, 135, -135, 180):
                    origin = pygame.Vector2(city.position) + pygame.Vector2(distance, 0).rotate(
                        angle + turn
                    )
                    group = [
                        origin + pygame.Vector2(offset).rotate(angle + turn) for offset in layout
                    ]
                    valid = True
                    for point in group:
                        if not (
                            360 <= point.x < WORLD_WIDTH - 360
                            and 360 <= point.y < WORLD_HEIGHT - 360
                        ):
                            valid = False
                            break
                        if (
                            territory_field[
                                int(point.y // country.grid_size), int(point.x // country.grid_size)
                            ]
                            < 96
                        ):
                            valid = False
                            break
                        if terrain.biome_at(point) not in (Biome.MEADOW, Biome.FOREST, Biome.BEACH):
                            valid = False
                            break
                        if not terrain.can_place_soldier(point, 4) or not terrain.can_place_unit(
                            point, 24
                        ):
                            valid = False
                            break
                        if any(
                            point.distance_squared_to(other.position) < 112**2
                            for other in cities.cities
                        ):
                            valid = False
                            break
                        if any(
                            point.distance_squared_to(other) < separation**2 for other in positions
                        ):
                            valid = False
                            break
                    if valid:
                        chosen = [tuple(point) for point in group]
                        break
                if chosen is not None:
                    break
            if chosen is None:
                break
            positions.extend(chosen)
        if len(positions) == 11:
            return positions
    raise ValueError("Недостатньо вільного місця для початкових груп армії")


def starting_army(terrain, country, cities, profile, territory_field):
    positions = group_positions(terrain, country, cities, territory_field)
    units = []
    infantry_number = 0
    tank_number = 0
    for index, position in enumerate(positions):
        if index in (2, 5, 8):
            name = ("Танк «Бастіон»", "Танк «Оплот»", "Танк «Варта»")[tank_number]
            if tank_number == 0:
                name = profile.name_for(cities.player_capital.position, name)
            unit_type = TankUnit
            tank_number += 1
        else:
            infantry_number += 1
            name = f"{infantry_number}-й піхотний загін"
            if infantry_number <= len(cities.player_cities):
                name = profile.name_for(cities.player_cities[infantry_number - 1].position, name)
            unit_type = UnitToken
        unit = unit_type(position, name=profile.name_for(position, name), profile_anchor=position)
        unit.update_environment(terrain.biome_at(position), 0)
        units.append(unit)
    return units
