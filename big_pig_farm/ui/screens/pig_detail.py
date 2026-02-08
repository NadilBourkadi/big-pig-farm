"""Detailed view screen for a single guinea pig."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static, Footer

from big_pig_farm.economy.market import calculate_pig_value
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.genetics import carrier_summary
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.needs import get_most_urgent_need
from big_pig_farm.ui.utils import format_needs_bar


class PigDetailScreen(Screen):
    """Screen showing detailed info about a single pig."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("f", "follow_pig", "Follow"),
        ("l", "toggle_lock", "Lock"),
        ("m", "toggle_mark_sale", "Mark"),
    ]

    DEFAULT_CSS = """
    PigDetailScreen {
        layout: vertical;
        background: $surface;
    }

    #detail-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #detail-content {
        height: 1fr;
        padding: 0 1;
    }

    .info-section {
        border: solid $secondary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    .section-title {
        text-style: bold;
    }
    """

    def __init__(self, state: GameState, pig: GuineaPig, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self.pig = pig

    def compose(self) -> ComposeResult:
        """Compose the detail screen."""
        pig = self.pig
        gender = "Male" if pig.gender == Gender.MALE else "Female"

        yield Static(f"{pig.name} - {pig.phenotype.display_name} {gender}", id="detail-header")

        with VerticalScroll(id="detail-content"):
            # Basic Info Section
            with Vertical(classes="info-section"):
                yield Static("BASIC INFO", classes="section-title")
                yield Static(f"  Age: {int(pig.age_days)} days ({pig.age_group.value})")
                yield Static(f"  Gender: {gender}")
                yield Static(f"  Color: {pig.phenotype.display_name}")
                yield Static(f"  Rarity: {pig.phenotype.rarity.value.title()}")
                if pig.origin_tag:
                    yield Static(f"  Origin: {pig.origin_tag}")
                value = calculate_pig_value(pig, self.state)
                yield Static(f"  Sale Value: ${value}")

            # Personality Section
            with Vertical(classes="info-section"):
                yield Static("PERSONALITY", classes="section-title")
                traits = ", ".join(t.value.title() for t in pig.personality)
                yield Static(f"  Traits: {traits}")

            # Breeding Section
            with Vertical(classes="info-section"):
                yield Static("BREEDING", classes="section-title")
                lock_status = "LOCKED" if pig.breeding_locked else "Unlocked"
                yield Static(f"  Breeding Lock: {lock_status} (press L to toggle)")

                if pig.is_pregnant:
                    days_left = 3 - pig.pregnancy_days
                    yield Static(f"  Status: Pregnant ({days_left:.1f} days until birth)")
                elif pig.can_breed:
                    yield Static(f"  Status: Ready to breed")
                elif not pig.is_adult:
                    yield Static(f"  Status: Too young (must be 3+ days)")
                    if pig.marked_for_sale:
                        yield Static(f"  Auto-sell: Will be sold at adulthood (press M to cancel)")
                    else:
                        yield Static(f"  Auto-sell: Off (press M to mark)")
                else:
                    yield Static(f"  Status: Not ready (needs higher happiness)")

            # Family Section
            with Vertical(classes="info-section"):
                yield Static("FAMILY", classes="section-title")
                mother = self._get_parent_name(pig.mother_id, pig.mother_name)
                father = self._get_parent_name(pig.father_id, pig.father_name)
                yield Static(f"  Mother: {mother}")
                yield Static(f"  Father: {father}")

            # Genetics Section (only with Genetics Lab)
            has_lab = bool(self.state.get_facilities_by_type(FacilityType.GENETICS_LAB))
            if has_lab:
                with Vertical(classes="info-section"):
                    yield Static("GENETICS", classes="section-title")
                    yield Static(self._format_genetics())

            # Needs Section
            with Vertical(classes="info-section"):
                yield Static("NEEDS", classes="section-title")
                yield Static(self._format_needs())

            # Debug/AI Section
            with Vertical(classes="info-section"):
                yield Static("AI STATE", classes="section-title")
                yield Static(self._format_ai_state())

        yield Footer()

    def _get_parent_name(self, parent_id, stored_name: str = None) -> str:
        """Get parent name or 'Unknown'."""
        if parent_id is None:
            return "Unknown (adopted/starter)"
        parent = self.state.get_guinea_pig(parent_id)
        if parent:
            return parent.name
        if stored_name:
            return f"{stored_name} (sold)"
        return "Unknown (no longer on farm)"

    def _format_genetics(self) -> str:
        """Format genotype and carrier info."""
        g = self.pig.genotype
        lines = []

        # Full genotype notation
        lines.append(f"  Genotype: E({g.e_locus[0]}/{g.e_locus[1]}) B({g.b_locus[0]}/{g.b_locus[1]}) S({g.s_locus[0]}/{g.s_locus[1]}) C({g.c_locus[0]}/{g.c_locus[1]}) R({g.r_locus[0]}/{g.r_locus[1]})")

        # Carrier summary
        summary = carrier_summary(g)
        lines.append(f"  Carries: {summary if summary != 'None' else 'No hidden alleles'}")

        return "\n".join(lines)

    def _format_needs(self) -> str:
        """Format all needs as text with bars."""
        needs = self.pig.needs
        lines = []

        needs_data = [
            ("Hunger", needs.hunger),
            ("Thirst", needs.thirst),
            ("Energy", needs.energy),
            ("Happiness", needs.happiness),
            ("Health", needs.health),
            ("Social", needs.social),
            ("Fun", 100 - needs.boredom),
        ]

        for name, value in needs_data:
            lines.append(f"  {name:10} {format_needs_bar(value)}")

        return "\n".join(lines)

    def _format_ai_state(self) -> str:
        """Format AI/behavior debug info."""
        pig = self.pig
        lines = []

        # Current behavior
        lines.append(f"  Behavior: {pig.behavior_state.value}")

        # Position
        pos = pig.position
        lines.append(f"  Position: ({pos.x:.1f}, {pos.y:.1f})")

        # Target
        if pig.target_position:
            target = pig.target_position
            lines.append(f"  Target: ({target.x:.1f}, {target.y:.1f})")
        else:
            lines.append(f"  Target: None")

        # Path info
        if pig.path:
            lines.append(f"  Path: {len(pig.path)} steps remaining")
        else:
            lines.append(f"  Path: None")

        # Most urgent need
        urgent = get_most_urgent_need(pig)
        lines.append(f"  Urgent need: {urgent}")

        # Behavior log (recent entries)
        if pig.behavior_log:
            lines.append("")
            lines.append("  Recent activity:")
            # Show last 5 entries, newest first
            for entry in reversed(pig.behavior_log[-5:]):
                lines.append(f"    • {entry}")

        return "\n".join(lines)

    def action_go_back(self) -> None:
        """Go back to pig list."""
        self.app.pop_screen()

    def action_follow_pig(self) -> None:
        """Follow this pig on the main screen."""
        # Store pig to follow and pop back to main screen
        self.app.pig_to_follow = self.pig
        # Pop back to main screen (may be multiple screens deep)
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()

    def action_toggle_lock(self) -> None:
        """Toggle breeding lock."""
        self.pig.breeding_locked = not self.pig.breeding_locked
        status = "locked" if self.pig.breeding_locked else "unlocked"
        self.notify(f"Breeding {status}")

    def action_toggle_mark_sale(self) -> None:
        """Toggle auto-sell mark on this pig."""
        if not self.pig.is_baby:
            self.notify("Only baby pigs can be marked for auto-sell", severity="warning")
            return
        self.pig.marked_for_sale = not self.pig.marked_for_sale
        status = "marked for auto-sell" if self.pig.marked_for_sale else "unmarked"
        self.notify(f"{self.pig.name} {status}")
