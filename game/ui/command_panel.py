from functools import lru_cache

import pygame

from game.ui.command_icons import create_command_icons
from game.ui.building_icons import create_building_icons
from game.ui.command_pages import CommandPages
from game.ui.fonts import fit_text, ui_font
from game.ui.theme import ACCENT, BORDER, MUTED, TEXT, panel_surface
from game.world.tank_art import tank_badge
from game.ui.transitions import SmoothLayer
from game.world.patriot_art import patriot_badge


SECTIONS = (("build", "Будівництво"), ("army", "Армія"), ("information", "Інформація"))


@lru_cache(maxsize=512)
def text_image(font, text, color):
    return font.render(str(text), True, color)


class CommandPanel:
    def __init__(self, kingdom, city_map, unit_control, camera, visibility, intelligence):
        self.kingdom = kingdom
        self.city_map = city_map
        self.unit_control = unit_control
        self.camera = camera
        self.visibility = visibility
        self.intelligence = intelligence
        self.rename_callback = None
        self.build_callback = None
        self.fleet = None
        self.airport = None
        self.drone_control = None
        self.recruitment = None
        self.barracks = None
        self.construction_site = None
        self.cancel_construction = None
        self.on_action = None
        self.dock_motion = SmoothLayer(.14)
        self.inspector_motion = SmoothLayer(.2)
        self.tooltip_motion = SmoothLayer(.14)
        self.tooltip_key = None
        self.tooltip_image = None
        self.icons = create_command_icons()
        self.icons["tank"] = tank_badge(40)
        self.icons["patriot"] = patriot_badge(40)
        self.building_icons = create_building_icons()
        self.icons["airport"] = pygame.transform.smoothscale(self.building_icons["airport"], (40, 40))
        self.icons["barracks"] = pygame.transform.smoothscale(self.building_icons["barracks"], (40, 40))
        self.icons["site"] = self.icons["build"]
        self.fonts = {
            "small": ui_font(14),
            "body": ui_font(15),
            "button": ui_font(15, True),
            "title": ui_font(18, True),
            "value": ui_font(25, True),
        }
        self.active_section = None
        self.collapsed = False
        self.paused = False
        self.pointer = pygame.Vector2(-1, -1)
        self.pressed_action = None
        self.pointer_button = None
        self.action_areas = {}
        self.surface_key = None
        self.origin = pygame.Vector2()
        self.panel_area = pygame.Rect(0, 0, 620, 188)
        self.inspector_area = pygame.Rect(0, 0, 620, 340)
        self.pages = CommandPages(self)
        self.layout(camera.viewport_size)

    @property
    def owned_cities(self):
        return sorted((city for city in self.city_map.cities if city.owner == "blue"), key=lambda city: not city.capital)

    @property
    def top(self):
        return self.inspector_area.top if self.active_section else self.panel_area.top

    def layout(self, screen_size):
        width = min(620, screen_size[0] - 300)
        height = 66 if self.collapsed else 188
        self.panel_area = pygame.Rect(10, screen_size[1] - height - 8, width, height)
        self.layout_inspector()
        self.action_areas.clear()
        self.surface_key = None
        self.render_surfaces()

    def layout_inspector(self):
        preferred_height = 470 if self.active_section == "barracks" else (440 if self.active_section in ("build", "airport", "information") else (400 if self.active_section == "army" else 340))
        height = min(preferred_height, max(250, self.panel_area.top - 110))
        self.inspector_area = pygame.Rect(self.panel_area.left, self.panel_area.top - height - 8, self.panel_area.w, height)

    def contains(self, position):
        return (self.panel_area.collidepoint(position) or bool(self.active_section and self.inspector_area.collidepoint(position))
                or self.dock_motion.contains(position) or self.inspector_motion.contains(position))

    def label(self, surface, text, position, style="body", color=TEXT, width=None):
        if width is not None:
            text = fit_text(self.fonts[style], str(text), width)
        image = text_image(self.fonts[style], str(text), color)
        surface.blit(image, position)
        return image.get_rect(topleft=position)

    def paragraph(self, surface, text, area, color=MUTED):
        words = text.split()
        line = ""
        vertical = area.top
        line_height = max(19, self.fonts["body"].get_linesize())
        for word in words:
            candidate = f"{line} {word}".strip()
            if line and self.fonts["body"].size(candidate)[0] > area.w:
                if vertical + self.fonts["body"].get_height() > area.bottom:
                    return vertical
                self.label(surface, line, (area.x, vertical), color=color)
                vertical += line_height
                line = word
            else:
                line = candidate
        if line and vertical + self.fonts["body"].get_height() <= area.bottom:
            self.label(surface, line, (area.x, vertical), color=color)
        return vertical + line_height

    def register(self, action, rectangle):
        self.action_areas[action] = pygame.Rect(rectangle).move(round(self.origin.x), round(self.origin.y))

    def button(self, surface, rectangle, text, action=None, active=False, enabled=True, icon=None):
        rectangle = pygame.Rect(rectangle)
        global_area = rectangle.move(round(self.origin.x), round(self.origin.y))
        hovered = enabled and global_area.collidepoint(self.pointer)
        pressed = action is not None and action == self.pressed_action
        color = (43, 65, 76) if active else ((48, 58, 47) if hovered else (28, 37, 33))
        if pressed:
            color = (21, 33, 33)
        pygame.draw.rect(surface, (6, 12, 12), rectangle.move(0, 2), border_radius=3)
        pygame.draw.rect(surface, color, rectangle, border_radius=3)
        pygame.draw.rect(surface, ACCENT if active or hovered else BORDER, rectangle, 1, border_radius=3)
        pygame.draw.line(surface, (121, 124, 91) if enabled else (62, 70, 58), (rectangle.x + 3, rectangle.y + 2), (rectangle.right - 4, rectangle.y + 2))
        if icon:
            surface.blit(pygame.transform.smoothscale(self.icons[icon], (24, 24)), (rectangle.x + 9, rectangle.centery - 12))
        text = fit_text(self.fonts["button"], text, rectangle.w - (48 if icon else 12))
        label = text_image(self.fonts["button"], text, TEXT if enabled else (151, 162, 146))
        target = label.get_rect(center=rectangle.center)
        if icon:
            target.x += 12
        surface.blit(label, target)
        if action is not None and enabled:
            self.register(action, rectangle)

    def rule(self, surface, left, right, vertical):
        pygame.draw.line(surface, (87, 82, 58), (left, vertical), (right, vertical))
        middle = (left + right) // 2
        pygame.draw.polygon(surface, (165, 144, 92), [(middle - 3, vertical), (middle, vertical - 2), (middle + 3, vertical), (middle, vertical + 2)])

    def crest(self, surface):
        points = [(22, 17), (39, 13), (56, 17), (54, 40), (39, 53), (24, 40)]
        pygame.draw.polygon(surface, (178, 154, 97), points)
        pygame.draw.polygon(surface, (31, 73, 119), [(25, 20), (39, 17), (53, 20), (51, 38), (39, 48), (27, 38)])
        pygame.draw.polygon(surface, (62, 117, 173), [(26, 20), (39, 17), (39, 47), (28, 37)])
        pygame.draw.line(surface, (225, 209, 155), (31, 32), (47, 32), 2)
        pygame.draw.line(surface, (225, 209, 155), (39, 24), (39, 40), 2)
        pygame.draw.polygon(surface, (225, 209, 155), [(39, 23), (43, 32), (39, 41), (35, 32)])

    @lru_cache(maxsize=64)
    def section_tile(self, section, title, shortcut, size, hovered, active, pressed):
        image = pygame.Surface(size, pygame.SRCALPHA)
        width, height = size
        top = (43, 66, 81) if active else ((55, 64, 51) if hovered else (38, 46, 39))
        bottom = (23, 36, 43) if active else (22, 29, 26)
        if pressed:
            top = bottom
        for vertical in range(height):
            progress = vertical / max(1, height - 1)
            color = tuple(round(first + (last - first) * progress) for first, last in zip(top, bottom))
            pygame.draw.line(image, color, (0, vertical), (width - 1, vertical))
        pygame.draw.rect(image, ACCENT if hovered or active else (107, 99, 69), image.get_rect(), 1, border_radius=3)
        pygame.draw.rect(image, (63, 70, 54), (3, 3, width - 6, height - 6), 1, border_radius=2)
        pygame.draw.line(image, (151, 139, 98) if hovered or active else (91, 94, 70), (5, 2), (width - 6, 2))
        pygame.draw.ellipse(image, (8, 17, 20), (width // 2 - 25, 9, 50, 42))
        pygame.draw.ellipse(image, (16, 26, 27), (width // 2 - 23, 7, 46, 42))
        pygame.draw.arc(image, (128, 115, 75), (width // 2 - 23, 7, 46, 42), .2, 2.9, 1)
        image.blit(self.icons[section], (width // 2 - 20, 7))
        label = text_image(self.fonts["button"], title, ACCENT if active else (TEXT if hovered else MUTED))
        image.blit(label, label.get_rect(midbottom=(width // 2, height - 7)))
        self.label(image, shortcut, (width - 19, 4), "small", (172, 159, 112))
        if active:
            pygame.draw.line(image, (216, 187, 122), (7, height - 3), (width - 8, height - 3), 2)
            pygame.draw.polygon(image, ACCENT, [(width // 2 - 3, height - 4), (width // 2, height - 7), (width // 2 + 3, height - 4)])
        return image

    def render_dock(self):
        self.origin.update(self.panel_area.topleft)
        surface = panel_surface(self.panel_area.size).copy()
        width = surface.get_width()
        self.crest(surface)
        selected_units = self.unit_control.selected
        drone = self.drone_control.selected if self.drone_control is not None else None
        title = selected_units[0].name if len(selected_units) == 1 else (f"Обрані загони: {len(selected_units)}" if selected_units else "СИНЄ КОРОЛІВСТВО")
        if drone is not None:
            title = drone.definition.name
        controls = ("rename", "pause", "capital", "collapse") if len(selected_units) == 1 else ("pause", "capital", "collapse")
        control_start = width - 23 - len(controls) * 31
        self.label(surface, title, (68, 15), "title", ACCENT, width=control_start - 78)
        if self.paused:
            subtitle = "ЧАС ЗУПИНЕНО"
        elif drone is not None:
            subtitle = f"БПЛА · Ресурс {drone.timer_label} · Знімків: {drone.photographed}"
        elif len(selected_units) == 1:
            subtitle = f"{selected_units[0].detail_label} · F2 — змінити назву"
        elif selected_units:
            infantry = sum(not unit.is_tank for unit in selected_units) * 6
            tanks = sum(unit.is_tank and not unit.is_patriot for unit in selected_units)
            patriots = sum(unit.is_patriot for unit in selected_units)
            parts = [f"Бійців: {infantry}"]
            if tanks:
                parts.append(f"Танків: {tanks}")
            if patriots:
                parts.append(f"Петріот: {patriots}")
            subtitle = " · ".join(parts)
        else:
            subtitle = f"Міста: {len(self.owned_cities)} · Загони: {len(self.unit_control.owned_units)}"
        self.label(surface, subtitle, (69, 39), "small", (159, 190, 204) if self.paused else MUTED)
        for index, action in enumerate(controls):
            rectangle = pygame.Rect(control_start + index * 31, 20, 27, 28)
            self.button(surface, rectangle, "", (action,), active=action == "pause" and self.paused)
            horizontal, vertical = rectangle.center
            if action == "rename":
                pygame.draw.line(surface, ACCENT, (horizontal - 5, vertical + 5), (horizontal + 5, vertical - 5), 3)
                pygame.draw.line(surface, (80, 147, 187), (horizontal + 3, vertical - 7), (horizontal + 7, vertical - 3), 3)
                pygame.draw.line(surface, ACCENT, (horizontal - 7, vertical + 7), (horizontal - 3, vertical + 6))
            elif action == "pause":
                if self.paused:
                    pygame.draw.polygon(surface, ACCENT, [(horizontal - 3, vertical - 6), (horizontal + 5, vertical), (horizontal - 3, vertical + 6)])
                else:
                    for offset in (-4, 2):
                        pygame.draw.rect(surface, ACCENT, (horizontal + offset, vertical - 5, 3, 10))
            elif action == "capital":
                pygame.draw.circle(surface, ACCENT, (horizontal, vertical), 5, 1)
                for start, end in (((-8, 0), (8, 0)), ((0, -8), (0, 8))):
                    pygame.draw.line(surface, ACCENT, (horizontal + start[0], vertical + start[1]), (horizontal + end[0], vertical + end[1]))
            else:
                pygame.draw.line(surface, ACCENT, (horizontal - 5, vertical), (horizontal + 5, vertical))
                if self.collapsed:
                    pygame.draw.line(surface, ACCENT, (horizontal, vertical - 5), (horizontal, vertical + 5))
        if not self.collapsed:
            self.rule(surface, 23, width - 24, 64)
            gap = 7
            tile_width = (width - 40 - gap * (len(SECTIONS) - 1)) // len(SECTIONS)
            for index, (section, title) in enumerate(SECTIONS):
                rectangle = pygame.Rect(20 + index * (tile_width + gap), 74, tile_width, 70)
                action = ("section", section)
                self.register(action, rectangle)
                hovered = self.action_areas[action].collidepoint(self.pointer)
                image = self.section_tile(section, title, str(index + 1), rectangle.size, hovered, self.active_section == section, self.pressed_action == action)
                surface.blit(image, rectangle)
                if section == "information" and self.intelligence.unread:
                    badge = pygame.Rect(rectangle.right - 31, rectangle.y + 8, 23, 20)
                    pygame.draw.rect(surface, (132, 73, 44), badge, border_radius=4)
                    label = text_image(self.fonts["small"], str(min(99, self.intelligence.unread)), TEXT)
                    surface.blit(label, label.get_rect(center=badge.center))
            selected = len(self.unit_control.selected)
            status = f"Обрано: {selected}" if selected else "ПАНЕЛЬ КЕРУВАННЯ"
            self.label(surface, status, (23, 154), "small", ACCENT if selected else MUTED)
            hint = "ПКМ — наказ · Ctrl — вибір" if selected else "Пробіл — пауза"
            if drone is not None:
                hint = "ЛКМ по ворогу — удар · по землі — маршрут" if drone.definition.strike else "ЛКМ — маршрут · Shift — продовжити"
            image = text_image(self.fonts["small"], hint, MUTED)
            surface.blit(image, (width - image.get_width() - 23, 154))
        return surface

    def render_state(self):
        return (
            tuple(self.panel_area), tuple(self.inspector_area), self.active_section, self.paused,
            self.collapsed, self.pages.selected_building, self.pages.construction.page, self.pages.army_page,
            self.pages.airport.page, self.pages.information.page,
            self.pages.barracks.page, self.pages.barracks.roster,
            (id(self.construction_site), round(self.construction_site.construction_progress * 100), int(self.construction_site.construction_remaining)) if self.construction_site is not None and self.active_section == "site" else None,
            self.recruitment.revision if self.recruitment is not None else None,
            tuple((id(unit), self.recruitment.can_disband(self.barracks, unit)) for unit in self.recruitment.garrison(self.barracks).units) if self.recruitment is not None and self.recruitment.valid_barracks(self.barracks) else (),
            tuple((unit.name, unit.selected, bool(unit.route), unit.planning_target is not None) for unit in self.unit_control.owned_units),
            tuple(city.position for city in self.owned_cities),
            (self.kingdom.gold, self.kingdom.area),
            self.intelligence.revision, self.intelligence.unread,
            self.fleet.revision if self.fleet is not None else None,
            self.fleet.production.state_key(self.airport) if self.fleet is not None and self.active_section == "airport" else None,
            (self.drone_control.selected.identity, int(self.drone_control.selected.remaining), self.drone_control.selected.photographed) if self.drone_control is not None and self.drone_control.selected is not None else None,
            self.action_at(self.pointer), self.pressed_action,
        )

    def render_surfaces(self):
        self.layout_inspector()
        if self.surface_key == self.render_state():
            return
        self.action_areas.clear()
        self.dock_surface = self.render_dock()
        self.inspector_surface = None
        if self.active_section:
            self.origin.update(self.inspector_area.topleft)
            background = self.pages.construction.background(self.inspector_area.size) if self.active_section == "build" else panel_surface(self.inspector_area.size)
            self.inspector_surface = background.copy()
            title = dict(SECTIONS).get(self.active_section, "Казарми" if self.active_section == "barracks" else "Військовий аеропорт")
            if self.active_section == "site":
                title = self.construction_site.definition.name if self.construction_site is not None else "Будівництво"
            self.inspector_surface.blit(self.icons[self.active_section], (20, 14))
            self.label(self.inspector_surface, title, (70, 20), "title", ACCENT)
            subtitles = {"build": "ПРОМИСЛОВІСТЬ ТА ОБОРОНА", "army": "ЗАГОНИ ТА НАКАЗИ", "information": "ПОВІТРЯНА РОЗВІДКА", "airport": "БЕЗПІЛОТНА АВІАЦІЯ · ВИРОБНИЦТВО ТА ВИЛІТ", "barracks": "ПІДГОТОВКА · ПІХОТА ТА БРОНЕТЕХНІКА"}
            self.label(self.inspector_surface, subtitles.get(self.active_section, "БУДІВЕЛЬНИЙ МАЙДАНЧИК"), (71, 43), "small", MUTED, width=self.inspector_area.w - 130)
            self.button(self.inspector_surface, (self.inspector_area.w - 48, 21, 25, 25), "×", ("close",))
            if self.active_section != "build":
                self.rule(self.inspector_surface, 23, self.inspector_area.w - 24, 65)
            self.pages.draw(self.inspector_surface, pygame.Rect(22, 77, self.inspector_area.w - 44, self.inspector_area.h - 111), self.active_section)
        self.surface_key = self.render_state()

    def action_at(self, position):
        return next((action for action, area in reversed(tuple(self.action_areas.items())) if area.collidepoint(position)), None)

    def begin_press(self, position, button):
        self.pointer.update(position)
        self.pointer_button = button
        self.pressed_action = self.action_at(position) if button == 1 else None

    def end_press(self, position, button):
        if button != self.pointer_button:
            return False
        self.pointer.update(position)
        action = self.pressed_action
        self.cancel_press()
        if action is not None and action == self.action_at(position):
            self.activate(action)
        return True

    def cancel_press(self):
        self.pointer_button = None
        self.pressed_action = None

    def focus(self, position):
        center = pygame.Vector2(self.camera.viewport_size) / 2
        destination = center.copy()
        if self.contains(center):
            destination.x = (self.panel_area.right + self.camera.viewport_size[0]) / 2
            destination.y = min(center.y, (100 + self.camera.viewport_size[1] - 266) / 2)
        self.camera.zoom_anchor.update(center)
        self.camera.target_zoom = max(self.camera.target_zoom, .8)
        self.camera.pan_to(pygame.Vector2(position) - (destination - center) / self.camera.target_zoom)

    def activate(self, action):
        if self.on_action is not None:
            self.on_action()
        command, *arguments = action
        if command == "section":
            self.active_section = None if self.active_section == arguments[0] else arguments[0]
            if self.active_section == "information":
                self.intelligence.mark_read()
        elif command == "close":
            self.active_section = None
        elif command == "pause":
            self.paused = not self.paused
        elif command == "capital":
            self.focus(self.city_map.player_capital.position)
        elif command == "collapse":
            self.collapsed = not self.collapsed
            self.active_section = None
            self.layout(self.camera.viewport_size)
        elif command == "rename" and self.rename_callback is not None:
            selected = self.unit_control.selected
            unit = self.unit_control.units[arguments[0]] if arguments else (selected[0] if len(selected) == 1 else None)
            if unit is not None:
                self.rename_callback(unit)
        elif command == "place_building" and self.build_callback is not None:
            self.build_callback(arguments[0])
        elif command == "cancel_construction" and self.cancel_construction is not None:
            self.cancel_construction(self.construction_site)
        elif command == "drone_buy" and self.fleet is not None:
            success, message = self.fleet.purchase(self.airport, arguments[0])
            if not success:
                self.unit_control.notify(message)
        elif command == "drone_launch" and self.fleet is not None:
            drone, message = self.fleet.launch(self.airport, arguments[0])
            if drone is None:
                self.unit_control.notify(message)
            elif self.drone_control is not None:
                self.unit_control.cancel(deselect=True)
                self.drone_control.cancel()
                self.drone_control.selected = drone
        elif command == "drone_cancel" and self.fleet is not None:
            self.fleet.production.cancel(self.airport, arguments[0])
        elif command == "drone_focus" and self.fleet is not None and self.drone_control is not None:
            drones = [drone for drone in self.fleet.drones if drone.airport is self.airport and drone.definition.key == arguments[0] and drone.controllable]
            if drones:
                current = self.drone_control.selected
                index = (drones.index(current) + 1) % len(drones) if current in drones else 0
                self.unit_control.cancel(deselect=True)
                self.drone_control.cancel()
                self.drone_control.selected = drones[index]
                self.focus(drones[index].position)
        elif command == "recruit" and self.recruitment is not None:
            success, message = self.recruitment.recruit(self.barracks, arguments[0])
            if not success:
                self.unit_control.notify(message)
        elif command == "recruit_cancel" and self.recruitment is not None:
            self.recruitment.cancel_last(self.barracks)
        elif command == "disband" and self.recruitment is not None:
            if 0 <= arguments[0] < len(self.unit_control.units):
                success, message = self.recruitment.disband(self.barracks, self.unit_control.units[arguments[0]])
                if not success:
                    self.unit_control.notify(message)
        else:
            self.pages.activate(command, arguments)
        self.render_surfaces()

    def handle_key(self, key):
        shortcuts = {pygame.K_F1 + index: section for index, (section, _) in enumerate(SECTIONS)}
        shortcuts.update({pygame.K_1 + index: section for index, (section, _) in enumerate(SECTIONS)})
        if key in shortcuts:
            if self.collapsed:
                self.collapsed = False
                self.layout(self.camera.viewport_size)
            self.activate(("section", shortcuts[key]))
        elif key == pygame.K_SPACE:
            self.activate(("pause",))
        elif key == pygame.K_ESCAPE and self.active_section:
            self.activate(("close",))
        else:
            return False
        return True

    def draw(self, screen, duration=1 / 60):
        self.render_surfaces()
        self.inspector_motion.set(self.inspector_surface, self.inspector_area.topleft)
        self.inspector_motion.draw(screen, duration)
        self.dock_motion.set(self.dock_surface, self.panel_area.topleft)
        self.dock_motion.draw(screen, duration)
        action = self.action_at(self.pointer)
        tooltips = {("pause",): "Продовжити · Пробіл" if self.paused else "Пауза · Пробіл", ("capital",): "Перейти до столиці", ("collapse",): "Розгорнути панель" if self.collapsed else "Згорнути панель", ("rename",): "Перейменувати загін · F2"}
        caption = tooltips.get(action)
        if caption != self.tooltip_key:
            self.tooltip_key = caption
            self.tooltip_image = None
        if caption is not None and self.tooltip_image is None:
            label = text_image(self.fonts["body"], tooltips[action], TEXT)
            rectangle = pygame.Rect(0, 0, label.get_width() + 16, label.get_height() + 12)
            self.tooltip_image = pygame.Surface(rectangle.size, pygame.SRCALPHA)
            pygame.draw.rect(self.tooltip_image, (17, 26, 25), rectangle, border_radius=3)
            pygame.draw.rect(self.tooltip_image, BORDER, rectangle, 1, border_radius=3)
            self.tooltip_image.blit(label, label.get_rect(center=rectangle.center))
        position = (round(self.pointer.x + 4), self.panel_area.top - 42)
        self.tooltip_motion.set(self.tooltip_image, position)
        self.tooltip_motion.draw(screen, duration)
