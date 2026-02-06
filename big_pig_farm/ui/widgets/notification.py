"""Notification/toast widget for game events."""

from textual.widgets import Static
from textual.reactive import reactive


class NotificationBar(Static):
    """Widget showing recent game notifications."""

    messages: reactive[list[str]] = reactive(list, init=False)
    current_index: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    NotificationBar {
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = []
        self._max_messages = 10

    def add_message(self, message: str, event_type: str = "info") -> None:
        """Add a new notification message."""
        # Add icon based on type
        icons = {
            "info": "🔔",
            "birth": "🎉",
            "death": "💔",
            "sale": "💰",
            "purchase": "🛒",
            "breeding": "💕",
        }
        icon = icons.get(event_type, "🔔")

        formatted = f"{icon} {message}"
        self.messages.append(formatted)

        # Keep only recent messages
        if len(self.messages) > self._max_messages:
            self.messages = self.messages[-self._max_messages:]

        # Show the new message
        self.current_index = len(self.messages) - 1
        self.refresh()

    def render(self) -> str:
        """Render the current notification."""
        if not self.messages:
            return ""

        message = self.messages[self.current_index]
        total = len(self.messages)
        index = self.current_index + 1

        # Truncate message if too long
        max_len = self.size.width - 10
        if len(message) > max_len:
            message = message[:max_len - 3] + "..."

        if total > 1:
            return f"{message}  [{index}/{total}]"
        return message

    def next_message(self) -> None:
        """Show the next message."""
        if self.messages:
            self.current_index = (self.current_index + 1) % len(self.messages)
            self.refresh()

    def prev_message(self) -> None:
        """Show the previous message."""
        if self.messages:
            self.current_index = (self.current_index - 1) % len(self.messages)
            self.refresh()

    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []
        self.current_index = 0
        self.refresh()
