from game.ui.hud_icons import IconCanvas
from game.world.building_shapes import crate, ground_shadow


def barracks_block(canvas, horizontal, vertical, width=48):
    canvas.polygon(
        (157, 150, 107),
        [
            (horizontal, vertical),
            (horizontal + width, vertical + 17),
            (horizontal + width, vertical + 37),
            (horizontal, vertical + 20),
        ],
    )
    canvas.polygon(
        (105, 120, 88),
        [
            (horizontal + width, vertical + 17),
            (horizontal + width + 17, vertical + 4),
            (horizontal + width + 17, vertical + 24),
            (horizontal + width, vertical + 37),
        ],
    )
    canvas.polygon(
        (87, 108, 77),
        [
            (horizontal - 2, vertical - 1),
            (horizontal + 8, vertical - 15),
            (horizontal + width + 20, vertical + 3),
            (horizontal + width + 1, vertical + 19),
        ],
    )
    canvas.polygon(
        (112, 130, 89),
        [
            (horizontal - 2, vertical - 1),
            (horizontal + 8, vertical - 15),
            (horizontal + width + 20, vertical + 3),
            (horizontal + width + 10, vertical + 4),
        ],
    )
    canvas.line(
        (165, 173, 122), (horizontal + 8, vertical - 15), (horizontal + width + 20, vertical + 3), 1
    )
    canvas.line((53, 75, 59), (horizontal, vertical), (horizontal + width, vertical + 17), 2)
    for offset in range(5, width - 2, 10):
        top = vertical + offset * 17 / width + 5
        canvas.polygon(
            (42, 69, 64),
            [
                (horizontal + offset, top),
                (horizontal + offset + 6, top + 2),
                (horizontal + offset + 6, top + 9),
                (horizontal + offset, top + 7),
            ],
        )
        canvas.line(
            (167, 178, 139), (horizontal + offset, top), (horizontal + offset + 6, top + 2), 1
        )
        canvas.line(
            (106, 133, 115),
            (horizontal + offset + 3, top + 1),
            (horizontal + offset + 3, top + 8),
            1,
        )
    canvas.line(
        (119, 124, 86), (horizontal + 2, vertical + 18), (horizontal + width - 2, vertical + 34), 2
    )
    canvas.polygon(
        (39, 60, 50),
        [
            (horizontal + width + 5, vertical + 16),
            (horizontal + width + 12, vertical + 11),
            (horizontal + width + 12, vertical + 25),
            (horizontal + width + 5, vertical + 30),
        ],
    )
    canvas.line(
        (191, 177, 118),
        (horizontal + width + 4, vertical + 16),
        (horizontal + width + 12, vertical + 10),
        1,
    )


def barracks_shape():
    canvas = IconCanvas(128)
    ground_shadow(canvas, (3, 101, 122, 23))
    canvas.polygon((129, 134, 94), [(3, 82), (49, 50), (122, 76), (124, 99), (84, 125), (7, 104)])
    canvas.polygon(
        (113, 122, 86), [(7, 104), (84, 125), (124, 99), (123, 105), (84, 128), (7, 109)]
    )
    canvas.polygon((148, 149, 111), [(38, 79), (67, 65), (115, 82), (85, 108)])
    for offset in (0, 12, 24):
        canvas.line(
            (127, 134, 100), (48 + offset, 83 + offset * 0.35), (72 + offset, 69 + offset * 0.35), 1
        )
    barracks_block(canvas, 48, 40, 44)
    barracks_block(canvas, 7, 62, 43)
    canvas.polygon((79, 97, 68), [(56, 103), (61, 99), (67, 101), (62, 106)])
    canvas.line((56, 75, 60), (61, 102), (61, 48), 2)
    canvas.line((185, 184, 135), (60, 102), (60, 48), 1)
    canvas.ellipse((225, 205, 140), (58, 46, 4, 4))
    canvas.polygon((46, 101, 159), [(62, 49), (79, 54), (76, 65), (62, 60)])
    canvas.line((119, 170, 205), (63, 50), (78, 54), 1)
    crate(canvas, (103, 94), 7)
    crate(canvas, (110, 88), 7)
    for horizontal, vertical in ((84, 110), (94, 104)):
        canvas.line((73, 87, 65), (horizontal - 3, vertical + 2), (horizontal, vertical - 9), 2)
        canvas.line((73, 87, 65), (horizontal + 4, vertical + 4), (horizontal, vertical - 9), 1)
        canvas.ellipse((177, 166, 115), (horizontal - 3, vertical - 14, 7, 9))
        canvas.ellipse((78, 93, 69), (horizontal - 1, vertical - 12, 3, 5))
    canvas.line((92, 107, 76), (10, 111), (47, 123), 2)
    for horizontal, vertical in ((10, 111), (28, 117), (47, 123)):
        canvas.line((99, 112, 80), (horizontal, vertical), (horizontal, vertical - 6), 1)
    return canvas.surface.convert_alpha()
