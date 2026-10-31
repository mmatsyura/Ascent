from dataclasses import dataclass
import math

import pygame

from game.ui.fonts import ui_font
from game.ui.demolition_view import DemolitionView
from game.ui.theme import panel_surface, TEXT, MUTED, ACCENT


DESTROY_SECONDS = {'mine':20,'barracks':30,'airport':40}


@dataclass
class BuildingOrder:
    building: object
    owner: str
    mode: str
    participants: tuple
    progress: float = 0

    @property
    def duration(self):
        return 180 if self.mode=='capture' else DESTROY_SECONDS[self.building.definition.key]


class BuildingOperations:
    def __init__(self, app):
        self.app = app
        self.orders = {}
        self.selected = None
        self.buttons = {}
        self.panel = pygame.Rect(0,0,390,180)
        self.offered = set()
        self.prompt_timer = 0
        self.refund_view = DemolitionView()

    def nearby(self, building, owner):
        return [unit for unit in self.app.units if unit.owner==owner and not unit.is_patriot and pygame.Vector2(unit.position).distance_squared_to(building.position)<165**2]

    def entitled(self, building, owner):
        city = min(self.app.city_map.cities,key=lambda city: pygame.Vector2(city.position).distance_squared_to(building.position))
        return city.owner==owner and pygame.Vector2(city.position).distance_squared_to(building.position)<460**2

    def demolish(self, building, owner):
        if building not in self.app.buildings.buildings:
            return False
        if building.owner!=owner and not self.entitled(building,owner):
            return False
        if building.owner==owner:
            kingdom=self.app.kingdom if owner=='blue' else next(c.kingdom for c in self.app.strategy.commanders if c.owner==owner)
            kingdom.gold += building.definition.gold_cost//3
        self.app.buildings.destroy(building)
        self.orders.pop(building,None)
        return True

    def start(self, building, owner, mode, participants=None):
        if building not in self.app.buildings.buildings or building.owner==owner or mode not in ('destroy','capture'):
            return False
        if mode=='capture' and building.definition.key=='barracks':
            return False
        units = self.nearby(building,owner) if participants is None else [unit for unit in participants if unit in self.nearby(building,owner)]
        if not units:
            return False
        for unit in units:
            self.app.unit_control.path_planner.cancel((unit,))
            unit.route.clear()
        self.orders[building]=BuildingOrder(building,owner,mode,tuple(units))
        return True

    def open_at(self, pointer):
        world=self.app.camera.screen_to_world(pointer)
        for building in reversed(self.app.buildings.buildings):
            if (building.owner=='blue' or self.app.visibility.is_visible(building.position)) and building.area.inflate(30,45).collidepoint(world):
                self.selected=building
                return True
        return False

    def contains(self, pointer):
        return self.selected is not None and self.panel.collidepoint(pointer)

    def handle(self,event):
        if self.selected is None:
            return False
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            self.selected=None
            return True
        if event.type!=pygame.MOUSEBUTTONDOWN or event.button!=1 or not self.panel.collidepoint(event.pos):
            return False
        building=self.selected
        for action,rectangle in self.buttons.items():
            if not rectangle.collidepoint(event.pos):
                continue
            if action in ('close','dismiss'):
                self.selected=None
            elif action=='cancel':
                if building in self.orders and self.orders[building].owner=='blue':
                    self.orders.pop(building,None)
            elif action=='demolish':
                if self.demolish(building,'blue'):
                    self.selected=None
            elif self.start(building,'blue',action,tuple(unit for unit in self.app.unit_control.selected if unit in self.nearby(building,'blue')) or None):
                self.selected=None
            self.app.soundscape.click()
            return True
        return True

    def update(self,duration):
        present=set(self.app.units)
        for building,order in tuple(self.orders.items()):
            if building not in self.app.buildings.buildings or building.owner==order.owner:
                self.orders.pop(building,None)
                continue
            if not any(unit in present for unit in order.participants):
                self.orders.pop(building,None)
                continue
            active=[unit for unit in order.participants if unit in present and pygame.Vector2(unit.position).distance_squared_to(building.position)<165**2 and not unit.route]
            contested=any(unit.owner!=order.owner and pygame.Vector2(unit.position).distance_squared_to(building.position)<165**2 for unit in self.app.units)
            if not active or contested:
                continue
            order.progress += duration
            if order.progress < order.duration:
                continue
            previous_owner=building.owner
            if order.mode=='destroy':
                self.app.buildings.destroy(building)
            else:
                building.owner=order.owner
                building.training_active=False
                self.app.buildings.revision+=1
            self.orders.pop(building,None)
            if previous_owner=='blue' and order.owner!='blue':
                self.app.intelligence.record(f'Втрачено споруду: {building.definition.name}',building.position,'Бойове донесення')
            if order.owner=='blue':
                self.app.unit_control.notify('Споруду захоплено.' if order.mode=='capture' else 'Споруду знищено.')
        if self.selected is not None and self.selected not in self.app.buildings.buildings:
            self.selected=None
        self.prompt_timer+=duration
        if self.prompt_timer>.5 and self.selected is None:
            self.prompt_timer=0
            for building in self.app.buildings.buildings:
                if building.owner=='blue' or building in self.offered or not self.app.visibility.is_visible(building.position):
                    continue
                if any(unit in self.app.unit_control.selected for unit in self.nearby(building,'blue')):
                    self.offered.add(building)
                    self.selected=building
                    break

    def draw(self,screen,camera):
        font=ui_font(14,True)
        for building,order in self.orders.items():
            if order.owner!='blue' and not self.app.visibility.is_visible(building.position):
                continue
            point=camera.world_to_screen(building.position)
            label=font.render(f'{"Захоплення" if order.mode=="capture" else "Знищення"} · {math.ceil(order.duration-order.progress)} с',True,ACCENT)
            area=label.get_rect(midbottom=(round(point.x),round(point.y-45*camera.zoom)))
            pygame.draw.rect(screen,(15,25,27),area.inflate(16,12),border_radius=4)
            screen.blit(label,area)
            pygame.draw.rect(screen,(169,119,69),(area.x,area.bottom+3,round(area.w*order.progress/order.duration),3))
        building=self.selected
        if building is None:
            return
        if building.owner=="blue":
            self.refund_view.draw(screen,self,building)
            return
        self.panel.size=(390,180)
        self.panel.midtop=(screen.get_width()//2,95)
        image=panel_surface(self.panel.size).copy()
        self.buttons={}
        image.blit(ui_font(19,True).render(building.definition.name,True,TEXT),(18,15))
        def button(action,text,y,enabled=True):
            rectangle=pygame.Rect(self.panel.x+16,self.panel.y+y,self.panel.w-32,30)
            pygame.draw.rect(image,(37,55,54) if enabled else (29,35,34),rectangle.move(-self.panel.x,-self.panel.y),border_radius=3)
            label=font.render(text,True,TEXT if enabled else MUTED)
            image.blit(label,(22,y+6))
            if enabled:self.buttons[action]=rectangle
        self.buttons['close']=pygame.Rect(self.panel.right-36,self.panel.y+9,28,26)
        image.blit(font.render('×',True,TEXT),(self.panel.w-29,13))
        if self.entitled(building,'blue'):
            button('demolish','Знести споруду біля захопленого міста',64)
            button('capture','Захопити · 180 с',103,building.definition.key!='barracks' and bool(self.nearby(building,'blue')))
        else:
            ready=bool(self.nearby(building,'blue'))
            button('destroy',f'Знищити · {DESTROY_SECONDS[building.definition.key]} с',59,ready)
            button('capture','Захопити · 180 с',96,ready and building.definition.key!='barracks')
        if building in self.orders and self.orders[building].owner=='blue':
            button('cancel','Скасувати операцію',137)
        elif building.owner!='blue' and not self.nearby(building,'blue'):
            image.blit(font.render('Підведіть піхоту або танк до споруди.',True,MUTED),(19,142))
        screen.blit(image,self.panel)
