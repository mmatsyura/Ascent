from functools import lru_cache
import math

import pygame

from game.sprite_cache import prepared_sprite


@lru_cache(maxsize=512)
def condition_bars(health, readiness):
    image = pygame.Surface((40, 15), pygame.SRCALPHA)
    for offset, value, color in ((0, health, (113, 169, 112) if health > 35 else (195, 104, 75)), (6, readiness, (111, 154, 193))):
        area = pygame.Rect(2, offset + 2, 36, 4)
        pygame.draw.rect(image, (12, 22, 23), area.inflate(2, 2), border_radius=2)
        pygame.draw.rect(image, (45, 56, 48), area)
        fill = pygame.Rect(area.x + 1, area.y + 1, round(34 * value / 100), 2)
        if fill.w:
            pygame.draw.rect(image, color, fill)
            pygame.draw.line(image, tuple(min(255, channel + 35) for channel in color), fill.topleft, (fill.right - 1, fill.top))
    return prepared_sprite(image)


@lru_cache(maxsize=192)
def impact_image(size, phase):
    image = pygame.Surface((size, size), pygame.SRCALPHA)
    progress = phase / 23
    center = pygame.Vector2(size / 2, size / 2)
    radius = size * (.08 + progress * .28)
    for index in range(6):
        angle = index * 2.399
        offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * radius * .6
        smoke = max(1, round(radius * (.4 + index % 3 * .07)))
        location = center + offset + pygame.Vector2(progress * 3, -progress * 5)
        pygame.draw.circle(image, (76, 73, 61, round((1 - progress) * 85)), location, smoke)
    heat = max(0, 1 - progress * 1.8)
    if heat > 0:
        for scale, color, opacity in ((1.3, (227, 133, 55), 30), (.7, (255, 180, 72), 120), (.35, (255, 237, 171), 230)):
            pygame.draw.circle(image, (*color, round(opacity * heat)), center, max(1, round(radius * scale)))
    pygame.draw.circle(image, (207, 184, 137, round(80 * (1 - progress))), center, max(1, round(radius)), 1)
    for index in range(7):
        direction = pygame.Vector2(1, 0).rotate(index * 137.5)
        start = center + direction * radius * .65
        end = center + direction * radius * (1.1 + index % 3 * .16)
        pygame.draw.aaline(image, (248, 201, 128, round(200 * (1 - progress))), start, end)
    return prepared_sprite(image)


@lru_cache(maxsize=96)
def muzzle_image(size, angle_step):
    image = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    center = pygame.Vector2(size, size)
    direction = pygame.Vector2(1, 0).rotate(angle_step * 15)
    side = pygame.Vector2(-direction.y, direction.x)
    pygame.draw.circle(image, (249, 166, 63, 25), center, size)
    pygame.draw.circle(image, (255, 199, 91, 65), center, max(1, size // 2))
    points = [center - side * size * .2, center + direction * size * .9, center + side * size * .2, center - direction * size * .22]
    pygame.draw.polygon(image, (255, 218, 126, 240), points)
    pygame.draw.line(image, (255, 249, 207), center, center + direction * size * .45, max(1, size // 7))
    return prepared_sprite(image)
