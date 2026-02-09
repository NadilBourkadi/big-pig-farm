"""Farm view widget - renders the farm grid with guinea pigs."""

from typing import Optional
from uuid import UUID

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.style import Style

from big_pig_farm.data.sprites import (
    ANIM_TICKS_PER_FRAME,
    get_pig_halfblock_sprite,
    get_facility_sprite,
    get_facility_halfblock_sprite,
    FAR_FACILITY_SPRITES,
    FLOOR_CHARS,
    FLOOR_CHARS_FAR,
    FLOOR_COLORS,
    FLOOR_COLORS_FAR,
    TERRAIN,
    Direction,
    ZoomLevel,
    ZOOM_SCALES,
)
from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.entities.facilities import Facility
from big_pig_farm.game.state import GameState


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


class FarmView(Static):
    """Widget that renders the farm grid with guinea pigs and facilities."""

    selected_pig_id: reactive[Optional[UUID]] = reactive(None)
    edit_mode: reactive[bool] = reactive(False)
    selected_facility_id: reactive[Optional[UUID]] = reactive(None)
    moving_facility: reactive[bool] = reactive(False)

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
        self._style_buffer: list[list[Optional[Style]]] = []
        # Cursor position for edit mode
        self._cursor_x = 5
        self._cursor_y = 5
        # Zoom
        self._zoom = ZoomLevel.NORMAL
        # Persistent facing direction per pig (avoids oscillation)
        self._pig_facing: dict[UUID, Direction] = {}
        # Animation tick counter (incremented every render call)
        self._render_tick: int = 0

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
        max_x = max(0, int(farm.width - width / scale))
        max_y = max(0, int(farm.height - height / scale))
        self._viewport_x = max(0, min(self._viewport_x, max_x))
        self._viewport_y = max(0, min(self._viewport_y, max_y))

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
        self._draw_terrain(width, height, offset_x, offset_y, scale)
        self._draw_facilities(width, height, offset_x, offset_y, scale)
        self._draw_guinea_pigs(width, height, offset_x, offset_y, scale)

        if self.edit_mode:
            self._draw_cursor(width, height, offset_x, offset_y, scale)

        return self._buffer_to_text()

    def _init_buffers(self, width: int, height: int) -> None:
        """Initialize character and style buffers."""
        self._char_buffer = [[" " for _ in range(width)] for _ in range(height)]
        self._style_buffer = [[None for _ in range(width)] for _ in range(height)]
        # Separate buffer for terrain/facility background colors.
        # Used when drawing pig outlines so semi-transparent edge pixels
        # blend with the ground instead of with other pigs' body colors.
        self._terrain_bg_buffer = [[None for _ in range(width)] for _ in range(height)]

    # ------------------------------------------------------------------
    # Terrain
    # ------------------------------------------------------------------

    def _floor_texture(self, wx: int, wy: int, far: bool = False) -> tuple[str, Style]:
        """Return a deterministic hay/straw character and style for a floor cell."""
        h = (wx * 7 + wy * 13) & 0xFFFF
        chars = FLOOR_CHARS_FAR if far else FLOOR_CHARS
        colors = FLOOR_COLORS_FAR if far else FLOOR_COLORS
        char = chars[h % len(chars)]
        color = colors[(h >> 4) % len(colors)]
        return char, Style(color=color, bgcolor="#4a3d28")

    def _draw_terrain(self, width: int, height: int, offset_x: int, offset_y: int, scale: float) -> None:
        """Draw the terrain/floor."""
        farm = self.state.farm

        if scale < 1.0:
            self._draw_terrain_far(width, height, offset_x, offset_y, scale)
            return

        for world_y in range(farm.height):
            for world_x in range(farm.width):
                screen_x = int((world_x - self._viewport_x) * scale) + offset_x
                screen_y = int((world_y - self._viewport_y) * scale) + offset_y

                if not (0 <= screen_x < width and 0 <= screen_y < height):
                    continue

                cell = farm.cells[world_y][world_x]

                if cell.cell_type.value == "wall":
                    if world_y == 0 and world_x == 0:
                        char = TERRAIN["corner_tl"]
                    elif world_y == 0 and world_x == farm.width - 1:
                        char = TERRAIN["corner_tr"]
                    elif world_y == farm.height - 1 and world_x == 0:
                        char = TERRAIN["corner_bl"]
                    elif world_y == farm.height - 1 and world_x == farm.width - 1:
                        char = TERRAIN["corner_br"]
                    elif world_y == 0 or world_y == farm.height - 1:
                        char = TERRAIN["wall_h"]
                    else:
                        char = TERRAIN["wall_v"]
                    style = Style(color="bright_white")
                elif cell.cell_type.value == "bedding":
                    char = TERRAIN["bedding"]
                    style = Style(color="yellow4")
                elif cell.cell_type.value == "grass":
                    char = TERRAIN["grass"]
                    style = Style(color="green")
                else:
                    char, style = self._floor_texture(world_x, world_y)

                self._char_buffer[screen_y][screen_x] = char
                self._style_buffer[screen_y][screen_x] = style
                self._terrain_bg_buffer[screen_y][screen_x] = style

                # At close zoom, fill the 2x2 block for this world cell
                if scale >= 2.0:
                    for dy in range(2):
                        for dx in range(2):
                            sx = screen_x + dx
                            sy = screen_y + dy
                            if 0 <= sx < width and 0 <= sy < height:
                                self._char_buffer[sy][sx] = char
                                self._style_buffer[sy][sx] = style
                                self._terrain_bg_buffer[sy][sx] = style

    def _draw_terrain_far(self, width: int, height: int, offset_x: int, offset_y: int, scale: float) -> None:
        """Simplified terrain for far zoom — explicit border + floor fill.

        At sub-1x scales, world→screen mapping is lossy (multiple world cells
        map to the same screen cell). Drawing border explicitly avoids walls
        being overwritten by adjacent floor cells.
        """
        farm = self.state.farm
        wall_style = Style(color="bright_white")

        # Screen extents of the farm rectangle
        x0 = int((0 - self._viewport_x) * scale) + offset_x
        y0 = int((0 - self._viewport_y) * scale) + offset_y
        x1 = int(((farm.width - 1) - self._viewport_x) * scale) + offset_x
        y1 = int(((farm.height - 1) - self._viewport_y) * scale) + offset_y

        # Fill interior with textured floor
        inv_scale = 1.0 / scale
        for sy in range(max(0, y0 + 1), min(height, y1)):
            wy = int((sy - offset_y) * inv_scale) + self._viewport_y
            for sx in range(max(0, x0 + 1), min(width, x1)):
                wx = int((sx - offset_x) * inv_scale) + self._viewport_x
                char, style = self._floor_texture(wx, wy, far=True)
                self._char_buffer[sy][sx] = char
                self._style_buffer[sy][sx] = style
                self._terrain_bg_buffer[sy][sx] = style

        # Draw horizontal walls (top + bottom)
        for sx in range(max(0, x0), min(width, x1 + 1)):
            if 0 <= y0 < height:
                self._char_buffer[y0][sx] = TERRAIN["wall_h"]
                self._style_buffer[y0][sx] = wall_style
            if 0 <= y1 < height:
                self._char_buffer[y1][sx] = TERRAIN["wall_h"]
                self._style_buffer[y1][sx] = wall_style

        # Draw vertical walls (left + right)
        for sy in range(max(0, y0 + 1), min(height, y1)):
            if 0 <= x0 < width:
                self._char_buffer[sy][x0] = TERRAIN["wall_v"]
                self._style_buffer[sy][x0] = wall_style
            if 0 <= x1 < width:
                self._char_buffer[sy][x1] = TERRAIN["wall_v"]
                self._style_buffer[sy][x1] = wall_style

        # Corners
        for cx, cy, key in [
            (x0, y0, "corner_tl"), (x1, y0, "corner_tr"),
            (x0, y1, "corner_bl"), (x1, y1, "corner_br"),
        ]:
            if 0 <= cx < width and 0 <= cy < height:
                self._char_buffer[cy][cx] = TERRAIN[key]
                self._style_buffer[cy][cx] = wall_style

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    def _draw_facilities(self, width: int, height: int, offset_x: int, offset_y: int, scale: float) -> None:
        """Draw all facilities on the farm."""
        for facility in self.state.get_facilities_list():
            self._draw_facility(facility, width, height, offset_x, offset_y, scale)

    def _draw_facility(self, facility: Facility, width: int, height: int, offset_x: int, offset_y: int, scale: float) -> None:
        """Draw a single facility using half-block sprites (with ASCII fallback)."""
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

        for dy, line in enumerate(sprite):
            for dx, char in enumerate(line):
                screen_x = int((facility.position_x + dx - self._viewport_x) * scale) + offset_x
                screen_y = int((facility.position_y + dy - self._viewport_y) * scale) + offset_y

                if 0 <= screen_x < width and 0 <= screen_y < height:
                    if char != " ":
                        self._char_buffer[screen_y][screen_x] = char
                        self._style_buffer[screen_y][screen_x] = Style(color=color)

    # ------------------------------------------------------------------
    # Guinea pigs
    # ------------------------------------------------------------------

    def _draw_guinea_pigs(self, width: int, height: int, offset_x: int, offset_y: int, scale: float) -> None:
        """Draw all guinea pigs, sorted by Y so lower pigs draw on top."""
        pigs = sorted(self.state.get_pigs_list(), key=lambda p: p.position.y)
        for pig in pigs:
            self._draw_pig(pig, width, height, offset_x, offset_y, scale)

    def _draw_pig(self, pig: GuineaPig, width: int, height: int, offset_x: int, offset_y: int, scale: float) -> None:
        """Draw a single guinea pig using half-block sprites (or dot at far zoom)."""
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
            phase = pig_hash % (tpf * 2)
            frame = ((self._render_tick + phase) // tpf) % 2
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

        # Draw down-arrow indicator above selected pig (skip at far zoom — too large)
        if is_selected and self._zoom != ZoomLevel.FAR:
            indicator_y = anchor_y - 1
            indicator_x = base_x - 1
            indicator_style = Style(color="yellow", bold=True)
            for i, ch in enumerate("vvv"):
                if 0 <= indicator_y < height and 0 <= indicator_x + i < width:
                    self._char_buffer[indicator_y][indicator_x + i] = ch
                    self._style_buffer[indicator_y][indicator_x + i] = indicator_style

        # Draw half-block sprite
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

                if is_selected:
                    style = Style(color="yellow", bgcolor=effective_bg, bold=True)
                else:
                    style = Style(color=fg, bgcolor=effective_bg)

                self._char_buffer[screen_y][screen_x] = char
                self._style_buffer[screen_y][screen_x] = style

        # Draw name below pig (skip at far zoom — no room)
        if self._zoom != ZoomLevel.FAR:
            name_y = anchor_y + sprite_h
            if 0 <= name_y < height:
                name = pig.name[:10]
                name_x = base_x - len(name) // 2
                name_style = Style(color="yellow", bold=True) if is_selected else Style(color="white", dim=True)
                for i, char in enumerate(name):
                    if 0 <= name_x + i < width:
                        self._char_buffer[name_y][name_x + i] = char
                        self._style_buffer[name_y][name_x + i] = name_style

    # ------------------------------------------------------------------
    # Buffer → Text
    # ------------------------------------------------------------------

    def _buffer_to_text(self) -> Text:
        """Convert the character buffer to Rich Text."""
        text = Text()

        for y, row in enumerate(self._char_buffer):
            for x, char in enumerate(row):
                style = self._style_buffer[y][x]
                text.append(char, style=style)
            if y < len(self._char_buffer) - 1:
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

        scaled_w = int(farm.width * scale)
        scaled_h = int(farm.height * scale)

        if scaled_w > width:
            self._viewport_x = int(pig.position.x) - int(width / scale) // 2
            max_vx = int(farm.width - width / scale)
            self._viewport_x = max(0, min(self._viewport_x, max_vx))

        if scaled_h > height:
            self._viewport_y = int(pig.position.y) - int(height / scale) // 2
            max_vy = int(farm.height - height / scale)
            self._viewport_y = max(0, min(self._viewport_y, max_vy))

        self.refresh()

    def select_pig(self, pig_id: Optional[UUID]) -> None:
        """Select a guinea pig."""
        self.selected_pig_id = pig_id

        if pig_id:
            pig = self.state.get_guinea_pig(pig_id)
            if pig:
                self.center_on_pig(pig)

        self.refresh()

    def scroll(self, dx: int, dy: int) -> None:
        """Scroll the viewport."""
        width = self.size.width
        height = self.size.height
        farm = self.state.farm
        scale = self._scale()

        self._viewport_x += dx
        self._viewport_y += dy

        max_x = max(0, int(farm.width - width / scale))
        max_y = max(0, int(farm.height - height / scale))

        self._viewport_x = max(0, min(self._viewport_x, max_x))
        self._viewport_y = max(0, min(self._viewport_y, max_y))

        self.refresh()

    # ------------------------------------------------------------------
    # Edit mode (unchanged)
    # ------------------------------------------------------------------

    def _draw_cursor(self, width: int, height: int, offset_x: int, offset_y: int, scale: float) -> None:
        """Draw the edit mode cursor."""
        screen_x = int((self._cursor_x - self._viewport_x) * scale) + offset_x
        screen_y = int((self._cursor_y - self._viewport_y) * scale) + offset_y

        if 0 <= screen_x < width and 0 <= screen_y < height:
            self._char_buffer[screen_y][screen_x] = "█"
            self._style_buffer[screen_y][screen_x] = Style(color="bright_magenta", bold=True)

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

    def select_facility_at_cursor(self) -> Optional[Facility]:
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

    def remove_selected_facility(self) -> Optional[Facility]:
        """Remove the currently selected facility."""
        if self.selected_facility_id:
            facility = self.state.remove_facility(self.selected_facility_id)
            self.selected_facility_id = None
            self.refresh()
            return facility
        return None

    def get_selected_facility(self) -> Optional[Facility]:
        """Get the currently selected facility."""
        if self.selected_facility_id:
            return self.state.get_facility(self.selected_facility_id)
        return None
