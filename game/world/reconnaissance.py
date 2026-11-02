from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Contact:
    position: tuple[float, float]
    owner: str
    name: str
    is_tank: bool
    observed_at: float


class Reconnaissance:
    def __init__(self, visibility, cities, buildings, units):
        self.visibility = visibility
        self.cities = cities
        self.buildings = buildings
        self.units = units
        self.elapsed = 0.0
        self.contact_lifetime = 30.0
        self.city_memory = {}
        self.on_city_discovered = None
        self.building_memory = {}
        self.contacts = {}
        self.visible_enemies = set()
        self.hidden_contacts = set()

    def update(self, elapsed_seconds):
        self.elapsed += max(0, elapsed_seconds)
        self.observe_cities()
        self.observe_buildings()
        self.observe_units()

    def observe_cities(self):
        observed = set()
        for city in self.cities.cities:
            if self.visibility.is_visible(city.position):
                observed.add(city.position)
                if city.position not in self.city_memory and self.on_city_discovered is not None:
                    self.on_city_discovered(city)
                frame = self.cities.flag_frame(city) if city.capital else None
                self.city_memory[city.position] = replace(city, remembered_frame=frame)
        for position in tuple(self.city_memory):
            if position not in observed and self.visibility.is_visible(position):
                del self.city_memory[position]

    def observe_buildings(self):
        observed = set()
        for building in self.buildings.buildings:
            if self.visibility.is_visible(building.position):
                observed.add(building)
                self.building_memory[building] = replace(building)
        for identity, snapshot in tuple(self.building_memory.items()):
            if identity not in observed and self.visibility.is_visible(snapshot.position):
                del self.building_memory[identity]

    def observe_units(self):
        self.visible_enemies = set()
        present = set(self.units)
        for unit in self.units:
            if unit.owner != "blue" and self.visibility.is_visible(unit.position):
                self.visible_enemies.add(unit)
                self.contacts[unit] = Contact(
                    tuple(unit.position), unit.owner, unit.name, unit.is_tank, self.elapsed
                )
                self.hidden_contacts.discard(unit)
        for unit, contact in tuple(self.contacts.items()):
            if unit in self.visible_enemies:
                continue
            expired = self.elapsed - contact.observed_at >= self.contact_lifetime
            location_visible = self.visibility.is_visible(contact.position)
            checked = location_visible and (unit in self.hidden_contacts or unit not in present)
            if not location_visible:
                self.hidden_contacts.add(unit)
            if expired or checked or unit.owner == "blue":
                del self.contacts[unit]
                self.hidden_contacts.discard(unit)

    def displayed_cities(self):
        live = {
            city.position: city
            for city in self.cities.cities
            if self.visibility.is_visible(city.position)
        }
        result = dict(self.city_memory)
        result.update(live)
        return tuple(result.values())

    def known_city(self, position):
        if self.visibility.is_visible(position):
            return next((city for city in self.cities.cities if city.position == position), None)
        return self.city_memory.get(position)

    def displayed_buildings(self):
        live = {
            building: building
            for building in self.buildings.buildings
            if building.owner == "blue" or self.visibility.is_visible(building.position)
        }
        result = dict(self.building_memory)
        result.update(live)
        return tuple(result.values())

    def old_contacts(self):
        return tuple(
            (contact, self.elapsed - contact.observed_at)
            for unit, contact in self.contacts.items()
            if unit not in self.visible_enemies
        )
