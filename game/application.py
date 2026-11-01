import argparse
from pathlib import Path
from dataclasses import replace

import pygame

from game.camera import Camera
from game.edge_scrolling import EdgeScrolling
from game.display import configure_display
from game.kingdom import Kingdom
from game.profile import PlayerProfile
from game.economy import Economy
from game.construction import Construction
from game.rendering import WorldRenderer
from game.settings import CAPITAL_VISION_RADIUS, CAMERA_SPEED, CITY_VISION_RADIUS, FRAME_RATE, WINDOW_SIZE
from game.ui.hud import KingdomHud
from game.ui.command_panel import CommandPanel
from game.ui.minimap import Minimap
from game.ui.map_hints import MapHints
from game.ui.unit_rename import UnitRename
from game.unit_control import UnitControl
from game.world.terrain import Terrain
from game.world.water_light import WaterLight
from game.world.cities import CityMap
from game.world.forest_rendering import ForestRendering
from game.world.visibility import Visibility, VisionSource
from game.world.intelligence import Intelligence
from game.world.building_manager import BuildingManager
from game.world.buildings import BUILDINGS_BY_KEY
from game.world.reconnaissance import Reconnaissance
from game.world.reveals import ObjectReveals
from game.ui.contact_markers import ContactMarkers
from game.aircraft.fleet import DroneFleet
from game.aircraft.control import DroneControl
from game.aircraft.reports import AerialReconnaissance
from game.aircraft.strikes import DroneStrikes
from game.aircraft.rendering import draw_aircraft, shadow_parts
from game.ui.gold_flow import GoldFlow
from game.audio.ambience import MineAmbience
from game.audio.drone_ambience import DroneAmbience
from game.audio.unit_radio import UnitRadio
from game.audio.radio_lines import radio_category
from game.audio.soundscape import Soundscape
from game.world.recruitment import Recruitment
from game.ui.building_interaction import BuildingInteraction
from game.ui.construction_status import ConstructionStatus
from game.world.country import Country
from game.world.deployment import starting_army
from game.ui.victory import Victory
from game.ui.game_menu import GameMenu
from game.ui.menu_view import loading_screen
from game.strategy.director import Strategy


class Application:
    def __init__(self, start_immediately=False, display_preferences=None):
        argument_parser = argparse.ArgumentParser()
        argument_parser.add_argument("--windowed", action="store_true")
        argument_parser.add_argument("--capture", type=Path)
        self.arguments = argument_parser.parse_args()

        configure_display()
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        self.fullscreen = not self.arguments.windowed
        self.window_size = WINDOW_SIZE
        if display_preferences is not None:
            self.fullscreen,self.window_size=display_preferences
        self.screen = self.create_display()
        pygame.display.set_caption("Ascent")
        self.screen.fill((19, 39, 47))
        pygame.display.flip()

        loading_screen(self.screen)
        self.terrain = Terrain()
        self.water_light = WaterLight(self.terrain)
        self.kingdom = Kingdom()
        self.city_map = CityMap(self.terrain)
        self.profile = PlayerProfile()
        self.country = Country(self.terrain, self.city_map)
        self.visibility = Visibility(self.terrain)
        initial_sources = [VisionSource(city.position, CAPITAL_VISION_RADIUS if city.capital else CITY_VISION_RADIUS, forest_blocked=True) for city in self.city_map.cities if city.owner == 'blue']
        self.visibility.set_sources(initial_sources, self.country)
        self.units = starting_army(self.terrain, self.country, self.city_map, self.profile, self.visibility.base_territory_field)
        self.buildings = BuildingManager(self.terrain, self.kingdom, self.city_map, self.units)
        self.economy = Economy(self.kingdom)
        self.intelligence = Intelligence()
        self.drone_fleet = DroneFleet(self.kingdom, self.buildings)
        self.drone_control = DroneControl(self.drone_fleet)
        self.refresh_visibility()
        self.unit_control = UnitControl(self.units, self.terrain, self.visibility, place_units=False)
        self.recruitment = Recruitment(self.kingdom, self.buildings, self.unit_control, self.unit_control.notify)
        self.building_interaction = BuildingInteraction(self.buildings)
        self.construction_status = ConstructionStatus(self.buildings)
        self.buildings.on_completed = lambda building: self.unit_control.notify(f"Збудовано: {building.definition.name}") if building.owner == "blue" else None
        self.refresh_visibility()
        self.reconnaissance = Reconnaissance(self.visibility, self.city_map, self.buildings, self.units)
        self.city_map.reconnaissance = self.reconnaissance
        self.buildings.reconnaissance = self.reconnaissance
        self.reconnaissance.update(0)
        self.reveals = ObjectReveals(self.reconnaissance)
        self.reveals.update(0)
        self.city_map.reveals = self.reveals
        self.reconnaissance.reveals = self.reveals
        self.contact_markers = ContactMarkers(self.reconnaissance)
        self.air_reconnaissance = AerialReconnaissance(self.drone_fleet, self.units, self.buildings, self.terrain, self.intelligence, self.unit_control.notify, self.city_map)
        self.reconnaissance.on_city_discovered = self.air_reconnaissance.city_discovered
        self.visibility_timer = 0
        self.city_map.visibility = self.visibility
        self.kingdom.army = len(self.unit_control.owned_units)
        self.camera = Camera(self.screen.get_size())
        self.edge_scrolling = EdgeScrolling()
        city_sources = list(self.visibility.sources[:4])
        city_sources.extend(VisionSource(unit.position, 110) for unit in self.units)
        left = min(source.position[0] - source.radius for source in city_sources)
        right = max(source.position[0] + source.radius for source in city_sources)
        top = min(source.position[1] - source.radius for source in city_sources)
        bottom = max(source.position[1] + source.radius for source in city_sources)
        self.camera.position.update((left + right) / 2, (top + bottom) / 2)
        available_height = max(200, self.screen.get_height() - 310)
        self.camera.zoom = self.camera.target_zoom = max(self.camera.minimum_zoom, min(self.screen.get_width() * .86 / (right - left), available_height / (bottom - top)))
        self.camera.position.y += 60 / self.camera.zoom
        self.camera.constrain()
        self.world_renderer = WorldRenderer(self.terrain.scenery)
        self.forest_rendering = ForestRendering(self.world_renderer)
        self.actors = []
        self.hud = KingdomHud()
        self.gold_flow = GoldFlow()
        self.mine_ambience = MineAmbience()
        self.unit_radio = UnitRadio()
        self.drone_ambience = DroneAmbience()
        self.soundscape = Soundscape()
        self.drone_fleet.production.on_ready = self.unit_control.notify
        self.drone_fleet.combat = DroneStrikes(self.drone_fleet, self.units, self.buildings, self.visibility, self.intelligence, self.unit_control.notify)
        self.drone_fleet.combat.on_explosion = lambda position: self.soundscape.explode(position, self.camera) if self.focused else None
        self.kingdom.on_purchase = self.soundscape.purchase
        self.unit_control.on_acknowledge = self.acknowledge_units
        self.economy.on_payout = self.gold_flow.paid
        self.minimap = Minimap(self.terrain)
        self.minimap.city_map = self.city_map
        self.minimap.visibility = self.visibility
        self.minimap.buildings = self.buildings
        self.minimap.contact_markers = self.contact_markers
        self.minimap.drone_fleet = self.drone_fleet
        self.minimap.layout(self.screen.get_size())
        self.construction = Construction(self.buildings, self.visibility)
        self.command_panel = CommandPanel(self.kingdom, self.city_map, self.unit_control, self.camera, self.visibility, self.intelligence)
        self.command_panel.rename_callback = self.open_unit_rename
        self.command_panel.build_callback = self.begin_building
        self.command_panel.fleet = self.drone_fleet
        self.command_panel.drone_control = self.drone_control
        self.command_panel.recruitment = self.recruitment
        self.command_panel.on_action = self.soundscape.click
        self.command_panel.cancel_construction = self.cancel_construction
        self.rename_dialog = UnitRename(self.save_unit_name)
        self.rename_dialog.layout(self.screen.get_size())
        self.map_hints = MapHints()
        self.pointer = pygame.Vector2(pygame.mouse.get_pos())
        self.clock = pygame.time.Clock()
        self.dragging = False
        self.drag_button = None
        self.running = True
        self.focused = True
        self.intelligence.on_report = lambda report: self.soundscape.information() if self.focused else False
        self.interface_seconds = 1 / 60
        self.strategy = Strategy(self)
        self.building_operations = self.strategy.operations
        self.victory = Victory()
        self.victory.on_continue = self.soundscape.click
        self.restart_requested=False
        self.menu=GameMenu(self)
        self.command_panel.on_pause=self.menu.pause
        if start_immediately:self.menu.begin()

    def refresh_visibility(self):
        self.country.update(self.city_map)
        sources = [VisionSource(city.position, CAPITAL_VISION_RADIUS if city.capital else CITY_VISION_RADIUS, forest_blocked=True) for city in self.city_map.cities if city.owner == "blue"]
        sources.extend(VisionSource(unit.position, unit.vision_radius, mobile=True) for unit in self.units if unit.owner == "blue")
        sources.extend(self.buildings.vision_sources())
        sources.extend(self.drone_fleet.vision_sources())
        self.visibility.set_sources(sources, self.country)
        self.country.update_control(self.visibility.territory_field, self.visibility.territory_revision)
        self.kingdom.area = self.country.area
        self.kingdom.land_fraction = self.country.fraction

    def acknowledge_units(self, units=None, action="select"):
        if self.focused and not self.command_panel.paused and not self.rename_dialog.active:
            responders = self.unit_control.selected if units is None else units
            if responders:
                self.soundscape.click("select" if action == "select" else "order")
                speaker = min(responders, key=lambda unit: pygame.Vector2(unit.position).distance_squared_to(self.camera.position))
                self.unit_radio.active = True
                self.unit_radio.play(speaker, self.camera, radio_category(responders), action)

    def begin_building(self, key):
        definition = BUILDINGS_BY_KEY[key]
        self.cancel_drag()
        if not self.construction.begin(definition):
            self.unit_control.notify("Недостатньо золота.")
            return False
        self.unit_control.cancel(deselect=True)
        self.drone_control.cancel(deselect=True)
        self.command_panel.active_section = None
        self.command_panel.render_surfaces()
        self.camera.zoom_anchor.update(pygame.Vector2(self.screen.get_size()) / 2)
        self.camera.target_zoom = max(self.camera.target_zoom, .9)
        return True

    def open_airport(self, airport):
        self.cancel_drag()
        self.unit_control.cancel(deselect=True)
        self.drone_control.cancel(deselect=True)
        self.command_panel.airport = airport
        self.command_panel.pages.airport.page = 0
        if self.command_panel.collapsed:
            self.command_panel.collapsed = False
            self.command_panel.layout(self.screen.get_size())
        self.command_panel.active_section = "airport"
        self.command_panel.surface_key = None
        self.command_panel.render_surfaces()

    def open_barracks(self, building):
        self.cancel_drag()
        self.unit_control.cancel(deselect=True)
        self.drone_control.cancel(deselect=True)
        self.command_panel.barracks = building
        self.command_panel.pages.barracks.page = 0
        self.command_panel.pages.barracks.roster = False
        if self.command_panel.collapsed:
            self.command_panel.collapsed = False
            self.command_panel.layout(self.screen.get_size())
        self.command_panel.active_section = "barracks"
        self.command_panel.surface_key = None
        self.command_panel.render_surfaces()

    def open_construction_site(self, building):
        self.cancel_drag()
        self.unit_control.cancel(deselect=True)
        self.drone_control.cancel(deselect=True)
        self.command_panel.construction_site = building
        if self.command_panel.collapsed:
            self.command_panel.collapsed = False
            self.command_panel.layout(self.screen.get_size())
        self.command_panel.active_section = "site"
        self.command_panel.surface_key = None
        self.command_panel.render_surfaces()

    def cancel_construction(self, building):
        if self.buildings.cancel_construction(building):
            self.command_panel.active_section = None
            self.command_panel.construction_site = None
            self.refresh_visibility()
            self.unit_control.notify("Будівництво скасовано. Золото повернуто.")

    def handle_aircraft_press(self, event):
        modifiers = pygame.key.get_mods()
        if event.button not in (1, 3) or modifiers & pygame.KMOD_CTRL:
            return False
        drone = self.drone_control.drone_at(event.pos, self.camera) if event.button == 1 else None
        if drone is not None:
            self.soundscape.click("select")
            self.unit_control.cancel(deselect=True)
            self.command_panel.active_section = None
            self.drone_control.begin(event.pos, self.camera, event.button, drone, modifiers)
            self.camera.stop_motion()
            return True
        unit = self.unit_control.unit_at(event.pos, self.screen, self.camera) if event.button == 1 else None
        building = self.buildings.interactive_at(event.pos, self.screen, self.camera) if event.button == 1 else None
        if building is not None and not building.completed:
            self.soundscape.click()
            self.open_construction_site(building)
            return True
        if unit is not None:
            self.drone_control.cancel(deselect=True)
            return False
        if building is not None:
            self.soundscape.click()
            if building.definition.key == "airport":
                self.open_airport(building)
            else:
                self.open_barracks(building)
            return True
        if self.drone_control.selected is not None:
            self.drone_control.begin(event.pos, self.camera, event.button, modifiers=modifiers)
            self.camera.stop_motion()
            return True
        return False

    def open_unit_rename(self, unit):
        self.cancel_drag()
        self.drone_control.cancel(deselect=True)
        for item in self.units:
            item.selected = item is unit
        self.rename_dialog.open(unit, self.screen.get_size())

    def save_unit_name(self, unit, name):
        if not self.profile.save_name(unit.profile_anchor or unit.home_city or unit.position, name):
            return False
        unit.name = name
        return True

    def create_display(self):
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode(self.window_size, pygame.RESIZABLE)

    def refresh_layout(self):
        self.cancel_drag()
        self.camera.viewport_size = self.screen.get_size()
        self.camera.zoom_anchor.update(pygame.Vector2(self.screen.get_size()) / 2)
        self.camera.constrain()
        self.minimap.layout(self.screen.get_size())
        self.command_panel.layout(self.screen.get_size())
        self.rename_dialog.layout(self.screen.get_size())

    def cancel_drag(self, cancel_placement=True):
        self.dragging = False
        self.drag_button = None
        self.minimap.end_drag()
        self.camera.stop_motion()
        self.unit_control.cancel()
        self.drone_control.cancel()
        self.command_panel.cancel_press()
        if cancel_placement:
            self.construction.cancel()

    def pointer_over_ui(self, position):
        return self.hud.panel_area.collidepoint(position) or self.command_panel.contains(position) or self.minimap.panel_area.collidepoint(position) or self.building_operations.contains(position)

    def handle_key(self, key):
        if key == pygame.K_ESCAPE:
            selected = bool(self.unit_control.selected or self.drone_control.selected is not None or self.map_hints.selected_city is not None or self.building_operations.selected is not None)
            placing = self.construction.active
            self.cancel_drag()
            self.unit_control.cancel(deselect=True)
            self.drone_control.cancel(deselect=True)
            self.map_hints.select_city(None)
            self.building_operations.selected = None
            if self.command_panel.active_section:
                self.command_panel.activate(("close",))
            if not selected and not placing:
                self.menu.pause()
        elif key == pygame.K_F2 and len(self.unit_control.selected) == 1:
            self.open_unit_rename(self.unit_control.selected[0])
        elif self.command_panel.handle_key(key):
            self.cancel_drag(cancel_placement=key != pygame.K_SPACE)
        elif key == pygame.K_x and self.drone_control.selected is not None:
            self.drone_fleet.hold(self.drone_control.selected)
        elif key == pygame.K_x and self.unit_control.selected:
            self.unit_control.stop()
        elif key == pygame.K_HOME:
            self.cancel_drag()
            self.camera.show_entire_map()
        elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.camera.change_zoom(pygame.Vector2(self.screen.get_size()) / 2, 1)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.camera.change_zoom(pygame.Vector2(self.screen.get_size()) / 2, -1)
        elif key == pygame.K_F11:
            if not self.fullscreen:
                self.window_size = self.screen.get_size()
            self.fullscreen = not self.fullscreen
            self.screen = self.create_display()
            self.dragging = False
            self.refresh_layout()

    def handle_events(self):
        for event in pygame.event.get():
            if hasattr(event, "pos"):
                self.pointer.update(event.pos)
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.focused = False
                self.cancel_drag()
                if not self.menu.active:self.menu.pause()
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.focused = True
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.window_size = (max(800, event.w), max(600, event.h))
                self.screen = self.create_display()
                self.refresh_layout()
            elif self.menu.active:
                self.menu.handle(event)
            elif self.victory.active:
                self.victory.handle_event(event)
            elif self.rename_dialog.active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.soundscape.click()
                self.rename_dialog.handle_event(event)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.handle_key(event.key)
            elif self.building_operations.handle(event):
                continue
            elif event.type == pygame.KEYDOWN:
                self.handle_key(event.key)
            elif event.type == pygame.MOUSEWHEEL:
                pointer = pygame.mouse.get_pos()
                if not self.command_panel.contains(pointer):
                    self.camera.change_zoom(pointer, event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2, 3):
                if self.building_operations.selected is not None and not self.building_operations.contains(event.pos):
                    self.building_operations.selected=None
                if self.building_operations.contains(event.pos):
                    continue
                if self.command_panel.contains(event.pos):
                    self.cancel_drag()
                    self.command_panel.begin_press(event.pos, event.button)
                    continue
                if self.hud.panel_area.collidepoint(event.pos):
                    continue
                if self.minimap.panel_area.collidepoint(event.pos):
                    if event.button == 1:
                        self.soundscape.click()
                    if event.button == 1 and not self.minimap.begin_drag(event.pos, self.camera):
                        self.minimap.handle_click(event.pos, self.camera)
                else:
                    if self.construction.active and event.button in (1, 3):
                        if event.button == 3:
                            self.construction.cancel()
                        else:
                            self.construction.update(event.pos, self.camera, False)
                            if self.construction.confirm():
                                self.soundscape.click()
                                self.refresh_visibility()
                        continue
                    if event.button == 1 and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.drone_control.cancel(deselect=True)
                    if event.button in (1,3) and self.unit_control.unit_at(event.pos,self.screen,self.camera) is None:
                        world = self.camera.screen_to_world(event.pos)
                        building = next((b for b in reversed(self.buildings.buildings) if b.area.inflate(30,45).collidepoint(world) and (b.owner=="blue" or self.visibility.is_visible(b.position))),None)
                        if building is not None and (building.owner!="blue" or event.button==3 or (building.completed and building.definition.key=="mine")):
                            self.building_operations.selected=building
                            continue
                    if self.handle_aircraft_press(event):
                        continue
                    if event.button == 3 and self.unit_control.selected:
                        self.unit_control.cancel()
                        self.unit_control.begin_order(event.pos, pygame.key.get_mods(), self.camera, button=3)
                        self.camera.stop_motion()
                        continue
                    city = None
                    if event.button == 1 and not pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT):
                        if self.unit_control.unit_at(event.pos, self.screen, self.camera) is None:
                            city = self.city_map.city_at(event.pos, self.screen, self.camera)
                        self.map_hints.select_city(city)
                        if city is not None:
                            self.soundscape.click()
                    if event.button == 1 and self.unit_control.begin(event.pos, pygame.key.get_mods(), self.screen, self.camera):
                        self.camera.stop_motion()
                        continue
                    if city is not None:
                        continue
                    self.dragging = True
                    self.drag_button = event.button
            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3):
                if self.command_panel.end_press(event.pos, event.button):
                    continue
                if event.button == self.drone_control.pointer_button:
                    self.drone_control.end(event.pos, self.camera, self.pointer_over_ui(event.pos))
                    continue
                if event.button == 1:
                    self.minimap.end_drag()
                if event.button == self.unit_control.pointer_button:
                    blocked = self.hud.panel_area.collidepoint(event.pos) or self.minimap.panel_area.collidepoint(event.pos) or self.command_panel.contains(event.pos)
                    self.unit_control.end(event.pos, self.screen, self.camera, blocked)
                if event.button == self.drag_button:
                    self.dragging = False
                    self.drag_button = None
            elif event.type == pygame.MOUSEMOTION:
                self.command_panel.pointer.update(event.pos)
                if self.drone_control.mode is not None:
                    self.drone_control.motion(event.pos, self.camera)
                elif self.unit_control.mode:
                    self.unit_control.motion(event.pos, self.camera)
                elif self.minimap.dragging:
                    self.minimap.drag(event.pos, self.camera)
                elif self.dragging:
                    self.camera.move(-pygame.Vector2(event.rel))

    def update(self, elapsed_seconds, wall_seconds=None):
        self.interface_seconds = min(.1, max(0, elapsed_seconds))
        self.menu.update(self.interface_seconds)
        if self.menu.active:
            self.unit_radio.update(False,self.camera,elapsed_seconds)
            self.mine_ambience.update(self.buildings.buildings,self.camera,elapsed_seconds,False)
            self.drone_ambience.update(self.drone_fleet.drones,self.camera,elapsed_seconds,False)
            self.soundscape.update(elapsed_seconds,self.focused,self.menu.state!='main')
            return
        if self.victory.active:
            self.victory.update(elapsed_seconds, self.screen.get_size())
            self.unit_radio.update(False, self.camera, elapsed_seconds)
            self.mine_ambience.update(self.buildings.buildings, self.camera, elapsed_seconds, False)
            self.drone_ambience.update(self.drone_fleet.drones, self.camera, elapsed_seconds, False)
            self.soundscape.update(elapsed_seconds, self.focused, True)
            return
        timer_seconds = elapsed_seconds if wall_seconds is None else wall_seconds
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if direction.length_squared() and self.focused and not self.rename_dialog.active:
            self.camera.move(direction.normalize() * CAMERA_SPEED * elapsed_seconds)
        edge_enabled = (self.focused and pygame.mouse.get_focused() and not self.rename_dialog.active
                        and not self.dragging and not self.minimap.dragging
                        and self.unit_control.mode is None and self.drone_control.mode is None
                        and not self.pointer_over_ui(self.pointer))
        edge_offset = self.edge_scrolling.update(self.pointer, self.screen.get_size(), elapsed_seconds, edge_enabled)
        if edge_offset.length_squared():
            self.camera.move(edge_offset)
        self.camera.update(elapsed_seconds)
        if not self.command_panel.paused and not self.rename_dialog.active:
            self.unit_control.update(elapsed_seconds, self.camera)
            captured = self.city_map.update(elapsed_seconds, self.units)
            if captured:
                self.refresh_visibility()
                for city, previous, owner in self.city_map.capture_events:
                    if previous == "blue":
                        self.intelligence.record(f"Втрачено місто: {city.name}", city.position, "Міське донесення")
                        self.reconnaissance.city_memory[city.position] = replace(city,capital=False,flag_color=None)
                own = [city.name for city in captured if city.owner == "blue"]
                if own:
                    self.unit_control.notify(f"Захоплено: {", ".join(own)}")
            self.forest_rendering.update(self.units, elapsed_seconds, self.camera)
            income_schedule = self.buildings.income_schedule(timer_seconds)
            self.buildings.update(elapsed_seconds, timer_seconds)
            self.recruitment.update(timer_seconds)
            self.kingdom.army = len(self.unit_control.owned_units)
            self.drone_fleet.update(timer_seconds)
            self.strategy.update(timer_seconds)
            self.air_reconnaissance.update(timer_seconds)
            self.gold_flow.update(timer_seconds)
            for duration, mines in income_schedule:
                self.economy.update(duration, sum(mine.definition.income_per_second for mine in mines), mines)
        self.drone_control.update()
        audible = self.focused and not self.command_panel.paused and not self.rename_dialog.active
        self.unit_radio.update(audible, self.camera, elapsed_seconds)
        ambient_volume = .5 if self.unit_radio.playing else 1.0
        self.mine_ambience.update([building for building in self.buildings.buildings if building.owner == "blue" or self.visibility.is_visible(building.position)], self.camera, elapsed_seconds, audible,
                                 volume_scale=ambient_volume)
        self.drone_ambience.update(self.strategy.audible_drones(), self.camera, elapsed_seconds, audible,
                                  volume_scale=ambient_volume)
        self.soundscape.update(elapsed_seconds, self.focused, self.command_panel.paused or self.rename_dialog.active, self.unit_radio.playing)
        self.construction_status.update(elapsed_seconds)
        self.building_interaction.update(self.pointer, self.screen, self.camera, elapsed_seconds,
                                         not self.focused or self.pointer_over_ui(self.pointer) or self.rename_dialog.active or self.construction.active or self.dragging or self.unit_control.mode is not None or self.drone_control.mode is not None)
        if self.command_panel.active_section == "information":
            self.intelligence.mark_read()
        if self.command_panel.active_section == "airport" and not self.drone_fleet.valid_airport(self.command_panel.airport):
            self.command_panel.active_section = None
        if self.command_panel.active_section == "barracks" and not self.recruitment.valid_barracks(self.command_panel.barracks):
            self.command_panel.active_section = None
        if self.command_panel.active_section == "site":
            site = self.command_panel.construction_site
            if site not in self.buildings.buildings:
                self.command_panel.active_section = None
                self.command_panel.construction_site = None
            elif site.completed:
                self.command_panel.construction_site = None
                if site.definition.key == "airport":
                    self.command_panel.airport = site
                    self.command_panel.pages.airport.page = 0
                    self.command_panel.active_section = "airport"
                elif site.definition.key == "barracks":
                    self.command_panel.barracks = site
                    self.command_panel.pages.barracks.page = 0
                    self.command_panel.pages.barracks.roster = False
                    self.command_panel.active_section = "barracks"
                else:
                    self.command_panel.active_section = None
        self.unit_control.separation.update(self.screen, self.camera, elapsed_seconds)
        self.visibility_timer += elapsed_seconds
        if self.visibility_timer >= .1 or (not any(unit.route for unit in self.units) and not self.drone_fleet.drones):
            self.refresh_visibility()
            self.visibility_timer = 0
        active_time = timer_seconds if not self.command_panel.paused and not self.rename_dialog.active else 0
        self.reconnaissance.update(active_time)
        self.reveals.update(active_time)
        self.rename_dialog.elapsed += timer_seconds
        self.construction.update(self.pointer, self.camera, self.pointer_over_ui(self.pointer), 0 if self.command_panel.paused else elapsed_seconds)
        blocked = self.rename_dialog.active or self.construction.active or self.dragging or self.minimap.dragging or self.unit_control.mode is not None or self.drone_control.mode is not None or self.drone_control.drone_at(self.pointer, self.camera) is not None or self.pointer_over_ui(self.pointer)
        self.map_hints.update(timer_seconds, self.pointer, self.screen, self.camera, self.city_map, self.unit_control, blocked)
        if self.victory.check(self.country.fraction):
            self.cancel_drag()
            self.soundscape.celebrate()

    def draw_frame(self):
        if self.menu.active:
            self.menu.draw(self.screen)
            pygame.display.flip()
            return
        if self.victory.active and self.victory.background is not None:
            self.victory.draw(self.screen)
            pygame.display.flip()
            return
        if self.actors:
            self.world_renderer.draw_scene(self.screen, self.camera, self.terrain, self.actors)
        self.forest_rendering.draw(self.screen, self.camera, self.terrain, self.units, self.buildings.displayed_buildings(), self.city_map, self.visibility, shadow_parts(self.drone_fleet, self.screen, self.camera), draw_background=not self.actors)
        self.water_light.draw(self.screen, self.camera, self.city_map.animation_time, self.visibility)
        draw_aircraft(self.screen, self.camera, self.drone_fleet, self.drone_control.selected)
        self.gold_flow.draw_labels(self.screen, self.camera)
        self.construction.draw_preview(self.screen, self.camera)
        self.visibility.draw(self.screen, self.camera)
        self.drone_fleet.combat.draw(self.screen, self.camera)
        self.strategy.draw(self.screen, self.camera)
        self.unit_control.draw_orders(self.screen, self.camera)
        self.building_interaction.draw(self.screen, self.camera)
        self.construction_status.draw(self.screen, self.camera)
        self.contact_markers.draw(self.screen, self.camera, self.pointer)
        self.drone_control.draw(self.screen, self.camera)
        self.construction.draw_range(self.screen, self.camera)
        self.map_hints.draw(self.screen, self.command_panel, self.minimap, self.camera)
        self.unit_control.draw_interface(self.screen, bottom=self.command_panel.top - 14, show_help=False)
        self.minimap.draw(self.screen, self.camera, self.interface_seconds)
        self.building_operations.draw(self.screen,self.camera)
        self.hud.draw(self.screen, self.kingdom, self.interface_seconds)
        self.command_panel.draw(self.screen, self.interface_seconds)
        self.construction.draw_interface(self.screen, self.interface_seconds)
        self.rename_dialog.draw(self.screen, self.interface_seconds)
        if self.victory.active:
            self.victory.draw(self.screen)
        self.menu.draw_exit(self.screen)
        pygame.display.flip()

    def run(self):
        rendered_frames = 0
        capture_frames=30 if self.menu.active else 2
        try:
            while self.running and not self.restart_requested:
                wall_seconds = self.clock.tick(FRAME_RATE) / 1000
                elapsed_seconds = min(wall_seconds, .05)
                self.handle_events()
                self.update(elapsed_seconds, wall_seconds)
                self.draw_frame()
                rendered_frames += 1

                if self.arguments.capture and rendered_frames == capture_frames:
                    self.arguments.capture.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(self.arguments.capture))
                    self.running = False
        finally:
            self.soundscape.close()
            self.drone_ambience.close()
            self.unit_radio.close()
            self.mine_ambience.close()
            for view in (self.command_panel,self.command_panel.pages.construction,self.command_panel.pages.airport,self.contact_markers):
                for method in vars(type(view)).values():
                    if hasattr(method,"cache_clear"):method.cache_clear()
            if not self.restart_requested:pygame.quit()
        return self.restart_requested
