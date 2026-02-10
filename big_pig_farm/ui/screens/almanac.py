"""Journal screen - tabbed view combining Pigdex, Contracts, and Event Log."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import VerticalScroll
from textual.widgets import Static, Footer, TabbedContent, TabPane

from big_pig_farm.economy.contracts import BreedingContract, ContractDifficulty
from big_pig_farm.entities.genetics import (
    BaseColor, Pattern, ColorIntensity, RoanType, Rarity,
)
from big_pig_farm.entities.pigdex import (
    phenotype_key_from_parts,
    key_to_rarity,
    ALL_BASE_COLORS,
    ALL_PATTERNS,
    ALL_INTENSITIES,
    ALL_ROAN_TYPES,
)
from big_pig_farm.game.state import GameState


# Pigdex grid labels
_COLOR_HEADERS = {
    BaseColor.BLACK: "Black",
    BaseColor.CHOCOLATE: "Chocolate",
    BaseColor.GOLDEN: "Golden",
    BaseColor.CREAM: "Cream",
}
_INTENSITY_LABELS = {
    ColorIntensity.FULL: "Full",
    ColorIntensity.CHINCHILLA: "Chinchilla",
    ColorIntensity.HIMALAYAN: "Himalayan",
}
_PATTERN_LABELS = {
    Pattern.SOLID: "Solid",
    Pattern.DUTCH: "Dutch",
    Pattern.DALMATIAN: "Dalmatian",
}
_RARITY_SYMBOLS = {
    Rarity.COMMON: "\u2713",
    Rarity.UNCOMMON: "\u2713*",
    Rarity.RARE: "\u2713**",
    Rarity.VERY_RARE: "\u2713***",
    Rarity.LEGENDARY: "\u2713!",
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
        self.state = state
        super().__init__(self._build_content(), **kwargs)

    def _build_content(self) -> str:
        pigdex = self.state.pigdex
        pct = pigdex.completion_percent
        lines = []
        lines.append(f"[bold]{pigdex.discovered_count}/{pigdex.total_possible} Discovered ({pct:.0f}%)[/]")
        lines.append("")

        # Column header row
        col_w = 12  # width per color column
        i_w = 12   # intensity label width
        p_w = 11   # pattern label width
        prefix_w = 2 + i_w + p_w  # total prefix width
        header = " " * prefix_w
        for color in ALL_BASE_COLORS:
            header += f"{_COLOR_HEADERS[color]:<{col_w}}"
        lines.append(f"[bold]{header}[/]")

        for roan in ALL_ROAN_TYPES:
            roan_label = "ROAN" if roan == RoanType.ROAN else "STANDARD"
            lines.append(f"[bold]{'─' * prefix_w}{'─' * col_w * len(ALL_BASE_COLORS)}[/]")
            lines.append(f"[bold]{roan_label}[/]")

            for intensity in ALL_INTENSITIES:
                i_label = _INTENSITY_LABELS[intensity]
                for pi, pattern in enumerate(ALL_PATTERNS):
                    p_label = _PATTERN_LABELS[pattern]
                    # Show intensity label only on first pattern row
                    if pi == 0:
                        prefix = f"  {i_label:<{i_w}}{p_label:<{p_w}}"
                    else:
                        prefix = f"  {'':<{i_w}}{p_label:<{p_w}}"

                    cells = ""
                    for color in ALL_BASE_COLORS:
                        key = phenotype_key_from_parts(color, pattern, intensity, roan)
                        if pigdex.is_discovered(key):
                            rarity = key_to_rarity(key)
                            symbol = _RARITY_SYMBOLS.get(rarity, "\u2713")
                            cells += f"[green]{symbol:<{col_w}}[/]"
                        else:
                            cells += f"[dim]{'·':<{col_w}}[/]"

                    lines.append(f"{prefix}{cells}")

        # Rarity legend
        lines.append("")
        lines.append("[dim]\u2713 Common  \u2713* Uncommon  \u2713** Rare  \u2713*** Very Rare  \u2713! Legendary[/]")

        # Milestones
        lines.append("")
        milestones = []
        for t in [25, 50, 75, 100]:
            status = "CLAIMED" if t in pigdex.milestone_rewards_claimed else (
                "[bold]READY![/]" if pct >= t else f"{t}%"
            )
            milestones.append(f"{t}%: {status}")
        lines.append(f"[bold]Milestones:[/] {' | '.join(milestones)}")

        return "\n".join(lines)


class ContractsPanel(Static):
    """Panel showing active breeding contracts."""

    def __init__(self, state: GameState, **kwargs):
        self.state = state
        super().__init__(self._build_content(), **kwargs)

    def _build_content(self) -> str:
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

        return "\n".join(lines)

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
        self.state = state
        super().__init__(self._build_content(), **kwargs)

    def _build_content(self) -> str:
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

        return "\n".join(lines)


class JournalScreen(Screen):
    """Tabbed screen combining Pigdex, Contracts, and Event Log."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", None),
        ("up", "scroll_up", None),
        ("down", "scroll_down", None),
        ("pageup", "page_up", None),
        ("pagedown", "page_down", None),
    ]

    DEFAULT_CSS = """
    JournalScreen {
        layout: vertical;
        background: $surface;
    }

    #journal-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #journal-tabs {
        height: 1fr;
    }

    .journal-panel {
        padding: 1;
        height: auto;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        yield Static("JOURNAL", id="journal-header")

        with TabbedContent(id="journal-tabs"):
            with TabPane("Pigdex"):
                with VerticalScroll():
                    yield PigdexPanel(self.state, classes="journal-panel")
            with TabPane("Contracts"):
                with VerticalScroll():
                    yield ContractsPanel(self.state, classes="journal-panel")
            with TabPane("Log"):
                with VerticalScroll():
                    yield EventLogPanel(self.state, classes="journal-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Set VerticalScroll heights inline to ensure scrolling works."""
        for vs in self.query(VerticalScroll):
            vs.styles.height = "1fr"

    def _get_active_scroll(self) -> VerticalScroll | None:
        """Get the VerticalScroll in the currently active tab."""
        tabs = self.query_one("#journal-tabs", TabbedContent)
        active_pane = tabs.get_pane(tabs.active)
        try:
            return active_pane.query_one(VerticalScroll)
        except Exception:
            return None

    def action_scroll_up(self) -> None:
        vs = self._get_active_scroll()
        if vs:
            vs.scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        vs = self._get_active_scroll()
        if vs:
            vs.scroll_down(animate=False)

    def action_page_up(self) -> None:
        vs = self._get_active_scroll()
        if vs:
            vs.scroll_page_up(animate=False)

    def action_page_down(self) -> None:
        vs = self._get_active_scroll()
        if vs:
            vs.scroll_page_down(animate=False)

    def action_go_back(self) -> None:
        self.app.pop_screen()
