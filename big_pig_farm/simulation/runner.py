"""Simulation tick orchestration — runs all game systems each tick."""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from big_pig_farm.data.config import NEEDS
from big_pig_farm.economy.contracts import generate_contracts
from big_pig_farm.game.debug_logger import DebugLogger
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.acclimation import update_acclimation
from big_pig_farm.simulation.auto_resources import tick_aoe_facilities, tick_auto_resources, tick_veggie_gardens
from big_pig_farm.simulation.behavior_controller import BehaviorController
from big_pig_farm.simulation.birth import advance_pregnancies, age_all_pigs
from big_pig_farm.simulation.breeding import check_breeding_opportunities, start_pregnancy_from_courtship
from big_pig_farm.simulation.culling import cull_surplus_breeders, sell_marked_adults
from big_pig_farm.simulation.needs import precompute_nearby_counts, update_all_needs

logger = logging.getLogger(__name__)


class SaveProtocol(Protocol):
    """Minimal interface for save managers used by SimulationRunner."""

    def save(self, state: GameState) -> None: ...
    def save_blob(self, json_blob: str) -> None: ...


class SimulationRunner:
    """Orchestrates all per-tick game systems in the correct order."""

    def __init__(
        self,
        state: GameState,
        behavior_controller: BehaviorController,
        save_manager: SaveProtocol,
        debug_logger: DebugLogger | None = None,
        on_pig_sold: Callable[[str, int, int, UUID], None] | None = None,
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
        self._save_thread: threading.Thread | None = None
        # Rolling TPS measurement (last 50 tick timestamps)
        self._tick_timestamps: deque[float] = deque(maxlen=50)
        self.current_tps: float = 0.0
        # Throttle expensive O(m*f) breeding checks to every 10 ticks (~1s)
        self._breeding_check_counter = 0
        self._breeding_check_interval = 10
        # Farm Bell perk: throttle to once per game-hour
        self._last_farm_bell_hour: int = -1

    def tick(self, delta_seconds: float) -> None:
        """Process one simulation tick. delta_seconds is already speed-scaled."""
        tick_start = time.perf_counter()
        self._tick_timestamps.append(tick_start)
        if len(self._tick_timestamps) >= 2:
            elapsed = self._tick_timestamps[-1] - self._tick_timestamps[0]
            if elapsed > 0:
                self.current_tps = (len(self._tick_timestamps) - 1) / elapsed
        state = self.state
        controller = self.behavior_controller
        profiling = self.debug_logger is not None

        # 1. Rebuild spatial grid first — used by needs, behaviors, and collision
        controller.collision.rebuild_spatial_grid()

        # 1b. Rebuild per-area population/capacity caches for overcrowding logic
        controller.facility_manager.update_area_populations()

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

        # 2a. Farm Bell perk: notify when any pig is critically hungry/thirsty
        if state.has_upgrade("farm_bell"):
            current_hour = state.game_time.day * 24 + state.game_time.hour
            if current_hour != self._last_farm_bell_hour:
                critical_pigs = [
                    pig for pig in pigs
                    if pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
                    or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD
                ]
                if critical_pigs:
                    self._last_farm_bell_hour = current_hour
                    names = ", ".join(p.name for p in critical_pigs[:3])
                    suffix = f" (+{len(critical_pigs) - 3} more)" if len(critical_pigs) > 3 else ""
                    state.log_event(
                        f"Farm Bell: {names}{suffix} need food/water!",
                        event_type="farm_bell",
                    )

        # 2b. Automatic resource systems (drip, auto-feeders, veggie gardens)
        game_hours = game_minutes / 60.0
        tick_auto_resources(state, game_hours)
        tick_veggie_gardens(state, game_hours)
        tick_aoe_facilities(state, game_hours)

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

        # 5. Biome acclimation — pigs adopt a new biome after extended stays
        game_hours = game_minutes / 60.0
        farm = state.farm
        for pig in pigs:
            if pig.preferred_biome is None:
                continue
            # O(1) via area dict instead of grid cell lookup
            biome_str: str | None = None
            if pig.current_area_id:
                area = farm.get_area_by_id(pig.current_area_id)
                if area:
                    biome_str = area.biome.value
            if biome_str == pig.preferred_biome and pig.acclimation_timer == 0.0 and pig.acclimating_biome is None:
                continue  # Home biome with no active timer — nothing to do
            old_biome = pig.preferred_biome
            update_acclimation(pig, biome_str, game_hours)
            if pig.preferred_biome != old_biome:
                state.log_event(
                    f"{pig.name} acclimated to the {pig.preferred_biome} biome!",
                    event_type="acclimation",
                )

        # 6. Advance pregnancies
        if profiling:
            phase_start = time.perf_counter()
        advance_pregnancies(state, game_hours)

        # 7. Age pigs and cleanup controller state for deaths
        deaths = age_all_pigs(state, game_hours)
        for dead_pig in deaths:
            controller.cleanup_dead_pig(dead_pig.id)

        # 8. Cull surplus breeders
        cull_surplus_breeders(state)

        # 9. Auto-sell marked pigs that reached adulthood
        sold_pigs = sell_marked_adults(state)
        for pig_name, total, contract_bonus, pig_id in sold_pigs:
            controller.cleanup_dead_pig(pig_id)
            if self.on_pig_sold:
                self.on_pig_sold(pig_name, total, contract_bonus, pig_id)

        # 10. Check for breeding (throttle expensive O(m*f) scans)
        self._breeding_check_counter += 1
        run_expensive = self._breeding_check_counter >= self._breeding_check_interval
        if run_expensive:
            self._breeding_check_counter = 0
        events_before = len(state.events)
        check_breeding_opportunities(state, run_expensive=run_expensive)

        # Notify on births
        if self.on_birth:
            for event in state.events[events_before:]:
                if event.event_type == "birth" and "gave birth" in event.message:
                    self.on_birth(event.message)

        # 11. Check contract refresh/expiry
        game_day = state.game_time.day
        board = state.contract_board
        board.check_expiry(game_day)
        if board.needs_refresh(game_day) or (not board.active_contracts and board.last_refresh_day == 0):
            player_biomes = [a.biome for a in state.farm.areas]
            new_contracts = generate_contracts(state.farm_tier, game_day, player_biomes, game_state=state)
            board.active_contracts.extend(new_contracts)
            board.last_refresh_day = game_day
        if profiling:
            breeding_ms = (time.perf_counter() - phase_start) * 1000.0

        # 12. Debug logging
        if profiling:
            tick_ms = (time.perf_counter() - tick_start) * 1000.0
            phase_times = {
                "needs": needs_ms,
                "behavior": behavior_ms,
                "collision": collision_ms,
                "breeding": breeding_ms,
            }
            assert self.debug_logger is not None
            self.debug_logger.tick(state, controller, tick_ms, phase_times)

        # 13. Auto-save every ~30 seconds (300 ticks)
        self._save_counter += 1
        if self._save_counter >= 300:
            self._save_counter = 0
            self._background_save(state)

    def _background_save(self, state: GameState) -> None:
        """Serialize state on main thread, offload I/O to a daemon thread.

        Skips if the previous save is still running. Serialization happens
        within tick(), which is synchronous — no state mutations can occur
        until model_dump_json() completes and the method returns.
        """
        if self._save_thread is not None and self._save_thread.is_alive():
            logger.warning("Auto-save skipped: previous save still in progress")
            return

        json_blob = state.model_dump_json()
        save_manager = self.save_manager

        def _write_save() -> None:
            try:
                save_manager.save_blob(json_blob)
            except Exception:
                logger.exception("Background auto-save failed")

        self._save_thread = threading.Thread(target=_write_save, daemon=True)
        self._save_thread.start()
