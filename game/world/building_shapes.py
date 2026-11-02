import pygame


def ground_shadow(canvas, rectangle):
    left, top, width, height = rectangle
    canvas.ellipse((22, 35, 26, 15), (left - 3, top - 2, width + 6, height + 4))
    canvas.ellipse((22, 35, 26, 28), rectangle)
    canvas.ellipse((22, 35, 26, 24), (left + 4, top + 3, width - 8, height - 6))


def railway(canvas, start, end, width=9):
    start, end = pygame.Vector2(start), pygame.Vector2(end)
    direction = (end - start).normalize()
    cross = pygame.Vector2(width, width * 0.35)
    canvas.polygon(
        (102, 108, 80),
        [start - cross * 0.85, start + cross * 0.85, end + cross * 0.85, end - cross * 0.85],
    )
    for index in range(10):
        center = start.lerp(end, index / 9)
        first, last = center - cross * 0.85, center + cross * 0.85
        canvas.polygon(
            (63, 72, 57), [first - direction, last - direction, last + direction, first + direction]
        )
        canvas.line((128, 112, 76), first - direction * 0.3, last - direction * 0.3, 1)
    for side in (-1, 1):
        offset = cross / 2 * side
        canvas.line((43, 58, 55), start + offset, end + offset, 2)
        canvas.line(
            (179, 187, 164),
            start + offset - pygame.Vector2(0, 0.7),
            end + offset - pygame.Vector2(0, 0.7),
            1,
        )


def crate(canvas, position, size=8):
    horizontal, vertical = position
    canvas.polygon(
        (91, 105, 73),
        [
            (horizontal, vertical),
            (horizontal + size, vertical + 3),
            (horizontal + size, vertical + 10),
            (horizontal, vertical + 7),
        ],
    )
    canvas.polygon(
        (60, 79, 61),
        [
            (horizontal + size, vertical + 3),
            (horizontal + size + 5, vertical - 1),
            (horizontal + size + 5, vertical + 6),
            (horizontal + size, vertical + 10),
        ],
    )
    canvas.polygon(
        (129, 139, 98),
        [
            (horizontal, vertical),
            (horizontal + 5, vertical - 4),
            (horizontal + size + 5, vertical - 1),
            (horizontal + size, vertical + 3),
        ],
    )
    canvas.line((167, 166, 117), (horizontal + 2, vertical + 1), (horizontal + 2, vertical + 7), 1)
    canvas.line(
        (42, 62, 49),
        (horizontal + size - 2, vertical + 3),
        (horizontal + size - 2, vertical + 9),
        1,
    )
