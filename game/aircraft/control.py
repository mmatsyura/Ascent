import math

import pygame

from game.aircraft.rendering import aircraft_rectangle
from game.ui.fonts import ui_font
from game.world.routes import simplify_route


class DroneControl:
    def __init__(self, fleet):
        self.fleet = fleet
        self.selected = None
        self.mode = None
        self.pointer_button = None
        self.start_pointer = pygame.Vector2()
        self.pointer = pygame.Vector2()
        self.points = []
        self.append = False
        self.font = ui_font(15, True)

    def drone_at(self, pointer, camera):
        matches = [drone for drone in self.fleet.drones if drone.controllable and aircraft_rectangle(drone, camera).inflate(6, 6).collidepoint(pointer)]
        return min(matches, key=lambda drone: pygame.Vector2(aircraft_rectangle(drone, camera).center).distance_squared_to(pointer), default=None)

    def cancel(self, deselect=False):
        self.mode = None
        self.pointer_button = None
        self.points = []
        if deselect:
            self.selected = None

    def begin(self, pointer, camera, button=1, drone=None, modifiers=0):
        if drone is not None:
            self.selected = drone
        if self.selected is None or not self.selected.controllable:
            return False
        self.mode = "pick" if drone is not None else "order"
        self.pointer_button = button
        self.start_pointer.update(pointer)
        self.pointer.update(pointer)
        self.append = bool(modifiers & pygame.KMOD_SHIFT)
        self.points = [] if drone is not None else [camera.screen_to_world(pointer)]
        return True

    def motion(self, pointer, camera):
        self.pointer.update(pointer)
        if self.mode is None:
            return
        if self.start_pointer.distance_to(pointer) < 6:
            return
        world = camera.screen_to_world(pointer)
        if not self.points or self.points[-1].distance_to(world) >= max(8, 5 / camera.zoom):
            if len(self.points) < 64:
                self.points.append(world)

    def end(self, pointer, camera, blocked=False):
        if self.mode is None:
            return False
        moved = self.start_pointer.distance_to(pointer) > 6
        if not blocked and self.selected is not None and (moved or self.mode == "order"):
            combat = self.fleet.combat
            if not moved and self.selected.definition.strike and combat is not None:
                target = combat.target_at(pointer, camera)
                if target is not None and combat.assign(self.selected, target):
                    self.cancel()
                    return True
            points = self.points + [camera.screen_to_world(pointer)]
            self.fleet.assign_route(self.selected, simplify_route(points, max(3, 2 / camera.zoom)), self.append)
        self.cancel()
        return True

    def update(self):
        if self.selected not in self.fleet.drones or not self.selected.controllable:
            self.cancel(deselect=True)

    def draw(self, screen, camera):
        drone = self.selected
        if drone is None:
            return
        center = camera.world_to_screen(drone.position)
        rectangle = aircraft_rectangle(drone, camera)
        pygame.draw.line(screen, (82, 126, 130), rectangle.center, (round(center.x), round(center.y)), 1)
        pygame.draw.circle(screen, (105, 157, 159), (round(center.x), round(center.y)), 2, 1)
        pygame.draw.ellipse(screen, (133, 202, 196), rectangle.inflate(3, 3), 1)
        if drone.route:
            points = [center] + [camera.world_to_screen(point) for point in drone.route]
            pygame.draw.lines(screen, (104, 174, 185), False, points, 1)
            end = points[-1]
            pygame.draw.circle(screen, (187, 218, 191), (round(end.x), round(end.y)), 4, 1)
        if drone.attack_position is not None:
            target = camera.world_to_screen(drone.attack_position)
            center = (round(target.x), round(target.y))
            radius = round(11 + 2 * math.sin(drone.animation_time * 3))
            pygame.draw.circle(screen, (223, 135, 101), center, radius, 2)
            for offset in (-1, 1):
                pygame.draw.line(screen, (241, 189, 131), (center[0] + offset * (radius - 3), center[1]), (center[0] + offset * (radius + 5), center[1]), 1)
                pygame.draw.line(screen, (241, 189, 131), (center[0], center[1] + offset * (radius - 3)), (center[0], center[1] + offset * (radius + 5)), 1)
        if self.mode and self.points:
            points = [camera.world_to_screen(point) for point in self.points] + [self.pointer]
            if len(points) > 1:
                pygame.draw.lines(screen, (164, 214, 193), False, points, 2)
        label = self.font.render(f"{drone.definition.name} · {drone.timer_label}", True, (225, 229, 197))
        area = label.get_rect(midbottom=(rectangle.centerx, rectangle.top - 7))
        area.clamp_ip(screen.get_rect().inflate(-12, -12))
        pygame.draw.rect(screen, (16, 31, 34), area.inflate(14, 8), border_radius=3)
        screen.blit(label, area)
