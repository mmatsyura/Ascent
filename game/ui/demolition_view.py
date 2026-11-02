from functools import lru_cache
import math

import pygame

from game.ui.theme import ACCENT, MUTED, TEXT, draw_button, panel_surface, ui_font
from game.world.building_art import building_asset


@lru_cache(maxsize=3)
def building_portrait(key):
    source = building_asset(key)
    ratio = min(77 / source.get_width(), 77 / source.get_height())
    return pygame.transform.smoothscale(
        source, (round(source.get_width() * ratio), round(source.get_height() * ratio))
    )


@lru_cache(maxsize=1)
def gold_emblem():
    image = pygame.Surface((58, 58), pygame.SRCALPHA)
    for x, y, radius in ((20, 34, 13), (36, 28, 13), (27, 20, 15)):
        pygame.draw.circle(image, (30, 25, 14, 150), (x + 1, y + 3), radius + 2)
        pygame.draw.circle(image, (123, 86, 34), (x, y + 2), radius)
        pygame.draw.circle(image, (222, 177, 84), (x, y), radius)
        pygame.draw.circle(image, (255, 221, 139), (x, y), radius, 1)
        pygame.draw.circle(image, (171, 120, 46), (x, y), radius - 4, 1)
        pygame.draw.line(image, (250, 213, 128), (x, y - 5), (x, y + 5), 2)
        pygame.draw.line(image, (250, 213, 128), (x - 3, y - 2), (x + 3, y - 2), 1)
        pygame.draw.line(image, (250, 213, 128), (x - 3, y + 2), (x + 3, y + 2), 1)
    return image


class DemolitionView:
    def __init__(self):
        self.motion = {}

    def draw(self, screen, operations, building):
        area = operations.panel
        area.size = (470, 326)
        area.midtop = (screen.get_width() // 2, 95)
        image = panel_surface(area.size).copy()
        operations.buttons = {}
        pointer = pygame.Vector2(pygame.mouse.get_pos()) - area.topleft
        duration = operations.app.interface_seconds

        def label(text, position, size=14, color=TEXT):
            image.blit(ui_font(size, True).render(text, True, color), position)

        pygame.draw.rect(image, (13, 22, 22), (21, 21, 86, 83), border_radius=5)
        pygame.draw.rect(image, (109, 100, 69), (21, 21, 86, 83), 1, border_radius=5)
        portrait = building_portrait(building.definition.key)
        image.blit(portrait, portrait.get_rect(center=(64, 62)))
        label("КЕРУВАННЯ СПОРУДОЮ", (124, 23), 12, MUTED)
        label(building.definition.name, (124, 46), 22)
        label("Демонтаж і повернення коштів", (124, 77), 13, MUTED)
        pygame.draw.line(image, (107, 94, 63), (24, 113), (area.w - 25, 113))
        pygame.draw.rect(image, (22, 33, 29), (24, 127, area.w - 48, 83), border_radius=5)
        pygame.draw.rect(image, (116, 101, 62), (24, 127, area.w - 48, 83), 1, border_radius=5)
        image.blit(gold_emblem(), (35, 140))
        label("ВИ ОТРИМАЄТЕ", (103, 139), 12, MUTED)
        label(f"+{building.definition.gold_cost//3}", (102, 157), 30, ACCENT)
        label("золота", (205, 174), 14, ACCENT)
        value = ui_font(13, True).render(f"Вартість: {building.definition.gold_cost}", True, MUTED)
        rule = ui_font(13, True).render("Повернення: 1/3 ціни", True, MUTED)
        image.blit(value, value.get_rect(right=area.w - 39, top=148))
        image.blit(rule, rule.get_rect(right=area.w - 39, top=174))

        def button(action, text, rectangle, destructive=False):
            rectangle = pygame.Rect(rectangle)
            hovered = rectangle.collidepoint(pointer)
            state = self.motion.setdefault(action, [0.0, 0.0])
            blend = -math.expm1(-max(0, duration) / 0.09)
            state[0] += (float(hovered) - state[0]) * blend
            state[1] += (float(hovered and pygame.mouse.get_pressed()[0]) - state[1]) * blend
            draw_button(image, rectangle, *state)
            if destructive:
                pygame.draw.line(image, (174, 116, 76), rectangle.topleft, rectangle.topright, 2)
            text_image = ui_font(14, True).render(
                text, True, (244, 205, 163) if destructive else TEXT
            )
            image.blit(text_image, text_image.get_rect(center=rectangle.center))
            operations.buttons[action] = rectangle.move(area.topleft)

        button("close", "Залишити", (24, 225, 185, 39))
        button("demolish", "Знести будівлю", (220, 225, 226, 39), True)
        pygame.draw.line(image, (80, 81, 61), (24, 277), (446, 277))
        label("Споруда зникне. Частину золота буде повернено.", (26, 287), 12, MUTED)
        close = pygame.Rect(area.w - 37, 16, 23, 24)
        draw_button(image, close, float(close.collidepoint(pointer)), False)
        mark = ui_font(17, True).render("×", True, MUTED)
        image.blit(mark, mark.get_rect(center=close.center))
        operations.buttons["dismiss"] = close.move(area.topleft)
        screen.blit(image, area)
