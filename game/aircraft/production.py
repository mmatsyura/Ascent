from collections import deque
from dataclasses import dataclass, field
import math


@dataclass
class ProductionQueue:
    jobs: deque = field(default_factory=deque)
    progress: float = 0


class DroneProduction:
    def __init__(self, fleet):
        self.fleet = fleet
        self.queues = {}
        self.on_ready = None

    def enqueue(self, airport, definition):
        self.queues.setdefault(airport, ProductionQueue()).jobs.append(definition)

    def status(self, airport, key):
        queue = self.queues.get(airport)
        if queue is None or not queue.jobs:
            return 0, None, 0
        count = sum(definition.key == key for definition in queue.jobs)
        active = queue.jobs[0]
        if active.key != key:
            return count, None, 0
        return count, max(0, math.ceil(active.production_duration - queue.progress)), queue.progress / active.production_duration

    def state_key(self, airport):
        queue = self.queues.get(airport)
        return (tuple(definition.key for definition in queue.jobs), int(queue.progress)) if queue is not None else None

    def cancel(self, airport, key):
        queue = self.queues.get(airport)
        if queue is None:
            return False
        for index in range(len(queue.jobs) - 1, -1, -1):
            definition = queue.jobs[index]
            if definition.key != key:
                continue
            del queue.jobs[index]
            if index == 0:
                queue.progress = 0
            self.fleet.kingdom.gold += definition.price
            self.fleet.revision += 1
            return True
        return False

    def update(self, duration):
        for airport, queue in tuple(self.queues.items()):
            if not self.fleet.valid_airport(airport):
                self.fleet.kingdom.gold += sum(definition.price for definition in queue.jobs)
                self.queues.pop(airport)
                self.fleet.stock.pop(airport, None)
                self.fleet.revision += 1
                continue
            remaining = max(0, duration)
            while queue.jobs and remaining > 0:
                definition = queue.jobs[0]
                step = min(remaining, definition.production_duration - queue.progress)
                queue.progress += step
                remaining -= step
                if queue.progress + 1e-8 < definition.production_duration:
                    break
                queue.jobs.popleft()
                queue.progress = 0
                self.fleet.stock[airport][definition.key] += 1
                self.fleet.revision += 1
                if self.on_ready is not None:
                    self.on_ready(f"Дрон готовий до вильоту: {definition.name}")
