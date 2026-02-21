"""Simulation tick orchestration — runs all game systems each tick."""

import time
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from big_pig_farm.data.config import NEEDS
from big_pig_farm.economy.contracts import generate_contracts
from big_pig_farm.game.debug_logger import DebugLogger
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.behavior import BehaviorController
from big_pig_farm.simulation.birth import advance_pregnancies, age_all_pigs
from big_pig_farm.simulation.breeding import check_breeding_opportunities, start_pregnancy_from_courtship
from big_pig_farm.simulation.culling import cull_surplus_breeders, sell_marked_adults
from big_pig_farm.simulation.needs import precompute_nearby_counts, update_all_needs


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
        debug_logger: DebugLogger | None = None,
        on_pig_sold: Callable[[str, int, UUID], None] | None = None,
        on_pregnancy: Callable[[str, str], None] | None = None,
        on_birth: Callable[[str], None] | None = None,
    ):
        self.state = state
        self.behavior_controller = behavior_controller
        self.save_manager = save_manager
        self.debug_logger = debug_logger
        self.on_pig_sold = on_pig_sold
        self.on_pregnancy = on_pregnancy
        self.on_birth = on_birth
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

        # 3b. Process completed courtships → start pregnancies
        for male_id, female_id in controller.completed_courtships:
            male = state.get_guinea_pig(male_id)
            female = state.get_guinea_pig(female_id)
            if male and female:
                start_pregnancy_from_courtship(male, female, state)
                if self.on_pregnancy:
                    self.on_pregnancy(male.name, female.name)
        controller.completed_courtships.clear()

        # 4. Separate any overlapping pigs
        if profiling:
            phase_start = time.perf_counter()
        controller.separate_overlapping_pigs()

        # 4b. Rescue pigs pushed onto non-walkable cells by collision
        controller.rescue_non_walkable_pigs(pigs)
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
        events_before = len(state.events)
        check_breeding_opportunities(state)

        # Notify on births
        if self.on_birth:
            for event in state.events[events_before:]:
                if event.event_type == "birth" and "gave birth" in event.message:
                    self.on_birth(event.message)

        # 10. Check contract refresh/expiry
        game_day = state.game_time.day
        board = state.contract_board
        board.check_expiry(game_day)
        if board.needs_refresh(game_day) or (not board.active_contracts and board.last_refresh_day == 0):
            player_biomes = [a.biome for a in state.farm.areas]
            new_contracts = generate_contracts(state.farm_tier, game_day, player_biomes)
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
