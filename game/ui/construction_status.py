from functools import lru_cache
import math

import pygame

from game.ui.theme import ACCENT, BORDER, ui_font
from game.world.building_rendering import building_parts


@lru_cache(maxsize=128)
def timer_label(name, remaining):
    text = f"{name} · {remaining // 60:02d}:{remaining % 60:02d}"
    return ui_font(14, True).render(text, True, ACCENT)


@lru_cache(maxsize=96)
def site_top(image):
    return image.get_bounding_rect(min_alpha=40).top


class ConstructionStatus:
    def __init__(self, buildings):
        self.buildings = buildings
        self.opacities = {}

    def update(self, duration):
        active = {
            building
            for building in self.buildings.buildings
            if building.owner == "blue" and not building.completed
        }
        for building in active:
            self.opacities.setdefault(building, 0)
        blend = -math.expm1(-max(0, duration) / 0.16)
        for building, opacity in tuple(self.opacities.items()):
            target = 1 if building in active else 0
            opacity += (target - opacity) * blend
            if opacity < 0.005 and target == 0:
                del self.opacities[building]
            else:
                self.opacities[building] = opacity

    def draw(self, screen, camera):
        visible = camera.visible_area.inflate(400, 400)
        for building, opacity in self.opacities.items():
            if not visible.collidepoint(building.position):
                continue
            part = building_parts(building, camera, workers=False)[0]
            center = camera.world_to_screen(building.position)
            point = pygame.Vector2(center.x, part.rectangle.top + site_top(part.image) - 8)
            label = timer_label(
                building.definition.name, math.ceil(building.construction_remaining)
            )
            image = pygame.Surface((label.get_width() + 20, 32), pygame.SRCALPHA)
            pygame.draw.rect(image, (14, 24, 26, 235), image.get_rect(), border_radius=4)
            pygame.draw.rect(image, (*BORDER, 220), image.get_rect(), 1, border_radius=4)
            image.blit(label, (10, 4))
            bar = pygame.Rect(9, 25, image.get_width() - 18, 3)
            pygame.draw.rect(image, (43, 56, 52), bar)
            pygame.draw.rect(
                image,
                (149, 181, 145),
                (bar.x, bar.y, round(bar.w * building.construction_progress), bar.h),
            )
            image.set_alpha(round(opacity * 255))
            screen.blit(image, image.get_rect(midbottom=(round(point.x), round(point.y))))
