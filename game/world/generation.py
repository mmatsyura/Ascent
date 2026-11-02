import numpy as np

from game.settings import MAP_SEED, TERRAIN_SCALE, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome


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


def generate_terrain():
    random = np.random.default_rng(MAP_SEED)
    width = WORLD_WIDTH // TERRAIN_SCALE
    height = WORLD_HEIGHT // TERRAIN_SCALE
    horizontal = np.linspace(0, 1, width, dtype=np.float32)[None, :]
    vertical = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    broad_noise = smooth_noise(width, height, 15, 12, random)
    ground_noise = smooth_noise(width, height, 95, 70, random)
    ridge_noise = smooth_noise(width, height, 170, 120, random)

    western_coast = 0.065 + 0.032 * np.sin(vertical * 17 + 1)
    western_coast += 0.115 * np.exp(-(((vertical - 0.37) / 0.115) ** 2))
    eastern_coast = 0.945 - 0.245 * np.exp(-(((vertical - 0.16) / 0.20) ** 2))
    eastern_coast -= 0.065 * np.sin(vertical * 15 + 0.6)
    shore_distance = np.minimum(horizontal - western_coast, eastern_coast - horizontal)
    shore_distance += (broad_noise - 0.5) * 0.045 + (ground_noise - 0.5) * 0.006

    for center_x, center_y, radius_x, radius_y in [
        (0.855, 0.11, 0.031, 0.035),
        (0.93, 0.29, 0.023, 0.043),
        (0.957, 0.77, 0.017, 0.021),
    ]:
        island_distance = 1 - np.sqrt(
            ((horizontal - center_x) / radius_x) ** 2 + ((vertical - center_y) / radius_y) ** 2
        )
        shore_distance = np.maximum(
            shore_distance, island_distance * 0.025 + (ground_noise - 0.5) * 0.003
        )

    lake_distance = (
        np.sqrt(((horizontal - 0.30) / 0.062) ** 2 + ((vertical - 0.195) / 0.028) ** 2) - 1
    )
    shore_distance = np.minimum(
        shore_distance, lake_distance * 0.025 + (ground_noise - 0.5) * 0.002
    )
    river_center = 0.47 + 0.075 * np.sin(vertical * 8.5 - 1.2) + 0.028 * np.sin(vertical * 18 + 0.3)
    river_width = 0.0072 + 0.0030 * vertical**2 + 0.0012 * np.sin(vertical * 22) ** 2
    river_distance = np.abs(horizontal - river_center) - river_width

    fork_progress = np.clip((vertical - 0.72) / 0.28, 0, 1)
    fork_center = river_center + 0.235 * fork_progress**1.12
    fork_center += 0.018 * np.sin(fork_progress * 8) * fork_progress
    fork_width = 0.0065 + 0.0025 * fork_progress + 0.0009 * np.sin(vertical * 27) ** 2
    fork_distance = np.abs(horizontal - fork_center) - fork_width
    fork_distance = np.where(vertical >= 0.72, fork_distance, np.inf)
    river_distance = np.minimum(river_distance, fork_distance)
    water_distance = np.minimum(shore_distance, river_distance)

    beach_width = 0.006 + broad_noise * 0.003 + ground_noise * 0.002
    beach_width += np.where(shore_distance < river_distance, 0.003, 0)
    sand_blend = np.clip((beach_width - water_distance) / (beach_width * 0.55), 0, 1)
    sand_blend = sand_blend**2 * (3 - 2 * sand_blend)

    elevation = np.zeros((height, width), dtype=np.float32)
    mountain_ranges = [
        (0.695, 0.315, 0.069, 0.132, 1.05),
        (0.733, 0.405, 0.080, 0.113, 0.96),
        (0.765, 0.505, 0.069, 0.116, 1.12),
        (0.725, 0.610, 0.071, 0.095, 0.85),
        (0.272, 0.735, 0.105, 0.067, 0.95),
        (0.355, 0.775, 0.074, 0.070, 0.87),
    ]
    for center_x, center_y, radius_x, radius_y, summit_height in mountain_ranges:
        relative_x = (horizontal - center_x) / radius_x
        relative_y = (vertical - center_y) / radius_y
        radial_distance = np.sqrt(relative_x**2 + relative_y**2)
        peak = np.clip(1 - radial_distance + (broad_noise - 0.5) * 0.22, 0, 1) * summit_height
        elevation = np.maximum(elevation, peak)

    elevation += (broad_noise - 0.5) * 0.10 + (ground_noise - 0.5) * 0.025
    mountain_mask = (elevation > 0.12) & (water_distance > 0.014)
    forest_field = broad_noise + 0.09 * np.sin(horizontal * 16 + vertical * 9)
    forest_strength = np.clip((forest_field - 0.40) / 0.36, 0, 1)
    forest_strength = forest_strength**2 * (3 - 2 * forest_strength)
    forest_strength *= np.clip((water_distance - 0.006) / 0.012, 0, 1)
    forest_strength *= 1 - np.clip((elevation - 0.02) / 0.10, 0, 1)
    forest_strength *= 1 - sand_blend
    forest_mask = (
        (forest_field > 0.48) & (water_distance > beach_width + 0.004) & (elevation < 0.065)
    )

    biomes = np.full((height, width), Biome.MEADOW, dtype=np.uint8)
    biomes[forest_mask] = Biome.FOREST
    biomes[(water_distance > 0) & (sand_blend > 0.35)] = Biome.BEACH
    biomes[mountain_mask] = Biome.MOUNTAIN
    biomes[water_distance <= 0] = Biome.WATER

    texture = (ground_noise - 0.5) * 9 + (ridge_noise - 0.5) * 3
    colors = np.empty((height, width, 3), dtype=np.float32)
    meadow_color = np.array([133, 153, 99], dtype=np.float32)
    colors[:] = meadow_color + ((broad_noise - 0.5) * 29 + texture)[..., None]
    dry_grass = np.clip((ground_noise - 0.48) * 2.4, 0, 0.6) * (1 - forest_strength)
    colors += dry_grass[..., None] * np.array([17, 5, -5])
    meadow_variation = np.sin(horizontal * 87 + broad_noise * 9) * np.sin(
        vertical * 71 + ground_noise * 6
    )
    meadow_variation *= (1 - forest_strength) * (1 - sand_blend)
    colors += meadow_variation[..., None] * np.array([2.8, 3.2, 1.4])
    colors -= forest_strength[..., None] * np.array([27, 26, 11])
    litter = np.clip((ground_noise - 0.52) * 3, 0, 1) * forest_strength
    colors += litter[..., None] * np.array([12, -3, -5])
    dry_sand = np.clip(water_distance / 0.0025, 0, 1)
    sand_color = np.array([166, 159, 119]) + dry_sand[..., None] * np.array([54, 44, 34])
    sand_ripples = np.sin(vertical * height * 0.8 + ground_noise * 9) * 1.4
    sand_color += (texture * 0.55 + sand_ripples)[..., None]
    dune_grain = np.sin(horizontal * width * 0.7 + ground_noise * 15) * np.sin(
        vertical * height * 0.63
    )
    sand_color += (dune_grain * dry_sand * 0.8)[..., None]
    wet_shore = np.exp(-np.maximum(water_distance, 0) / 0.0014)
    sand_color -= wet_shore[..., None] * np.array([12, 10, 6])
    colors = colors * (1 - sand_blend[..., None]) + sand_color * sand_blend[..., None]

    depth = np.clip(-water_distance / 0.038, 0, 1)
    water_color = np.array([58, 139, 145]) + depth[..., None] * np.array([-42, -88, -76])
    shallows = np.clip(1 - depth * 6, 0, 1)
    caustics = (
        np.sin(horizontal * width * 0.43 + ground_noise * 22)
        + np.sin(vertical * height * 0.51 + ridge_noise * 17)
    ) * 0.9
    water_color += (caustics * shallows)[..., None] * np.array([1.2, 1.8, 1.5])
    water_color += texture[..., None] * 0.3
    shoreline_glow = np.exp(-np.abs(water_distance) / 0.0018)
    water_color += shoreline_glow[..., None] * np.array([3, 6, 4])
    colors[biomes == Biome.WATER] = water_color[biomes == Biome.WATER]
    foam_mask = (water_distance <= 0) & (water_distance > -0.00065)
    colors[foam_mask] = colors[foam_mask] * 0.55 + np.array([178, 215, 199]) * 0.45

    mountain_height, rock_texture = create_mountain_relief(width, height, elevation, random)
    detail_random = np.random.default_rng(MAP_SEED + 871)
    stone_detail = smooth_noise(width, height, 690, 480, detail_random)
    stone_ridges = 1 - np.abs(stone_detail * 2 - 1)
    textured_height = mountain_height + stone_ridges * np.clip(elevation * 0.014, 0, 0.009)
    slope_y, slope_x = np.gradient(textured_height)
    lighting = np.clip((-slope_x * 32 - slope_y * 24), -0.62, 0.62)
    rock_color = np.array([126, 130, 119]) + lighting[..., None] * np.array([94, 94, 91])
    rock_color += ((rock_texture - 0.5) * 27 + (stone_detail - 0.5) * 8)[..., None]
    creases = np.clip((0.48 - rock_texture) * 2, 0, 1)
    rock_color -= (creases * np.clip(elevation * 2, 0, 1))[..., None] * np.array([12, 14, 16])
    cool_shadow = np.clip(-lighting, 0, 1)[..., None]
    rock_color += cool_shadow * np.array([-7, 0, 9])
    rock_seams = np.clip((0.25 - stone_detail) * 4, 0, 1)
    rock_color -= (rock_seams * np.clip(elevation * 2, 0, 1))[..., None] * np.array([7, 8, 7])
    foothills = np.clip((elevation - 0.12) / 0.13, 0, 1)[..., None]
    rock_color = np.array([111, 128, 99]) * (1 - foothills) + rock_color * foothills
    snow = np.clip((mountain_height - 0.67 + ground_noise * 0.08) / 0.16, 0, 1)[..., None]
    snow_color = np.array([221, 229, 220]) + lighting[..., None] * 35
    rock_color = rock_color * (1 - snow) + snow_color * snow
    mountain_blend = np.clip((elevation - 0.07) / 0.13, 0, 1)
    mountain_blend *= np.clip((water_distance - beach_width - 0.004) / 0.008, 0, 1)
    colors = colors * (1 - mountain_blend[..., None]) + rock_color * mountain_blend[..., None]

    return np.clip(colors, 0, 255).astype(np.uint8), biomes, forest_strength, random


def create_mountain_relief(width, height, elevation, random):
    relief = np.zeros((height, width), dtype=np.float32)
    amplitude = 1.0
    amplitude_sum = 0.0
    previous_ridge = np.ones_like(relief)

    for columns, rows in [(27, 22), (55, 44), (110, 88), (220, 176), (440, 352)]:
        octave = smooth_noise(width, height, columns, rows, random)
        ridge = (1 - np.abs(octave * 2 - 1)) ** 2
        relief += ridge * amplitude * (0.35 + 0.65 * previous_ridge)
        previous_ridge = ridge
        amplitude_sum += amplitude
        amplitude *= 0.52

    relief /= amplitude_sum
    horizontal = np.linspace(0, 1, width, dtype=np.float32)[None, :]
    vertical = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    ridge_height = np.zeros_like(relief)
    ridge_segments = [
        ((0.685, 0.285, 0.88), (0.716, 0.367, 0.94), 0.052),
        ((0.716, 0.367, 0.94), (0.735, 0.420, 1.08), 0.050),
        ((0.735, 0.420, 1.08), (0.773, 0.490, 1.12), 0.052),
        ((0.773, 0.490, 1.12), (0.745, 0.562, 0.95), 0.047),
        ((0.745, 0.562, 0.95), (0.719, 0.635, 0.77), 0.045),
        ((0.700, 0.325, 0.90), (0.662, 0.340, 0.28), 0.027),
        ((0.735, 0.420, 1.08), (0.779, 0.395, 0.34), 0.029),
        ((0.773, 0.490, 1.12), (0.800, 0.541, 0.35), 0.028),
        ((0.745, 0.562, 0.95), (0.706, 0.581, 0.22), 0.025),
        ((0.216, 0.726, 0.48), (0.273, 0.730, 0.96), 0.043),
        ((0.273, 0.730, 0.96), (0.317, 0.762, 0.75), 0.044),
        ((0.317, 0.762, 0.75), (0.365, 0.777, 0.88), 0.041),
        ((0.273, 0.730, 0.96), (0.269, 0.778, 0.23), 0.025),
        ((0.350, 0.773, 0.83), (0.369, 0.744, 0.22), 0.023),
    ]

    for start, end, ridge_width in ridge_segments:
        direction_x, direction_y = end[0] - start[0], end[1] - start[1]
        projection = (
            (horizontal - start[0]) * direction_x + (vertical - start[1]) * direction_y
        ) / (direction_x**2 + direction_y**2)
        projection = np.clip(projection, 0, 1)
        distance_x = (horizontal - start[0] - projection * direction_x) * 1.25
        distance_y = vertical - start[1] - projection * direction_y
        distance = np.sqrt(distance_x**2 + distance_y**2)
        segment_height = start[2] + projection * (end[2] - start[2])
        profile = np.clip(1 - distance / ridge_width, 0, 1) ** 1.4
        ridge_height = np.maximum(ridge_height, profile * segment_height)

    envelope = np.maximum(elevation, 0)
    mountain_height = envelope * (0.14 + relief * 0.32) + ridge_height * 0.72
    return mountain_height, octave
