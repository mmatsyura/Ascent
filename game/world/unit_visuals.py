from functools import lru_cache

import numpy as np
import pygame

from game.world.soldier_art import soldier_image
from game.world.squad_motion import OFFSETS, SQUAD_RADIUS, initialize_squad
from game.world.units import detail_blend, token_image, token_rectangle
from game.rendering import RenderPart as UnitDrawPart
from game.world.tank_visuals import tank_parts
from game.world.faction_art import faction_image
from game.world.water_rendering import water_image


@lru_cache(maxsize=96)
def blend_pose_images(previous, current, step):
    if step <= 0:
        return previous
    if step >= 32:
        return current
    progress = step / 32
    previous_alpha = pygame.surfarray.array_alpha(previous).astype(np.float32) * (1 - progress)
    current_alpha = pygame.surfarray.array_alpha(current).astype(np.float32) * progress
    alpha = previous_alpha + current_alpha
    colors = pygame.surfarray.array3d(previous).astype(np.float32) * previous_alpha[..., None]
    colors += pygame.surfarray.array3d(current).astype(np.float32) * current_alpha[..., None]
    np.divide(colors, alpha[..., None], out=colors, where=alpha[..., None] > 0)
    image = pygame.Surface(previous.get_size(), pygame.SRCALPHA)
    pygame.surfarray.blit_array(image, np.rint(colors).clip(0, 255).astype(np.uint8))
    pixels = pygame.surfarray.pixels_alpha(image)
    pixels[:] = np.rint(alpha).clip(0, 255).astype(np.uint8)
    del pixels
    return image


def formation_positions(unit, diameter=None, camera=None, terrain=None):
    if not unit.members and terrain is not None:
        initialize_squad(unit, terrain)
    if unit.members:
        return [tuple(member.previous_position.lerp(member.position, unit.member_blend)) if member.previous_position is not None else tuple(member.position) for member in unit.members]
    return [tuple(pygame.Vector2(unit.position) + pygame.Vector2(offset) * SQUAD_RADIUS) for offset in OFFSETS]


def unit_parts(unit, screen, camera, terrain=None):
    if unit.is_tank:
        parts = tank_parts(unit, screen, camera)
        if unit.owner != "blue":
            parts = [UnitDrawPart(part.depth, faction_image(part.image, unit.owner), part.rectangle) for part in parts]
        return parts
    rectangle = token_rectangle(unit, screen, camera)
    blend = detail_blend(camera.zoom)
    parts = []
    if blend < 1:
        image = token_image(rectangle.w, unit.selected)
        if blend > 0:
            image = image.copy()
            image.set_alpha(round((1 - blend) * 255))
        parts.append(UnitDrawPart(unit.position[1], image, rectangle))
    if blend > 0:
        height = max(12, round(26 * camera.zoom * unit.visual_scale))
        positions = formation_positions(unit, terrain=terrain)
        for index, point in enumerate(positions):
            member = unit.members[index] if unit.members else None
            direction = member.facing if member else pygame.Vector2(unit.facing)
            facing = "back" if direction.y < -.4 else ("left" if direction.x < -.25 else "front")
            phase = int(member.phase) % 16 if member and member.walking else 0
            pose = member.pose if member else "stand"
            image = soldier_image(height, unit.selected, phase, facing, pose)
            if member and member.pose_blend < 1:
                previous = soldier_image(height, unit.selected, phase, facing, member.previous_pose)
                image = blend_pose_images(previous, image, round(member.pose_blend * 32))
            image = water_image(image, member.immersion if member else unit.immersion, unit.squad_time + index * .4)
            if blend < 1:
                image = image.copy()
                image.set_alpha(round(blend * 255))
            position = camera.world_to_screen(point)
            area = image.get_rect(midbottom=(round(position.x), round(position.y + height * .04)))
            parts.append(UnitDrawPart(point[1], image, area))
    if unit.owner != "blue":
        parts = [UnitDrawPart(part.depth, faction_image(part.image, unit.owner), part.rectangle) for part in parts]
    return parts
