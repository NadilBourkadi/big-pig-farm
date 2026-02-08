"""Breeding screen for viewing breeding pairs and genetics."""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label, Footer
from textual.reactive import reactive

from big_pig_farm.entities.guinea_pig import GuineaPig, Gender
from big_pig_farm.entities.genetics import predict_offspring_probabilities, Genotype, carrier_summary, calculate_target_probability
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState
from big_pig_farm.ui.widgets.breeding_program_panel import BreedingProgramPanel


class PigListItem(ListItem):
    """List item for a guinea pig."""

    def __init__(self, pig: GuineaPig, is_paired: bool = False, is_auto_paired: bool = False):
        status = ""
        if is_auto_paired:
            status = " [AUTO]"
        elif is_paired:
            status = " [PAIRED]"
        elif pig.breeding_locked:
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
        ("p", "set_pair", "Pair"),
        ("c", "cancel_pair", "Cancel Pair"),
        ("t", "toggle_program", "Target"),
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

    #pair-status {
        height: auto;
        max-height: 3;
        padding: 0 1;
        color: $warning;
    }

    #program-status {
        height: auto;
        max-height: 2;
        padding: 0 1;
        color: $accent;
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
        yield Static("", id="pair-status")
        yield Static("", id="program-status")

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

        yield BreedingProgramPanel(
            self.state.breeding_program,
            has_genetics_lab=self._has_genetics_lab(),
            id="program-panel",
            classes="hidden",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self._populate_lists()
        self._update_pair_status()
        self._update_program_status()
        # Focus the male list by default
        male_list = self.query_one("#male-list", ListView)
        male_list.focus()

    def _get_paired_ids(self) -> set[UUID]:
        """Get the set of pig IDs currently in the active breeding pair."""
        if self.state.breeding_pair is None:
            return set()
        return {self.state.breeding_pair.male_id, self.state.breeding_pair.female_id}

    def _is_auto_paired(self) -> bool:
        """Check if the current breeding pair was set by auto-pair."""
        return (
            self.state.breeding_pair is not None
            and self.state.breeding_program.should_auto_pair()
        )

    def _populate_lists(self) -> None:
        """Populate the male and female lists."""
        male_list = self.query_one("#male-list", ListView)
        female_list = self.query_one("#female-list", ListView)

        male_list.clear()
        female_list.clear()

        pigs = self.state.get_pigs_list()
        paired_ids = self._get_paired_ids()
        auto_paired = self._is_auto_paired()

        # Add adult males
        males = [p for p in pigs if p.gender == Gender.MALE and p.is_adult]
        for pig in males:
            is_paired = pig.id in paired_ids
            male_list.append(PigListItem(
                pig,
                is_paired=is_paired and not auto_paired,
                is_auto_paired=is_paired and auto_paired,
            ))

        # Add adult females (including pregnant ones, but marked)
        females = [p for p in pigs if p.gender == Gender.FEMALE and p.is_adult]
        for pig in females:
            is_paired = pig.id in paired_ids
            female_list.append(PigListItem(
                pig,
                is_paired=is_paired and not auto_paired,
                is_auto_paired=is_paired and auto_paired,
            ))

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
                lines.append(f"Carriers: {carrier_summary(pig.genotype)}")
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
                lines.append(f"Carriers: {carrier_summary(pig.genotype)}")
            info.update("\n".join(lines))
        else:
            info.update("No female selected")

    def _update_pair_status(self) -> None:
        """Update the pair status banner."""
        banner = self.query_one("#pair-status", Static)
        pair = self.state.breeding_pair
        if pair is None:
            banner.update("")
            return

        male = self.state.get_guinea_pig(pair.male_id)
        female = self.state.get_guinea_pig(pair.female_id)
        if male is None or female is None:
            banner.update("")
            return

        male_ready = "Ready" if male.can_breed else "Not ready"
        female_ready = "Ready" if female.can_breed else "Not ready"
        auto_tag = " [AUTO]" if self._is_auto_paired() else ""
        banner.update(
            f"Active Pair{auto_tag}: {male.name} ({male_ready}) x {female.name} ({female_ready})"
            f" - Waiting... [C to cancel]"
        )

    def _update_program_status(self) -> None:
        """Update the breeding program progress banner."""
        banner = self.query_one("#program-status", Static)
        program = self.state.breeding_program
        if not program.enabled:
            banner.update("")
            return

        parts = ["Program: ON"]

        # Target description
        if program.has_target:
            panel = self.query_one("#program-panel", BreedingProgramPanel)
            summary = panel.get_summary()
            if summary:
                parts.append(summary)
        else:
            parts.append("No target set")

        # Current stock count
        adults = [p for p in self.state.get_pigs_list() if not p.is_baby]
        parts.append(f"Stock: {len(adults)}/{program.stock_limit}")

        # Best pair probability
        if program.has_target:
            best_prob = self._find_best_pair_probability()
            if best_prob is not None:
                parts.append(f"Best pair: {best_prob * 100:.1f}%")

        banner.update(" | ".join(parts))

    def _find_best_pair_probability(self) -> Optional[float]:
        """Find the highest target probability across all eligible pairs."""
        program = self.state.breeding_program
        pigs = self.state.get_pigs_list()

        males = [p for p in pigs if p.gender == Gender.MALE and p.can_breed and not p.breeding_locked]
        females = [p for p in pigs if p.gender == Gender.FEMALE and p.can_breed
                   and not p.is_pregnant and not p.breeding_locked]

        if not males or not females:
            return None

        best = 0.0
        for male in males:
            for female in females:
                prob = calculate_target_probability(
                    male.genotype, female.genotype,
                    program.target_colors, program.target_patterns,
                    program.target_intensities, program.target_roan,
                )
                if prob > best:
                    best = prob

        return best if best > 0 else None

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
            bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
            lines.append(f"{bar} {percentage:5.1f}% - {phenotype}")

        if len(sorted_probs) > 8:
            lines.append(f"\n... and {len(sorted_probs) - 8} more possibilities")

        # Target probability if program has target
        program = self.state.breeding_program
        if program.has_target:
            target_prob = calculate_target_probability(
                self.selected_male.genotype,
                self.selected_female.genotype,
                program.target_colors,
                program.target_patterns,
                program.target_intensities,
                program.target_roan,
            )
            lines.append(f"\nTarget probability: {target_prob * 100:.1f}%")

        # Pair hint
        pair = self.state.breeding_pair
        if (pair and pair.male_id == self.selected_male.id
                and pair.female_id == self.selected_female.id):
            lines.append("\nThis pair is currently active")
        else:
            lines.append("\nPress P to set this breeding pair")

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

    def action_set_pair(self) -> None:
        """Set the selected pigs as a manual breeding pair."""
        if not self.selected_male or not self.selected_female:
            self.notify("Select both a male and a female first", severity="error")
            return

        male = self.selected_male
        female = self.selected_female

        # Hard blocks
        if female.is_pregnant:
            self.notify(f"{female.name} is already pregnant", severity="error")
            return
        if male.breeding_locked:
            self.notify(f"{male.name} is breeding-locked", severity="error")
            return
        if female.breeding_locked:
            self.notify(f"{female.name} is breeding-locked", severity="error")
            return

        # Set the pair
        self.state.set_breeding_pair(male.id, female.id)

        # Soft warnings
        warnings = []
        if not male.can_breed:
            warnings.append(f"{male.name} not ready yet")
        if not female.can_breed:
            warnings.append(f"{female.name} not ready yet")

        if warnings:
            self.notify(f"Pair set — waiting: {', '.join(warnings)}")
        else:
            self.notify(f"Pair set: {male.name} x {female.name}")

        self._update_pair_status()
        self._populate_lists()
        self._update_predictions()

    def action_cancel_pair(self) -> None:
        """Cancel the active breeding pair."""
        if self.state.breeding_pair is None:
            self.notify("No active breeding pair", severity="warning")
            return

        self.state.clear_breeding_pair()
        self.notify("Breeding pair cancelled")
        self._update_pair_status()
        self._populate_lists()
        self._update_predictions()

    def action_toggle_program(self) -> None:
        """Toggle the breeding program panel visibility."""
        panel = self.query_one("#program-panel", BreedingProgramPanel)
        if panel.has_class("hidden"):
            panel.has_genetics_lab = self._has_genetics_lab()
            panel.remove_class("hidden")
            panel.refresh_content()
            panel.focus()
        else:
            panel.add_class("hidden")
            self._update_program_status()
            # Return focus to last active pig list
            if self._active_panel == "female":
                self.action_focus_females()
            else:
                self.action_focus_males()
