import pygame

from game.ui.hud_icons import IconCanvas, create_hud_icons
from game.world.soldier_art import helmet, rifle


def construction_icon():
    canvas = IconCanvas()
    canvas.line((81, 64, 39), (7, 34), (7, 5), 3)
    canvas.line((213, 175, 99), (6, 5), (32, 5), 3)
    canvas.line((184, 149, 83), (7, 6), (20, 14), 1)
    canvas.line((165, 161, 132), (30, 6), (30, 16))
    canvas.polygon((128, 145, 145), [(12, 21), (25, 15), (36, 21), (24, 28)])
    canvas.polygon((84, 106, 110), [(12, 21), (24, 28), (24, 37), (12, 30)])
    canvas.polygon((53, 78, 88), [(24, 28), (36, 21), (36, 31), (24, 37)])
    canvas.line((209, 219, 203), (13, 21), (25, 16))
    canvas.polygon((33, 49, 53), [(27, 29), (32, 26), (32, 33), (27, 36)])
    canvas.line((217, 180, 104), (3, 37), (11, 37), 2)
    return canvas.finish()


def recruit_icon():
    surface = pygame.Surface((120, 120), pygame.SRCALPHA)
    pygame.draw.polygon(surface, (58, 75, 46), [(15, 112), (32, 73), (85, 72), (110, 112)])
    pygame.draw.rect(surface, (44, 59, 42), (47, 77, 35, 35), border_radius=5)
    pygame.draw.circle(surface, (187, 158, 114), (61, 57), 18)
    helmet(surface, (61, 46))
    rifle(surface, (69, 92), -23, .85)
    pygame.draw.line(surface, (65, 146, 216), (32, 81), (27, 94), 5)
    return pygame.transform.smoothscale(surface, (40, 40))


def army_icon():
    canvas = IconCanvas()
    canvas.polygon((165, 150, 104), [(7, 5), (20, 2), (33, 5), (32, 25), (20, 38), (8, 25)])
    canvas.polygon((37, 68, 88), [(10, 7), (20, 5), (30, 7), (29, 24), (20, 33), (11, 24)])
    for vertical in (11, 18, 25):
        canvas.line((225, 199, 139), (15, vertical), (20, vertical + 4), 2)
        canvas.line((225, 199, 139), (20, vertical + 4), (25, vertical), 2)
    return canvas.finish()


def information_icon():
    canvas = IconCanvas()
    for radius in (17, 11, 5):
        canvas.ellipse((112, 154, 157), (20 - radius, 20 - radius, radius * 2, radius * 2), 1)
    canvas.line((195, 181, 129), (20, 3), (20, 37))
    canvas.line((195, 181, 129), (3, 20), (37, 20))
    canvas.polygon((49, 97, 113), [(20, 20), (33, 8), (37, 20)])
    canvas.line((233, 208, 138), (20, 20), (32, 8), 2)
    canvas.ellipse((234, 215, 157), (25, 10, 5, 5))
    canvas.ellipse((99, 164, 191), (11, 27, 4, 4))
    return canvas.finish()


def create_command_icons():
    resources = create_hud_icons()
    return {
        **resources,
        "build": construction_icon(),
        "recruit": recruit_icon(),
        "army": army_icon(),
        "information": information_icon(),
    }
