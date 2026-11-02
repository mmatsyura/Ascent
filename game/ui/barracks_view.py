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
        panel.button(
            surface,
            (area.x, area.y, half, 29),
            "Підготовка",
            ("barracks_tab", False),
            active=not self.roster,
        )
        panel.button(
            surface,
            (area.x + half + 8, area.y, half, 29),
            f"Підрозділи · {len(state.units)}",
            ("barracks_tab", True),
            active=self.roster,
        )
        panel.label(
            surface,
            f"Місця: {total} / {GARRISON_LIMIT} · У черзі: {len(state.queue)}",
            (area.x + 2, area.y + 39),
            "small",
            MUTED,
        )
        content = pygame.Rect(area.x, area.y + 65, area.w, area.h - 65)
        if self.roster:
            self.draw_roster(surface, content, state)
        else:
            self.draw_training(surface, content, state, total)

    def draw_training(self, surface, area, state, total):
        panel = self.panel
        self.page = max(0, min(1, self.page))
        definitions = RECRUITS[self.page * 2 : self.page * 2 + 2]
        row_height = max(48, min(76, (area.h - 75) // 2))
        for index, definition in enumerate(definitions):
            rectangle = pygame.Rect(area.x, area.y + index * (row_height + 6), area.w, row_height)
            surface.blit(
                panel.pages.construction.project_background(rectangle.size, False, False), rectangle
            )
            icon = panel.icons[
                "army" if definition.key in ("infantry", "anti_tank") else definition.key
            ]
            surface.blit(
                pygame.transform.smoothscale(icon, (32, 32)),
                (rectangle.x + 7, rectangle.centery - 16),
            )
            panel.label(
                surface, definition.name, (rectangle.x + 47, rectangle.y + 5), "button", TEXT
            )
            detail = {
                "infantry": "6 бійців",
                "anti_tank": "Ракетники проти броні",
                "tank": "Бронетехніка",
                "patriot": "ППО · 35% · 7 с",
            }[definition.key]
            panel.label(
                surface,
                f"{int(definition.duration)} с · {detail}",
                (rectangle.x + 47, rectangle.y + 28),
                "small",
                MUTED,
                width=area.w - 190,
            )
            panel.button(
                surface,
                (rectangle.right - 126, rectangle.centery - 15, 120, 30),
                f"Набрати · {definition.price}",
                ("recruit", definition.key),
                enabled=panel.kingdom.gold >= definition.price and total < GARRISON_LIMIT,
            )
        y = area.y + 2 * (row_height + 6)
        if state.queue:
            definition = state.queue[0]
            panel.label(
                surface,
                f"{definition.name} · {max(0,int(definition.duration-state.progress))} с",
                (area.x, y),
                "small",
                ACCENT,
                width=area.w - 110,
            )
            panel.button(surface, (area.right - 100, y, 98, 24), "Скасувати", ("recruit_cancel",))
        panel.button(
            surface,
            (area.x, area.bottom - 25, 35, 24),
            "‹",
            ("barracks_page", -1),
            enabled=self.page > 0,
        )
        panel.label(
            surface, f"{self.page+1} / 2", (area.centerx - 18, area.bottom - 21), "small", MUTED
        )
        panel.button(
            surface,
            (area.right - 35, area.bottom - 25, 35, 24),
            "›",
            ("barracks_page", 1),
            enabled=self.page < 1,
        )

    def draw_roster(self, surface, area, state):
        panel = self.panel
        units = state.units
        per_page = max(1, (area.h - 48) // 54)
        pages = max(1, (len(units) + per_page - 1) // per_page)
        self.page = max(0, min(self.page, pages - 1))
        for row, unit in enumerate(units[self.page * per_page : (self.page + 1) * per_page]):
            index = panel.unit_control.units.index(unit)
            rectangle = pygame.Rect(area.x, area.y + row * 54, area.w, 48)
            nearby = panel.recruitment.can_disband(panel.barracks, unit)
            panel.pages.card(
                surface,
                rectangle,
                unit.icon_key,
                unit.name,
                "Біля казарм · можна розпустити" if nearby else "Поза радіусом казарм",
                ("unit", index),
                unit.selected,
                right_space=140,
            )
            panel.button(
                surface,
                (rectangle.right - 130, rectangle.y + 10, 124, 29),
                "Розпустити",
                ("disband", index),
                enabled=nearby,
            )
        if not units:
            panel.paragraph(
                surface, "Тут з’являться підрозділи, підготовлені саме в цих казармах.", area
            )
        panel.label(
            surface,
            f"Розпуск: весь підрозділ у радіусі {DISBAND_RADIUS} м",
            (area.x + 2, area.bottom - 20),
            "small",
            MUTED,
        )
        if pages > 1:
            panel.button(
                surface,
                (area.x, area.bottom - 51, 38, 25),
                "‹",
                ("barracks_page", -1),
                enabled=self.page > 0,
            )
            panel.label(
                surface,
                f"{self.page + 1} / {pages}",
                (area.centerx - 20, area.bottom - 47),
                "small",
                MUTED,
            )
            panel.button(
                surface,
                (area.right - 38, area.bottom - 51, 38, 25),
                "›",
                ("barracks_page", 1),
                enabled=self.page + 1 < pages,
            )
