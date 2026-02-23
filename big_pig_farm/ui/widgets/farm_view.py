"""Farm view widget - renders the farm grid with guinea pigs."""

from uuid import UUID

from rich.style import Style
from rich.text import Text
from textual.events import Click, MouseScrollDown, MouseScrollUp
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from big_pig_farm.data.indicator_sprites import (
    IndicatorType,
    get_far_indicator,
    get_indicator_halfblock,
    get_pig_indicator_type,
)
from big_pig_farm.data.sprites import (
    ANIM_FRAME_COUNT,
    ANIM_TICKS_PER_FRAME,
    FLOOR_CHARS,
    FLOOR_CHARS_FAR,
    FLOOR_COLORS,
    FLOOR_COLORS_FAR,
    TERRAIN,
    WALL_GRAIN,
    WALL_PLANK,
    WALL_POST,
    ZOOM_SCALES,
    Direction,
    ZoomLevel,
    get_facility_halfblock_sprite,
    get_facility_sprite,
    get_pig_halfblock_sprite,
)
from big_pig_farm.entities.biomes import BIOMES, BiomeType
from big_pig_farm.entities.facilities import Facility
from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.game.state import GameState
from big_pig_farm.game.world import CellType

# Ordered cycle for zoom toggle
_ZOOM_ORDER = [ZoomLevel.FAR, ZoomLevel.NORMAL, ZoomLevel.CLOSE]

# Short labels drawn below facility sprites (normal + close zoom only)
_FACILITY_LABELS: dict[str, str] = {
    "food_bowl": "Food",
    "water_bottle": "Water",
    "hay_rack": "Hay",
    "hideout": "Hideout",
    "exercise_wheel": "Wheel",
    "tunnel": "Tunnel",
    "play_area": "Play",
    "breeding_den": "Love Den",
    "nursery": "Nursery",
    "veggie_garden": "Garden",
    "grooming_station": "Groom",
    "genetics_lab": "Gen. Lab",
}


VIEWPORT_PADDING = 4  # world cells of extra scroll beyond farm edges

# Indicator timing (in render ticks, ~15fps)
_INDICATOR_SHOW_TICKS = 45       # ~3 seconds visible
_INDICATOR_COOLDOWN_TICKS = 150  # ~10 seconds hidden
_INDICATOR_PULSE_TICKS = 8       # toggle bright/dim every ~0.5s


class _IndicatorTimer:
    """Tracks the ephemeral show/cooldown cycle for one pig's status indicator."""
    __slots__ = ("indicator_type", "trigger_tick", "visible")

    def __init__(self, indicator_type: IndicatorType, trigger_tick: int) -> None:
        self.indicator_type = indicator_type
        self.trigger_tick = trigger_tick
        self.visible = True


class FarmView(Static):
    """Widget that renders the farm grid with guinea pigs and facilities."""

    selected_pig_id: reactive[UUID | None] = reactive(None)
    edit_mode: reactive[bool] = reactive(False)
    selected_facility_id: reactive[UUID | None] = reactive(None)
    moving_facility: reactive[bool] = reactive(False)

    class ScrollPanned(Message):
        """Posted when the user scrolls the farm view."""

    class PigClicked(Message):
        """Posted when the user clicks on a pig sprite."""

        def __init__(self, pig: GuineaPig) -> None:
            super().__init__()
            self.pig = pig

    class EmptyClicked(Message):
        """Posted when the user clicks on empty space (no pig)."""

    DEFAULT_CSS = """
    FarmView {
        width: 1fr;
        height: 1fr;
        min-width: 40;
        min-height: 10;
        background: $surface;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._viewport_x = 0
        self._viewport_y = 0
        self._char_buffer: list[list[str]] = []
        self._style_buffer: list[list[Style | None]] = []
        self._terrain_bg_buffer: list[list[Style | None]] = []
        # Cached buffer dimensions — only reallocate when size changes
        self._buf_width: int = 0
        self._buf_height: int = 0
        # Cursor position for edit mode
        self._cursor_x = 5
        self._cursor_y = 5
        # Zoom
        self._zoom = ZoomLevel.NORMAL
        # Persistent facing direction per pig (avoids oscillation)
        self._pig_facing: dict[UUID, Direction] = {}
        # Animation tick counter (incremented every render call)
        self._render_tick: int = 0
        # Status indicator ephemeral timers per pig
        self._indicator_timers: dict[UUID, _IndicatorTimer] = {}

    @property
    def zoom(self) -> ZoomLevel:
        return self._zoom

    def cycle_zoom(self, direction: int = 1) -> ZoomLevel:
        """Cycle zoom level forward (+1) or backward (-1). Returns new level."""
        idx = _ZOOM_ORDER.index(self._zoom)
        idx = (idx + direction) % len(_ZOOM_ORDER)
        self._zoom = _ZOOM_ORDER[idx]
        self._clamp_viewport()
        self.refresh()
        return self._zoom

    def _clamp_viewport(self) -> None:
        """Clamp viewport to valid range for current zoom level."""
        width = self.size.width
        height = self.size.height
        if width <= 0 or height <= 0:
            return
        farm = self.state.farm
        scale = self._scale()

        max_x_base = int(farm.width - width / scale)
        max_y_base = int(farm.height - height / scale)

        if max_x_base > 0:
            self._viewport_x = max(-VIEWPORT_PADDING, min(self._viewport_x, max_x_base + VIEWPORT_PADDING))
        else:
            self._viewport_x = 0

        if max_y_base > 0:
            self._viewport_y = max(-VIEWPORT_PADDING, min(self._viewport_y, max_y_base + VIEWPORT_PADDING))
        else:
            self._viewport_y = 0

    def _scale(self) -> float:
        return ZOOM_SCALES[self._zoom]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> Text:
        """Render the farm view."""
        self._render_tick += 1
        width = self.size.width
        height = self.size.height

        if width <= 0 or height <= 0:
            return Text("Resize window")

        farm = self.state.farm
        scale = self._scale()

        # Scaled farm dimensions (in screen chars)
        scaled_w = int(farm.width * scale)
        scaled_h = int(farm.height * scale)

        # Calculate centering offset if scaled farm is smaller than viewport
        offset_x = max(0, (width - scaled_w) // 2)
        offset_y = max(0, (height - scaled_h) // 2)

        # Initialize buffers
        self._init_buffers(width, height)

        # Draw layers
        self._draw_terrain(width, height, offset_x, offset_y)
        self._draw_facilities(width, height, offset_x, offset_y)
        self._draw_guinea_pigs(width, height, offset_x, offset_y)

        if self.edit_mode:
            self._draw_cursor(width, height, offset_x, offset_y)

        return self._buffer_to_text()

    def _init_buffers(self, width: int, height: int) -> None:
        """Initialize or clear character and style buffers.

        Reuses existing buffer arrays when dimensions haven't changed,
        avoiding ~57,600 object allocations per frame.
        """
        if width == self._buf_width and height == self._buf_height:
            # Clear in-place — much cheaper than reallocating
            for row in self._char_buffer:
                for column in range(width):
                    row[column] = " "
            for row in self._style_buffer:
                for column in range(width):
                    row[column] = None
            for row in self._terrain_bg_buffer:
                for column in range(width):
                    row[column] = None
        else:
            self._buf_width = width
            self._buf_height = height
            self._char_buffer = [[" "] * width for _ in range(height)]
            self._style_buffer = [[None] * width for _ in range(height)]
            self._terrain_bg_buffer = [[None] * width for _ in range(height)]

    # ------------------------------------------------------------------
    # Terrain
    # ------------------------------------------------------------------

    def _floor_texture(self, wx: int, wy: int, far: bool = False) -> tuple[str, Style]:
        """Return a deterministic character and style for a floor cell.

        Uses biome-specific palettes when the cell belongs to a biome area.
        Tunnel cells render as grey stone.
        """
        farm = self.state.farm

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

    def _wall_texture(
        self,
        wx: int,
        wy: int,
        farm_w: int,
        farm_h: int,
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
        farm = self.state.farm

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

    def _draw_terrain(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw the terrain/floor."""
        farm = self.state.farm
        scale = self._scale()

        if scale < 1.0:
            self._draw_terrain_far(width, height, offset_x, offset_y)
            return

        cell_w = max(1, int(scale))
        cell_h = max(1, int(scale))

        for world_y in range(farm.height):
            for world_x in range(farm.width):
                screen_x = int((world_x - self._viewport_x) * scale) + offset_x
                screen_y = int((world_y - self._viewport_y) * scale) + offset_y

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
                                wc, ws = self._wall_texture(
                                    world_x, world_y,
                                    farm.width, farm.height,
                                    dx, dy, cell_w, cell_h,
                                )
                                self._char_buffer[sy][sx] = wc
                                self._style_buffer[sy][sx] = ws
                                self._terrain_bg_buffer[sy][sx] = ws
                    continue

                if cell.cell_type.value == "bedding":
                    char = TERRAIN["bedding"]
                    style = Style(color="yellow4")
                elif cell.cell_type.value == "grass":
                    char = TERRAIN["grass"]
                    style = Style(color="green")
                else:
                    char, style = self._floor_texture(world_x, world_y)

                for dy in range(cell_h):
                    for dx in range(cell_w):
                        sx = screen_x + dx
                        sy = screen_y + dy
                        if 0 <= sx < width and 0 <= sy < height:
                            self._char_buffer[sy][sx] = char
                            self._style_buffer[sy][sx] = style
                            self._terrain_bg_buffer[sy][sx] = style

    def _draw_terrain_far(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Simplified terrain for far zoom — cell-by-cell with biome support.

        At sub-1x scales, world->screen mapping is lossy (multiple world cells
        map to the same screen cell). We iterate screen cells, map back to
        world coordinates, and check a 2×2 block of world cells so that
        single-cell-thick walls are never missed by sub-sampling.
        """
        farm = self.state.farm
        scale = self._scale()
        inv_scale = 1.0 / scale
        vp_x = self._viewport_x
        vp_y = self._viewport_y
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

                # Check 2×2 world neighborhood, prefer walls
                wall_cell = None
                floor_cell = None
                for cy in range(wy0, min(wy1, farm_h)):
                    if cy < 0:
                        continue
                    row = cells[cy]
                    for cx in range(wx0, min(wx1, farm_w)):
                        if cx < 0:
                            continue
                        c = row[cx]
                        if c.area_id is None and not c.is_tunnel:
                            continue  # void cell
                        if c.cell_type == CellType.WALL:
                            wall_cell = c
                            break
                        elif floor_cell is None:
                            floor_cell = c
                    if wall_cell is not None:
                        break

                cell = wall_cell or floor_cell
                if cell is None:
                    continue

                # Use the primary sample coordinates for texture hashing
                wx = max(0, min(wx0, farm_w - 1))
                wy = max(0, min(wy0, farm_h - 1))

                if cell.cell_type == CellType.WALL:
                    # Wall — use biome tint if available
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
                        self._char_buffer[sy][sx] = "▀"
                        self._style_buffer[sy][sx] = Style(color=plank, bgcolor=grain)
                    else:
                        self._char_buffer[sy][sx] = "█"
                        self._style_buffer[sy][sx] = Style(color=plank)
                else:
                    # Floor / tunnel
                    char, style = self._floor_texture(wx, wy, far=True)
                    self._char_buffer[sy][sx] = char
                    self._style_buffer[sy][sx] = style
                    self._terrain_bg_buffer[sy][sx] = style

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    def _draw_facilities(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw all facilities on the farm."""
        for facility in self.state.get_facilities_list():
            self._draw_facility(facility, width, height, offset_x, offset_y)

    def _draw_facility(self, facility: Facility, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw a single facility using half-block sprites (with ASCII fallback)."""
        scale = self._scale()

        # Determine state for consumable facilities
        if facility.is_empty:
            state = "empty"
        elif facility.current_amount >= facility.max_amount:
            state = "full"
        else:
            state = ""

        is_selected = self.edit_mode and facility.id == self.selected_facility_id
        is_moving = is_selected and self.moving_facility

        # Try half-block sprite
        halfblock = get_facility_halfblock_sprite(
            facility.facility_type.value, state, self._zoom,
        )

        if halfblock is not None:
            # Anchor at top-left of facility position (not centered like pigs)
            anchor_x = int((facility.position_x - self._viewport_x) * scale) + offset_x
            anchor_y = int((facility.position_y - self._viewport_y) * scale) + offset_y

            sprite_h = len(halfblock)
            sprite_w = len(halfblock[0]) if halfblock else 0

            for dy, row in enumerate(halfblock):
                for dx, (char, fg, bg) in enumerate(row):
                    screen_x = anchor_x + dx
                    screen_y = anchor_y + dy

                    if not (0 <= screen_x < width and 0 <= screen_y < height):
                        continue

                    if char == " " and fg is None and bg is None:
                        continue  # Transparent — don't overwrite terrain

                    if is_moving:
                        style = Style(color="bright_green", bgcolor=bg, bold=True)
                    elif is_selected:
                        style = Style(color="yellow", bgcolor=bg, bold=True)
                    else:
                        style = Style(color=fg, bgcolor=bg)

                    self._char_buffer[screen_y][screen_x] = char
                    self._style_buffer[screen_y][screen_x] = style
                    self._terrain_bg_buffer[screen_y][screen_x] = style

            # Draw label below sprite (skip at far zoom — no room)
            if self._zoom != ZoomLevel.FAR:
                label = _FACILITY_LABELS.get(facility.facility_type.value, "")
                if label:
                    label_y = anchor_y + sprite_h
                    label_x = anchor_x + (sprite_w - len(label)) // 2
                    if is_moving:
                        label_style = Style(color="bright_green", bold=True)
                    elif is_selected:
                        label_style = Style(color="yellow", bold=True)
                    else:
                        label_style = Style(color="white", dim=True)
                    for i, ch in enumerate(label):
                        sx = label_x + i
                        if 0 <= sx < width and 0 <= label_y < height:
                            self._char_buffer[label_y][sx] = ch
                            self._style_buffer[label_y][sx] = label_style
            return

        # Fallback: ASCII sprite (monochrome cyan)
        sprite = get_facility_sprite(facility.facility_type.value, state)

        if is_moving:
            color = "bright_green"
        elif is_selected:
            color = "yellow"
        else:
            color = "cyan"

        cell_w = max(1, int(scale))
        for dy, line in enumerate(sprite):
            for dx, char in enumerate(line):
                screen_x = int((facility.position_x + dx - self._viewport_x) * scale) + offset_x
                screen_y = int((facility.position_y + dy - self._viewport_y) * scale) + offset_y

                if 0 <= screen_y < height and char != " ":
                    for cx in range(cell_w):
                        sx = screen_x + cx
                        if 0 <= sx < width:
                            self._char_buffer[screen_y][sx] = char
                            self._style_buffer[screen_y][sx] = Style(color=color)

    # ------------------------------------------------------------------
    # Guinea pigs
    # ------------------------------------------------------------------

    def _draw_guinea_pigs(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw all guinea pigs, sorted by Y so lower pigs draw on top."""
        pigs = sorted(self.state.get_pigs_list(), key=lambda p: p.position.y)
        for pig in pigs:
            self._draw_pig(pig, width, height, offset_x, offset_y)

    def _draw_pig(self, pig: GuineaPig, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw a single guinea pig using half-block sprites (or dot at far zoom)."""
        scale = self._scale()

        # Determine direction — look ahead in path for meaningful horizontal
        # movement.  Only update the stored facing when a clear direction is
        # found, so vertical movement and float-boundary crossings don't cause
        # rapid left/right flipping.
        if pig.path and len(pig.path) > 0:
            for wx, _wy in pig.path:
                if wx > pig.position.x + 0.5:
                    self._pig_facing[pig.id] = Direction.RIGHT
                    break
                elif wx < pig.position.x - 0.5:
                    self._pig_facing[pig.id] = Direction.LEFT
                    break
        direction = self._pig_facing.get(pig.id, Direction.RIGHT)

        is_selected = pig.id == self.selected_pig_id

        # Screen position of the pig's world coordinate
        base_x = int((pig.position.x - self._viewport_x) * scale) + offset_x
        base_y = int((pig.position.y - self._viewport_y) * scale) + offset_y

        base_color_name = pig.phenotype.base_color.name  # BLACK, CHOCOLATE, etc.

        # --- All zoom levels: half-block sprite ---
        tpf = ANIM_TICKS_PER_FRAME.get(pig.display_state)
        if tpf:
            pig_hash = pig.id.int
            speed_var = (pig_hash >> 8) % 3 - 1   # -1, 0, or +1
            tpf = max(2, tpf + speed_var)
            frame_count = ANIM_FRAME_COUNT.get(pig.display_state, 2)
            # Ping-pong: 3 frames → 0,1,2,1,0,1,2,1 … (cycle_len=4)
            cycle_len = (frame_count - 1) * 2 if frame_count > 1 else 1
            phase = pig_hash % (tpf * cycle_len)
            pos = ((self._render_tick + phase) // tpf) % cycle_len
            frame = pos if pos < frame_count else cycle_len - pos
        else:
            frame = 0

        halfblock = get_pig_halfblock_sprite(
            pig.display_state, direction, base_color_name,
            is_baby=pig.is_baby, zoom=self._zoom, frame=frame,
        )
        if halfblock is None:
            return

        sprite_h = len(halfblock)
        sprite_w = len(halfblock[0]) if halfblock else 0

        # Center sprite on pig position
        anchor_x = base_x - sprite_w // 2
        anchor_y = base_y - sprite_h // 2

        # Draw oval glow under selected pig (before sprite so it shows
        # through transparent/edge pixels)
        if is_selected and self._zoom != ZoomLevel.FAR:
            glow_bg = "#8a7010"
            pad = 2  # padding around sprite for ellipse bounds
            cx = anchor_x + (sprite_w - 1) / 2
            cy = anchor_y + (sprite_h - 1) / 2
            rx = (sprite_w + 2 * pad) / 2
            ry = (sprite_h + 2 * pad) / 2
            for gy in range(anchor_y - pad, anchor_y + sprite_h + pad):
                for gx in range(anchor_x - pad, anchor_x + sprite_w + pad):
                    if ((gx - cx) / rx) ** 2 + ((gy - cy) / ry) ** 2 > 1.0:
                        continue
                    if 0 <= gx < width and 0 <= gy < height:
                        existing = self._style_buffer[gy][gx]
                        fg = existing.color if existing else None
                        glow_style = Style(color=fg, bgcolor=glow_bg)
                        self._style_buffer[gy][gx] = glow_style
                        self._terrain_bg_buffer[gy][gx] = glow_style

        # Draw half-block sprite (always use natural colors)
        for dy, row in enumerate(halfblock):
            for dx, (char, fg, bg) in enumerate(row):
                screen_x = anchor_x + dx
                screen_y = anchor_y + dy

                if not (0 <= screen_x < width and 0 <= screen_y < height):
                    continue

                if char == " " and fg is None and bg is None:
                    continue  # Transparent pixel — don't overwrite background

                # For semi-transparent edge cells, inherit the bg from
                # the terrain/facility layer so the pig blends with the
                # ground instead of picking up another pig's body color.
                effective_bg = bg
                if effective_bg is None:
                    terrain = self._terrain_bg_buffer[screen_y][screen_x]
                    if terrain is not None:
                        effective_bg = terrain.bgcolor

                style = Style(color=fg, bgcolor=effective_bg)

                self._char_buffer[screen_y][screen_x] = char
                self._style_buffer[screen_y][screen_x] = style

        # Draw status indicator above pig (skip for selected pig — sidebar shows details)
        if not is_selected:
            self._draw_indicator(pig, width, height, anchor_x, anchor_y, base_x, sprite_w)

        # Draw name below pig (skip at far zoom — no room)
        if self._zoom != ZoomLevel.FAR:
            name_y = anchor_y + sprite_h
            if 0 <= name_y < height:
                name = pig.name[:10]
                name_x = base_x - len(name) // 2
                name_style = Style(color="bright_yellow", bold=True) if is_selected else Style(color="white", dim=True)
                for i, char in enumerate(name):
                    if 0 <= name_x + i < width:
                        self._char_buffer[name_y][name_x + i] = char
                        self._style_buffer[name_y][name_x + i] = name_style

    # ------------------------------------------------------------------
    # Status indicators
    # ------------------------------------------------------------------

    def _update_indicator_timer(self, pig: GuineaPig) -> IndicatorType | None:
        """Manage the show/cooldown/resurface cycle for a pig's status indicator.

        Returns the IndicatorType to draw, or None if nothing should be shown.
        """
        current_type = get_pig_indicator_type(pig)
        timer = self._indicator_timers.get(pig.id)
        tick = self._render_tick

        # No critical need — clear timer entirely
        if current_type is None:
            self._indicator_timers.pop(pig.id, None)
            return None

        # New indicator or type changed — start fresh
        if timer is None or timer.indicator_type != current_type:
            timer = _IndicatorTimer(current_type, tick)
            self._indicator_timers[pig.id] = timer
            return current_type

        elapsed = tick - timer.trigger_tick

        # Show phase
        if elapsed < _INDICATOR_SHOW_TICKS:
            return current_type

        # Cooldown phase
        if elapsed < _INDICATOR_SHOW_TICKS + _INDICATOR_COOLDOWN_TICKS:
            return None

        # Cooldown expired — resurface
        timer.trigger_tick = tick
        return current_type

    def _draw_indicator(
        self,
        pig: GuineaPig,
        width: int,
        height: int,
        anchor_x: int,
        anchor_y: int,
        base_x: int,
        sprite_w: int,
    ) -> None:
        """Draw a floating status indicator icon above a pig."""
        indicator_type = self._update_indicator_timer(pig)
        if indicator_type is None:
            return

        # Pulse animation: toggle bright/dim
        bright = (self._render_tick // _INDICATOR_PULSE_TICKS) % 2 == 0

        zoom_val = self._zoom.value  # "far", "normal", "close"

        if self._zoom == ZoomLevel.FAR:
            char, color = get_far_indicator(indicator_type, bright)
            icon_x = base_x
            icon_y = anchor_y - 1
            if 0 <= icon_x < width and 0 <= icon_y < height:
                self._char_buffer[icon_y][icon_x] = char
                self._style_buffer[icon_y][icon_x] = Style(color=color)
            return

        halfblock = get_indicator_halfblock(indicator_type, zoom_val, bright)
        if halfblock is None:
            return

        icon_h = len(halfblock)
        icon_w = len(halfblock[0]) if halfblock else 0

        # Position: centered horizontally on pig, directly above sprite top
        icon_x = base_x - icon_w // 2
        icon_y = anchor_y - icon_h

        for dy, row in enumerate(halfblock):
            for dx, (char, fg, bg) in enumerate(row):
                sx = icon_x + dx
                sy = icon_y + dy
                if not (0 <= sx < width and 0 <= sy < height):
                    continue
                if char == " " and fg is None and bg is None:
                    continue
                self._char_buffer[sy][sx] = char
                self._style_buffer[sy][sx] = Style(color=fg, bgcolor=bg)

    # ------------------------------------------------------------------
    # Buffer → Text
    # ------------------------------------------------------------------

    def _buffer_to_text(self) -> Text:
        """Convert the character buffer to Rich Text.

        Uses run-length encoding to batch consecutive same-style characters
        into single Text.append() calls, reducing call count from ~6400 to
        ~200-500 per frame.
        """
        text = Text()
        style_rows = self._style_buffer
        last_row = len(self._char_buffer) - 1

        for y, row in enumerate(self._char_buffer):
            styles = style_rows[y]
            # Run-length encode: group consecutive chars with the same style
            run_start = 0
            run_style = styles[0] if row else None
            for x in range(1, len(row)):
                style = styles[x]
                if style is not run_style and style != run_style:
                    text.append("".join(row[run_start:x]), style=run_style)
                    run_start = x
                    run_style = style
            # Flush final run
            if row:
                text.append("".join(row[run_start:]), style=run_style)
            if y < last_row:
                text.append("\n")

        return text

    # ------------------------------------------------------------------
    # Camera / viewport
    # ------------------------------------------------------------------

    def center_on_pig(self, pig: GuineaPig) -> None:
        """Center the viewport on a specific guinea pig."""
        width = self.size.width
        height = self.size.height
        farm = self.state.farm
        scale = self._scale()

        if int(farm.width * scale) > width:
            self._viewport_x = int(pig.position.x) - int(width / scale) // 2

        if int(farm.height * scale) > height:
            self._viewport_y = int(pig.position.y) - int(height / scale) // 2

        self._clamp_viewport()
        self.refresh()

    def select_pig(self, pig_id: UUID | None) -> None:
        """Select a guinea pig."""
        self.selected_pig_id = pig_id

        if pig_id:
            pig = self.state.get_guinea_pig(pig_id)
            if pig:
                self.center_on_pig(pig)

        self.refresh()

    def scroll(self, dx: int, dy: int) -> None:
        """Scroll the viewport."""
        self._viewport_x += dx
        self._viewport_y += dy
        self._clamp_viewport()
        self.refresh()

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        """Pan viewport on scroll-up. Shift+scroll pans left instead."""
        if event.shift:
            self.scroll(-2, 0)
        else:
            self.scroll(0, -2)
        self.post_message(self.ScrollPanned())

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        """Pan viewport on scroll-down. Shift+scroll pans right instead."""
        if event.shift:
            self.scroll(2, 0)
        else:
            self.scroll(0, 2)
        self.post_message(self.ScrollPanned())

    def on_click(self, event: Click) -> None:
        """Click on a pig to follow, or on empty space to stop following."""
        if self.edit_mode:
            return
        pig = self._pig_at_screen_pos(event.x, event.y)
        if pig is not None:
            self.post_message(self.PigClicked(pig))
        else:
            self.post_message(self.EmptyClicked())

    def _pig_at_screen_pos(self, screen_x: int, screen_y: int) -> GuineaPig | None:
        """Return the pig whose sprite covers (screen_x, screen_y), or None."""
        scale = self._scale()
        width = self.size.width
        height = self.size.height

        farm = self.state.farm
        scaled_w = int(farm.width * scale)
        scaled_h = int(farm.height * scale)
        offset_x = max(0, (width - scaled_w) // 2)
        offset_y = max(0, (height - scaled_h) // 2)

        best_pig: GuineaPig | None = None
        best_dist = float("inf")

        for pig in self.state.get_pigs_list():
            direction = self._pig_facing.get(pig.id, Direction.RIGHT)
            base_color_name = pig.phenotype.base_color.name

            # Use frame=0 for hit-testing — all frames share the same dimensions
            halfblock = get_pig_halfblock_sprite(
                pig.display_state, direction, base_color_name,
                is_baby=pig.is_baby, zoom=self._zoom, frame=0,
            )
            if halfblock is None:
                continue

            sprite_h = len(halfblock)
            sprite_w = len(halfblock[0])

            base_x = int((pig.position.x - self._viewport_x) * scale) + offset_x
            base_y = int((pig.position.y - self._viewport_y) * scale) + offset_y

            anchor_x = base_x - sprite_w // 2
            anchor_y = base_y - sprite_h // 2

            # 1px padding on small sprites so far-zoom dots are easier to click
            pad = 1 if sprite_w <= 3 or sprite_h <= 3 else 0
            if not (anchor_x - pad <= screen_x < anchor_x + sprite_w + pad
                    and anchor_y - pad <= screen_y < anchor_y + sprite_h + pad):
                continue

            # Pick the pig closest to the click point (overlapping pigs
            # resolve by center distance, not render Z-order)
            dist = abs(screen_x - base_x) + abs(screen_y - base_y)
            if dist < best_dist:
                best_dist = dist
                best_pig = pig

        return best_pig

    # ------------------------------------------------------------------
    # Edit mode (unchanged)
    # ------------------------------------------------------------------

    def _draw_cursor(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw the edit mode cursor."""
        scale = self._scale()
        screen_x = int((self._cursor_x - self._viewport_x) * scale) + offset_x
        screen_y = int((self._cursor_y - self._viewport_y) * scale) + offset_y

        cell_w = max(1, int(scale))
        if 0 <= screen_y < height:
            for cx in range(cell_w):
                sx = screen_x + cx
                if 0 <= sx < width:
                    self._char_buffer[screen_y][sx] = "█"
                    self._style_buffer[screen_y][sx] = Style(color="bright_magenta", bold=True)

    def toggle_edit_mode(self) -> bool:
        """Toggle edit mode on/off. Returns new state."""
        self.edit_mode = not self.edit_mode
        if not self.edit_mode:
            self.selected_facility_id = None
            self.moving_facility = False
        self.refresh()
        return self.edit_mode

    def move_cursor(self, dx: int, dy: int) -> None:
        """Move the cursor in edit mode."""
        if not self.edit_mode:
            return

        farm = self.state.farm
        new_x = self._cursor_x + dx
        new_y = self._cursor_y + dy

        new_x = max(1, min(new_x, farm.width - 2))
        new_y = max(1, min(new_y, farm.height - 2))

        if self.moving_facility and self.selected_facility_id:
            facility = self.state.get_facility(self.selected_facility_id)
            if facility and farm.is_walkable(new_x, new_y):
                can_move = True
                for other in self.state.get_facilities_list():
                    if other.id != facility.id:
                        if (abs(other.position_x - new_x) < 3 and
                            abs(other.position_y - new_y) < 3):
                            can_move = False
                            break

                if can_move:
                    farm.remove_facility(facility)
                    facility.position_x = new_x
                    facility.position_y = new_y
                    farm.place_facility(facility)

        self._cursor_x = new_x
        self._cursor_y = new_y
        self.refresh()

    def select_facility_at_cursor(self) -> Facility | None:
        """Select the facility under the cursor."""
        if not self.edit_mode:
            return None

        for facility in self.state.get_facilities_list():
            # Use halfblock sprite dimensions for hit-testing
            halfblock = get_facility_halfblock_sprite(
                facility.facility_type.value, "", self._zoom,
            )
            if halfblock is not None:
                sprite_height = len(halfblock)
                sprite_width = len(halfblock[0]) if halfblock else 0
            else:
                sprite = get_facility_sprite(facility.facility_type.value)
                sprite_width = max(len(line) for line in sprite)
                sprite_height = len(sprite)

            if (facility.position_x <= self._cursor_x < facility.position_x + sprite_width and
                facility.position_y <= self._cursor_y < facility.position_y + sprite_height):
                self.selected_facility_id = facility.id
                self.refresh()
                return facility

        self.selected_facility_id = None
        self.refresh()
        return None

    def start_moving_facility(self) -> bool:
        """Start moving the selected facility."""
        if self.selected_facility_id:
            self.moving_facility = True
            self.refresh()
            return True
        return False

    def confirm_placement(self) -> bool:
        """Confirm facility placement after moving."""
        if self.moving_facility:
            self.moving_facility = False
            self.refresh()
            return True
        return False

    def remove_selected_facility(self) -> Facility | None:
        """Remove the currently selected facility."""
        if self.selected_facility_id:
            facility = self.state.remove_facility(self.selected_facility_id)
            self.selected_facility_id = None
            self.refresh()
            return facility
        return None

    def get_selected_facility(self) -> Facility | None:
        """Get the currently selected facility."""
        if self.selected_facility_id:
            return self.state.get_facility(self.selected_facility_id)
        return None
