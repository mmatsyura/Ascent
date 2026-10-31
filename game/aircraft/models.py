from dataclasses import dataclass, field
from math import ceil

from game.aircraft.definitions import DroneDefinition, DRONE_VISION_RADIUS, FLIGHT_ALTITUDE


@dataclass(eq=False)
class Drone:
    definition: DroneDefinition
    airport: object
    position: tuple[float, float]
    identity: int
    state: str = "takeoff"
    state_time: float = 0
    flight_age: float = 0
    altitude: float = 0
    heading: float = 45
    animation_time: float = 0
    orbit_center: tuple[float, float] = (0, 0)
    orbit_radius: float = 170
    route: list = field(default_factory=list)
    photographed: int = 0
    attack_target: object = None
    attack_position: tuple[float, float] | None = None
    dive_origin: tuple[float, float] | None = None

    @property
    def owner(self):
        return self.airport.owner

    @property
    def controllable(self):
        return self.state in ("takeoff", "cruising")

    @property
    def remaining(self):
        return max(0, self.definition.flight_lifetime - self.flight_age)

    @property
    def vision_radius(self):
        return DRONE_VISION_RADIUS * self.definition.vision_factor * max(0, min(1, self.altitude / FLIGHT_ALTITUDE))

    @property
    def timer_label(self):
        seconds = max(0, ceil(self.remaining))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
