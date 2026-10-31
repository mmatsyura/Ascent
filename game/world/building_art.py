from functools import lru_cache

import pygame

from game.world.airport_art import airport_shape
from game.world.barracks_art import barracks_shape
from game.world.mine_art import mine_shape
from game.world.buildings import BUILDINGS_BY_KEY


@lru_cache(maxsize=3)
def building_source(key):
    return {"mine": mine_shape, "airport": airport_shape, "barracks": barracks_shape}[key]()


@lru_cache(maxsize=3)
def building_bounds(key):
    return building_source(key).get_bounding_rect(min_alpha=8)


@lru_cache(maxsize=3)
def building_asset(key):
    return building_source(key).subsurface(building_bounds(key)).copy()


@lru_cache(maxsize=3)
def building_layout(key):
    image = building_asset(key)
    maximum = BUILDINGS_BY_KEY[key].sprite_size
    scale = min(maximum[0] / image.get_width(), maximum[1] / image.get_height())
    width = round(image.get_width() * scale)
    height = round(image.get_height() * scale)
    return (width + 8, height + 18), (4 + width / 2, 14 + height * .78), (width, height)


def building_point(key, position):
    bounds = building_bounds(key)
    _, _, size = building_layout(key)
    art_scale = building_source(key).get_width() / 128
    return (
        round((4 + (position[0] * art_scale - bounds.x) * size[0] / bounds.w) * 2),
        round((14 + (position[1] * art_scale - bounds.y) * size[1] / bounds.h) * 2),
    )


@lru_cache(maxsize=3)
def building_base(key):
    size, _, image_size = building_layout(key)
    image = pygame.Surface((size[0] * 2, size[1] * 2), pygame.SRCALPHA)
    sprite = pygame.transform.smoothscale(building_asset(key), (image_size[0] * 2, image_size[1] * 2))
    image.blit(sprite, (8, 28))
    return image
