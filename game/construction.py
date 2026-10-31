import pygame

from game.ui.fonts import fit_text, ui_font
from game.ui.theme import ACCENT, BORDER, TEXT
from game.world.building_manager import PlacedBuilding, building_area
from game.world.building_rendering import building_parts
from game.ui.transitions import SmoothLayer


class Construction:
    def __init__(self, manager, visibility):
        self.manager = manager
        self.visibility = visibility
        self.definition = None
        self.position = pygame.Vector2()
        self.pointer = pygame.Vector2()
        self.error = ""
        self.blocked = True
        self.animation_time = 0
        self.font = ui_font(14)
        self.title_font = ui_font(15, True)
        self.tooltip_motion = SmoothLayer(.16)
        self.tooltip_key = None
        self.tooltip_image = None

    @property
    def active(self):
        return self.definition is not None

    def begin(self, definition):
        if not self.manager.kingdom.can_afford(definition.cost):
            return False
        self.definition = definition
        self.error = ""
        self.blocked = True
        self.animation_time = 0
        return True

    def cancel(self):
        self.definition = None
        self.error = ""

    def update(self, pointer, camera, blocked, elapsed_seconds=0):
        if not self.active:
            return
        self.pointer.update(pointer)
        self.animation_time += elapsed_seconds
        world = camera.screen_to_world(pointer)
        self.position.update(round(world.x / 4) * 4, round(world.y / 4) * 4)
        self.blocked = blocked
        self.error = self.manager.validation(self.definition, self.position, self.visibility) if not blocked else ""

    def confirm(self):
        if not self.active or self.blocked:
            return False
        building, self.error = self.manager.place(self.definition, self.position, self.visibility)
        if building is None:
            return False
        self.cancel()
        return True

    def draw_preview(self, screen, camera):
        if not self.active or self.blocked:
            return
        color = (207, 119, 103) if self.error else (126, 195, 166)
        area = building_area(self.definition, self.position)
        points = [camera.world_to_screen(point) for point in (area.topleft, area.topright, area.bottomright, area.bottomleft)]
        preview = PlacedBuilding(self.definition, tuple(self.position), self.animation_time)
        parts = building_parts(preview, camera)
        region = pygame.Rect(round(points[0].x), round(points[0].y), round(points[2].x - points[0].x), round(points[2].y - points[0].y))
        region = region.unionall([part.rectangle for part in parts]).inflate(6, 6).clip(screen.get_rect())
        if not region.w or not region.h:
            return
        overlay = pygame.Surface(region.size, pygame.SRCALPHA)
        local_points = [point - pygame.Vector2(region.topleft) for point in points]
        pygame.draw.polygon(overlay, (*color, 42), local_points)
        pygame.draw.lines(overlay, (*color, 220), True, local_points, 2)
        for part in parts:
            image = part.image.copy()
            image.set_alpha(165 if self.error else 210)
            overlay.blit(image, part.rectangle.move(-region.x, -region.y))
        screen.blit(overlay, region)

    def draw_range(self, screen, camera):
        if not self.active or self.blocked:
            return
        position = camera.world_to_screen(self.position)
        radius = max(1, round(self.definition.vision_radius * camera.zoom))
        pygame.draw.circle(screen, (81, 121, 141), (round(position.x), round(position.y)), radius, 1)

    def draw_interface(self, screen, duration=1 / 60):
        if not self.active or self.blocked:
            self.tooltip_motion.set(None, self.tooltip_motion.target_position)
            self.tooltip_motion.draw(screen, duration)
            return
        title = self.title_font.render(f"{self.definition.name} · {self.definition.gold_cost} золота", True, ACCENT)
        detail = self.error or "ЛКМ — збудувати · ПКМ / Esc — скасувати"
        detail = fit_text(self.font, detail, 360)
        label = self.font.render(detail, True, (230, 159, 141) if self.error else TEXT)
        area = pygame.Rect(round(self.pointer.x + 20), round(self.pointer.y + 25), max(title.get_width(), label.get_width()) + 24, 62)
        area.clamp_ip(screen.get_rect().inflate(-16, -16))
        key = (self.definition.key, detail)
        if key != self.tooltip_key:
            self.tooltip_key = key
            self.tooltip_image = pygame.Surface(area.size, pygame.SRCALPHA)
            pygame.draw.rect(self.tooltip_image, (15, 26, 32), self.tooltip_image.get_rect(), border_radius=4)
            pygame.draw.rect(self.tooltip_image, BORDER, self.tooltip_image.get_rect(), 1, border_radius=4)
            self.tooltip_image.blit(title, (12, 10))
            self.tooltip_image.blit(label, (12, 34))
        self.tooltip_motion.set(self.tooltip_image, area.topleft)
        self.tooltip_motion.draw(screen, duration)
