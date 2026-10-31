from dataclasses import dataclass

from game.world.tanks import TankUnit


@dataclass(eq=False)
class PatriotUnit(TankUnit):
    deployment: float = 0
    deployment_delay: float = .7

    @property
    def is_patriot(self):
        return True

    @property
    def icon_key(self):
        return "patriot"

    @property
    def speed_factor(self):
        return 1 / (1.8 * 1.3)

    @property
    def detail_label(self):
        return "ППО · перезаряджання 4 с · шанс 35%"

    def update_environment(self, biome, elapsed_seconds):
        super().update_environment(biome, elapsed_seconds)
        self.vision_radius *= .85

    def update_deployment(self, duration):
        duration = max(0, duration)
        if self.route:
            self.deployment_delay = .7
            self.deployment = max(0, self.deployment - duration / 2.6)
        else:
            self.deployment_delay = max(0, self.deployment_delay - duration)
            if self.deployment_delay == 0:
                self.deployment = min(1, self.deployment + duration / 3.8)
