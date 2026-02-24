"""Main Textual Application class for Big Pig Farm."""

from pathlib import Path
from uuid import UUID

from textual import events
from textual._xterm_parser import XTermParser
from textual.app import App

from big_pig_farm.data.names import generate_unique_name
from big_pig_farm.economy.currency import format_currency
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.entities.pigdex import phenotype_key
from big_pig_farm.game.debug_logger import DebugLogger
from big_pig_farm.game.engine import GameEngine
from big_pig_farm.game.save_manager_v2 import CombinedSaveManager
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.behavior_controller import BehaviorController
from big_pig_farm.simulation.birth import register_pig_in_pigdex
from big_pig_farm.simulation.runner import SimulationRunner
from big_pig_farm.ui.screens.main_game import MainGameScreen

# ---------------------------------------------------------------------------
# Patch Textual's xterm parser to support horizontal trackpad scrolling.
#
# SGR mouse protocol scroll button codes:
#   64 = scroll up,   65 = scroll down   (bit 1 clear → vertical)
#   66 = scroll left,  67 = scroll right  (bit 1 set   → horizontal)
#
# Textual only checks bit 0 (up vs down) and ignores bit 1 entirely, so
# horizontal trackpad scrolling arrives as vertical.  We fix this by
# setting the shift flag when bit 1 is set, which our FarmView scroll
# handlers already interpret as "pan horizontally".
# ---------------------------------------------------------------------------
_original_parse_mouse_code = XTermParser.parse_mouse_code


def _patched_parse_mouse_code(self: XTermParser, code: str) -> events.Event | None:
    event = _original_parse_mouse_code(self, code)
    if event is None:
        return None
    if isinstance(event, events.MouseScrollUp | events.MouseScrollDown):
        # Re-parse the button code to check bit 1 (horizontal flag)
        sgr_match = self._re_sgr_mouse.match(code)
        if sgr_match:
            buttons = int(sgr_match.group(1))
            if buttons & 2:  # horizontal scroll
                # Reconstruct the event with shift=True
                event = type(event)(
                    event.x, event.y, event.delta_x, event.delta_y,
                    event.button, True, event.meta, event.ctrl,
                    screen_x=event.screen_x, screen_y=event.screen_y,
                )
    return event


XTermParser.parse_mouse_code = _patched_parse_mouse_code  # type: ignore[assignment]


class BigPigFarmApp(App):
    """The main Big Pig Farm application."""

    TITLE = "Big Pig Farm"
    SUB_TITLE = "A Guinea Pig Idle Simulation"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def __init__(self, debug: bool = False):
        super().__init__()
        self.debug_mode = debug
        self.save_manager = CombinedSaveManager()
        self.pig_to_follow: GuineaPig | None = None  # Set by pig list/detail screens

        # Try to load existing save
        loaded_state = self.save_manager.load()
        if loaded_state:
            self.state = loaded_state
            # Backfill pigdex from existing pigs (for saves that predate pigdex)
            for pig in self.state.get_pigs_list():
                key = phenotype_key(pig.phenotype)
                self.state.pigdex.register_phenotype(key, self.state.game_time.day)
            self.state.log_event("Welcome back to Big Pig Farm!", "info")
        else:
            self.state = GameState()
            self._setup_new_game()

        self.engine = GameEngine(self.state)
        self.behavior_controller = BehaviorController(self.state)

        # Debug logging
        debug_logger: DebugLogger | None = None
        if debug:
            log_path = Path.home() / ".big_pig_farm" / "debug_log.txt"
            debug_logger = DebugLogger(log_path)
            self.state.log_event("Debug mode enabled", "info")

        # Simulation runner orchestrates all per-tick systems
        self.runner = SimulationRunner(
            state=self.state,
            behavior_controller=self.behavior_controller,
            save_manager=self.save_manager,
            debug_logger=debug_logger,
            on_pig_sold=self._on_pig_auto_sold,
            on_pregnancy=self._on_pregnancy,
            on_birth=self._on_birth,
        )

    def _setup_new_game(self) -> None:
        """Set up a new game with starting resources."""
        existing_names: set[str] = set()

        # Create starting guinea pigs
        for gender in [Gender.MALE, Gender.FEMALE]:
            name = generate_unique_name(existing_names, gender=gender.value)
            existing_names.add(name)

            # Random starting position
            pos = self.state.farm.find_random_walkable()
            if pos:
                position = Position(x=float(pos[0]), y=float(pos[1]))
            else:
                position = Position(x=5.0, y=5.0)

            pig = GuineaPig.create(
                name=name,
                gender=gender,
                position=position,
                age_days=5.0,  # Start as adults
            )
            self.state.add_guinea_pig(pig)

        # Register starter pigs in pigdex
        for pig in self.state.get_pigs_list():
            register_pig_in_pigdex(self.state, pig)

        # Place starting facilities
        food_bowl = Facility.create(FacilityType.FOOD_BOWL, 5, 3)
        water_bottle = Facility.create(FacilityType.WATER_BOTTLE, 10, 3)
        hideout = Facility.create(FacilityType.HIDEOUT, 14, 3)

        self.state.add_facility(food_bowl)
        self.state.add_facility(water_bottle)
        self.state.add_facility(hideout)

        # Log starting message
        self.state.log_event("Welcome to Big Pig Farm!", "info")

    def on_mount(self) -> None:
        """Handle app mount."""
        # Push the main game screen
        self.push_screen(MainGameScreen(self.state))

        # Register simulation callbacks
        self.engine.register_tick_callback(self.runner.tick)

        # Start the game engine
        self.run_worker(self._start_engine())

    async def _start_engine(self) -> None:
        """Start the game engine in a worker."""
        await self.engine.start()

    def on_unmount(self) -> None:
        """Handle app unmount."""
        self.run_worker(self._stop_engine())

    async def _stop_engine(self) -> None:
        """Stop the game engine."""
        await self.engine.stop()
        # Save on exit
        self.save_manager.save(self.state)

    def _on_pig_auto_sold(self, pig_name: str, total: int, pig_id: UUID) -> None:
        """Callback when a pig is auto-sold by the simulation runner."""
        self.notify(f"{pig_name} grew up and was auto-sold for {format_currency(total)}!")

    def _on_pregnancy(self, male_name: str, female_name: str) -> None:
        """Callback when a courtship completes and pregnancy begins."""
        self.notify(f"{male_name} and {female_name} are expecting!")

    def _on_birth(self, message: str) -> None:
        """Callback when a pig gives birth."""
        self.notify(message)
