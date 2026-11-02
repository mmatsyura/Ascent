from functools import lru_cache
import math

import pygame

from game.rendering import prepared_sprite
from game.world.soldier_art import badge_background
from game.world.tank_geometry import TankCanvas


def draw_wheels(canvas, angle, phase):
    for side in (-1, 1):
        for depth in (-36, -17, 18, 38):
            horizontal = side * 23
            tire = [
                (
                    horizontal,
                    depth + math.cos(index * math.tau / 16) * 7.5,
                    8 + math.sin(index * math.tau / 16) * 7.5,
                )
                for index in range(16)
            ]
            hub = [
                (
                    horizontal + side * 0.3,
                    depth + math.cos(index * math.tau / 12) * 4,
                    8 + math.sin(index * math.tau / 12) * 4,
                )
                for index in range(12)
            ]
            canvas.polygon((25, 30, 27), tire, angle)
            canvas.polygon((98, 111, 78), hub, angle)
            for index in range(4):
                rotation = (index + phase / 4) * math.pi / 2
                canvas.polygon(
                    (47, 56, 43),
                    [
                        (
                            horizontal + side * 0.6,
                            depth + math.cos(rotation) * 1.4,
                            8 + math.sin(rotation) * 1.4,
                        ),
                        (
                            horizontal + side * 0.6,
                            depth + math.cos(rotation + 0.4) * 3.4,
                            8 + math.sin(rotation + 0.4) * 3.4,
                        ),
                        (
                            horizontal + side * 0.6,
                            depth + math.cos(rotation + 0.9) * 2.7,
                            8 + math.sin(rotation + 0.9) * 2.7,
                        ),
                    ],
                    angle,
                )


def draw_chassis(canvas, angle, deployment):
    canvas.box((64, 79, 54), (-20, -47, 40, 98), 9, 16, angle)
    canvas.box((96, 112, 73), (-23, -14, 46, 65), 15, 19, angle)
    canvas.box((78, 94, 63), (-21, -50, 42, 29), 14, 33, angle)
    canvas.roof((123, 132, 86), [(-20, -49), (20, -49), (20, -23), (-20, -23)], 33.2, angle)
    canvas.roof(
        (63, 78, 54), [(-20, -49), (-4, -49), (1, -41), (-12, -34), (-20, -36)], 33.3, angle
    )
    canvas.roof((122, 105, 74), [(5, -46), (17, -49), (20, -33), (12, -31)], 33.4, angle)
    canvas.polygon(
        (25, 43, 45), [(-18, -50.2, 22), (18, -50.2, 22), (18, -50.2, 30), (-18, -50.2, 30)], angle
    )
    canvas.polygon(
        (93, 124, 119),
        [(-16, -50.4, 28), (16, -50.4, 28), (16, -50.4, 30), (-16, -50.4, 30)],
        angle,
    )
    canvas.polygon(
        (68, 82, 65),
        [(-0.8, -50.5, 22), (0.8, -50.5, 22), (0.8, -50.5, 30), (-0.8, -50.5, 30)],
        angle,
    )
    for side in (-1, 1):
        x = side * 21.2
        canvas.polygon(
            (37, 58, 58), [(x, -46, 23), (x, -27, 23), (x, -27, 30), (x, -46, 30)], angle
        )
        canvas.polygon(
            (132, 139, 92), [(x, -30, 18), (x, -24, 18), (x, -24, 19), (x, -30, 19)], angle
        )
        canvas.box((74, 86, 60), (side * 22 - 2, -46, 4, 8), 31, 35, angle)
        canvas.box((80, 97, 63), (side * 21 - 3, 3, 6, 41), 17, 22, angle)
    canvas.box((48, 62, 47), (-19, -52, 38, 2), 11, 15, angle)
    canvas.box((56, 66, 49), (-17, -50.8, 34, 1), 16, 20, angle)
    for x in (-16, 11):
        canvas.box((211, 204, 147), (x, -53, 5, 1), 15, 18, angle)
        canvas.box((151, 57, 43), (x, 51, 5, 1), 12, 15, angle)
    canvas.box((56, 70, 49), (-23, 49, 46, 3), 8, 12, angle)
    for x in (-19, 13):
        canvas.box((217, 205, 167), (x, 52.1, 7, 0.5), 9, 12, angle)
        canvas.box((153, 65, 49), (x + 2, 52.7, 2, 0.3), 9, 12, angle)
    for side in (-1, 1):
        for y in (-7, 41):
            extension = 24 + deployment * 14
            left = -extension if side < 0 else 20
            canvas.box((98, 114, 75), (left, y - 2, extension - 20, 4), 9, 13, angle)
            x = side * extension
            if deployment > 0.06:
                canvas.box((67, 83, 57), (x - 2, y - 2, 4, 4), 1, 12, angle)
                canvas.disc((44, 55, 42), (x, y), 4.5, 1, angle)


def draw_launcher(canvas, angle, deployment):
    elevation = math.radians(58 * deployment)
    cosine, sine = math.cos(elevation), math.sin(elevation)

    def point(x, distance, height):
        return (x, 37 - distance * cosine + height * sine, 21 + distance * sine + height * cosine)

    canvas.box((78, 95, 62), (-14, 29, 28, 12), 18, 24, angle)
    canvas.polygon(
        (164, 169, 121), [(-2, 5, 18), (2, 5, 18), point(2, 30, -2), point(-2, 30, -2)], angle
    )
    for row in range(2):
        for column in range(2):
            left = -17 + column * 17
            bottom = row * 10
            color = (107, 123, 79) if (row + column) % 2 == 0 else (95, 111, 73)
            faces = (
                (
                    tuple(round(value * 0.65) for value in color),
                    [
                        (left, 0, bottom),
                        (left + 16, 0, bottom),
                        (left + 16, 0, bottom + 9),
                        (left, 0, bottom + 9),
                    ],
                ),
                (
                    (62, 75, 51),
                    [
                        (left, 0, bottom),
                        (left, 61, bottom),
                        (left, 61, bottom + 9),
                        (left, 0, bottom + 9),
                    ],
                ),
                (
                    (76, 92, 60),
                    [
                        (left + 16, 0, bottom),
                        (left + 16, 61, bottom),
                        (left + 16, 61, bottom + 9),
                        (left + 16, 0, bottom + 9),
                    ],
                ),
                (
                    color,
                    [
                        (left, 0, bottom + 9),
                        (left + 16, 0, bottom + 9),
                        (left + 16, 61, bottom + 9),
                        (left, 61, bottom + 9),
                    ],
                ),
                (
                    (44, 54, 40),
                    [
                        (left, 61, bottom),
                        (left + 16, 61, bottom),
                        (left + 16, 61, bottom + 9),
                        (left, 61, bottom + 9),
                    ],
                ),
            )
            for shade, vertices in faces:
                canvas.polygon(shade, [point(*vertex) for vertex in vertices], angle)
            for position, patch_color in (
                (6, (61, 76, 51)),
                (24, (133, 115, 78)),
                (44, (49, 62, 43)),
            ):
                canvas.polygon(
                    patch_color,
                    [
                        point(left + 1, position, bottom + 9.1),
                        point(left + 14, position + 4, bottom + 9.1),
                        point(left + 12, position + 13, bottom + 9.1),
                        point(left + 3, position + 9, bottom + 9.1),
                    ],
                    angle,
                )
            for distance in (1, 19, 40, 59):
                canvas.polygon(
                    (150, 151, 104),
                    [
                        point(left - 0.4, distance, bottom + 9.3),
                        point(left + 16.4, distance, bottom + 9.3),
                        point(left + 16.4, distance + 1.3, bottom + 9.3),
                        point(left - 0.4, distance + 1.3, bottom + 9.3),
                    ],
                    angle,
                )
            canvas.polygon(
                (150, 150, 108),
                [
                    point(left + 1, 61.3, bottom + 1),
                    point(left + 15, 61.3, bottom + 1),
                    point(left + 15, 61.3, bottom + 8),
                    point(left + 1, 61.3, bottom + 8),
                ],
                angle,
            )
            canvas.polygon(
                (39, 48, 37),
                [
                    point(left + 3, 61.5, bottom + 2),
                    point(left + 13, 61.5, bottom + 2),
                    point(left + 13, 61.5, bottom + 7),
                    point(left + 3, 61.5, bottom + 7),
                ],
                angle,
            )
    mast_height = 30 + deployment * 33
    canvas.box((67, 81, 53), (22, 12, 1.3, 1.3), 19, mast_height, angle)
    canvas.box((140, 144, 100), (22, 12, 0.6, 0.6), mast_height, mast_height + 9, angle)


@lru_cache(maxsize=64)
def chassis_layer(angle, deployment_step, phase):
    deployment = deployment_step / 32
    deployment = deployment * deployment * (3 - 2 * deployment)
    canvas = TankCanvas()
    shadow = [
        (math.cos(index * math.tau / 20) * 32, math.sin(index * math.tau / 20) * 57, 0)
        for index in range(20)
    ]
    canvas.polygon((18, 30, 23, 35), shadow, angle, underlay=True)
    draw_wheels(canvas, angle, phase)
    draw_chassis(canvas, angle, deployment)
    return canvas.finish(256)


@lru_cache(maxsize=96)
def launcher_layer(angle, deployment_step):
    deployment = deployment_step / 32
    deployment = deployment * deployment * (3 - 2 * deployment)
    canvas = TankCanvas()
    draw_launcher(canvas, angle, deployment)
    return canvas.finish(256)


@lru_cache(maxsize=32)
def patriot_source(angle, deployment_step, phase=0, selected=False):
    image = chassis_layer(angle, deployment_step, phase).copy()
    image.blit(launcher_layer(angle, deployment_step), (0, 0))
    if selected:
        image.fill((204, 215, 203, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return image


@lru_cache(maxsize=384)
def patriot_sprite(size, angle, deployment_step, phase=0, selected=False):
    return prepared_sprite(
        pygame.transform.smoothscale(
            patriot_source(angle, deployment_step, phase, selected), (size, size)
        )
    )


@lru_cache(maxsize=2)
def patriot_badge_source(selected=False):
    image = badge_background().copy()
    sprite = patriot_sprite(164, 35, 25)
    image.blit(sprite, sprite.get_rect(center=(80, 96)))
    if selected:
        image.fill((180, 180, 180, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return image


@lru_cache(maxsize=96)
def patriot_badge(size, selected=False):
    return prepared_sprite(
        pygame.transform.smoothscale(patriot_badge_source(selected), (size, size))
    )
