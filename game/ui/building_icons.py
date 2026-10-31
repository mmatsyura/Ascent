import pygame

from game.world.building_art import building_asset
from game.world.buildings import BUILDINGS


def create_building_icons():
    icons = {}
    for definition in BUILDINGS:
        key = definition.key
        source = building_asset(key)
        scale = min(120 / source.get_width(), 120 / source.get_height())
        sprite = pygame.transform.smoothscale(source, (round(source.get_width() * scale), round(source.get_height() * scale)))
        image = pygame.Surface((128, 128), pygame.SRCALPHA)
        image.blit(sprite, sprite.get_rect(center=(64, 64)))
        icons[key] = image
    return icons
