"""Facilities management screen."""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Static, DataTable, Footer

from big_pig_farm.game.state import GameState
from big_pig_farm.economy.currency import add_money
from big_pig_farm.economy.shop import get_facility_cost


class FacilitiesScreen(Screen):
    """Screen showing all placed facilities."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("r", "remove_facility", "Remove"),
        ("m", "move_facility", "Move"),
    ]

    DEFAULT_CSS = """
    FacilitiesScreen {
        layout: vertical;
        background: $surface;
    }

    #facilities-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #facilities-table {
        height: 1fr;
        margin: 1;
    }

    #facilities-help {
        height: 3;
        padding: 1;
        background: $surface-darken-1;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        """Compose the facilities screen."""
        count = len(self.state.facilities)
        yield Static(f"Facilities ({count} placed)", id="facilities-header")

        yield DataTable(id="facilities-table")

        yield Static(
            "Arrow keys to select | R to remove | M to move (coming soon)",
            id="facilities-help"
        )

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        table = self.query_one("#facilities-table", DataTable)
        table.add_columns("Name", "Position", "Level", "Status")
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the table data."""
        table = self.query_one("#facilities-table", DataTable)
        table.clear()

        for facility in self.state.get_facilities_list():
            name = facility.facility_type.display_name
            position = f"({facility.position_x}, {facility.position_y})"
            level = f"Lv.{facility.level}"

            # Status based on fill level for consumables
            if facility.max_amount > 0:
                fill_pct = int((facility.current_amount / facility.max_amount) * 100)
                if fill_pct == 0:
                    status = "Empty!"
                elif fill_pct < 30:
                    status = f"Low ({fill_pct}%)"
                else:
                    status = f"OK ({fill_pct}%)"
            else:
                status = "Active"

            table.add_row(name, position, level, status, key=str(facility.id))

    def action_go_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()

    def action_remove_facility(self) -> None:
        """Remove the selected facility and refund its cost."""
        table = self.query_one("#facilities-table", DataTable)
        if table.cursor_row is None:
            return

        row_key, _ = table.coordinate_to_cell_key((table.cursor_row, 0))
        if row_key:
            facility_id = UUID(str(row_key.value))
            facility = self.state.facilities.get(facility_id)

            if facility:
                # Get refund amount
                refund = get_facility_cost(facility.facility_type)
                name = facility.facility_type.value.replace('_', ' ').title()
                # Remove from state
                self.state.remove_facility(facility_id)
                # Refund
                add_money(self.state, refund, f"Removed {name}")
                self.notify(f"Removed {name} (+${refund})")
                self._refresh_table()
                self._update_header()

    def action_move_facility(self) -> None:
        """Move the selected facility (placeholder)."""
        self.notify("Move feature coming soon!")

    def _update_header(self) -> None:
        """Update the header."""
        header = self.query_one("#facilities-header", Static)
        count = len(self.state.facilities)
        header.update(f"Facilities ({count} placed)")
