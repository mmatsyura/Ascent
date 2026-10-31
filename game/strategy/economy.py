from collections import Counter

import pygame

from game.world.building_manager import BuildingManager
from game.world.buildings import BUILDINGS_BY_KEY


class Development:
    def __init__(self, commander):
        self.commander = commander
        self.site_index = 0
        self.failed_until = 0

    def construct(self, key):
        leader = self.commander
        app = leader.app
        definition = BUILDINGS_BY_KEY[key]
        if not leader.kingdom.can_afford(definition.cost) or leader.elapsed < self.failed_until:
            return False
        cities = [city for city in app.city_map.cities if city.owner == leader.owner]
        cities.sort(key=lambda city: (leader.knowledge.threat(city.position), not city.capital))
        if not cities:
            return False
        manager = BuildingManager(app.terrain, leader.kingdom, app.city_map, app.units)
        manager.buildings = app.buildings.buildings
        manager.reservations = app.buildings.reservations
        for attempt in range(48):
            index = self.site_index + attempt
            city = cities[(index//12) % len(cities)]
            radius = 120 + ((index//len(cities)) % 9) * 58
            angle = index * 137.508
            position = pygame.Vector2(city.position) + pygame.Vector2(radius, 0).rotate(angle)
            building, _ = manager.place(definition, position, leader.knowledge)
            if building is None:
                continue
            building.owner = leader.owner
            app.buildings.revision += 1
            self.site_index = index + 1
            leader.statistics['constructed'] += 1
            return True
        self.site_index += 48
        self.failed_until = leader.elapsed + 8
        return False

    def think(self):
        leader=self.commander;app=leader.app
        own=[building for building in app.buildings.buildings if building.owner==leader.owner]
        counts=Counter(building.definition.key for building in own)
        troops=[unit for unit in app.units if unit.owner==leader.owner]
        cities=sum(city.owner==leader.owner for city in app.city_map.cities)
        danger=max((leader.knowledge.threat(city.position) for city in app.city_map.cities if city.owner==leader.owner),default=0)
        mines=counts['mine']
        need_army=len(troops)<max(16,min(64,cities*3+8))
        if mines==0:
            self.construct('mine');return
        if counts['barracks']==0:
            self.construct('barracks');return
        emergency=len(troops)<6 or danger>10
        if len(troops)<6 or (mines>=4 and len(troops)<16):
            for building in own:
                if leader.recruitment.valid_barracks(building) and not leader.recruitment.garrison(building).queue:
                    leader.recruitment.recruit(building,'anti_tank' if sum(unit.is_anti_tank for unit in troops)<3 else 'tank' if sum(unit.is_tank for unit in troops)<5 else 'infantry')
        if not emergency:
            if mines<4 and self.construct('mine'):return
            if counts['barracks']<min(5,1+mines//3) and self.construct('barracks'):return
            if counts['airport']<min(3,max(1,mines//4)) and mines>=3 and self.construct('airport'):return
            if mines<min(16,5+cities) and leader.kingdom.gold>850 and self.construct('mine'):return
        reserve=500 if mines<4 and not emergency else 0
        if mines>=5 and not emergency and len(troops)>=18:
            reserve=3000
        air_pressure=len(leader.doctrine.air_hotspots)
        enemy_tanks=sum(contact.target.is_tank and not contact.target.is_patriot for contact in leader.knowledge.contacts.values())
        required_ppo=min(8,max(2,counts['airport']+air_pressure+mines//5))
        for building in own:
            if not leader.recruitment.valid_barracks(building):continue
            state=leader.recruitment.garrison(building)
            if len(state.queue)>=2 or len(troops)+sum(len(g.queue) for g in leader.recruitment.garrisons.values())>=72:continue
            if not need_army and sum(unit.is_patriot for unit in troops)>=required_ppo:continue
            if leader.kingdom.gold<reserve+90:continue
            ppo=sum(unit.is_patriot for unit in troops)+sum(job.key=='patriot' for g in leader.recruitment.garrisons.values() for job in g.queue)
            if ppo<required_ppo and len(troops)>=10:
                key='patriot'
            elif sum(unit.is_anti_tank for unit in troops)<max(3,enemy_tanks*2,len(troops)//5):
                key='anti_tank'
            elif sum(unit.is_tank and not unit.is_patriot for unit in troops)<len(troops)*.32:
                key='tank'
            else:key='infantry'
            leader.recruitment.recruit(building,key)
        airports=[building for building in own if leader.fleet.valid_airport(building)]
        scouts=sum(not drone.definition.strike and drone.controllable for drone in leader.fleet.drones)
        for airport in airports:
            for key,count in tuple(leader.fleet.stock[airport].items()):
                if key!='flamingo' and count:
                    leader.fleet.launch(airport,key)
            queued=leader.fleet.production.queues.get(airport)
            if queued and len(queued.jobs)>=3:continue
            if len(leader.fleet.drones)>24:continue
            if scouts<2:
                key='kamikaze' if leader.kingdom.gold<2500 else 'aviamen'
            else:key='flamingo'
            leader.fleet.purchase(airport,key)
        ready=sum(leader.fleet.stock[airport]['flamingo'] for airport in airports)
        if ready>=3:
            for airport in airports:
                while leader.fleet.stock[airport]['flamingo']:
                    drone,_=leader.fleet.launch(airport,'flamingo')
                    if drone is not None:
                        drone.orbit_radius=40
                        drone.orbit_center=airport.position
                    leader.statistics['wave_launch']+=1
