from dataclasses import dataclass

from game.settings import BASE_CITY_VISION_RADIUS


@dataclass(frozen=True)
class BuildingDefinition:
    key: str
    name: str
    description: str
    effect: str
    gold_cost: int
    accent: tuple[int, int, int]
    footprint: tuple[int, int]
    sprite_size: tuple[int, int]
    income_per_second: float = 0
    construction_duration: float = 45

    @property
    def cost(self):
        return {"gold": self.gold_cost}

    @property
    def vision_radius(self):
        return BASE_CITY_VISION_RADIUS / 2


BUILDINGS = (
    BuildingDefinition(
        "mine",
        "Шахта",
        "Підземний видобуток руди.",
        "+8 золота за секунду",
        500,
        (220, 187, 121),
        (72, 48),
        (104, 98),
        8,
        30,
    ),
    BuildingDefinition(
        "airport",
        "Військовий аеропорт",
        "База бойової авіації та БПЛА.",
        "Закупівля та запуск дронів",
        1000,
        (144, 183, 201),
        (124, 84),
        (156, 124),
        construction_duration=60,
    ),
    BuildingDefinition(
        "barracks",
        "Казарми",
        "База підготовки особового складу.",
        "Підготовка піхоти й танків · 15 місць",
        500,
        (155, 183, 137),
        (104, 72),
        (136, 112),
    ),
)

BUILDINGS_BY_KEY = {definition.key: definition for definition in BUILDINGS}
