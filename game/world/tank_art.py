from functools import lru_cache
import math

import pygame
from game.sprite_cache import prepared_sprite
from game.world.badge_art import badge_background

from game.world.tank_geometry import TankCanvas


def draw_tracks(canvas, angle, phase):
    for side in (-1, 1):
        left = -34 if side < 0 else 19
        outline = [(left + 3, -37), (left + 12, -37), (left + 15, -30), (left + 15, 31), (left + 11, 38), (left + 3, 38), (left, 30), (left, -30)]
        canvas.solid((52, 68, 51), outline, 1, 11, angle, roof=(65, 81, 58))
        for index in range(12):
            depth = -33 + (index * 5.8 + phase * 1.45) % 66
            canvas.box((95, 110, 77), (left + 1, depth, 13, 2), 11, 11.8, angle)
        for depth in (-26, -13, 0, 13, 26):
            horizontal = -34.3 if side < 0 else 34.3
            wheel = [(horizontal, depth + math.cos(step * math.tau / 12) * 5.3, 6 + math.sin(step * math.tau / 12) * 4.4) for step in range(12)]
            hub = [(horizontal + side * .2, depth + math.cos(step * math.tau / 8) * 2, 6 + math.sin(step * math.tau / 8) * 1.7) for step in range(8)]
            canvas.polygon((31, 46, 35), wheel, angle)
            canvas.polygon((113, 127, 80), hub, angle)
        for depth in (-37, 37):
            for height in (3, 7):
                canvas.polygon((85, 99, 68), [(left + 3, depth, height), (left + 12, depth, height), (left + 12, depth, height + 1), (left + 3, depth, height + 1)], angle)


def draw_hull(canvas, angle):
    outline = [(-23, -36), (22, -36), (28, -24), (27, 30), (20, 36), (-22, 36), (-28, 27), (-28, -23)]
    canvas.solid((111, 128, 80), outline, 9, 18, angle)
    canvas.roof((139, 149, 94), [(-23, -36), (22, -36), (25, -24), (-25, -24)], 18.2, angle)
    canvas.roof((79, 104, 62), [(-24, -20), (-8, -23), (-2, -4), (-18, 5), (-26, -3)], 18.3, angle)
    canvas.roof((85, 111, 65), [(14, -20), (25, -24), (25, 19), (12, 27), (7, 8)], 18.3, angle)
    canvas.box((55, 78, 47), (-17, 20, 34, 11), 18, 18.8, angle)
    for horizontal in range(-14, 16, 5):
        canvas.box((33, 55, 39), (horizontal, 21, 2, 9), 18.8, 19.3, angle)
    for horizontal in (-20, -7, 6):
        canvas.box((143, 153, 96), (horizontal, -33, 11, 7), 18.2, 20, angle)
    for horizontal in (-28, 22):
        canvas.box((116, 134, 83), (horizontal, -23, 6, 48), 12, 18, angle)
        for depth in (-18, -3, 12):
            canvas.box((63, 91, 52), (horizontal + 1, depth, 4, 1.4), 18, 18.4, angle)
    for horizontal in (-22, 18):
        canvas.box((213, 210, 148), (horizontal, -36.4, 4, 1.2), 13, 16, angle)
        canvas.box((139, 65, 44), (horizontal, 36.2, 4, 1), 12, 14, angle)
    canvas.polygon((57, 124, 170), [(-28.2, -14, 13), (-28.2, 2, 13), (-28.2, 2, 17), (-28.2, -14, 17)], angle)


def draw_turret(canvas, angle):
    outline = [(-16, -15), (3, -19), (19, -10), (19, 9), (7, 18), (-17, 13), (-22, 0)]
    canvas.solid((126, 143, 86), outline, 18.5, 29, angle)
    canvas.roof((150, 159, 101), [(-16, -15), (3, -19), (-1, -2), (-19, 1), (-22, 0)], 29.2, angle)
    canvas.roof((91, 119, 69), [(3, -19), (19, -10), (19, 9), (7, 18), (1, 5)], 29.3, angle)
    canvas.box((89, 115, 66), (-8, -23, 14, 12), 21, 27, angle)
    canvas.box((123, 144, 85), (-3.3, -69, 6, 49), 24, 28, angle)
    canvas.box((177, 182, 117), (-2.6, -68, 1, 46), 28, 28.5, angle)
    for depth in (-57, -38):
        canvas.box((65, 91, 53), (-3.8, depth, 7, 2), 24, 28.8, angle)
    canvas.box((86, 110, 64), (-4.8, -75, 9, 7), 24.5, 29, angle)
    canvas.box((26, 44, 31), (-3.1, -75.2, 5.5, .7), 25.5, 27.8, angle)
    canvas.disc((64, 89, 53), (4, 5), 7.2, 30, angle)
    canvas.disc((133, 149, 89), (4, 5), 5.5, 31, angle)
    canvas.box((48, 73, 44), (2.8, 1.5, 1.4, 7), 31, 31.5, angle)
    canvas.box((44, 72, 71), (-13, -8, 6, 3), 29, 31.5, angle)
    canvas.box((43, 63, 41), (12, -8, 2.3, 14), 30, 32, angle)
    canvas.box((31, 47, 34), (12.5, -15, 1.2, 8), 31, 32, angle)
    canvas.box((47, 78, 47), (-15, 10, 1, 1), 29, 48, angle)


@lru_cache(maxsize=128)
def hull_faces(angle):
    canvas = TankCanvas()
    draw_hull(canvas, angle)
    return tuple(canvas.faces)


@lru_cache(maxsize=128)
def hull_layer(angle, phase):
    canvas = TankCanvas()
    shadow = [(math.cos(index * math.tau / 16) * 39, math.sin(index * math.tau / 16) * 43, 0) for index in range(16)]
    canvas.polygon((18, 30, 23, 35), shadow, angle, underlay=True)
    draw_tracks(canvas, angle, phase)
    canvas.faces.extend(hull_faces(angle))
    return canvas.finish(256)


@lru_cache(maxsize=180)
def turret_layer(angle):
    canvas = TankCanvas()
    draw_turret(canvas, angle)
    return canvas.finish(256)


@lru_cache(maxsize=32)
def tank_source(hull_step, turret_step, phase=0, selected=False):
    image = hull_layer(hull_step, phase).copy()
    image.blit(turret_layer(turret_step), (0, 0))
    if selected:
        image.fill((204, 215, 203, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return image


@lru_cache(maxsize=512)
def tank_sprite(size, hull_step, turret_step, phase=0, selected=False):
    return prepared_sprite(pygame.transform.smoothscale(tank_source(hull_step, turret_step, phase, selected), (size, size)))


@lru_cache(maxsize=48)
def tank_badge(size, selected=False):
    image = pygame.Surface((160, 160), pygame.SRCALPHA)
    image.blit(badge_background(), (0, 0))
    silhouette = tank_sprite(168, 35, 30)
    image.blit(silhouette, silhouette.get_rect(center=(80, 84)))
    if selected:
        image.fill((180, 180, 180, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return prepared_sprite(pygame.transform.smoothscale(image, (size, size)))
