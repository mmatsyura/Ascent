import numpy as np


def smooth_noise(width, height, columns, rows, random):
    lattice = random.random((rows + 1, columns + 1)).astype(np.float32)
    horizontal = np.linspace(0, columns, width, endpoint=False, dtype=np.float32)
    vertical = np.linspace(0, rows, height, endpoint=False, dtype=np.float32)
    column_indices = horizontal.astype(int)
    row_indices = vertical.astype(int)

    horizontal -= column_indices
    vertical -= row_indices
    horizontal = horizontal * horizontal * (3 - 2 * horizontal)
    vertical = vertical * vertical * (3 - 2 * vertical)

    upper = lattice[row_indices[:, None], column_indices] * (1 - horizontal)
    upper += lattice[row_indices[:, None], column_indices + 1] * horizontal
    lower = lattice[row_indices[:, None] + 1, column_indices] * (1 - horizontal)
    lower += lattice[row_indices[:, None] + 1, column_indices + 1] * horizontal

    return upper * (1 - vertical[:, None]) + lower * vertical[:, None]
