"""Guinea pig list/browser screen."""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Static, DataTable, Footer

from big_pig_farm.economy.market import calculate_pig_value, sell_pig
from big_pig_farm.game.state import GameState
from big_pig_farm.ui.screens.pig_detail import PigDetailScreen
from big_pig_farm.ui.utils import format_needs_bar


class PigListScreen(Screen):
    """Screen showing all guinea pigs in a list."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("v", "view_pig", "View"),
        ("f", "follow_pig", "Follow"),
        ("s", "sell_pig", "Sell"),
        ("r", "rename_pig", "Rename"),
        ("l", "toggle_breeding_lock", "Lock"),
        ("m", "toggle_mark_sale", "Mark"),
    ]

    DEFAULT_CSS = """
    PigListScreen {
        layout: vertical;
        background: $surface;
    }

    #pig-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #pig-table {
        height: 1fr;
        margin: 1;
    }

    #pig-footer-info {
        height: 2;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._table: Optional[DataTable] = None

    def compose(self) -> ComposeResult:
        """Compose the pig list screen."""
        count = self.state.pig_count
        capacity = self.state.capacity
        yield Static(f"Guinea Pigs ({count}/{capacity})", id="pig-header")

        self._table = DataTable(id="pig-table")
        yield self._table

        yield Static("V = View | F = Follow | L = Lock | M = Mark | S = Sell", id="pig-footer-info")

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        if self._table:
            self._table.cursor_type = "row"
            self._table.add_columns("Name", "Age", "Gender", "Color", "Happiness", "Breed", "Value")
            self._refresh_table()
            self._table.focus()

    def _refresh_table(self) -> None:
        """Refresh the table data."""
        if not self._table:
            return

        self._table.clear()

        for pig in self.state.get_pigs_list():
            age_str = f"{int(pig.age_days)}d ({pig.age_group.value})"
            happiness_bar = format_needs_bar(pig.needs.happiness)
            value = calculate_pig_value(pig, self.state)

            # Breeding status column
            if pig.is_baby and pig.marked_for_sale:
                breed_status = "Sell@Adult"
            elif pig.breeding_locked:
                breed_status = "LOCKED"
            elif pig.is_pregnant:
                breed_status = "Pregnant"
            elif not pig.is_adult:
                breed_status = "Baby"
            elif pig.can_breed:
                breed_status = "Ready"
            else:
                breed_status = "Not ready"

            self._table.add_row(
                pig.name,
                age_str,
                pig.gender.value.capitalize(),
                pig.phenotype.display_name,
                happiness_bar,
                breed_status,
                f"${value}",
                key=str(pig.id),
            )

    def _get_selected_pig(self):
        """Get the currently selected pig."""
        if not self._table or self._table.cursor_row is None:
            return None

        row_key, _ = self._table.coordinate_to_cell_key((self._table.cursor_row, 0))

        if row_key:
            pig_id = UUID(str(row_key.value))
            return self.state.get_guinea_pig(pig_id)
        return None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on a row - view pig details."""
        self.action_view_pig()

    def action_go_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()

    def action_view_pig(self) -> None:
        """View the selected pig's details."""
        pig = self._get_selected_pig()
        if pig:
            self.app.push_screen(PigDetailScreen(self.state, pig))

    def action_sell_pig(self) -> None:
        """Sell the selected pig."""
        pig = self._get_selected_pig()
        if pig:
            value = sell_pig(self.state, pig)
            self.notify(f"Sold {pig.name} for ${value}!")
            self._refresh_table()
            self._update_header()

    def action_toggle_breeding_lock(self) -> None:
        """Toggle breeding lock on the selected pig."""
        pig = self._get_selected_pig()
        if pig:
            pig.breeding_locked = not pig.breeding_locked
            status = "locked" if pig.breeding_locked else "unlocked"
            self.notify(f"{pig.name} breeding {status}")
            self._refresh_table()

    def action_toggle_mark_sale(self) -> None:
        """Toggle auto-sell mark on the selected pig."""
        pig = self._get_selected_pig()
        if not pig:
            return
        if not pig.is_baby:
            self.notify("Only baby pigs can be marked for auto-sell", severity="warning")
            return
        pig.marked_for_sale = not pig.marked_for_sale
        status = "marked for auto-sell" if pig.marked_for_sale else "unmarked"
        self.notify(f"{pig.name} {status}")
        self._refresh_table()

    def action_follow_pig(self) -> None:
        """Follow the selected pig on the main screen."""
        pig = self._get_selected_pig()
        if pig:
            # Store pig to follow and go back to main screen
            self.app.pig_to_follow = pig
            self.app.pop_screen()

    def action_rename_pig(self) -> None:
        """Rename the selected pig (placeholder)."""
        self.notify("Rename feature coming soon!")

    def _update_header(self) -> None:
        """Update the header."""
        header = self.query_one("#pig-header", Static)
        count = self.state.pig_count
        capacity = self.state.capacity
        header.update(f"Guinea Pigs ({count}/{capacity})")
