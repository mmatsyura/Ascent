import math

import pygame

from game.ui.theme import ACCENT, MUTED, TEXT


class ConstructionSiteView:
    def __init__(self, panel):
        self.panel = panel

    def draw(self, surface, area):
        panel = self.panel
        building = panel.construction_site
        if building is None or building.completed:
            return
        compact = area.h < 210
        icon_size = 54 if compact else 88
        icon = pygame.transform.smoothscale(
            panel.building_icons[building.definition.key], (icon_size, icon_size)
        )
        surface.blit(icon, (area.x, area.y))
        left = area.x + icon_size + 14
        remaining = math.ceil(building.construction_remaining)
        panel.label(
            surface,
            f"Залишилося {remaining // 60:02d}:{remaining % 60:02d}",
            (left, area.y + 5),
            "title",
            ACCENT,
            width=area.right - left,
        )
        panel.label(
            surface,
            "Будівельна бригада працює",
            (left, area.y + 34),
            "small",
            MUTED,
            width=area.right - left,
        )
        top = area.y + icon_size + 14
        bar = pygame.Rect(area.x + 2, top, area.w - 4, 7)
        pygame.draw.rect(surface, (26, 38, 34), bar, border_radius=3)
        pygame.draw.rect(
            surface,
            (149, 181, 145),
            (bar.x, bar.y, round(bar.w * building.construction_progress), bar.h),
            border_radius=3,
        )
        panel.label(
            surface,
            f"Готовність: {round(building.construction_progress * 100)}%",
            (area.x + 2, top + 15),
            "small",
            TEXT,
        )
        panel.label(
            surface,
            f"Повернення: {building.definition.gold_cost} золота",
            (area.x + 2, area.bottom - 69),
            "small",
            MUTED,
        )
        panel.button(
            surface,
            (area.x, area.bottom - 38, area.w, 34),
            "Скасувати будівництво",
            ("cancel_construction",),
        )
