"""Breeding screen for viewing breeding pairs and genetics."""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label, Footer
from textual.reactive import reactive

from big_pig_farm.entities.guinea_pig import GuineaPig, Gender
from big_pig_farm.entities.genetics import predict_offspring_probabilities, Genotype
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState


class PigListItem(ListItem):
    """List item for a guinea pig."""

    def __init__(self, pig: GuineaPig):
        status = ""
        if pig.breeding_locked:
            status = " [LOCKED]"
        elif pig.is_pregnant:
            status = " [Pregnant]"
        elif not pig.can_breed:
            status = " [Can't breed]"

        label = f"{pig.name} - {pig.phenotype.display_name}{status}"
        super().__init__(Label(label))
        self.pig = pig


class BreedingScreen(Screen):
    """Screen for breeding planning and genetics viewing."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
        ("tab", "switch_panel", "Switch"),
        ("m", "focus_males", "Males"),
        ("f", "focus_females", "Females"),
    ]

    DEFAULT_CSS = """
    BreedingScreen {
        layout: vertical;
        background: $surface;
    }

    #breeding-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #breeding-content {
        height: 1fr;
        padding: 1;
    }

    #parent-selection {
        height: 12;
        layout: horizontal;
    }

    .parent-panel {
        width: 1fr;
        margin: 0 1;
    }

    .panel-title {
        height: 1;
        text-style: bold;
        margin-bottom: 1;
    }

    .parent-list {
        height: 8;
        border: solid $secondary;
    }

    .parent-list:focus {
        border: solid $primary;
    }

    #selected-info {
        height: 5;
        layout: horizontal;
        margin: 1;
    }

    .info-panel {
        width: 1fr;
        border: solid $secondary;
        padding: 0 1;
        margin: 0 1;
    }

    #prediction-panel {
        height: 1fr;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    .help-text {
        text-style: italic;
        color: $text-muted;
    }
    """

    selected_male: reactive[Optional[GuineaPig]] = reactive(None)
    selected_female: reactive[Optional[GuineaPig]] = reactive(None)

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._active_panel = "male"  # Track which panel is active

    def compose(self) -> ComposeResult:
        """Compose the breeding screen."""
        yield Static("Breeding Planner - Select parents to predict offspring", id="breeding-header")

        with Container(id="breeding-content"):
            with Horizontal(id="parent-selection"):
                with Vertical(classes="parent-panel"):
                    yield Static("Males [M]", classes="panel-title")
                    yield ListView(id="male-list", classes="parent-list")

                with Vertical(classes="parent-panel"):
                    yield Static("Females [F]", classes="panel-title")
                    yield ListView(id="female-list", classes="parent-list")

            with Horizontal(id="selected-info"):
                yield Static("No male selected", id="male-info", classes="info-panel")
                yield Static("No female selected", id="female-info", classes="info-panel")

            yield Static(
                "Select a male and female to see offspring predictions\n\n"
                "Use Tab to switch between lists, or M/F to jump directly",
                id="prediction-panel"
            )

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self._populate_lists()
        # Focus the male list by default
        male_list = self.query_one("#male-list", ListView)
        male_list.focus()

    def _populate_lists(self) -> None:
        """Populate the male and female lists."""
        male_list = self.query_one("#male-list", ListView)
        female_list = self.query_one("#female-list", ListView)

        male_list.clear()
        female_list.clear()

        pigs = self.state.get_pigs_list()

        # Add adult males
        males = [p for p in pigs if p.gender == Gender.MALE and p.is_adult]
        for pig in males:
            male_list.append(PigListItem(pig))

        # Add adult females (including pregnant ones, but marked)
        females = [p for p in pigs if p.gender == Gender.FEMALE and p.is_adult]
        for pig in females:
            female_list.append(PigListItem(pig))

        # Show message if no pigs available
        if not males:
            male_list.append(ListItem(Label("No adult males")))
        if not females:
            female_list.append(ListItem(Label("No adult females")))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle pig highlight in either list."""
        if not isinstance(event.item, PigListItem):
            return

        pig = event.item.pig
        list_id = event.list_view.id

        if list_id == "male-list":
            self.selected_male = pig
            self._update_male_info()
        elif list_id == "female-list":
            self.selected_female = pig
            self._update_female_info()

        self._update_predictions()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle enter press - switch to other panel after selection."""
        if not isinstance(event.item, PigListItem):
            return

        list_id = event.list_view.id

        # After selecting in one list, switch to the other
        if list_id == "male-list":
            self.action_focus_females()
        elif list_id == "female-list":
            self.action_focus_males()

    def _has_genetics_lab(self) -> bool:
        """Check if player has a Genetics Lab."""
        return bool(self.state.get_facilities_by_type(FacilityType.GENETICS_LAB))

    @staticmethod
    def _carrier_summary(genotype: Genotype) -> str:
        """Get a short carrier summary for a genotype."""
        carriers = []
        g = genotype
        if g.e_locus[0] != g.e_locus[1] and "e" in g.e_locus:
            carriers.append("E/e")
        if g.b_locus[0] != g.b_locus[1] and "b" in g.b_locus:
            carriers.append("B/b")
        if g.s_locus[0] != g.s_locus[1] and "s" in g.s_locus:
            carriers.append("S/s")
        if g.c_locus[0] != g.c_locus[1] and "ch" in g.c_locus:
            carriers.append("C/ch")
        if "R" in g.r_locus and "r" in g.r_locus:
            carriers.append("R/r")
        return ", ".join(carriers) if carriers else "None"

    def _update_male_info(self) -> None:
        """Update male parent info display."""
        info = self.query_one("#male-info", Static)
        if self.selected_male:
            pig = self.selected_male
            can_breed = "Yes" if pig.can_breed else "No"
            lines = [
                f"Male: {pig.name}",
                f"Color: {pig.phenotype.display_name} | Rarity: {pig.phenotype.rarity.value}",
                f"Can breed: {can_breed}",
            ]
            if self._has_genetics_lab():
                lines.append(f"Carriers: {self._carrier_summary(pig.genotype)}")
            info.update("\n".join(lines))
        else:
            info.update("No male selected")

    def _update_female_info(self) -> None:
        """Update female parent info display."""
        info = self.query_one("#female-info", Static)
        if self.selected_female:
            pig = self.selected_female
            status = ""
            if pig.is_pregnant:
                days_left = 3 - pig.pregnancy_days
                status = f" | Pregnant ({days_left:.1f} days left)"
            can_breed = "Yes" if pig.can_breed else "No"
            lines = [
                f"Female: {pig.name}",
                f"Color: {pig.phenotype.display_name} | Rarity: {pig.phenotype.rarity.value}",
                f"Can breed: {can_breed}{status}",
            ]
            if self._has_genetics_lab():
                lines.append(f"Carriers: {self._carrier_summary(pig.genotype)}")
            info.update("\n".join(lines))
        else:
            info.update("No female selected")

    def _update_predictions(self) -> None:
        """Update offspring predictions."""
        panel = self.query_one("#prediction-panel", Static)

        if not self.selected_male or not self.selected_female:
            panel.update(
                "Select a male and female to see offspring predictions\n\n"
                "Use Tab to switch between lists, or M/F to jump directly"
            )
            return

        # Calculate predictions
        try:
            probs = predict_offspring_probabilities(
                self.selected_male.genotype,
                self.selected_female.genotype,
            )
        except Exception:
            panel.update("Unable to calculate predictions")
            return

        # Sort by probability
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        # Build status warnings
        warnings = []
        if not self.selected_male.can_breed:
            if self.selected_male.breeding_locked:
                warnings.append(f"{self.selected_male.name} is locked")
            else:
                warnings.append(f"{self.selected_male.name} can't breed yet")
        if not self.selected_female.can_breed:
            if self.selected_female.breeding_locked:
                warnings.append(f"{self.selected_female.name} is locked")
            elif self.selected_female.is_pregnant:
                warnings.append(f"{self.selected_female.name} is pregnant")
            else:
                warnings.append(f"{self.selected_female.name} can't breed yet")

        lines = [
            f"Offspring from {self.selected_male.name} x {self.selected_female.name}:"
        ]

        if warnings:
            lines.append(f"Note: {', '.join(warnings)}")

        lines.append("")  # Blank line before predictions

        for phenotype, prob in sorted_probs[:8]:  # Show top 8
            percentage = prob * 100
            bar_len = int(prob * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"{bar} {percentage:5.1f}% - {phenotype}")

        if len(sorted_probs) > 8:
            lines.append(f"\n... and {len(sorted_probs) - 8} more possibilities")

        panel.update("\n".join(lines))

    def action_go_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()

    def action_switch_panel(self) -> None:
        """Switch focus between male and female lists."""
        if self._active_panel == "male":
            self.action_focus_females()
        else:
            self.action_focus_males()

    def action_focus_males(self) -> None:
        """Focus the male list."""
        self._active_panel = "male"
        male_list = self.query_one("#male-list", ListView)
        male_list.focus()

    def action_focus_females(self) -> None:
        """Focus the female list."""
        self._active_panel = "female"
        female_list = self.query_one("#female-list", ListView)
        female_list.focus()
