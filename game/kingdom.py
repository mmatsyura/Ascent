from dataclasses import dataclass, field
from collections.abc import Callable


@dataclass
class Kingdom:
    gold: int = 500
    army: int = 0
    area: int = 0
    land_fraction: float = 0
    on_purchase: Callable | None = field(default=None, repr=False, compare=False)

    def can_afford(self, cost):
        return all(resource == "gold" and 0 <= amount <= self.gold for resource, amount in cost.items())

    def spend(self, cost):
        if not self.can_afford(cost):
            return False
        for resource, amount in cost.items():
            setattr(self, resource, getattr(self, resource) - amount)
        if self.on_purchase is not None and any(amount > 0 for amount in cost.values()):
            self.on_purchase()
        return True
