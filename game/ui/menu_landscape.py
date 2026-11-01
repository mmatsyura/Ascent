import numpy as np
import pygame


def periodic_noise(width, height, columns, rows, random):
    lattice = random.random((rows, columns)).astype(np.float32)
    x = np.arange(width, dtype=np.float32) * columns / width
    y = np.arange(height, dtype=np.float32) * rows / height
    column, row = x.astype(np.int32), y.astype(np.int32)
    x -= column
    y -= row
    x = x * x * (3 - 2 * x)
    y = y * y * (3 - 2 * y)
    upper = lattice[row[:, None] % rows, column % columns] * (1 - x)
    upper += lattice[row[:, None] % rows, (column + 1) % columns] * x
    lower = lattice[(row[:, None] + 1) % rows, column % columns] * (1 - x)
    lower += lattice[(row[:, None] + 1) % rows, (column + 1) % columns] * x
    return upper * (1 - y[:, None]) + lower * y[:, None]


def menu_landscape(size):
    width = min(800, size[0])
    height = max(600, round(size[1] * 2 * width / size[0]))
    random = np.random.default_rng(4731)
    x = np.arange(width, dtype=np.float32)[None, :] / width
    angle = np.arange(height, dtype=np.float32)[:, None] / height * np.pi * 2
    broad = periodic_noise(width, height, 11, 17, random)
    detail = periodic_noise(width, height, 83, 107, random)
    coast = np.minimum(x - (.07 + .035 * np.sin(angle * 3)), (.94 + .055 * np.sin(angle * 2 + 1)) - x)
    river = np.abs(x - (.46 + .09 * np.sin(angle + .6) + .025 * np.sin(angle * 3))) - .009
    shore = np.minimum(coast + (broad - .5) * .025, river)
    forest = np.clip((broad - .38) * 2.7, 0, 1)
    colors = np.empty((height, width, 3), dtype=np.float32)
    colors[:] = np.array([133, 153, 99]) + ((broad - .5) * 24 + (detail - .5) * 5)[..., None]
    colors -= forest[..., None] * np.array([28, 27, 12])
    ridge_center = .75 + .045 * np.sin(angle * 2 + .4)
    ridge = np.clip(1 - np.abs(x - ridge_center) / .08, 0, 1)
    ridge *= .6 + .25 * np.sin(angle + 1) ** 2
    elevation = ridge * (.7 + detail * .3)
    slope_x = (np.roll(elevation, -1, 1) - np.roll(elevation, 1, 1)) * .5
    slope_y = (np.roll(elevation, -1, 0) - np.roll(elevation, 1, 0)) * .5
    light = np.clip(-slope_x * 10 - slope_y * 7, -.45, .45)
    rock = np.array([124, 132, 120]) + light[..., None] * 110 + (detail - .5)[..., None] * 13
    snow = np.clip((elevation - .62) * 5, 0, .9)[..., None]
    rock = rock * (1 - snow) + np.array([221, 229, 218]) * snow
    mountain = np.clip(ridge * 4, 0, 1)[..., None]
    colors = colors * (1 - mountain) + rock * mountain
    sand = np.clip((.014 - shore) / .009, 0, 1)[..., None]
    sand = sand * sand * (3 - 2 * sand)
    colors = colors * (1 - sand) + (np.array([205, 196, 147]) + (detail - .5)[..., None] * 8) * sand
    depth = np.clip(-shore / .055, 0, 1)
    water = np.array([55, 133, 140]) + depth[..., None] * np.array([-39, -80, -69])
    colors[shore <= 0] = water[shore <= 0]
    image = pygame.surfarray.make_surface(np.clip(colors, 0, 255).astype(np.uint8).transpose(1, 0, 2)).convert()
    for horizontal, vertical in random.integers((0, 0), (width, height), size=(18000, 2)):
        if forest[vertical, horizontal] < .45 or shore[vertical, horizontal] < .022 or ridge[vertical, horizontal] > .05:
            continue
        radius = int(random.integers(2, 5))
        for offset in (-height, 0, height):
            point = int(horizontal), int(vertical) + offset
            pygame.draw.ellipse(image, (62, 83, 51), (point[0] - radius, point[1], radius * 3, radius + 2))
            pygame.draw.circle(image, (36, 65, 46), point, radius)
            pygame.draw.circle(image, (65, 94, 57), (point[0] - 1, point[1] - 1), max(1, radius - 1))
    result = pygame.transform.smoothscale(image, (size[0], size[1] * 2))
    result.fill((95, 121, 112), special_flags=pygame.BLEND_RGB_MULT)
    return result
