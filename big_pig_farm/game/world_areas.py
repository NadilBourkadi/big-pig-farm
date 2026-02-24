"""Area management functions for FarmGrid."""

from __future__ import annotations

from typing import TYPE_CHECKING

from big_pig_farm.entities.areas import FarmArea
from big_pig_farm.game.world import CellType
from big_pig_farm.game.world_tunnels import connect_areas

if TYPE_CHECKING:
    from big_pig_farm.game.world import FarmGrid


def repair_area_cells(farm: FarmGrid) -> None:
    """Re-stamp area_id on border cells and mark void cells non-walkable.

    Needed for saves created before add_area() was used consistently.
    Also cleans up ghost cells -- cells whose area_id points to an area
    that no longer contains that position (from room repositioning).
    """
    # First pass: clear orphaned area_id from cells outside their area
    for y in range(farm.height):
        for x in range(farm.width):
            cell = farm.cells[y][x]
            if cell.area_id is None or cell.is_tunnel:
                continue
            area = farm.get_area_by_id(cell.area_id)
            if area is None or not area.contains(x, y):
                cell.area_id = None
                cell.facility_id = None
                cell.cell_type = CellType.FLOOR
                cell.is_walkable = False
                cell.is_corner = False
                cell.is_horizontal_wall = False

    # Second pass: stamp cells within each area's bounds
    for area in farm.areas:
        for x in range(area.x1, area.x2 + 1):
            for y in range(area.y1, area.y2 + 1):
                if not farm.is_valid_position(x, y):
                    continue
                cell = farm.cells[y][x]
                if cell.is_tunnel:
                    continue
                is_border = (x == area.x1 or x == area.x2
                             or y == area.y1 or y == area.y2)
                if is_border:
                    cell.cell_type = CellType.WALL
                    cell.is_walkable = False
                    cell.area_id = area.id
                else:
                    # Unconditionally reset interior cells -- fixes stale
                    # WALL cells left behind when rooms reposition.
                    cell.cell_type = CellType.FLOOR
                    if cell.facility_id is None:
                        cell.is_walkable = True
                    cell.area_id = area.id

    # Mark void cells (outside all areas and tunnels) as non-walkable
    for y in range(farm.height):
        for x in range(farm.width):
            cell = farm.cells[y][x]
            if cell.area_id is None and not cell.is_tunnel:
                cell.is_walkable = False

    farm._compute_wall_flags()
    farm._invalidate_walkable_cache()


def get_adjacent_pairs(farm: FarmGrid) -> list[tuple[FarmArea, FarmArea]]:
    """Return all pairs of rooms in horizontally/vertically adjacent grid slots."""
    pairs: list[tuple[FarmArea, FarmArea]] = []
    by_slot: dict[tuple[int, int], FarmArea] = {}
    for area in farm.areas:
        by_slot[(area.grid_col, area.grid_row)] = area

    for (col, row), area in by_slot.items():
        # Right neighbor
        right = by_slot.get((col + 1, row))
        if right is not None:
            pairs.append((area, right))
        # Below neighbor
        below = by_slot.get((col, row + 1))
        if below is not None:
            pairs.append((area, below))

    return pairs


def rebuild_tunnels(farm: FarmGrid) -> None:
    """Re-carve all tunnel connections using current tunnel dimensions.

    Uses get_adjacent_pairs() so newly adjacent rooms after relayout
    get connected, and connections to non-adjacent rooms are dropped.
    """
    if len(farm.areas) < 2:
        return

    # Clear all existing tunnel cells back to their base state
    for tunnel in farm.tunnels:
        for x, y in tunnel.cells:
            if farm.is_valid_position(x, y):
                cell = farm.cells[y][x]
                cell.is_tunnel = False
                cell.is_horizontal_wall = False
                # Restore to wall if on an area border, otherwise void
                if cell.area_id is not None:
                    cell.cell_type = CellType.WALL
                    cell.is_walkable = False
                else:
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = False
    farm.tunnels.clear()

    # Re-carve each adjacent pair with current settings
    for area_a, area_b in get_adjacent_pairs(farm):
        connect_areas(farm, area_a, area_b)


def add_area(farm: FarmGrid, area: FarmArea) -> None:
    """Register an area and carve its walls and interior cells."""
    farm.areas.append(area)
    farm._area_lookup[area.id] = area
    # Set wall cells around area perimeter
    for x in range(area.x1, area.x2 + 1):
        for y in range(area.y1, area.y2 + 1):
            if not farm.is_valid_position(x, y):
                continue
            cell = farm.cells[y][x]
            is_border = (x == area.x1 or x == area.x2
                         or y == area.y1 or y == area.y2)
            if is_border:
                cell.cell_type = CellType.WALL
                cell.is_walkable = False
                cell.area_id = area.id
            else:
                cell.cell_type = CellType.FLOOR
                cell.is_walkable = True
                cell.area_id = area.id
    farm._compute_wall_flags()
    farm._invalidate_walkable_cache()
