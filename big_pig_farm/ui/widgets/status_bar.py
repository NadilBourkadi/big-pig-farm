"""Status bar widget showing resources and time."""

from textual.reactive import reactive
from textual.widgets import Static

from big_pig_farm.data.config import BREEDING, SPEED_DISPLAY, GameSpeed
from big_pig_farm.economy.currency import format_currency
from big_pig_farm.entities.facilities import FacilityType


class StatusBar(Static):
    """Top status bar showing game resources and time (2 lines)."""

    day: reactive[int] = reactive(1)
    time_display: reactive[str] = reactive("8:00 AM")
    time_of_day: reactive[str] = reactive("Morning")
    money: reactive[int] = reactive(100)
    pig_count: reactive[int] = reactive(0)
    capacity: reactive[int] = reactive(4)
    farm_tier: reactive[int] = reactive(1)
    food_level: reactive[int] = reactive(100)
    water_level: reactive[int] = reactive(100)
    is_paused: reactive[bool] = reactive(False)
    speed: reactive[int] = reactive(1)
    warning: reactive[str] = reactive("")
    edit_mode: reactive[bool] = reactive(False)
    debug_tps: reactive[float] = reactive(0.0)

    DEFAULT_CSS = """
    StatusBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """

    def render(self) -> str:
        """Render the single-line status bar."""
        # Pause/speed indicator
        if self.is_paused:
            speed_str = "\u23f8 PAUSED"
        elif self.speed > GameSpeed.NORMAL.value:
            speed_str = f"\u25b6\u25b6 {SPEED_DISPLAY.get(GameSpeed(self.speed), f'{self.speed}x')}"
        else:
            speed_str = "\u25b6"

        parts = [
            f"Day {self.day}",
            f"T{self.farm_tier}",
            format_currency(self.money),
            f"\U0001f439 {self.pig_count}/{self.capacity}",
            f"\U0001f957 {self.food_level}%",
            f"\U0001f4a7 {self.water_level}%",
            speed_str,
        ]

        if self.warning:
            parts.append(f"\u26a0 {self.warning}")

        if self.debug_tps > 0:
            parts.append(f"{self.debug_tps:.1f} tps")

        if self.edit_mode:
            parts.append("[bold reverse] EDIT [/]")

        return " \u2502 ".join(parts)

    _facility_frame_counter: int = 0
    _FACILITY_QUERY_INTERVAL: int = 7  # recompute every ~1s at 7 Hz

    def update_from_state(self, state, tps: float = 0.0) -> None:
        """Update all values from game state."""
        self.debug_tps = tps
        self.day = state.game_time.day
        self.time_display = state.game_time.display_time
        self.time_of_day = state.game_time.time_of_day
        self.money = state.money
        self.pig_count = state.pig_count
        self.capacity = state.capacity
        self.farm_tier = state.farm_tier
        self.is_paused = state.is_paused
        self.speed = state.speed.value
        self._speed_enum = state.speed

        # Recompute facility levels and population warning only every ~1s
        self._facility_frame_counter += 1
        if self._facility_frame_counter >= self._FACILITY_QUERY_INTERVAL:
            self._facility_frame_counter = 0
            self._recompute_facility_levels(state)
            self._recompute_population_warning(state)

    def force_refresh_facilities(self, state) -> None:
        """Force immediate facility recompute (call after player actions)."""
        self._facility_frame_counter = 0
        self._recompute_facility_levels(state)

    def _recompute_facility_levels(self, state) -> None:
        """Query facilities and update food/water percentages."""
        food_facilities = (
            state.get_facilities_by_type(FacilityType.FOOD_BOWL)
            + state.get_facilities_by_type(FacilityType.HAY_RACK)
        )
        if food_facilities:
            avg_food = sum(f.fill_percentage for f in food_facilities) / len(food_facilities)
            self.food_level = int(avg_food)
        else:
            self.food_level = 0

        water_facilities = state.get_facilities_by_type(FacilityType.WATER_BOTTLE)
        if water_facilities:
            avg_water = sum(f.fill_percentage for f in water_facilities) / len(water_facilities)
            self.water_level = int(avg_water)
        else:
            self.water_level = 0

    def _recompute_population_warning(self, state) -> None:
        """Check breeding population and update warning."""
        if state.breeding_program.enabled:
            adults = [p for p in state.get_pigs_list() if not p.is_baby]
            if len(adults) <= BREEDING.MIN_BREEDING_POPULATION:
                self.warning = "LOW POP"
            else:
                self.warning = ""
        else:
            self.warning = ""
