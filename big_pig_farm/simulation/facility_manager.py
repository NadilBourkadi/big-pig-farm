"""Facility selection, interaction, and tracking for guinea pig AI."""

from typing import Optional
from uuid import UUID
import random

from big_pig_farm.data.config import BEHAVIOR, NEEDS, FACILITY_INTERACTION
from big_pig_farm.entities.guinea_pig import GuineaPig, BehaviorState, Position
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.collision import CollisionHandler
from big_pig_farm.simulation.needs import get_most_urgent_need


class FacilityManager:
    """Manages facility selection, occupancy tracking, and resource consumption."""

    def __init__(self, game_state: GameState, collision: CollisionHandler):
        self.game_state = game_state
        self.collision = collision
        self._failed_facilities: dict[UUID, set[UUID]] = {}
        self._failed_cooldowns: dict[UUID, int] = {}
        # Per-decision pathfinding cache: avoids redundant A* calls when
        # get_reachable_facilities, find_open_interaction_point, and
        # try_alternative_facility all pathfind to the same points.
        self._path_cache: dict[tuple[tuple[int, int], tuple[int, int]], list[tuple[int, int]]] = {}

    def begin_decision(self) -> None:
        """Start a facility decision — enable path caching."""
        self._path_cache.clear()

    def end_decision(self) -> None:
        """End a facility decision — discard cached paths."""
        self._path_cache.clear()

    def _cached_find_path(
        self, start: tuple[int, int], goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """find_path with per-decision caching."""
        key = (start, goal)
        result = self._path_cache.get(key)
        if result is not None:
            return result
        path = self.game_state.farm.find_path(start, goal)
        self._path_cache[key] = path
        return path

    def get_failed_facilities(self, pig_id: UUID) -> set[UUID]:
        """Get the set of failed facility IDs for a pig."""
        return self._failed_facilities.get(pig_id, set())

    def add_failed_facility(self, pig_id: UUID, facility_id: UUID) -> None:
        """Mark a facility as failed for a pig."""
        if pig_id not in self._failed_facilities:
            self._failed_facilities[pig_id] = set()
        self._failed_facilities[pig_id].add(facility_id)

    def clear_failed_facilities(self, pig_id: UUID) -> None:
        """Clear the failed facilities list for a pig."""
        self._failed_facilities[pig_id] = set()

    def get_failed_cooldown(self, pig_id: UUID) -> int:
        """Get remaining cooldown cycles for a pig's failed list."""
        return self._failed_cooldowns.get(pig_id, 0)

    def set_failed_cooldown(self, pig_id: UUID, cycles: int) -> None:
        """Set the cooldown cycles for a pig's failed list."""
        self._failed_cooldowns[pig_id] = cycles

    def clear_failed_cooldown(self, pig_id: UUID) -> None:
        """Clear the cooldown for a pig."""
        self._failed_cooldowns.pop(pig_id, None)

    def tick_failed_cooldown(self, pig_id: UUID) -> None:
        """Decrement the failed cooldown and clear failed list when expired."""
        cooldown = self._failed_cooldowns.get(pig_id, 0)
        if cooldown > 0:
            cooldown -= 1
            if cooldown <= 0:
                self._failed_facilities[pig_id] = set()
                del self._failed_cooldowns[pig_id]
            else:
                self._failed_cooldowns[pig_id] = cooldown

    def get_reachable_facilities(self, pig: GuineaPig, facility_type: FacilityType) -> list[Facility]:
        """Get facilities of a type that the pig can actually path to."""
        facilities = self.game_state.get_facilities_by_type(facility_type)

        if not facilities:
            return []

        # Filter out empty facilities for consumables
        if facility_type in (FacilityType.FOOD_BOWL, FacilityType.WATER_BOTTLE, FacilityType.HAY_RACK):
            facilities = [f for f in facilities if not f.is_empty]

        # Filter out recently failed facilities for this pig
        failed = self._failed_facilities.get(pig.id, set())
        if failed:
            facilities = [f for f in facilities if f.id not in failed]

        # Filter to only facilities we can path to at least one interaction point
        reachable = []
        start = pig.position.grid_pos()
        farm = self.game_state.farm

        for facility in facilities:
            # Check if ANY interaction point is reachable (not just primary)
            found_reachable_point = False
            for point in facility.interaction_points:
                # Bounds check first
                if not farm.is_valid_position(point[0], point[1]):
                    continue
                if not farm.is_walkable(point[0], point[1]):
                    continue
                # Try to path there
                path = self._cached_find_path(start, point)
                if path:
                    found_reachable_point = True
                    break

            if found_reachable_point:
                reachable.append(facility)

        return reachable

    def find_open_interaction_point(self, pig: GuineaPig, facility: Facility) -> Optional[tuple[int, int]]:
        """Find an unoccupied interaction point around a facility."""
        farm = self.game_state.farm
        start = pig.position.grid_pos()

        # Use the facility-use blocking radius for occupancy checks so that
        # points marked "open" are genuinely reachable (consistent with the
        # actual blocking distance used against facility-using pigs)
        occupancy_radius = BEHAVIOR.BLOCKING_FACILITY_USE

        # Get all interaction points and filter to walkable/valid ones
        candidates = []
        for point in facility.interaction_points:
            # Bounds check first
            if not farm.is_valid_position(point[0], point[1]):
                continue
            if not farm.is_walkable(point[0], point[1]):
                continue

            # Check if another pig is too close to this point or heading there
            point_pos = Position(x=float(point[0]), y=float(point[1]))
            occupied = False

            for other_pig in self.game_state.get_pigs_list():
                if other_pig.id == pig.id:
                    continue

                # Only count pigs as occupying if they're actively using a facility,
                # not just idling or wandering nearby
                is_using_facility = other_pig.behavior_state in (
                    BehaviorState.EATING, BehaviorState.DRINKING,
                    BehaviorState.SLEEPING, BehaviorState.PLAYING,
                )

                # Check if pig is within occupancy radius of this point
                dist = other_pig.position.distance_to(point_pos)
                if dist < occupancy_radius and is_using_facility:
                    occupied = True
                    break

                # Check if pig is heading to this point to use a facility
                if other_pig.target_facility_id and other_pig.target_position:
                    target_dist = other_pig.target_position.distance_to(point_pos)
                    if target_dist < occupancy_radius:
                        occupied = True
                        break

            if not occupied:
                # Verify we can path there
                path = self._cached_find_path(start, point)
                if path:
                    candidates.append((point, len(path)))

        if candidates:
            # Pick the closest unoccupied point (by path length, not manhattan distance)
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]

        # All interaction points are occupied - return None so the caller
        # can try a different facility instead of sending the pig to cluster
        return None

    def count_pigs_near_or_heading_to(self, pig: GuineaPig, facility: Facility) -> int:
        """Count pigs near or heading to a facility (excluding the given pig)."""
        fx, fy = facility.interaction_point
        facility_pos = Position(x=float(fx), y=float(fy))
        count = 0
        for other_pig in self.game_state.get_pigs_list():
            if other_pig.id == pig.id:
                continue
            # Check if pig is near the facility
            dist = other_pig.position.distance_to(facility_pos)
            if dist < BEHAVIOR.FACILITY_NEARBY_RADIUS:
                count += 1
            # Check if pig is heading toward this facility
            elif other_pig.target_facility_id == facility.id:
                count += 1
            elif other_pig.target_position:
                target_dist = other_pig.target_position.distance_to(facility_pos)
                if target_dist < BEHAVIOR.FACILITY_HEADING_RADIUS:
                    count += 1
        return count

    def rank_facilities_by_spread(self, pig: GuineaPig, facilities: list[Facility]) -> list[Facility]:
        """Rank facilities by preference, putting less crowded and closer ones first."""
        if not facilities:
            return []

        # Pre-compute crowd counts once instead of per-facility-per-call
        crowd_counts = {f.id: self.count_pigs_near_or_heading_to(pig, f) for f in facilities}

        def score(f: Facility) -> float:
            fx, fy = f.interaction_point
            dist = pig.position.distance_to(Position(x=float(fx), y=float(fy)))
            return (dist * BEHAVIOR.FACILITY_DISTANCE_WEIGHT
                    + crowd_counts[f.id] * BEHAVIOR.CROWDING_PENALTY
                    + random.uniform(0, BEHAVIOR.SCORING_RANDOM_VARIANCE))

        ranked = sorted(facilities, key=score)

        # Chance to shuffle an uncrowded facility to the front
        uncrowded = [f for f in ranked if crowd_counts[f.id] == 0]
        if uncrowded and random.random() < BEHAVIOR.UNCROWDED_CHANCE:
            pick = random.choice(uncrowded)
            ranked.remove(pick)
            ranked.insert(0, pick)

        return ranked

    def count_pigs_using_facility(self, facility: Facility, exclude_pig: Optional[GuineaPig] = None) -> int:
        """Count how many pigs are currently using a facility (within interaction range)."""
        count = 0
        for point in facility.interaction_points:
            for other_pig in self.game_state.get_pigs_list():
                if exclude_pig and other_pig.id == exclude_pig.id:
                    continue
                # Check if pig is near this interaction point and in a using state
                dist = other_pig.position.distance_to(Position(x=float(point[0]), y=float(point[1])))
                if dist < BEHAVIOR.OCCUPANCY_RADIUS:
                    # Check if actually using (not just passing by)
                    if other_pig.behavior_state in (BehaviorState.SLEEPING, BehaviorState.EATING,
                                                     BehaviorState.DRINKING, BehaviorState.PLAYING):
                        count += 1
                        break  # Don't double-count same pig at multiple points
        return count

    def check_arrived_at_facility(self, pig: GuineaPig) -> None:
        """Check if pig arrived at a facility and update behavior state."""
        grid_pos = pig.position.grid_pos()
        successfully_using_facility = False

        for facility in self.game_state.get_facilities_list():
            # Check if pig is at an interaction point for this facility
            # Must be at exact position or orthogonally adjacent (not diagonal)
            for ix, iy in facility.interaction_points:
                dx = abs(grid_pos[0] - ix)
                dy = abs(grid_pos[1] - iy)
                # Allow same cell (0,0) or orthogonally adjacent (1,0) or (0,1)
                if (dx + dy) <= FACILITY_INTERACTION.ADJACENCY_DISTANCE:
                    # Found a nearby facility - check what type and set state
                    if facility.facility_type in (FacilityType.FOOD_BOWL, FacilityType.HAY_RACK):
                        if not facility.is_empty and pig.needs.hunger < NEEDS.SATISFACTION_THRESHOLD:
                            pig.behavior_state = BehaviorState.EATING
                            pig.target_position = None
                            pig.target_description = f"eating at {facility.name}"
                            pig.log_behavior(f"Arrived at {facility.name}, eating")
                            successfully_using_facility = True
                        elif facility.is_empty:
                            # Facility empty - mark as failed so we try alternatives
                            pig.log_behavior(f"{facility.name} is empty")
                            self.add_failed_facility(pig.id, facility.id)
                        # Don't return - keep checking or fall through to idle
                        if successfully_using_facility:
                            self.clear_failed_facilities(pig.id)
                            return
                    elif facility.facility_type == FacilityType.WATER_BOTTLE:
                        if not facility.is_empty and pig.needs.thirst < NEEDS.SATISFACTION_THRESHOLD:
                            pig.behavior_state = BehaviorState.DRINKING
                            pig.target_position = None
                            pig.target_description = f"drinking at {facility.name}"
                            pig.log_behavior(f"Arrived at {facility.name}, drinking")
                            successfully_using_facility = True
                        elif facility.is_empty:
                            pig.log_behavior(f"{facility.name} is empty")
                            self.add_failed_facility(pig.id, facility.id)
                        if successfully_using_facility:
                            self.clear_failed_facilities(pig.id)
                            return
                    elif facility.facility_type == FacilityType.HIDEOUT:
                        if pig.needs.energy < NEEDS.SATISFACTION_THRESHOLD:
                            # Check hideout capacity
                            capacity = facility.info.capacity
                            pigs_using = self.count_pigs_using_facility(facility, pig)
                            if pigs_using < capacity:
                                pig.behavior_state = BehaviorState.SLEEPING
                                pig.target_position = None
                                pig.target_description = f"sleeping in {facility.name}"
                                pig.log_behavior(f"Arrived at {facility.name}, sleeping")
                                successfully_using_facility = True
                            else:
                                # Hideout is full - mark as failed but sleep nearby anyway
                                pig.log_behavior(f"{facility.name} is full, sleeping nearby")
                                self.add_failed_facility(pig.id, facility.id)
                                pig.behavior_state = BehaviorState.SLEEPING
                                pig.target_position = None
                                pig.target_description = f"sleeping near {facility.name} (full)"
                                successfully_using_facility = True  # Still sleeping, counts as success
                        if successfully_using_facility:
                            return
                    elif facility.facility_type in (FacilityType.EXERCISE_WHEEL, FacilityType.TUNNEL, FacilityType.PLAY_AREA):
                        pig.behavior_state = BehaviorState.PLAYING
                        pig.target_position = None
                        pig.target_description = f"playing at {facility.name}"
                        pig.log_behavior(f"Arrived at {facility.name}, playing")
                        self.clear_failed_facilities(pig.id)
                        return

        # No suitable facility found or needs already satisfied - go idle
        # DON'T clear failed facilities - we want to remember them for next decision
        pig.behavior_state = BehaviorState.IDLE
        pig.target_position = None
        pig.target_facility_id = None
        pig.target_description = None
        pig.log_behavior("Arrived but nothing to do, idling")

    def consume_from_nearby_facility(self, pig: GuineaPig, delta_seconds: float) -> None:
        """Consume resources from a nearby facility."""
        grid_pos = pig.position.grid_pos()

        for facility in self.game_state.get_facilities_list():
            ix, iy = facility.interaction_point
            if abs(grid_pos[0] - ix) <= FACILITY_INTERACTION.ADJACENCY_DISTANCE and abs(grid_pos[1] - iy) <= FACILITY_INTERACTION.ADJACENCY_DISTANCE:
                if pig.behavior_state == BehaviorState.EATING:
                    if facility.facility_type in (FacilityType.FOOD_BOWL, FacilityType.HAY_RACK):
                        consumed = facility.consume(delta_seconds * BEHAVIOR.RESOURCE_CONSUME_RATE)
                        if consumed <= 0:
                            # Bowl is empty, find another or stop
                            pig.behavior_state = BehaviorState.IDLE
                        else:
                            # Apply health bonus from hay rack (fiber is good for digestion!)
                            if facility.facility_type == FacilityType.HAY_RACK:
                                health_bonus = facility.info.health_bonus
                                pig.needs.health = min(100, pig.needs.health + health_bonus * delta_seconds * BEHAVIOR.FACILITY_BONUS_SCALE)
                        break

                elif pig.behavior_state == BehaviorState.DRINKING:
                    if facility.facility_type == FacilityType.WATER_BOTTLE:
                        consumed = facility.consume(delta_seconds * BEHAVIOR.RESOURCE_CONSUME_RATE)
                        if consumed <= 0:
                            pig.behavior_state = BehaviorState.IDLE
                        break

                elif pig.behavior_state == BehaviorState.SLEEPING:
                    if facility.facility_type == FacilityType.HIDEOUT:
                        # Sleeping in a hideout gives happiness bonus (cozy!)
                        happiness_bonus = facility.info.happiness_bonus
                        if happiness_bonus:
                            pig.needs.happiness = min(100, pig.needs.happiness + happiness_bonus * delta_seconds * BEHAVIOR.FACILITY_BONUS_SCALE)
                        break

                elif pig.behavior_state == BehaviorState.PLAYING:
                    if facility.facility_type in (FacilityType.EXERCISE_WHEEL, FacilityType.TUNNEL, FacilityType.PLAY_AREA):
                        # Apply facility-specific bonuses
                        health_bonus = facility.info.health_bonus
                        happiness_bonus = facility.info.happiness_bonus
                        social_bonus = facility.info.social_bonus

                        if health_bonus:
                            pig.needs.health = min(100, pig.needs.health + health_bonus * delta_seconds * BEHAVIOR.FACILITY_BONUS_SCALE)
                        if happiness_bonus:
                            pig.needs.happiness = min(100, pig.needs.happiness + happiness_bonus * delta_seconds * BEHAVIOR.FACILITY_BONUS_SCALE)
                        if social_bonus:
                            pig.needs.social = min(100, pig.needs.social + social_bonus * delta_seconds * BEHAVIOR.FACILITY_BONUS_SCALE)
                        break

    def try_alternative_facility(self, pig: GuineaPig, blocked_target: Position) -> bool:
        """Try to find an alternative facility when blocked. Returns True if found."""
        # Only blame the facility if the pig is actually near it (blocked AT the
        # facility). If the pig is far away, it's blocked by traffic en route —
        # adding the facility to failed_facilities causes a death spiral when
        # multiple pigs all try to reach the same distant facility.
        if pig.id not in self._failed_facilities:
            self._failed_facilities[pig.id] = set()
        if pig.target_facility_id:
            target_facility = self.game_state.get_facility(pig.target_facility_id)
            if target_facility:
                near_facility = any(
                    abs(pig.position.x - p[0]) <= 3 and abs(pig.position.y - p[1]) <= 3
                    for p in target_facility.interaction_points
                )
                if near_facility:
                    self._failed_facilities[pig.id].add(pig.target_facility_id)

        # Infer what type of facility we need from target_description
        desc = pig.target_description or ""

        # Map facility names in description to facility types to try
        if "Exercise Wheel" in desc or "Tunnel" in desc or "Play Area" in desc:
            facility_types = [FacilityType.TUNNEL, FacilityType.PLAY_AREA, FacilityType.EXERCISE_WHEEL]
        elif "Food Bowl" in desc or "Hay Rack" in desc:
            facility_types = [FacilityType.HAY_RACK, FacilityType.FOOD_BOWL]
        elif "Water Bottle" in desc:
            facility_types = [FacilityType.WATER_BOTTLE]
        elif "Hideout" in desc:
            facility_types = [FacilityType.HIDEOUT]
        else:
            # Fall back to most urgent need
            urgent_need = get_most_urgent_need(pig)
            need_to_facilities = {
                "hunger": [FacilityType.HAY_RACK, FacilityType.FOOD_BOWL],
                "thirst": [FacilityType.WATER_BOTTLE],
                "energy": [FacilityType.HIDEOUT],
                "happiness": [FacilityType.EXERCISE_WHEEL, FacilityType.PLAY_AREA, FacilityType.TUNNEL],
                "social": [FacilityType.PLAY_AREA],
            }
            facility_types = need_to_facilities.get(urgent_need, [])

        if not facility_types:
            return False

        for facility_type in facility_types:
            # get_reachable_facilities already filters out failed facilities
            facilities = self.get_reachable_facilities(pig, facility_type)
            if not facilities:
                continue

            ranked = self.rank_facilities_by_spread(pig, facilities)

            for facility in ranked:
                target = self.find_open_interaction_point(pig, facility)
                if target:
                    start = pig.position.grid_pos()
                    path = self._cached_find_path(start, target)
                    if path:
                        pig.path = path[1:]
                        if pig.path:
                            pig.target_position = Position(x=float(target[0]), y=float(target[1]))
                            pig.target_facility_id = facility.id
                            pig.log_behavior(f"Blocked, switching to {facility.name}")
                            pig.target_description = f"going to {facility.name}"
                            return True

        return False

    def cleanup_pig(self, pig_id: UUID) -> None:
        """Remove tracking state for a pig."""
        self._failed_facilities.pop(pig_id, None)
        self._failed_cooldowns.pop(pig_id, None)

    def reset_all(self) -> None:
        """Clear all tracking state."""
        self._failed_facilities.clear()
        self._failed_cooldowns.clear()
