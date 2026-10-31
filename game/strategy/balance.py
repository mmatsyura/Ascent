import numpy as np

from game.settings import TERRAIN_SCALE
from game.world.biomes import Biome


FACTIONS = ('blue', 'red', 'green', 'purple')


def balance_territories(terrain, cities):
    stride = 8
    rows, columns = terrain.biomes.shape
    weights_land = (terrain.biomes != Biome.WATER).reshape(rows//stride,stride,columns//stride,stride).sum(axis=(1,3))
    y, x = np.nonzero(weights_land)
    samples = weights_land[y,x]
    x, y = (x+.5) * stride * TERRAIN_SCALE, (y+.5) * stride * TERRAIN_SCALE
    distances = np.asarray([(x-city.position[0])**2 + (y-city.position[1])**2 for city in cities], dtype=np.float64)
    owners = np.array([FACTIONS.index(city.owner) if city.owner in FACTIONS else 4 for city in cities])
    weights = np.ones(5)
    for _ in range(100):
        winner = owners[np.argmin(distances / weights[owners, None]**2, axis=0)]
        fractions = np.bincount(winner, weights=samples, minlength=5) / samples.sum()
        if max(abs(fractions[:4] - .12)) < .001:
            break
        weights[:4] *= np.exp((.12 - fractions[:4]) * 1.5)
    for city, owner in zip(cities, owners):
        city.influence_weight = float(weights[owner])
