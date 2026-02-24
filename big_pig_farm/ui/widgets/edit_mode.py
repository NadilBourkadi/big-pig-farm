"""Edit mode functions for the farm view.

Module-level functions that handle facility selection, cursor movement,
and placement in edit mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.style import Style

from big_pig_farm.data.sprites import get_facility_halfblock_sprite, get_facility_sprite
from big_pig_farm.entities.facilities import Facility

if TYPE_CHECKING:
    from big_pig_farm.ui.widgets.farm_view import FarmView


def toggle_edit_mode(view: FarmView) -> bool:
    """Toggle edit mode on/off. Returns new state."""
    view.edit_mode = not view.edit_mode
    if not view.edit_mode:
        view.selected_facility_id = None
        view.moving_facility = False
    view.refresh()
    return view.edit_mode


def move_cursor(view: FarmView, dx: int, dy: int) -> None:
    """Move the cursor in edit mode."""
    if not view.edit_mode:
        return

    farm = view.state.farm
    new_x = view._cursor_x + dx
    new_y = view._cursor_y + dy

    new_x = max(1, min(new_x, farm.width - 2))
    new_y = max(1, min(new_y, farm.height - 2))

    if view.moving_facility and view.selected_facility_id:
        facility = view.state.get_facility(view.selected_facility_id)
        if facility and farm.is_walkable(new_x, new_y):
            can_move = True
            for other in view.state.get_facilities_list():
                if other.id != facility.id:
                    if (abs(other.position_x - new_x) < 3
                            and abs(other.position_y - new_y) < 3):
                        can_move = False
                        break

            if can_move:
                farm.remove_facility(facility)
                facility.position_x = new_x
                facility.position_y = new_y
                farm.place_facility(facility)

    view._cursor_x = new_x
    view._cursor_y = new_y
    view.refresh()


def select_facility_at_cursor(view: FarmView) -> Facility | None:
    """Select the facility under the cursor."""
    if not view.edit_mode:
        return None

    for facility in view.state.get_facilities_list():
        # Use halfblock sprite dimensions for hit-testing
        halfblock = get_facility_halfblock_sprite(
            facility.facility_type.value, "", view._zoom,
        )
        if halfblock is not None:
            sprite_height = len(halfblock)
            sprite_width = len(halfblock[0]) if halfblock else 0
        else:
            sprite = get_facility_sprite(facility.facility_type.value)
            sprite_width = max(len(line) for line in sprite)
            sprite_height = len(sprite)

        if (facility.position_x <= view._cursor_x < facility.position_x + sprite_width
                and facility.position_y <= view._cursor_y < facility.position_y + sprite_height):
            view.selected_facility_id = facility.id
            view.refresh()
            return facility

    view.selected_facility_id = None
    view.refresh()
    return None


def start_moving_facility(view: FarmView) -> bool:
    """Start moving the selected facility."""
    if view.selected_facility_id:
        view.moving_facility = True
        view.refresh()
        return True
    return False


def confirm_placement(view: FarmView) -> bool:
    """Confirm facility placement after moving."""
    if view.moving_facility:
        view.moving_facility = False
        view.refresh()
        return True
    return False


def remove_selected_facility(view: FarmView) -> Facility | None:
    """Remove the currently selected facility."""
    if view.selected_facility_id:
        facility = view.state.remove_facility(view.selected_facility_id)
        view.selected_facility_id = None
        view.refresh()
        return facility
    return None


def get_selected_facility(view: FarmView) -> Facility | None:
    """Get the currently selected facility."""
    if view.selected_facility_id:
        return view.state.get_facility(view.selected_facility_id)
    return None


def draw_cursor(
    view: FarmView,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
) -> None:
    """Draw the edit mode cursor."""
    scale = view._scale()
    screen_x = int((view._cursor_x - view._viewport_x) * scale) + offset_x
    screen_y = int((view._cursor_y - view._viewport_y) * scale) + offset_y

    cell_w = max(1, int(scale))
    if 0 <= screen_y < height:
        for cx in range(cell_w):
            sx = screen_x + cx
            if 0 <= sx < width:
                view._char_buffer[screen_y][sx] = "█"
                view._style_buffer[screen_y][sx] = Style(
                    color="bright_magenta", bold=True,
                )
