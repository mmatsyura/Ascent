import pygame

from game.world.biomes import Biome
from game.world.squad_motion import initialize_squad
from game.world.tanks import TankUnit
from game.world.units import UnitToken


def deploy_opponents(app):
    for owner in ('red', 'green', 'purple'):
        cities = sorted((city for city in app.city_map.cities if city.owner == owner), key=lambda city: not city.capital)
        for index in range(11):
            city = cities[min(3, index // 3)]
            chosen = None
            for radius in range(130, 650, 45):
                for angle in range(0, 360, 20):
                    point = pygame.Vector2(city.position) + pygame.Vector2(radius, 0).rotate(angle + index * 37)
                    if app.terrain.biome_at(point) == Biome.WATER or not app.terrain.can_place_unit(point, 24):
                        continue
                    if any(point.distance_squared_to(other.position) < 110**2 for other in app.units):
                        continue
                    nearest = min(app.city_map.cities, key=lambda item: point.distance_squared_to(item.position) / item.influence_weight**2)
                    if nearest.owner != owner:
                        continue
                    chosen = tuple(point)
                    break
                if chosen:
                    break
            if chosen is None:
                raise ValueError(f'No deployment location for {owner}: {index}')
            kind = TankUnit if index in (2, 5, 8) else UnitToken
            unit = kind(chosen, owner=owner, name=f'{"Танк" if kind is TankUnit else "Піхотний загін"} {index+1}')
            unit.update_environment(app.terrain.biome_at(chosen), 0)
            if not unit.is_tank:
                initialize_squad(unit, app.terrain, app.unit_control.soldier_navigation,
                                 placement_allowed=lambda point: app.terrain.biome_at(point) in (Biome.MEADOW, Biome.FOREST, Biome.BEACH))
            app.units.append(unit)
