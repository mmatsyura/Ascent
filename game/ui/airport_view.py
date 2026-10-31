from functools import lru_cache

import pygame

from game.aircraft.art import drone_icon
from game.aircraft.definitions import DRONES
from game.ui.theme import ACCENT, MUTED, TEXT


class AirportView:
    def __init__(self, panel):
        self.panel = panel
        self.page = 0
        self.icons = {definition.key: drone_icon(definition.key, 82) for definition in DRONES}

    @lru_cache(maxsize=32)
    def icon(self, key, size):
        return pygame.transform.smoothscale(self.icons[key], (size, size))

    def draw(self, surface, area):
        panel = self.panel
        airport = panel.airport
        fleet = panel.fleet
        if fleet is None or not fleet.valid_airport(airport):
            panel.label(surface, "Аеропорт недоступний.", area.topleft, color=MUTED)
            return
        content = area.copy()
        per_page = max(1, min(2, (content.h - 22) // 96))
        pages = (len(DRONES) + per_page - 1) // per_page
        if pages > 1:
            content.h -= 32
        self.page = max(0, min(self.page, pages - 1))
        first = self.page * per_page
        rows = DRONES[first:first + per_page]
        height = (content.h - (len(rows) - 1) * 10) // len(rows)
        airborne_counts = {}
        for drone in fleet.drones:
            if drone.airport is airport and drone.controllable:
                airborne_counts[drone.definition.key] = airborne_counts.get(drone.definition.key, 0) + 1
        for row, definition in enumerate(rows):
            rectangle = pygame.Rect(content.x, content.y + row * (height + 10), content.w, height)
            ready = fleet.stock[airport][definition.key]
            airborne = airborne_counts.get(definition.key, 0)
            queued, remaining, progress = fleet.production.status(airport, definition.key)
            if airborne:
                panel.register(("drone_focus", definition.key), rectangle)
            hovered = rectangle.move(panel.origin).collidepoint(panel.pointer)
            surface.blit(panel.pages.construction.project_background(rectangle.size, bool(ready), hovered), rectangle)
            icon_size = min(82, height - 10)
            icon = self.icon(definition.key, icon_size)
            surface.blit(icon, (rectangle.x + 5, rectangle.centery - icon_size // 2))
            text_left = rectangle.x + min(104, height - 4) + 10
            price_left = rectangle.right - 125
            text_width = price_left - text_left - 10
            top = rectangle.centery - 32
            panel.label(surface, definition.name, (text_left, top), "title", TEXT, width=text_width)
            minutes = round(definition.flight_lifetime / 60)
            role = "Ударний" if definition.strike else "Розвідник"
            panel.label(surface, f"{role} · {minutes} хв · збірка {int(definition.production_duration)} с", (text_left, top + 26), "small", MUTED, width=text_width)
            if remaining is not None:
                count_label = f"готових: {ready}" if ready else f"у черзі: {queued}"
                status = f"Збірка {remaining // 60:02d}:{remaining % 60:02d} · {count_label}"
            elif queued:
                status = f"Очікує збірки: {queued}"
            else:
                status = f"Готово до вильоту: {ready}" if ready else (f"У повітрі: {airborne} · обрати" if airborne else definition.description)
            panel.label(surface, status, (text_left, top + 49), "small", definition.accent, width=text_width)
            if definition.strike and height >= 125:
                panel.label(surface, "Піхота / ППО 80% · танки / споруди 20%", (text_left, top + 71), "small", MUTED, width=rectangle.right - text_left - 10)
            if remaining is not None:
                bar = pygame.Rect(rectangle.x + 10, rectangle.bottom - 5, rectangle.w - 20, 2)
                pygame.draw.rect(surface, (36, 48, 43), bar)
                pygame.draw.rect(surface, definition.accent, (bar.x, bar.y, round(bar.w * progress), bar.h))
            surface.blit(panel.pages.construction.icon("gold", 20), (price_left, top + 1))
            panel.label(surface, f"{definition.price:,}".replace(",", " "), (price_left + 25, top), "title", ACCENT, width=98)
            can_buy = panel.kingdom.gold >= definition.price
            if ready:
                panel.button(surface, (price_left, top + 32, 88, 28), "Виліт", ("drone_launch", definition.key), active=True)
                panel.button(surface, (price_left + 94, top + 32, 25, 28), "+", ("drone_buy", definition.key), enabled=can_buy)
            else:
                panel.button(surface, (price_left, top + 32, 88 if queued else 119, 28), "Замовити", ("drone_buy", definition.key), enabled=can_buy)
                if queued:
                    panel.button(surface, (price_left + 94, top + 32, 25, 28), "×", ("drone_cancel", definition.key))
        if pages > 1:
            panel.button(surface, (area.x, area.bottom - 25, 40, 25), "‹", ("airport_page", -1), enabled=self.page > 0)
            panel.label(surface, f"{self.page + 1} / {pages}", (area.centerx - 17, area.bottom - 23), "small", MUTED)
            panel.button(surface, (area.right - 40, area.bottom - 25, 40, 25), "›", ("airport_page", 1), enabled=self.page + 1 < pages)
