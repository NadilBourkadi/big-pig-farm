"""Terrain rendering functions for the farm view.

Module-level functions that draw terrain (floors, walls, biomes, tunnels)
into FarmView's character/style buffers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.style import Style

from big_pig_farm.data.sprites import (
    FLOOR_CHARS,
    FLOOR_CHARS_FAR,
    FLOOR_COLORS,
    FLOOR_COLORS_FAR,
    TERRAIN,
    WALL_GRAIN,
    WALL_PLANK,
    WALL_POST,
)
from big_pig_farm.entities.biomes import BIOMES, BiomeType
from big_pig_farm.game.world import CellType

if TYPE_CHECKING:
    from big_pig_farm.ui.widgets.farm_view import FarmView


def floor_texture(
    view: FarmView, wx: int, wy: int, far: bool = False,
) -> tuple[str, Style]:
    """Return a deterministic character and style for a floor cell.

    Uses biome-specific palettes when the cell belongs to a biome area.
    Tunnel cells render as grey stone.
    """
    farm = view.state.farm

    # Check for tunnel cells
    if farm.is_valid_position(wx, wy) and farm.cells[wy][wx].is_tunnel:
        h = (wx * 7 + wy * 13) & 0xFFFF
        tunnel_chars = ["·", ".", ",", "'"]
        char = tunnel_chars[h % len(tunnel_chars)]
        tunnel_colors = ["#808080", "#707070", "#909090", "#757575"]
        color = tunnel_colors[(h >> 4) % len(tunnel_colors)]
        return char, Style(color=color, bgcolor="#3a3a3a")

    # Check for biome-specific floor
    biome = farm.get_biome_at(wx, wy)
    if biome is not None and biome != BiomeType.MEADOW:
        info = BIOMES[biome]
        h = (wx * 7 + wy * 13) & 0xFFFF
        chars = info.floor_chars
        colors = info.floor_colors
        char = chars[h % len(chars)]
        color = colors[(h >> 4) % len(colors)]
        return char, Style(color=color, bgcolor=info.floor_bg)

    # Default meadow/hay texture
    h = (wx * 7 + wy * 13) & 0xFFFF
    chars = FLOOR_CHARS_FAR if far else FLOOR_CHARS
    colors = FLOOR_COLORS_FAR if far else FLOOR_COLORS
    char = chars[h % len(chars)]
    color = colors[(h >> 4) % len(colors)]
    return char, Style(color=color, bgcolor="#4a3d28")


def wall_texture(
    view: FarmView,
    wx: int,
    wy: int,
    dx: int = 0,
    dy: int = 0,
    cell_w: int = 1,
    cell_h: int = 1,
) -> tuple[str, Style]:
    """Return (char, style) for a wall cell with wooden fence texture.

    dx/dy are sub-cell offsets (0..cell_w-1, 0..cell_h-1) used at close
    zoom for per-character detail within a single world cell.
    Uses biome-specific wall tints when the wall belongs to a biome area.
    """
    farm = view.state.farm

    # Get biome tint for this wall cell
    plank_palette = WALL_PLANK
    grain_palette = WALL_GRAIN
    post_color = WALL_POST
    if farm.is_valid_position(wx, wy):
        cell = farm.cells[wy][wx]
        if cell.area_id is not None:
            area = farm.get_area_by_id(cell.area_id)
            if area is not None:
                info = BIOMES.get(area.biome)
                if info and info.wall_tint_plank:
                    plank_palette = info.wall_tint_plank
                if info and info.wall_tint_grain:
                    grain_palette = info.wall_tint_grain

    # Use pre-computed wall flags (set by FarmGrid._compute_wall_flags)
    is_corner = False
    is_horizontal = False
    if farm.is_valid_position(wx, wy):
        wall_cell = farm.cells[wy][wx]
        is_corner = wall_cell.is_corner
        is_horizontal = wall_cell.is_horizontal_wall

    h = (wx * 11 + wy * 17) & 0xFFFF
    plank = plank_palette[h % len(plank_palette)]
    grain = grain_palette[(h >> 3) % len(grain_palette)]

    if is_corner:
        return "█", Style(color=post_color)

    if is_horizontal:
        if cell_h > 1:
            if dy == 0:
                return "█", Style(color=plank)
            return "▀", Style(color=plank, bgcolor=grain)
        return "▀", Style(color=plank, bgcolor=grain)

    # Vertical wall
    if cell_w > 1:
        color = grain if dx == 0 else plank
        return "█", Style(color=color)
    return "█", Style(color=plank)


def draw_terrain(
    view: FarmView,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
) -> None:
    """Draw the terrain/floor."""
    farm = view.state.farm
    scale = view._scale()

    if scale < 1.0:
        draw_terrain_far(view, width, height, offset_x, offset_y)
        return

    cell_w = max(1, int(scale))
    cell_h = max(1, int(scale))

    for world_y in range(farm.height):
        for world_x in range(farm.width):
            screen_x = int((world_x - view._viewport_x) * scale) + offset_x
            screen_y = int((world_y - view._viewport_y) * scale) + offset_y

            if not (0 <= screen_x < width and 0 <= screen_y < height):
                continue

            cell = farm.cells[world_y][world_x]

            # Skip void cells (not part of any area or tunnel)
            if cell.area_id is None and not cell.is_tunnel:
                continue

            if cell.cell_type.value == "wall":
                for dy in range(cell_h):
                    for dx in range(cell_w):
                        sx = screen_x + dx
                        sy = screen_y + dy
                        if 0 <= sx < width and 0 <= sy < height:
                            wc, ws = wall_texture(
                                view,
                                world_x, world_y,
                                dx, dy, cell_w, cell_h,
                            )
                            view._char_buffer[sy][sx] = wc
                            view._style_buffer[sy][sx] = ws
                            view._terrain_bg_buffer[sy][sx] = ws
                continue

            if cell.cell_type.value == "bedding":
                char = TERRAIN["bedding"]
                style = Style(color="yellow4")
            elif cell.cell_type.value == "grass":
                char = TERRAIN["grass"]
                style = Style(color="green")
            else:
                char, style = floor_texture(view, world_x, world_y)

            for dy in range(cell_h):
                for dx in range(cell_w):
                    sx = screen_x + dx
                    sy = screen_y + dy
                    if 0 <= sx < width and 0 <= sy < height:
                        view._char_buffer[sy][sx] = char
                        view._style_buffer[sy][sx] = style
                        view._terrain_bg_buffer[sy][sx] = style


def draw_terrain_far(
    view: FarmView,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
) -> None:
    """Simplified terrain for far zoom -- cell-by-cell with biome support.

    At sub-1x scales, world->screen mapping is lossy (multiple world cells
    map to the same screen cell). We iterate screen cells, map back to
    world coordinates, and check a 2x2 block of world cells so that
    single-cell-thick walls are never missed by sub-sampling.
    """
    farm = view.state.farm
    scale = view._scale()
    inv_scale = 1.0 / scale
    vp_x = view._viewport_x
    vp_y = view._viewport_y
    farm_w = farm.width
    farm_h = farm.height
    cells = farm.cells

    # Draw each screen pixel by mapping back to world coordinates
    for sy in range(height):
        wy0 = int((sy - offset_y) * inv_scale) + vp_y
        wy1 = int((sy + 1 - offset_y) * inv_scale) + vp_y
        for sx in range(width):
            wx0 = int((sx - offset_x) * inv_scale) + vp_x
            wx1 = int((sx + 1 - offset_x) * inv_scale) + vp_x

            # Check 2x2 world neighborhood, prefer walls
            wall_cell = None
            floor_cell = None
            for cy in range(wy0, min(wy1, farm_h)):
                if cy < 0:
                    continue
                row = cells[cy]
                for cx in range(wx0, min(wx1, farm_w)):
                    if cx < 0:
                        continue
                    candidate = row[cx]
                    if candidate.area_id is None and not candidate.is_tunnel:
                        continue  # void cell
                    if candidate.cell_type == CellType.WALL:
                        wall_cell = candidate
                        break
                    elif floor_cell is None:
                        floor_cell = candidate
                if wall_cell is not None:
                    break

            cell = wall_cell or floor_cell
            if cell is None:
                continue

            # Use the primary sample coordinates for texture hashing
            wx = max(0, min(wx0, farm_w - 1))
            wy = max(0, min(wy0, farm_h - 1))

            if cell.cell_type == CellType.WALL:
                # Wall -- use biome tint if available
                plank_palette = WALL_PLANK
                grain_palette = WALL_GRAIN
                if cell.area_id is not None:
                    area = farm.get_area_by_id(cell.area_id)
                    if area:
                        info = BIOMES.get(area.biome)
                        if info and info.wall_tint_plank:
                            plank_palette = info.wall_tint_plank
                        if info and info.wall_tint_grain:
                            grain_palette = info.wall_tint_grain

                h = (wx * 11 + wy * 17) & 0xFFFF
                plank = plank_palette[h % len(plank_palette)]
                grain = grain_palette[(h >> 3) % len(grain_palette)]

                # Use pre-computed wall flags for orientation
                if cell.is_horizontal_wall or cell.is_corner:
                    view._char_buffer[sy][sx] = "▀"
                    view._style_buffer[sy][sx] = Style(color=plank, bgcolor=grain)
                else:
                    view._char_buffer[sy][sx] = "█"
                    view._style_buffer[sy][sx] = Style(color=plank)
            else:
                # Floor / tunnel
                char, style = floor_texture(view, wx, wy, far=True)
                view._char_buffer[sy][sx] = char
                view._style_buffer[sy][sx] = style
                view._terrain_bg_buffer[sy][sx] = style
