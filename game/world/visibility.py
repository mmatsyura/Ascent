from dataclasses import dataclass
import math

import numpy as np
import pygame

from game.settings import FOG_EDGE_WIDTH, WORLD_HEIGHT, WORLD_WIDTH
from game.world.forest_visibility import ForestVisibility


@dataclass(frozen=True)
class VisionSource:
    position: tuple[float, float]
    radius: float
    forest_blocked: bool = False
    territorial: bool = True
    mobile: bool = False
    records_exploration: bool = True


class Visibility:
    def __init__(self, terrain=None):
        self.grid_size = 8
        self.sources = ()
        self.revision = 0
        self.surface = None
        self.field = None
        self.territory_sources = None
        self.territory_field = None
        self.territory_bounds = None
        self.territory_mask = None
        self.static_sources = None
        self.base_territory_field = None
        self.base_vision_field = None
        self.base_bounds = None
        self.territory_revision = 0
        self.country = None
        self.country_revision = -1
        self.contours = []
        self.frame_key = None
        self.frame_surface = None
        self.frame_bounds = None
        self.frame_margin = 144
        self.frame_zoom = None
        self.preview_buffer = None
        self.scaling_buffer = None
        self.mini_cache = {}
        self.forest = ForestVisibility(terrain, self.grid_size) if terrain is not None else None
        self.explored = np.zeros((WORLD_HEIGHT // self.grid_size, WORLD_WIDTH // self.grid_size), dtype=bool)
        self.explored_opacity = 104
        self.exploration_alpha = np.full(self.explored.shape, 255, dtype=np.uint8)
        self.horizontal = np.arange(WORLD_WIDTH // self.grid_size, dtype=np.float32)[None, :] * self.grid_size
        self.vertical = np.arange(WORLD_HEIGHT // self.grid_size, dtype=np.float32)[:, None] * self.grid_size

    def set_sources(self, sources, country=None):
        sources = tuple(sources)
        country_changed = country is not None and country.revision != self.country_revision
        if country is not None:
            self.country = country
            self.country_revision = country.revision
        if sources == self.sources and self.surface is not None and not country_changed:
            return
        self.sources = sources
        width, height = WORLD_WIDTH // self.grid_size, WORLD_HEIGHT // self.grid_size
        previous_field = self.field
        territory_sources = tuple(source for source in sources if source.territorial)
        territory_changed = territory_sources != self.territory_sources or country_changed
        self.territory_sources = territory_sources
        static_sources = tuple(source for source in territory_sources if not source.mobile)
        base_changed = country_changed or static_sources != self.static_sources
        self.static_sources = static_sources
        if base_changed:
            self.base_territory_field = self.country.field.copy() if self.country is not None else np.full((height, width), -100000, dtype=np.float32)
            self.base_vision_field = self.country.vision.copy() if self.country is not None else self.base_territory_field.copy()
            self.base_bounds = self.country.bounds.copy() if self.country is not None else pygame.Rect(0, 0, 0, 0)
            for source in static_sources:
                area, distance = self.source_field(source)
                for field in (self.base_territory_field, self.base_vision_field):
                    patch = field[area.top:area.bottom, area.left:area.right]
                    np.maximum(patch, distance, out=patch)
                self.base_bounds = self.base_bounds.union(area) if self.base_bounds.w else area
        if territory_changed:
            self.territory_field = self.base_territory_field.copy()
            self.territory_bounds = self.base_bounds.copy()
        self.field = self.base_vision_field.copy()
        bounds = self.territory_bounds.copy()
        temporary = []
        for source in sources:
            if source.territorial and not source.mobile:
                continue
            area, distance = self.source_field(source)
            if source.records_exploration:
                patch = self.field[area.top:area.bottom, area.left:area.right]
                np.maximum(patch, distance, out=patch)
            else:
                temporary.append((area, distance))
            bounds = bounds.union(area) if bounds.w else area
            if source.territorial and territory_changed:
                territory_patch = self.territory_field[area.top:area.bottom, area.left:area.right]
                np.maximum(territory_patch, distance, out=territory_patch)
                self.territory_bounds = self.territory_bounds.union(area) if self.territory_bounds.w else area

        self.remember_visible(self.territory_field if territory_changed else None)
        for area, distance in temporary:
            patch = self.field[area.top:area.bottom, area.left:area.right]
            np.maximum(patch, distance, out=patch)

        if not territory_changed and previous_field is not None and np.array_equal(previous_field, self.field):
            return

        left, top, right, bottom = bounds.left, bounds.top, bounds.right, bounds.bottom
        patch = self.field[top:bottom, left:right]
        fade = np.clip(-patch / FOG_EDGE_WIDTH, 0, 1)
        fade = fade * fade * (3 - 2 * fade)
        if self.surface is None:
            self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.surface.fill((0, 0, 0, 255))
        alpha = pygame.surfarray.pixels_alpha(self.surface)
        alpha[:] = self.exploration_alpha.T
        patch_alpha = alpha[left:right, top:bottom]
        np.minimum(patch_alpha, np.round(fade.T * 255).astype(np.uint8), out=patch_alpha)
        del patch_alpha
        del alpha

        if territory_changed:
            mask = self.territory_field >= 0
            if self.territory_mask is None or not np.array_equal(mask, self.territory_mask):
                self.territory_mask = mask
                self.update_territory()
        self.revision += 1
        self.frame_key = None
        self.mini_cache.clear()

    def source_field(self, source):
        reach = source.radius + FOG_EDGE_WIDTH + self.grid_size
        left = max(0, int((source.position[0] - reach) // self.grid_size))
        right = min(WORLD_WIDTH // self.grid_size, math.ceil((source.position[0] + reach) / self.grid_size))
        top = max(0, int((source.position[1] - reach) // self.grid_size))
        bottom = min(WORLD_HEIGHT // self.grid_size, math.ceil((source.position[1] + reach) / self.grid_size))
        area = pygame.Rect(left, top, right - left, bottom - top)
        distance = source.radius - np.hypot(self.horizontal[:, left:right] - source.position[0], self.vertical[top:bottom] - source.position[1])
        if source.forest_blocked and self.forest is not None:
            distance = self.forest.field(source, area)
        return area, distance

    def update_territory(self):
        bounds = self.territory_bounds
        self.contours = []
        self.territory_revision += 1
        self.area = int(np.count_nonzero(self.territory_mask[::8, ::8]))
        if not bounds.w or not bounds.h:
            return
        step = 2
        mask_field = self.territory_mask[bounds.top:bounds.bottom:step, bounds.left:bounds.right:step]
        inside = pygame.Surface((mask_field.shape[1], mask_field.shape[0]), pygame.SRCALPHA)
        alpha = pygame.surfarray.pixels_alpha(inside)
        alpha[:] = mask_field.T.astype(np.uint8) * 255
        del alpha
        mask = pygame.mask.from_surface(inside)
        for component in mask.connected_components():
            points = np.asarray(component.outline(2), dtype=np.float32) * (self.grid_size * step)
            points += np.array(bounds.topleft, dtype=np.float32) * self.grid_size
            if len(points) < 3:
                continue
            for _ in range(2):
                following = np.roll(points, -1, axis=0)
                points = np.stack((points * .75 + following * .25, points * .25 + following * .75), axis=1).reshape(-1, 2)
            self.contours.append(points.tolist())

    def remember_visible(self, territory_field=None):
        visible = self.field >= 0
        if territory_field is not None:
            visible |= territory_field >= 0
        added = visible & ~self.explored
        if not np.any(added):
            return
        self.explored |= visible
        rows = np.flatnonzero(np.any(added, axis=1))
        columns = np.flatnonzero(np.any(added, axis=0))
        height, width = self.explored.shape
        left, right = max(0, int(columns[0]) - 2), min(width, int(columns[-1]) + 3)
        top, bottom = max(0, int(rows[0]) - 2), min(height, int(rows[-1]) + 3)
        sample_left, sample_right = max(0, left - 2), min(width, right + 2)
        sample_top, sample_bottom = max(0, top - 2), min(height, bottom + 2)
        softened = self.explored[sample_top:sample_bottom, sample_left:sample_right].astype(np.float32)
        for _ in range(2):
            horizontal = np.pad(softened, ((0, 0), (1, 1)), mode="edge")
            softened = (horizontal[:, :-2] + horizontal[:, 1:-1] + horizontal[:, 2:]) / 3
            vertical = np.pad(softened, ((1, 1), (0, 0)), mode="edge")
            softened = (vertical[:-2] + vertical[1:-1] + vertical[2:]) / 3
        patch = softened[top - sample_top:bottom - sample_top, left - sample_left:right - sample_left]
        self.exploration_alpha[top:bottom, left:right] = np.rint(255 - patch * (255 - self.explored_opacity)).astype(np.uint8)

    def is_visible(self, position):
        if self.field is None or not (0 <= position[0] < WORLD_WIDTH and 0 <= position[1] < WORLD_HEIGHT):
            return False
        horizontal, vertical = position[0] / self.grid_size, position[1] / self.grid_size
        column, row = int(horizontal), int(vertical)
        next_column = min(column + 1, self.field.shape[1] - 1)
        next_row = min(row + 1, self.field.shape[0] - 1)
        fraction_x, fraction_y = horizontal - column, vertical - row
        top = self.field[row, column] * (1 - fraction_x) + self.field[row, next_column] * fraction_x
        bottom = self.field[next_row, column] * (1 - fraction_x) + self.field[next_row, next_column] * fraction_x
        return bool(top * (1 - fraction_y) + bottom * fraction_y >= 0)

    def is_explored(self, position):
        if not (0 <= position[0] < WORLD_WIDTH and 0 <= position[1] < WORLD_HEIGHT):
            return False
        column, row = int(position[0] // self.grid_size), int(position[1] // self.grid_size)
        return bool(self.explored[row, column])

    def is_known(self, position):
        return self.is_visible(position) or self.is_explored(position)

    def points_known(self, x, y):
        horizontal, vertical = x / self.grid_size, y / self.grid_size
        columns = np.clip(horizontal.astype(np.int32), 0, self.field.shape[1] - 1)
        rows = np.clip(vertical.astype(np.int32), 0, self.field.shape[0] - 1)
        following_columns = np.minimum(columns + 1, self.field.shape[1] - 1)
        following_rows = np.minimum(rows + 1, self.field.shape[0] - 1)
        dx, dy = horizontal - columns, vertical - rows
        top = self.field[rows, columns] * (1 - dx) + self.field[rows, following_columns] * dx
        bottom = self.field[following_rows, columns] * (1 - dx) + self.field[following_rows, following_columns] * dx
        return self.explored[rows, columns] | (top * (1 - dy) + bottom * dy >= 0)

    def visible_cells(self, shape, step, center_offset):
        horizontal = (np.arange(shape[1], dtype=np.float32)[None, :] + center_offset) * step / self.grid_size
        vertical = (np.arange(shape[0], dtype=np.float32)[:, None] + center_offset) * step / self.grid_size
        columns = np.clip(horizontal.astype(np.int32), 0, self.field.shape[1] - 1)
        rows = np.clip(vertical.astype(np.int32), 0, self.field.shape[0] - 1)
        next_columns = np.minimum(columns + 1, self.field.shape[1] - 1)
        next_rows = np.minimum(rows + 1, self.field.shape[0] - 1)
        fraction_x = horizontal - columns.astype(np.float32)
        fraction_y = vertical - rows.astype(np.float32)
        top = self.field[rows, columns] * (1 - fraction_x) + self.field[rows, next_columns] * fraction_x
        bottom = self.field[next_rows, columns] * (1 - fraction_x) + self.field[next_rows, next_columns] * fraction_x
        return top * (1 - fraction_y) + bottom * fraction_y >= 0

    def known_cells(self, shape, step, center_offset):
        if shape == self.field.shape and step == self.grid_size and center_offset == .5:
            padded = np.pad(self.field, ((0, 1), (0, 1)), mode="edge")
            middle = padded[:-1, :-1] + padded[:-1, 1:]
            middle += padded[1:, :-1]
            middle += padded[1:, 1:]
            return self.explored | (middle >= 0)
        horizontal = ((np.arange(shape[1]) + center_offset) * step / self.grid_size).astype(np.int32)
        vertical = ((np.arange(shape[0]) + center_offset) * step / self.grid_size).astype(np.int32)
        horizontal = np.clip(horizontal, 0, self.explored.shape[1] - 1)
        vertical = np.clip(vertical, 0, self.explored.shape[0] - 1)
        return self.explored[vertical[:, None], horizontal[None, :]] | self.visible_cells(shape, step, center_offset)

    def draw(self, screen, camera):
        zoom_changed = self.frame_zoom is not None and self.frame_zoom != camera.zoom
        self.frame_zoom = camera.zoom
        preview = zoom_changed or camera.zoom != camera.target_zoom
        key = (camera.zoom, camera.viewport_size, self.revision, preview)
        size = camera.viewport_size
        left = camera.position.x - size[0] / camera.zoom / 2
        top = camera.position.y - size[1] / camera.zoom / 2
        view_right = left + size[0] / camera.zoom
        view_bottom = top + size[1] / camera.zoom
        covered = (self.frame_bounds is not None and self.frame_bounds[0] <= left and self.frame_bounds[1] <= top
                   and self.frame_bounds[2] >= view_right and self.frame_bounds[3] >= view_bottom)
        if key != self.frame_key or not covered:
            margin = 0 if preview else self.frame_margin / camera.zoom
            column = max(0, math.floor((left - margin) / self.grid_size))
            row = max(0, math.floor((top - margin) / self.grid_size))
            right = min(self.surface.get_width(), math.ceil((view_right + margin) / self.grid_size))
            bottom = min(self.surface.get_height(), math.ceil((view_bottom + margin) / self.grid_size))
            area = pygame.Rect(column, row, right - column, bottom - row)
            scale = self.grid_size * camera.zoom
            scaled_size = (math.ceil(area.w * scale), math.ceil(area.h * scale))
            buffer_size = (size[0] + self.frame_margin * 2 + 40, size[1] + self.frame_margin * 2 + 40)
            if self.scaling_buffer is None or self.scaling_buffer.get_size() != buffer_size:
                self.scaling_buffer = pygame.Surface(buffer_size, pygame.SRCALPHA)
            scaled = self.scaling_buffer.subsurface((0, 0, *scaled_size))
            if preview:
                preview_size = ((scaled_size[0] + 1) // 2, (scaled_size[1] + 1) // 2)
                if self.preview_buffer is None or self.preview_buffer.get_width() < preview_size[0] or self.preview_buffer.get_height() < preview_size[1]:
                    self.preview_buffer = pygame.Surface(((buffer_size[0] + 1) // 2, (buffer_size[1] + 1) // 2), pygame.SRCALPHA)
                working = self.preview_buffer.subsurface((0, 0, *preview_size))
            else:
                working = scaled
            pygame.transform.smoothscale(self.surface.subsurface(area), working.get_size(), working)
            alpha = pygame.surfarray.pixels_alpha(working)
            alpha[alpha >= 250] = 255
            del alpha
            if preview:
                pygame.transform.scale(working, scaled_size, scaled)
            origin_x, origin_y = column * self.grid_size, row * self.grid_size
            for contour in self.contours:
                if len(contour) > 2:
                    points = [(round((horizontal - origin_x) * camera.zoom), round((vertical - origin_y) * camera.zoom)) for horizontal, vertical in contour]
                    pygame.draw.lines(scaled, (0, 0, 0, 255), True, points, 2)
            self.frame_surface = scaled
            self.frame_bounds = (origin_x, origin_y, right * self.grid_size, bottom * self.grid_size)
            self.frame_key = key
        position = (round((self.frame_bounds[0] - left) * camera.zoom), round((self.frame_bounds[1] - top) * camera.zoom))
        screen.blit(self.frame_surface, position)

    def draw_minimap(self, screen, map_area):
        key = (map_area.size, self.revision)
        if key not in self.mini_cache:
            overlay = pygame.transform.smoothscale(self.surface, map_area.size)
            alpha = pygame.surfarray.pixels_alpha(overlay)
            alpha[alpha >= 250] = 255
            del alpha
            for contour in self.contours:
                if len(contour) > 2:
                    points = [(round(horizontal / WORLD_WIDTH * map_area.w), round(vertical / WORLD_HEIGHT * map_area.h)) for horizontal, vertical in contour]
                    pygame.draw.lines(overlay, (0, 0, 0, 255), True, points, 1)
            self.mini_cache[key] = overlay
        screen.blit(self.mini_cache[key], map_area)
