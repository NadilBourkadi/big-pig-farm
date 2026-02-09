"""Farm view widget - renders the ASCII farm grid with guinea pigs."""

from typing import Optional
from uuid import UUID

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.style import Style

from big_pig_farm.data.sprites import (
    get_pig_sprite,
    get_facility_sprite,
    TERRAIN,
    Direction,
)
from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.entities.facilities import Facility
from big_pig_farm.game.state import GameState


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

    def render(self) -> Text:
        """Render the farm view."""
        # Get available size
        width = self.size.width
        height = self.size.height

        if width <= 0 or height <= 0:
            return Text("Resize window")

        farm = self.state.farm

        # Calculate centering offset if farm is smaller than viewport
        offset_x = max(0, (width - farm.width) // 2)
        offset_y = max(0, (height - farm.height) // 2)

        # Initialize buffers
        self._init_buffers(width, height)

        # Draw terrain (centered)
        self._draw_terrain(width, height, offset_x, offset_y)

        # Draw facilities (centered)
        self._draw_facilities(width, height, offset_x, offset_y)

        # Draw guinea pigs (centered)
        self._draw_guinea_pigs(width, height, offset_x, offset_y)

        # Draw cursor in edit mode
        if self.edit_mode:
            self._draw_cursor(width, height, offset_x, offset_y)

        # Convert buffer to Rich Text
        return self._buffer_to_text()

    def _init_buffers(self, width: int, height: int) -> None:
        """Initialize character and style buffers."""
        self._char_buffer = [[" " for _ in range(width)] for _ in range(height)]
        self._style_buffer = [[None for _ in range(width)] for _ in range(height)]

    def _draw_terrain(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw the terrain/floor (only visible portion)."""
        farm = self.state.farm

        # Only iterate cells that fall within the viewport
        y_start = max(0, self._viewport_y - offset_y)
        y_end = min(farm.height, self._viewport_y - offset_y + height)
        x_start = max(0, self._viewport_x - offset_x)
        x_end = min(farm.width, self._viewport_x - offset_x + width)

        for world_y in range(y_start, y_end):
            for world_x in range(x_start, x_end):
                screen_x = world_x - self._viewport_x + offset_x
                screen_y = world_y - self._viewport_y + offset_y

                if 0 <= screen_x < width and 0 <= screen_y < height:
                    cell = farm.cells[world_y][world_x]

                    if cell.cell_type.value == "wall":
                        # Draw walls with box-drawing characters
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
                        char = TERRAIN["floor"]
                        style = Style(color="grey37")

                    self._char_buffer[screen_y][screen_x] = char
                    self._style_buffer[screen_y][screen_x] = style

    def _draw_facilities(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw all facilities on the farm."""
        for facility in self.state.get_facilities_list():
            self._draw_facility(facility, width, height, offset_x, offset_y)

    def _draw_facility(self, facility: Facility, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw a single facility."""
        # Get sprite based on fill state
        if facility.is_empty:
            sprite = get_facility_sprite(facility.facility_type.value, "empty")
        elif facility.current_amount >= facility.max_amount:
            sprite = get_facility_sprite(facility.facility_type.value, "full")
        else:
            sprite = get_facility_sprite(facility.facility_type.value)

        # Check if this facility is selected
        is_selected = self.edit_mode and facility.id == self.selected_facility_id
        is_moving = is_selected and self.moving_facility

        # Determine color
        if is_moving:
            color = "bright_green"
        elif is_selected:
            color = "yellow"
        else:
            color = "cyan"

        # Draw sprite at facility position
        for dy, line in enumerate(sprite):
            for dx, char in enumerate(line):
                screen_x = facility.position_x + dx - self._viewport_x + offset_x
                screen_y = facility.position_y + dy - self._viewport_y + offset_y

                if 0 <= screen_x < width and 0 <= screen_y < height:
                    if char != " ":
                        self._char_buffer[screen_y][screen_x] = char
                        self._style_buffer[screen_y][screen_x] = Style(color=color)

    def _draw_guinea_pigs(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw all guinea pigs."""
        for pig in self.state.get_pigs_list():
            self._draw_pig(pig, width, height, offset_x, offset_y)

    def _draw_pig(self, pig: GuineaPig, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw a single guinea pig."""
        # Determine direction based on movement
        if pig.path and len(pig.path) > 0:
            next_x = pig.path[0][0]
            direction = Direction.RIGHT if next_x > pig.position.x else Direction.LEFT
        else:
            direction = Direction.RIGHT

        # Get sprite for current state
        sprite = get_pig_sprite(pig.display_state, direction, pig.is_baby)

        # Calculate screen position (center sprite on pig position)
        base_x = int(pig.position.x) - self._viewport_x + offset_x
        base_y = int(pig.position.y) - self._viewport_y + offset_y

        # Determine color based on phenotype
        color = pig.phenotype.ascii_color

        # Highlight if selected
        is_selected = pig.id == self.selected_pig_id
        if is_selected:
            color = "yellow"

        # Draw sprite (block out background only for interior spaces)
        for dy, line in enumerate(sprite):
            # Find the bounds of actual sprite content on this line
            first_char = -1
            last_char = -1
            for i, c in enumerate(line):
                if c != " ":
                    if first_char == -1:
                        first_char = i
                    last_char = i

            for dx, char in enumerate(line):
                screen_x = base_x + dx - len(line) // 2
                screen_y = base_y + dy - len(sprite) // 2

                if 0 <= screen_x < width and 0 <= screen_y < height:
                    # Draw non-space characters, or interior spaces (between first and last char)
                    if char != " ":
                        self._char_buffer[screen_y][screen_x] = char
                        self._style_buffer[screen_y][screen_x] = Style(color=color)
                    elif first_char != -1 and first_char < dx < last_char:
                        # Interior space - block out background
                        self._char_buffer[screen_y][screen_x] = " "
                        self._style_buffer[screen_y][screen_x] = Style()

        # Draw name below pig (if there's room)
        name_y = base_y + len(sprite) // 2 + 1
        if 0 <= name_y < height:
            name = pig.name[:10]  # Truncate long names
            name_x = base_x - len(name) // 2
            for i, char in enumerate(name):
                if 0 <= name_x + i < width:
                    self._char_buffer[name_y][name_x + i] = char
                    self._style_buffer[name_y][name_x + i] = Style(color="white", dim=True)

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

    def center_on_pig(self, pig: GuineaPig) -> None:
        """Center the viewport on a specific guinea pig."""
        width = self.size.width
        height = self.size.height
        farm = self.state.farm

        # Only scroll if farm is larger than viewport
        if farm.width > width:
            self._viewport_x = int(pig.position.x) - width // 2
            self._viewport_x = max(0, min(self._viewport_x, farm.width - width))

        if farm.height > height:
            self._viewport_y = int(pig.position.y) - height // 2
            self._viewport_y = max(0, min(self._viewport_y, farm.height - height))

        self.refresh()

    def select_pig(self, pig_id: Optional[UUID]) -> None:
        """Select a guinea pig."""
        self.selected_pig_id = pig_id

        # Center on selected pig
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

        self._viewport_x += dx
        self._viewport_y += dy

        # Clamp to farm bounds (only if farm is larger than viewport)
        max_x = max(0, farm.width - width)
        max_y = max(0, farm.height - height)

        self._viewport_x = max(0, min(self._viewport_x, max_x))
        self._viewport_y = max(0, min(self._viewport_y, max_y))

        self.refresh()

    def _draw_cursor(self, width: int, height: int, offset_x: int, offset_y: int) -> None:
        """Draw the edit mode cursor."""
        screen_x = self._cursor_x - self._viewport_x + offset_x
        screen_y = self._cursor_y - self._viewport_y + offset_y

        # Draw a blinking cursor marker
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

        # Clamp to farm bounds (inside walls)
        new_x = max(1, min(new_x, farm.width - 2))
        new_y = max(1, min(new_y, farm.height - 2))

        # If moving a facility, move it with the cursor
        if self.moving_facility and self.selected_facility_id:
            facility = self.state.get_facility(self.selected_facility_id)
            if facility and farm.is_walkable(new_x, new_y):
                # Check if new position is valid (not overlapping other facilities)
                can_move = True
                for other in self.state.get_facilities_list():
                    if other.id != facility.id:
                        # Simple overlap check
                        if (abs(other.position_x - new_x) < 3 and
                            abs(other.position_y - new_y) < 3):
                            can_move = False
                            break

                if can_move:
                    # Remove from old position
                    farm.remove_facility(facility)
                    # Update position
                    facility.position_x = new_x
                    facility.position_y = new_y
                    # Place at new position
                    farm.place_facility(facility)

        self._cursor_x = new_x
        self._cursor_y = new_y
        self.refresh()

    def select_facility_at_cursor(self) -> Optional[Facility]:
        """Select the facility under the cursor."""
        if not self.edit_mode:
            return None

        for facility in self.state.get_facilities_list():
            # Check if cursor is within facility bounds
            sprite = get_facility_sprite(facility.facility_type.value)
            sprite_width = max(len(line) for line in sprite)
            sprite_height = len(sprite)

            if (facility.position_x <= self._cursor_x < facility.position_x + sprite_width and
                facility.position_y <= self._cursor_y < facility.position_y + sprite_height):
                self.selected_facility_id = facility.id
                self.refresh()
                return facility

        # No facility under cursor
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
