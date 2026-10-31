from collections import OrderedDict
import math

import pygame

from game.world.unit_visuals import unit_parts
from game.world.building_rendering import building_parts
from game.settings import FOREST_CLEAR_RADIUS, FOREST_FADE_RADIUS
from game.world.tank_tracks import trail_part
from game.world.reveals import faded_parts
from game.world.screen_regions import dirty_regions


class ForestRendering:
    def __init__(self, world_renderer):
        self.world_renderer = world_renderer
        self.fading_trees = {}
        self.scaled_images = OrderedDict()
        self.still_frame = None
        self.still_key = None
        self.still_images = []
        self.camera_key = None
        self.tree_queries = OrderedDict()
        self.fade_targets = {}
        self.fade_timer = .12
        self.ground_frame = None
        self.ground_key = None
        self.tree_layer_key = None
        self.tree_layers = {}

    def nearby_trees(self, area):
        key = tuple(area)
        if key in self.tree_queries:
            self.tree_queries.move_to_end(key)
            return self.tree_queries[key]
        renderer = self.world_renderer
        result = []
        expanded = area.inflate(160, 200)
        for row in range(math.floor(expanded.top / renderer.chunk_size), math.floor(expanded.bottom / renderer.chunk_size) + 1):
            for column in range(math.floor(expanded.left / renderer.chunk_size), math.floor(expanded.right / renderer.chunk_size) + 1):
                result.extend(tree for tree in renderer.chunks.get((column, row), ()) if tree.bounds.colliderect(area))
        self.tree_queries[key] = result
        if len(self.tree_queries) > 128:
            self.tree_queries.popitem(last=False)
        return result

    def update(self, units, elapsed_seconds, camera=None):
        self.fade_timer += elapsed_seconds
        if self.fade_timer >= .12:
            self.fade_timer %= .12
            self.update_fade_targets(units, camera)
        blend = -math.expm1(-elapsed_seconds / .22)
        for tree_id, state in list(self.fading_trees.items()):
            target = self.fade_targets.get(tree_id, 255)
            state[1] += (target - state[1]) * blend
            if abs(state[1] - target) < .5:
                state[1] = target
            if state[1] == 255:
                del self.fading_trees[tree_id]

    def update_fade_targets(self, units, camera):
        self.fade_targets = {}
        reach = FOREST_FADE_RADIUS
        visible = camera.visible_area.inflate(reach * 3, reach * 3) if camera is not None else None
        groups = {}
        for unit in units:
            if unit.owner != "blue" or not unit.in_forest or (visible is not None and not visible.collidepoint(unit.position)):
                continue
            cell = math.floor(unit.position[0] / reach), math.floor(unit.position[1] / reach)
            groups.setdefault(cell, []).append(unit.position)
        trees = {}
        for column, row in groups:
            area = pygame.Rect((column - 1) * reach, (row - 1) * reach, reach * 3, reach * 3)
            trees.update((id(tree), tree) for tree in self.nearby_trees(area))
        for tree_id, tree in trees.items():
            x, y = tree.position
            column, row = math.floor(x / reach), math.floor(y / reach)
            distance_squared = reach * reach
            for row_offset in (-1, 0, 1):
                for column_offset in (-1, 0, 1):
                    for unit_x, unit_y in groups.get((column + column_offset, row + row_offset), ()):
                        distance_squared = min(distance_squared, (unit_x - x) ** 2 + (unit_y - y) ** 2)
            strength = max(0, min(1, (reach - math.sqrt(distance_squared)) / (reach - FOREST_CLEAR_RADIUS)))
            if strength <= 0:
                continue
            strength = strength * strength * (3 - 2 * strength)
            self.fade_targets[tree_id] = 255 - 153 * strength
            self.fading_trees.setdefault(tree_id, [tree, 255.0])

    def tree_image(self, tree, zoom):
        size = (max(1, round(tree.image.get_width() * zoom)), max(1, round(tree.image.get_height() * zoom)))
        key = (id(tree.image), size)
        if key not in self.scaled_images:
            self.scaled_images[key] = pygame.transform.smoothscale(tree.image, size)
            if len(self.scaled_images) > 256:
                self.scaled_images.popitem(last=False)
        else:
            self.scaled_images.move_to_end(key)
        image = self.scaled_images[key]
        state = self.fading_trees.get(id(tree))
        if state is not None:
            image = image.copy()
            image.set_alpha(round(state[1]))
        return image

    def world_area(self, rectangle, camera):
        corner = camera.screen_to_world(rectangle.topleft)
        return pygame.Rect(math.floor(corner.x), math.floor(corner.y), math.ceil(rectangle.w / camera.zoom) + 2, math.ceil(rectangle.h / camera.zoom) + 2)

    def draw(self, screen, camera, terrain, units, buildings=(), city_map=None, visibility=None, ground_parts=()):
        regions = []
        visible_parts = []
        screen_area = screen.get_rect()
        visible_world = camera.visible_area.inflate(400, 400)
        reveals = getattr(city_map, "reveals", None)
        for part in ground_parts:
            if screen_area.colliderect(part.rectangle):
                visible_parts.append((part, part.rectangle))
                regions.append(part.rectangle.inflate(2, 2).clip(screen_area))
        units = [unit for unit in units if unit.owner == "blue" or visibility is None or visibility.is_visible(unit.position)]
        for unit in units:
            if unit.is_tank and unit.owner == "blue":
                part = trail_part(unit, screen, camera)
                if part is not None:
                    visible_parts.append((part, part.rectangle))
                    regions.append(part.rectangle.inflate(3, 3).clip(screen_area))
        if city_map is not None:
            for part in city_map.draw_parts(screen, camera):
                if screen_area.colliderect(part.rectangle):
                    visible_parts.append((part, part.rectangle))
                    regions.append(part.rectangle.inflate(4, 4).clip(screen_area))
        for unit in units:
            if not visible_world.collidepoint(unit.position):
                continue
            parts = unit_parts(unit, screen, camera, terrain)
            if reveals is not None:
                parts = faded_parts(parts, reveals.unit_opacity(unit))
            for part in parts:
                rectangle = part.rectangle
                if not screen_area.colliderect(rectangle):
                    continue
                visible_parts.append((part, rectangle))
                regions.append(rectangle.inflate(3, 3).clip(screen_area))

        for building in buildings:
            if not visible_world.collidepoint(building.position):
                continue
            parts = building_parts(building, camera)
            if reveals is not None:
                parts = faded_parts(parts, reveals.building_opacity(building))
            for part in parts:
                if screen_area.colliderect(part.rectangle):
                    visible_parts.append((part, part.rectangle))
                    regions.append(part.rectangle.inflate(6, 6).clip(screen_area))

        visible_parts.sort(key=lambda item: item[0].depth)
        camera_key = (camera.position.x, camera.position.y, camera.zoom, camera.viewport_size, getattr(terrain, "revision", 0))
        tree_key = tuple((tree_id, round(state[1])) for tree_id, state in self.fading_trees.items())
        layer_key = camera_key, tree_key
        if layer_key != self.tree_layer_key:
            self.tree_layers.clear()
            self.tree_layer_key = layer_key
        part_key = tuple((part.depth, id(part.image), tuple(rectangle)) for part, rectangle in visible_parts)
        frame_key = (camera_key, tree_key, part_key)
        if frame_key == self.still_key and self.still_frame is not None:
            screen.blit(self.still_frame, (0, 0))
            return
        for tree, opacity in self.fading_trees.values():
            bounds = tree.bounds
            corner = camera.world_to_screen(bounds.topleft)
            rectangle = pygame.Rect(math.floor(corner.x) - 2, math.floor(corner.y) - 2, math.ceil(bounds.w * camera.zoom) + 4, math.ceil(bounds.h * camera.zoom) + 4)
            rectangle = rectangle.clip(screen_area)
            if rectangle.w and rectangle.h:
                regions.append(rectangle)

        regions = dirty_regions(regions, screen_area)
        if regions:
            if self.ground_key != camera_key or self.ground_frame is None:
                if self.ground_frame is None or self.ground_frame.get_size() != screen.get_size():
                    self.ground_frame = pygame.Surface(screen.get_size()).convert()
                self.ground_frame.fill((0, 0, 0))
                camera.draw(self.ground_frame, terrain)
                self.ground_key = camera_key
            previous_clip = screen.get_clip()
            for region in regions:
                screen.set_clip(region)
                screen.blit(self.ground_frame, region, region)
                region_key = tuple(region)
                if region_key not in self.tree_layers:
                    if len(self.tree_layers) >= 128:
                        self.tree_layers.pop(next(iter(self.tree_layers)))
                    trees = []
                    for tree in self.nearby_trees(self.world_area(region, camera)):
                        position = camera.world_to_screen(tree.position) - pygame.Vector2(tree.anchor) * camera.zoom
                        trees.append((tree.position[1], 0, (self.tree_image(tree, camera.zoom), (round(position.x), round(position.y)))))
                    self.tree_layers[region_key] = trees
                layers = self.tree_layers[region_key].copy()
                layers.extend((part.depth, 1, (part.image, rectangle)) for part, rectangle in visible_parts if region.colliderect(rectangle))
                layers.sort(key=lambda layer: (layer[0], layer[1]))
                screen.blits([layer[2] for layer in layers], doreturn=False)
            screen.set_clip(previous_clip)

        if regions and camera_key == self.camera_key and not any(unit.route or any(member.walking for member in unit.members) for unit in units):
            if self.still_frame is None or self.still_frame.get_size() != screen.get_size():
                self.still_frame = screen.copy()
            else:
                self.still_frame.blit(screen, (0, 0))
            self.still_key = frame_key
            self.still_images = [part.image for part, _ in visible_parts]
        else:
            self.still_key = None
            self.still_images = []
        self.camera_key = camera_key
