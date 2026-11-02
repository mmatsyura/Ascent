from collections import deque
from dataclasses import dataclass
from time import perf_counter


@dataclass
class PathRequest:
    unit: object
    destinations: tuple
    iterator: object = None
    route: list = None
    waypoint: int = 0
    start: tuple = None


class PathPlanner:
    def __init__(self, navigation, notify):
        self.navigation = navigation
        self.notify = notify
        self.pending = deque()
        self.requests = {}
        self.corridors = {}
        self.terrain_revision = -1

    def cancel(self, units):
        for unit in units:
            self.requests.pop(unit, None)
            unit.planning_target = None

    def submit(self, orders):
        for unit, destinations in orders:
            self.cancel((unit,))
            if not destinations:
                unit.route.clear()
                continue
            request = PathRequest(
                unit,
                tuple(tuple(point) for point in destinations),
                route=[],
                start=tuple(unit.position),
            )
            unit.route.clear()
            unit.planning_target = request.destinations[-1]
            self.requests[unit] = request
            if unit.owner == "blue":
                self.pending.appendleft(request)
            else:
                self.pending.append(request)

    def shared_route(self, request, cells):
        route = self.corridors.get(request.destinations)
        if not route:
            return None
        try:
            first_end = route.index(request.destinations[0]) + 1
        except ValueError:
            return None
        for index in range(min(4, first_end)):
            if self.navigation.clear_line(request.start, route[index], cells, check_cells=False):
                return route[index:].copy()
        return None

    def update(self, units, budget=0.002):
        deadline = perf_counter() + budget
        present = set(units)
        revision = self.navigation.terrain.revision
        if self.terrain_revision != revision:
            self.corridors.clear()
            self.terrain_revision = revision
            for request in self.requests.values():
                request.iterator = None
                request.route.clear()
                request.waypoint = 0
                request.start = tuple(request.unit.position)
        cells = None
        while self.pending and perf_counter() < deadline:
            request = self.pending[0]
            unit = request.unit
            if unit not in present or self.requests.get(unit) is not request:
                self.pending.popleft()
                if unit not in present:
                    self.cancel((unit,))
                continue
            if cells is None:
                cells = self.navigation.allowed_cells()
            if request.iterator is None and request.waypoint == 0:
                shared = self.shared_route(request, cells)
                if shared is not None:
                    self.finish(request, shared)
                    continue
            if request.iterator is None:
                request.iterator = self.navigation.iter_path(
                    request.start, request.destinations[request.waypoint], cells
                )
            try:
                next(request.iterator)
            except StopIteration as result:
                if result.value is None:
                    self.finish(request, None)
                    if unit.owner == "blue":
                        self.notify("Немає прохідного шляху до вибраної точки")
                    continue
                request.route.extend(result.value)
                request.start = request.route[-1] if request.route else request.start
                request.waypoint += 1
                request.iterator = None
                if request.waypoint == len(request.destinations):
                    self.finish(request, request.route)

    def finish(self, request, route):
        self.pending.popleft()
        self.requests.pop(request.unit, None)
        request.unit.planning_target = None
        if route is not None:
            request.unit.route = route.copy()
            self.corridors[request.destinations] = route.copy()
            if len(self.corridors) > 32:
                self.corridors.pop(next(iter(self.corridors)))
