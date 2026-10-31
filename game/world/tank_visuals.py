import pygame

from game.rendering import RenderPart
from game.world.tank_art import tank_badge, tank_sprite
from game.world.tank_geometry import TANK_RENDER_SIZE
from game.world.units import detail_blend, token_rectangle
from game.world.water_rendering import water_image
from game.world.patriot_art import patriot_badge, patriot_sprite


def tank_parts(unit, screen, camera):
    blend = detail_blend(camera.zoom)
    parts = []
    if blend < 1:
        rectangle = token_rectangle(unit, screen, camera)
        image = patriot_badge(rectangle.w, unit.selected) if unit.is_patriot else tank_badge(rectangle.w, unit.selected)
        if blend > 0:
            image = image.copy()
            image.set_alpha(round((1 - blend) * 255))
        parts.append(RenderPart(unit.position[1], image, rectangle))
    if blend > 0:
        size = max(24, round(TANK_RENDER_SIZE * camera.zoom * unit.visual_scale))
        if unit.is_patriot:
            image = patriot_sprite(size, round(unit.hull_angle / 2) * 2 % 360, round(unit.deployment * 32), int(unit.travelled / 2) % 4, unit.selected)
        else:
            image = tank_sprite(size, round(unit.hull_angle / 2) * 2 % 360, round(unit.turret_angle / 2) * 2 % 360, int(unit.travelled / 1.5) % 4, unit.selected)
        image = water_image(image, unit.immersion, unit.squad_time, .52 if unit.is_patriot else .10)
        if blend < 1:
            image = image.copy()
            image.set_alpha(round(blend * 255))
        center = camera.world_to_screen(unit.position)
        if unit.recoil and not unit.is_patriot:
            center -= pygame.Vector2(0,-1).rotate(unit.turret_angle)*unit.recoil*2.5*camera.zoom
        parts.append(RenderPart(unit.position[1], image, image.get_rect(center=(round(center.x), round(center.y)))))
    return parts
