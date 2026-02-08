"""Widget for configuring the breeding filter in the Breeding Planner."""

from textual.widgets import Static
from textual.events import Key

from big_pig_farm.entities.genetics import BaseColor, Pattern, ColorIntensity, RoanType
from big_pig_farm.simulation.breeding_filter import BreedingFilter


# Ordered lists of values per axis for display
_COLORS = list(BaseColor)
_PATTERNS = list(Pattern)
_INTENSITIES = list(ColorIntensity)
_ROAN = list(RoanType)

# Human-readable labels
_COLOR_LABELS = {
    BaseColor.BLACK: "Black",
    BaseColor.CHOCOLATE: "Chocolate",
    BaseColor.GOLDEN: "Golden",
    BaseColor.LIGHT_GOLDEN: "Cream",
}

_PATTERN_LABELS = {
    Pattern.SOLID: "Solid",
    Pattern.DUTCH: "Dutch",
    Pattern.DALMATIAN: "Dalmatian",
}

_INTENSITY_LABELS = {
    ColorIntensity.FULL: "Full",
    ColorIntensity.CHINCHILLA: "Chinchilla",
    ColorIntensity.HIMALAYAN: "Himalayan",
}

_ROAN_LABELS = {
    RoanType.NONE: "None",
    RoanType.ROAN: "Roan",
}

# All axes in order
_AXES = [
    ("Color", _COLORS, _COLOR_LABELS),
    ("Pattern", _PATTERNS, _PATTERN_LABELS),
    ("Intensity", _INTENSITIES, _INTENSITY_LABELS),
    ("Roan", _ROAN, _ROAN_LABELS),
]


class BreedingFilterPanel(Static, can_focus=True):
    """Panel for configuring trait-based breeding filter."""

    DEFAULT_CSS = """
    BreedingFilterPanel {
        height: auto;
        max-height: 16;
        border: solid $accent;
        padding: 0 1;
        background: $surface;
        margin: 0 1;
    }

    BreedingFilterPanel.hidden {
        display: none;
    }
    """

    def __init__(self, breeding_filter: BreedingFilter, has_genetics_lab: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.breeding_filter = breeding_filter
        self.has_genetics_lab = has_genetics_lab
        self._cursor_axis = 0  # Which axis row
        self._cursor_item = 0  # Which item within the axis

    def _get_set_for_axis(self, axis_idx: int) -> set:
        """Get the keep_* set for a given axis index."""
        if axis_idx == 0:
            return self.breeding_filter.keep_colors
        elif axis_idx == 1:
            return self.breeding_filter.keep_patterns
        elif axis_idx == 2:
            return self.breeding_filter.keep_intensities
        elif axis_idx == 3:
            return self.breeding_filter.keep_roan
        elif axis_idx == 4:
            return set()  # carrier-aware toggle
        elif axis_idx == 5:
            return set()  # enabled toggle
        return set()

    def _total_rows(self) -> int:
        """Total navigable rows: 4 trait axes + carrier_aware + enabled."""
        return 6

    def _items_in_row(self, row: int) -> int:
        """Number of items in a given row."""
        if row < 4:
            return len(_AXES[row][1])
        return 1  # carrier_aware and enabled are single toggles

    def on_key(self, event: Key) -> None:
        """Handle keyboard navigation and toggling."""
        key = event.key

        if key == "up":
            self._cursor_axis = max(0, self._cursor_axis - 1)
            self._cursor_item = min(self._cursor_item, self._items_in_row(self._cursor_axis) - 1)
            event.stop()
        elif key == "down":
            self._cursor_axis = min(self._total_rows() - 1, self._cursor_axis + 1)
            self._cursor_item = min(self._cursor_item, self._items_in_row(self._cursor_axis) - 1)
            event.stop()
        elif key == "left":
            self._cursor_item = max(0, self._cursor_item - 1)
            event.stop()
        elif key == "right":
            self._cursor_item = min(self._items_in_row(self._cursor_axis) - 1, self._cursor_item + 1)
            event.stop()
        elif key in ("space", "enter"):
            self._toggle_current()
            event.stop()
        else:
            return

        self.refresh_content()

    def _toggle_current(self) -> None:
        """Toggle the currently selected item."""
        if self._cursor_axis < 4:
            # Trait axis toggle
            axis_name, values, labels = _AXES[self._cursor_axis]
            keep_set = self._get_set_for_axis(self._cursor_axis)
            value = values[self._cursor_item]
            if value in keep_set:
                keep_set.discard(value)
            else:
                keep_set.add(value)
        elif self._cursor_axis == 4:
            # Carrier-aware toggle
            self.breeding_filter.carrier_aware = not self.breeding_filter.carrier_aware
        elif self._cursor_axis == 5:
            # Enabled toggle
            self.breeding_filter.enabled = not self.breeding_filter.enabled

    def refresh_content(self) -> None:
        """Redraw the panel."""
        lines = ["Breeding Filter  (arrows + space to toggle, G to close)"]
        lines.append("")

        for axis_idx, (axis_name, values, labels) in enumerate(_AXES):
            keep_set = self._get_set_for_axis(axis_idx)
            items = []
            for item_idx, val in enumerate(values):
                checked = "x" if val in keep_set else " "
                label = labels[val]
                if axis_idx == self._cursor_axis and item_idx == self._cursor_item:
                    items.append(f">\[{checked}] {label}")
                else:
                    items.append(f" \[{checked}] {label}")
            all_empty = len(keep_set) == 0
            suffix = " (any)" if all_empty else ""
            lines.append(f"  {axis_name}:{suffix}  {'  '.join(items)}")

        lines.append("")

        # Carrier-aware toggle
        ca_check = "x" if self.breeding_filter.carrier_aware else " "
        lab_status = " (Lab built)" if self.has_genetics_lab else " (needs Lab)"
        ca_cursor = ">" if self._cursor_axis == 4 else " "
        lines.append(f"  {ca_cursor}\[{ca_check}] Carrier-Aware Mode{lab_status}")

        # Enabled toggle
        en_check = "x" if self.breeding_filter.enabled else " "
        en_cursor = ">" if self._cursor_axis == 5 else " "
        lines.append(f"  {en_cursor}\[{en_check}] Filter Enabled")

        self.update("\n".join(lines))

    def get_summary(self) -> str:
        """Get a compact one-line summary of the filter state."""
        bf = self.breeding_filter
        if not bf.enabled:
            return ""

        parts = []
        if bf.keep_colors:
            parts.append(", ".join(_COLOR_LABELS[c] for c in bf.keep_colors))
        if bf.keep_patterns:
            parts.append(", ".join(_PATTERN_LABELS[p] for p in bf.keep_patterns))
        if bf.keep_intensities:
            parts.append(", ".join(_INTENSITY_LABELS[i] for i in bf.keep_intensities))
        if bf.keep_roan:
            roan_vals = [_ROAN_LABELS[r] for r in bf.keep_roan if r != RoanType.NONE]
            if roan_vals:
                parts.append(", ".join(roan_vals))

        trait_str = "; ".join(parts) if parts else "all traits"
        carrier = " +carriers" if bf.carrier_aware else ""
        return f"Filter: ON — Keep {trait_str}{carrier}"
