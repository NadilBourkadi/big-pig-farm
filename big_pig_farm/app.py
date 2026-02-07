"""Main Textual Application class for Big Pig Farm."""

from pathlib import Path

from textual.app import App

from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.entities.pigdex import phenotype_key
from big_pig_farm.data.names import generate_unique_name
from big_pig_farm.game.state import GameState
from big_pig_farm.game.engine import GameEngine
from big_pig_farm.game.save_manager import SaveManager
from big_pig_farm.game.debug_logger import DebugLogger
from big_pig_farm.simulation.behavior import BehaviorController
from big_pig_farm.simulation.needs import update_all_needs
from big_pig_farm.simulation.breeding import advance_pregnancies, age_all_pigs, check_breeding_opportunities, register_pig_in_pigdex, sell_marked_adults
from big_pig_farm.economy.contracts import generate_contracts
from big_pig_farm.ui.screens.main_game import MainGameScreen


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
        self.save_manager = SaveManager()
        self._save_counter = 0
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
        self.debug_logger: DebugLogger | None = None
        if debug:
            log_path = Path.home() / ".big_pig_farm" / "debug_log.txt"
            self.debug_logger = DebugLogger(log_path)
            self.state.log_event("Debug mode enabled", "info")

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
        self.engine.register_tick_callback(self._simulation_tick)

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

    def _simulation_tick(self, delta_seconds: float) -> None:
        """Process one simulation tick."""
        # delta_seconds is already speed-scaled from the engine
        # Convert to game minutes (1 real second = 1 game minute at 1x)
        game_minutes = delta_seconds

        # Update all guinea pig needs
        for pig in self.state.get_pigs_list():
            update_all_needs(pig, game_minutes, self.state)

        # Update behaviors
        for pig in self.state.get_pigs_list():
            self.behavior_controller.update(pig, delta_seconds)

        # Separate any overlapping pigs
        self.behavior_controller.separate_overlapping_pigs()

        # Advance pregnancies
        game_hours = game_minutes / 60.0
        advance_pregnancies(self.state, game_hours)

        # Age pigs and cleanup controller state for deaths
        deaths = age_all_pigs(self.state, game_hours)
        for dead_pig in deaths:
            self.behavior_controller.cleanup_dead_pig(dead_pig.id)

        # Auto-sell marked pigs that reached adulthood
        sold_pigs = sell_marked_adults(self.state)
        for pig_name, total, pig_id in sold_pigs:
            self.behavior_controller.cleanup_dead_pig(pig_id)
            self.notify(f"{pig_name} grew up and was auto-sold for ${total}!")

        # Check for breeding
        check_breeding_opportunities(self.state)

        # Check contract refresh/expiry
        game_day = self.state.game_time.day
        board = self.state.contract_board
        board.check_expiry(game_day)
        if board.needs_refresh(game_day) or (not board.active_contracts and board.last_refresh_day == 0):
            new_contracts = generate_contracts(self.state.farm.tier, game_day)
            board.active_contracts.extend(new_contracts)
            board.last_refresh_day = game_day

        # Debug logging
        if self.debug_logger:
            self.debug_logger.tick(self.state, self.behavior_controller)

        # Auto-save every ~30 seconds (300 ticks)
        self._save_counter += 1
        if self._save_counter >= 300:
            self._save_counter = 0
            self.save_manager.save(self.state)
