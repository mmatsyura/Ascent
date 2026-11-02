from functools import lru_cache
import math

import pygame

from game.rendering import prepared_sprite


@lru_cache(maxsize=1)
def badge_background():
    image = pygame.Surface((160, 160), pygame.SRCALPHA)
    pygame.draw.circle(image, (7, 15, 23, 100), (80, 84), 75)
    pygame.draw.circle(image, (26, 33, 36), (80, 78), 74)
    pygame.draw.circle(image, (175, 165, 123), (80, 78), 72)
    pygame.draw.circle(image, (61, 71, 66), (80, 79), 70)
    pygame.draw.circle(image, (13, 29, 41), (80, 78), 67)
    for radius in range(64, 0, -1):
        progress = 1 - radius / 64
        color = (round(30 + progress * 12), round(61 + progress * 24), round(82 + progress * 29))
        pygame.draw.circle(image, color, (80, 76), radius)
    pygame.draw.arc(image, (231, 216, 165), (9, 7, 142, 142), 0.3, 2.8, 2)
    pygame.draw.arc(image, (91, 122, 136), (17, 13, 126, 126), 0.35, 2.7, 2)
    for angle in (45, 135, 225, 315):
        horizontal = round(80 + math.cos(math.radians(angle)) * 70)
        vertical = round(78 + math.sin(math.radians(angle)) * 70)
        pygame.draw.circle(image, (26, 33, 33), (horizontal, vertical + 1), 3)
        pygame.draw.circle(image, (205, 188, 141), (horizontal, vertical), 2)
    return image


def rifle(image, origin, angle=0, scale=1):
    origin = pygame.Vector2(origin)

    def point(horizontal, vertical):
        return origin + pygame.Vector2(horizontal, vertical).rotate(angle) * scale

    def line(color, start, end, width):
        pygame.draw.line(image, color, point(*start), point(*end), max(1, round(width * scale)))

    line((29, 35, 35), (-17, 0), (25, 0), 7)
    line((77, 83, 74), (-8, -3), (14, -3), 3)
    line((19, 25, 27), (23, -1), (45, -1), 3)
    line((24, 30, 30), (40, -5), (40, -1), 2)
    line((33, 39, 37), (-19, 0), (-28, 7), 7)
    line((27, 33, 32), (2, 3), (5, 15), 5)
    line((27, 33, 32), (-10, 3), (-13, 11), 4)
    line((16, 22, 23), (0, -7), (11, -7), 4)


def helmet(image, center, back=False):
    horizontal, vertical = center
    pygame.draw.ellipse(image, (29, 39, 33), (horizontal - 17, vertical - 17, 35, 29))
    pygame.draw.ellipse(image, (102, 115, 74), (horizontal - 15, vertical - 17, 31, 24))
    pygame.draw.ellipse(image, (128, 136, 87), (horizontal - 12, vertical - 15, 15, 10))
    pygame.draw.polygon(
        image,
        (68, 84, 53),
        [
            (horizontal + 2, vertical - 14),
            (horizontal + 13, vertical - 10),
            (horizontal + 15, vertical + 2),
            (horizontal + 4, vertical),
        ],
    )
    pygame.draw.line(
        image, (42, 53, 42), (horizontal - 16, vertical + 4), (horizontal + 17, vertical + 4), 4
    )
    if not back:
        pygame.draw.line(
            image, (39, 53, 51), (horizontal - 10, vertical + 7), (horizontal + 12, vertical + 7), 5
        )
        pygame.draw.line(
            image, (117, 146, 142), (horizontal - 8, vertical + 6), (horizontal, vertical + 6), 2
        )


@lru_cache(maxsize=192)
def soldier_source(selected=False, phase=0, facing="front", pose="stand"):
    image = pygame.Surface((112, 132), pygame.SRCALPHA)
    stride = math.sin(phase / 16 * math.tau) * 5
    bob = abs(math.sin(phase / 16 * math.tau)) * 1.2
    if pose == "prone":
        pygame.draw.ellipse(image, (15, 25, 22, 50), (5, 111, 101, 13))
        pygame.draw.lines(image, (51, 66, 47), False, [(45, 107), (28, 101), (15, 110)], 11)
        pygame.draw.lines(image, (79, 91, 56), False, [(44, 112), (27, 118), (10, 116)], 12)
        pygame.draw.line(image, (34, 40, 33), (10, 116), (4, 113), 7)
        pygame.draw.line(image, (40, 46, 36), (15, 110), (8, 106), 7)
        pygame.draw.line(image, (115, 121, 76), (38, 112), (27, 116), 4)
        pygame.draw.polygon(
            image, (82, 96, 58), [(35, 102), (59, 88), (75, 94), (68, 109), (42, 118)]
        )
        pygame.draw.ellipse(image, (48, 64, 44), (43, 88, 23, 20))
        pygame.draw.line(image, (112, 119, 75), (49, 93), (55, 106), 3)
        pygame.draw.polygon(image, (52, 67, 47), [(63, 94), (75, 96), (70, 110), (59, 109)])
        pygame.draw.lines(image, (79, 96, 58), False, [(69, 96), (84, 112), (94, 102)], 8)
        pygame.draw.lines(image, (104, 115, 71), False, [(60, 100), (65, 117), (78, 105)], 9)
        pygame.draw.line(image, (59, 137, 209), (62, 101), (64, 106), 3)
        pygame.draw.circle(image, (183, 153, 112), (74, 94), 8)
        helmet(image, (75, 83), facing == "back")
        rifle(image, (85, 102), -7, 0.58)
        pygame.draw.circle(image, (184, 157, 116), (77, 105), 3)
        pygame.draw.circle(image, (184, 157, 116), (94, 101), 3)
    else:
        crouching = pose == "kneel"
        top = 67 if crouching else 44 + bob
        hip = 94 if crouching else 88 + bob
        pygame.draw.ellipse(image, (15, 25, 22, 52), (22, 117, 65, 10))
        if crouching:
            pygame.draw.lines(image, (56, 72, 48), False, [(44, hip), (30, 106), (32, 120)], 12)
            pygame.draw.lines(image, (88, 100, 61), False, [(59, hip), (73, 105), (56, 120)], 12)
            feet = [(28, 122), (60, 122)]
        else:
            pygame.draw.line(image, (52, 68, 47), (44, hip), (round(39 + stride), 119), 12)
            pygame.draw.line(image, (88, 100, 61), (59, hip), (round(65 - stride), 119), 12)
            pygame.draw.line(image, (115, 121, 76), (42, 97), (round(39 + stride * 0.5), 108), 4)
            feet = [(round(36 + stride), 122), (round(62 - stride), 122)]
        for horizontal, vertical in feet:
            pygame.draw.line(
                image, (31, 37, 30), (horizontal, vertical), (horizontal + 12, vertical), 7
            )
        torso = [(35, top + 3), (65, top), (72, hip), (35, hip + 3)]
        pygame.draw.polygon(image, (96, 108, 66), torso)
        pygame.draw.polygon(
            image, (65, 83, 48), [(36, top + 9), (47, top + 12), (43, top + 28), (35, top + 25)]
        )
        pygame.draw.polygon(
            image, (136, 136, 88), [(57, top + 7), (65, top + 5), (69, top + 23), (59, top + 21)]
        )
        pygame.draw.rect(
            image, (52, 67, 47), (42, round(top + 7), 23, round(hip - top - 10)), border_radius=4
        )
        pygame.draw.line(image, (126, 127, 81), (46, top + 5), (46, hip - 6), 3)
        pygame.draw.line(image, (126, 127, 81), (61, top + 5), (61, hip - 6), 3)
        for horizontal in (46, 54, 62):
            pygame.draw.rect(
                image, (105, 112, 68), (horizontal - 3, round(hip - 18), 6, 10), border_radius=1
            )
        if facing == "back":
            pygame.draw.rect(image, (69, 82, 47), (40, round(top + 5), 25, 28), border_radius=5)
            pygame.draw.rect(image, (98, 109, 65), (44, round(top + 10), 17, 18), border_radius=3)
        pygame.draw.lines(
            image, (104, 115, 71), False, [(35, top + 9), (28, top + 24), (45, top + 29)], 9
        )
        pygame.draw.lines(
            image, (79, 96, 58), False, [(67, top + 8), (77, top + 23), (68, top + 31)], 9
        )
        pygame.draw.line(image, (59, 137, 209), (32, top + 9), (28, top + 16), 4)
        pygame.draw.circle(image, (186, 159, 117), (46, round(top + 29)), 4)
        pygame.draw.circle(image, (186, 159, 117), (68, round(top + 31)), 4)
        pygame.draw.circle(image, (183, 153, 112), (53, round(top - 4)), 12)
        helmet(image, (53, round(top - 10)), facing == "back")
        rifle(image, (58, top + 27), -13 if crouching else 17, 0.79)
    if facing == "left":
        image = pygame.transform.flip(image, True, False)
    if selected:
        image.fill((192, 192, 192, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return image


@lru_cache(maxsize=1024)
def soldier_image(height, selected=False, phase=0, facing="front", pose="stand"):
    return prepared_sprite(
        pygame.transform.smoothscale(
            soldier_source(selected, phase, facing, pose),
            (max(8, round(height * 112 / 132)), height),
        ).convert_alpha()
    )


@lru_cache(maxsize=2)
def military_badge_source(selected=False):
    image = badge_background().copy()
    pygame.draw.polygon(
        image, (58, 75, 46), [(25, 120), (49, 88), (109, 87), (139, 123), (119, 141), (40, 141)]
    )
    pygame.draw.polygon(
        image, (100, 112, 69), [(34, 117), (53, 90), (74, 96), (68, 139), (41, 137)]
    )
    pygame.draw.rect(image, (44, 59, 42), (65, 95, 45, 42), border_radius=6)
    for horizontal in (71, 84, 97):
        pygame.draw.rect(image, (122, 128, 80), (horizontal, 116, 10, 18), border_radius=2)
    pygame.draw.circle(image, (187, 158, 114), (81, 72), 23)
    pygame.draw.polygon(image, (51, 65, 43), [(60, 76), (100, 76), (96, 94), (79, 101), (65, 91)])
    head = pygame.Surface((112, 70), pygame.SRCALPHA)
    helmet(head, (55, 33))
    head = pygame.transform.smoothscale(head, (179, 112))
    image.blit(head, (-8, 4))
    pygame.draw.line(image, (54, 136, 211), (48, 100), (41, 111), 6)
    rifle(image, (88, 113), -27, 1.05)
    pygame.draw.circle(image, (182, 155, 116), (73, 121), 6)
    pygame.draw.circle(image, (182, 155, 116), (109, 102), 6)
    if selected:
        image.fill((180, 180, 180, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return image


@lru_cache(maxsize=96)
def military_badge(size, selected=False):
    return prepared_sprite(
        pygame.transform.smoothscale(military_badge_source(selected), (size, size)).convert_alpha()
    )


def rifle_muzzle(phase, facing, pose, anti_tank=False):
    if anti_tank:
        point = pygame.Vector2(112 * 0.78, 132 * 0.25)
    elif pose == "prone":
        point = pygame.Vector2(85, 102) + pygame.Vector2(45, -1).rotate(-7) * 0.58
    else:
        top = 67 if pose == "kneel" else 44 + abs(math.sin(phase / 16 * math.tau)) * 1.2
        point = (
            pygame.Vector2(58, top + 27)
            + pygame.Vector2(45, -1).rotate(-13 if pose == "kneel" else 17) * 0.79
        )
    if facing == "left" and not anti_tank:
        point.x = 111 - point.x
    return pygame.Vector2((point.x - 56) / 132, point.y / 132 - 0.96)
