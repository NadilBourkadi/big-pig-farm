"""Guinea pig list/browser screen with split detail view."""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Static, DataTable, Footer

from big_pig_farm.economy.market import calculate_pig_value, sell_pig
from big_pig_farm.game.state import GameState
from big_pig_farm.ui.screens.pig_detail import PigDetailPanel
from big_pig_farm.ui.utils import format_needs_bar, format_breeding_status


class PigListScreen(Screen):
    """Screen showing all guinea pigs with a split detail panel."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("f", "follow_pig", "Follow"),
        ("s", "sell_pig", "Sell"),
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

    #pig-split {
        layout: horizontal;
        height: 1fr;
    }

    #pig-table {
        width: 1fr;
        height: 100%;
    }

    #pig-detail-panel {
        width: 42;
        height: 100%;
        border-left: solid $secondary;
        overflow-y: auto;
        padding: 1;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        """Compose the pig list screen with split detail panel."""
        count = self.state.pig_count
        capacity = self.state.capacity
        yield Static(f"Guinea Pigs ({count}/{capacity})", id="pig-header")

        with Container(id="pig-split"):
            yield DataTable(id="pig-table")
            yield PigDetailPanel(self.state, id="pig-detail-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        # Set styles inline — widget DEFAULT_CSS has higher specificity than
        # screen DEFAULT_CSS in Textual 0.47, so screen-level CSS doesn't apply.
        split = self.query_one("#pig-split", Container)
        split.styles.layout = "horizontal"
        split.styles.height = "1fr"

        table = self.query_one("#pig-table", DataTable)
        table.styles.width = "1fr"
        table.styles.height = "100%"
        table.cursor_type = "row"
        table.add_columns("Name", "Age", "Gender", "Color", "Happiness", "Breed", "Value")

        panel = self.query_one("#pig-detail-panel", PigDetailPanel)
        panel.styles.width = 42
        panel.styles.height = "100%"
        panel.styles.overflow_y = "auto"

        self._refresh_table()
        table.focus()

    def _refresh_table(self) -> None:
        """Refresh the table data."""
        table = self.query_one("#pig-table", DataTable)
        table.clear()

        for pig in self.state.get_pigs_list():
            age_str = f"{int(pig.age_days)}d ({pig.age_group.value})"
            happiness_bar = format_needs_bar(pig.needs.happiness)
            value = calculate_pig_value(pig, self.state)
            breed_status = format_breeding_status(pig)

            table.add_row(
                pig.name,
                age_str,
                pig.gender.value.capitalize(),
                pig.phenotype.display_name,
                happiness_bar,
                breed_status,
                f"${value}",
                key=str(pig.id),
            )

        # Select first row to show details
        if self.state.get_pigs_list():
            self._update_detail_panel()

    def _get_selected_pig(self):
        """Get the currently selected pig."""
        table = self.query_one("#pig-table", DataTable)
        if table.cursor_row is None:
            return None

        row_key, _ = table.coordinate_to_cell_key((table.cursor_row, 0))

        if row_key:
            pig_id = UUID(str(row_key.value))
            return self.state.get_guinea_pig(pig_id)
        return None

    def _update_detail_panel(self, pig=None) -> None:
        """Update the detail panel for the currently highlighted pig."""
        if pig is None:
            pig = self._get_selected_pig()
        panel = self.query_one("#pig-detail-panel", PigDetailPanel)
        panel.refresh_pig(pig)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update detail panel when cursor moves to a new row."""
        pig_id = UUID(str(event.row_key.value))
        pig = self.state.get_guinea_pig(pig_id)
        self._update_detail_panel(pig)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on a row - follow pig."""
        self.action_follow_pig()

    def action_go_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()

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
            self.app.pig_to_follow = pig
            self.app.pop_screen()

    def _update_header(self) -> None:
        """Update the header."""
        header = self.query_one("#pig-header", Static)
        count = self.state.pig_count
        capacity = self.state.capacity
        header.update(f"Guinea Pigs ({count}/{capacity})")
