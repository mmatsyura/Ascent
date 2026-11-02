import numpy as np
import pygame

from game.camera import Camera
from game.world.building_rendering import building_parts
from game.world.cities import city_color, marker_image
from game.world.faction_visuals import flag_image
from game.world.unit_visuals import unit_parts


def take_photo(terrain, target, kind, drone, cities=None):
    size = (320, 180)
    camera = Camera(size)
    camera.position.update(target.position)
    camera.zoom = camera.target_zoom = 1.1
    camera.constrain()
    photo = pygame.Surface(size).convert()
    camera.draw(photo, terrain, scenery=True)
    if kind == "city":
        point = camera.world_to_screen(target.position)
        marker = marker_image(target.capital, 14 if target.capital else 6, city_color(target))
        photo.blit(marker, marker.get_rect(center=(round(point.x), round(point.y))))
        if target.capital and target.flag_color is not None:
            frame = cities.flag_frame(target) if cities is not None else 0
            flag = flag_image(target.flag_color, 32, frame)
            photo.blit(flag, (round(point.x) - 4, round(point.y) - 32))
    else:
        parts = (
            building_parts(target, camera)
            if kind == "building"
            else unit_parts(target, photo, camera)
        )
        for part in parts:
            photo.blit(part.image, part.rectangle)
    top_left = camera.screen_to_world((0, 0))
    horizontal = top_left.x + np.arange(size[0], dtype=np.float32)[:, None] / camera.zoom
    vertical = top_left.y + np.arange(size[1], dtype=np.float32)[None, :] / camera.zoom
    distance = np.hypot(horizontal - drone.position[0], vertical - drone.position[1])
    mask = pygame.Surface(size, pygame.SRCALPHA)
    alpha = pygame.surfarray.pixels_alpha(mask)
    alpha[:] = np.rint(np.clip((distance - drone.vision_radius + 12) / 12, 0, 1) * 255).astype(
        np.uint8
    )
    del alpha
    photo.blit(mask, (0, 0))
    pygame.draw.rect(photo, (136, 166, 144), photo.get_rect(), 1)
    center = camera.world_to_screen(target.position)
    for side_x in (-1, 1):
        for side_y in (-1, 1):
            first = (round(center.x + side_x * 13), round(center.y + side_y * 11))
            pygame.draw.line(photo, (224, 188, 113), first, (first[0] - side_x * 5, first[1]), 1)
            pygame.draw.line(photo, (224, 188, 113), first, (first[0], first[1] - side_y * 5), 1)
    return pygame.transform.smoothscale(photo, (160, 90))
