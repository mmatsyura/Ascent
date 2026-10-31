import math

import pygame

from game.settings import UNIT_FOREST_SPEED_FACTOR, UNIT_SPEED, UNIT_WATER_SPEED
from game.world.biomes import Biome
from game.ui.fonts import ui_font
from game.world.navigation import Navigation
from game.world.path_planner import PathPlanner
from game.world.member_paths import MemberPaths
from game.world.routes import simplify_route
from game.world.squad_motion import cohesion_speed, initialize_squad, update_squad_timed
from game.world.squad_separation import SquadSeparation
from game.world.units import detail_blend, selection_rectangle, token_rectangle
from game.world.tank_motion import tank_drive_factor, update_tank


class UnitControl:
    def __init__(self, units, terrain, visibility, place_units=True):
        self.units = units
        self.terrain = terrain
        self.visibility = visibility
        self.on_acknowledge = None
        self.navigation = Navigation(terrain, visibility)
        self.path_planner = PathPlanner(self.navigation, self.notify)
        self.soldier_navigation = Navigation(terrain, visibility, avoid_trees=True)
        self.soldier_navigation.member_paths = MemberPaths(self.soldier_navigation)
        self.separation = SquadSeparation(units, visibility)
        self.mode = None
        self.pointer_button = None
        self.start_pointer = pygame.Vector2()
        self.pointer = pygame.Vector2()
        self.points = []
        self.route_mode = False
        self.message = ""
        self.message_time = 0
        self.message_opacity = 0
        self.order_feedback = []
        self.feedback_time = 0
        self.font = ui_font(15)
        for unit in units:
            if place_units:
                self.place_at_city(unit)
            unit.update_environment(terrain.biome_at(unit.position), 0)
            if not unit.is_tank:
                initialize_squad(unit, terrain, self.soldier_navigation, self.deployment_allowed if not place_units else None)

    def deployment_allowed(self, point):
        if self.terrain.biome_at(point) not in (Biome.MEADOW, Biome.FOREST, Biome.BEACH):
            return False
        return self.visibility.is_visible(point)

    @property
    def selected(self):
        return [unit for unit in self.units if unit.selected]

    @property
    def owned_units(self):
        return [unit for unit in self.units if unit.owner == "blue"]

    def acknowledge(self, units, action="select"):
        if self.on_acknowledge is not None:
            responders = [unit for unit in units if unit.owner == "blue" and unit.movable]
            if responders:
                self.on_acknowledge(responders, action)

    def unit_at(self, position, screen, camera):
        world = camera.screen_to_world(position)
        candidates = [unit for unit in self.units if unit.owner == "blue" and unit.movable
                      and abs(unit.position[0] - world.x) < 240 and abs(unit.position[1] - world.y) < 240
                      and selection_rectangle(unit, screen, camera).collidepoint(position)]

        def distance(unit):
            centers = [pygame.Vector2(token_rectangle(unit, screen, camera).center)]
            if detail_blend(camera.zoom) > 0:
                centers.extend(camera.world_to_screen(member.position) - pygame.Vector2(0, 12 * camera.zoom) for member in unit.members)
            return min(point.distance_squared_to(position) for point in centers)

        return min(candidates, key=distance, default=None)

    def place_at_city(self, unit):
        origin = pygame.Vector2(unit.position)
        unit.home_city = tuple(origin)
        offsets = [(0, 64), (64, 0), (-64, 0), (0, -64), (0, 0)]
        if unit.is_tank:
            offsets = [pygame.Vector2(0, distance).rotate(angle) for distance in (88, 112, 144) for angle in (0, 60, -60, 120, -120, 180)]
        for offset in offsets:
            candidate = origin + offset
            cell = self.navigation.cell(candidate)
            if self.navigation.allowed(cell, self.navigation.walkable) and self.terrain.can_place_unit(candidate, 24 if unit.is_tank else 4):
                unit.position = tuple(candidate)
                return

    def cancel(self, deselect=False):
        self.mode = None
        self.pointer_button = None
        self.points = []
        if deselect:
            for unit in self.units:
                unit.selected = False

    def begin(self, position, modifiers, screen, camera):
        self.pointer_button = 1
        self.start_pointer.update(position)
        self.pointer.update(position)
        self.route_mode = bool(modifiers & pygame.KMOD_SHIFT)
        if modifiers & pygame.KMOD_CTRL:
            self.mode = "selection"
            self.points = []
            return True
        hit = self.unit_at(position, screen, camera)
        if hit is not None:
            if not hit.selected:
                for unit in self.units:
                    unit.selected = unit is hit
            self.mode = "unit_route"
            self.points = [camera.screen_to_world(position)]
            self.acknowledge(self.selected)
            return True
        if self.selected:
            return self.begin_order(position, modifiers, camera)
        return False

    def begin_order(self, position, modifiers, camera, button=1):
        self.pointer_button = button
        self.start_pointer.update(position)
        self.pointer.update(position)
        self.route_mode = bool(modifiers & pygame.KMOD_SHIFT)
        self.mode = "ground_order"
        self.points = [camera.screen_to_world(position)]
        return True

    def motion(self, position, camera):
        self.pointer.update(position)
        if self.mode not in ("unit_route", "ground_order"):
            return
        point = camera.screen_to_world(position)
        if self.points[-1].distance_to(point) >= max(16, 6 / camera.zoom) and len(self.points) < 64:
            self.points.append(point)

    def end(self, position, screen, camera, blocked=False):
        if self.mode is None:
            return False
        mode = self.mode
        self.pointer.update(position)
        if blocked:
            self.cancel()
            return True
        moved = self.start_pointer.distance_to(self.pointer) > 6
        if mode == "selection":
            if moved:
                rectangle = pygame.Rect(self.start_pointer, self.pointer - self.start_pointer)
                rectangle.normalize()
                for unit in self.units:
                    unit.selected = unit.owner == "blue" and unit.movable and rectangle.colliderect(selection_rectangle(unit, screen, camera))
                self.acknowledge(self.selected)
            else:
                hit = self.unit_at(position, screen, camera)
                if hit is not None:
                    hit.selected = not hit.selected
                    if hit.selected:
                        self.acknowledge(self.selected)
        elif moved:
            destination = camera.screen_to_world(position)
            if mode == "unit_route" or self.route_mode or len(self.selected) == 1:
                points = self.points + [destination]
                self.issue_route(points, tolerance=max(4, 2 / camera.zoom), skip_origin=mode == "unit_route")
            else:
                self.issue_formation(self.points[0], destination)
        elif mode == "ground_order":
            self.issue_move(camera.screen_to_world(position))
        self.cancel()
        return True

    def notify(self, message):
        self.message = message
        self.message_time = 2.5

    def assign_orders(self, orders):
        prepared = []
        destinations = {}
        for unit, points in orders:
            route = []
            for point in points:
                key = tuple(point)
                if key not in destinations:
                    destinations[key] = self.navigation.nearest_destination(point)
                destination = destinations[key]
                if destination is None:
                    self.notify("Немає прохідного шляху до вибраної точки")
                    return False
                route.append(tuple(destination))
            prepared.append((unit, route))
        self.path_planner.submit(prepared)
        self.path_planner.update(self.units)
        self.order_feedback = [route[-1] for _, route in prepared if route]
        self.feedback_time = .8
        self.message = ""
        self.message_time = 0
        self.acknowledge((unit for unit, route in prepared if route), "move")
        return True

    def issue_move(self, destination):
        selected = self.selected
        if not selected:
            return False
        return self.assign_orders([(unit, [pygame.Vector2(destination)]) for unit in selected])

    def issue_formation(self, start, end):
        selected = self.selected
        direction = pygame.Vector2(end) - start
        selected.sort(key=lambda unit: pygame.Vector2(unit.position).dot(direction))
        positions = [pygame.Vector2(start).lerp(end, index / max(1, len(selected) - 1)) for index in range(len(selected))]
        return self.assign_orders([(unit, [point]) for unit, point in zip(selected, positions)])

    def issue_route(self, points, tolerance=4, skip_origin=False):
        simplified = simplify_route(points, tolerance)
        if not simplified:
            return False
        first_waypoint = 1 if skip_origin and len(simplified) > 1 else 0
        selected = self.selected
        orders = []
        for unit in selected:
            route = []
            for step, point in enumerate(simplified):
                if step < first_waypoint:
                    continue
                route.append(point)
            orders.append((unit, route))
        return self.assign_orders(orders)

    def stop(self):
        selected = self.selected
        self.path_planner.cancel(selected)
        for unit in selected:
            unit.route.clear()
        self.cancel()
        self.acknowledge(selected, "stop")

    def update(self, elapsed_seconds, camera=None):
        self.path_planner.update(self.units)
        self.message_time = max(0, self.message_time - elapsed_seconds)
        target_opacity = min(1, self.message_time / .25)
        self.message_opacity += (target_opacity - self.message_opacity) * -math.expm1(-max(0, elapsed_seconds) / .08)
        self.feedback_time = max(0, self.feedback_time - elapsed_seconds)
        visible = camera.visible_area.inflate(300, 300) if camera is not None else None
        detailed = camera is None or detail_blend(camera.zoom) > 0
        for unit in self.units:
            interval = 1 / (20 if unit.route else 12) if detailed and (visible is None or visible.collidepoint(unit.position)) else 1 / 6
            previous_position = unit.position
            if unit.is_patriot:
                unit.update_deployment(elapsed_seconds)
            unit.animation_time = unit.animation_time + elapsed_seconds if unit.route else 0
            if not unit.movable or not unit.route:
                unit.update_environment(self.terrain.biome_at(unit.position), elapsed_seconds)
                if unit.is_tank:
                    update_tank(unit, elapsed_seconds, self.terrain, previous_position)
                else:
                    update_squad_timed(unit, elapsed_seconds, self.terrain, self.soldier_navigation, interval)
                continue
            biome = self.terrain.biome_at(unit.position)
            speed = UNIT_WATER_SPEED if biome == Biome.WATER else UNIT_SPEED * (UNIT_FOREST_SPEED_FACTOR if biome == Biome.FOREST else 1)
            speed *= unit.speed_factor
            if unit.is_tank:
                if unit.is_patriot and unit.deployment > .015:
                    movement_factor = 0
                else:
                    movement_factor = tank_drive_factor(unit, elapsed_seconds)
            else:
                movement_factor = cohesion_speed(unit)
            remaining = speed * movement_factor * elapsed_seconds
            while unit.route and remaining > 0:
                start = pygame.Vector2(unit.position)
                destination = pygame.Vector2(unit.route[0])
                distance = start.distance_to(destination)
                if distance > .001:
                    unit.facing = tuple((destination - start).normalize())
                movement = min(remaining, distance)
                position = destination if distance < .001 else start.lerp(destination, movement / distance)
                if not self.terrain.can_move(start, position, radius=4):
                    self.path_planner.submit(((unit, unit.route.copy()),))
                    break
                actual_movement = position - start
                if actual_movement.length_squared() > 1e-8:
                    unit.facing = tuple(actual_movement.normalize())
                unit.position = tuple(position)
                remaining -= movement
                if position.distance_squared_to(destination) < 1e-6:
                    unit.route.pop(0)
            unit.update_environment(self.terrain.biome_at(unit.position), elapsed_seconds)
            if unit.is_tank:
                update_tank(unit, elapsed_seconds, self.terrain, previous_position)
            else:
                update_squad_timed(unit, elapsed_seconds, self.terrain, self.soldier_navigation, interval)

        self.soldier_navigation.member_paths.update(self.units)

    def draw_orders(self, screen, camera):
        if self.feedback_time:
            for point in dict.fromkeys(tuple(point) for point in self.order_feedback):
                position = camera.world_to_screen(point)
                radius = round(5 + (1 - self.feedback_time / .8) * 12)
                pygame.draw.circle(screen, (157, 204, 177), (round(position.x), round(position.y)), radius, 1)
        projected = {}
        segments = set()
        endpoints = set()
        for unit in self.selected:
            if unit.planning_target is not None:
                target = tuple(camera.world_to_screen(unit.planning_target))
                if target not in endpoints:
                    pygame.draw.circle(screen, (158, 174, 182), (round(target[0]), round(target[1])), 6, 1)
                    endpoints.add(target)
            if unit.route:
                origin = pygame.Vector2(token_rectangle(unit, screen, camera).center) if detail_blend(camera.zoom) < 1 else camera.world_to_screen(unit.position)
                points = [tuple(origin)]
                route = unit.route if len(unit.route) <= 64 else [unit.route[index] for index in range(0, len(unit.route), max(1, len(unit.route) // 63))] + [unit.route[-1]]
                for point in route:
                    key = tuple(point)
                    if key not in projected:
                        projected[key] = tuple(camera.world_to_screen(point))
                    points.append(projected[key])
                for first, last in zip(points, points[1:]):
                    key = first, last
                    if key not in segments:
                        segments.add(key)
                        pygame.draw.line(screen, (137, 184, 215), first, last, 1)
                end = points[-1]
                if end not in endpoints:
                    pygame.draw.circle(screen, (179, 208, 217), (round(end[0]), round(end[1])), 4, 1)
                    endpoints.add(end)
        if self.mode in ("ground_order", "unit_route") and self.points:
            if self.mode == "ground_order" and not self.route_mode and len(self.selected) > 1:
                points = [camera.world_to_screen(self.points[0]), self.pointer]
            else:
                points = [camera.world_to_screen(point) for point in self.points] + [self.pointer]
            passable = self.terrain.can_place_unit(camera.screen_to_world(self.pointer), radius=4)
            color = (147, 204, 173) if passable else (208, 104, 92)
            if len(points) > 1:
                pygame.draw.lines(screen, color, False, points, 2)

    def draw_interface(self, screen, bottom=None, show_help=True):
        if self.mode == "selection":
            rectangle = pygame.Rect(self.start_pointer, self.pointer - self.start_pointer)
            rectangle.normalize()
            clipped = rectangle.clip(screen.get_rect())
            overlay = pygame.Surface(clipped.size, pygame.SRCALPHA)
            overlay.fill((76, 143, 210, 30))
            screen.blit(overlay, clipped)
            pygame.draw.rect(screen, (161, 201, 230), rectangle, 1)
        text = self.message if self.message_time else (f"Загонів: {len(self.selected)}   ·   ПКМ: рух   ·   Ctrl: вибір   ·   Shift: маршрут   ·   X: стоп   ·   Esc: зняти вибір" if self.selected and show_help else "")
        if text:
            label = self.font.render(text, True, (225, 229, 214))
            if bottom is not None and bottom < 120:
                area = label.get_rect(topright=(screen.get_width() - 24, 104))
            else:
                area = label.get_rect(bottomleft=(24, screen.get_height() - 24 if bottom is None else bottom))
            background = pygame.Surface((area.w + 18, area.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(background, (20, 31, 32), background.get_rect(), border_radius=3)
            background.blit(label, (9, 6))
            background.set_alpha(round(255 * self.message_opacity) if self.message_time else 255)
            screen.blit(background, (area.x - 9, area.y - 6))
