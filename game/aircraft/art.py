from functools import lru_cache
import math

import pygame

from game.ui.hud_icons import IconCanvas
from game.aircraft.flamingo_art import draw_flamingo


def rotor(canvas, center, radius, phase):
    horizontal, vertical = center
    canvas.ellipse((153, 181, 169, 30), (horizontal - radius, vertical - radius, radius * 2, radius * 2))
    angle = phase / 8 * math.tau
    for side in (-1, 1):
        tip = (horizontal + math.cos(angle) * radius * side, vertical + math.sin(angle) * radius * side)
        canvas.line((129, 151, 140, 150), center, tip, 2)
    canvas.ellipse((37, 59, 55), (horizontal - 2, vertical - 2, 4, 4))


@lru_cache(maxsize=40)
def drone_source(key, phase=0):
    canvas = IconCanvas(128)
    if key == "flamingo":
        draw_flamingo(canvas, phase)
    elif key == "kamikaze":
        rotor(canvas, (64, 101), 13, phase)
        canvas.polygon((48, 65, 53), [(64, 17), (111, 94), (95, 99), (70, 83), (64, 110), (58, 83), (32, 99), (17, 94)])
        canvas.polygon((139, 151, 105), [(64, 14), (108, 91), (95, 94), (69, 79), (64, 104), (59, 79), (33, 94), (20, 91)])
        canvas.polygon((176, 179, 124), [(64, 14), (69, 79), (64, 104), (59, 79)])
        canvas.polygon((105, 128, 88), [(48, 55), (59, 45), (58, 76), (33, 91)])
        canvas.polygon((100, 121, 84), [(74, 44), (88, 65), (94, 91), (70, 78)])
        canvas.line((206, 207, 150), (64, 20), (64, 75), 1)
        canvas.polygon((42, 69, 73), [(60, 25), (64, 17), (68, 25), (67, 33), (61, 33)])
        canvas.line((57, 92, 107), (28, 88), (43, 81), 2)
        canvas.line((191, 170, 105), (85, 82), (97, 89), 1)
    elif key == "p1_sun":
        rotor(canvas, (64, 98), 11, phase)
        for horizontal in (43, 82):
            canvas.line((62, 85, 83), (horizontal, 52), (horizontal, 106), 4)
            canvas.line((166, 184, 171), (horizontal - 1, 54), (horizontal - 1, 104), 1)
        canvas.polygon((100, 129, 133), [(19, 55), (59, 43), (63, 18), (68, 43), (110, 55), (108, 66), (69, 62), (67, 92), (61, 92), (57, 62), (20, 66)])
        canvas.polygon((191, 203, 178), [(20, 53), (59, 42), (63, 14), (67, 42), (109, 53), (108, 61), (68, 57), (67, 87), (60, 87), (58, 57), (20, 61)])
        for horizontal in (26, 83):
            canvas.polygon((46, 82, 97), [(horizontal, 53), (horizontal + 19, 48), (horizontal + 20, 58), (horizontal, 60)])
            for offset in (5, 11, 17):
                canvas.line((97, 137, 147), (horizontal + offset, 52), (horizontal + offset, 58), 1)
        canvas.polygon((154, 177, 165), [(34, 100), (92, 100), (94, 106), (34, 108)])
        canvas.line((57, 105, 131), (43, 98), (43, 108), 4)
        canvas.line((57, 105, 131), (83, 98), (83, 108), 4)
        canvas.ellipse((31, 61, 72), (59, 20, 9, 13))
        canvas.line((230, 223, 173), (61, 38), (61, 70), 1)
        canvas.ellipse((36, 60, 57), (58, 77, 11, 10))
        canvas.ellipse((119, 179, 187), (61, 79, 5, 5))
    else:
        for horizontal, vertical in ((29, 31), (99, 31), (29, 96), (99, 96)):
            canvas.line((42, 65, 61), (64, 65), (horizontal, vertical), 8)
            canvas.line((122, 145, 128), (64, 62), (horizontal, vertical - 2), 3)
            rotor(canvas, (horizontal, vertical), 22, phase)
        canvas.polygon((37, 59, 57), [(49, 40), (78, 40), (86, 64), (76, 90), (51, 90), (43, 64)])
        canvas.polygon((133, 155, 125), [(50, 38), (77, 38), (84, 61), (75, 84), (53, 84), (45, 61)])
        canvas.polygon((174, 185, 144), [(50, 38), (64, 35), (64, 80), (53, 82), (45, 61)])
        canvas.polygon((59, 86, 78), [(57, 46), (71, 46), (74, 62), (55, 62)])
        canvas.line((54, 111, 151), (51, 65), (51, 75), 3)
        canvas.ellipse((24, 44, 47), (55, 78, 17, 15))
        canvas.ellipse((89, 159, 174), (60, 82, 8, 8))
        for horizontal in (50, 77):
            canvas.line((57, 78, 61), (horizontal, 75), (horizontal - 4, 93), 2)
    return canvas.surface.convert_alpha()


@lru_cache(maxsize=40)
def flight_source(key, phase=0, wreck=False):
    original = drone_source(key, 0 if wreck else phase)
    if wreck:
        original = original.copy()
        damage = pygame.Rect(80 * 3, 35 * 3, 45 * 3, 45 * 3)
        fragment = original.subsurface(damage).copy()
        original.fill((0, 0, 0, 0), damage)
        original.blit(fragment, damage.move(12 * 3, 15 * 3))
    return pygame.transform.smoothscale(original, (144, 144))


@lru_cache(maxsize=256)
def drone_frame(key, heading, phase=0, wreck=False):
    radians = math.radians(heading)
    view_angle = math.degrees(math.atan2(math.sin(radians) * .7, math.cos(radians)))
    source = pygame.transform.rotate(flight_source(key, phase, wreck), -view_angle)
    source = pygame.transform.smoothscale(source, (source.get_width(), max(1, round(source.get_height() * .7))))
    image = pygame.Surface((192, 192), pygame.SRCALPHA)
    if wreck:
        source = source.copy()
        source.fill((102, 109, 96, 255), special_flags=pygame.BLEND_RGBA_MULT)
    image.blit(source, source.get_rect(center=(96, 97)))
    image.blit(source, source.get_rect(center=(96, 95)))
    return image


@lru_cache(maxsize=512)
def drone_sprite(key, size, heading, phase=0, selected=False, wreck=False):
    image = pygame.transform.smoothscale(drone_frame(key, heading, phase, wreck), (size, size))
    if selected and not wreck:
        image.fill((192, 212, 202, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return image


@lru_cache(maxsize=32)
def drone_icon(key, size=64):
    image = pygame.Surface((size, size), pygame.SRCALPHA)
    source = drone_sprite(key, max(32, round(size * 1.32)), 35, 0)
    image.blit(source, source.get_rect(center=(size // 2, size // 2)))
    return image


@lru_cache(maxsize=64)
def drone_badge(key, size, selected=False):
    image = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    pygame.draw.circle(image, (11, 29, 33), (center, center), center - 1)
    pygame.draw.circle(image, (114, 171, 170), (center, center), center - 2, 1)
    image.blit(drone_icon(key, size), (0, 0))
    if selected:
        image.fill((184, 211, 202, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return image
