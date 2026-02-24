"""Grid expansion and room addition functions for FarmGrid."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from big_pig_farm.data.config import ROOM_TIERS
from big_pig_farm.entities.areas import FarmArea, TunnelConnection
from big_pig_farm.entities.biomes import BIOMES, BiomeType
from big_pig_farm.game.world import Cell, CellType
from big_pig_farm.game.world_areas import rebuild_tunnels, repair_area_cells

if TYPE_CHECKING:
    from big_pig_farm.game.world import FarmGrid


def expand_grid(
    farm: FarmGrid,
    new_width: int,
    new_height: int,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Expand the grid canvas and shift existing content by offset.

    Creates a larger grid, copies existing cells into it at the offset
    position, and updates all area/tunnel coordinates.  New cells are
    non-walkable void so pigs can't wander into the gap between areas.
    """
    new_cells = [
        [Cell(is_walkable=False) for _ in range(new_width)]
        for _ in range(new_height)
    ]

    # Copy existing cells
    for y in range(farm.height):
        for x in range(farm.width):
            new_x = x + offset_x
            new_y = y + offset_y
            if 0 <= new_x < new_width and 0 <= new_y < new_height:
                new_cells[new_y][new_x] = farm.cells[y][x]

    farm.width = new_width
    farm.height = new_height
    farm.cells = new_cells

    # Shift area coordinates
    if offset_x != 0 or offset_y != 0:
        for area in farm.areas:
            area.x1 += offset_x
            area.y1 += offset_y
            area.x2 += offset_x
            area.y2 += offset_y

        # Shift tunnel cell coordinates
        for tunnel in farm.tunnels:
            tunnel.cells = [
                (x + offset_x, y + offset_y) for x, y in tunnel.cells
            ]

    farm._invalidate_walkable_cache()


def compute_grid_layout(farm: FarmGrid) -> dict[int, tuple[int, int]]:
    """Compute world-coordinate origins for each area using 2-column grid.

    Returns {area_index: (x1, y1)} for each area.
    """
    gap = 7  # Gap between room walls for tunnel corridor

    # Collect room dimensions per slot
    slots: list[tuple[int, int, int, int]] = []  # (col, row, width, height)
    for area in farm.areas:
        col = area.grid_col
        row = area.grid_row
        room_width = area.x2 - area.x1 + 1
        room_height = area.y2 - area.y1 + 1
        slots.append((col, row, room_width, room_height))

    # Compute max width per column and max height per row
    max_col = max(slot[0] for slot in slots) if slots else 0
    max_row = max(slot[1] for slot in slots) if slots else 0

    col_widths = [0] * (max_col + 1)
    row_heights = [0] * (max_row + 1)
    for col, row, width, height in slots:
        col_widths[col] = max(col_widths[col], width)
        row_heights[row] = max(row_heights[row], height)

    # Cumulative offsets
    col_offsets = [0] * (max_col + 1)
    for column in range(1, max_col + 1):
        col_offsets[column] = col_offsets[column - 1] + col_widths[column - 1] + gap
    row_offsets = [0] * (max_row + 1)
    for row in range(1, max_row + 1):
        row_offsets[row] = row_offsets[row - 1] + row_heights[row - 1] + gap

    # Compute origin for each area, centered within its slot
    origins: dict[int, tuple[int, int]] = {}
    for i, (col, row, width, height) in enumerate(slots):
        center_x = col_offsets[col] + (col_widths[col] - width) // 2
        center_y = row_offsets[row] + (row_heights[row] - height) // 2
        origins[i] = (center_x, center_y)

    return origins


def add_room(
    farm: FarmGrid,
    biome: BiomeType,
    room_name: str | None = None,
) -> tuple[FarmArea, list[TunnelConnection], int, int, dict[UUID, tuple[int, int]]] | None:
    """Add a new room with the given biome using 2-column grid layout.

    Returns (new_area, tunnels, offset_x, offset_y, room_deltas) or None
    if at max rooms.  offset_x/offset_y are the grid expansion offsets.
    room_deltas maps area_id -> (dx, dy) for each existing area that
    repositioned (callers must use this to relocate entities per-room).
    """
    # Ensure there's at least a starter area to attach to
    if not farm.areas:
        farm._create_legacy_starter_area()

    room_idx = len(farm.areas)
    if room_idx >= len(ROOM_TIERS):
        return None

    room_tier = ROOM_TIERS[room_idx]
    room_width = room_tier.room_width
    room_height = room_tier.room_height

    if room_name is None:
        room_name = f"{BIOMES[biome].display_name} Room"

    # Assign next grid slot (reading order, 2 columns)
    new_col = room_idx % 2
    new_row = room_idx // 2

    # Create the area with placeholder coordinates (will be repositioned)
    new_area = FarmArea(
        name=room_name,
        biome=biome,
        x1=0, y1=0,
        x2=room_width - 1, y2=room_height - 1,
        grid_col=new_col, grid_row=new_row,
    )

    # Temporarily add to areas list to compute full grid layout
    farm.areas.append(new_area)
    farm._area_lookup[new_area.id] = new_area
    origins = compute_grid_layout(farm)

    # Compute required grid size
    total_width = 0
    total_height = 0
    for i, area in enumerate(farm.areas):
        origin_x, origin_y = origins[i]
        area_width = area.x2 - area.x1 + 1
        area_height = area.y2 - area.y1 + 1
        total_width = max(total_width, origin_x + area_width)
        total_height = max(total_height, origin_y + area_height)

    # Remove the temporarily added area (we'll re-add via add_area below)
    farm.areas.pop()
    del farm._area_lookup[new_area.id]

    # Compute offset needed to shift existing content
    # (existing areas already have world coords, new layout may differ)
    offset_x = 0
    offset_y = 0
    if len(farm.areas) > 0:
        # Check if existing areas need shifting
        old_origin_0 = (farm.areas[0].x1, farm.areas[0].y1)
        new_origin_0 = origins[0]
        offset_x = new_origin_0[0] - old_origin_0[0]
        offset_y = new_origin_0[1] - old_origin_0[1]

    # Expand grid if needed
    need_width = max(farm.width + max(0, offset_x), total_width)
    need_height = max(farm.height + max(0, offset_y), total_height)

    # If there's negative offset (existing content needs to shift right/down)
    shift_x = max(0, -offset_x) if offset_x < 0 else 0
    shift_y = max(0, -offset_y) if offset_y < 0 else 0
    if shift_x > 0 or shift_y > 0:
        need_width = max(need_width, farm.width + shift_x)
        need_height = max(need_height, farm.height + shift_y)

    # Only shift existing content if offset changed
    entity_offset_x = 0
    entity_offset_y = 0
    room_deltas: dict[UUID, tuple[int, int]] = {}
    if offset_x != 0 or offset_y != 0:
        # We need to rebuild the entire grid with proper positions
        # Clear tunnel cells first
        for tunnel in farm.tunnels:
            for x, y in tunnel.cells:
                if farm.is_valid_position(x, y):
                    cell = farm.cells[y][x]
                    cell.is_tunnel = False
                    cell.is_horizontal_wall = False
        farm.tunnels.clear()

        # Expand and shift
        if need_width > farm.width or need_height > farm.height or shift_x > 0 or shift_y > 0:
            expand_grid(farm, need_width, need_height, shift_x, shift_y)
            entity_offset_x = shift_x
            entity_offset_y = shift_y

        # Clear all area ownership before repositioning so orphaned
        # cells at old positions don't render as ghost walls/floors
        for row in farm.cells:
            for cell in row:
                if cell.area_id is not None and not cell.is_tunnel:
                    cell.area_id = None
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = False
                    cell.is_corner = False
                    cell.is_horizontal_wall = False

        # Compute per-room deltas BEFORE repositioning (after grid shift)
        for i, area in enumerate(farm.areas):
            target_x1, target_y1 = origins[i]
            dx = target_x1 - area.x1
            dy = target_y1 - area.y1
            if dx != 0 or dy != 0:
                room_deltas[area.id] = (dx, dy)

        # Reposition existing areas to their new grid positions
        for i, area in enumerate(farm.areas):
            target_x1, target_y1 = origins[i]
            area_width = area.x2 - area.x1 + 1
            area_height = area.y2 - area.y1 + 1
            area.x1 = target_x1
            area.y1 = target_y1
            area.x2 = target_x1 + area_width - 1
            area.y2 = target_y1 + area_height - 1

        # Rebuild cells for all existing areas
        repair_area_cells(farm)
    elif need_width > farm.width or need_height > farm.height:
        expand_grid(farm, need_width, need_height, 0, 0)

    # Place the new area at its computed position
    new_origin = origins[room_idx]
    new_area.x1 = new_origin[0]
    new_area.y1 = new_origin[1]
    new_area.x2 = new_origin[0] + room_width - 1
    new_area.y2 = new_origin[1] + room_height - 1
    farm.add_area(new_area)

    # Rebuild all tunnel connections based on adjacency
    rebuild_tunnels(farm)

    return new_area, list(farm.tunnels), entity_offset_x, entity_offset_y, room_deltas
