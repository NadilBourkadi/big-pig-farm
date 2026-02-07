"""Pigdex screen - collection tracker for all phenotype combinations."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import VerticalScroll
from textual.widgets import Static, Footer

from big_pig_farm.entities.genetics import (
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    Rarity,
)
from big_pig_farm.entities.pigdex import (
    Pigdex,
    phenotype_key_from_parts,
    key_to_display_name,
    key_to_rarity,
    get_all_phenotype_keys,
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


class PigdexScreen(Screen):
    """Screen showing all 72 phenotype combinations and discovery progress."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    PigdexScreen {
        layout: vertical;
        background: $surface;
    }

    #pigdex-header {
        height: 3;
        background: $primary;
        padding: 1;
        text-align: center;
    }

    #pigdex-content {
        height: 1fr;
        padding: 1;
    }

    .section-label {
        text-style: bold;
        margin: 1 0 0 0;
    }

    #pigdex-footer-info {
        height: 3;
        padding: 0 1;
        border-top: solid $secondary;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        pigdex = self.state.pigdex
        pct = pigdex.completion_percent
        yield Static(
            f"PIGDEX - {pigdex.discovered_count}/{pigdex.total_possible} Discovered ({pct:.0f}%)",
            id="pigdex-header",
        )

        with VerticalScroll(id="pigdex-content"):
            # Organize by roan status, then intensity, then pattern, then color
            for roan in ALL_ROAN_TYPES:
                roan_label = "ROAN VARIANTS" if roan == RoanType.ROAN else "STANDARD"
                yield Static(f"--- {roan_label} ---", classes="section-label")

                for intensity in ALL_INTENSITIES:
                    intensity_name = intensity.value.title()
                    yield Static(f"  {intensity_name}:", classes="section-label")

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
                        yield Static(f"    {pattern_name:10} {' | '.join(line_parts)}")

        # Milestone progress
        milestones = []
        for t in [25, 50, 75, 100]:
            status = "CLAIMED" if t in pigdex.milestone_rewards_claimed else (
                "READY!" if pct >= t else f"{t}%"
            )
            milestones.append(f"{t}%: {status}")

        yield Static(f"Milestones: {' | '.join(milestones)}", id="pigdex-footer-info")
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()
