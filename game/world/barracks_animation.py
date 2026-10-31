import math

import pygame

from game.world.soldier_art import soldier_image


def animate_barracks(image, overlay, point, phase, training):
    wave = math.sin(phase * math.tau)
    flag = [point(62, 49), point(70, 51 + wave * .7), point(79, 54 + wave * 1.5), point(76, 65 + wave), point(69, 62 - wave * .6), point(62, 60)]
    pygame.draw.polygon(image, (47, 107, 169), flag)
    pygame.draw.polygon(image, (34, 81, 137), (flag[1], flag[2], flag[3], flag[4]))
    pygame.draw.lines(image, (125, 176, 209), False, flag[:3], 1)
    if not training:
        return
    for index in range(3):
        progress = (phase + index / 3) % 1
        path = progress * 2 if progress < .5 else (1 - progress) * 2
        position = point(72 + path * 22, 92 - path * 13)
        facing = "back" if progress < .5 else "front"
        height = max(12, round((point(0, 13)[1] - point(0, 0)[1])))
        soldier = soldier_image(height, False, int(phase * 32 + index * 4) % 16, facing, "stand")
        image.blit(soldier, soldier.get_rect(midbottom=position))
    for index in range(3):
        opacity = round(45 + 20 * math.sin(phase * math.tau + index))
        pygame.draw.circle(overlay, (176, 159, 111, opacity), point(78 + index * 6, 100 - index * 3), 3)
