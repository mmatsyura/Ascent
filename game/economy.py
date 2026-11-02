import math


class Economy:
    def __init__(self, kingdom):
        self.kingdom = kingdom
        self.payment_interval = 2.0
        self.base_income = 1.0
        self.payment_time = 0.0
        self.pending_gold = 0.0
        self.mine_pending = {}
        self.on_payout = None

    def update(self, elapsed_seconds, building_income=0, mines=()):
        remaining = max(0, elapsed_seconds)
        income = self.base_income + building_income
        while remaining > 1e-9:
            duration = min(remaining, self.payment_interval - self.payment_time)
            self.pending_gold += income * duration
            for mine in mines:
                self.mine_pending[mine] = (
                    self.mine_pending.get(mine, 0) + mine.definition.income_per_second * duration
                )
            self.payment_time += duration
            remaining -= duration
            if self.payment_time >= self.payment_interval - 1e-9:
                payout = math.floor(self.pending_gold + 1e-8)
                self.kingdom.gold += payout
                self.pending_gold -= payout
                self.payment_time = 0.0
                payments = []
                for mine, earned in tuple(self.mine_pending.items()):
                    amount = math.floor(earned + 1e-8)
                    self.mine_pending[mine] -= amount
                    if amount:
                        payments.append((mine, amount))
                if self.on_payout is not None:
                    self.on_payout(payout, payments)
