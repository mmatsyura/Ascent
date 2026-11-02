from types import SimpleNamespace

from game.aircraft.explosions import draw_explosions
from game.aircraft.rendering import draw_aircraft
from game.strategy.air_defense import AirDefense
from game.strategy.building_operations import BuildingOperations
from game.strategy.commander import Commander
from game.strategy.deployment import deploy_opponents
from game.strategy.ground_combat import GroundCombat


class Strategy:
    def __init__(self, app):
        self.app = app
        deploy_opponents(app)
        self.commanders = [
            Commander(app, owner, index) for index, owner in enumerate(("red", "green", "purple"))
        ]
        self.operations = BuildingOperations(app)
        self.air_defense = AirDefense(app)
        self.ground_combat = GroundCombat(app)

    @property
    def fleets(self):
        return [self.app.drone_fleet, *(commander.fleet for commander in self.commanders)]

    def audible_drones(self):
        return [
            drone
            for fleet in self.fleets
            for drone in fleet.drones
            if drone.owner == "blue" or self.app.visibility.is_visible(drone.position)
        ]

    def update(self, duration):
        for commander in self.commanders:
            commander.update(duration)
        self.operations.update(duration)
        self.air_defense.update(duration, self.fleets)
        self.ground_combat.update(duration)

    def draw(self, screen, camera):
        for commander in self.commanders:
            visible = [
                drone
                for drone in commander.fleet.drones
                if self.app.visibility.is_visible(drone.position)
            ]
            draw_aircraft(screen, camera, SimpleNamespace(drones=visible))
            explosions = commander.fleet.combat.explosions
            draw_explosions(
                screen,
                camera,
                [
                    explosion
                    for explosion in explosions
                    if self.app.visibility.is_visible(explosion.position)
                ],
            )
        self.ground_combat.draw(screen, camera)
        self.air_defense.draw(screen, camera)
