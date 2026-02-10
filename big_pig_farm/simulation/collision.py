"""Collision detection and separation for guinea pigs."""

import math
import random
from typing import Optional

from big_pig_farm.data.config import BEHAVIOR, NEEDS
from big_pig_farm.entities.guinea_pig import GuineaPig, BehaviorState, Position
from big_pig_farm.game.state import GameState


class CollisionHandler:
    """Handles pig-to-pig collision detection and separation."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def is_cell_occupied_by_pig(self, x: int, y: int, exclude_pig: Optional[GuineaPig] = None) -> bool:
        """Check if a cell is occupied by another guinea pig."""
        for other_pig in self.game_state.get_pigs_list():
            if exclude_pig and other_pig.id == exclude_pig.id:
                continue
            other_pos = other_pig.position.grid_pos()
            if other_pos[0] == x and other_pos[1] == y:
                return True
        return False

    def is_position_blocked(self, target_x: float, target_y: float, exclude_pig: GuineaPig, min_distance: float = BEHAVIOR.BLOCKING_DEFAULT) -> bool:
        """Check if moving to a position would collide with another pig.

        Uses a reduced blocking radius against other pigs that are also
        actively moving, so pigs can pass each other on their way to
        facilities instead of forming traffic jams.
        """
        # Emergency override: pigs with critical health ignore blocking
        # entirely so they can push through traffic to reach food/water
        if exclude_pig.needs.health < NEEDS.CRITICAL_THRESHOLD:
            return False

        for other_pig in self.game_state.get_pigs_list():
            if other_pig.id == exclude_pig.id:
                continue
            # If both pigs are actively moving, use a tighter radius so they
            # can squeeze past each other without visually overlapping
            if exclude_pig.path and other_pig.path:
                effective_distance = BEHAVIOR.BLOCKING_BOTH_MOVING
            elif other_pig.behavior_state in (
                BehaviorState.EATING, BehaviorState.DRINKING,
                BehaviorState.SLEEPING, BehaviorState.PLAYING,
            ):
                # Pigs actively using a facility are stationary and "tucked in"
                # — they shouldn't block as much space as an idle pig
                effective_distance = BEHAVIOR.BLOCKING_FACILITY_USE
            else:
                effective_distance = min_distance
            # Check distance to other pig
            dx = target_x - other_pig.position.x
            dy = target_y - other_pig.position.y
            distance = (dx * dx + dy * dy) ** 0.5
            if distance < effective_distance:
                return True
        return False

    def separate_overlapping_pigs(self) -> None:
        """Push apart any pigs that are too close to each other.

        Uses tiered separation thresholds based on movement state.
        The invariant is: separation threshold < blocking threshold
        for the same movement state, so separation never undoes
        movement that passed the blocking check.
        """
        pigs = self.game_state.get_pigs_list()
        farm = self.game_state.farm

        for i, pig_a in enumerate(pigs):
            for pig_b in pigs[i + 1:]:
                # Tiered separation: must stay below corresponding
                # blocking threshold to avoid separation vs pathfinding deadlock.
                # Both moving:          1.0 (blocking = 1.5)
                # Both using facility:  1.0 (allow co-sleeping/co-eating)
                # One moving:           2.0 (blocking = 2.5)
                # Both idle:            3.0 (MIN_PIG_DISTANCE)
                both_moving = pig_a.path and pig_b.path
                facility_use_states = (
                    BehaviorState.EATING, BehaviorState.DRINKING,
                    BehaviorState.SLEEPING, BehaviorState.PLAYING,
                )
                both_using_facility = (
                    pig_a.behavior_state in facility_use_states
                    and pig_b.behavior_state in facility_use_states
                )
                if both_moving:
                    threshold = BEHAVIOR.SEPARATION_BOTH_MOVING
                elif both_using_facility:
                    threshold = BEHAVIOR.SEPARATION_FACILITY_USE
                elif pig_a.path or pig_b.path:
                    threshold = BEHAVIOR.SEPARATION_ONE_MOVING
                else:
                    threshold = BEHAVIOR.MIN_PIG_DISTANCE

                dx = pig_b.position.x - pig_a.position.x
                dy = pig_b.position.y - pig_a.position.y
                distance = (dx * dx + dy * dy) ** 0.5

                if distance < threshold and distance > BEHAVIOR.OVERLAP_EPSILON:
                    # Calculate separation needed
                    overlap = threshold - distance
                    separation = overlap / 2 + BEHAVIOR.SEPARATION_PADDING

                    # Normalize direction
                    nx = dx / distance
                    ny = dy / distance

                    # Move pigs apart (each moves half the overlap distance)
                    new_ax = pig_a.position.x - nx * separation
                    new_ay = pig_a.position.y - ny * separation
                    new_bx = pig_b.position.x + nx * separation
                    new_by = pig_b.position.y + ny * separation

                    # Only apply if BOTH new positions are walkable.
                    # Asymmetric separation (one moves, one can't) causes
                    # ratcheting near walls that pins pigs in place.
                    a_ok = farm.is_walkable(int(new_ax), int(new_ay))
                    b_ok = farm.is_walkable(int(new_bx), int(new_by))
                    if a_ok and b_ok:
                        pig_a.position.x = new_ax
                        pig_a.position.y = new_ay
                        pig_b.position.x = new_bx
                        pig_b.position.y = new_by

                elif distance <= BEHAVIOR.OVERLAP_EPSILON:
                    # Pigs are exactly on top of each other - push one in random direction
                    angle = random.random() * 2 * math.pi  # Random angle in radians
                    push = BEHAVIOR.MIN_PIG_DISTANCE / 2
                    new_x = pig_b.position.x + push * math.cos(angle)
                    new_y = pig_b.position.y + push * math.sin(angle)
                    if farm.is_walkable(int(new_x), int(new_y)):
                        pig_b.position.x = new_x
                        pig_b.position.y = new_y
