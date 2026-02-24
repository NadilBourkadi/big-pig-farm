"""BehaviorController — orchestrates guinea pig AI across decision, seeking, and movement."""

import random
from typing import TYPE_CHECKING
from uuid import UUID

from big_pig_farm.data.config import BEHAVIOR, NEEDS, SIMULATION
from big_pig_farm.entities.guinea_pig import BehaviorState, GuineaPig
from big_pig_farm.simulation.behavior_decision import is_content, make_decision
from big_pig_farm.simulation.behavior_movement import (
    clamp_to_bounds,
    rescue_non_walkable_pigs,
    rescue_to_walkable,
    update_movement,
)
from big_pig_farm.simulation.breeding import clear_courtship
from big_pig_farm.simulation.collision import CollisionHandler
from big_pig_farm.simulation.facility_manager import FacilityManager

if TYPE_CHECKING:
    from big_pig_farm.game.state import GameState


class BehaviorController:
    """Controls guinea pig behavior and decision making."""

    def __init__(self, game_state: "GameState"):
        self.game_state = game_state
        self.collision = CollisionHandler(game_state)
        self.facility_manager = FacilityManager(game_state, self.collision)
        self._decision_timers: dict[UUID, float] = {}
        self._blocked_timers: dict[UUID, float] = {}  # Track how long pigs have been blocked
        self._stuck_positions: dict[UUID, tuple[int, int]] = {}  # Last known grid cell while blocked
        self._stuck_timers: dict[UUID, float] = {}  # Time stuck at same grid cell (not reset by facility switches)
        # Unreachable facility backoff: {pig_id: {need_type: remaining_cycles}}
        # Prevents pigs from re-running the full facility lookup + A* every 2s
        # when no reachable facility of that type exists.
        self._unreachable_needs: dict[UUID, dict[str, int]] = {}
        # Track grid generation to clear unreachable backoff when the
        # walkable grid changes (facility built/removed/refilled).
        self._last_grid_gen: int = 0
        # Courtship pairs that completed the together phase — consumed by runner
        self.completed_courtships: list[tuple[UUID, UUID]] = []

    def cleanup_dead_pig(self, pig_id: UUID) -> None:
        """Remove tracking state for a pig that is no longer alive."""
        self._decision_timers.pop(pig_id, None)
        self._blocked_timers.pop(pig_id, None)
        self._stuck_positions.pop(pig_id, None)
        self._stuck_timers.pop(pig_id, None)
        self._unreachable_needs.pop(pig_id, None)
        self.facility_manager.cleanup_pig(pig_id)
        # Clear partner's courtship if this pig was courting
        for pig in self.game_state.get_pigs_list():
            if pig.courting_partner_id == pig_id:
                clear_courtship(pig)

    def reset_all_tracking(self) -> None:
        """Clear all internal tracking state for every pig.

        Used after auto-arrange repositions facilities, so pigs
        start fresh with no stale blocked/failed/stuck state.
        """
        self._decision_timers.clear()
        self._blocked_timers.clear()
        self._stuck_positions.clear()
        self._stuck_timers.clear()
        self._unreachable_needs.clear()
        self.facility_manager.reset_all()

    def separate_overlapping_pigs(self) -> None:
        """Delegate to collision handler."""
        self.collision.separate_overlapping_pigs()

    def update(self, pig: GuineaPig, delta_seconds: float) -> None:
        """Update behavior for a guinea pig."""
        # Clear unreachable backoff when the walkable grid changes
        # (facility built/removed) so pigs notice new facilities immediately
        grid_gen = self.game_state.farm.grid_generation
        if grid_gen != self._last_grid_gen:
            self._unreachable_needs.clear()
            self._last_grid_gen = grid_gen

        # Check if it's time to make a new decision
        timer = self._decision_timers.get(pig.id, random.uniform(0, 1))  # Stagger initial timers
        timer += delta_seconds

        # Emergency override: critical hunger/thirst fires immediately
        if (pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
                or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD):
            interval = 0.0
        elif is_content(pig):
            interval = BEHAVIOR.CONTENT_DECISION_INTERVAL
        else:
            interval = SIMULATION.DECISION_INTERVAL_SECONDS

        if timer >= interval:
            make_decision(self, pig)
            # Add small random offset to prevent synchronized decisions
            timer = random.uniform(0, SIMULATION.DECISION_INTERVAL_SECONDS / 4)

        self._decision_timers[pig.id] = timer

        # Update movement
        update_movement(self, pig, delta_seconds)

        # Clamp position inside walkable bounds (walls + buffer)
        clamp_to_bounds(self, pig)

        # Rescue pigs stuck on non-walkable cells (e.g. pushed there by collision)
        farm = self.game_state.farm
        gx, gy = int(pig.position.x), int(pig.position.y)
        if not farm.is_walkable(gx, gy):
            rescue_to_walkable(self, pig, farm)

        # Track current area — clear unreachable backoff on area change
        area = self.game_state.farm.get_area_at(int(pig.position.x), int(pig.position.y))
        new_area_id = area.id if area else None
        if new_area_id != pig.current_area_id:
            self._unreachable_needs.pop(pig.id, None)
        pig.current_area_id = new_area_id

        # Update behavior-specific logic
        self._update_current_behavior(pig, delta_seconds)

    def rescue_non_walkable_pigs(self, pigs: list[GuineaPig]) -> None:
        """Post-collision sweep: rescue any pigs that ended up on non-walkable cells."""
        rescue_non_walkable_pigs(self, pigs)

    def _update_current_behavior(self, pig: GuineaPig, delta_seconds: float) -> None:
        """Update behavior-specific effects."""
        # Check if pig just arrived at a facility (path complete, wandering state)
        if pig.behavior_state == BehaviorState.WANDERING and not pig.path:
            # Reset blocked/stuck timers since we arrived
            self._blocked_timers[pig.id] = 0
            self._stuck_positions.pop(pig.id, None)
            self._stuck_timers.pop(pig.id, None)
            self.facility_manager.check_arrived_at_facility(pig)

        # Courting: advance together-phase timer when adjacent to partner
        if pig.behavior_state == BehaviorState.COURTING and not pig.path:
            partner = (
                self.game_state.get_guinea_pig(pig.courting_partner_id)
                if pig.courting_partner_id else None
            )
            if partner and partner.behavior_state == BehaviorState.COURTING:
                dist = pig.position.distance_to(partner.position)
                if dist <= BEHAVIOR.MIN_PIG_DISTANCE + 2.0:
                    # Both arrived — advance timer (only on initiator to avoid double-counting)
                    if pig.courting_initiator:
                        prev_timer = pig.courting_timer
                        pig.courting_timer += delta_seconds
                        partner.courting_timer = pig.courting_timer
                        # Happiness boost while courting
                        pig.needs.happiness = min(100.0, pig.needs.happiness + BEHAVIOR.COURTSHIP_HAPPINESS_BOOST * (delta_seconds / 60.0))
                        partner.needs.happiness = min(100.0, partner.needs.happiness + BEHAVIOR.COURTSHIP_HAPPINESS_BOOST * (delta_seconds / 60.0))
                        # Queue completion only on the tick that crosses the threshold
                        if (pig.courting_timer >= BEHAVIOR.COURTSHIP_TOGETHER_SECONDS
                                and prev_timer < BEHAVIOR.COURTSHIP_TOGETHER_SECONDS):
                            self.completed_courtships.append((pig.id, partner.id))

        # Consuming resources and applying bonuses from facilities
        if pig.behavior_state in (
            BehaviorState.EATING, BehaviorState.DRINKING,
            BehaviorState.SLEEPING, BehaviorState.PLAYING,
        ):
            if not pig.path:  # At the facility
                self.facility_manager.consume_from_nearby_facility(pig, delta_seconds)
