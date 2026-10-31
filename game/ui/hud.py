import pygame

from game.ui.hud_icons import create_hud_icons
from game.ui.fonts import ui_font
from game.ui.theme import ACCENT, MUTED, TEXT, panel_surface
from game.ui.transitions import SmoothLayer


class KingdomHud:
    def __init__(self):
        self.panel_area = pygame.Rect(10, 12, 526, 76)
        self.label_font = ui_font(14, True)
        self.value_font = ui_font(25, True)
        self.entries = [
            ("gold", "ЗОЛОТО", 150),
            ("army", "АРМІЯ", 150),
            ("area", "ТЕРИТОРІЯ", 190),
        ]
        self.icons = {name: pygame.transform.smoothscale(icon, (34, 34)) for name, icon in create_hud_icons().items()}
        self.cached_values = None
        self.surface = pygame.Surface(self.panel_area.size, pygame.SRCALPHA)
        self.background = self.create_background()
        self.motion = SmoothLayer(.16)

    def create_background(self):
        background = panel_surface(self.panel_area.size).copy()
        position_x = 18

        for index, (name, label, cell_width) in enumerate(self.entries):
            if index:
                pygame.draw.line(background, (76, 77, 55), (position_x - 7, 19), (position_x - 7, 51))
                pygame.draw.polygon(background, (173, 143, 87), [(position_x - 7, 31), (position_x - 5, 35), (position_x - 7, 39), (position_x - 9, 35)])

            background.blit(self.icons[name], (position_x + 1, 18))
            label_image = self.label_font.render(label, True, MUTED)
            background.blit(label_image, (position_x + 44, 13))
            position_x += cell_width

        return background

    def draw(self, screen, kingdom, duration=1 / 60):
        values = (kingdom.gold, kingdom.army, round(kingdom.land_fraction * 100, 1))

        if values != self.cached_values:
            self.surface = pygame.Surface(self.panel_area.size, pygame.SRCALPHA)
            self.cached_values = values
            self.surface.fill((0, 0, 0, 0))
            self.surface.blit(self.background, (0, 0))
            position_x = 18

            for index, (name, _, cell_width) in enumerate(self.entries):
                number = f"{values[index]:.1f}%".replace('.', ',') if name == "area" else format(values[index], ",").replace(",", " ")
                value_image = self.value_font.render(number, True, ACCENT if name == "gold" else TEXT)
                self.surface.blit(value_image, (position_x + 43, 30))
                position_x += cell_width

        self.motion.set(self.surface, self.panel_area.topleft)
        self.motion.draw(screen, duration)
