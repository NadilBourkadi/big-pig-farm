"""Pathfinding functions for FarmGrid (A* and random walkable lookups)."""

from __future__ import annotations

import heapq
import random
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from big_pig_farm.game.world import FarmGrid

from big_pig_farm.data.config import SIMULATION


def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Manhattan distance heuristic for A*."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(farm: FarmGrid, x: int, y: int) -> list[tuple[int, int]]:
    """Get walkable neighboring cells (4-directional)."""
    neighbors = []
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if farm.is_walkable(nx, ny):
            neighbors.append((nx, ny))
    return neighbors


def find_path(
    farm: FarmGrid,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """Find path from start to goal using A* algorithm."""
    farm._pathfind_calls += 1

    if not farm.is_walkable(goal[0], goal[1]):
        # Try to find nearest walkable cell to goal
        nearest = find_nearest_walkable(farm, goal)
        if nearest is None:
            return []
        goal = nearest

    if start == goal:
        return [start]

    # A* algorithm
    open_set: list[tuple[float, tuple[int, int]]] = [(0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0}
    f_score: dict[tuple[int, int], float] = {start: heuristic(start, goal)}

    iterations = 0
    max_iterations = SIMULATION.MAX_PATHFINDING_ITERATIONS + 250 * len(farm.areas)

    while open_set and iterations < max_iterations:
        iterations += 1
        _, current = heapq.heappop(open_set)

        if current == goal:
            farm._pathfind_nodes += iterations
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in get_neighbors(farm, current[0], current[1]):
            tentative_g = g_score[current] + 1  # Cost is 1 per cell

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                f_score[neighbor] = f
                heapq.heappush(open_set, (f, neighbor))

    farm._pathfind_nodes += iterations
    return []  # No path found


def reset_perf_counters(farm: FarmGrid) -> None:
    """Reset pathfinding performance counters for the next snapshot window."""
    farm._pathfind_calls = 0
    farm._pathfind_nodes = 0


def find_nearest_walkable(
    farm: FarmGrid,
    pos: tuple[int, int],
    max_distance: int = 5,
) -> tuple[int, int] | None:
    """Find the nearest walkable cell to a position."""
    x, y = pos
    for distance in range(1, max_distance + 1):
        for dx in range(-distance, distance + 1):
            for dy in range(-distance, distance + 1):
                if abs(dx) + abs(dy) == distance:
                    nx, ny = x + dx, y + dy
                    if farm.is_walkable(nx, ny):
                        return (nx, ny)
    return None


def find_random_walkable(farm: FarmGrid) -> tuple[int, int] | None:
    """Find a random walkable position on the grid."""
    if farm._walkable_cache is None:
        farm._walkable_cache = [
            (x, y)
            for y in range(1, farm.height - 1)
            for x in range(1, farm.width - 1)
            if farm.is_walkable(x, y)
        ]

    if farm._walkable_cache:
        return random.choice(farm._walkable_cache)
    return None


def find_random_walkable_in_area(
    farm: FarmGrid, area_id: UUID,
) -> tuple[int, int] | None:
    """Find a random walkable position within a specific area."""
    cached = farm._area_walkable_cache.get(area_id)
    if cached is None:
        area = farm._area_lookup.get(area_id)
        if area is None:
            return None
        cached = [
            (x, y)
            for y in range(area.y1, area.y2 + 1)
            for x in range(area.x1, area.x2 + 1)
            if farm.is_walkable(x, y) and farm.cells[y][x].area_id == area_id
        ]
        farm._area_walkable_cache[area_id] = cached
    if cached:
        return random.choice(cached)
    return None
