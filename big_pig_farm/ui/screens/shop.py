"""Shop screen for purchasing facilities, items, and adopting pigs."""

import random
from typing import Optional

from textual.app import ComposeResult
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button, Label, ListView, ListItem, Footer
from textual.reactive import reactive

from big_pig_farm.economy.shop import (
    get_shop_items,
    purchase_item,
    get_farm_upgrade_info,
    get_room_total_cost,
    purchase_new_room,
    ShopCategory,
    ShopItem,
)
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.economy.currency import format_currency
from big_pig_farm.entities.facilities import FACILITY_INFO
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.entities.bloodlines import BLOODLINES
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.breeding import register_pig_in_pigdex
from big_pig_farm.ui.screens.adoption import calculate_adoption_cost, generate_adoption_pig
from big_pig_farm.ui.utils import format_facility_bonuses


class ShopItemWidget(ListItem):
    """Widget representing a shop item."""

    def __init__(self, item: ShopItem, can_afford: bool):
        # Build the display string
        cost_str = format_currency(item.cost)
        lock_str = f" [Tier {item.required_tier}]" if not item.unlocked else ""
        afford_str = "" if can_afford else " (!)"
        label = f"{item.name:20} {cost_str:>8}{lock_str}{afford_str}"

        super().__init__(Label(label))
        self.item = item
        self.can_afford = can_afford


class AdoptionPigWidget(ListItem):
    """Widget displaying a guinea pig available for adoption."""

    def __init__(self, pig: GuineaPig, cost: int, can_afford: bool):
        gender_symbol = "M" if pig.gender == Gender.MALE else "F"
        rarity = pig.phenotype.rarity.value.title()
        color = pig.phenotype.display_name
        afford_str = "" if can_afford else " (!)"
        bloodline_str = f"  [{pig.origin_tag}]" if pig.origin_tag else ""

        label = f"{pig.name:18} {gender_symbol} | {color:12} ({rarity:10}) | {format_currency(cost):>8}{afford_str}{bloodline_str}"

        super().__init__(Label(label))
        self.pig = pig
        self.cost = cost
        self.can_afford = can_afford


class ShopScreen(Screen):
    """Screen for the in-game shop and adoption center."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", None),
        ("f", "category_facilities", "Facilities"),
        ("d", "category_food", "Food"),
        ("u", "category_upgrades", "Upgrades"),
        ("a", "category_adoption", "Adopt"),
        ("r", "refresh_adoption", "Refresh"),
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
        height: 8;
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
        self._available_pigs: list[GuineaPig] = []
        self._selected_pig: Optional[GuineaPig] = None

    def compose(self) -> ComposeResult:
        """Compose the shop screen."""
        yield Static(f"SHOP - Balance: {format_currency(self.state.money)}", id="shop-header")

        with Container(id="shop-content"):
            with Horizontal(id="category-bar"):
                yield Button("Facilities [F]", id="cat-facilities", classes="category-btn")
                yield Button("Food [D]", id="cat-food", classes="category-btn")
                yield Button("Upgrades [U]", id="cat-upgrades", classes="category-btn")
                yield Button("Adopt [A]", id="cat-adoption", classes="category-btn")

            yield ListView(id="item-list")

            yield Static("Select an item to see details", id="item-detail")

        yield Footer()

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Show refresh binding only in adoption category."""
        if action == "refresh_adoption":
            return self.current_category == ShopCategory.ADOPTION
        return True

    def on_mount(self) -> None:
        """Handle mount event."""
        self._refresh_items()
        list_view = self.query_one("#item-list", ListView)
        list_view.focus()

    def _refresh_items(self) -> None:
        """Refresh the item list."""
        try:
            list_view = self.query_one("#item-list", ListView)
        except NoMatches:
            return

        list_view.clear()
        self._is_upgrade_selected = False
        self._selected_pig = None

        if self.current_category == ShopCategory.ADOPTION:
            if not self._available_pigs:
                self._generate_available_pigs()
            for pig in self._available_pigs:
                cost = calculate_adoption_cost(pig)
                can_afford = self.state.money >= cost
                list_view.append(AdoptionPigWidget(pig, cost, can_afford))
        elif self.current_category == ShopCategory.UPGRADES:
            upgrade_info = get_farm_upgrade_info(self.state)
            if upgrade_info:
                label = f"Add New Room ({upgrade_info['name']})  Base: {format_currency(upgrade_info['cost'])}"
                list_view.append(ListItem(Label(label), id="farm-upgrade"))
                self._is_upgrade_selected = True
            else:
                list_view.append(ListItem(Label("All rooms built!")))
        else:
            items = get_shop_items(self.current_category, self.state.farm.tier)
            for item in items:
                can_afford = self.state.money >= item.cost
                widget = ShopItemWidget(item, can_afford)
                list_view.append(widget)

    def _generate_available_pigs(self) -> None:
        """Generate a new set of pigs available for adoption."""
        existing_names = {p.name for p in self.state.get_pigs_list()}
        for pig in self._available_pigs:
            existing_names.add(pig.name)

        self._available_pigs = []
        num_pigs = random.randint(3, 5)
        farm_tier = self.state.farm.tier

        for _ in range(num_pigs):
            pig = generate_adoption_pig(existing_names, farm_tier=farm_tier)
            self._available_pigs.append(pig)
            existing_names.add(pig.name)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle item highlight (when navigating with arrows)."""
        if isinstance(event.item, AdoptionPigWidget):
            self._selected_pig = event.item.pig
            self.selected_item = None
            self._is_upgrade_selected = False
            self._update_detail()
        elif isinstance(event.item, ShopItemWidget):
            self.selected_item = event.item.item
            self._selected_pig = None
            self._is_upgrade_selected = False
            self._update_detail()
        elif self.current_category == ShopCategory.UPGRADES:
            self.selected_item = None
            self._selected_pig = None
            self._is_upgrade_selected = True
            self._update_detail()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection (when pressing enter)."""
        if isinstance(event.item, AdoptionPigWidget):
            self._selected_pig = event.item.pig
            self._update_detail()
        elif isinstance(event.item, ShopItemWidget):
            self.selected_item = event.item.item
            self._update_detail()
        self.action_purchase()

    def _update_detail(self) -> None:
        """Update the detail panel."""
        detail = self.query_one("#item-detail", Static)

        if self._selected_pig:
            pig = self._selected_pig
            cost = calculate_adoption_cost(pig)
            can_afford = "Yes" if self.state.money >= cost else "No"
            gender = "Male" if pig.gender == Gender.MALE else "Female"
            traits = ", ".join(t.value.title() for t in pig.personality)
            rarity = pig.phenotype.rarity.value.title()
            bloodline_line = ""
            if pig.origin_tag:
                for bloodline in BLOODLINES.values():
                    if bloodline.display_name == pig.origin_tag:
                        bloodline_line = f"\nBloodline: {pig.origin_tag} - {bloodline.description}"
                        break

            capacity_str = f"Farm: {self.state.pig_count}/{self.state.capacity} pigs"
            detail.update(
                f"{pig.name} - {format_currency(cost)}\n"
                f"Gender: {gender} | Color: {pig.phenotype.display_name}\n"
                f"Rarity: {rarity} | Personality: {traits}\n"
                f"Can afford: {can_afford} | {capacity_str}{bloodline_line}"
            )
        elif self._is_upgrade_selected:
            upgrade_info = get_farm_upgrade_info(self.state)
            if upgrade_info:
                rooms = len(self.state.farm.areas)
                detail.update(
                    f"Add New Room — {upgrade_info['name']}\n"
                    f"Base cost: {format_currency(upgrade_info['cost'])} + biome cost\n"
                    f"Size: {upgrade_info['width']}x{upgrade_info['height']} | +{upgrade_info['capacity']} pig capacity\n"
                    f"Rooms: {rooms} | Press Enter to choose a biome"
                )
            else:
                detail.update("All rooms have been built!")
        elif self.selected_item:
            item = self.selected_item
            can_afford = "Yes" if self.state.money >= item.cost else "No"
            unlocked = "Yes" if item.unlocked else f"Requires Tier {item.required_tier}"

            lines = [
                f"{item.name} - {format_currency(item.cost)}",
                f"{item.description}",
                f"Can afford: {can_afford} | Available: {unlocked}",
            ]
            if item.facility_type:
                bonuses = format_facility_bonuses(item.facility_type)
                if bonuses:
                    lines.append(f"Bonuses: {bonuses}")
            detail.update("\n".join(lines))
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
        elif event.button.id == "cat-adoption":
            self.action_category_adoption()

    def action_category_facilities(self) -> None:
        """Switch to facilities category."""
        self.current_category = ShopCategory.FACILITIES
        self._refresh_items()
        self._refresh_footer()
        self.notify("Facilities")
        self.query_one("#item-list", ListView).focus()

    def action_category_food(self) -> None:
        """Switch to food category."""
        self.current_category = ShopCategory.FOOD
        self._refresh_items()
        self._refresh_footer()
        self.notify("Food & Supplies")
        self.query_one("#item-list", ListView).focus()

    def action_category_upgrades(self) -> None:
        """Switch to upgrades category."""
        self.current_category = ShopCategory.UPGRADES
        self._refresh_items()
        self._refresh_footer()
        self.notify("Farm Upgrades")
        self.query_one("#item-list", ListView).focus()

    def action_category_adoption(self) -> None:
        """Switch to adoption category."""
        self.current_category = ShopCategory.ADOPTION
        self._refresh_items()
        self._refresh_footer()
        self.notify("Adoption Center")
        self.query_one("#item-list", ListView).focus()

    def action_cycle_category(self) -> None:
        """Cycle through categories."""
        cycle = [
            ShopCategory.FACILITIES,
            ShopCategory.FOOD,
            ShopCategory.UPGRADES,
            ShopCategory.ADOPTION,
        ]
        idx = cycle.index(self.current_category)
        next_cat = cycle[(idx + 1) % len(cycle)]
        getattr(self, f"action_category_{next_cat.value}")()

    def action_refresh_adoption(self) -> None:
        """Generate a new set of available pigs."""
        if self.current_category != ShopCategory.ADOPTION:
            return
        self._available_pigs = []
        self._generate_available_pigs()
        self._refresh_items()
        self.notify("New pigs available!")

    def action_go_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()

    def action_purchase(self) -> None:
        """Attempt to purchase selected item or adopt selected pig."""
        # Handle adoption
        if self.current_category == ShopCategory.ADOPTION:
            self._adopt_pig()
            return

        # Handle room addition — open biome selection
        if self._is_upgrade_selected:
            upgrade_info = get_farm_upgrade_info(self.state)
            if not upgrade_info:
                self.notify("All rooms built!", severity="warning")
                return
            from big_pig_farm.ui.screens.biome_select import BiomeSelectScreen
            self.app.push_screen(
                BiomeSelectScreen(farm_tier=self.state.farm.tier),
                callback=self._on_biome_selected,
            )
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

    def _adopt_pig(self) -> None:
        """Adopt the selected pig."""
        if not self._selected_pig:
            self.notify("Select a pig first!", severity="warning")
            return

        if self.state.is_at_capacity:
            self.notify("Farm is at capacity! Upgrade or sell pigs.", severity="error")
            return

        pig = self._selected_pig
        cost = calculate_adoption_cost(pig)

        if self.state.money < cost:
            self.notify("Not enough money!", severity="error")
            return

        position = self._find_spawn_position()
        if position is None:
            self.notify("No space for new pig!", severity="error")
            return

        pig.position = Position(x=float(position[0]), y=float(position[1]))
        self.state.spend_money(cost)
        self.state.add_guinea_pig(pig)

        register_pig_in_pigdex(self.state, pig)

        self.state.log_event(
            f"Adopted {pig.name} ({pig.phenotype.display_name}) for {cost} Squeaks",
            event_type="adoption",
        )

        self.notify(f"Welcome home, {pig.name}!")

        self._available_pigs.remove(pig)
        self._selected_pig = None
        self._refresh_items()
        self._update_header()

    def _on_biome_selected(self, biome: Optional[BiomeType]) -> None:
        """Callback when biome is selected from BiomeSelectScreen."""
        if biome is None:
            return  # Cancelled

        total_cost = get_room_total_cost(self.state, biome)
        if self.state.money < total_cost:
            self.notify(f"Need {format_currency(total_cost)}!", severity="error")
            return

        if purchase_new_room(self.state, biome):
            from big_pig_farm.entities.biomes import BIOMES
            biome_name = BIOMES[biome].display_name
            self.notify(f"Built new {biome_name} room!")
            self._refresh_items()
            self._update_header()
            self._update_detail()
        else:
            self.notify("Could not add room!", severity="error")

    def _find_spawn_position(self) -> Optional[tuple[int, int]]:
        """Find a valid spawn position for an adopted pig."""
        farm = self.state.farm

        for _ in range(100):
            x = random.randint(2, farm.width - 3)
            y = random.randint(2, farm.height - 3)

            if farm.is_walkable(x, y):
                cell = farm.get_cell(x, y)
                if cell and not cell.facility_id:
                    return (x, y)

        return None

    def _find_placement_position(self, item: ShopItem) -> Optional[tuple[int, int]]:
        """Find a valid position to place a facility."""
        if not item.facility_type:
            return None

        info = FACILITY_INFO[item.facility_type]
        width = info.size.width
        height = info.size.height

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
        header.update(f"SHOP - Balance: {format_currency(self.state.money)}")

    def _refresh_footer(self) -> None:
        """Refresh footer to reflect context-sensitive bindings."""
        self.set_focus(self.focused)
