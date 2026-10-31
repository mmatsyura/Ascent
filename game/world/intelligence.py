from collections import deque
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class IntelReport:
    title: str
    source: str
    position: tuple[float, float]
    photo: object = None
    elapsed: float = 0


class Intelligence:
    def __init__(self):
        self.discovered_cities = set()
        self.reports = deque(maxlen=32)
        self.revision = 0
        self.unread = 0
        self.on_report = None

    def record(self, title, position, source="Наземна розвідка", photo=None, elapsed=0):
        report = IntelReport(title, source, tuple(position), photo, elapsed)
        self.reports.appendleft(report)
        self.revision += 1
        self.unread += 1
        if self.on_report is not None:
            self.on_report(report)
        return report

    def attach_photo(self, report, photo):
        for index, current in enumerate(self.reports):
            if current is report:
                self.reports[index] = replace(current, photo=photo)
                self.revision += 1
                return True
        return False

    def mark_read(self):
        self.unread = 0

    def update(self, cities, visibility):
        for city in cities:
            if city.position in self.discovered_cities or not visibility.is_visible(city.position):
                continue
            self.discovered_cities.add(city.position)
            kind = "Столиця" if city.capital else "Місто"
            source = "Міські спостерігачі" if city.owner == "blue" else "Наземна розвідка"
            self.record(f"{kind} {city.name}", city.position, source)
