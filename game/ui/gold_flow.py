from dataclasses import dataclass

import pygame

from game.ui.hud_icons import gold_icon
from game.ui.theme import ui_font


@dataclass
class GoldPayment:
    position: tuple[float, float]
    amount: int
    age: float = 0


class GoldFlow:
    def __init__(self):
        self.payments = []
        self.font = ui_font(16, True)
        self.coin = pygame.transform.smoothscale(gold_icon(), (13, 13))

    def paid(self, total, mines):
        for mine, amount in mines:
            if amount > 0:
                self.payments.append(GoldPayment(tuple(mine.position), amount))
        self.payments = self.payments[-96:]

    def update(self, elapsed_seconds):
        for payment in self.payments:
            payment.age += elapsed_seconds
        self.payments[:] = [payment for payment in self.payments if payment.age < 1.8]

    def draw_labels(self, screen, camera):
        for payment in self.payments:
            position = camera.world_to_screen(payment.position) - pygame.Vector2(
                0, 42 * camera.zoom + payment.age * 16
            )
            if not screen.get_rect().inflate(100, 100).collidepoint(position):
                continue
            alpha = round(
                255 * min(1, payment.age / 0.12) * max(0, min(1, (1.8 - payment.age) / 0.55))
            )
            label = self.font.render(f"+{payment.amount}", True, (247, 213, 120))
            shadow = self.font.render(f"+{payment.amount}", True, (24, 29, 21))
            label.set_alpha(alpha)
            shadow.set_alpha(alpha)
            area = label.get_rect(center=(round(position.x + 7), round(position.y)))
            screen.blit(shadow, area.move(1, 1))
            screen.blit(label, area)
            coin = self.coin.copy()
            coin.set_alpha(alpha)
            screen.blit(coin, (area.x - 16, area.centery - 6))
