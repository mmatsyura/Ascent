from functools import lru_cache
import math

import pygame

from game.rendering import RenderPart
from game.world.units import detail_blend
from game.world.tank_geometry import TANK_TRACK_OFFSET, track_lateral


@lru_cache(maxsize=96)
def tread_stamp(zoom_step, angle_step):
    zoom = zoom_step / 100
    stamp = pygame.Surface((max(2, round(7 / 1.5 * zoom)), max(2, round(3 / 1.5 * zoom))), pygame.SRCALPHA)
    stamp.fill((56, 66, 42, 90))
    pygame.draw.line(stamp, (89, 94, 59, 65), (0, 0), (stamp.get_width() - 1, 0))
    return pygame.transform.rotate(stamp, -angle_step)


def trail_part(unit, screen, camera):
    if not unit.tracks or detail_blend(camera.zoom) <= 0:
        return None
    age_key = (int(unit.squad_time * 4), len(unit.tracks))
    key = (camera.position.x, camera.position.y, camera.zoom, camera.viewport_size, unit.track_revision, age_key)
    if unit.trail_cache_key == key:
        return unit.trail_cache
    visible = camera.visible_area.inflate(40, 40)
    marks = [mark for mark in unit.tracks if visible.collidepoint(mark[0])]
    if not marks:
        return None
    points = [camera.world_to_screen(mark[0]) for mark in marks]
    radius = math.ceil((TANK_TRACK_OFFSET + 6) * camera.zoom)
    left = math.floor(min(point.x for point in points)) - radius
    top = math.floor(min(point.y for point in points)) - radius
    right = math.ceil(max(point.x for point in points)) + radius
    bottom = math.ceil(max(point.y for point in points)) + radius
    area = pygame.Rect(left, top, right - left, bottom - top).clip(screen.get_rect())
    if not area.w or not area.h:
        return None
    image = pygame.Surface(area.size, pygame.SRCALPHA)
    for mark, position in zip(marks, points):
        _, angle, age = mark
        lateral = track_lateral(angle) * camera.zoom
        stamp_angle = math.degrees(math.atan2(lateral.y, lateral.x))
        stamp = tread_stamp(max(1, round(camera.zoom * 100)), round(stamp_angle / 3) * 3)
        opacity = round(255 * min(1, (20 - age) / 8) * detail_blend(camera.zoom))
        if opacity < 255:
            stamp = stamp.copy()
            stamp.set_alpha(opacity)
        for side in (-1, 1):
            center = position + lateral * side - pygame.Vector2(area.topleft)
            image.blit(stamp, stamp.get_rect(center=(round(center.x), round(center.y))))
    unit.trail_cache_key = key
    unit.trail_cache = RenderPart(-math.inf, image, area)
    return unit.trail_cache
