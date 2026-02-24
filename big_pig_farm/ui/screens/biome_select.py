"""Biome selection screen for adding new rooms."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Footer, Label, ListItem, ListView, Static

from big_pig_farm.economy.currency import format_currency
from big_pig_farm.entities.biomes import BIOMES, BiomeInfo, BiomeType


class BiomeListItem(ListItem):
    """Widget representing a biome option."""

    def __init__(
        self,
        biome: BiomeType,
        info: BiomeInfo,
        available: bool,
        lock_reason: str | None = None,
    ):
        if lock_reason == "built":
            right_col = "Built"
        elif not available and lock_reason:
            right_col = lock_reason
        elif info.cost > 0:
            right_col = format_currency(info.cost)
        else:
            right_col = "Free"
        label = f"{info.display_name:16} {right_col:>12}"
        super().__init__(Label(label), disabled=not available)
        self.biome = biome
        self.info = info
        self.available = available
        self.lock_reason = lock_reason


def _missing_tier(biome: BiomeType, covered_tiers: set[int]) -> int | None:
    """Return the lowest tier < biome's tier that isn't covered, or None."""
    required = BIOMES[biome].required_tier
    for tier in range(1, required):
        if tier not in covered_tiers:
            return tier
    return None


class BiomeSelectScreen(ModalScreen[BiomeType | None]):
    """Modal for selecting a biome when adding a new room."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Select"),
    ]

    DEFAULT_CSS = """
    BiomeSelectScreen {
        align: center middle;
    }

    #biome-dialog {
        width: 64;
        height: 24;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #biome-title {
        height: 1;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #biome-list {
        height: 1fr;
        border: solid $primary;
    }

    #biome-detail {
        height: 6;
        padding: 1;
        border: solid $secondary;
        margin-top: 1;
    }

    BiomeListItem:disabled {
        opacity: 40%;
    }
    """

    def __init__(
        self,
        farm_tier: int,
        existing_biomes: set[BiomeType],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.farm_tier = farm_tier
        self.existing_biomes = existing_biomes
        self._covered_tiers = {
            BIOMES[biome].required_tier for biome in existing_biomes
        }

    def compose(self) -> ComposeResult:
        with Container(id="biome-dialog"):
            yield Static("Select a Biome for New Room", id="biome-title")
            yield ListView(id="biome-list")
            yield Static("Select a biome to see details", id="biome-detail")
        yield Footer()

    def on_mount(self) -> None:
        list_view = self.query_one("#biome-list", ListView)
        for biome_type in BiomeType:
            info = BIOMES[biome_type]
            available, lock_reason = self._biome_status(biome_type, info)
            list_view.append(BiomeListItem(biome_type, info, available, lock_reason))
        list_view.focus()

    def _biome_status(
        self, biome: BiomeType, info: BiomeInfo
    ) -> tuple[bool, str | None]:
        """Return (available, lock_reason) for a biome."""
        if biome in self.existing_biomes:
            return False, "built"
        if info.required_tier > self.farm_tier:
            return False, f"tier {info.required_tier}"
        missing = _missing_tier(biome, self._covered_tiers)
        if missing is not None:
            return False, f"build a tier {missing} biome first"
        return True, None

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, BiomeListItem):
            self._update_detail(event.item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, BiomeListItem):
            self._try_select(event.item)

    def _update_detail(self, item: BiomeListItem) -> None:
        detail = self.query_one("#biome-detail", Static)
        info = item.info
        cost_str = format_currency(info.cost) if info.cost > 0 else "Free"

        if not item.available and item.lock_reason:
            status_str = item.lock_reason.capitalize()
        else:
            status_str = "Available"

        boosts = []
        for locus, rate in info.mutation_boost_loci.items():
            locus_name = locus.replace("_locus", "").upper()
            boosts.append(f"{locus_name} +{rate:.1%}")
        boost_str = ", ".join(boosts) if boosts else "None"

        detail.update(
            f"{info.display_name} - {cost_str} ({status_str})\n"
            f"{info.description}\n"
            f"Mutation boosts: {boost_str}\n"
            f"Happiness bonus: +{info.happiness_bonus:.1f}/hr"
        )

    def _try_select(self, item: BiomeListItem) -> None:
        if not item.available:
            reason = (item.lock_reason or "unavailable").capitalize()
            self.notify(f"Cannot select: {reason}", severity="error")
            return
        self.dismiss(item.biome)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        list_view = self.query_one("#biome-list", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, BiomeListItem):
            self._try_select(list_view.highlighted_child)
