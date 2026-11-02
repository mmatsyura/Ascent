import pygame


def plan_member_route(member, target, center, navigation):
    planner = getattr(navigation, "member_paths", None)
    if planner is not None:
        planner.submit(member, target, center)
        return
    cells = navigation.allowed_cells()
    route = navigation.find_path(member.position, target, cells)
    if route is None:
        regroup = navigation.nearest_destination(center, radius=48)
        if regroup is not None:
            route = navigation.find_path(member.position, regroup, cells)
    if route is None:
        for distance in (12, 24, 36):
            for angle in range(0, 360, 45):
                candidate = center + pygame.Vector2(distance, 0).rotate(angle)
                if not navigation.can_place(candidate, radius=4):
                    continue
                route = navigation.find_path(member.position, candidate, cells)
                if route is not None:
                    break
            if route is not None:
                break
    member.detour = route or []
    member.detour_goal = pygame.Vector2(target)
    member.retry_time = 0.55


def advance_member(member, target, center, speed, elapsed_seconds, navigation):
    member.direct_remaining -= elapsed_seconds
    revision = navigation.terrain.revision
    if (
        member.direct_remaining > 0
        and member.direct_goal is not None
        and member.direct_goal.distance_squared_to(target) < 64
        and member.direct_revision == revision
    ):
        direct = member.direct_clear
    else:
        direct = navigation.can_move(member.position, target, radius=4)
        member.direct_goal = pygame.Vector2(target)
        member.direct_clear = direct
        member.direct_remaining = 0.18
        member.direct_revision = revision
    if direct:
        planner = getattr(navigation, "member_paths", None)
        if planner is not None:
            planner.cancel(member)
        member.detour.clear()
        member.detour_goal = None
    else:
        target_changed = member.detour_goal is None or member.detour_goal.distance_to(target) > 12
        if member.retry_time <= 0 and (
            not member.detour or target_changed or member.blocked_seconds > 0.1
        ):
            plan_member_route(member, target, center, navigation)

    remaining = speed * elapsed_seconds
    travelled = 0
    direction = member.facing
    while remaining > 1e-8:
        waypoint = pygame.Vector2(member.detour[0]) if member.detour else target
        delta = waypoint - member.position
        distance = delta.length()
        if distance < 1e-7:
            if member.detour:
                member.detour.pop(0)
                continue
            break
        direction = delta / distance
        movement = min(remaining, distance)
        position = (
            waypoint.copy() if movement == distance else member.position + direction * movement
        )
        if not navigation.can_move(member.position, position, radius=4):
            member.direct_remaining = 0
            member.detour.clear()
            member.detour_goal = None
            member.retry_time = min(member.retry_time, 0.1)
            break
        member.position = position
        travelled += movement
        remaining -= movement
        if member.detour and movement == distance:
            member.detour.pop(0)
    member.blocked_seconds = 0 if travelled > 0.001 else member.blocked_seconds + elapsed_seconds
    return travelled, direction
