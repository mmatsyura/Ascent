from game.rendering import RenderPart


def faded_parts(parts, opacity):
    if opacity <= 0:
        return
    for part in parts:
        if opacity >= 255:
            yield part
        else:
            image = part.image.copy()
            source_alpha = part.image.get_alpha()
            image.set_alpha(round((255 if source_alpha is None else source_alpha) * opacity / 255))
            yield RenderPart(part.depth, image, part.rectangle)


class ObjectReveals:
    def __init__(self, reconnaissance):
        self.reconnaissance = reconnaissance
        self.duration = .7
        self.cities = {}
        self.buildings = {}
        self.units = {}

    @staticmethod
    def building_key(building):
        return building.definition.key, tuple(building.position)

    @staticmethod
    def opacity(progress):
        return round(255 * progress * progress * (3 - 2 * progress))

    def update(self, elapsed_seconds):
        step = max(0, elapsed_seconds) / self.duration
        recon = self.reconnaissance
        present = set(recon.units)
        for unit in tuple(self.units):
            if unit not in present:
                del self.units[unit]
        for city in recon.displayed_cities():
            previous = self.cities.get(city.position, 0)
            self.cities[city.position] = 1 if city.owner == "blue" else min(1, previous + step)
        for building in recon.displayed_buildings():
            key = self.building_key(building)
            previous = self.buildings.get(key, 0)
            self.buildings[key] = 1 if building.owner == "blue" else min(1, previous + step)
        for unit in recon.units:
            if unit.owner == "blue":
                self.units[unit] = 1
            elif unit in recon.visible_enemies:
                self.units[unit] = min(1, self.units.get(unit, 0) + step)
            else:
                self.units.pop(unit, None)

    def city_opacity(self, city):
        return 255 if city.owner == "blue" else self.opacity(self.cities.get(city.position, 0))

    def building_opacity(self, building):
        return 255 if building.owner == "blue" else self.opacity(self.buildings.get(self.building_key(building), 0))

    def unit_opacity(self, unit):
        return 255 if unit.owner == "blue" else self.opacity(self.units.get(unit, 0))
