from dataclasses import dataclass
import math
import random

import pygame

from game.ui.theme import ACCENT, MUTED, TEXT, draw_button, panel_surface, ui_font


@dataclass
class CelebrationParticle:
    position: pygame.Vector2
    velocity: pygame.Vector2
    color: tuple
    lifetime: float
    age: float = 0
    size: float = 2
    confetti: bool = False
    spin: float = 0


class Victory:
    def __init__(self):
        self.active = False
        self.achieved = False
        self.elapsed = 0
        self.fraction = 0
        self.background = None
        self.particles = []
        self.random = random.Random(5480)
        self.burst_time = 0.3
        self.size = None
        self.hover = 0
        self.button = pygame.Rect(0, 0, 260, 43)
        self.title = ui_font(62, True)
        self.subtitle = ui_font(20)
        self.body = ui_font(17)
        self.small = ui_font(14, True)
        self.palette = (
            (244, 205, 106),
            (91, 164, 236),
            (154, 222, 225),
            (246, 231, 179),
            (211, 147, 79),
        )
        self.on_continue = None

    def check(self, fraction):
        if self.achieved or fraction + 1e-9 < 0.8:
            return False
        self.active = self.achieved = True
        self.elapsed = 0
        self.fraction = fraction
        self.background = None
        return True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
            pygame.K_ESCAPE,
            pygame.K_SPACE,
        ):
            if self.elapsed > 0.65:
                self.active = False
        elif (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.button.collidepoint(event.pos)
        ):
            if self.elapsed > 0.65:
                self.active = False
        if not self.active and self.on_continue is not None:
            self.on_continue()
        return True

    def update(self, duration, size):
        self.elapsed += max(0, duration)
        self.size = size
        self.burst_time -= duration
        if self.burst_time <= 0 and self.elapsed < 10:
            self.burst_time = self.random.uniform(0.45, 0.85)
            self.burst(size)
        if self.elapsed < 7 and len(self.particles) < 380:
            for _ in range(2):
                self.particles.append(
                    CelebrationParticle(
                        pygame.Vector2(self.random.uniform(0, size[0]), -10),
                        pygame.Vector2(self.random.uniform(-25, 25), self.random.uniform(25, 60)),
                        self.random.choice(self.palette),
                        9,
                        size=self.random.uniform(2, 4),
                        confetti=True,
                        spin=self.random.uniform(0, math.tau),
                    )
                )
        for particle in self.particles:
            particle.age += duration
            particle.velocity.y += (9 if particle.confetti else 30) * duration
            particle.position += particle.velocity * duration
            particle.spin += duration * 2
            if not particle.confetti:
                particle.velocity *= math.exp(-duration * 0.5)
        self.particles[:] = [
            particle
            for particle in self.particles
            if particle.age < particle.lifetime and particle.position.y < size[1] + 20
        ]
        hovered = self.button.collidepoint(pygame.mouse.get_pos())
        self.hover += (float(hovered) - self.hover) * -math.expm1(-duration / 0.1)

    def burst(self, size):
        if len(self.particles) > 350:
            return
        origin = pygame.Vector2(
            self.random.uniform(size[0] * 0.1, size[0] * 0.9),
            self.random.uniform(size[1] * 0.08, size[1] * 0.4),
        )
        color = self.random.choice(self.palette)
        for index in range(48):
            angle = index / 48 * math.tau + self.random.uniform(-0.03, 0.03)
            speed = self.random.uniform(45, 135)
            self.particles.append(
                CelebrationParticle(
                    origin.copy(),
                    pygame.Vector2(math.cos(angle), math.sin(angle)) * speed,
                    color,
                    self.random.uniform(1.3, 2.3),
                    size=self.random.uniform(1.4, 2.7),
                )
            )

    def crest(self, surface, center):
        x, y = center
        scale = 1 + 0.025 * math.sin(self.elapsed * 2)
        for side in (-1, 1):
            for index in range(9):
                angle = math.radians(33 + index * 13)
                px = x + side * math.sin(angle) * 67 * scale
                py = y + math.cos(angle) * 66 * scale
                leaf = pygame.Rect(0, 0, 17, 7)
                leaf.center = (round(px), round(py))
                pygame.draw.ellipse(
                    surface, (184 + index * 5, 151 + index * 5, 81 + index * 4), leaf
                )
        pygame.draw.circle(surface, (215, 184, 111), (x, y), 52)
        pygame.draw.circle(surface, (35, 67, 86), (x, y), 48)
        pygame.draw.circle(surface, (29, 53, 65), (x, y), 43)
        shield = [
            (x - 28, y - 25),
            (x, y - 33),
            (x + 28, y - 25),
            (x + 24, y + 14),
            (x, y + 35),
            (x - 24, y + 14),
        ]
        pygame.draw.polygon(surface, (192, 167, 103), shield)
        pygame.draw.polygon(
            surface,
            (47, 113, 175),
            [
                (x - 24, y - 22),
                (x, y - 28),
                (x + 24, y - 22),
                (x + 20, y + 12),
                (x, y + 29),
                (x - 20, y + 12),
            ],
        )
        points = []
        for index in range(10):
            angle = -math.pi / 2 + index * math.pi / 5
            radius = 22 if index % 2 == 0 else 9
            points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
        pygame.draw.polygon(surface, (245, 218, 142), points)

    def draw(self, screen):
        if not self.active:
            return
        if self.background is None:
            self.background = screen.copy()
        elif self.background.get_size() != screen.get_size():
            self.background = pygame.transform.smoothscale(self.background, screen.get_size())
        screen.blit(self.background, (0, 0))
        width, height = screen.get_size()
        reveal = min(1, self.elapsed / 0.75)
        reveal = reveal * reveal * (3 - 2 * reveal)
        veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        veil.fill((4, 13, 22, round(214 * reveal)))
        screen.blit(veil, (0, 0))
        halo = pygame.Surface((600, 600), pygame.SRCALPHA)
        for radius in range(280, 20, -12):
            opacity = round((1 - radius / 300) * 5 * reveal)
            pygame.draw.circle(halo, (94, 158, 190, opacity), (300, 300), radius)
        screen.blit(halo, (width // 2 - 300, height // 2 - 350))
        card_width, card_height = min(720, width - 48), min(472, height - 56)
        card = panel_surface((card_width, card_height)).copy()
        center = card_width // 2
        self.crest(card, (center, 93))
        title_font = self.title if width >= 800 else ui_font(48, True)
        title = title_font.render("ПЕРЕМОГА", True, (247, 222, 155))
        shadow = title_font.render("ПЕРЕМОГА", True, (8, 16, 20))
        card.blit(shadow, shadow.get_rect(center=(center + 1, 195)))
        card.blit(title, title.get_rect(center=(center, 192)))
        caption = self.subtitle.render("Ваше королівство підкорило цей світ", True, TEXT)
        card.blit(caption, caption.get_rect(center=(center, 244)))
        percent = f"{self.fraction * 100:.1f}%".replace(".", ",")
        detail = self.body.render(f"Під контролем {percent} суші · мета 80%", True, MUTED)
        card.blit(detail, detail.get_rect(center=(center, 279)))
        bar = pygame.Rect(76, 311, card_width - 152, 7)
        pygame.draw.rect(card, (18, 32, 34), bar, border_radius=3)
        pygame.draw.rect(
            card,
            (201, 177, 107),
            (bar.x, bar.y, round(bar.w * min(1, self.fraction)), bar.h),
            border_radius=3,
        )
        label = self.small.render("СИНЄ КОРОЛІВСТВО · НОВА ДОБА", True, ACCENT)
        card.blit(label, label.get_rect(center=(center, 345)))
        local_button = pygame.Rect(center - 130, card_height - 87, 260, 43)
        draw_button(card, local_button, self.hover)
        text = self.body.render("Продовжити гру", True, TEXT)
        card.blit(text, text.get_rect(center=local_button.center))
        hint = self.small.render("Enter — продовжити", True, MUTED)
        card.blit(hint, hint.get_rect(center=(center, card_height - 27)))
        position = (
            width // 2 - card_width // 2,
            height // 2 - card_height // 2 + round((1 - reveal) * 24),
        )
        card.set_alpha(round(reveal * 255))
        screen.blit(card, position)
        self.button = local_button.move(position)
        particles = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        for particle in self.particles:
            fade = min(1, particle.age / 0.1, (particle.lifetime - particle.age) / 0.6) * reveal
            color = (*particle.color, max(0, min(255, round(255 * fade))))
            point = (round(particle.position.x), round(particle.position.y))
            if particle.confetti:
                length = max(1, round(particle.size * (1 + abs(math.sin(particle.spin)))))
                pygame.draw.line(particles, color, point, (point[0] + length, point[1] + 2), 2)
            else:
                tail = particle.position - particle.velocity * 0.045
                pygame.draw.line(
                    particles,
                    color,
                    point,
                    (round(tail.x), round(tail.y)),
                    max(1, round(particle.size)),
                )
        screen.blit(particles, (0, 0))


class Defeat:
    def __init__(self, on_home):
        self.active = False
        self.achieved = False
        self.elapsed = 0
        self.background = None
        self.on_home = on_home
        self.button = pygame.Rect(0, 0, 280, 44)
        self.hover = 0
        self.title = ui_font(58, True)
        self.body = ui_font(19)
        self.small = ui_font(15)

    def check(self, cities):
        if self.achieved or any(city.owner == "blue" for city in cities):
            return False
        self.active = self.achieved = True
        self.elapsed = 0
        self.background = None
        return True

    def update(self, duration, size):
        self.elapsed += max(0, duration)
        target = float(self.button.collidepoint(pygame.mouse.get_pos()))
        self.hover += (target - self.hover) * -math.expm1(-max(0, duration) / 0.1)

    def handle_event(self, event):
        if self.elapsed < 0.65:
            return True
        keyboard = event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
            pygame.K_ESCAPE,
        )
        clicked = (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.button.collidepoint(event.pos)
        )
        if keyboard or clicked:
            self.on_home()
        return True

    def draw(self, screen):
        if not self.active:
            return
        if self.background is None:
            self.background = screen.copy()
        elif self.background.get_size() != screen.get_size():
            self.background = pygame.transform.smoothscale(self.background, screen.get_size())
        screen.blit(self.background, (0, 0))
        width, height = screen.get_size()
        reveal = min(1, self.elapsed / 0.7)
        reveal = reveal * reveal * (3 - 2 * reveal)
        veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        veil.fill((12, 12, 19, round(215 * reveal)))
        screen.blit(veil, (0, 0))
        card = panel_surface((min(660, width - 48), 390)).copy()
        center = card.get_width() // 2
        pygame.draw.line(card, (161, 106, 85), (center - 85, 57), (center + 85, 57), 2)
        title = self.title.render("ПОРАЗКА", True, (214, 154, 129))
        card.blit(title, title.get_rect(center=(center, 119)))
        caption = self.body.render("Усі ваші міста та столицю захоплено", True, TEXT)
        card.blit(caption, caption.get_rect(center=(center, 191)))
        detail = self.small.render("Ви більше не контролюєте жодного міста.", True, MUTED)
        card.blit(detail, detail.get_rect(center=(center, 226)))
        local_button = pygame.Rect(center - 140, 281, 280, 44)
        draw_button(card, local_button, self.hover)
        label = self.body.render("До головного меню", True, TEXT)
        card.blit(label, label.get_rect(center=local_button.center))
        hint = self.small.render("Enter / Esc — головне меню", True, MUTED)
        card.blit(hint, hint.get_rect(center=(center, 352)))
        position = (width // 2 - center, height // 2 - 195 + round((1 - reveal) * 18))
        card.set_alpha(round(255 * reveal))
        screen.blit(card, position)
        self.button = local_button.move(position)
