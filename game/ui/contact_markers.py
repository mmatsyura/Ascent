from functools import lru_cache

import pygame

from game.settings import WORLD_HEIGHT, WORLD_WIDTH
from game.ui.theme import ui_font
from game.world.cities import marker_scale
from game.world.faction_visuals import FACTION_COLORS


class ContactMarkers:
    def __init__(self, reconnaissance):
        self.reconnaissance = reconnaissance
        self.font = ui_font(15, True)
        self.detail_font = ui_font(14)

    @lru_cache(maxsize=48)
    def marker(self, size, is_tank, owner):
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        radius = max(8, center - 2)
        color = FACTION_COLORS.get(owner, (174, 137, 107))
        outline = tuple(round(channel * 0.65 + 50) for channel in color)
        pygame.draw.circle(image, (24, 29, 28, 225), (center, center), radius)
        for start in range(0, 360, 60):
            pygame.draw.arc(
                image,
                (*outline, 230),
                (2, 2, size - 4, size - 4),
                start * 0.0174533,
                (start + 38) * 0.0174533,
                2,
            )
        label = self.font.render("?", True, (225, 191, 143))
        image.blit(label, label.get_rect(center=(center, center - 1)))
        if is_tank:
            pygame.draw.line(
                image, (155, 146, 113), (center - 5, size - 6), (center + 5, size - 6), 2
            )
        return image

    def draw(self, screen, camera, pointer=None):
        scale = marker_scale(screen.get_size(), camera.zoom, camera.minimum_zoom)
        size = max(24, min(48, round(max(22, 29 * scale))))
        for contact, age in self.reconnaissance.old_contacts():
            center = camera.world_to_screen(contact.position)
            rectangle = pygame.Rect(0, 0, size, size)
            rectangle.center = (round(center.x), round(center.y))
            if not screen.get_rect().colliderect(rectangle):
                continue
            image = self.marker(size, contact.is_tank, contact.owner).copy()
            opacity = round(205 * max(0, 1 - age / self.reconnaissance.contact_lifetime) ** 0.65)
            image.set_alpha(opacity)
            screen.blit(image, rectangle)
            if pointer is not None and rectangle.collidepoint(pointer):
                caption = self.detail_font.render(
                    f"Останній контакт · {int(age)} с тому", True, (204, 190, 156)
                )
                area = caption.get_rect(midtop=(rectangle.centerx, rectangle.bottom + 6))
                area.clamp_ip(screen.get_rect().inflate(-12, -12))
                pygame.draw.rect(screen, (15, 24, 27), area.inflate(14, 8), border_radius=3)
                screen.blit(caption, area)

    def draw_minimap(self, screen, area):
        for unit in self.reconnaissance.visible_enemies:
            position = (
                round(area.x + unit.position[0] / WORLD_WIDTH * area.w),
                round(area.y + unit.position[1] / WORLD_HEIGHT * area.h),
            )
            reveals = getattr(self.reconnaissance, "reveals", None)
            opacity = reveals.unit_opacity(unit) if reveals is not None else 255
            if opacity <= 0:
                continue
            if opacity == 255:
                pygame.draw.circle(screen, (12, 22, 24), position, 3)
                pygame.draw.circle(
                    screen, FACTION_COLORS.get(unit.owner, (192, 76, 59)), position, 2
                )
            else:
                marker = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(marker, (12, 22, 24), (4, 4), 3)
                pygame.draw.circle(marker, FACTION_COLORS.get(unit.owner, (192, 76, 59)), (4, 4), 2)
                marker.set_alpha(opacity)
                screen.blit(marker, (position[0] - 4, position[1] - 4))
        for contact, age in self.reconnaissance.old_contacts():
            if age > self.reconnaissance.contact_lifetime * 0.9:
                continue
            position = (
                round(area.x + contact.position[0] / WORLD_WIDTH * area.w),
                round(area.y + contact.position[1] / WORLD_HEIGHT * area.h),
            )
            pygame.draw.circle(screen, (158, 128, 91), position, 2, 1)
