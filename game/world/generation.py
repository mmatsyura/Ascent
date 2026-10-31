import numpy as np

from game.settings import MAP_SEED, TERRAIN_SCALE, WORLD_HEIGHT, WORLD_WIDTH
from game.world.biomes import Biome
from game.world.noise import smooth_noise


def generate_terrain():
    random = np.random.default_rng(MAP_SEED)
    width = WORLD_WIDTH // TERRAIN_SCALE
    height = WORLD_HEIGHT // TERRAIN_SCALE
    horizontal = np.linspace(0, 1, width, dtype=np.float32)[None, :]
    vertical = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    broad_noise = smooth_noise(width, height, 15, 12, random)
    ground_noise = smooth_noise(width, height, 95, 70, random)
    ridge_noise = smooth_noise(width, height, 170, 120, random)

    western_coast = .065 + .032 * np.sin(vertical * 17 + 1)
    western_coast += .115 * np.exp(-((vertical - .37) / .115) ** 2)
    eastern_coast = .945 - .245 * np.exp(-((vertical - .16) / .20) ** 2)
    eastern_coast -= .065 * np.sin(vertical * 15 + .6)
    shore_distance = np.minimum(horizontal - western_coast, eastern_coast - horizontal)
    shore_distance += (broad_noise - .5) * .045 + (ground_noise - .5) * .006

    for center_x, center_y, radius_x, radius_y in [(.855, .11, .031, .035), (.93, .29, .023, .043), (.957, .77, .017, .021)]:
        island_distance = 1 - np.sqrt(((horizontal - center_x) / radius_x) ** 2 + ((vertical - center_y) / radius_y) ** 2)
        shore_distance = np.maximum(shore_distance, island_distance * .025 + (ground_noise - .5) * .003)

    lake_distance = np.sqrt(((horizontal - .30) / .062) ** 2 + ((vertical - .195) / .028) ** 2) - 1
    shore_distance = np.minimum(shore_distance, lake_distance * .025 + (ground_noise - .5) * .002)
    river_center = .47 + .075 * np.sin(vertical * 8.5 - 1.2) + .028 * np.sin(vertical * 18 + .3)
    river_width = .0072 + .0030 * vertical ** 2 + .0012 * np.sin(vertical * 22) ** 2
    river_distance = np.abs(horizontal - river_center) - river_width

    fork_progress = np.clip((vertical - .72) / .28, 0, 1)
    fork_center = river_center + .235 * fork_progress ** 1.12
    fork_center += .018 * np.sin(fork_progress * 8) * fork_progress
    fork_width = .0065 + .0025 * fork_progress + .0009 * np.sin(vertical * 27) ** 2
    fork_distance = np.abs(horizontal - fork_center) - fork_width
    fork_distance = np.where(vertical >= .72, fork_distance, np.inf)
    river_distance = np.minimum(river_distance, fork_distance)
    water_distance = np.minimum(shore_distance, river_distance)

    beach_width = .006 + broad_noise * .003 + ground_noise * .002
    beach_width += np.where(shore_distance < river_distance, .003, 0)
    sand_blend = np.clip((beach_width - water_distance) / (beach_width * .55), 0, 1)
    sand_blend = sand_blend ** 2 * (3 - 2 * sand_blend)

    elevation = np.zeros((height, width), dtype=np.float32)
    mountain_ranges = [
        (.695, .315, .069, .132, 1.05),
        (.733, .405, .080, .113, .96),
        (.765, .505, .069, .116, 1.12),
        (.725, .610, .071, .095, .85),
        (.272, .735, .105, .067, .95),
        (.355, .775, .074, .070, .87),
    ]
    for center_x, center_y, radius_x, radius_y, summit_height in mountain_ranges:
        relative_x = (horizontal - center_x) / radius_x
        relative_y = (vertical - center_y) / radius_y
        radial_distance = np.sqrt(relative_x ** 2 + relative_y ** 2)
        peak = np.clip(1 - radial_distance + (broad_noise - .5) * .22, 0, 1) * summit_height
        elevation = np.maximum(elevation, peak)

    elevation += (broad_noise - .5) * .10 + (ground_noise - .5) * .025
    mountain_mask = (elevation > .12) & (water_distance > .014)
    forest_field = broad_noise + .09 * np.sin(horizontal * 16 + vertical * 9)
    forest_strength = np.clip((forest_field - .40) / .36, 0, 1)
    forest_strength = forest_strength ** 2 * (3 - 2 * forest_strength)
    forest_strength *= np.clip((water_distance - .006) / .012, 0, 1)
    forest_strength *= 1 - np.clip((elevation - .02) / .10, 0, 1)
    forest_strength *= 1 - sand_blend
    forest_mask = (forest_field > .48) & (water_distance > beach_width + .004) & (elevation < .065)

    biomes = np.full((height, width), Biome.MEADOW, dtype=np.uint8)
    biomes[forest_mask] = Biome.FOREST
    biomes[(water_distance > 0) & (sand_blend > .35)] = Biome.BEACH
    biomes[mountain_mask] = Biome.MOUNTAIN
    biomes[water_distance <= 0] = Biome.WATER

    texture = (ground_noise - .5) * 9 + (ridge_noise - .5) * 3
    colors = np.empty((height, width, 3), dtype=np.float32)
    meadow_color = np.array([144, 158, 100], dtype=np.float32)
    colors[:] = meadow_color + ((broad_noise - .5) * 22 + texture)[..., None]
    colors -= forest_strength[..., None] * np.array([30, 25, 12])
    litter = np.clip((ground_noise - .52) * 3, 0, 1) * forest_strength
    colors += litter[..., None] * np.array([12, -3, -5])
    dry_sand = np.clip(water_distance / .0025, 0, 1)
    sand_color = np.array([171, 166, 126]) + dry_sand[..., None] * np.array([41, 32, 24])
    sand_ripples = np.sin(vertical * height * .8 + ground_noise * 9) * 1.4
    sand_color += (texture * .55 + sand_ripples)[..., None]
    colors = colors * (1 - sand_blend[..., None]) + sand_color * sand_blend[..., None]

    depth = np.clip(-water_distance / .038, 0, 1)
    water_color = np.array([62, 136, 143]) + depth[..., None] * np.array([-43, -82, -68])
    water_color += texture[..., None] * .3
    colors[biomes == Biome.WATER] = water_color[biomes == Biome.WATER]
    foam_mask = (water_distance <= 0) & (water_distance > -.00065)
    colors[foam_mask] = colors[foam_mask] * .55 + np.array([178, 215, 199]) * .45

    mountain_height, rock_texture = create_mountain_relief(width, height, elevation, random)
    slope_y, slope_x = np.gradient(mountain_height)
    lighting = np.clip((-slope_x * 32 - slope_y * 24), -.62, .62)
    rock_color = np.array([126, 130, 119]) + lighting[..., None] * np.array([94, 94, 91])
    rock_color += (rock_texture - .5)[..., None] * 20
    foothills = np.clip((elevation - .12) / .13, 0, 1)[..., None]
    rock_color = np.array([111, 128, 99]) * (1 - foothills) + rock_color * foothills
    snow = np.clip((mountain_height - .67 + ground_noise * .08) / .16, 0, 1)[..., None]
    snow_color = np.array([221, 229, 220]) + lighting[..., None] * 35
    rock_color = rock_color * (1 - snow) + snow_color * snow
    mountain_blend = np.clip((elevation - .07) / .13, 0, 1)
    mountain_blend *= np.clip((water_distance - beach_width - .004) / .008, 0, 1)
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
        relief += ridge * amplitude * (.35 + .65 * previous_ridge)
        previous_ridge = ridge
        amplitude_sum += amplitude
        amplitude *= .52

    relief /= amplitude_sum
    horizontal = np.linspace(0, 1, width, dtype=np.float32)[None, :]
    vertical = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    ridge_height = np.zeros_like(relief)
    ridge_segments = [
        ((.685, .285, .88), (.716, .367, .94), .052),
        ((.716, .367, .94), (.735, .420, 1.08), .050),
        ((.735, .420, 1.08), (.773, .490, 1.12), .052),
        ((.773, .490, 1.12), (.745, .562, .95), .047),
        ((.745, .562, .95), (.719, .635, .77), .045),
        ((.700, .325, .90), (.662, .340, .28), .027),
        ((.735, .420, 1.08), (.779, .395, .34), .029),
        ((.773, .490, 1.12), (.800, .541, .35), .028),
        ((.745, .562, .95), (.706, .581, .22), .025),
        ((.216, .726, .48), (.273, .730, .96), .043),
        ((.273, .730, .96), (.317, .762, .75), .044),
        ((.317, .762, .75), (.365, .777, .88), .041),
        ((.273, .730, .96), (.269, .778, .23), .025),
        ((.350, .773, .83), (.369, .744, .22), .023),
    ]

    for start, end, ridge_width in ridge_segments:
        direction_x, direction_y = end[0] - start[0], end[1] - start[1]
        projection = ((horizontal - start[0]) * direction_x + (vertical - start[1]) * direction_y) / (direction_x ** 2 + direction_y ** 2)
        projection = np.clip(projection, 0, 1)
        distance_x = (horizontal - start[0] - projection * direction_x) * 1.25
        distance_y = vertical - start[1] - projection * direction_y
        distance = np.sqrt(distance_x ** 2 + distance_y ** 2)
        segment_height = start[2] + projection * (end[2] - start[2])
        profile = np.clip(1 - distance / ridge_width, 0, 1) ** 1.4
        ridge_height = np.maximum(ridge_height, profile * segment_height)

    envelope = np.maximum(elevation, 0)
    mountain_height = envelope * (.14 + relief * .32) + ridge_height * .72
    return mountain_height, octave
