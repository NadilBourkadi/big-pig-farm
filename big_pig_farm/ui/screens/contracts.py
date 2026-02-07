"""Contracts screen - view active breeding contracts."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import VerticalScroll
from textual.widgets import Static, Footer

from big_pig_farm.economy.contracts import BreedingContract, ContractDifficulty
from big_pig_farm.game.state import GameState


DIFFICULTY_LABELS = {
    ContractDifficulty.EASY: "Easy",
    ContractDifficulty.MEDIUM: "Medium",
    ContractDifficulty.HARD: "Hard",
    ContractDifficulty.EXPERT: "Expert",
}


class ContractsScreen(Screen):
    """Screen showing active breeding contracts."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    ContractsScreen {
        layout: vertical;
        background: $surface;
    }

    #contracts-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #contracts-content {
        height: 1fr;
        padding: 1;
    }

    .contract-card {
        border: solid $secondary;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #contracts-stats {
        height: 3;
        padding: 0 1;
        border-top: solid $secondary;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        board = self.state.contract_board
        yield Static(
            f"BREEDING CONTRACTS - {len(board.active_contracts)} Active",
            id="contracts-header",
        )

        with VerticalScroll(id="contracts-content"):
            if not board.active_contracts:
                yield Static("No active contracts. Check back later!")
            else:
                for contract in board.active_contracts:
                    yield Static(
                        self._format_contract(contract),
                        classes="contract-card",
                    )

        stats = (
            f"Completed: {board.completed_contracts} | "
            f"Total Bonus Earned: {board.total_contract_earnings} Squeaks | "
            f"Day {self.state.game_time.day}"
        )
        yield Static(stats, id="contracts-stats")
        yield Footer()

    def _format_contract(self, contract: BreedingContract) -> str:
        """Format a contract for display."""
        difficulty = DIFFICULTY_LABELS.get(contract.difficulty, "?")
        days_left = max(0, contract.deadline_day - self.state.game_time.day)

        lines = [
            f"{contract.description}",
            f"Difficulty: {difficulty} | Reward: +{contract.reward} Squeaks (bonus)",
            f"Expires: Day {contract.deadline_day} ({days_left} days left)",
        ]
        return "\n".join(lines)

    def action_go_back(self) -> None:
        self.app.pop_screen()
