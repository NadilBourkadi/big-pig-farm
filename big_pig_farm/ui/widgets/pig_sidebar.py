"""Sidebar widget showing selected pig details."""

from textual.widgets import Static
from textual.reactive import reactive

from big_pig_farm.entities.guinea_pig import GuineaPig, Gender
from big_pig_farm.simulation.needs import get_most_urgent_need
from big_pig_farm.ui.utils import format_needs_bar


class PigSidebar(Static):
    """Sidebar showing details of the selected/followed pig."""

    DEFAULT_CSS = """
    PigSidebar {
        width: 38;
        height: 100%;
        border: solid $secondary;
        padding: 0 1;
        background: $surface;
    }

    PigSidebar.hidden {
        display: none;
    }
    """

    pig_id: reactive[str | None] = reactive(None)

    def __init__(self, state, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._pig: GuineaPig | None = None

    def set_pig(self, pig: GuineaPig | None) -> None:
        """Set the pig to display."""
        self._pig = pig
        if pig:
            self.remove_class("hidden")
        else:
            self.add_class("hidden")
        self.refresh_content()

    def refresh_content(self) -> None:
        """Refresh the sidebar content."""
        if not self._pig:
            self.update("")
            return

        pig = self._pig
        lines = []

        # Header
        gender = "♂" if pig.gender == Gender.MALE else "♀"
        lines.append(f"[bold]{pig.name}[/] {gender}")
        lines.append(f"{pig.phenotype.display_name}")
        lines.append("")

        # Needs bars
        lines.append("[dim]Needs:[/]")
        lines.append(f" Hunger  {format_needs_bar(pig.needs.hunger)}")
        lines.append(f" Thirst  {format_needs_bar(pig.needs.thirst)}")
        lines.append(f" Energy  {format_needs_bar(pig.needs.energy)}")
        lines.append(f" Happy   {format_needs_bar(pig.needs.happiness)}")
        lines.append(f" Health  {format_needs_bar(pig.needs.health)}")
        lines.append(f" Social  {format_needs_bar(pig.needs.social)}")
        lines.append(f" Fun     {format_needs_bar(100 - pig.needs.boredom)}")
        lines.append("")

        # AI State
        lines.append("[dim]AI State:[/]")
        if pig.target_description:
            lines.append(f" {pig.target_description}")
        else:
            lines.append(f" {pig.behavior_state.value}")
        urgent = get_most_urgent_need(pig)
        lines.append(f" Need: {urgent}")
        if pig.path:
            lines.append(f" {len(pig.path)} steps away")
        lines.append("")

        # Recent log
        lines.append("[dim]Recent:[/]")
        if pig.behavior_log:
            for entry in reversed(pig.behavior_log[-6:]):
                # Truncate long entries
                if len(entry) > 34:
                    entry = entry[:31] + "..."
                lines.append(f" • {entry}")
        else:
            lines.append(" (no activity)")

        self.update("\n".join(lines))

