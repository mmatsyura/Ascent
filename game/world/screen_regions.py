import pygame


def dirty_regions(rectangles, screen_area, tile_size=128):
    columns = (screen_area.w + tile_size - 1) // tile_size
    rows = (screen_area.h + tile_size - 1) // tile_size
    occupied = [bytearray(columns) for _ in range(rows)]
    for rectangle in rectangles:
        area = rectangle.clip(screen_area)
        if not area.w or not area.h:
            continue
        left, right = area.left // tile_size, (area.right - 1) // tile_size + 1
        for row in range(area.top // tile_size, (area.bottom - 1) // tile_size + 1):
            occupied[row][left:right] = b"\x01" * (right - left)
    regions = []
    active = {}
    for row, cells in enumerate(occupied):
        runs = {}
        column = 0
        while column < columns:
            if not cells[column]:
                column += 1
                continue
            left = column
            while column < columns and cells[column]:
                column += 1
            key = left, column
            rectangle = active.pop(key, None)
            if rectangle is None:
                rectangle = pygame.Rect(
                    left * tile_size, row * tile_size, (column - left) * tile_size, tile_size
                )
            else:
                rectangle.h += tile_size
            runs[key] = rectangle
        regions.extend(active.values())
        active = runs
    regions.extend(active.values())
    return [rectangle.clip(screen_area) for rectangle in regions]
