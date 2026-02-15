"""Simulation tick orchestration — runs all game systems each tick."""

from typing import Callable, Optional, Protocol
from uuid import UUID

from big_pig_farm.data.config import NEEDS
from big_pig_farm.game.state import GameState
from big_pig_farm.game.debug_logger import DebugLogger
from big_pig_farm.simulation.behavior import BehaviorController
from big_pig_farm.simulation.needs import update_all_needs, precompute_nearby_counts
from big_pig_farm.simulation.breeding import (
    advance_pregnancies,
    age_all_pigs,
    check_breeding_opportunities,
    register_pig_in_pigdex,
    sell_marked_adults,
    cull_surplus_breeders,
)
from big_pig_farm.economy.contracts import generate_contracts


class SaveProtocol(Protocol):
    """Minimal interface for save managers used by SimulationRunner."""

    def save(self, state: GameState) -> None: ...


class SimulationRunner:
    """Orchestrates all per-tick game systems in the correct order."""

    def __init__(
        self,
        state: GameState,
        behavior_controller: BehaviorController,
        save_manager: SaveProtocol,
        debug_logger: Optional[DebugLogger] = None,
        on_pig_sold: Optional[Callable[[str, int, UUID], None]] = None,
    ):
        self.state = state
        self.behavior_controller = behavior_controller
        self.save_manager = save_manager
        self.debug_logger = debug_logger
        self.on_pig_sold = on_pig_sold
        self._save_counter = 0

    def tick(self, delta_seconds: float) -> None:
        """Process one simulation tick. delta_seconds is already speed-scaled."""
        state = self.state
        controller = self.behavior_controller

        # 1. Update all guinea pig needs
        game_minutes = delta_seconds
        pigs = state.get_pigs_list()
        nearby_counts = precompute_nearby_counts(pigs, NEEDS.SOCIAL_RADIUS)
        for pig in pigs:
            update_all_needs(pig, game_minutes, state, nearby_count=nearby_counts.get(pig.id, 0))

        # 2. Rebuild spatial grid for fast collision/blocking checks
        controller.collision.rebuild_spatial_grid()

        # 3. Update behaviors
        for pig in state.get_pigs_list():
            controller.update(pig, delta_seconds)

        # 4. Separate any overlapping pigs
        controller.separate_overlapping_pigs()

        # 5. Advance pregnancies
        game_hours = game_minutes / 60.0
        advance_pregnancies(state, game_hours)

        # 6. Age pigs and cleanup controller state for deaths
        deaths = age_all_pigs(state, game_hours)
        for dead_pig in deaths:
            controller.cleanup_dead_pig(dead_pig.id)

        # 7. Cull surplus breeders
        cull_surplus_breeders(state)

        # 8. Auto-sell marked pigs that reached adulthood
        sold_pigs = sell_marked_adults(state)
        for pig_name, total, pig_id in sold_pigs:
            controller.cleanup_dead_pig(pig_id)
            if self.on_pig_sold:
                self.on_pig_sold(pig_name, total, pig_id)

        # 9. Check for breeding
        check_breeding_opportunities(state)

        # 10. Check contract refresh/expiry
        game_day = state.game_time.day
        board = state.contract_board
        board.check_expiry(game_day)
        if board.needs_refresh(game_day) or (not board.active_contracts and board.last_refresh_day == 0):
            player_biomes = [a.biome for a in state.farm.areas]
            new_contracts = generate_contracts(state.farm.tier, game_day, player_biomes)
            board.active_contracts.extend(new_contracts)
            board.last_refresh_day = game_day

        # 11. Debug logging
        if self.debug_logger:
            self.debug_logger.tick(state, controller)

        # 12. Auto-save every ~30 seconds (300 ticks)
        self._save_counter += 1
        if self._save_counter >= 300:
            self._save_counter = 0
            self.save_manager.save(state)
