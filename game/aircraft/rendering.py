from functools import lru_cache
import math

import pygame

from game.aircraft.art import drone_badge, drone_sprite
from game.aircraft.definitions import FLIGHT_ALTITUDE
from game.rendering import RenderPart
from game.world.faction_art import faction_image


def aircraft_rectangle(drone, camera):
    size = max(25, round(72 * camera.zoom))
    if camera.zoom < .8:
        size = max(24, round(26 * max(1, camera.zoom / camera.minimum_zoom) ** .24))
    position = camera.world_to_screen(drone.position) - pygame.Vector2(0, drone.altitude * camera.zoom)
    return pygame.Rect(round(position.x - size / 2), round(position.y - size / 2), size, size)


def aircraft_opacity(drone):
    height = max(0, min(1, drone.altitude / FLIGHT_ALTITUDE))
    return round(255 - height * 110) if drone.state != "burning" else 255


@lru_cache(maxsize=48)
def soft_shadow(size, opacity):
    image = pygame.Surface((size, max(4, round(size * .35))), pygame.SRCALPHA)
    for inset, alpha in ((0, opacity // 4), (2, opacity // 2), (4, opacity)):
        rectangle = image.get_rect().inflate(-inset * 2, -inset)
        if rectangle.w > 0 and rectangle.h > 0:
            pygame.draw.ellipse(image, (20, 34, 30, alpha), rectangle)
    return image


def shadow_parts(fleet, screen, camera):
    parts = []
    for drone in fleet.drones:
        if drone.state in ("burning", "finished"):
            continue
        size = max(8, round((28 + drone.altitude * .3) * camera.zoom))
        opacity = round(44 - 15 * drone.altitude / FLIGHT_ALTITUDE)
        image = soft_shadow(size, opacity)
        center = camera.world_to_screen(drone.position) + pygame.Vector2(3, 5) * camera.zoom
        rectangle = image.get_rect(center=(round(center.x), round(center.y)))
        if screen.get_rect().colliderect(rectangle):
            parts.append(RenderPart(-math.inf, image, rectangle))
    return parts


def draw_fire(screen, drone, camera):
    center = camera.world_to_screen(drone.position)
    scale = max(.5, camera.zoom)
    overlay = pygame.Surface((max(32, round(64 * scale)), max(48, round(94 * scale))), pygame.SRCALPHA)
    base = pygame.Vector2(overlay.get_width() / 2, overlay.get_height() * .8)
    phase = drone.animation_time
    pygame.draw.ellipse(overlay, (34, 39, 29, 90), (base.x - 15 * scale, base.y - 4 * scale, 30 * scale, 10 * scale))
    for offset in (-1, 1):
        x, y = base.x + offset * 12 * scale, base.y + 2 * scale
        pygame.draw.polygon(overlay, (67, 75, 59, 235), [(x, y), (x + offset * 8 * scale, y - 5 * scale), (x + offset * 5 * scale, y + 4 * scale)])
    for index in range(4):
        progress = (phase * .22 + index / 4) % 1
        x = base.x + (math.sin(progress * 6 + index) * 4 + progress * 6) * scale
        y = base.y - (8 + progress * 55) * scale
        pygame.draw.circle(overlay, (47, 52, 42, round((1 - progress) * 70)), (round(x), round(y)), max(2, round((4 + progress * 8) * scale)))
    for index in range(3):
        sway = math.sin(phase * 6 + index * 2) * 3
        horizontal = base.x + (index - 1) * 5 * scale
        height = (11 + 5 * math.sin(phase * 8 + index)) * scale
        points = [(horizontal - 5 * scale, base.y), (horizontal + sway * scale, base.y - height), (horizontal + 5 * scale, base.y)]
        pygame.draw.polygon(overlay, (229, 111, 43, 210), points)
        pygame.draw.polygon(overlay, (246, 199, 89, 230), [(horizontal - 2 * scale, base.y), (horizontal, base.y - height * .6), (horizontal + 3 * scale, base.y)])
    overlay.set_alpha(round(255 * min(1, max(0, 20 - drone.state_time) / 2)))
    screen.blit(overlay, (round(center.x - base.x), round(center.y - base.y)))


def draw_aircraft(screen, camera, fleet, selected=None):
    for drone in sorted(fleet.drones, key=lambda item: item.altitude):
        rectangle = aircraft_rectangle(drone, camera)
        if not screen.get_rect().inflate(100, 140).colliderect(rectangle):
            continue
        badge = camera.zoom < .8 and drone.controllable
        if badge:
            image = drone_badge(drone.definition.key, rectangle.w, drone is selected)
        else:
            phase = 0 if drone.state == "burning" else int(drone.animation_time * 18) % 8
            image = drone_sprite(drone.definition.key, rectangle.w, round(drone.heading / 2) * 2 % 360, phase, drone is selected, drone.state == "burning")
        if drone.owner != "blue":
            image = faction_image(image, drone.owner)
        opacity = 255 if badge else aircraft_opacity(drone)
        if drone.state == "burning" and drone.state_time > 18:
            opacity = round(opacity * max(0, 20 - drone.state_time) / 2)
        if opacity < 255:
            image = image.copy()
            image.set_alpha(opacity)
        screen.blit(image, rectangle)
        if drone.state == "burning":
            draw_fire(screen, drone, camera)
