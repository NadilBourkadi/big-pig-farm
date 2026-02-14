"""Sidebar widget showing selected pig details."""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text

from big_pig_farm.data.sprite_pixels import (
    generate_portrait_with_scene,
    convert_pixels,
    render_to_rich_text,
    PALETTES,
)
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender
from big_pig_farm.simulation.needs import get_most_urgent_need
from big_pig_farm.ui.utils import format_needs_bar, format_breeding_status


class PigSidebar(Static):
    """Sidebar showing details of the selected/followed pig."""

    DEFAULT_CSS = """
    PigSidebar {
        width: 38;
        height: 100%;
        border: solid $secondary;
        padding: 1 1 0 1;
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

    def _build_portrait(self, pig: GuineaPig) -> Text:
        """Render a half-block portrait for the sidebar."""
        grid = generate_portrait_with_scene(
            pig.phenotype.base_color.name,
            pig.phenotype.pattern.value,
            pig.phenotype.intensity.value,
            pig.phenotype.roan.value,
            str(pig.id),
        )
        palette = PALETTES.get(pig.phenotype.base_color.name, PALETTES["BLACK"])
        converted = convert_pixels(grid, palette)
        return render_to_rich_text(converted, center_width=34)

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

        # Breeding status
        lines.append(f"[dim]Breed:[/] {format_breeding_status(pig)}")
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

        # Build portrait
        portrait = self._build_portrait(pig)
        portrait_lines = str(portrait).count("\n") + 1

        # Calculate how many recent entries fit
        # Fixed lines: portrait + all lines above + "Recent:" label + 1 blank
        fixed_lines = portrait_lines + 1 + len(lines) + 1
        available = self.size.height - 2 - fixed_lines  # -2 for border
        recent_count = max(3, available)

        # Recent log
        lines.append("[dim]Recent:[/]")
        if pig.behavior_log:
            for entry in reversed(pig.behavior_log[-recent_count:]):
                # Truncate long entries
                if len(entry) > 34:
                    entry = entry[:31] + "..."
                lines.append(f" • {entry}")
        else:
            lines.append(" (no activity)")

        combined = Text()
        combined.append_text(portrait)
        combined.append("\n\n")
        combined.append(Text.from_markup("\n".join(lines)))
        self.update(combined)

