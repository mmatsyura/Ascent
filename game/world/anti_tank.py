from dataclasses import dataclass

from game.world.units import UnitToken


@dataclass(eq=False)
class AntiTankUnit(UnitToken):
    @property
    def is_anti_tank(self):
        return True

    @property
    def speed_factor(self):
        return .76

    @property
    def detail_label(self):
        return "Протитанковий загін · 6 бійців"
