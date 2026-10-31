import pygame

from game.ui.theme import ACCENT, MUTED, TEXT
from game.world.recruitment import DISBAND_RADIUS, GARRISON_LIMIT, RECRUITS


class BarracksView:
    def __init__(self, panel):
        self.panel = panel
        self.page = 0
        self.roster = False

    def draw(self, surface, area):
        panel = self.panel
        recruitment = panel.recruitment
        building = panel.barracks
        if recruitment is None or not recruitment.valid_barracks(building):
            return
        state = recruitment.garrison(building)
        total = len(state.units) + len(state.queue)
        half = (area.w - 8) // 2
        panel.button(surface, (area.x, area.y, half, 29), "Підготовка", ("barracks_tab", False), active=not self.roster)
        panel.button(surface, (area.x + half + 8, area.y, half, 29), f"Підрозділи · {len(state.units)}", ("barracks_tab", True), active=self.roster)
        panel.label(surface, f"Місця: {total} / {GARRISON_LIMIT} · У черзі: {len(state.queue)}", (area.x + 2, area.y + 39), "small", MUTED)
        content = pygame.Rect(area.x, area.y + 65, area.w, area.h - 65)
        if self.roster:
            self.draw_roster(surface, content, state)
        else:
            self.draw_training(surface, content, state, total)

    def draw_training(self, surface, area, state, total):
        panel = self.panel
        compact = area.h < 238
        row_height = 80 if compact else min(78, (area.h - 36 - 8 * (len(RECRUITS) - 1)) // len(RECRUITS))
        for index, definition in enumerate(RECRUITS):
            width = (area.w - 8 * (len(RECRUITS) - 1)) // len(RECRUITS) if compact else area.w
            rectangle = pygame.Rect(area.x + index * (width + 8) if compact else area.x,
                                    area.y if compact else area.y + index * (row_height + 8), width, row_height)
            surface.blit(panel.pages.construction.project_background(rectangle.size, False, False), rectangle)
            icon = panel.icons["army" if definition.key == "infantry" else definition.key]
            if compact:
                surface.blit(pygame.transform.smoothscale(icon, (30, 30)), (rectangle.x + 7, rectangle.y + 10))
                panel.label(surface, definition.name, (rectangle.x + 44, rectangle.y + 7), "button", TEXT)
                panel.label(surface, f"{int(definition.duration)} с", (rectangle.x + 44, rectangle.y + 29), "small", MUTED)
                panel.button(surface, (rectangle.x + 7, rectangle.bottom - 29, rectangle.w - 14, 24), f"Набрати · {definition.price}", ("recruit", definition.key), enabled=panel.kingdom.gold >= definition.price and total < GARRISON_LIMIT)
                continue
            surface.blit(icon, (rectangle.x + 8, rectangle.centery - 20))
            panel.label(surface, definition.name, (rectangle.x + 57, rectangle.y + 8), "title", TEXT)
            detail = {"infantry": "Загін із 6 бійців", "tank": "1 танк", "patriot": "ППО · 35% · постріл / 4 с"}[definition.key]
            description = f"{int(definition.duration)} с · {detail}"
            panel.label(surface, description, (rectangle.x + 57, rectangle.y + 33), "small", MUTED, width=area.w - 211)
            panel.button(surface, (rectangle.right - 137, rectangle.centery - 17, 126, 34), f"Набрати · {definition.price}", ("recruit", definition.key), enabled=panel.kingdom.gold >= definition.price and total < GARRISON_LIMIT)
        vertical = area.y + (row_height + 8 if compact else len(RECRUITS) * (row_height + 8))
        if state.queue:
            definition = state.queue[0]
            seconds = max(0, int(definition.duration - state.progress + .999))
            status = f"{definition.name} · {seconds} с" if seconds else "Звільніть вихід із казарм"
            panel.label(surface, status, (area.x + 2, vertical), "small", ACCENT, width=area.w - 110)
            bar = pygame.Rect(area.x + 2, vertical + 22, area.w - 110, 4)
            pygame.draw.rect(surface, (17, 27, 29), bar, border_radius=2)
            ratio = state.progress / definition.duration
            pygame.draw.rect(surface, (130, 170, 152), (bar.x, bar.y, round(bar.w * ratio), bar.h), border_radius=2)
            panel.button(surface, (area.right - 97, vertical, 96, 28), "Скасувати", ("recruit_cancel",))
        else:
            panel.label(surface, "Казарми готові до підготовки.", (area.x + 2, vertical + 5), "small", MUTED)

    def draw_roster(self, surface, area, state):
        panel = self.panel
        units = state.units
        per_page = max(1, (area.h - 48) // 54)
        pages = max(1, (len(units) + per_page - 1) // per_page)
        self.page = max(0, min(self.page, pages - 1))
        for row, unit in enumerate(units[self.page * per_page:(self.page + 1) * per_page]):
            index = panel.unit_control.units.index(unit)
            rectangle = pygame.Rect(area.x, area.y + row * 54, area.w, 48)
            nearby = panel.recruitment.can_disband(panel.barracks, unit)
            panel.pages.card(surface, rectangle, unit.icon_key, unit.name, "Біля казарм · можна розпустити" if nearby else "Поза радіусом казарм", ("unit", index), unit.selected, right_space=140)
            panel.button(surface, (rectangle.right - 130, rectangle.y + 10, 124, 29), "Розпустити", ("disband", index), enabled=nearby)
        if not units:
            panel.paragraph(surface, "Тут з’являться підрозділи, підготовлені саме в цих казармах.", area)
        panel.label(surface, f"Розпуск: весь підрозділ у радіусі {DISBAND_RADIUS} м", (area.x + 2, area.bottom - 20), "small", MUTED)
        if pages > 1:
            panel.button(surface, (area.x, area.bottom - 51, 38, 25), "‹", ("barracks_page", -1), enabled=self.page > 0)
            panel.label(surface, f"{self.page + 1} / {pages}", (area.centerx - 20, area.bottom - 47), "small", MUTED)
            panel.button(surface, (area.right - 38, area.bottom - 51, 38, 25), "›", ("barracks_page", 1), enabled=self.page + 1 < pages)
