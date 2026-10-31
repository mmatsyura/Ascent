import pygame


class AirMissions:
    def __init__(self,leader):
        self.leader=leader
        self.assigned={}
        self.wave=0
        self.wave_members=set()

    def command(self):
        leader=self.leader;app=leader.app
        drones=[drone for drone in leader.fleet.drones if drone.controllable]
        active=set(drones)
        self.assigned={drone:point for drone,point in self.assigned.items() if drone in active}
        strikes=[drone for drone in drones if drone.definition.strike and drone.attack_target is None]
        contacts=[*leader.knowledge.contacts.values(),*leader.knowledge.buildings.values()]
        contacts=[contact for contact in contacts if leader.knowledge.is_visible(contact.position) and leader.fleet.combat.valid(contact.target)]
        self.wave_members.intersection_update(active)
        if len(strikes)>=3:
            self.wave_members.update(strikes)
        attackers=[drone for drone in strikes if drone in self.wave_members]
        if attackers and contacts:
            self.wave+=1
            allocations={}
            for drone in attackers:
                def score(contact):
                    target=contact.target
                    value=9 if getattr(target,'is_patriot',False) else 6 if hasattr(target,'definition') and target.definition.key=='airport' else 4 if hasattr(target,'definition') else 3 if getattr(target,'is_tank',False) else 2
                    p=leader.fleet.combat.chance(target)
                    shots=allocations.get(target,0)
                    return pygame.Vector2(drone.position).distance_to(contact.position)/(value*p)+shots*1400
                for contact in sorted(contacts,key=score):
                    route=leader.air_routes.route(drone.position,contact.position)
                    if not route:continue
                    if leader.fleet.combat.assign(drone,contact.target):
                        drone.route=route
                        allocations[contact.target]=allocations.get(contact.target,0)+1
                        leader.statistics['air_strike']+=1
                        leader.statistics['salvo']+=int(len(allocations)==1 and sum(allocations.values())==1)
                        break
        objectives=[memory.position for memory in leader.knowledge.cities.values() if memory.owner!=leader.owner]
        objectives.extend(memory.position for memory in leader.knowledge.buildings.values())
        objectives.extend(contact.position for contact in leader.knowledge.contacts.values())
        center=sum((pygame.Vector2(city.position) for city in app.city_map.cities if city.owner==leader.owner),pygame.Vector2())
        count=sum(city.owner==leader.owner for city in app.city_map.cities)
        center/=max(1,count)
        used=[]
        for drone in drones:
            if drone.attack_target is not None or drone.route:continue
            if drone.definition.strike:
                if drone not in self.wave_members:continue
                memories=[*leader.knowledge.buildings.values(),*leader.knowledge.contacts.values()]
                targets=[memory.position for memory in memories]
                targets.extend(memory.position for memory in leader.knowledge.cities.values() if memory.owner!=leader.owner)
                for point in sorted(targets,key=lambda point:pygame.Vector2(drone.position).distance_squared_to(point)):
                    if pygame.Vector2(drone.position).distance_squared_to(point)<100**2:continue
                    route=leader.air_routes.route(drone.position,point)
                    if route:
                        leader.fleet.assign_route(drone,route)
                        break
                continue
            candidates=sorted(objectives,key=lambda point:pygame.Vector2(drone.position).distance_to(point)+sum(pygame.Vector2(point).distance_squared_to(other)<500**2 for other in used)*2000)
            unknown=[]
            for _ in range(12):
                point=leader.explore(drone.position,set())
                if point:
                    enemy_direction=(pygame.Vector2(point)-center).length()
                    unknown.append((enemy_direction,point))
            candidates.extend(point for _,point in sorted(unknown,reverse=True))
            for point in candidates:
                route=leader.air_routes.route(drone.position,point)
                if not route:continue
                if pygame.Vector2(drone.position).distance_squared_to(point)<120**2:continue
                leader.fleet.assign_route(drone,route)
                self.assigned[drone]=tuple(point)
                used.append(point)
                leader.statistics['recon_mission']+=1
                return
