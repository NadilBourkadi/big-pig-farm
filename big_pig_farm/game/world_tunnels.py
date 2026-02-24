"""Tunnel carving functions for FarmGrid."""

from __future__ import annotations

from typing import TYPE_CHECKING

from big_pig_farm.entities.areas import FarmArea, TunnelConnection
from big_pig_farm.game.world import CellType

if TYPE_CHECKING:
    from big_pig_farm.game.world import FarmGrid

# Tunnel dimensions: 5 cells wide (half-width 2 -> range -2..+2)
TUNNEL_HALF_WIDTH = 2


def connect_areas(
    farm: FarmGrid, area_a: FarmArea, area_b: FarmArea,
) -> list[TunnelConnection]:
    """Carve two 5-wide tunnel corridors between two areas.

    Tunnels are placed at 1/3 and 2/3 of the shared wall overlap so
    traffic can flow through both without bottlenecking.
    """
    dx = area_b.center_x - area_a.center_x
    dy = area_b.center_y - area_a.center_y

    if abs(dx) >= abs(dy):
        return _carve_horizontal_tunnels(farm, area_a, area_b)
    else:
        return _carve_vertical_tunnels(farm, area_a, area_b)


def _carve_one_horizontal_tunnel(
    farm: FarmGrid,
    area_a_id,
    area_b_id,
    t_x1: int,
    t_x2: int,
    center_y: int,
) -> TunnelConnection:
    """Carve a single horizontal 5-wide tunnel with barrier walls."""
    hw = TUNNEL_HALF_WIDTH
    tunnel_cells = []

    for x in range(t_x1, t_x2 + 1):
        # Walkable corridor
        for dy in range(-hw, hw + 1):
            y = center_y + dy
            if farm.is_valid_position(x, y):
                cell = farm.cells[y][x]
                cell.cell_type = CellType.FLOOR
                cell.is_walkable = True
                cell.is_tunnel = True
                tunnel_cells.append((x, y))

        # Barrier walls on both sides of the corridor
        for barrier_dy in (-(hw + 1), hw + 1):
            y = center_y + barrier_dy
            if farm.is_valid_position(x, y):
                cell = farm.cells[y][x]
                cell.cell_type = CellType.WALL
                cell.is_walkable = False
                cell.is_tunnel = True
                cell.is_horizontal_wall = True
                tunnel_cells.append((x, y))

    tunnel = TunnelConnection(
        area_a_id=area_a_id, area_b_id=area_b_id,
        cells=tunnel_cells, orientation="horizontal",
    )
    farm.tunnels.append(tunnel)
    return tunnel


def _carve_horizontal_tunnels(
    farm: FarmGrid, area_a: FarmArea, area_b: FarmArea,
) -> list[TunnelConnection]:
    """Carve two horizontal 5-wide tunnels between two areas."""
    if area_a.center_x > area_b.center_x:
        area_a, area_b = area_b, area_a

    t_x1 = area_a.x2
    t_x2 = area_b.x1

    overlap_y1 = max(area_a.interior_y1, area_b.interior_y1)
    overlap_y2 = min(area_a.interior_y2, area_b.interior_y2)

    if overlap_y2 - overlap_y1 < 2:
        mid_y = (area_a.center_y + area_b.center_y) // 2
        overlap_y1 = mid_y - 1
        overlap_y2 = mid_y + 1

    span = overlap_y2 - overlap_y1
    center_a = overlap_y1 + span // 4
    center_b = overlap_y1 + 3 * span // 4

    tunnels = [
        _carve_one_horizontal_tunnel(farm, area_a.id, area_b.id, t_x1, t_x2, center_a),
        _carve_one_horizontal_tunnel(farm, area_a.id, area_b.id, t_x1, t_x2, center_b),
    ]
    farm._compute_wall_flags()
    farm._invalidate_walkable_cache()
    return tunnels


def _carve_one_vertical_tunnel(
    farm: FarmGrid,
    area_a_id,
    area_b_id,
    t_y1: int,
    t_y2: int,
    center_x: int,
) -> TunnelConnection:
    """Carve a single vertical tunnel with barrier walls.

    Uses double the half-width of horizontal tunnels to compensate
    for terminal characters being ~2x taller than wide.
    """
    hw = TUNNEL_HALF_WIDTH * 2 + 1
    tunnel_cells = []

    for y in range(t_y1, t_y2 + 1):
        # Walkable corridor
        for dx in range(-hw, hw + 1):
            x = center_x + dx
            if farm.is_valid_position(x, y):
                cell = farm.cells[y][x]
                cell.cell_type = CellType.FLOOR
                cell.is_walkable = True
                cell.is_tunnel = True
                tunnel_cells.append((x, y))

        # Barrier walls on both sides of the corridor
        for barrier_dx in (-(hw + 1), hw + 1):
            x = center_x + barrier_dx
            if farm.is_valid_position(x, y):
                cell = farm.cells[y][x]
                cell.cell_type = CellType.WALL
                cell.is_walkable = False
                cell.is_tunnel = True
                # Vertical tunnel barrier walls are vertical walls (not horizontal)
                tunnel_cells.append((x, y))

    tunnel = TunnelConnection(
        area_a_id=area_a_id, area_b_id=area_b_id,
        cells=tunnel_cells, orientation="vertical",
    )
    farm.tunnels.append(tunnel)
    return tunnel


def _carve_vertical_tunnels(
    farm: FarmGrid, area_a: FarmArea, area_b: FarmArea,
) -> list[TunnelConnection]:
    """Carve two vertical 5-wide tunnels between two areas."""
    if area_a.center_y > area_b.center_y:
        area_a, area_b = area_b, area_a

    t_y1 = area_a.y2
    t_y2 = area_b.y1

    overlap_x1 = max(area_a.interior_x1, area_b.interior_x1)
    overlap_x2 = min(area_a.interior_x2, area_b.interior_x2)

    if overlap_x2 - overlap_x1 < 2:
        mid_x = (area_a.center_x + area_b.center_x) // 2
        overlap_x1 = mid_x - 1
        overlap_x2 = mid_x + 1

    span = overlap_x2 - overlap_x1
    center_a = overlap_x1 + span // 4
    center_b = overlap_x1 + 3 * span // 4

    tunnels = [
        _carve_one_vertical_tunnel(farm, area_a.id, area_b.id, t_y1, t_y2, center_a),
        _carve_one_vertical_tunnel(farm, area_a.id, area_b.id, t_y1, t_y2, center_b),
    ]
    farm._compute_wall_flags()
    farm._invalidate_walkable_cache()
    return tunnels
