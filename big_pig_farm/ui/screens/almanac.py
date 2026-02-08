"""Almanac screen - tabbed view combining Pigdex, Contracts, and Event Log."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import VerticalScroll
from textual.widgets import Static, Footer, TabbedContent, TabPane

from big_pig_farm.economy.contracts import BreedingContract, ContractDifficulty
from big_pig_farm.entities.genetics import RoanType, Rarity
from big_pig_farm.entities.pigdex import (
    phenotype_key_from_parts,
    key_to_display_name,
    key_to_rarity,
    ALL_BASE_COLORS,
    ALL_PATTERNS,
    ALL_INTENSITIES,
    ALL_ROAN_TYPES,
)
from big_pig_farm.game.state import GameState


RARITY_MARKERS = {
    Rarity.COMMON: " ",
    Rarity.UNCOMMON: "*",
    Rarity.RARE: "**",
    Rarity.VERY_RARE: "***",
    Rarity.LEGENDARY: "!!!!",
}

DIFFICULTY_LABELS = {
    ContractDifficulty.EASY: "Easy",
    ContractDifficulty.MEDIUM: "Medium",
    ContractDifficulty.HARD: "Hard",
    ContractDifficulty.EXPERT: "Expert",
}

EVENT_ICONS = {
    "info": "\U0001f514",
    "birth": "\U0001f389",
    "death": "\U0001f494",
    "sale": "\U0001f4b0",
    "purchase": "\U0001f6d2",
    "breeding": "\U0001f495",
    "mutation": "\u2728",
    "pigdex": "\U0001f4d6",
    "contract": "\U0001f4dc",
}


class PigdexPanel(Static):
    """Panel showing Pigdex collection progress."""

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def on_mount(self) -> None:
        self._render_content()

    def _render_content(self) -> None:
        pigdex = self.state.pigdex
        pct = pigdex.completion_percent
        lines = []
        lines.append(f"[bold]{pigdex.discovered_count}/{pigdex.total_possible} Discovered ({pct:.0f}%)[/]")
        lines.append("")

        for roan in ALL_ROAN_TYPES:
            roan_label = "ROAN VARIANTS" if roan == RoanType.ROAN else "STANDARD"
            lines.append(f"[bold]--- {roan_label} ---[/]")

            for intensity in ALL_INTENSITIES:
                intensity_name = intensity.value.title()
                lines.append(f"  [bold]{intensity_name}:[/]")

                for pattern in ALL_PATTERNS:
                    line_parts = []
                    for color in ALL_BASE_COLORS:
                        key = phenotype_key_from_parts(color, pattern, intensity, roan)
                        if pigdex.is_discovered(key):
                            name = key_to_display_name(key)
                            rarity = key_to_rarity(key)
                            marker = RARITY_MARKERS.get(rarity, "")
                            line_parts.append(f"{name}{marker}")
                        else:
                            line_parts.append("[???]")

                    pattern_name = pattern.value.title()
                    lines.append(f"    {pattern_name:10} {' | '.join(line_parts)}")

        # Milestones
        lines.append("")
        milestones = []
        for t in [25, 50, 75, 100]:
            status = "CLAIMED" if t in pigdex.milestone_rewards_claimed else (
                "READY!" if pct >= t else f"{t}%"
            )
            milestones.append(f"{t}%: {status}")
        lines.append(f"Milestones: {' | '.join(milestones)}")

        self.update("\n".join(lines))


class ContractsPanel(Static):
    """Panel showing active breeding contracts."""

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def on_mount(self) -> None:
        self._render_content()

    def _render_content(self) -> None:
        board = self.state.contract_board
        lines = []
        lines.append(f"[bold]{len(board.active_contracts)} Active Contracts[/]")
        lines.append("")

        if not board.active_contracts:
            lines.append("No active contracts. Check back later!")
        else:
            for contract in board.active_contracts:
                lines.append(self._format_contract(contract))
                lines.append("")

        lines.append(f"[dim]Completed: {board.completed_contracts} | "
                     f"Total Bonus: {board.total_contract_earnings} Squeaks | "
                     f"Day {self.state.game_time.day}[/]")

        self.update("\n".join(lines))

    def _format_contract(self, contract: BreedingContract) -> str:
        difficulty = DIFFICULTY_LABELS.get(contract.difficulty, "?")
        days_left = max(0, contract.deadline_day - self.state.game_time.day)
        parts = [
            f"  {contract.description}",
            f"  Difficulty: {difficulty} | Reward: +{contract.reward} Squeaks",
            f"  Expires: Day {contract.deadline_day} ({days_left} days left)",
        ]
        if contract.breeding_hint:
            parts.append(f"  Tip: {contract.breeding_hint}")
        return "\n".join(parts)


class EventLogPanel(Static):
    """Panel showing scrollable event history."""

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def on_mount(self) -> None:
        self._render_content()

    def _render_content(self) -> None:
        events = self.state.events
        lines = []
        lines.append(f"[bold]{len(events)} Events[/]")
        lines.append("")

        if not events:
            lines.append("No events yet.")
        else:
            for event in reversed(events):
                icon = EVENT_ICONS.get(event.event_type, "\U0001f514")
                lines.append(f"{icon} Day {event.game_day} | {event.message}")

        self.update("\n".join(lines))


class AlmanacScreen(Screen):
    """Tabbed screen combining Pigdex, Contracts, and Event Log."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    AlmanacScreen {
        layout: vertical;
        background: $surface;
    }

    #almanac-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #almanac-tabs {
        height: 1fr;
    }

    .almanac-panel {
        padding: 1;
        height: auto;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        yield Static("ALMANAC", id="almanac-header")

        with TabbedContent("Pigdex", "Contracts", "Log", id="almanac-tabs"):
            with TabPane("Pigdex"):
                with VerticalScroll():
                    yield PigdexPanel(self.state, classes="almanac-panel")
            with TabPane("Contracts"):
                with VerticalScroll():
                    yield ContractsPanel(self.state, classes="almanac-panel")
            with TabPane("Log"):
                with VerticalScroll():
                    yield EventLogPanel(self.state, classes="almanac-panel")

        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()
