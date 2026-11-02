import pygame


def simplify_route(points, tolerance=4):
    points = [pygame.Vector2(point) for point in points]
    if len(points) < 3:
        return points
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        first, last = pending.pop()
        direction = points[last] - points[first]
        length_squared = direction.length_squared()
        furthest = None
        maximum_distance = tolerance * tolerance
        for index in range(first + 1, last):
            progress = (
                max(0, min(1, (points[index] - points[first]).dot(direction) / length_squared))
                if length_squared
                else 0
            )
            projection = points[first] + direction * progress
            distance = points[index].distance_squared_to(projection)
            if distance > maximum_distance:
                maximum_distance = distance
                furthest = index
        if furthest is not None:
            keep.add(furthest)
            pending.extend(((first, furthest), (furthest, last)))
    return [points[index] for index in sorted(keep)]
