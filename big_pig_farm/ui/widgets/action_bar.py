"""Action bar widget showing available controls."""

from textual.app import ComposeResult
from textual.widgets import Static


class ActionBar(Static):
    """Bottom bar showing available keyboard controls."""

    DEFAULT_CSS = """
    ActionBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, controls: list[tuple[str, str]] | None = None):
        """Initialize with list of (key, action) tuples."""
        super().__init__()
        self.controls = controls or [
            ("F", "Feed"),
            ("S", "Shop"),
            ("P", "Pigs"),
            ("B", "Breeding"),
            ("Space", "Pause"),
            ("+/-", "Speed"),
            ("Q", "Quit"),
        ]

    def render(self) -> str:
        """Render the action bar content."""
        parts = [f"[{key}]{action}" for key, action in self.controls]
        return "  ".join(parts)

    def set_controls(self, controls: list[tuple[str, str]]) -> None:
        """Update the displayed controls."""
        self.controls = controls
        self.refresh()
