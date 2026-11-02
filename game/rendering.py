from collections import OrderedDict
from dataclasses import dataclass
from functools import cached_property
import math

import pygame


@dataclass
class RenderPart:
    depth: float
    image: pygame.Surface
    rectangle: pygame.Rect


@dataclass(eq=False)
class WorldSprite:
    image: pygame.Surface
    position: tuple[float, float]
    anchor: tuple[float, float]

    @cached_property
    def bounds(self):
        return pygame.Rect(
            self.position[0] - self.anchor[0],
            self.position[1] - self.anchor[1],
            *self.image.get_size(),
        )


class WorldRenderer:
    def __init__(self, scenery):
        self.chunk_size = 256
        self.chunks = {}
        self.scaled_images = OrderedDict()
        self.frame_surface = None
        self.frame_key = None
        self.frame_position = None
        self.frame_margin = 96
        self.frame_zoom = None
        self.scenery = scenery
        self.scenery_revision = None

        for sprite in scenery:
            chunk = (
                int(sprite.position[0] // self.chunk_size),
                int(sprite.position[1] // self.chunk_size),
            )
            self.chunks.setdefault(chunk, []).append(sprite)

    def draw_scene(self, screen, camera, terrain, actors=()):
        revision = getattr(terrain, "revision", 0)
        if revision != self.scenery_revision:
            self.chunks.clear()
            for sprite in self.scenery:
                chunk = (
                    int(sprite.position[0] // self.chunk_size),
                    int(sprite.position[1] // self.chunk_size),
                )
                self.chunks.setdefault(chunk, []).append(sprite)
            self.scenery_revision = revision
            self.frame_key = None
        if actors:
            camera.draw(screen, terrain)
            self.draw(screen, camera, actors)
            return

        frame_key = (
            camera.zoom,
            camera.viewport_size,
            revision,
            tuple(camera.render_bounds) if camera.render_bounds is not None else None,
        )
        zoom_changed = self.frame_zoom is not None and camera.zoom != self.frame_zoom
        self.frame_zoom = camera.zoom
        margin = 0 if zoom_changed or camera.zoom != camera.target_zoom else self.frame_margin
        frame_size = (camera.viewport_size[0] + margin * 2, camera.viewport_size[1] + margin * 2)
        if (
            self.frame_surface is None
            or self.frame_surface.get_width() < frame_size[0]
            or self.frame_surface.get_height() < frame_size[1]
        ):
            self.frame_surface = pygame.Surface(
                (
                    camera.viewport_size[0] + self.frame_margin * 2,
                    camera.viewport_size[1] + self.frame_margin * 2,
                )
            ).convert()
            self.frame_key = None

        displacement = (
            (self.frame_position - camera.position) * camera.zoom
            if self.frame_position is not None
            else pygame.Vector2()
        )
        frame_key += (margin,)
        if frame_key != self.frame_key or max(abs(displacement.x), abs(displacement.y)) > max(
            0, margin - 4
        ):
            area = pygame.Rect(-margin, -margin, *frame_size)
            frame = self.frame_surface.subsurface((0, 0, *frame_size))
            frame.fill((0, 0, 0))
            camera.draw(frame, terrain, scenery=True, area=area, offset=(margin, margin))
            self.frame_key = frame_key
            self.frame_position = camera.position.copy()
            displacement.update(0, 0)

        screen.blit(
            self.frame_surface,
            (round(displacement.x) - margin, round(displacement.y) - margin),
            (0, 0, *frame_size),
        )

    def visible_sprites(self, visible_area, actors):
        query_area = visible_area.inflate(160, 200)
        sprites = []

        for row in range(
            math.floor(query_area.top / self.chunk_size),
            math.floor(query_area.bottom / self.chunk_size) + 1,
        ):
            for column in range(
                math.floor(query_area.left / self.chunk_size),
                math.floor(query_area.right / self.chunk_size) + 1,
            ):
                sprites.extend(
                    sprite
                    for sprite in self.chunks.get((column, row), ())
                    if query_area.collidepoint(sprite.position)
                )

        sprites.extend(actor for actor in actors if query_area.colliderect(actor.bounds))
        sprites.sort(key=lambda sprite: sprite.position[1])
        return sprites

    def draw(self, screen, camera, actors=()):
        screen_offset_x = camera.viewport_size[0] / 2 - camera.position.x * camera.zoom
        screen_offset_y = camera.viewport_size[1] / 2 - camera.position.y * camera.zoom

        blits = []
        for sprite in self.visible_sprites(camera.visible_area, actors):
            scaled_size = (
                max(1, round(sprite.image.get_width() * camera.zoom)),
                max(1, round(sprite.image.get_height() * camera.zoom)),
            )
            image_key = (id(sprite.image), *scaled_size)
            cached_image = self.scaled_images.get(image_key)

            if cached_image is None or cached_image[0] is not sprite.image:
                cached_image = (
                    sprite.image,
                    pygame.transform.smoothscale(sprite.image, scaled_size),
                )
                self.scaled_images[image_key] = cached_image
                if len(self.scaled_images) > 512:
                    self.scaled_images.popitem(last=False)
            else:
                self.scaled_images.move_to_end(image_key)

            screen_x = (sprite.position[0] - sprite.anchor[0]) * camera.zoom + screen_offset_x
            screen_y = (sprite.position[1] - sprite.anchor[1]) * camera.zoom + screen_offset_y
            blits.append((cached_image[1], (round(screen_x), round(screen_y))))

        screen.blits(blits, doreturn=False)


def prepared_sprite(image):
    image.set_alpha(image.get_alpha(), pygame.RLEACCEL)
    return image
