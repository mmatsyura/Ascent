import math

from game.ui.hud_icons import IconCanvas
from game.world.building_shapes import crate, ground_shadow


def fighter(canvas, center, scale=0.6):
    angle = math.radians(43)

    def point(horizontal, vertical):
        return (
            center[0] + (horizontal * math.cos(angle) - vertical * math.sin(angle)) * scale,
            center[1] + (horizontal * math.sin(angle) + vertical * math.cos(angle)) * scale,
        )

    outline = [
        (0, -31),
        (3, -10),
        (19, 8),
        (19, 13),
        (6, 7),
        (5, 21),
        (11, 28),
        (10, 31),
        (3, 27),
        (0, 33),
        (-3, 27),
        (-10, 31),
        (-11, 28),
        (-5, 21),
        (-6, 7),
        (-19, 13),
        (-19, 8),
        (-3, -10),
    ]
    vertices = [point(*vertex) for vertex in outline]
    canvas.polygon(
        (18, 34, 34, 85), [(horizontal + 2, vertical + 3) for horizontal, vertical in vertices]
    )
    canvas.polygon((123, 147, 151), vertices)
    canvas.polygon(
        (182, 196, 183),
        [point(*vertex) for vertex in ((0, -30), (3, -9), (2, 22), (0, 29), (-2, 22), (-3, -9))],
    )
    canvas.polygon(
        (40, 76, 91),
        [point(*vertex) for vertex in ((-3, -13), (0, -20), (3, -13), (2, -5), (-2, -5))],
    )
    canvas.line((213, 218, 192), point(0, -28), point(0, -21), 1)
    for side in (-1, 1):
        canvas.polygon(
            (62, 83, 88),
            [
                point(side * horizontal, vertical)
                for horizontal, vertical in ((4, 18), (8, 14), (7, 27), (4, 24))
            ],
        )
        canvas.line((189, 202, 181), point(side * 5, 1), point(side * 16, 10), 1)
        canvas.line((30, 46, 48), point(side * 3, 27), point(side * 3, 31), 2)


def hangar(canvas, horizontal, vertical):
    canvas.polygon(
        (51, 68, 54),
        [
            (horizontal, vertical),
            (horizontal + 3, vertical - 13),
            (horizontal + 12, vertical - 22),
            (horizontal + 30, vertical - 15),
            (horizontal + 35, vertical - 1),
            (horizontal + 19, vertical + 10),
        ],
    )
    canvas.polygon(
        (105, 120, 86),
        [
            (horizontal, vertical),
            (horizontal + 3, vertical - 13),
            (horizontal + 12, vertical - 22),
            (horizontal + 30, vertical - 15),
            (horizontal + 20, vertical - 5),
            (horizontal + 17, vertical + 7),
        ],
    )
    for offset in (5, 11, 17):
        canvas.line(
            (81, 100, 72),
            (horizontal + offset, vertical - 12),
            (horizontal + offset + 8, vertical - 19 + offset * 0.14),
            1,
        )
    canvas.polygon(
        (58, 75, 61),
        [
            (horizontal, vertical),
            (horizontal + 10, vertical - 10),
            (horizontal + 17, vertical - 7),
            (horizontal + 19, vertical + 10),
        ],
    )
    canvas.polygon(
        (17, 34, 33),
        [
            (horizontal + 3, vertical),
            (horizontal + 10, vertical - 7),
            (horizontal + 14, vertical - 5),
            (horizontal + 15, vertical + 6),
        ],
    )
    canvas.line((164, 171, 124), (horizontal, vertical), (horizontal + 10, vertical - 10), 1)
    canvas.line(
        (164, 171, 124), (horizontal + 10, vertical - 10), (horizontal + 17, vertical - 7), 1
    )


def airport_shape():
    canvas = IconCanvas(128)
    ground_shadow(canvas, (3, 104, 122, 21))
    canvas.polygon((105, 117, 82), [(3, 96), (72, 23), (125, 49), (124, 93), (94, 123), (25, 119)])
    canvas.polygon(
        (79, 96, 74), [(4, 97), (28, 111), (94, 122), (124, 92), (124, 97), (94, 126), (24, 122)]
    )
    canvas.polygon((66, 79, 71), [(9, 98), (75, 28), (96, 38), (29, 110)])
    canvas.polygon((53, 68, 63), [(12, 98), (76, 31), (91, 39), (28, 106)])
    canvas.line((193, 195, 154), (13, 97), (76, 32), 1)
    canvas.line((157, 175, 154), (28, 105), (90, 40), 1)
    for horizontal, vertical in ((25, 91), (36, 80), (47, 69), (58, 58), (69, 47)):
        canvas.line((219, 220, 191), (horizontal, vertical), (horizontal + 4, vertical - 4), 1)
    for horizontal, vertical in ((16, 96), (19, 98), (22, 100), (76, 34), (79, 36), (82, 38)):
        canvas.line((223, 220, 184), (horizontal, vertical), (horizontal + 6, vertical - 6), 1)
    canvas.polygon((130, 138, 105), [(43, 93), (85, 48), (120, 63), (81, 112)])
    for offset in (0, 12, 24):
        canvas.line(
            (111, 123, 96), (48 + offset, 94 + offset * 0.35), (87 + offset, 53 + offset * 0.35), 1
        )
    for offset in (0, 12, 24):
        canvas.line((111, 123, 96), (51 + offset, 82 - offset), (85 + offset, 95 - offset), 1)
    canvas.line((201, 181, 109), (36, 97), (69, 62), 1)
    canvas.line((201, 181, 109), (69, 62), (86, 68), 1)
    hangar(canvas, 89, 67)
    hangar(canvas, 71, 91)
    canvas.polygon((142, 146, 110), [(94, 43), (106, 36), (115, 40), (104, 49)])
    canvas.polygon((98, 113, 90), [(94, 43), (104, 49), (104, 69), (94, 63)])
    canvas.polygon((72, 93, 76), [(104, 49), (115, 40), (115, 60), (104, 69)])
    canvas.polygon((51, 72, 65), [(91, 38), (104, 29), (119, 35), (106, 46)])
    canvas.polygon((119, 163, 159), [(92, 38), (106, 45), (106, 53), (92, 46)])
    canvas.polygon((53, 103, 116), [(106, 45), (118, 35), (118, 43), (106, 53)])
    canvas.line((186, 199, 161), (92, 38), (106, 45), 1)
    canvas.line((71, 95, 84), (99, 41), (99, 49), 1)
    canvas.line((173, 184, 144), (106, 30), (106, 19), 1)
    canvas.ellipse((111, 129, 103), (101, 15, 10, 6))
    canvas.ellipse((155, 164, 121), (103, 16, 6, 3))
    fighter(canvas, (55, 94), 0.62)
    crate(canvas, (106, 91), 6)
    crate(canvas, (112, 87), 6)
    canvas.line((87, 106, 85), (120, 63), (123, 65), 2)
    canvas.line((151, 160, 118), (120, 63), (120, 57), 1)
    canvas.polygon((191, 113, 69), [(120, 57), (127, 59), (123, 61)])
    for horizontal, vertical in ((33, 115), (93, 120), (123, 97)):
        canvas.line((85, 104, 77), (horizontal, vertical), (horizontal, vertical - 6), 1)
    return canvas.surface.convert_alpha()
