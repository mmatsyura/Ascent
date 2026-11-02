import pygame


class IconCanvas:
    def __init__(self, size=40):
        self.scale = 3
        self.size = size
        self.surface = pygame.Surface((size * self.scale, size * self.scale), pygame.SRCALPHA)

    def polygon(self, color, points, width=0):
        pygame.draw.polygon(
            self.surface,
            color,
            [(round(x * self.scale), round(y * self.scale)) for x, y in points],
            width * self.scale,
        )

    def ellipse(self, color, rectangle, width=0):
        pygame.draw.ellipse(
            self.surface,
            color,
            [round(value * self.scale) for value in rectangle],
            width * self.scale,
        )

    def line(self, color, start, end, width=1):
        pygame.draw.line(
            self.surface,
            color,
            [round(value * self.scale) for value in start],
            [round(value * self.scale) for value in end],
            width * self.scale,
        )

    def finish(self):
        return pygame.transform.smoothscale(self.surface, (self.size, self.size))


def gold_icon():
    canvas = IconCanvas()

    for horizontal, vertical, count in [(3, 23, 2), (18, 23, 4)]:
        for level in range(count):
            top = vertical - level * 4
            canvas.ellipse((126, 79, 23), (horizontal, top + 3, 18, 9))
            canvas.ellipse((202, 143, 39), (horizontal, top, 18, 9))
            canvas.ellipse((247, 207, 96), (horizontal + 1, top, 16, 6))
            canvas.ellipse((191, 128, 30), (horizontal + 4, top + 1, 10, 4), 1)
            canvas.line((255, 231, 147), (horizontal + 4, top + 7), (horizontal + 4, top + 8))

    return canvas.finish()


def army_icon():
    canvas = IconCanvas()

    for mirrored in (False, True):

        def mirror(point):
            return (40 - point[0], point[1]) if mirrored else point

        canvas.polygon(
            (185, 207, 212),
            [mirror(point) for point in [(6, 4), (12, 7), (32, 31), (28, 33), (8, 10)]],
        )
        canvas.line((244, 249, 235), mirror((7, 5)), mirror((29, 31)))
        canvas.line((181, 144, 74), mirror((23, 29)), mirror((32, 23)), 3)
        canvas.line((121, 80, 43), mirror((29, 31)), mirror((34, 37)), 3)

    canvas.polygon((195, 181, 130), [(9, 12), (20, 8), (31, 12), (29, 27), (20, 35), (11, 27)])
    canvas.polygon((62, 106, 136), [(12, 14), (20, 11), (28, 14), (26, 26), (20, 31), (14, 26)])
    canvas.polygon((39, 73, 98), [(20, 11), (28, 14), (26, 26), (20, 31)])
    canvas.line((228, 218, 169), (20, 15), (20, 26), 2)
    canvas.line((228, 218, 169), (16, 19), (24, 19), 2)
    return canvas.finish()


def area_icon():
    canvas = IconCanvas()
    canvas.polygon(
        (100, 75, 43), [(3, 9), (14, 5), (25, 8), (36, 5), (36, 32), (25, 36), (14, 33), (3, 36)]
    )
    canvas.polygon(
        (207, 190, 138), [(4, 8), (14, 4), (25, 7), (35, 4), (35, 30), (25, 34), (14, 31), (4, 34)]
    )
    canvas.polygon((157, 158, 108), [(14, 4), (25, 7), (25, 34), (14, 31)])
    canvas.line((112, 143, 147), (7, 14), (15, 20), 2)
    canvas.line((112, 143, 147), (15, 20), (12, 30), 2)
    canvas.polygon((106, 128, 74), [(19, 25), (23, 18), (31, 20), (29, 28)])
    canvas.line((78, 65, 44), (23, 23), (23, 6), 2)
    canvas.polygon((167, 68, 47), [(24, 6), (33, 9), (24, 13)])
    canvas.line((244, 225, 168), (5, 9), (12, 6))
    return canvas.finish()


def create_hud_icons():
    return {
        "gold": gold_icon(),
        "army": army_icon(),
        "area": area_icon(),
    }
