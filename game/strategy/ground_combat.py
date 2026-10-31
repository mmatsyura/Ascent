from collections import defaultdict

import pygame


class GroundCombat:
    def __init__(self, app):
        self.app = app
        self.accumulator = 0
        self.tracers = []
        self.elapsed = 0
        self.losses = defaultdict(int)

    def update(self, duration):
        self.elapsed += duration
        self.accumulator += duration
        self.tracers[:] = [trace for trace in self.tracers if self.elapsed-trace[2] < .18]
        if self.accumulator < .25:
            return
        step = min(.5, self.accumulator)
        self.accumulator = 0
        buckets = defaultdict(list)
        for unit in self.app.units:
            buckets[(int(unit.position[0]//200),int(unit.position[1]//200))].append(unit)
        damage = defaultdict(float)
        for unit in self.app.units:
            if unit.is_patriot:
                continue
            reach = min(unit.vision_radius, 180 if unit.is_tank else 105)
            x,y = int(unit.position[0]//200),int(unit.position[1]//200)
            nearby = [other for row in range(y-1,y+2) for col in range(x-1,x+2) for other in buckets.get((col,row),())
                      if other.owner != unit.owner and pygame.Vector2(unit.position).distance_squared_to(other.position) <= reach**2]
            if not nearby:
                continue
            target = min(nearby,key=lambda other: other.health + pygame.Vector2(unit.position).distance_to(other.position)*.4)
            if not self.app.terrain.can_move(unit.position,target.position,radius=1):
                continue
            power = 11 if unit.is_tank else 6
            if target.is_tank and not unit.is_tank:
                power *= .45
            if target.in_forest:
                power *= .65
            damage[target] += power*step
            self.tracers.append((tuple(unit.position),tuple(target.position),self.elapsed,unit.owner))
        for unit, amount in damage.items():
            unit.health = max(0,unit.health-amount)
        destroyed = [unit for unit in self.app.units if unit.health <= 0]
        for unit in destroyed:
            self.app.units.remove(unit)
            self.losses[unit.owner] += 1
            if unit.owner == 'blue':
                self.app.intelligence.record(f'Втрачено підрозділ: {unit.name}',unit.position,'Бойове донесення')
        cities = [city for city in self.app.city_map.cities if city.owner]
        for unit in self.app.units:
            if unit not in damage and unit.health < 100 and not unit.route:
                if any(city.owner == unit.owner and pygame.Vector2(unit.position).distance_squared_to(city.position)<210**2 for city in cities):
                    unit.health = min(100,unit.health+step*1.2)

    def draw(self, screen, camera):
        for start,end,born,owner in self.tracers:
            if owner != 'blue' and not self.app.visibility.is_visible(start):
                continue
            origin,destination = camera.world_to_screen(start),camera.world_to_screen(end)
            progress = min(1,(self.elapsed-born)/.18)
            tip = origin.lerp(destination,progress)
            tail = origin.lerp(destination,max(0,progress-.18))
            pygame.draw.line(screen,(236,200,111),tail,tip,max(1,round(camera.zoom)))
        for unit in self.app.units:
            if unit.health >= 99.9 or (unit.owner != 'blue' and not self.app.visibility.is_visible(unit.position)):
                continue
            point = camera.world_to_screen(unit.position)
            rectangle = pygame.Rect(round(point.x-14),round(point.y-22),28,4)
            if not screen.get_rect().colliderect(rectangle):
                continue
            pygame.draw.rect(screen,(29,34,31),rectangle)
            pygame.draw.rect(screen,(113,169,112) if unit.health>35 else (195,104,75),(rectangle.x+1,rectangle.y+1,round(26*unit.health/100),2))
