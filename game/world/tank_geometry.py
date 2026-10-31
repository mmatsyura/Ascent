import math
from functools import lru_cache

import pygame


TANK_RENDER_SIZE = 128 / 1.5
TANK_TRACK_OFFSET = 13.0
GROUND_DEPTH = .64


@lru_cache(maxsize=720)
def view_basis(angle):
    radians = math.radians(angle)
    projected_angle = math.atan2(math.sin(radians) * GROUND_DEPTH, math.cos(radians))
    return math.cos(projected_angle), math.sin(projected_angle)


def track_lateral(angle):
    cosine, sine = view_basis(angle)
    return pygame.Vector2(cosine, sine * GROUND_DEPTH) * TANK_TRACK_OFFSET


class TankCanvas:
    def __init__(self):
        self.faces = []

    def transform(self, point, angle):
        horizontal, depth, height = point
        cosine, sine = view_basis(angle)
        return (horizontal * cosine - depth * sine, horizontal * sine + depth * cosine, height)

    def project(self, point):
        horizontal, depth, height = point
        return (round(256 + horizontal * 3), round(256 + (depth * GROUND_DEPTH - height * .9) * 3))

    def polygon(self, color, points, angle=0, underlay=False):
        points = [self.transform(point, angle) for point in points]
        depth = sum(point[1] + point[2] * .8 for point in points) / len(points)
        if underlay:
            depth = -math.inf
        self.faces.append((depth, color, [self.project(point) for point in points]))

    def roof(self, color, points, height, angle=0):
        self.polygon(color, [(horizontal, depth, height) for horizontal, depth in points], angle)

    def solid(self, color, footprint, bottom, top, angle=0, roof=None):
        for index, first in enumerate(footprint):
            last = footprint[(index + 1) % len(footprint)]
            rotated_first = self.transform((*first, 0), angle)
            rotated_last = self.transform((*last, 0), angle)
            edge_x = rotated_last[0] - rotated_first[0]
            edge_y = rotated_last[1] - rotated_first[1]
            light = .61 + .17 * (edge_y - edge_x) / max(1, math.hypot(edge_x, edge_y))
            shade = tuple(round(channel * light) for channel in color)
            self.polygon(shade, [(*first, bottom), (*last, bottom), (*last, top), (*first, top)], angle)
        self.roof(roof or color, footprint, top, angle)

    def box(self, color, rectangle, bottom, top, angle=0, roof=None):
        left, rear, width, length = rectangle
        self.solid(color, [(left, rear), (left + width, rear), (left + width, rear + length), (left, rear + length)], bottom, top, angle, roof)

    def disc(self, color, center, radius, height, angle=0):
        points = [(center[0] + math.cos(index * math.tau / 12) * radius,
                   center[1] + math.sin(index * math.tau / 12) * radius) for index in range(12)]
        self.solid(color, points, height - 1.5, height, angle)

    def finish(self, size, selected=False):
        image = pygame.Surface((512, 512), pygame.SRCALPHA)
        for _, color, points in sorted(self.faces, key=lambda face: face[0]):
            pygame.draw.polygon(image, color, points)
        if selected:
            image.fill((204, 215, 203, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return pygame.transform.smoothscale(image, (size, size))
