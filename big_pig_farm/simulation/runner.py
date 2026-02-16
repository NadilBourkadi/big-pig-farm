"""Simulation tick orchestration — runs all game systems each tick."""

import time
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
        tick_start = time.perf_counter()
        state = self.state
        controller = self.behavior_controller
        profiling = self.debug_logger is not None

        # 1. Rebuild spatial grid first — used by needs, behaviors, and collision
        controller.collision.rebuild_spatial_grid()

        # 2. Update all guinea pig needs
        if profiling:
            phase_start = time.perf_counter()
        game_minutes = delta_seconds
        pigs = state.get_pigs_list()
        nearby_counts = precompute_nearby_counts(pigs, NEEDS.SOCIAL_RADIUS, controller.collision.spatial_grid)
        for pig in pigs:
            update_all_needs(pig, game_minutes, state, nearby_count=nearby_counts.get(pig.id, 0))
        if profiling:
            needs_ms = (time.perf_counter() - phase_start) * 1000.0

        # 3. Update behaviors
        if profiling:
            phase_start = time.perf_counter()
        for pig in pigs:
            controller.update(pig, delta_seconds)
        if profiling:
            behavior_ms = (time.perf_counter() - phase_start) * 1000.0

        # 4. Separate any overlapping pigs
        if profiling:
            phase_start = time.perf_counter()
        controller.separate_overlapping_pigs()
        if profiling:
            collision_ms = (time.perf_counter() - phase_start) * 1000.0

        # 5. Advance pregnancies
        if profiling:
            phase_start = time.perf_counter()
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
        if profiling:
            breeding_ms = (time.perf_counter() - phase_start) * 1000.0

        # 11. Debug logging
        if profiling:
            tick_ms = (time.perf_counter() - tick_start) * 1000.0
            phase_times = {
                "needs": needs_ms,
                "behavior": behavior_ms,
                "collision": collision_ms,
                "breeding": breeding_ms,
            }
            self.debug_logger.tick(state, controller, tick_ms, phase_times)

        # 12. Auto-save every ~30 seconds (300 ticks)
        self._save_counter += 1
        if self._save_counter >= 300:
            self._save_counter = 0
            self.save_manager.save(state)
