"""Biome selection screen for adding new rooms."""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import Static, Label, ListView, ListItem, Footer

from big_pig_farm.economy.currency import format_currency
from big_pig_farm.entities.biomes import BiomeType, BiomeInfo, BIOMES


class BiomeListItem(ListItem):
    """Widget representing a biome option."""

    def __init__(self, biome: BiomeType, info: BiomeInfo, unlocked: bool):
        lock_str = "" if unlocked else " [locked]"
        cost_str = format_currency(info.cost) if info.cost > 0 else "Free"
        label = f"{info.display_name:16} {cost_str:>8}{lock_str}"
        super().__init__(Label(label))
        self.biome = biome
        self.info = info
        self.unlocked = unlocked


class BiomeSelectScreen(ModalScreen[Optional[BiomeType]]):
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
    """

    def __init__(self, farm_tier: int, **kwargs):
        super().__init__(**kwargs)
        self.farm_tier = farm_tier

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
            unlocked = info.required_tier <= self.farm_tier
            list_view.append(BiomeListItem(biome_type, info, unlocked))
        list_view.focus()

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
        unlock_str = f"Tier {info.required_tier}" if not item.unlocked else "Unlocked"

        boosts = []
        for locus, rate in info.mutation_boost_loci.items():
            locus_name = locus.replace("_locus", "").upper()
            boosts.append(f"{locus_name} +{rate:.1%}")
        boost_str = ", ".join(boosts) if boosts else "None"

        detail.update(
            f"{info.display_name} - {cost_str} ({unlock_str})\n"
            f"{info.description}\n"
            f"Mutation boosts: {boost_str}\n"
            f"Happiness bonus: +{info.happiness_bonus:.1f}/hr"
        )

    def _try_select(self, item: BiomeListItem) -> None:
        if not item.unlocked:
            self.notify(f"Requires Tier {item.info.required_tier}!", severity="error")
            return
        self.dismiss(item.biome)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        list_view = self.query_one("#biome-list", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, BiomeListItem):
            self._try_select(list_view.highlighted_child)
