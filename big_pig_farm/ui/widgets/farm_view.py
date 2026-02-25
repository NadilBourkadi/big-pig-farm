"""Farm view widget - renders the farm grid with guinea pigs."""

from uuid import UUID

from rich.style import Style
from rich.text import Text
from textual.events import Click, MouseScrollDown, MouseScrollUp
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from big_pig_farm.data.sprites import (
    ZOOM_SCALES,
    Direction,
    ZoomLevel,
    get_facility_halfblock_sprite,
    get_facility_sprite,
)
from big_pig_farm.entities.facilities import Facility
from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.game.state import GameState
from big_pig_farm.ui.widgets.edit_mode import (
    confirm_placement as _confirm_placement,
    draw_cursor as _draw_cursor,
    get_selected_facility as _get_selected_facility,
    move_cursor as _move_cursor,
    remove_selected_facility as _remove_selected_facility,
    select_facility_at_cursor as _select_facility_at_cursor,
    start_moving_facility as _start_moving_facility,
    toggle_edit_mode as _toggle_edit_mode,
)
from big_pig_farm.ui.widgets.pig_renderer import (
    _IndicatorTimer,
    draw_guinea_pigs as _draw_guinea_pigs,
    pig_at_screen_pos as _pig_at_screen_pos,
)
from big_pig_farm.ui.widgets.terrain_renderer import (
    draw_terrain as _draw_terrain,
)

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
    "feast_table": "Feast",
    "campfire": "Campfire",
    "therapy_garden": "Therapy",
    "hot_spring": "Hot Spring",
    "stage": "Stage",
}


VIEWPORT_PADDING = 4  # world cells of extra scroll beyond farm edges


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
        # Cached buffer dimensions -- only reallocate when size changes
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
        # Terrain snapshot cache -- avoids redrawing static terrain every frame
        self._terrain_cache_key: tuple | None = None
        self._terrain_snapshot_char: list[list[str]] = []
        self._terrain_snapshot_style: list[list[Style | None]] = []
        self._terrain_snapshot_bg: list[list[Style | None]] = []

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
            self._viewport_x = max(
                -VIEWPORT_PADDING,
                min(self._viewport_x, max_x_base + VIEWPORT_PADDING),
            )
        else:
            self._viewport_x = 0

        if max_y_base > 0:
            self._viewport_y = max(
                -VIEWPORT_PADDING,
                min(self._viewport_y, max_y_base + VIEWPORT_PADDING),
            )
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

        # Terrain cache: skip _init_buffers + _draw_terrain on cache hit
        cache_key = (
            self._viewport_x, self._viewport_y,
            self._zoom.value, width, height,
            farm.grid_generation,
        )
        if cache_key == self._terrain_cache_key:
            self._restore_terrain_snapshot(height)
        else:
            self._init_buffers(width, height)
            _draw_terrain(self, width, height, offset_x, offset_y)
            self._snapshot_terrain(height)
            self._terrain_cache_key = cache_key

        # Draw layers
        self._draw_facilities(width, height, offset_x, offset_y)
        _draw_guinea_pigs(self, width, height, offset_x, offset_y)

        if self.edit_mode:
            _draw_cursor(self, width, height, offset_x, offset_y)

        return self._buffer_to_text()

    def _init_buffers(self, width: int, height: int) -> None:
        """Initialize or clear character and style buffers.

        Reuses existing buffer arrays when dimensions haven't changed,
        avoiding ~57,600 object allocations per frame.
        """
        if width == self._buf_width and height == self._buf_height:
            # Clear in-place -- much cheaper than reallocating
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

    def _snapshot_terrain(self, height: int) -> None:
        """Snapshot the 3 render buffers after terrain draw.

        Elements (strings, Style objects) are immutable, so shallow row
        copies preserve object identity for the RLE fast-path in
        _buffer_to_text().
        """
        self._terrain_snapshot_char = [
            row[:] for row in self._char_buffer[:height]
        ]
        self._terrain_snapshot_style = [
            row[:] for row in self._style_buffer[:height]
        ]
        self._terrain_snapshot_bg = [
            row[:] for row in self._terrain_bg_buffer[:height]
        ]

    def _restore_terrain_snapshot(self, height: int) -> None:
        """Restore terrain snapshot into render buffers via slice assignment.

        ~120 C-level list_ass_slice calls replace ~9600 Python __setitem__
        calls from _init_buffers + _draw_terrain.
        """
        for row_idx in range(height):
            self._char_buffer[row_idx][:] = (
                self._terrain_snapshot_char[row_idx]
            )
            self._style_buffer[row_idx][:] = (
                self._terrain_snapshot_style[row_idx]
            )
            self._terrain_bg_buffer[row_idx][:] = (
                self._terrain_snapshot_bg[row_idx]
            )

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    def _draw_facilities(
        self, width: int, height: int, offset_x: int, offset_y: int,
    ) -> None:
        """Draw all facilities on the farm."""
        for facility in self.state.get_facilities_list():
            self._draw_facility(facility, width, height, offset_x, offset_y)

    def _draw_facility(
        self,
        facility: Facility,
        width: int,
        height: int,
        offset_x: int,
        offset_y: int,
    ) -> None:
        """Draw a single facility using half-block sprites (with ASCII fallback)."""
        scale = self._scale()

        # Determine state for consumable facilities
        if facility.is_empty:
            state = "empty"
        elif facility.current_amount >= facility.max_amount:
            state = "full"
        else:
            state = ""

        is_selected = (
            self.edit_mode and facility.id == self.selected_facility_id
        )
        is_moving = is_selected and self.moving_facility

        # Try half-block sprite
        halfblock = get_facility_halfblock_sprite(
            facility.facility_type.value, state, self._zoom,
        )

        if halfblock is not None:
            self._draw_facility_halfblock(
                facility, halfblock, width, height,
                offset_x, offset_y, scale, is_selected, is_moving,
            )
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
                screen_x = int(
                    (facility.position_x + dx - self._viewport_x) * scale
                ) + offset_x
                screen_y = int(
                    (facility.position_y + dy - self._viewport_y) * scale
                ) + offset_y

                if 0 <= screen_y < height and char != " ":
                    for cx in range(cell_w):
                        sx = screen_x + cx
                        if 0 <= sx < width:
                            self._char_buffer[screen_y][sx] = char
                            self._style_buffer[screen_y][sx] = Style(
                                color=color,
                            )

    def _draw_facility_halfblock(
        self,
        facility: Facility,
        halfblock: list,
        width: int,
        height: int,
        offset_x: int,
        offset_y: int,
        scale: float,
        is_selected: bool,
        is_moving: bool,
    ) -> None:
        """Draw a facility's half-block sprite and optional label."""
        # Anchor at top-left of facility position (not centered like pigs)
        anchor_x = int(
            (facility.position_x - self._viewport_x) * scale
        ) + offset_x
        anchor_y = int(
            (facility.position_y - self._viewport_y) * scale
        ) + offset_y

        sprite_h = len(halfblock)
        sprite_w = len(halfblock[0]) if halfblock else 0

        for dy, row in enumerate(halfblock):
            for dx, (char, fg, bg) in enumerate(row):
                screen_x = anchor_x + dx
                screen_y = anchor_y + dy

                if not (0 <= screen_x < width and 0 <= screen_y < height):
                    continue

                if char == " " and fg is None and bg is None:
                    continue  # Transparent -- don't overwrite terrain

                if is_moving:
                    style = Style(
                        color="bright_green", bgcolor=bg, bold=True,
                    )
                elif is_selected:
                    style = Style(color="yellow", bgcolor=bg, bold=True)
                else:
                    style = Style(color=fg, bgcolor=bg)

                self._char_buffer[screen_y][screen_x] = char
                self._style_buffer[screen_y][screen_x] = style
                self._terrain_bg_buffer[screen_y][screen_x] = style

        # Draw label below sprite (skip at far zoom -- no room)
        if self._zoom != ZoomLevel.FAR:
            label = _FACILITY_LABELS.get(
                facility.facility_type.value, "",
            )
            if label:
                label_y = anchor_y + sprite_h
                label_x = anchor_x + (sprite_w - len(label)) // 2
                if is_moving:
                    label_style = Style(
                        color="bright_green", bold=True,
                    )
                elif is_selected:
                    label_style = Style(color="yellow", bold=True)
                else:
                    label_style = Style(color="white", dim=True)
                for i, ch in enumerate(label):
                    sx = label_x + i
                    if 0 <= sx < width and 0 <= label_y < height:
                        self._char_buffer[label_y][sx] = ch
                        self._style_buffer[label_y][sx] = label_style

    # ------------------------------------------------------------------
    # Buffer -> Text
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
            self._viewport_x = (
                int(pig.position.x) - int(width / scale) // 2
            )

        if int(farm.height * scale) > height:
            self._viewport_y = (
                int(pig.position.y) - int(height / scale) // 2
            )

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

    def _pig_at_screen_pos(
        self, screen_x: int, screen_y: int,
    ) -> GuineaPig | None:
        """Return the pig whose sprite covers (screen_x, screen_y), or None."""
        return _pig_at_screen_pos(self, screen_x, screen_y)

    # ------------------------------------------------------------------
    # Edit mode (delegated)
    # ------------------------------------------------------------------

    def toggle_edit_mode(self) -> bool:
        """Toggle edit mode on/off. Returns new state."""
        return _toggle_edit_mode(self)

    def move_cursor(self, dx: int, dy: int) -> None:
        """Move the cursor in edit mode."""
        _move_cursor(self, dx, dy)

    def select_facility_at_cursor(self) -> Facility | None:
        """Select the facility under the cursor."""
        return _select_facility_at_cursor(self)

    def start_moving_facility(self) -> bool:
        """Start moving the selected facility."""
        return _start_moving_facility(self)

    def confirm_placement(self) -> bool:
        """Confirm facility placement after moving."""
        return _confirm_placement(self)

    def remove_selected_facility(self) -> Facility | None:
        """Remove the currently selected facility."""
        return _remove_selected_facility(self)

    def get_selected_facility(self) -> Facility | None:
        """Get the currently selected facility."""
        return _get_selected_facility(self)
