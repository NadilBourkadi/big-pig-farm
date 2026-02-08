"""Widget for configuring the breeding program in the Breeding Planner."""

from textual.widgets import Static
from textual.events import Key

from big_pig_farm.entities.genetics import BaseColor, Pattern, ColorIntensity, RoanType
from big_pig_farm.simulation.breeding_program import BreedingProgram


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
    BaseColor.CREAM: "Cream",
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


class BreedingProgramPanel(Static, can_focus=True):
    """Panel for configuring the breeding program target and settings."""

    DEFAULT_CSS = """
    BreedingProgramPanel {
        height: auto;
        max-height: 20;
        border: solid $accent;
        padding: 0 1;
        background: $surface;
        margin: 0 1;
    }

    BreedingProgramPanel.hidden {
        display: none;
    }
    """

    def __init__(self, breeding_program: BreedingProgram, has_genetics_lab: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.breeding_program = breeding_program
        self.has_genetics_lab = has_genetics_lab
        self._cursor_axis = 0  # Which axis row
        self._cursor_item = 0  # Which item within the axis

    def _get_set_for_axis(self, axis_idx: int) -> set:
        """Get the target set for a given axis index."""
        if axis_idx == 0:
            return self.breeding_program.target_colors
        elif axis_idx == 1:
            return self.breeding_program.target_patterns
        elif axis_idx == 2:
            return self.breeding_program.target_intensities
        elif axis_idx == 3:
            return self.breeding_program.target_roan
        elif axis_idx in (4, 5, 6, 7):
            return set()  # toggle rows
        return set()

    def _total_rows(self) -> int:
        """Total navigable rows: 4 trait axes + keep_carriers + auto_pair + stock_limit + enabled."""
        return 8

    def _items_in_row(self, row: int) -> int:
        """Number of items in a given row."""
        if row < 4:
            return len(_AXES[row][1])
        return 1  # toggles and stock limit are single items

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
            if self._cursor_axis == 6:
                # Stock limit: decrease
                self.breeding_program.stock_limit = max(2, self.breeding_program.stock_limit - 1)
                event.stop()
            else:
                self._cursor_item = max(0, self._cursor_item - 1)
                event.stop()
        elif key == "right":
            if self._cursor_axis == 6:
                # Stock limit: increase
                self.breeding_program.stock_limit = min(20, self.breeding_program.stock_limit + 1)
                event.stop()
            else:
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
            target_set = self._get_set_for_axis(self._cursor_axis)
            value = values[self._cursor_item]
            if value in target_set:
                target_set.discard(value)
            else:
                target_set.add(value)
        elif self._cursor_axis == 4:
            # Keep carriers toggle
            self.breeding_program.keep_carriers = not self.breeding_program.keep_carriers
        elif self._cursor_axis == 5:
            # Auto-pair toggle
            self.breeding_program.auto_pair = not self.breeding_program.auto_pair
        elif self._cursor_axis == 6:
            # Stock limit — space does nothing, use left/right
            pass
        elif self._cursor_axis == 7:
            # Enabled toggle
            self.breeding_program.enabled = not self.breeding_program.enabled

    def refresh_content(self) -> None:
        """Redraw the panel."""
        lines = ["Breeding Program Target  (arrows + space to toggle, T to close)"]
        lines.append("")

        for axis_idx, (axis_name, values, labels) in enumerate(_AXES):
            target_set = self._get_set_for_axis(axis_idx)
            items = []
            for item_idx, val in enumerate(values):
                checked = "x" if val in target_set else " "
                label = labels[val]
                if axis_idx == self._cursor_axis and item_idx == self._cursor_item:
                    items.append(f">\[{checked}] {label}")
                else:
                    items.append(f" \[{checked}] {label}")
            all_empty = len(target_set) == 0
            suffix = " (any)" if all_empty else ""
            lines.append(f"  {axis_name}:{suffix}  {'  '.join(items)}")

        lines.append("")

        # Keep carriers toggle
        kc_check = "x" if self.breeding_program.keep_carriers else " "
        lab_status = " (Lab built)" if self.has_genetics_lab else " (needs Lab)"
        kc_cursor = ">" if self._cursor_axis == 4 else " "
        lines.append(f"  {kc_cursor}\[{kc_check}] Keep Carriers{lab_status}")

        # Auto-pair toggle
        ap_check = "x" if self.breeding_program.auto_pair else " "
        ap_cursor = ">" if self._cursor_axis == 5 else " "
        lines.append(f"  {ap_cursor}\[{ap_check}] Auto-Pair")

        # Stock limit
        sl_cursor = ">" if self._cursor_axis == 6 else " "
        lines.append(f"  {sl_cursor} Stock Limit: < {self.breeding_program.stock_limit} >  (left/right to adjust)")

        # Enabled toggle
        en_check = "x" if self.breeding_program.enabled else " "
        en_cursor = ">" if self._cursor_axis == 7 else " "
        lines.append(f"  {en_cursor}\[{en_check}] Program Enabled")

        self.update("\n".join(lines))

    def get_summary(self) -> str:
        """Get a compact one-line summary of the program state."""
        bp = self.breeding_program
        if not bp.enabled:
            return ""

        parts = []
        if bp.target_colors:
            parts.append(", ".join(_COLOR_LABELS[c] for c in bp.target_colors))
        if bp.target_patterns:
            parts.append(", ".join(_PATTERN_LABELS[p] for p in bp.target_patterns))
        if bp.target_intensities:
            parts.append(", ".join(_INTENSITY_LABELS[i] for i in bp.target_intensities))
        if bp.target_roan:
            roan_vals = [_ROAN_LABELS[r] for r in bp.target_roan if r != RoanType.NONE]
            if roan_vals:
                parts.append(", ".join(roan_vals))

        trait_str = "; ".join(parts) if parts else "all traits"
        auto = " | Auto-pair ON" if bp.auto_pair else ""
        return f"Target: {trait_str}{auto} | Stock: {bp.stock_limit}"
