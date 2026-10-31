from dataclasses import dataclass
from functools import lru_cache
import math
import random

import pygame


@dataclass
class Explosion:
    position: tuple
    variant: int
    age: float = 0


@lru_cache(maxsize=3)
def blast_details(variant):
    randomizer = random.Random(540 + variant)
    return tuple((randomizer.random() * math.tau, randomizer.uniform(.65, 1.2), randomizer.uniform(-1, 1)) for _ in range(20))


@lru_cache(maxsize=3)
def scorch_image(variant):
    image = pygame.Surface((128, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(image, (24, 29, 23, 60), (8, 15, 112, 35))
    pygame.draw.ellipse(image, (38, 36, 26, 80), (24, 22, 80, 22))
    for angle, length, _ in blast_details(variant):
        point = (round(64 + math.cos(angle) * 44 * length), round(32 + math.sin(angle) * 15 * length))
        pygame.draw.line(image, (37, 38, 28, 135), point, (point[0] + 3, point[1] + 1), 2)
    return image


@lru_cache(maxsize=96)
def blast_frame(frame, variant):
    time = frame / 20
    image = pygame.Surface((256, 256), pygame.SRCALPHA)
    center = pygame.Vector2(128, 158)
    flash = max(0, 1 - time / .45)
    if flash:
        for radius in range(72, 4, -6):
            pygame.draw.circle(image, (255, 195, 91, round(flash * (1 - radius / 80) * 65)), center, radius)
    ring = min(1, time / .85)
    if ring < 1:
        area = pygame.Rect(0, 0, max(4, round(ring * 192)), max(2, round(ring * 82)))
        area.center = center
        pygame.draw.ellipse(image, (238, 214, 158, round((1 - ring) * 165)), area, 2)
    for index, (angle, length, sideways) in enumerate(blast_details(variant)[:9]):
        age = max(0, time - index * .025)
        smoke = min(1, age / .7)
        radius = max(2, round((6 + smoke * 17 + age * 3) * length))
        position = center + pygame.Vector2(math.cos(angle) * (9 + age * 10), -age * (18 + index * 1.8) + math.sin(angle) * 10)
        opacity = round(min(1, age / .15) * max(0, 1 - age / 4.8) * 130)
        pygame.draw.circle(image, (51 + index * 2, 53 + index * 2, 46 + index * 2, opacity), position, radius)
    flame = max(0, 1 - time / 1.3)
    if flame:
        for index in range(6):
            angle = index * math.tau / 6 + variant
            reach = (6 + time * 25) * flame
            point = center + pygame.Vector2(math.cos(angle) * reach, math.sin(angle) * reach * .55 - time * 16)
            radius = max(1, round((8 + time * 30) * flame))
            pygame.draw.circle(image, (227, 89 + index * 10, 33, round(flame * 235)), point, radius)
            pygame.draw.circle(image, (253, 185 + index * 5, 91, round(flame * 245)), point - (0, 2), max(1, round(radius * .63)))
        pygame.draw.circle(image, (255, 241, 185, round(flash * 255)), center - (0, 3), max(1, round(21 * flash)))
    for index, (angle, speed, side) in enumerate(blast_details(variant)):
        lifetime = .7 + speed * .6
        if time > lifetime:
            continue
        movement = pygame.Vector2(math.cos(angle) * 86 * speed * time, math.sin(angle) * 47 * speed * time - 36 * time + 35 * time * time)
        point = center + movement
        tail = point - pygame.Vector2(math.cos(angle) * 7, math.sin(angle) * 3)
        opacity = round((1 - time / lifetime) * 230)
        pygame.draw.line(image, (249, 196, 103, opacity), point, tail, 2 if index % 4 == 0 else 1)
    return image


def draw_explosions(screen, camera, explosions):
    visible = screen.get_rect().inflate(300, 340)
    for explosion in explosions:
        center = camera.world_to_screen(explosion.position)
        if not visible.collidepoint(center):
            continue
        scale = max(.4, camera.zoom)
        scorch = pygame.transform.smoothscale(scorch_image(explosion.variant), (max(1, round(70 * scale)), max(1, round(35 * scale))))
        if explosion.age > 18:
            scorch.set_alpha(round(max(0, 20 - explosion.age) / 2 * 255))
        screen.blit(scorch, scorch.get_rect(center=(round(center.x), round(center.y))))
        if explosion.age < 4.8:
            image = blast_frame(min(95, int(explosion.age * 20)), explosion.variant)
            size = max(32, round(142 * scale))
            image = pygame.transform.smoothscale(image, (size, size))
            screen.blit(image, (round(center.x - size / 2), round(center.y - size * 158 / 256)))
