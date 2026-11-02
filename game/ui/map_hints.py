import math

import pygame

from game.ui.theme import fit_text, ui_font
from game.world.cities import City, marker_radius, marker_scale


class MapHints:
    def __init__(self):
        self.target = None
        self.selected_city = None
        self.hover_seconds = 0
        self.caption = ""
        self.opacity = 0
        self.font = ui_font(15)
        self.selected_font = ui_font(17, True)

    def select_city(self, city):
        self.selected_city = city
        if city is not None:
            self.target = city
            self.caption = f"{'Столиця' if city.capital else 'Місто'} · {city.name}"
            self.hover_seconds = 0

    def update(self, elapsed_seconds, pointer, screen, camera, cities, units, blocked=False):
        unit = None if blocked else units.unit_at(pointer, screen, camera)
        city = None if blocked or unit is not None else cities.city_at(pointer, screen, camera)
        if city is None and unit is None and self.selected_city is not None:
            city = cities.known_city(self.selected_city.position)
            self.selected_city = city
        target = city if city is not None else unit
        if target is not self.target:
            self.hover_seconds = 0
            if target is not None:
                self.target = target
                self.opacity = 0
        else:
            self.hover_seconds += elapsed_seconds
        visible = city is not None or (unit is not None and self.hover_seconds >= 2)
        if visible:
            self.caption = (
                f"{'Столиця' if city.capital else 'Місто'} · {city.name}"
                if city is not None
                else unit.name
            )
        target_opacity = (
            (245 if city is not None and city is self.selected_city else 165) if visible else 0
        )
        self.opacity += (target_opacity - self.opacity) * -math.expm1(-elapsed_seconds / 0.16)
        if target is None and self.opacity < 2:
            self.target = None

    def draw(self, screen, command_panel, minimap, camera=None):
        if self.opacity < 2 or not self.caption:
            return
        left = command_panel.panel_area.right + 14
        right = minimap.panel_area.left - 14
        if isinstance(self.target, City) and camera is not None:
            width = 300
            point = camera.world_to_screen(self.target.position)
            radius = marker_radius(
                self.target.capital,
                marker_scale(screen.get_size(), camera.zoom, camera.minimum_zoom),
            )
            center = (point.x, point.y + radius + 17)
        elif right - left >= 220:
            width = right - left
            center = ((left + right) // 2, screen.get_height() - 27)
        else:
            width = max(220, screen.get_width() - command_panel.panel_area.right - 30)
            center = (
                screen.get_width() - width // 2 - 18,
                min(command_panel.panel_area.top, minimap.panel_area.top) - 19,
            )
        selected = isinstance(self.target, City) and self.target is self.selected_city
        font = self.selected_font if selected else self.font
        caption = fit_text(font, self.caption, width)
        image = font.render(caption, True, (246, 229, 182) if selected else (207, 218, 216))
        shadow = font.render(caption, True, (5, 13, 16))
        rectangle = image.get_rect(center=(round(center[0]), round(center[1])))
        rectangle.clamp_ip(screen.get_rect().inflate(-12, -12))
        if selected:
            background = pygame.Surface((rectangle.w + 22, rectangle.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(background, (13, 24, 27, 220), background.get_rect(), border_radius=4)
            pygame.draw.rect(
                background, (165, 146, 95, 220), background.get_rect(), 1, border_radius=4
            )
            pygame.draw.line(background, (225, 199, 126), (9, 1), (background.get_width() - 10, 1))
            background.set_alpha(round(self.opacity))
            screen.blit(background, (rectangle.x - 11, rectangle.y - 6))
        shadow.set_alpha(round(self.opacity))
        image.set_alpha(round(self.opacity))
        screen.blit(shadow, rectangle.move(0, 1))
        screen.blit(image, rectangle)
