"""Shop screen for purchasing facilities and items."""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button, Label, ListView, ListItem, Footer
from textual.reactive import reactive

from big_pig_farm.economy.shop import (
    get_shop_items,
    purchase_item,
    get_farm_upgrade_info,
    purchase_farm_upgrade,
    ShopCategory,
    ShopItem,
)
from big_pig_farm.economy.currency import format_money
from big_pig_farm.entities.facilities import FACILITY_INFO
from big_pig_farm.game.state import GameState


class ShopItemWidget(ListItem):
    """Widget representing a shop item."""

    def __init__(self, item: ShopItem, can_afford: bool):
        # Build the display string
        cost_str = f"${item.cost}"
        lock_str = f" [Tier {item.required_tier}]" if not item.unlocked else ""
        afford_str = "" if can_afford else " (!)"
        label = f"{item.name:20} {cost_str:>8}{lock_str}{afford_str}"

        super().__init__(Label(label))
        self.item = item
        self.can_afford = can_afford


class ShopScreen(Screen):
    """Screen for the in-game shop."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("f", "category_facilities", "Facilities"),
        ("d", "category_food", "Food"),
        ("u", "category_upgrades", "Upgrades"),
        ("tab", "cycle_category", "Switch"),
        ("enter", "purchase", "Buy"),
    ]

    DEFAULT_CSS = """
    ShopScreen {
        layout: vertical;
        background: $surface;
    }

    #shop-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #shop-content {
        height: 1fr;
        padding: 1;
    }

    #category-bar {
        height: 3;
        padding: 0 1;
    }

    #item-list {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }

    #item-detail {
        height: 7;
        padding: 1;
        border: solid $secondary;
        margin: 1;
    }

    .item-name {
        width: 20;
    }

    .item-cost {
        width: 10;
        text-align: right;
    }

    .item-locked {
        color: $error;
        margin-left: 2;
    }

    .category-btn {
        margin: 0 1;
    }
    """

    current_category: reactive[ShopCategory] = reactive(ShopCategory.FACILITIES)
    selected_item: reactive[Optional[ShopItem]] = reactive(None)

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._is_upgrade_selected = False

    def compose(self) -> ComposeResult:
        """Compose the shop screen."""
        yield Static(f"SHOP - Balance: ${format_money(self.state.money)}", id="shop-header")

        with Container(id="shop-content"):
            with Horizontal(id="category-bar"):
                yield Button("Facilities [F]", id="cat-facilities", classes="category-btn")
                yield Button("Food [D]", id="cat-food", classes="category-btn")
                yield Button("Upgrades [U]", id="cat-upgrades", classes="category-btn")

            yield ListView(id="item-list")

            yield Static("Select an item to see details", id="item-detail")

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self._refresh_items()
        # Focus the list view so arrow keys and enter work
        list_view = self.query_one("#item-list", ListView)
        list_view.focus()

    def _refresh_items(self) -> None:
        """Refresh the item list."""
        try:
            list_view = self.query_one("#item-list", ListView)
        except Exception:
            return

        list_view.clear()
        self._is_upgrade_selected = False

        if self.current_category == ShopCategory.UPGRADES:
            # Show farm upgrade option
            upgrade_info = get_farm_upgrade_info(self.state)
            if upgrade_info:
                can_afford = self.state.money >= upgrade_info["cost"]
                label = f"Expand to {upgrade_info['name']:15} ${upgrade_info['cost']:>6}"
                if not can_afford:
                    label += " (!)"
                list_view.append(ListItem(Label(label), id="farm-upgrade"))
                self._is_upgrade_selected = True
            else:
                list_view.append(ListItem(Label("Farm is at maximum size!")))
        else:
            items = get_shop_items(self.current_category, self.state.farm.tier)
            for item in items:
                can_afford = self.state.money >= item.cost
                widget = ShopItemWidget(item, can_afford)
                list_view.append(widget)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle item highlight (when navigating with arrows)."""
        if isinstance(event.item, ShopItemWidget):
            self.selected_item = event.item.item
            self._is_upgrade_selected = False
            self._update_detail()
        elif self.current_category == ShopCategory.UPGRADES:
            self.selected_item = None
            self._is_upgrade_selected = True
            self._update_detail()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection (when pressing enter)."""
        if isinstance(event.item, ShopItemWidget):
            self.selected_item = event.item.item
            self._update_detail()
        # Trigger purchase on enter for any item (including farm upgrade)
        self.action_purchase()

    def _update_detail(self) -> None:
        """Update the detail panel."""
        detail = self.query_one("#item-detail", Static)

        if self._is_upgrade_selected:
            upgrade_info = get_farm_upgrade_info(self.state)
            if upgrade_info:
                can_afford = "Yes" if self.state.money >= upgrade_info["cost"] else "No"
                current_tier = self.state.farm.tier
                detail.update(
                    f"Upgrade to {upgrade_info['name']} - ${upgrade_info['cost']}\n"
                    f"Size: {upgrade_info['width']}x{upgrade_info['height']} | Capacity: {upgrade_info['capacity']} pigs\n"
                    f"Can afford: {can_afford} | Current tier: {current_tier}"
                )
            else:
                detail.update("Your farm is at maximum size!")
        elif self.selected_item:
            item = self.selected_item
            can_afford = "Yes" if self.state.money >= item.cost else "No"
            unlocked = "Yes" if item.unlocked else f"Requires Tier {item.required_tier}"

            detail.update(
                f"{item.name} - ${item.cost}\n"
                f"{item.description}\n"
                f"Can afford: {can_afford} | Available: {unlocked}"
            )
        else:
            detail.update("Select an item to see details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cat-facilities":
            self.action_category_facilities()
        elif event.button.id == "cat-food":
            self.action_category_food()
        elif event.button.id == "cat-upgrades":
            self.action_category_upgrades()

    def action_category_facilities(self) -> None:
        """Switch to facilities category."""
        self.current_category = ShopCategory.FACILITIES
        self._refresh_items()
        self.notify("Facilities")
        self.query_one("#item-list", ListView).focus()

    def action_category_food(self) -> None:
        """Switch to food category."""
        self.current_category = ShopCategory.FOOD
        self._refresh_items()
        self.notify("Food & Supplies")
        self.query_one("#item-list", ListView).focus()

    def action_category_upgrades(self) -> None:
        """Switch to upgrades category."""
        self.current_category = ShopCategory.UPGRADES
        self._refresh_items()
        self.notify("Farm Upgrades")
        self.query_one("#item-list", ListView).focus()

    def action_cycle_category(self) -> None:
        """Cycle through categories."""
        if self.current_category == ShopCategory.FACILITIES:
            self.action_category_food()
        elif self.current_category == ShopCategory.FOOD:
            self.action_category_upgrades()
        else:
            self.action_category_facilities()

    def action_go_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()

    def action_purchase(self) -> None:
        """Attempt to purchase selected item."""
        # Handle farm upgrade purchase
        if self._is_upgrade_selected:
            upgrade_info = get_farm_upgrade_info(self.state)
            if not upgrade_info:
                self.notify("Farm is at maximum size!", severity="warning")
                return
            if self.state.money < upgrade_info["cost"]:
                self.notify("Not enough money!", severity="error")
                return
            if purchase_farm_upgrade(self.state):
                self.notify(f"Upgraded to {upgrade_info['name']}!", severity="information")
                self._refresh_items()
                self._update_header()
                self._update_detail()
            return

        if not self.selected_item:
            return

        item = self.selected_item

        if not item.unlocked:
            self.notify("Item not unlocked yet!", severity="error")
            return

        if self.state.money < item.cost:
            self.notify("Not enough money!", severity="error")
            return

        # For facilities, need to find a placement position
        if item.facility_type:
            pos = self._find_placement_position(item)
            if pos is None:
                self.notify("No space for this facility!", severity="error")
                return

            if purchase_item(self.state, item, pos):
                self.notify(f"Purchased {item.name}!", severity="information")
                self._refresh_items()
                self._update_header()
        else:
            if purchase_item(self.state, item, None):
                self.notify(f"Purchased {item.name}!", severity="information")
                self._refresh_items()
                self._update_header()

    def _find_placement_position(self, item: ShopItem) -> Optional[tuple[int, int]]:
        """Find a valid position to place a facility."""
        if not item.facility_type:
            return None

        info = FACILITY_INFO[item.facility_type]
        size = info["size"]
        width = size.width
        height = size.height

        farm = self.state.farm

        # Try to find an open position
        for y in range(2, farm.height - height - 1):
            for x in range(2, farm.width - width - 1):
                can_place = True
                for dy in range(height):
                    for dx in range(width):
                        if not farm.is_walkable(x + dx, y + dy):
                            can_place = False
                            break
                        cell = farm.get_cell(x + dx, y + dy)
                        if cell and cell.facility_id:
                            can_place = False
                            break
                    if not can_place:
                        break

                if can_place:
                    return (x, y)

        return None

    def _update_header(self) -> None:
        """Update the header with current balance."""
        header = self.query_one("#shop-header", Static)
        header.update(f"SHOP - Balance: ${format_money(self.state.money)}")
