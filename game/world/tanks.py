from dataclasses import dataclass, field
import random

from game.world.units import UnitToken


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
