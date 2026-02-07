"""Event log screen - scrollable history of game events."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import VerticalScroll
from textual.widgets import Static, Footer

from big_pig_farm.game.state import GameState


EVENT_ICONS = {
    "info": "\U0001f514",
    "birth": "\U0001f389",
    "death": "\U0001f494",
    "sale": "\U0001f4b0",
    "purchase": "\U0001f6d2",
    "breeding": "\U0001f495",
    "mutation": "\u2728",
    "pigdex": "\U0001f4d6",
}


class EventLogScreen(Screen):
    """Screen showing scrollable event history."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    EventLogScreen {
        layout: vertical;
        background: $surface;
    }

    #event-log-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #event-log-content {
        height: 1fr;
        padding: 1;
    }

    .event-entry {
        height: auto;
        margin: 0 0 0 0;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        count = len(self.state.events)
        yield Static(f"EVENT LOG - {count} Events", id="event-log-header")

        with VerticalScroll(id="event-log-content"):
            if not self.state.events:
                yield Static("No events yet.")
            else:
                for event in reversed(self.state.events):
                    icon = EVENT_ICONS.get(event.event_type, "\U0001f514")
                    yield Static(
                        f"{icon} Day {event.game_day} | {event.message}",
                        classes="event-entry",
                    )

        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()
