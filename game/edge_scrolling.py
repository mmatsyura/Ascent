import math

import pygame

from game.settings import CAMERA_SPEED


class EdgeScrolling:
    def __init__(self):
        self.velocity = pygame.Vector2()

    def update(self, pointer, viewport_size, elapsed_seconds, enabled=True):
        width, height = viewport_size
        if not enabled or not (0 <= pointer[0] < width and 0 <= pointer[1] < height):
            self.velocity.update(0, 0)
            return pygame.Vector2()
        margin = max(24, min(42, height * .03))
        direction = pygame.Vector2(
            self.edge_strength(pointer[0], width, margin),
            self.edge_strength(pointer[1], height, margin),
        )
        if direction.length_squared() > 1:
            direction.normalize_ip()
        blend = -math.expm1(-12 * max(0, elapsed_seconds))
        self.velocity += (direction * CAMERA_SPEED - self.velocity) * blend
        if self.velocity.length_squared() < .01:
            self.velocity.update(0, 0)
        return self.velocity * elapsed_seconds

    @staticmethod
    def edge_strength(position, extent, margin):
        strength = max(0, 1 - position / margin) - max(0, 1 - (extent - 1 - position) / margin)
        magnitude = abs(strength)
        return -math.copysign(magnitude * magnitude * (3 - 2 * magnitude), strength)
