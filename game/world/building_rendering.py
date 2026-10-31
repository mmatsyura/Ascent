from functools import lru_cache

import pygame

from game.rendering import RenderPart
from game.world.faction_art import faction_image
from game.world.building_animation import ANIMATION_FRAMES, ANIMATION_RATE, building_frame
from game.world.building_art import building_layout
from game.world.construction_art import builder_parts, construction_frame


@lru_cache(maxsize=192)
def scaled_building(key, frame, size, training=False):
    return pygame.transform.smoothscale(building_frame(key, frame, training), size)


@lru_cache(maxsize=96)
def scaled_construction(key, stage, size):
    return pygame.transform.smoothscale(construction_frame(key, stage), size)


def building_parts(building, camera, workers=True):
    key = building.definition.key
    size, anchor, _ = building_layout(key)
    training = key == "barracks" and building.training_active
    clock = building.training_time if training else building.animation_time
    frame = int(clock * ANIMATION_RATE) % ANIMATION_FRAMES
    scaled_size = (max(1, round(size[0] * camera.zoom)), max(1, round(size[1] * camera.zoom)))
    if building.completed:
        image = scaled_building(key, frame, scaled_size, training)
    else:
        image = scaled_construction(key, round(building.construction_progress * 32), scaled_size)
    if building.owner != "blue":
        image = faction_image(image, building.owner)
    center = camera.world_to_screen(building.position)
    rectangle = image.get_rect(topleft=(round(center.x - anchor[0] * camera.zoom), round(center.y - anchor[1] * camera.zoom)))
    parts = [RenderPart(building.position[1], image, rectangle)]
    if workers and (not building.completed or building.builder_departure > 0):
        parts.extend(builder_parts(building, camera))
    return parts
