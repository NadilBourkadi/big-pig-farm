"""Collision detection and separation for guinea pigs."""

import math
import random
from typing import Optional
from uuid import UUID

from big_pig_farm.data.config import BEHAVIOR, NEEDS
from big_pig_farm.entities.guinea_pig import GuineaPig, BehaviorState, Position
from big_pig_farm.game.state import GameState


# Spatial grid cell size — must be >= largest blocking/separation radius
# so that all potentially interacting pigs are in the same or adjacent bucket.
_GRID_CELL_SIZE = 5


class SpatialGrid:
    """Uniform grid for fast spatial lookups of guinea pigs.

    Divides the farm into cells of _GRID_CELL_SIZE.  After calling
    rebuild() once per tick, get_nearby() returns only pigs in the
    same or adjacent buckets — typically 0-5 instead of all N pigs.
    """

    __slots__ = ("_cells", "_cell_size")

    def __init__(self, cell_size: int = _GRID_CELL_SIZE) -> None:
        self._cell_size = cell_size
        self._cells: dict[tuple[int, int], list[GuineaPig]] = {}

    def rebuild(self, pigs: list[GuineaPig]) -> None:
        """Re-bin all pigs into grid cells.  Call once per tick."""
        self._cells.clear()
        cs = self._cell_size
        for pig in pigs:
            key = (int(pig.position.x) // cs, int(pig.position.y) // cs)
            bucket = self._cells.get(key)
            if bucket is None:
                bucket = []
                self._cells[key] = bucket
            bucket.append(pig)

    def get_nearby(self, x: float, y: float) -> list[GuineaPig]:
        """Return all pigs in the same and 8 adjacent cells."""
        cs = self._cell_size
        cx = int(x) // cs
        cy = int(y) // cs
        result: list[GuineaPig] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                bucket = self._cells.get((cx + dx, cy + dy))
                if bucket:
                    result.extend(bucket)
        return result

    def unique_nearby_pairs(self) -> list[tuple[GuineaPig, GuineaPig]]:
        """Yield unique (pig_a, pig_b) pairs that share the same or adjacent cells.

        Uses a set to avoid emitting the same pair twice when pigs sit
        near a cell boundary.
        """
        seen: set[tuple[UUID, UUID]] = set()
        pairs: list[tuple[GuineaPig, GuineaPig]] = []
        for key, bucket in self._cells.items():
            cx, cy = key
            # Collect pigs from this cell + neighbors
            neighborhood: list[GuineaPig] = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = self._cells.get((cx + dx, cy + dy))
                    if nb:
                        neighborhood.extend(nb)
            # Check all pairs within the neighborhood
            for i in range(len(bucket)):
                a = bucket[i]
                for b in neighborhood:
                    if a.id >= b.id:
                        continue  # Canonical ordering to avoid duplicates
                    pair_key = (a.id, b.id)
                    if pair_key not in seen:
                        seen.add(pair_key)
                        pairs.append((a, b))
        return pairs


class CollisionHandler:
    """Handles pig-to-pig collision detection and separation."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.spatial_grid = SpatialGrid()

    def rebuild_spatial_grid(self) -> None:
        """Re-bin all pigs.  Call once per tick before behavior updates."""
        self.spatial_grid.rebuild(self.game_state.get_pigs_list())

    def is_cell_occupied_by_pig(self, x: int, y: int, exclude_pig: Optional[GuineaPig] = None) -> bool:
        """Check if a cell is occupied by another guinea pig."""
        for other_pig in self.spatial_grid.get_nearby(float(x), float(y)):
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

        for other_pig in self.spatial_grid.get_nearby(target_x, target_y):
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
        farm = self.game_state.farm

        for pig_a, pig_b in self.spatial_grid.unique_nearby_pairs():
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
