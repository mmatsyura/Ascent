import math

import pygame

from game.settings import WORLD_HEIGHT, WORLD_WIDTH
from game.ui.theme import ACCENT, MUTED, TEXT, draw_button, panel_surface, ui_font


class Minimap:
    def __init__(self, terrain):
        self.collapsed = False
        self.screen_size = (1440, 900)
        self.map_size = (328, 225)
        self.image = terrain.create_overview(self.map_size)
        self.font = ui_font(14, True)
        self.header_font = ui_font(14, True)
        self.map_area = pygame.Rect(0, 0, *self.map_size)
        self.button_areas = {}
        self.panel_area = pygame.Rect(0, 0, 364, 322)
        self.background = self.create_background()
        self.overview_label = self.font.render("Огляд", True, TEXT)
        self.cached_scale = None
        self.scale_image = None
        self.dragging = False
        self.drag_offset = pygame.Vector2()
        self.city_map = None
        self.visibility = None
        self.buildings = None
        self.contact_markers = None
        self.drone_fleet = None
        self.button_motion = {}

    def create_background(self):
        background = panel_surface(self.panel_area.size).copy()
        background.blit(self.header_font.render("МІНІКАРТА", True, MUTED), (34, 17))
        pygame.draw.line(background, (104, 98, 66), (27, 36), (337, 36))
        pygame.draw.rect(background, (9, 16, 19), (16, 44, 332, 229))
        pygame.draw.rect(background, (146, 127, 82), (16, 44, 332, 229), 1)
        return background

    def layout(self, screen_size):
        self.screen_size = screen_size
        self.panel_area.size = (364, 42 if self.collapsed else 322)
        self.background = self.create_background()
        self.map_area.size = (0, 0) if self.collapsed else self.map_size
        self.panel_area.bottomright = (screen_size[0] - 10, screen_size[1] - 8)
        self.map_area.topleft = (self.panel_area.x + 18, self.panel_area.y + 46)
        self.toggle_area = pygame.Rect(self.panel_area.right - 35, self.panel_area.y + 10, 24, 24)
        self.button_areas = {
            "zoom_out": pygame.Rect(self.panel_area.x + 18, self.panel_area.y + 281, 29, 24),
            "overview": pygame.Rect(self.panel_area.x + 54, self.panel_area.y + 281, 256, 24),
            "zoom_in": pygame.Rect(self.panel_area.x + 317, self.panel_area.y + 281, 29, 24),
        }

    def handle_click(self, position, camera):
        if self.toggle_area.collidepoint(position):
            self.collapsed = not self.collapsed
            self.end_drag()
            self.layout(self.screen_size)
            return True
        if self.map_area.collidepoint(position):
            camera.pan_to(self.world_position(position))
            return True

        for action, button_area in self.button_areas.items():
            if button_area.collidepoint(position):
                if action == "overview":
                    camera.zoom_anchor.update(pygame.Vector2(camera.viewport_size) / 2)
                    camera.target_zoom = camera.minimum_zoom
                    camera.pan_to((WORLD_WIDTH / 2, WORLD_HEIGHT / 2))
                else:
                    camera.change_zoom(
                        pygame.Vector2(camera.viewport_size) / 2, 1 if action == "zoom_in" else -1
                    )
                return True

        return self.panel_area.collidepoint(position)

    def world_position(self, position):
        horizontal = max(0, min(1, (position[0] - self.map_area.x) / self.map_area.w))
        vertical = max(0, min(1, (position[1] - self.map_area.y) / self.map_area.h))
        return pygame.Vector2(horizontal * WORLD_WIDTH, vertical * WORLD_HEIGHT)

    def viewport_rectangle(self, camera):
        visible_width = camera.viewport_size[0] / camera.zoom
        visible_height = camera.viewport_size[1] / camera.zoom
        return pygame.Rect(
            round(
                self.map_area.x
                + (camera.position.x - visible_width / 2) / WORLD_WIDTH * self.map_area.w
            ),
            round(
                self.map_area.y
                + (camera.position.y - visible_height / 2) / WORLD_HEIGHT * self.map_area.h
            ),
            max(1, round(visible_width / WORLD_WIDTH * self.map_area.w)),
            max(1, round(visible_height / WORLD_HEIGHT * self.map_area.h)),
        ).clip(self.map_area)

    def begin_drag(self, position, camera):
        if not self.map_area.collidepoint(position):
            return False
        self.dragging = True
        if self.viewport_rectangle(camera).collidepoint(position):
            self.drag_offset = self.world_position(position) - camera.position
            camera.stop_motion()
        else:
            self.drag_offset.update(0, 0)
            self.drag(position, camera)
        return True

    def drag(self, position, camera):
        if self.dragging:
            camera.pan_to(self.world_position(position) - self.drag_offset)

    def end_drag(self):
        self.dragging = False
        self.drag_offset.update(0, 0)

    def draw(self, screen, camera, duration=1 / 60):
        screen.blit(self.background, self.panel_area)
        pygame.draw.rect(screen, (41, 54, 49), self.toggle_area, border_radius=3)
        label = self.font.render("+" if self.collapsed else "−", True, TEXT)
        screen.blit(label, label.get_rect(center=self.toggle_area.center))
        if self.collapsed:
            return
        screen.blit(self.image, self.map_area)
        if self.city_map is not None:
            self.city_map.draw_minimap(screen, self.map_area)
        if self.buildings is not None:
            for building in self.buildings.displayed_buildings():
                point = (
                    round(self.map_area.x + building.position[0] / WORLD_WIDTH * self.map_area.w),
                    round(self.map_area.y + building.position[1] / WORLD_HEIGHT * self.map_area.h),
                )
                reveals = getattr(self.city_map, "reveals", None)
                opacity = reveals.building_opacity(building) if reveals is not None else 255
                if opacity <= 0:
                    continue
                if opacity == 255:
                    pygame.draw.rect(screen, (9, 20, 25), (point[0] - 3, point[1] - 3, 6, 6))
                    pygame.draw.rect(
                        screen, building.definition.accent, (point[0] - 2, point[1] - 2, 4, 4)
                    )
                else:
                    marker = pygame.Surface((6, 6), pygame.SRCALPHA)
                    marker.fill((9, 20, 25))
                    pygame.draw.rect(marker, building.definition.accent, (1, 1, 4, 4))
                    marker.set_alpha(opacity)
                    screen.blit(marker, (point[0] - 3, point[1] - 3))
        if self.visibility is not None:
            self.visibility.draw_minimap(screen, self.map_area)
        if self.contact_markers is not None:
            self.contact_markers.draw_minimap(screen, self.map_area)
        if self.drone_fleet is not None:
            for drone in self.drone_fleet.drones:
                if not drone.controllable:
                    continue
                point = (
                    round(self.map_area.x + drone.position[0] / WORLD_WIDTH * self.map_area.w),
                    round(self.map_area.y + drone.position[1] / WORLD_HEIGHT * self.map_area.h),
                )
                pygame.draw.circle(screen, (11, 29, 34), point, 3)
                pygame.draw.circle(screen, (142, 211, 207), point, 2)
        viewport = self.viewport_rectangle(camera)
        pygame.draw.rect(screen, (12, 23, 26), viewport.inflate(2, 2).clip(self.map_area), 1)
        pygame.draw.rect(
            screen,
            ACCENT if self.dragging else (233, 228, 204),
            viewport,
            2 if self.dragging else 1,
        )

        scale = round(camera.zoom / camera.minimum_zoom * 100)
        if scale != self.cached_scale:
            self.cached_scale = scale
            self.scale_image = self.font.render(f"{scale}%", True, ACCENT)
        screen.blit(
            self.scale_image,
            self.scale_image.get_rect(right=self.panel_area.x + 310, top=self.panel_area.y + 17),
        )

        mouse_position = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        for action, button_area in self.button_areas.items():
            hovered = button_area.collidepoint(mouse_position)
            state = self.button_motion.setdefault(action, [0.0, 0.0])
            blend = -math.expm1(-max(0, duration) / 0.085)
            state[0] += (float(hovered) - state[0]) * blend
            state[1] += (float(hovered and mouse_pressed) - state[1]) * blend
            draw_button(screen, button_area, *state)
            if action == "overview":
                screen.blit(
                    self.overview_label, self.overview_label.get_rect(center=button_area.center)
                )
            else:
                center_x, center_y = button_area.center
                pygame.draw.line(
                    screen, TEXT, (center_x - 4, center_y), (center_x + 4, center_y), 1
                )
                if action == "zoom_in":
                    pygame.draw.line(
                        screen, TEXT, (center_x, center_y - 4), (center_x, center_y + 4), 1
                    )
