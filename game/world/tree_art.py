import math
import random

import pygame


def tree_image(style, radius, shade):
    scale = 3
    image = pygame.Surface((72 * scale, 100 * scale), pygame.SRCALPHA)
    detail = random.Random(9401 + style)

    def polygon(color, points):
        pygame.draw.polygon(image, color, [(round(x * scale), round(y * scale)) for x, y in points])

    def line(color, start, end, width):
        pygame.draw.line(image, color, (start[0] * scale, start[1] * scale), (end[0] * scale, end[1] * scale), max(1, round(width * scale)))

    def ellipse(color, rectangle):
        pygame.draw.ellipse(image, color, tuple(round(value * scale) for value in rectangle))

    line((51, 49, 35), (36, 64), (36, 88), 4)
    line((118, 104, 66), (35, 65), (35, 87), 1)
    line((62, 61, 42), (36, 84), (31, 89), 1.5)
    line((62, 61, 42), (36, 84), (41, 89), 1.5)
    if style % 3 == 0:
        for spread, rise in ((radius, -12), (radius * .8, -25), (radius * .55, -37)):
            baseline = 88 + rise
            tip = baseline - 27
            edge = [(36, tip)]
            for step in range(1, 6):
                y = tip + step * 27 / 5
                edge.extend(((36 + spread * step / 5, y), (36 + spread * (step - .7) / 5, y + 1)))
            edge += [(36, baseline + 3)]
            for step in range(5, 0, -1):
                y = tip + step * 27 / 5
                edge.extend(((36 - spread * step / 5, y), (36 - spread * (step - .7) / 5, y - 1)))
            polygon((29 + shade, 61 + shade, 49 + shade), edge)
            polygon((58 + shade, 88 + shade, 58 + shade), [(36, tip), (36, baseline), (36 - spread, baseline)])
            for step in range(1, 6):
                y = tip + step * 4.5
                width = spread * step / 6
                line((77 + shade, 104 + shade, 66 + shade), (36 - width, y + 2), (35, y - 2), .7)
                line((38 + shade, 72 + shade, 53 + shade), (36, y), (36 + width * .8, y + 3), 1)
    else:
        palette = ((38, 66, 42), (54, 83, 48), (71, 98, 54), (94, 116, 66))
        for offset_x, offset_y, size in ((0, -23, radius), (-8, -30, radius - 3), (7, -31, radius - 4), (-3, -40, radius - 6)):
            x, y = 36 + offset_x, 88 + offset_y
            ellipse(tuple(value + shade for value in palette[0]), (x - size, y - size, size * 2, size * 1.85))
            for index in range(9):
                angle = index * math.tau / 9
                lobe = size * detail.uniform(.32, .48)
                cx = x + math.cos(angle) * size * .57
                cy = y + math.sin(angle) * size * .5
                tone = 2 if math.cos(angle) + math.sin(angle) < -.2 else 1
                ellipse(tuple(value + shade for value in palette[tone]), (cx - lobe, cy - lobe, lobe * 2, lobe * 1.7))
            ellipse(tuple(value + shade for value in palette[2]), (x - size * .65, y - size * .72, size * 1.15, size * 1.02))
            for _ in range(16):
                angle = detail.uniform(0, math.tau)
                distance = math.sqrt(detail.random()) * size * .65
                cx = x - 2 + math.cos(angle) * distance
                cy = y - 3 + math.sin(angle) * distance * .7
                leaf = detail.uniform(.8, 2.1)
                tone = 3 if cx + cy < x + y - 4 else 1
                ellipse(tuple(value + shade for value in palette[tone]), (cx, cy, leaf * 1.6, leaf))
    return pygame.transform.smoothscale(image, (72, 100)).convert_alpha()
