from functools import lru_cache
import math

import pygame

from game.world.units import detail_blend, token_rectangle


@lru_cache(maxsize=96)
def selection_frame(width, height, circular):
    image = pygame.Surface((width, height), pygame.SRCALPHA)
    area = image.get_rect().inflate(-4, -4)
    if circular:
        for start in (.15, math.pi * .65, math.pi * 1.15, math.pi * 1.65):
            pygame.draw.arc(image, (8, 20, 25, 195), area.inflate(2, 2), start, start + .8, 3)
            pygame.draw.arc(image, (189, 219, 215, 225), area, start, start + .8, 1)
    else:
        length = min(15, max(5, width // 5))
        for x, y, dx, dy in ((area.left, area.top, 1, 1), (area.right - 1, area.top, -1, 1), (area.left, area.bottom - 1, 1, -1), (area.right - 1, area.bottom - 1, -1, -1)):
            points = [(x, y + dy * length), (x, y), (x + dx * length, y)]
            pygame.draw.lines(image, (9, 24, 29, 170), False, points, 3)
            pygame.draw.aalines(image, (183, 217, 212, 210), False, points)
    return image


def draw_selection(screen, camera, units):
    visible = camera.visible_area.inflate(220, 220)
    detailed = detail_blend(camera.zoom) >= .5
    blits = []
    for unit in units:
        if not visible.collidepoint(unit.position):
            continue
        if not detailed:
            area = token_rectangle(unit, screen, camera).inflate(10, 10)
        else:
            size = round((85 if unit.is_tank else 135) * camera.zoom)
            if len(units) > 8:
                size = min(size, 64)
            area = pygame.Rect(0, 0, size, round(size * .65))
            point = camera.world_to_screen(unit.position)
            area.center = round(point.x), round(point.y)
        if detailed:
            for index, position in enumerate((area.topleft, (area.right - 18, area.top), (area.left, area.bottom - 18), (area.right - 18, area.bottom - 18))):
                blits.append((selection_corner(index), position))
        else:
            image = selection_frame(area.w, area.h, True)
            blits.append((image, area))
    screen.blits(blits, doreturn=False)


@lru_cache(maxsize=4)
def selection_corner(index):
    image = pygame.Surface((18, 18), pygame.SRCALPHA)
    points = [(2, 15), (2, 2), (15, 2)]
    pygame.draw.lines(image, (9, 24, 29, 155), False, points, 3)
    pygame.draw.aalines(image, (183, 217, 212, 195), False, points)
    return pygame.transform.flip(image, bool(index % 2), bool(index // 2))


@lru_cache(maxsize=48)
def order_marker(phase):
    image = pygame.Surface((52, 52), pygame.SRCALPHA)
    progress = phase / 31
    radius = 6 + progress * 15
    alpha = round(230 * (1 - progress))
    center = pygame.Vector2(26, 26)
    points = [center + pygame.Vector2(radius, 0).rotate(angle) for angle in (0, 90, 180, 270)]
    pygame.draw.aalines(image, (180, 223, 203, alpha), True, points)
    pygame.draw.circle(image, (207, 234, 216, alpha), center, 2)
    return image
