from functools import lru_cache
import math

import pygame

from game.world.barracks_animation import animate_barracks
from game.world.building_art import building_base, building_point

ANIMATION_FRAMES = 64
ANIMATION_RATE = 16


def soft_light(surface, position, radius, color, opacity):
    center = (round(position[0]), round(position[1]))
    for size in range(max(1, round(radius)), 0, -1):
        strength = (1 - size / (radius + 1)) ** 2
        pygame.draw.circle(surface, (*color, round(opacity * strength)), center, size)


def animate_mine(image, overlay, point, phase):
    center = point(78.5, 18.5)
    radius_x = point(86, 18.5)[0] - center[0]
    radius_y = point(78.5, 28)[1] - center[1]
    wheel = pygame.Rect(
        round(center[0] - radius_x),
        round(center[1] - radius_y),
        round(radius_x * 2),
        round(radius_y * 2),
    )
    pygame.draw.ellipse(image, (38, 54, 51), wheel)
    pygame.draw.ellipse(image, (187, 173, 111), wheel, 2)
    for spoke in range(6):
        angle = math.tau * (phase + spoke / 6)
        tip = (
            round(center[0] + math.cos(angle) * (radius_x - 2)),
            round(center[1] + math.sin(angle) * (radius_y - 2)),
        )
        pygame.draw.line(image, (144, 157, 132), center, tip, 2)
    pygame.draw.circle(image, (211, 188, 117), center, 2)
    lift = 56 + math.sin(phase * math.tau) * 12
    pygame.draw.polygon(
        image,
        (58, 76, 68),
        [point(76, lift), point(85, lift + 3), point(85, lift + 13), point(76, lift + 10)],
    )
    for offset in (0, 4, 8):
        pygame.draw.line(
            image,
            (164, 169, 130),
            point(76 + offset, lift + offset / 3),
            point(76 + offset, lift + 10 + offset / 3),
            1,
        )
    travel = (0.5 - 0.5 * math.cos(phase * math.tau)) * 12
    horizontal = 103 - travel
    vertical = 97 + (109 - horizontal) * 26 / 42 - 6
    for offset in (-5, 5):
        pygame.draw.circle(
            image, (30, 45, 39), point(horizontal + offset, vertical + 6 + offset * 0.35), 4
        )
    pygame.draw.polygon(
        image,
        (67, 90, 81),
        [
            point(horizontal - 9, vertical - 4),
            point(horizontal + 7, vertical),
            point(horizontal + 5, vertical + 8),
            point(horizontal - 7, vertical + 4),
        ],
    )
    pygame.draw.polygon(
        image,
        (146, 150, 111),
        [
            point(horizontal - 9, vertical - 4),
            point(horizontal - 2, vertical - 9),
            point(horizontal + 10, vertical - 4),
            point(horizontal + 7, vertical),
        ],
    )
    for offset in (-3, 2, 6):
        pygame.draw.polygon(
            image,
            (206, 173, 90),
            [
                point(horizontal + offset - 3, vertical - 5),
                point(horizontal + offset, vertical - 10),
                point(horizontal + offset + 3, vertical - 5),
            ],
        )
    for index in range(4):
        progress = (phase + index / 4) % 1
        smoke = point(20 + math.sin(progress * 7 + index) * 2, 34 - progress * 21)
        pygame.draw.circle(
            overlay, (158, 171, 156, round((1 - progress) * 45)), smoke, round(2 + progress * 5)
        )
    soft_light(overlay, point(106, 83), 5, (242, 191, 91), 70 + 10 * math.sin(phase * math.tau))


def animate_airport(image, overlay, point, phase):
    center = point(106, 18)
    angle = phase * math.tau
    offset = pygame.Vector2(math.cos(angle) * 10, math.sin(angle) * 3)
    pygame.draw.line(
        image, (66, 89, 73), pygame.Vector2(center) - offset, pygame.Vector2(center) + offset, 4
    )
    pygame.draw.line(
        image, (169, 177, 131), pygame.Vector2(center) - offset, pygame.Vector2(center) + offset, 1
    )
    for index in range(8):
        for horizontal, vertical in (
            (11 + index * 8.2, 100 - index * 8.7),
            (30 + index * 8.2, 109 - index * 8.7),
        ):
            strength = 0.5 + 0.5 * math.sin(phase * math.tau - index * 0.9)
            soft_light(overlay, point(horizontal, vertical), 3, (248, 213, 140), 65 + strength * 90)
    soft_light(
        overlay,
        point(106, 30),
        4,
        (244, 94, 72),
        40 + 65 * max(0, math.sin(phase * math.tau * 2)) ** 8,
    )
    soft_light(overlay, point(49, 102), 3, (107, 194, 162), 35 + 35 * math.sin(phase * math.tau))
    flutter = math.sin(phase * math.tau * 2) * 2
    pygame.draw.polygon(
        image,
        (190, 116, 72),
        [point(120, 57), point(127, 59 + flutter), point(123, 61 + flutter * 0.5)],
    )


@lru_cache(maxsize=256)
def building_frame(key, frame, training=False):
    image = building_base(key).copy()
    phase = frame / ANIMATION_FRAMES
    overlay = pygame.Surface(image.get_size(), pygame.SRCALPHA)

    def point(horizontal, vertical):
        return building_point(key, (horizontal, vertical))

    if key == "mine":
        animate_mine(image, overlay, point, phase)
    elif key == "airport":
        animate_airport(image, overlay, point, phase)
    elif key == "barracks":
        animate_barracks(image, overlay, point, phase, training)
        for position in ((102, 57), (59, 77)):
            soft_light(
                overlay, point(*position), 4, (238, 200, 125), 40 + 7 * math.sin(phase * math.tau)
            )
    image.blit(overlay, (0, 0))
    return image
