from functools import lru_cache
import math

import pygame

from game.rendering import RenderPart
from game.world.building_art import building_base, building_layout
from game.world.buildings import BUILDINGS_BY_KEY


@lru_cache(maxsize=100)
def construction_frame(key, stage):
    progress = stage / 32
    image = pygame.Surface(building_base(key).get_size(), pygame.SRCALPHA)
    _, anchor, _ = building_layout(key)
    center = pygame.Vector2(anchor) * 2
    width, depth = BUILDINGS_BY_KEY[key].footprint
    foundation = [(center.x, center.y - depth * .55), (center.x + width * .85, center.y),
                  (center.x, center.y + depth * .55), (center.x - width * .85, center.y)]
    pygame.draw.polygon(image, (65, 67, 47, 90), [(x, y + 5) for x, y in foundation])
    pygame.draw.polygon(image, (132, 127, 98), foundation)
    pygame.draw.lines(image, (81, 85, 65), True, foundation, 3)
    for step in range(1, 5):
        fraction = step / 5
        first = pygame.Vector2(foundation[0]).lerp(foundation[3], fraction)
        last = pygame.Vector2(foundation[1]).lerp(foundation[2], fraction)
        pygame.draw.line(image, (151, 145, 111), first, last, 1)
    if progress > .12:
        finished = building_base(key)
        bounds = finished.get_bounding_rect(min_alpha=20)
        reveal = min(1, (progress - .12) / .85)
        top = bounds.bottom - round(bounds.h * reveal)
        visible = pygame.Rect(0, top, finished.get_width(), finished.get_height() - top)
        image.blit(finished, visible, visible)
    scaffold = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    height = min(image.get_height() * .65, 24 + progress * image.get_height() * .6)
    left, right = foundation[3], foundation[1]
    posts = [left, pygame.Vector2(left).lerp(foundation[2], .55), foundation[2], pygame.Vector2(foundation[2]).lerp(right, .65), right]
    opacity = round(255 * min(1, (1 - progress) / .12))
    for x, y in posts:
        pygame.draw.line(scaffold, (111, 94, 58, opacity), (x, y), (x, y - height), 4)
        pygame.draw.line(scaffold, (172, 148, 91, opacity), (x - 1, y), (x - 1, y - height), 1)
    for level in (.25, .65):
        points = [(x, y - height * level) for x, y in posts]
        pygame.draw.lines(scaffold, (134, 113, 69, opacity), False, points, 3)
    for first, last in zip(posts, posts[1:]):
        pygame.draw.line(scaffold, (96, 98, 76, opacity), (first[0], first[1] - height * .24), (last[0], last[1] - height * .65), 2)
    image.blit(scaffold, (0, 0))
    for index in range(3):
        x, y = center.x - width * .66 + index * 7, center.y + depth * .30 + index * 3
        pygame.draw.polygon(image, (121, 96, 58), [(x, y), (x + 23, y - 9), (x + 23, y - 4), (x, y + 5)])
        pygame.draw.line(image, (188, 155, 91), (x, y), (x + 22, y - 9), 2)
    crate = pygame.Rect(round(center.x + width * .50), round(center.y + depth * .08), 16, 13)
    pygame.draw.rect(image, (126, 106, 66), crate)
    pygame.draw.rect(image, (83, 79, 52), crate, 2)
    pygame.draw.line(image, (182, 152, 92), crate.topleft, crate.bottomright, 2)
    return image


@lru_cache(maxsize=256)
def worker_image(height, phase, walking=False, left=False, variant=0):
    image = pygame.Surface((80, 120), pygame.SRCALPHA)
    stride = math.sin(phase / 16 * math.tau) * 6 if walking else 0
    bob = abs(math.sin(phase / 16 * math.tau)) * 1.5 if walking else 0
    pygame.draw.ellipse(image, (18, 27, 24, 40), (16, 108, 54, 9))
    for x, offset in ((29, stride), (49, -stride)):
        pygame.draw.line(image, (47, 65, 68), (x, 78), (x + offset, 106), 11)
        pygame.draw.line(image, (31, 40, 38), (x + offset - 3, 110), (x + offset + 8, 110), 7)
    pygame.draw.polygon(image, (69, 92, 96), [(23, 44 + bob), (52, 44 + bob), (59, 82), (23, 83)])
    pygame.draw.polygon(image, (185, 121, 53), [(24, 45 + bob), (34, 43 + bob), (38, 82), (23, 82)])
    pygame.draw.polygon(image, (211, 153, 67), [(44, 43 + bob), (53, 45 + bob), (58, 81), (42, 82)])
    pygame.draw.line(image, (217, 215, 151), (24, 67), (55, 67), 4)
    pygame.draw.circle(image, (184, 151, 107), (38, round(36 + bob)), 11)
    pygame.draw.ellipse(image, (219, 184, 84) if variant % 2 == 0 else (193, 132, 61), (23, round(18 + bob), 32, 24))
    pygame.draw.line(image, (235, 207, 121), (22, 36 + bob), (57, 36 + bob), 4)
    pygame.draw.line(image, (156, 122, 59), (39, 20 + bob), (39, 33 + bob), 2)
    if walking:
        pygame.draw.line(image, (86, 103, 96), (25, 49), (18, 70 + stride), 8)
        pygame.draw.line(image, (184, 151, 107), (18, 70 + stride), (29, 74 + stride), 5)
        pygame.draw.line(image, (145, 115, 66), (16, 65), (69, 48), 8)
        pygame.draw.line(image, (198, 168, 105), (16, 62), (69, 45), 2)
    else:
        swing = math.sin(phase / 16 * math.tau)
        hand = (65, 61 - swing * 17)
        pygame.draw.lines(image, (79, 99, 96), False, [(51, 48), (61, 52), hand], 8)
        pygame.draw.circle(image, (184, 151, 107), hand, 4)
        pygame.draw.line(image, (131, 107, 66), hand, (hand[0] + 8, hand[1] - 15), 4)
        pygame.draw.line(image, (92, 103, 99), (hand[0] + 3, hand[1] - 17), (hand[0] + 14, hand[1] - 12), 6)
        if phase in (5, 6):
            pygame.draw.line(image, (214, 188, 115, 180), (68, 79), (73, 75), 2)
    if left:
        image = pygame.transform.flip(image, True, False)
    return pygame.transform.smoothscale(image, (max(8, round(height * 80 / 120)), height))


def builder_parts(building, camera):
    width, height = building.definition.footprint
    half_width, half_height = width / 2 + 14, height / 2 + 13
    corners = [(-half_width, -half_height), (half_width, -half_height), (half_width, half_height), (-half_width, half_height)]
    parts = []
    for index in range(4):
        clock = building.animation_time + index * 7.1
        segment = int(clock / 8) % 4
        progress = (clock / 8) % 1
        walking = progress < .4 or building.completed
        first, last = pygame.Vector2(corners[segment]), pygame.Vector2(corners[(segment + 1) % 4])
        fraction = min(1, progress / .4)
        position = last if not walking else first.lerp(last, fraction * fraction * (3 - 2 * fraction))
        if building.completed:
            position += position.normalize() * (1.8 - building.builder_departure) * 14
        position += pygame.Vector2(building.position)
        image = worker_image(max(12, round(26 * camera.zoom)), int(clock * (4 if walking else 6)) % 16, walking, last.x < first.x, index % 2)
        if building.completed:
            image = image.copy()
            image.set_alpha(round(255 * min(1, building.builder_departure / 1.2)))
        screen_position = camera.world_to_screen(position)
        rectangle = image.get_rect(midbottom=(round(screen_position.x), round(screen_position.y)))
        parts.append(RenderPart(position.y, image, rectangle))
    return parts
