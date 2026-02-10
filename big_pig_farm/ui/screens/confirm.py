"""Confirmation dialog screen."""

from typing import Callable

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button


class ConfirmScreen(ModalScreen[bool]):
    """A modal confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm-dialog {
        width: 50;
        height: 10;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #confirm-message {
        height: 3;
        content-align: center middle;
        text-align: center;
    }

    #confirm-buttons {
        height: 3;
        align: center middle;
    }

    #confirm-buttons Button {
        margin: 0 2;
    }
    """

    def __init__(self, message: str, destructive: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.destructive = destructive

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        yes_variant = "error" if self.destructive else "success"
        with Container(id="confirm-dialog"):
            yield Static(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", id="yes-btn", variant=yes_variant)
                yield Button("No", id="no-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "yes-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle key press."""
        if event.key == "y":
            self.dismiss(True)
        elif event.key == "n" or event.key == "escape":
            self.dismiss(False)
