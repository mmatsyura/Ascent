from collections import deque
from dataclasses import dataclass
from time import perf_counter

import pygame


@dataclass
class MemberRequest:
    member: object
    target: pygame.Vector2
    center: pygame.Vector2
    iterator: object = None


class MemberPaths:
    def __init__(self, navigation):
        self.navigation = navigation
        self.pending = deque()
        self.requests = {}
        self.revision = navigation.terrain.revision

    def submit(self, member, target, center):
        if id(member) in self.requests:
            return
        request = MemberRequest(member, pygame.Vector2(target), pygame.Vector2(center))
        self.requests[id(member)] = request
        self.pending.append(request)
        member.retry_time = 0.55

    def cancel(self, member):
        self.requests.pop(id(member), None)

    def route(self, request, cells):
        navigation = self.navigation
        member, target, center = request.member, request.target, request.center
        result = yield from navigation.iter_path(member.position, target, cells)
        if result is not None:
            return result
        yield None
        regroup = navigation.nearest_destination(center, radius=48)
        if regroup is not None:
            result = yield from navigation.iter_path(member.position, regroup, cells)
            if result is not None:
                return result
        for distance in (12, 24, 36):
            for angle in range(0, 360, 45):
                yield None
                candidate = center + pygame.Vector2(distance, 0).rotate(angle)
                if navigation.can_place(candidate, radius=4):
                    result = yield from navigation.iter_path(member.position, candidate, cells)
                    if result is not None:
                        return result
        return []

    def update(self, units, budget=0.0015):
        if not self.pending:
            return
        present = {id(member) for unit in units for member in unit.members}
        revision = self.navigation.terrain.revision
        if revision != self.revision:
            self.revision = revision
            for request in self.requests.values():
                request.iterator = None
        deadline = perf_counter() + budget
        cells = self.navigation.allowed_cells()
        while self.pending and perf_counter() < deadline:
            request = self.pending.popleft()
            identity = id(request.member)
            if identity not in present or self.requests.get(identity) is not request:
                if identity not in present:
                    self.requests.pop(identity, None)
                continue
            if request.iterator is None:
                request.iterator = self.route(request, cells)
            try:
                next(request.iterator)
                self.pending.append(request)
            except StopIteration as result:
                member = request.member
                member.detour = result.value or []
                member.detour_goal = request.target
                member.retry_time = 0.3 if member.detour else 0.75
                self.requests.pop(identity, None)
