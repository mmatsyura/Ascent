import ctypes
import math
import sys
import time

import pygame

from game.settings import (
    CAMERA_SPEED,
    MAX_ZOOM,
    PAN_RESPONSE,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    ZOOM_RESPONSE,
)


class Camera:
    def __init__(self, viewport_size):
        self.viewport_size = viewport_size
        self.position = pygame.Vector2(WORLD_WIDTH * 0.51, WORLD_HEIGHT * 0.51)
        self.pan_remaining = pygame.Vector2()
        self.zoom = self.minimum_zoom * 1.16
        self.target_zoom = self.zoom
        self.zoom_anchor = pygame.Vector2(viewport_size) / 2
        self.scaling_buffer = None
        self.render_bounds = None
        self.constrain()

    @property
    def minimum_zoom(self):
        return max(self.viewport_size[0] / WORLD_WIDTH, self.viewport_size[1] / WORLD_HEIGHT)

    @property
    def visible_area(self):
        visible_size = pygame.Vector2(self.viewport_size) / self.zoom
        return pygame.Rect(self.position - visible_size / 2, visible_size)

    def constrain(self):
        self.zoom = max(self.minimum_zoom, min(MAX_ZOOM, self.zoom))
        self.target_zoom = max(self.minimum_zoom, min(MAX_ZOOM, self.target_zoom))
        half_width = self.viewport_size[0] / self.zoom / 2
        half_height = self.viewport_size[1] / self.zoom / 2
        self.position.x = max(half_width, min(WORLD_WIDTH - half_width, self.position.x))
        self.position.y = max(half_height, min(WORLD_HEIGHT - half_height, self.position.y))
        destination = self.position + self.pan_remaining
        destination.x = max(half_width, min(WORLD_WIDTH - half_width, destination.x))
        destination.y = max(half_height, min(WORLD_HEIGHT - half_height, destination.y))
        self.pan_remaining = destination - self.position

    def screen_to_world(self, screen_position):
        offset = pygame.Vector2(screen_position) - pygame.Vector2(self.viewport_size) / 2
        return self.position + offset / self.zoom

    def world_to_screen(self, world_position):
        return pygame.Vector2(
            (world_position[0] - self.position.x) * self.zoom + self.viewport_size[0] / 2,
            (world_position[1] - self.position.y) * self.zoom + self.viewport_size[1] / 2,
        )

    def change_zoom(self, screen_position, steps):
        self.zoom_anchor.update(screen_position)
        self.target_zoom = max(self.minimum_zoom, min(MAX_ZOOM, self.target_zoom * 1.16**steps))

    def update(self, elapsed_seconds):
        if self.zoom != self.target_zoom:
            anchored_position = self.screen_to_world(self.zoom_anchor)
            blend = -math.expm1(-ZOOM_RESPONSE * elapsed_seconds)
            difference = math.log(self.target_zoom / self.zoom)
            self.zoom = (
                self.target_zoom
                if abs(difference) < 0.0001
                else self.zoom * math.exp(difference * blend)
            )
            self.position += anchored_position - self.screen_to_world(self.zoom_anchor)

        if self.pan_remaining.length_squared():
            blend = -math.expm1(-PAN_RESPONSE * elapsed_seconds)
            movement = (
                self.pan_remaining
                if self.pan_remaining.length() * self.zoom < 0.04
                else self.pan_remaining * blend
            )
            self.position += movement
            self.pan_remaining -= movement

        self.constrain()

    def move(self, screen_offset):
        self.pan_remaining += pygame.Vector2(screen_offset) / self.zoom
        self.constrain()

    def pan_to(self, world_position):
        self.pan_remaining = pygame.Vector2(world_position) - self.position
        self.constrain()

    def stop_motion(self):
        self.pan_remaining.update(0, 0)

    def show_entire_map(self):
        self.stop_motion()
        self.position.update(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)
        self.zoom = self.minimum_zoom
        self.target_zoom = self.zoom
        self.constrain()

    def draw(self, screen, terrain, scenery=False, area=None, offset=(0, 0)):
        detail_level = max(0, round(math.log2(1 / self.zoom))) if self.zoom < 1 else 0
        detail_level = min(len(terrain.detail_levels) - 1, detail_level)

        divisor = 2**detail_level
        area = pygame.Rect((0, 0), self.viewport_size) if area is None else area
        if self.render_bounds is not None:
            area = area.clip(self.render_bounds)
        if not area.w or not area.h:
            return
        view_left = self.position.x - self.viewport_size[0] / self.zoom / 2
        view_top = self.position.y - self.viewport_size[1] / self.zoom / 2
        world_left = view_left + area.left / self.zoom
        world_top = view_top + area.top / self.zoom
        visible_width = area.w / self.zoom
        visible_height = area.h / self.zoom

        source_surface = (
            terrain.scenery_detail_levels[detail_level]
            if scenery
            else terrain.detail_levels[detail_level]
        )
        source_left = max(0, math.floor(world_left / divisor))
        source_top = max(0, math.floor(world_top / divisor))
        source_right = min(
            source_surface.get_width(), math.ceil((world_left + visible_width) / divisor)
        )
        source_bottom = min(
            source_surface.get_height(), math.ceil((world_top + visible_height) / divisor)
        )
        source_area = pygame.Rect(
            source_left, source_top, source_right - source_left, source_bottom - source_top
        )
        if source_area.w <= 0 or source_area.h <= 0:
            return

        scale = self.zoom * divisor
        scaled_size = (math.ceil(source_area.w * scale), math.ceil(source_area.h * scale))
        buffer_size = (
            max(self.viewport_size[0] + 8, scaled_size[0]),
            max(self.viewport_size[1] + 8, scaled_size[1]),
        )

        if (
            self.scaling_buffer is None
            or self.scaling_buffer.get_width() < buffer_size[0]
            or self.scaling_buffer.get_height() < buffer_size[1]
        ):
            self.scaling_buffer = pygame.Surface(buffer_size).convert()

        scaled_surface = self.scaling_buffer.subsurface((0, 0, *scaled_size))
        pygame.transform.smoothscale(
            source_surface.subsurface(source_area), scaled_size, scaled_surface
        )

        screen.blit(
            scaled_surface,
            (
                round((source_left * divisor - view_left) * self.zoom + offset[0]),
                round((source_top * divisor - view_top) * self.zoom + offset[1]),
            ),
        )


class EdgeScrolling:
    def __init__(self):
        self.velocity = pygame.Vector2()

    def update(self, pointer, viewport_size, elapsed_seconds, enabled=True):
        width, height = viewport_size
        if not enabled or not (0 <= pointer[0] < width and 0 <= pointer[1] < height):
            self.velocity.update(0, 0)
            return pygame.Vector2()
        margin = max(24, min(42, height * 0.03))
        direction = pygame.Vector2(
            self.edge_strength(pointer[0], width, margin),
            self.edge_strength(pointer[1], height, margin),
        )
        if direction.length_squared() > 1:
            direction.normalize_ip()
        blend = -math.expm1(-12 * max(0, elapsed_seconds))
        self.velocity += (direction * CAMERA_SPEED - self.velocity) * blend
        if self.velocity.length_squared() < 0.01:
            self.velocity.update(0, 0)
        return self.velocity * elapsed_seconds

    @staticmethod
    def edge_strength(position, extent, margin):
        strength = max(0, 1 - position / margin) - max(0, 1 - (extent - 1 - position) / margin)
        magnitude = abs(strength)
        return -math.copysign(magnitude * magnitude * (3 - 2 * magnitude), strength)


def configure_display():
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            pass


class FrameClock:
    def __init__(self):
        self.previous_frame = time.perf_counter()

    def tick(self, frame_rate=0):
        if frame_rate > 0:
            deadline = self.previous_frame + 1 / frame_rate
            remaining = deadline - time.perf_counter()
            if remaining > 0.00025:
                time.sleep(remaining - 0.00025)
            while time.perf_counter() < deadline:
                pass
        current = time.perf_counter()
        duration = current - self.previous_frame
        self.previous_frame = current
        return duration * 1000
