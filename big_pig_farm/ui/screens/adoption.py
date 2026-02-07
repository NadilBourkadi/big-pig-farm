"""Adoption Center screen for purchasing new guinea pigs."""

import random
from typing import Optional

from textual.app import ComposeResult
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Static, Label, ListView, ListItem, Footer

from big_pig_farm.data.config import BLOODLINE
from big_pig_farm.data.names import generate_unique_name
from big_pig_farm.economy.currency import format_money
from big_pig_farm.economy.market import get_rarity_multiplier
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.entities.bloodlines import (
    BLOODLINES,
    pick_random_bloodline,
    generate_bloodline_pig_genotype,
)
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.breeding import register_pig_in_pigdex


# Adoption costs are higher than sale prices to prevent buy/sell exploits
ADOPTION_BASE_COST = 50  # Common pigs cost 50 (sell for 25)


def calculate_adoption_cost(pig: GuineaPig) -> int:
    """Calculate the adoption cost for a guinea pig.

    Bloodline pigs have their cost multiplied by the bloodline cost_multiplier
    (applied on top of rarity multiplier).
    """
    multiplier = get_rarity_multiplier(pig.phenotype.rarity)
    base_cost = int(ADOPTION_BASE_COST * multiplier)

    # Bloodline pigs cost more based on their bloodline
    if pig.origin_tag:
        for bloodline in BLOODLINES.values():
            if bloodline.display_name == pig.origin_tag:
                base_cost = int(base_cost * bloodline.cost_multiplier)
                break

    return base_cost


def generate_adoption_pig(existing_names: set[str], farm_tier: int = 1) -> GuineaPig:
    """Generate a random guinea pig available for adoption.

    About 50% of generated pigs are bloodline carriers (filtered by farm tier).
    """
    gender = random.choice([Gender.MALE, Gender.FEMALE])
    name = generate_unique_name(existing_names, gender=gender.value)

    # Chance to generate a bloodline carrier pig
    origin_tag = None
    genotype = None
    if random.random() < BLOODLINE.BLOODLINE_PIG_CHANCE:
        bloodline = pick_random_bloodline(farm_tier)
        if bloodline:
            genotype = generate_bloodline_pig_genotype(bloodline)
            origin_tag = bloodline.display_name

    # Create an adult pig (age 5 days) with random genetics
    pig = GuineaPig.create(
        name=name,
        gender=gender,
        genotype=genotype,
        age_days=5.0,  # Adults ready for adoption
    )
    pig.origin_tag = origin_tag
    return pig


class AdoptionPigWidget(ListItem):
    """Widget displaying a guinea pig available for adoption."""

    def __init__(self, pig: GuineaPig, cost: int, can_afford: bool):
        gender_symbol = "M" if pig.gender == Gender.MALE else "F"
        rarity = pig.phenotype.rarity.value.title()
        color = pig.phenotype.display_name
        afford_str = "" if can_afford else " (!)"
        bloodline_str = f"  [{pig.origin_tag}]" if pig.origin_tag else ""

        label = f"{pig.name:18} {gender_symbol} | {color:12} ({rarity:10}) | ${cost:>4}{afford_str}{bloodline_str}"

        super().__init__(Label(label))
        self.pig = pig
        self.cost = cost
        self.can_afford = can_afford


class AdoptionScreen(Screen):
    """Screen for adopting new guinea pigs."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("enter", "adopt", "Adopt"),
        ("r", "refresh_pigs", "Refresh"),
    ]

    DEFAULT_CSS = """
    AdoptionScreen {
        layout: vertical;
        background: $surface;
    }

    #adoption-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #adoption-content {
        height: 1fr;
        padding: 1;
    }

    #pig-list {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }

    #pig-detail {
        height: 8;
        padding: 1;
        border: solid $secondary;
        margin: 1;
    }

    #info-bar {
        height: 3;
        padding: 0 1;
    }

    .info-text {
        margin: 0 2;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._available_pigs: list[GuineaPig] = []
        self._selected_pig: Optional[GuineaPig] = None

    def compose(self) -> ComposeResult:
        """Compose the adoption screen."""
        yield Static(
            f"ADOPTION CENTER - Balance: ${format_money(self.state.money)}",
            id="adoption-header"
        )

        with Container(id="adoption-content"):
            with Horizontal(id="info-bar"):
                capacity_str = f"Farm: {self.state.pig_count}/{self.state.capacity} pigs"
                yield Static(capacity_str, classes="info-text")
                yield Static("Press R to see new pigs", classes="info-text")

            yield ListView(id="pig-list")

            yield Static("Select a pig to see details", id="pig-detail")

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self._generate_available_pigs()
        self._refresh_list()
        list_view = self.query_one("#pig-list", ListView)
        list_view.focus()

    def _generate_available_pigs(self) -> None:
        """Generate a new set of pigs available for adoption."""
        existing_names = {p.name for p in self.state.get_pigs_list()}
        # Also include names of pigs we're generating
        for pig in self._available_pigs:
            existing_names.add(pig.name)

        self._available_pigs = []
        num_pigs = random.randint(3, 5)
        farm_tier = self.state.farm.tier

        for _ in range(num_pigs):
            pig = generate_adoption_pig(existing_names, farm_tier=farm_tier)
            self._available_pigs.append(pig)
            existing_names.add(pig.name)

    def _refresh_list(self) -> None:
        """Refresh the pig list display."""
        try:
            list_view = self.query_one("#pig-list", ListView)
        except NoMatches:
            return

        list_view.clear()
        self._selected_pig = None

        for pig in self._available_pigs:
            cost = calculate_adoption_cost(pig)
            can_afford = self.state.money >= cost
            widget = AdoptionPigWidget(pig, cost, can_afford)
            list_view.append(widget)

        self._update_detail()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle pig highlight."""
        if isinstance(event.item, AdoptionPigWidget):
            self._selected_pig = event.item.pig
            self._update_detail()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle pig selection (enter key)."""
        if isinstance(event.item, AdoptionPigWidget):
            self._selected_pig = event.item.pig
            self._update_detail()
            self.action_adopt()

    def _update_detail(self) -> None:
        """Update the detail panel."""
        detail = self.query_one("#pig-detail", Static)

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

            detail.update(
                f"{pig.name} - ${cost}\n"
                f"Gender: {gender} | Color: {pig.phenotype.display_name}\n"
                f"Rarity: {rarity} | Personality: {traits}\n"
                f"Can afford: {can_afford}{bloodline_line}"
            )
        else:
            detail.update("Select a pig to see details")

    def _update_header(self) -> None:
        """Update the header with current balance."""
        header = self.query_one("#adoption-header", Static)
        header.update(f"ADOPTION CENTER - Balance: ${format_money(self.state.money)}")

    def _update_info_bar(self) -> None:
        """Update the capacity info."""
        try:
            info_bar = self.query_one("#info-bar", Horizontal)
            # Get the first Static (capacity display)
            statics = list(info_bar.query(Static))
            if statics:
                capacity_str = f"Farm: {self.state.pig_count}/{self.state.capacity} pigs"
                statics[0].update(capacity_str)
        except NoMatches:
            pass

    def action_go_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()

    def action_refresh_pigs(self) -> None:
        """Generate a new set of available pigs."""
        self._generate_available_pigs()
        self._refresh_list()
        self.notify("New pigs available!")

    def action_adopt(self) -> None:
        """Adopt the selected pig."""
        if not self._selected_pig:
            self.notify("Select a pig first!", severity="warning")
            return

        # Check capacity
        if self.state.is_at_capacity:
            self.notify("Farm is at capacity! Upgrade or sell pigs.", severity="error")
            return

        pig = self._selected_pig
        cost = calculate_adoption_cost(pig)

        # Check affordability
        if self.state.money < cost:
            self.notify("Not enough money!", severity="error")
            return

        # Find a valid position for the new pig
        position = self._find_spawn_position()
        if position is None:
            self.notify("No space for new pig!", severity="error")
            return

        # Complete the adoption
        pig.position = position
        self.state.spend_money(cost)
        self.state.add_guinea_pig(pig)

        # Register in pigdex
        register_pig_in_pigdex(self.state, pig)

        # Log the event
        self.state.log_event(
            f"Adopted {pig.name} ({pig.phenotype.display_name}) for {cost} Squeaks",
            event_type="adoption",
        )

        self.notify(f"Welcome home, {pig.name}!")

        # Remove from available list and refresh
        self._available_pigs.remove(pig)
        self._selected_pig = None
        self._refresh_list()
        self._update_header()
        self._update_info_bar()

    def _find_spawn_position(self) -> Optional[Position]:
        """Find a valid spawn position for the adopted pig."""
        farm = self.state.farm

        # Try to find an open walkable position
        for _ in range(100):  # Max attempts
            x = random.randint(2, farm.width - 3)
            y = random.randint(2, farm.height - 3)

            if farm.is_walkable(x, y):
                # Check not too close to facilities
                cell = farm.get_cell(x, y)
                if cell and not cell.facility_id:
                    return Position(x=float(x), y=float(y))

        return None
