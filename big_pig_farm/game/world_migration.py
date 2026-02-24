"""Layout migration for legacy saves."""

from __future__ import annotations

from typing import TYPE_CHECKING

from big_pig_farm.game.world import Cell
from big_pig_farm.game.world_areas import rebuild_tunnels
from big_pig_farm.game.world_expansion import compute_grid_layout

if TYPE_CHECKING:
    from big_pig_farm.game.state import GameState


def relayout_areas(state: GameState) -> bool:
    """Migrate a legacy or outdated layout to the 2-column grid layout.

    Assigns grid_col/grid_row to each area, computes new world positions,
    relocates pigs and facilities, and rebuilds the grid fresh.
    Returns True if a relayout was performed, False if already up-to-date.
    """
    farm = state.farm
    if len(farm.areas) < 2:
        return False

    # Step 1: Assign grid slots (idempotent if already set)
    for i, area in enumerate(farm.areas):
        area.grid_col = i % 2
        area.grid_row = i // 2

    # Step 2: Compute expected positions using grid layout
    origins = compute_grid_layout(farm)

    # Check if any area is out of position (covers both legacy linear
    # layouts and gap-size changes)
    needs_relayout = any(
        (area.x1, area.y1) != origins[i]
        for i, area in enumerate(farm.areas)
    )
    if not needs_relayout:
        return False

    # Step 3: Compute deltas and relocate entities
    deltas: dict = {}
    for i, area in enumerate(farm.areas):
        target_x1, target_y1 = origins[i]
        dx = target_x1 - area.x1
        dy = target_y1 - area.y1
        deltas[area.id] = (dx, dy)

    # Relocate pigs (those in tunnel corridors will be clamped later)
    for pig in state.get_pigs_list():
        area = farm.get_area_at(int(pig.position.x), int(pig.position.y))
        if area and area.id in deltas:
            dx, dy = deltas[area.id]
            pig.position.x += dx
            pig.position.y += dy
        pig.path = []
        pig.target_position = None
        pig.target_facility_id = None

    # Relocate facilities
    for facility in state.get_facilities_list():
        area = farm.get_area_at(facility.position_x, facility.position_y)
        if area and area.id in deltas:
            dx, dy = deltas[area.id]
            farm.remove_facility(facility)
            facility.position_x += dx
            facility.position_y += dy

    # Step 4: Update area coordinates
    for i, area in enumerate(farm.areas):
        target_x1, target_y1 = origins[i]
        area_width = area.x2 - area.x1 + 1
        area_height = area.y2 - area.y1 + 1
        area.x1 = target_x1
        area.y1 = target_y1
        area.x2 = target_x1 + area_width - 1
        area.y2 = target_y1 + area_height - 1

    # Step 5: Compute required grid size and rebuild
    total_width = 0
    total_height = 0
    for area in farm.areas:
        total_width = max(total_width, area.x2 + 1)
        total_height = max(total_height, area.y2 + 1)

    # Rebuild grid fresh
    farm.width = total_width
    farm.height = total_height
    farm.cells = [
        [Cell(is_walkable=False) for _ in range(total_width)]
        for _ in range(total_height)
    ]
    farm.tunnels.clear()

    # Re-carve all areas
    saved_areas = list(farm.areas)
    farm.areas.clear()
    farm._area_lookup.clear()
    for area in saved_areas:
        farm.add_area(area)

    # Re-place facilities
    for facility in state.get_facilities_list():
        farm.place_facility(facility)

    # Rebuild tunnels using adjacency pairs
    rebuild_tunnels(farm)

    # Clamp any orphaned pigs (e.g. those that were in tunnel corridors)
    # to the nearest walkable cell
    for pig in state.get_pigs_list():
        pig_x, pig_y = int(pig.position.x), int(pig.position.y)
        if not farm.is_walkable(pig_x, pig_y):
            walkable = farm.find_nearest_walkable((pig_x, pig_y), max_distance=20)
            if walkable:
                pig.position.x = float(walkable[0])
                pig.position.y = float(walkable[1])

    return True
