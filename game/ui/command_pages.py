import pygame

from game.ui.airport_view import AirportView
from game.ui.barracks_view import BarracksView
from game.ui.construction_site_view import ConstructionSiteView
from game.ui.construction_view import ConstructionView
from game.ui.information_view import InformationView
from game.ui.theme import ACCENT, MUTED, TEXT
from game.world.buildings import BUILDINGS


class CommandPages:
    def __init__(self, panel):
        self.panel = panel
        self.selected_building = 0
        self.construction = ConstructionView(panel)
        self.army_page = 0
        self.airport = AirportView(panel)
        self.information = InformationView(panel)
        self.barracks = BarracksView(panel)
        self.site = ConstructionSiteView(panel)

    def card(self, surface, area, icon, title, subtitle, action=None, active=False, right_space=8):
        panel = self.panel
        panel.button(surface, area, "", action, active)
        surface.blit(panel.icons[icon], (area.x + 8, area.centery - 20))
        panel.label(
            surface,
            title,
            (area.x + 55, area.y + 3),
            "button",
            ACCENT if active else TEXT,
            width=area.w - 55 - right_space,
        )
        panel.label(
            surface,
            subtitle,
            (area.x + 55, area.y + 25),
            "small",
            MUTED,
            width=area.w - 55 - right_space,
        )

    def draw(self, surface, area, section):
        getattr(self, f"draw_{section}")(surface, area)

    def draw_build(self, surface, area):
        self.construction.draw(surface, area, self.selected_building)

    def draw_army(self, surface, area):
        panel = self.panel
        units = panel.unit_control.owned_units
        per_page = max(1, (area.h - 38) // 51)
        page_count = max(1, (len(units) + per_page - 1) // per_page)
        self.army_page = max(0, min(self.army_page, page_count - 1))
        if page_count > 1:
            per_page = max(1, (area.h - 70) // 51)
            page_count = (len(units) + per_page - 1) // per_page
            self.army_page = min(self.army_page, page_count - 1)
        first = self.army_page * per_page
        for row, unit in enumerate(units[first : first + per_page]):
            index = panel.unit_control.units.index(unit)
            rectangle = pygame.Rect(area.x, area.y + row * 51, area.w, 46)
            status = (
                "Планування маршруту"
                if unit.planning_target is not None
                else ("У русі" if unit.route else "На позиції")
            )
            self.card(
                surface,
                rectangle,
                unit.icon_key,
                unit.name,
                f"{unit.detail_label} · {status}",
                ("unit", index),
                unit.selected,
                right_space=45,
            )
            button = pygame.Rect(rectangle.right - 35, rectangle.y + 10, 26, 26)
            panel.button(surface, button, "", ("rename", index))
            horizontal, vertical = button.center
            pygame.draw.line(
                surface, ACCENT, (horizontal - 5, vertical + 5), (horizontal + 5, vertical - 5), 3
            )
            pygame.draw.line(
                surface,
                (80, 147, 187),
                (horizontal + 3, vertical - 7),
                (horizontal + 7, vertical - 3),
                3,
            )
        if page_count > 1:
            panel.button(
                surface,
                (area.x, area.bottom - 62, 40, 25),
                "‹",
                ("army_page", -1),
                enabled=self.army_page > 0,
            )
            panel.label(
                surface,
                f"{self.army_page + 1} / {page_count}",
                (area.centerx - 17, area.bottom - 59),
                "small",
                MUTED,
            )
            panel.button(
                surface,
                (area.right - 40, area.bottom - 62, 40, 25),
                "›",
                ("army_page", 1),
                enabled=self.army_page + 1 < page_count,
            )
        width = (area.w - 8) // 2
        panel.button(surface, (area.x, area.bottom - 30, width, 30), "Обрати всі", ("select_all",))
        panel.button(
            surface,
            (area.x + width + 8, area.bottom - 30, width, 30),
            "Зупинити",
            ("stop",),
            enabled=bool(panel.unit_control.selected),
        )

    def draw_information(self, surface, area):
        self.information.draw(surface, area)

    def draw_airport(self, surface, area):
        self.airport.draw(surface, area)

    def draw_barracks(self, surface, area):
        self.barracks.draw(surface, area)

    def draw_site(self, surface, area):
        self.site.draw(surface, area)

    def activate(self, command, arguments):
        panel = self.panel
        if command == "building":
            self.selected_building = arguments[0]
        elif command == "building_page":
            self.construction.page += arguments[0]
        elif command == "army_page":
            self.army_page += arguments[0]
        elif command == "airport_page":
            self.airport.page += arguments[0]
        elif command == "barracks_page":
            self.barracks.page += arguments[0]
        elif command == "barracks_tab":
            self.barracks.roster = arguments[0]
            self.barracks.page = 0
        elif command == "information_page":
            self.information.page += arguments[0]
        elif command == "report_focus":
            reports = list(panel.intelligence.reports)
            if 0 <= arguments[0] < len(reports):
                panel.focus(reports[arguments[0]].position)
        elif command == "unit":
            if panel.drone_control is not None:
                panel.drone_control.cancel(deselect=True)
            target = panel.unit_control.units[arguments[0]]
            for unit in panel.unit_control.units:
                unit.selected = unit is target
            panel.unit_control.acknowledge((target,))
            panel.focus(target.position)
        elif command == "select_all":
            if panel.drone_control is not None:
                panel.drone_control.cancel(deselect=True)
            for unit in panel.unit_control.units:
                unit.selected = unit.owner == "blue" and unit.movable
            panel.unit_control.acknowledge(panel.unit_control.selected)
        elif command == "stop":
            panel.unit_control.stop()
