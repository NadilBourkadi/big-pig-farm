"""Pig detail panel widget and standalone detail screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static, Footer
from rich.text import Text

from big_pig_farm.data.sprite_pixels import (
    generate_portrait,
    convert_pixels,
    render_to_rich_text,
    PALETTES,
)
from big_pig_farm.economy.market import calculate_pig_value, calculate_pig_value_breakdown
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.genetics import carrier_summary
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.needs import get_most_urgent_need
from big_pig_farm.ui.utils import format_needs_bar, format_breeding_status


class PigDetailPanel(Static):
    """Reusable widget showing detailed info about a single pig.

    Can be embedded in any screen (e.g., the pig list split view).
    Call refresh_pig() to update content for a new pig.
    """

    DEFAULT_CSS = """
    PigDetailPanel {
        padding: 0 1;
    }

    PigDetailPanel.no-pig {
        content-align: center middle;
    }
    """

    def __init__(self, state: GameState, pig: GuineaPig | None = None, **kwargs):
        self.state = state
        self._pig = pig
        super().__init__(self._build_full_content(), **kwargs)

    def refresh_pig(self, pig: GuineaPig | None) -> None:
        """Update the panel for a different pig."""
        self._pig = pig
        self.update(self._build_full_content())

    def _build_full_content(self) -> Text | str:
        """Build portrait + text content as a Rich Text object."""
        if not self._pig:
            return "[dim]Select a pig to see details[/]"

        portrait = self._build_portrait_text(self._pig)
        markup = self._build_content()

        combined = Text()
        combined.append_text(portrait)
        combined.append("\n\n")
        combined.append(Text.from_markup(markup))
        return combined

    def _build_portrait_text(self, pig: GuineaPig) -> Text:
        """Render a half-block portrait for the given pig."""
        grid = generate_portrait(
            pig.phenotype.base_color.name,
            pig.phenotype.pattern.value,
            pig.phenotype.intensity.value,
            pig.phenotype.roan.value,
            str(pig.id),
        )
        palette = PALETTES.get(pig.phenotype.base_color.name, PALETTES["BLACK"])
        converted = convert_pixels(grid, palette)
        return render_to_rich_text(converted, center_width=38)

    def _build_content(self) -> str:
        """Build all pig detail content as a markup string."""
        if not self._pig:
            return "[dim]Select a pig to see details[/]"

        pig = self._pig
        gender_str = "Male" if pig.gender == Gender.MALE else "Female"
        gender_icon = "\u2642" if pig.gender == Gender.MALE else "\u2640"
        lines = []

        # Header
        lines.append(f"[bold]{pig.name}[/] {gender_icon}  {pig.phenotype.display_name}")
        lines.append("")

        # Basic Info
        lines.append("[bold]BASIC INFO[/]")
        lines.append(f"  Age: {int(pig.age_days)} days ({pig.age_group.value})")
        lines.append(f"  Gender: {gender_str}")
        lines.append(f"  Rarity: {pig.phenotype.rarity.value.title()}")
        if pig.origin_tag:
            lines.append(f"  Origin: {pig.origin_tag}")
        breakdown = calculate_pig_value_breakdown(pig, self.state)
        lines.append(f"  Sale Value: ${breakdown['total']}")
        if breakdown["rarity_mult"] != 1.0:
            lines.append(f"    Rarity: x{breakdown['rarity_mult']:.1f}")
        if breakdown["age_mult"] != 1.0:
            lines.append(f"    Age: x{breakdown['age_mult']:.1f}")
        if breakdown["health_mult"] != 1.0:
            lines.append(f"    Health: x{breakdown['health_mult']:.2f}")
        if breakdown["grooming_mult"] != 1.0:
            lines.append(f"    Grooming: x{breakdown['grooming_mult']:.2f}")
        lines.append("")

        # Personality
        lines.append("[bold]PERSONALITY[/]")
        traits = ", ".join(t.value.title() for t in pig.personality)
        lines.append(f"  Traits: {traits}")
        lines.append("")

        # Breeding
        lines.append("[bold]BREEDING[/]")
        lock_status = "LOCKED" if pig.breeding_locked else "Unlocked"
        lines.append(f"  Lock: {lock_status}")
        lines.append(f"  Status: {format_breeding_status(pig, verbose=True)}")
        if pig.is_baby:
            mark_str = "Yes" if pig.marked_for_sale else "No"
            lines.append(f"  Auto-sell: {mark_str}")
        lines.append("")

        # Family
        lines.append("[bold]FAMILY[/]")
        mother = self._get_parent_name(pig.mother_id, pig.mother_name)
        father = self._get_parent_name(pig.father_id, pig.father_name)
        lines.append(f"  Mother: {mother}")
        lines.append(f"  Father: {father}")
        lines.append("")

        # Genetics (only with Genetics Lab)
        has_lab = bool(self.state.get_facilities_by_type(FacilityType.GENETICS_LAB))
        if has_lab:
            lines.append("[bold]GENETICS[/]")
            g = pig.genotype
            lines.append(f"  Genotype: E({g.e_locus[0]}/{g.e_locus[1]}) B({g.b_locus[0]}/{g.b_locus[1]}) S({g.s_locus[0]}/{g.s_locus[1]}) C({g.c_locus[0]}/{g.c_locus[1]}) R({g.r_locus[0]}/{g.r_locus[1]})")
            summary = carrier_summary(g)
            lines.append(f"  Carries: {summary if summary != 'None' else 'No hidden alleles'}")
            lines.append("")

        # Needs
        lines.append("[bold]NEEDS[/]")
        needs = pig.needs
        needs_data = [
            ("Hunger", needs.hunger),
            ("Thirst", needs.thirst),
            ("Energy", needs.energy),
            ("Happy", needs.happiness),
            ("Health", needs.health),
            ("Social", needs.social),
            ("Fun", 100 - needs.boredom),
        ]
        for name, val in needs_data:
            lines.append(f"  {name:8} {format_needs_bar(val)}")
        lines.append("")

        # AI State
        lines.append("[bold]AI STATE[/]")
        if pig.target_description:
            lines.append(f"  {pig.target_description}")
        else:
            lines.append(f"  {pig.behavior_state.value}")
        urgent = get_most_urgent_need(pig)
        lines.append(f"  Need: {urgent}")
        if pig.path:
            lines.append(f"  {len(pig.path)} steps away")
        lines.append("")

        # Behavior Log
        lines.append("[bold]RECENT ACTIVITY[/]")
        if pig.behavior_log:
            for entry in reversed(pig.behavior_log[-5:]):
                lines.append(f"  \u2022 {entry}")
        else:
            lines.append("  (no activity)")

        return "\n".join(lines)

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


class PigDetailScreen(Screen):
    """Standalone screen showing detailed info about a single pig.

    Kept for backwards compatibility but delegates rendering to PigDetailPanel.
    """

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

    #detail-panel-container {
        height: 1fr;
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
        yield PigDetailPanel(self.state, pig, id="detail-panel-container")
        yield Footer()

    def action_go_back(self) -> None:
        """Go back to pig list."""
        self.app.pop_screen()

    def action_follow_pig(self) -> None:
        """Follow this pig on the main screen."""
        self.app.pig_to_follow = self.pig
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
