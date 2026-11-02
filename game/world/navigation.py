import heapq
import math

import numpy as np
import pygame


class Navigation:
    def __init__(self, terrain, visibility, avoid_trees=False):
        self.terrain = terrain
        self.visibility = visibility
        self.step = 4 if avoid_trees else 8
        self.center_offset = 0 if avoid_trees else 0.5
        self.avoid_trees = avoid_trees
        self.terrain_revision = getattr(terrain, "revision", 0)
        mask = terrain.soldier_walkable if avoid_trees else terrain.walkable
        self.can_place = terrain.can_place_soldier if avoid_trees else terrain.can_place_unit
        self.can_move = terrain.can_move_soldier if avoid_trees else terrain.can_move
        if avoid_trees:
            self.walkable = np.zeros_like(mask)
            self.walkable[1:, 1:] = mask[:-1, :-1] & mask[1:, :-1] & mask[:-1, 1:] & mask[1:, 1:]
        else:
            self.walkable = mask.reshape(mask.shape[0] // 2, 2, mask.shape[1] // 2, 2).all(
                axis=(1, 3)
            )

    def allowed_cells(self):
        revision = getattr(self.terrain, "revision", 0)
        if revision != self.terrain_revision:
            self.__init__(self.terrain, self.visibility, self.avoid_trees)
        return self.walkable

    def cell(self, position):
        return int(position[0] // self.step), int(position[1] // self.step)

    def center(self, cell):
        return (
            (cell[0] + self.center_offset) * self.step,
            (cell[1] + self.center_offset) * self.step,
        )

    def allowed(self, cell, cells):
        return (
            0 <= cell[0] < cells.shape[1]
            and 0 <= cell[1] < cells.shape[0]
            and bool(cells[cell[1], cell[0]])
        )

    def clear_line(self, start, end, cells, check_cells=True):
        if not check_cells:
            return self.can_move(start, end, radius=4)
        start, end = pygame.Vector2(start), pygame.Vector2(end)
        count = max(1, math.ceil(start.distance_to(end) / 8))
        fractions = np.linspace(0, 1, count + 1)
        x = start.x + (end.x - start.x) * fractions
        y = start.y + (end.y - start.y) * fractions
        columns, rows = (x / self.step).astype(np.int32), (y / self.step).astype(np.int32)
        valid = (x >= 0) & (y >= 0) & (columns < cells.shape[1]) & (rows < cells.shape[0])
        if not valid.all():
            return False
        if check_cells and not cells[rows, columns].all():
            return False
        return self.can_move(start, end, radius=4)

    def nearest_destination(self, destination, radius=28):
        destination = pygame.Vector2(destination)
        if not (
            0 <= destination.x < self.walkable.shape[1] * self.step
            and 0 <= destination.y < self.walkable.shape[0] * self.step
        ):
            return None
        if self.can_place(destination, radius=4):
            return destination
        for distance in range(4, radius + 1, 4):
            for index in range(16):
                offset = pygame.Vector2(distance, 0).rotate(index * 22.5)
                point = destination + offset
                if self.can_place(point, radius=4):
                    return point
        return None

    def connector(self, point, cells):
        cell = self.cell(point)
        candidates = [
            (cell[0] + horizontal, cell[1] + vertical)
            for vertical in range(-2, 3)
            for horizontal in range(-2, 3)
        ]
        candidates.sort(
            key=lambda candidate: pygame.Vector2(self.center(candidate)).distance_squared_to(point)
        )
        return next(
            (
                candidate
                for candidate in candidates
                if self.allowed(candidate, cells)
                and self.clear_line(point, self.center(candidate), cells, check_cells=False)
            ),
            None,
        )

    def find_path(self, start, destination, cells):
        iterator = self.iter_path(start, destination, cells)
        while True:
            try:
                next(iterator)
            except StopIteration as result:
                return result.value

    def iter_path(self, start, destination, cells):
        destination = self.nearest_destination(destination)
        if destination is None:
            return None
        if self.clear_line(start, destination, cells, check_cells=False):
            return [tuple(destination)]
        first, last = self.connector(start, cells), self.connector(destination, cells)
        if first is None or last is None:
            return None

        frontier = [(0, 0, first)]
        costs = {first: 0}
        previous = {}
        visits = 0
        while frontier and visits < 80000:
            _, cost, current = heapq.heappop(frontier)
            if cost != costs.get(current):
                continue
            if current == last:
                break
            visits += 1
            if visits % 96 == 0:
                yield None
            for horizontal, vertical in (
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ):
                neighbor = (current[0] + horizontal, current[1] + vertical)
                if not self.allowed(neighbor, cells):
                    continue
                if (
                    horizontal
                    and vertical
                    and not (
                        self.allowed((current[0] + horizontal, current[1]), cells)
                        and self.allowed((current[0], current[1] + vertical), cells)
                    )
                ):
                    continue
                next_cost = cost + (14 if horizontal and vertical else 10)
                if next_cost >= costs.get(neighbor, math.inf):
                    continue
                costs[neighbor] = next_cost
                previous[neighbor] = current
                delta_x, delta_y = abs(neighbor[0] - last[0]), abs(neighbor[1] - last[1])
                heuristic = 10 * max(delta_x, delta_y) + 4 * min(delta_x, delta_y)
                heapq.heappush(frontier, (next_cost + heuristic, next_cost, neighbor))
        if last not in costs or (last != first and last not in previous):
            return None

        chain = [last]
        while chain[-1] != first:
            chain.append(previous[chain[-1]])
        raw = (
            [tuple(start)] + [self.center(cell) for cell in reversed(chain)] + [tuple(destination)]
        )
        route = []
        index = 0
        while index < len(raw) - 1:
            following = min(len(raw) - 1, index + 24)
            while following > index + 1 and not self.clear_line(
                raw[index], raw[following], cells, check_cells=False
            ):
                following -= 1
            if not self.clear_line(raw[index], raw[following], cells, check_cells=False):
                return None
            if len(route) % 4 == 0:
                yield None
            route.append(raw[following])
            index = following
        return route
