from functools import lru_cache

import pygame

from game.ui.theme import ACCENT, MUTED, TEXT, panel_surface
from game.world.buildings import BUILDINGS


class ConstructionView:
    def __init__(self, panel):
        self.panel = panel
        self.page = 0

    @lru_cache(maxsize=8)
    def background(self, size):
        image = panel_surface(size).copy()
        self.panel.rule(image, 23, size[0] - 24, 65)
        return image

    @lru_cache(maxsize=24)
    def icon(self, key, size):
        source = (
            self.panel.building_icons[key]
            if key in self.panel.building_icons
            else self.panel.icons[key]
        )
        return pygame.transform.smoothscale(source, (size, size))

    @lru_cache(maxsize=32)
    def project_background(self, size, selected, hovered):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        width, height = size
        for vertical in range(height):
            progress = vertical / max(1, height - 1)
            color = (
                (round(45 - 14 * progress), round(53 - 13 * progress), round(41 - 11 * progress))
                if selected
                else (round(31 - 8 * progress), round(40 - 9 * progress), round(33 - 8 * progress))
            )
            pygame.draw.line(surface, color, (0, vertical), (width - 1, vertical))
        pygame.draw.rect(
            surface,
            ACCENT if selected else ((152, 143, 103) if hovered else (88, 96, 72)),
            surface.get_rect(),
            1,
            border_radius=3,
        )
        pygame.draw.line(surface, (122, 127, 91), (2, 2), (width - 3, 2))
        art_width = min(104, height - 4)
        pygame.draw.rect(surface, (19, 29, 25), (2, 3, art_width, height - 6), border_radius=2)
        for horizontal in range(12, art_width, 16):
            pygame.draw.line(surface, (32, 45, 35), (horizontal, 4), (horizontal, height - 5))
        for vertical in range(14, height - 4, 16):
            pygame.draw.line(surface, (32, 45, 35), (3, vertical), (art_width, vertical))
        return surface

    def draw(self, surface, area, selected_index):
        panel = self.panel
        compact = area.h < 245
        content = area.copy()
        if not compact:
            surface.blit(self.icon("gold", 23), (area.x, area.y + 1))
            panel.label(surface, "Доступне золото", (area.x + 31, area.y + 3), "small", MUTED)
            balance = format(panel.kingdom.gold, ",").replace(",", " ")
            width = panel.fonts["title"].size(balance)[0]
            panel.label(surface, balance, (area.right - width - 1, area.y), "title", ACCENT)
            content.y += 36
            content.h -= 36
        gap = 10
        per_page = len(BUILDINGS)
        if content.h < len(BUILDINGS) * 90 + gap * (len(BUILDINGS) - 1):
            content.h -= 32
            per_page = max(1, (content.h + gap) // (90 + gap))
        page_count = (len(BUILDINGS) + per_page - 1) // per_page
        self.page = max(0, min(self.page, page_count - 1))
        first = self.page * per_page
        projects = BUILDINGS[first : first + per_page]
        row_height = (content.h - gap * (len(projects) - 1)) // len(projects)
        for row, definition in enumerate(projects):
            index = first + row
            rectangle = pygame.Rect(
                content.x, content.y + row * (row_height + gap), content.w, row_height
            )
            action = ("building", index)
            panel.register(action, rectangle)
            hovered = panel.action_areas[action].collidepoint(panel.pointer)
            selected = selected_index == index
            surface.blit(self.project_background(rectangle.size, selected, hovered), rectangle)
            if selected:
                pygame.draw.line(
                    surface,
                    definition.accent,
                    (rectangle.x, rectangle.y + 8),
                    (rectangle.x, rectangle.bottom - 9),
                    3,
                )
            icon_size = min(90, row_height - 15)
            surface.blit(
                self.icon(definition.key, icon_size),
                (rectangle.x + 6, rectangle.centery - icon_size // 2),
            )
            price_width = 106
            price_left = rectangle.right - price_width
            pygame.draw.line(
                surface,
                (52, 73, 85),
                (price_left - 7, rectangle.y + 12),
                (price_left - 7, rectangle.bottom - 13),
            )
            text_left = rectangle.x + min(104, row_height - 4) + 13
            text_width = price_left - text_left - 18
            text_top = rectangle.y + (row_height - 65) // 2
            panel.label(
                surface, definition.name, (text_left, text_top), "title", TEXT, width=text_width
            )
            panel.label(
                surface,
                definition.description,
                (text_left, text_top + 26),
                "small",
                MUTED,
                width=text_width,
            )
            panel.label(
                surface,
                definition.effect,
                (text_left, text_top + 49),
                "small",
                definition.accent,
                width=text_width,
            )
            price_top = rectangle.y + (row_height - 65) // 2
            panel.label(surface, "ВАРТІСТЬ", (price_left, price_top), "small", (158, 175, 182))
            amount = format(definition.gold_cost, ",").replace(",", " ")
            surface.blit(self.icon("gold", 21), (price_left - 1, price_top + 25))
            panel.label(
                surface,
                amount,
                (price_left + 25, price_top + 19),
                "value",
                ACCENT,
                width=price_width - 31,
            )
            shortage = max(0, definition.gold_cost - panel.kingdom.gold)
            if shortage:
                status = f"Бракує {shortage:,}".replace(",", " ")
                panel.label(
                    surface,
                    status,
                    (price_left, price_top + 51),
                    "small",
                    (206, 155, 131),
                    width=price_width - 5,
                )
            else:
                panel.button(
                    surface,
                    (price_left - 1, price_top + 51, price_width - 4, 23),
                    "Будувати",
                    ("place_building", definition.key),
                    active=True,
                )
        if page_count > 1:
            panel.button(
                surface,
                (area.x, area.bottom - 25, 40, 25),
                "‹",
                ("building_page", -1),
                enabled=self.page > 0,
            )
            panel.label(
                surface,
                f"{self.page + 1} / {page_count}",
                (area.centerx - 17, area.bottom - 23),
                "small",
                MUTED,
            )
            panel.button(
                surface,
                (area.right - 40, area.bottom - 25, 40, 25),
                "›",
                ("building_page", 1),
                enabled=self.page + 1 < page_count,
            )
