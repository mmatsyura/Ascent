from dataclasses import dataclass

from game.settings import BASE_UNIT_VISION_RADIUS


TAKEOFF_DURATION = 6.0
FALL_DURATION = 3.0
BURN_DURATION = 20.0
FLIGHT_ALTITUDE = 26.0
DRONE_VISION_RADIUS = BASE_UNIT_VISION_RADIUS * .9


@dataclass(frozen=True)
class DroneDefinition:
    key: str
    name: str
    price: int
    speed: float
    description: str
    accent: tuple[int, int, int]
    flight_lifetime: float = 600.0
    production_duration: float = 30.0
    vision_factor: float = 1.0
    strike: bool = False
    records_exploration: bool = True


DRONES = (
    DroneDefinition("kamikaze", "Камикадзе", 1500, 10, "Легкий дрон із дельтоподібним крилом.", (190, 177, 122), 300, 30),
    DroneDefinition("p1_sun", "P1-SUN", 2000, 12, "Крилатий розвідник із хвостовими балками.", (155, 194, 201), 600, 45),
    DroneDefinition("aviamen", "Авіамен", 2500, 14, "Маневровий апарат повітряного огляду.", (173, 195, 148), 900, 60),
    DroneDefinition("flamingo", "Фламінго", 3000, 42, "Тимчасовий огляд та одноразовий удар по цілі.", (215, 162, 130), 900, 120, 1 / 3.6, True, False),
)
DRONES_BY_KEY = {definition.key: definition for definition in DRONES}
