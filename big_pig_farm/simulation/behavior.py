"""AI state machine and decision making for guinea pigs."""

import math
import random
from typing import Optional
from uuid import UUID

from big_pig_farm.data.config import NEEDS, SIMULATION, BEHAVIOR, FACILITY_INTERACTION
from big_pig_farm.entities.guinea_pig import GuineaPig, BehaviorState, Personality, Position
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.simulation.needs import get_most_urgent_need, get_target_facility_for_need


class BehaviorController:
    """Controls guinea pig behavior and decision making."""

    def __init__(self, game_state):
        self.game_state = game_state
        self._decision_timers: dict[UUID, float] = {}
        self._blocked_timers: dict[UUID, float] = {}  # Track how long pigs have been blocked
        self._failed_facilities: dict[UUID, set[UUID]] = {}  # Track recently-failed facility IDs per pig
        self._failed_cooldowns: dict[UUID, int] = {}  # Decisions remaining before clearing failed list

    def cleanup_dead_pig(self, pig_id: UUID) -> None:
        """Remove tracking state for a pig that is no longer alive."""
        self._decision_timers.pop(pig_id, None)
        self._blocked_timers.pop(pig_id, None)
        self._failed_facilities.pop(pig_id, None)
        self._failed_cooldowns.pop(pig_id, None)

    def update(self, pig: GuineaPig, delta_seconds: float) -> None:
        """Update behavior for a guinea pig."""
        # Check if it's time to make a new decision
        timer = self._decision_timers.get(pig.id, random.uniform(0, 1))  # Stagger initial timers
        timer += delta_seconds

        if timer >= SIMULATION.DECISION_INTERVAL_SECONDS:
            self._make_decision(pig)
            # Add small random offset to prevent synchronized decisions
            timer = random.uniform(0, SIMULATION.DECISION_INTERVAL_SECONDS / 4)

        self._decision_timers[pig.id] = timer

        # Update movement
        self._update_movement(pig, delta_seconds)

        # Update behavior-specific logic
        self._update_current_behavior(pig, delta_seconds)

    def _make_decision(self, pig: GuineaPig) -> None:
        """Make a behavioral decision for the pig."""
        # If pig is actively traveling to a facility with a valid path, check if still valid
        if pig.behavior_state == BehaviorState.WANDERING and pig.path and pig.target_facility_id:
            # Verify the target facility is still usable
            target_facility = self.game_state.get_facility(pig.target_facility_id)
            if target_facility:
                # Check if consumable facility became empty
                if target_facility.facility_type in (FacilityType.FOOD_BOWL, FacilityType.WATER_BOTTLE, FacilityType.HAY_RACK):
                    if target_facility.is_empty:
                        pig.log_behavior(f"{target_facility.name} became empty, seeking alternative")
                        # Mark as failed and force new decision
                        if pig.id not in self._failed_facilities:
                            self._failed_facilities[pig.id] = set()
                        self._failed_facilities[pig.id].add(target_facility.id)
                        pig.path = []
                        pig.target_position = None
                        pig.target_facility_id = None
                        # Fall through to make new decision
                    else:
                        return  # Facility still valid, continue traveling
                else:
                    return  # Non-consumable facility, continue traveling
            else:
                # Facility was removed, force new decision
                pig.log_behavior("Target facility removed, seeking alternative")
                pig.path = []
                pig.target_position = None
                pig.target_facility_id = None
                # Fall through to make new decision

        # If pig was heading to a facility but lost their path, don't clear failed list yet
        # Just let them re-decide (they might pick the same or different facility)
        if pig.target_facility_id and not pig.path:
            # Clear target since we're re-deciding
            pig.target_facility_id = None
            pig.target_description = None
            # Don't clear failed facilities - keep them excluded
        elif self._failed_cooldowns.get(pig.id, 0) > 0:
            # Recently gave up on blocked facilities — count down before retrying
            self._failed_cooldowns[pig.id] -= 1
            if self._failed_cooldowns[pig.id] <= 0:
                self._failed_facilities[pig.id] = set()
                del self._failed_cooldowns[pig.id]
        else:
            # Clear failed facilities when making a completely fresh decision
            self._failed_facilities[pig.id] = set()

        # If sleeping, wake up when energy full or when hunger/thirst is critical
        if pig.behavior_state == BehaviorState.SLEEPING:
            if pig.needs.energy >= NEEDS.SATISFACTION_THRESHOLD:
                pig.log_behavior("Woke up (energy full)")
                pig.behavior_state = BehaviorState.IDLE
                pig.target_description = None
            elif ((pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
                    or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD)
                    and pig.needs.energy >= BEHAVIOR.EMERGENCY_WAKE_ENERGY):
                pig.log_behavior("Woke up (hunger/thirst critical)")
                pig.behavior_state = BehaviorState.IDLE
                pig.target_description = None
            return

        # If eating/drinking and still hungry/thirsty, keep doing it.
        # Never cross-interrupt between eating and drinking — the pig commits
        # to its current action until satisfied (need >= 90). Without this,
        # pigs with both hunger and thirst critical oscillate forever between
        # food and water (Buridan's ass), because the needs cross each other's
        # critical threshold during recovery.
        if pig.behavior_state == BehaviorState.EATING and pig.needs.hunger < NEEDS.SATISFACTION_THRESHOLD:
            return
        if pig.behavior_state == BehaviorState.DRINKING and pig.needs.thirst < NEEDS.SATISFACTION_THRESHOLD:
            return

        # Just finished eating/drinking - wander away to make room for others
        if pig.behavior_state in (BehaviorState.EATING, BehaviorState.DRINKING):
            pig.log_behavior(f"Finished {pig.behavior_state.value}, wandering away")
            pig.target_description = None
            self._start_wandering(pig)
            return

        # If playing and still bored, keep playing — unless hunger/thirst critical
        if pig.behavior_state == BehaviorState.PLAYING and pig.needs.boredom > BEHAVIOR.BOREDOM_KEEP_PLAYING:
            if (pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
                    or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD):
                pig.log_behavior("Stopped playing (hunger/thirst critical)")
                pig.behavior_state = BehaviorState.IDLE
                pig.target_description = None
            else:
                return  # Keep playing until boredom is satisfied
        # If socializing and still need social, keep socializing — unless hunger/thirst critical
        if pig.behavior_state == BehaviorState.SOCIALIZING and pig.needs.social < NEEDS.SATISFACTION_THRESHOLD:
            if (pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
                    or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD):
                pig.log_behavior("Stopped socializing (hunger/thirst critical)")
                pig.behavior_state = BehaviorState.IDLE
                pig.target_description = None
            else:
                return  # Keep socializing until satisfied

        # Just finished playing/socializing - wander away
        if pig.behavior_state in (BehaviorState.PLAYING, BehaviorState.SOCIALIZING):
            pig.log_behavior(f"Finished {pig.behavior_state.value}, wandering away")
            pig.target_description = None
            self._start_wandering(pig)
            return

        # Check for urgent needs
        urgent_need = get_most_urgent_need(pig)

        if urgent_need == "energy" and pig.needs.energy < BEHAVIOR.ENERGY_SLEEP_THRESHOLD:
            pig.log_behavior(f"Tired (energy={pig.needs.energy:.0f}), seeking sleep")
            self._seek_sleep(pig)
            return

        if urgent_need in ("hunger", "thirst"):
            pig.log_behavior(f"Need {urgent_need} ({getattr(pig.needs, urgent_need):.0f}%), seeking facility")
            self._seek_facility_for_need(pig, urgent_need)
            return

        if urgent_need == "social" and not pig.has_trait(Personality.SHY):
            pig.log_behavior("Lonely, seeking social interaction")
            self._seek_social_interaction(pig)
            return

        # Boredom drives exploration/play
        if pig.needs.boredom > BEHAVIOR.BOREDOM_PLAY_THRESHOLD:
            pig.log_behavior(f"Bored ({pig.needs.boredom:.0f}), seeking play")
            self._seek_play(pig)
            return

        # Default behaviors based on personality
        if pig.has_trait(Personality.LAZY) and random.random() < BEHAVIOR.LAZY_SLEEP_CHANCE:
            pig.log_behavior("Feeling lazy, going to sleep")
            self._seek_sleep(pig)
            return

        if pig.has_trait(Personality.PLAYFUL) and random.random() < BEHAVIOR.PLAYFUL_PLAY_CHANCE:
            pig.log_behavior("Feeling playful, seeking play")
            self._seek_play(pig)
            return

        if pig.has_trait(Personality.SOCIAL) and random.random() < BEHAVIOR.SOCIAL_SOCIALIZE_CHANCE:
            pig.log_behavior("Feeling social, seeking friends")
            self._seek_social_interaction(pig)
            return

        # Random wandering or idle
        if random.random() < BEHAVIOR.WANDER_CHANCE:
            pig.log_behavior("Nothing urgent, wandering")
            pig.target_description = None
            self._start_wandering(pig)
        else:
            pig.log_behavior("Nothing urgent, idling")
            pig.behavior_state = BehaviorState.IDLE
            pig.target_position = None
            pig.target_facility_id = None
            pig.target_description = None
            pig.path = []

    def _seek_facility_for_need(self, pig: GuineaPig, need: str) -> None:
        """Find and move towards a facility that addresses a need."""
        facility_types = get_target_facility_for_need(need)
        if facility_types is None:
            pig.log_behavior(f"No facility type for {need}, wandering")
            pig.target_description = None
            self._start_wandering(pig)
            return

        # Try each facility type in order, and verify we can path there
        for facility_type in facility_types:
            facilities = self._get_reachable_facilities(pig, facility_type)
            if not facilities:
                continue

            # Sort by spread score so we try less crowded facilities first
            ranked = self._rank_facilities_by_spread(pig, facilities)

            # Try each facility in order until we find one with an open point
            for facility in ranked:
                target = self._find_open_interaction_point(pig, facility)
                if target:
                    self._set_path_to(pig, target)
                    # Verify path was actually set
                    if pig.path:
                        pig.log_behavior(f"Going to {facility.name} at ({target[0]}, {target[1]})")
                        pig.behavior_state = BehaviorState.WANDERING
                        pig.target_facility_id = facility.id
                        pig.target_description = f"going to {facility.name}"
                        return
                    else:
                        pig.log_behavior(f"Path to {facility.name} failed, trying alternatives")
                        if pig.id not in self._failed_facilities:
                            self._failed_facilities[pig.id] = set()
                        self._failed_facilities[pig.id].add(facility.id)
                else:
                    pig.log_behavior(f"All points at {facility.name} occupied, trying alternatives")

        # No reachable facilities found
        pig.log_behavior(f"No reachable {need} facility, wandering")
        pig.target_description = None
        self._start_wandering(pig)

    def _get_reachable_facilities(self, pig: GuineaPig, facility_type: FacilityType) -> list[Facility]:
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
                path = farm.find_path(start, point)
                if path:
                    found_reachable_point = True
                    break

            if found_reachable_point:
                reachable.append(facility)

        return reachable

    def _find_open_interaction_point(self, pig: GuineaPig, facility: Facility) -> Optional[tuple[int, int]]:
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
                path = farm.find_path(start, point)
                if path:
                    candidates.append((point, len(path)))

        if candidates:
            # Pick the closest unoccupied point (by path length, not manhattan distance)
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]

        # All interaction points are occupied - return None so the caller
        # can try a different facility instead of sending the pig to cluster
        return None

    def _count_pigs_near_or_heading_to(self, pig: GuineaPig, facility: Facility) -> int:
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

    def _rank_facilities_by_spread(self, pig: GuineaPig, facilities: list[Facility]) -> list[Facility]:
        """Rank facilities by preference, putting less crowded and closer ones first."""
        if not facilities:
            return []

        def score(f: Facility) -> float:
            fx, fy = f.interaction_point
            dist = pig.position.distance_to(Position(x=float(fx), y=float(fy)))
            crowd = self._count_pigs_near_or_heading_to(pig, f)
            return dist + (crowd * BEHAVIOR.CROWDING_PENALTY) + random.uniform(0, BEHAVIOR.SCORING_RANDOM_VARIANCE)

        ranked = sorted(facilities, key=score)

        # Chance to shuffle an uncrowded facility to the front
        uncrowded = [f for f in ranked if self._count_pigs_near_or_heading_to(pig, f) == 0]
        if uncrowded and random.random() < BEHAVIOR.UNCROWDED_CHANCE:
            pick = random.choice(uncrowded)
            ranked.remove(pick)
            ranked.insert(0, pick)

        return ranked

    def _seek_sleep(self, pig: GuineaPig) -> None:
        """Find a place to sleep."""
        hideouts = self._get_reachable_facilities(pig, FacilityType.HIDEOUT)

        for hideout in hideouts or []:
            target = self._find_open_interaction_point(pig, hideout)
            if target:
                self._set_path_to(pig, target)
                # Verify path was actually set
                if pig.path:
                    pig.log_behavior(f"Going to {hideout.name} to sleep")
                    pig.behavior_state = BehaviorState.WANDERING
                    pig.target_facility_id = hideout.id
                    pig.target_description = f"going to {hideout.name}"
                    return
                else:
                    # Path failed - mark as failed and try next hideout
                    pig.log_behavior(f"Path to {hideout.name} failed, trying alternatives")
                    if pig.id not in self._failed_facilities:
                        self._failed_facilities[pig.id] = set()
                    self._failed_facilities[pig.id].add(hideout.id)

        # No reachable hideout - sleep where standing
        pig.path = []
        pig.target_position = None
        pig.target_facility_id = None
        pig.target_description = "sleeping"
        pig.behavior_state = BehaviorState.SLEEPING
        pig.log_behavior("No reachable hideout, sleeping where standing")

    def _seek_play(self, pig: GuineaPig) -> None:
        """Find something to play with."""
        play_facilities = [
            FacilityType.EXERCISE_WHEEL,
            FacilityType.PLAY_AREA,
            FacilityType.TUNNEL,
        ]

        for facility_type in play_facilities:
            facilities = self._get_reachable_facilities(pig, facility_type)
            for facility in facilities or []:
                target = self._find_open_interaction_point(pig, facility)
                if target:
                    self._set_path_to(pig, target)
                    # Verify path was actually set
                    if pig.path:
                        pig.log_behavior(f"Going to {facility.name} to play")
                        pig.behavior_state = BehaviorState.WANDERING
                        pig.target_facility_id = facility.id
                        pig.target_description = f"going to {facility.name}"
                        return
                    else:
                        # Path failed - mark as failed and try next
                        pig.log_behavior(f"Path to {facility.name} failed, trying alternatives")
                        if pig.id not in self._failed_facilities:
                            self._failed_facilities[pig.id] = set()
                        self._failed_facilities[pig.id].add(facility.id)

        # No reachable play facilities - just wander playfully
        pig.log_behavior("No reachable play facility, wandering playfully")
        pig.target_description = None
        self._start_wandering(pig)
        if random.random() < BEHAVIOR.NO_PLAY_FACILITY_PLAY_CHANCE:
            pig.behavior_state = BehaviorState.PLAYING
            pig.target_description = "playing around"

    def _seek_social_interaction(self, pig: GuineaPig) -> None:
        """Find another guinea pig to socialize with."""
        other_pigs = [
            p for p in self.game_state.get_pigs_list()
            if p.id != pig.id and not p.has_trait(Personality.SHY)
        ]

        if not other_pigs:
            pig.target_description = None
            self._start_wandering(pig)
            return

        # Find nearest other pig
        nearest = min(other_pigs, key=lambda p: pig.position.distance_to(p.position))

        # Move to a cell adjacent to the other pig, not on top of them
        target_pos = self._find_adjacent_cell(
            (int(nearest.position.x), int(nearest.position.y)),
            pig
        )
        if target_pos:
            start = pig.position.grid_pos()
            path = self.game_state.farm.find_path(start, target_pos)
            if path:
                self._set_path_to(pig, target_pos)
                pig.log_behavior(f"Going to socialize with {nearest.name}")
                pig.behavior_state = BehaviorState.SOCIALIZING
                pig.target_facility_id = None  # Not going to a facility
                pig.target_description = f"going to {nearest.name}"
                return

        # Can't reach any other pig - wander instead
        pig.log_behavior("Can't reach friends, wandering")
        pig.target_facility_id = None
        pig.target_description = None
        self._start_wandering(pig)

    def _find_adjacent_cell(self, target: tuple[int, int], pig: GuineaPig) -> Optional[tuple[int, int]]:
        """Find a walkable cell near the target but with enough spacing."""
        tx, ty = target
        farm = self.game_state.farm

        # Check cells at MIN_PIG_DISTANCE away for proper spacing
        spacing = int(BEHAVIOR.MIN_PIG_DISTANCE)
        adjacents = [
            (tx - spacing, ty), (tx + spacing, ty),
            (tx, ty - spacing), (tx, ty + spacing),
            (tx - spacing, ty - spacing), (tx + spacing, ty + spacing),
            (tx - spacing, ty + spacing), (tx + spacing, ty - spacing),
        ]

        # Sort by distance to pig (prefer cells closer to the approaching pig)
        pig_pos = pig.position.grid_pos()
        adjacents.sort(key=lambda p: abs(p[0] - pig_pos[0]) + abs(p[1] - pig_pos[1]))

        for ax, ay in adjacents:
            if farm.is_walkable(ax, ay) and not self._is_cell_occupied_by_pig(ax, ay, exclude_pig=pig):
                return (ax, ay)

        return target  # Fallback to original target

    def _start_wandering(self, pig: GuineaPig) -> None:
        """Start random wandering, preferring less crowded areas of the farm."""
        farm = self.game_state.farm

        # Calculate the center of mass of all other pigs
        other_pigs = [p for p in self.game_state.get_pigs_list() if p.id != pig.id]
        if other_pigs:
            avg_x = sum(p.position.x for p in other_pigs) / len(other_pigs)
            avg_y = sum(p.position.y for p in other_pigs) / len(other_pigs)
        else:
            avg_x, avg_y = farm.width / 2, farm.height / 2

        best_target = None
        best_score = -1

        # Try multiple random positions and pick one away from the pig cluster
        for _ in range(BEHAVIOR.WANDER_ATTEMPTS):
            target = farm.find_random_walkable()
            if target and not self._is_cell_occupied_by_pig(target[0], target[1], exclude_pig=pig):
                # Score based on distance from center of pig cluster (higher = better)
                dist_from_cluster = ((target[0] - avg_x) ** 2 + (target[1] - avg_y) ** 2) ** 0.5

                # Also consider minimum distance from any pig
                min_pig_dist = float('inf')
                for other_pig in other_pigs:
                    dist = ((target[0] - other_pig.position.x) ** 2 +
                            (target[1] - other_pig.position.y) ** 2) ** 0.5
                    min_pig_dist = min(min_pig_dist, dist)

                # Combined score: distance from cluster + minimum pig distance
                score = dist_from_cluster + min_pig_dist * BEHAVIOR.WANDER_PIG_DISTANCE_WEIGHT

                if score > best_score:
                    best_score = score
                    best_target = target

        if best_target:
            self._set_path_to(pig, best_target)
        pig.behavior_state = BehaviorState.WANDERING

    def _set_path_to(self, pig: GuineaPig, target: tuple[int, int]) -> None:
        """Calculate and set path to target."""
        start = pig.position.grid_pos()
        path = self.game_state.farm.find_path(start, target)

        if path:
            pig.path = path[1:]  # Skip current position
            if pig.path:
                pig.target_position = Position(x=float(target[0]), y=float(target[1]))

    def _is_cell_occupied_by_pig(self, x: int, y: int, exclude_pig: Optional[GuineaPig] = None) -> bool:
        """Check if a cell is occupied by another guinea pig."""
        for other_pig in self.game_state.get_pigs_list():
            if exclude_pig and other_pig.id == exclude_pig.id:
                continue
            other_pos = other_pig.position.grid_pos()
            if other_pos[0] == x and other_pos[1] == y:
                return True
        return False

    def _is_position_blocked(self, target_x: float, target_y: float, exclude_pig: GuineaPig, min_distance: float = BEHAVIOR.BLOCKING_DEFAULT) -> bool:
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

    def _count_pigs_using_facility(self, facility: Facility, exclude_pig: Optional[GuineaPig] = None) -> int:
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

    def _try_alternative_facility(self, pig: GuineaPig, blocked_target: Position) -> bool:
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
            # _get_reachable_facilities already filters out failed facilities
            facilities = self._get_reachable_facilities(pig, facility_type)
            if not facilities:
                continue

            ranked = self._rank_facilities_by_spread(pig, facilities)

            for facility in ranked:
                target = self._find_open_interaction_point(pig, facility)
                if target:
                    self._set_path_to(pig, target)
                    if pig.path:
                        pig.target_facility_id = facility.id
                        pig.log_behavior(f"Blocked, switching to {facility.name}")
                        pig.target_description = f"going to {facility.name}"
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

    def _give_up_and_fallback(self, pig: GuineaPig) -> None:
        """Give up reaching a facility and apply a need-specific fallback behavior.

        Instead of going IDLE (which causes immediate re-decision to the same
        facility), apply a fallback: sleep where standing, wander away, etc.
        Failed facilities are preserved so the pig doesn't immediately retry.
        """
        desc = pig.target_description or ""
        pig.path = []
        pig.target_position = None
        pig.target_facility_id = None
        pig.target_description = None
        self._blocked_timers[pig.id] = 0

        # If hunger or thirst is critical, clear failed list so the pig
        # immediately retries on next decision — don't let cooldowns kill it
        has_critical_need = (
            pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
            or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD
        )
        if has_critical_need:
            self._failed_facilities[pig.id] = set()
            self._failed_cooldowns.pop(pig.id, None)
        else:
            # Keep failed facilities for 3 decision cycles (~6 seconds) before retrying
            self._failed_cooldowns[pig.id] = BEHAVIOR.FAILED_COOLDOWN_CYCLES

        if "Hideout" in desc or "sleep" in desc:
            # Sleep where standing — the hideouts are all occupied
            pig.behavior_state = BehaviorState.SLEEPING
            pig.target_description = "sleeping (no hideout available)"
            pig.log_behavior("All hideouts blocked, sleeping where standing")
        else:
            # Wander away and try again later
            pig.behavior_state = BehaviorState.IDLE
            pig.log_behavior("All facilities blocked, wandering away")
            self._start_wandering(pig)
            # Set a longer cooldown before next decision to avoid retrying immediately
            self._decision_timers[pig.id] = 0

    def _try_dodge(self, pig: GuineaPig, path_dx: float, path_dy: float, delta_seconds: float, speed: float) -> bool:
        """Try to sidestep perpendicular to the path direction to get around a blocking pig.

        Returns True if the pig successfully dodged.
        """
        farm = self.game_state.farm
        move_dist = min(speed * delta_seconds, BEHAVIOR.DODGE_MAX_STEP)  # Cap dodge step

        # Calculate perpendicular directions (rotate 90 degrees both ways)
        perp_dirs = [(-path_dy, path_dx), (path_dy, -path_dx)]
        length = (path_dx * path_dx + path_dy * path_dy) ** 0.5
        if length < BEHAVIOR.PATH_VECTOR_EPSILON:
            return False

        for pdx, pdy in perp_dirs:
            pdx /= length
            pdy /= length
            new_x = pig.position.x + pdx * move_dist
            new_y = pig.position.y + pdy * move_dist
            if (farm.is_valid_position(int(new_x), int(new_y))
                    and farm.is_walkable(int(new_x), int(new_y))
                    and not self._is_position_blocked(new_x, new_y, pig)):
                pig.position.x = new_x
                pig.position.y = new_y
                return True
        return False

    def _update_movement(self, pig: GuineaPig, delta_seconds: float) -> None:
        """Update pig position along its path."""
        if not pig.path:
            return

        # Don't move while sleeping
        if pig.behavior_state == BehaviorState.SLEEPING:
            return

        # Calculate movement speed
        speed = SIMULATION.BASE_MOVE_SPEED

        # Reduce speed if tired
        if pig.needs.energy < BEHAVIOR.ENERGY_SLEEP_THRESHOLD:
            speed *= BEHAVIOR.TIRED_SPEED_MULT

        # Babies are slower
        if pig.is_baby:
            speed *= BEHAVIOR.BABY_SPEED_MULT

        # Get next path point
        next_point = pig.path[0]
        target_x, target_y = float(next_point[0]), float(next_point[1])

        dx = target_x - pig.position.x
        dy = target_y - pig.position.y
        distance = (dx * dx + dy * dy) ** 0.5

        if distance < BEHAVIOR.WAYPOINT_REACHED:
            # Reached this waypoint - check if we can actually move there
            if not self._is_position_blocked(target_x, target_y, pig):
                pig.position.x = target_x
                pig.position.y = target_y
                pig.path.pop(0)

                if not pig.path:
                    pig.target_position = None
            else:
                # Try dodging sideways to get around the blocking pig
                if self._try_dodge(pig, dx, dy, delta_seconds, speed):
                    if pig.target_description and "(blocked)" in pig.target_description:
                        pig.target_description = pig.target_description.replace(" (blocked)", "")
                    self._blocked_timers[pig.id] = 0
                else:
                    # Blocked - track how long and try to find alternative
                    blocked_time = self._blocked_timers.get(pig.id, 0) + delta_seconds
                    self._blocked_timers[pig.id] = blocked_time

                    if pig.target_description and "(blocked)" not in pig.target_description:
                        pig.target_description = f"{pig.target_description} (blocked)"

                    # After 2 seconds of being blocked, try to find an alternative facility
                    if blocked_time > BEHAVIOR.BLOCKED_TIME_ALTERNATIVE:
                        current_target = pig.target_position
                        if current_target and self._try_alternative_facility(pig, current_target):
                            self._blocked_timers[pig.id] = 0
                        elif blocked_time > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
                            self._give_up_and_fallback(pig)
        else:
            # Calculate proposed new position
            move_distance = speed * delta_seconds
            if move_distance >= distance:
                new_x, new_y = target_x, target_y
            else:
                new_x = pig.position.x + (dx / distance) * move_distance
                new_y = pig.position.y + (dy / distance) * move_distance

            # Check if new position would collide with another pig
            if not self._is_position_blocked(new_x, new_y, pig, min_distance=BEHAVIOR.BLOCKING_DEFAULT):
                pig.position.x = new_x
                pig.position.y = new_y
                # Clear blocked status and timer
                if pig.target_description and "(blocked)" in pig.target_description:
                    pig.target_description = pig.target_description.replace(" (blocked)", "")
                self._blocked_timers[pig.id] = 0
            elif self._try_dodge(pig, dx, dy, delta_seconds, speed):
                # Dodged sideways to get around blocking pig
                if pig.target_description and "(blocked)" in pig.target_description:
                    pig.target_description = pig.target_description.replace(" (blocked)", "")
                self._blocked_timers[pig.id] = 0
            else:
                # Blocked and can't dodge - track how long and try to find alternative
                blocked_time = self._blocked_timers.get(pig.id, 0) + delta_seconds
                self._blocked_timers[pig.id] = blocked_time

                if pig.target_description and "(blocked)" not in pig.target_description:
                    pig.target_description = f"{pig.target_description} (blocked)"

                # After 2 seconds of being blocked, try to find an alternative facility
                if blocked_time > 2.0:
                    current_target = pig.target_position
                    if current_target and self._try_alternative_facility(pig, current_target):
                        # Found alternative, reset blocked timer
                        self._blocked_timers[pig.id] = 0
                    elif blocked_time > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
                        self._give_up_and_fallback(pig)

    def _update_current_behavior(self, pig: GuineaPig, delta_seconds: float) -> None:
        """Update behavior-specific effects."""
        # Check if pig just arrived at a facility (path complete, wandering state)
        if pig.behavior_state == BehaviorState.WANDERING and not pig.path:
            self._check_arrived_at_facility(pig)

        # Consuming resources from facilities when eating/drinking
        if pig.behavior_state in (BehaviorState.EATING, BehaviorState.DRINKING):
            if not pig.path:  # At the facility
                self._consume_from_nearby_facility(pig, delta_seconds)

    def _check_arrived_at_facility(self, pig: GuineaPig) -> None:
        """Check if pig arrived at a facility and update behavior state."""
        # Reset blocked timer since we arrived
        self._blocked_timers[pig.id] = 0

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
                            if pig.id not in self._failed_facilities:
                                self._failed_facilities[pig.id] = set()
                            self._failed_facilities[pig.id].add(facility.id)
                        # Don't return - keep checking or fall through to idle
                        if successfully_using_facility:
                            self._failed_facilities[pig.id] = set()
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
                            if pig.id not in self._failed_facilities:
                                self._failed_facilities[pig.id] = set()
                            self._failed_facilities[pig.id].add(facility.id)
                        if successfully_using_facility:
                            self._failed_facilities[pig.id] = set()
                            return
                    elif facility.facility_type == FacilityType.HIDEOUT:
                        if pig.needs.energy < NEEDS.SATISFACTION_THRESHOLD:
                            # Check hideout capacity
                            capacity = facility.info.capacity
                            pigs_using = self._count_pigs_using_facility(facility, pig)
                            if pigs_using < capacity:
                                pig.behavior_state = BehaviorState.SLEEPING
                                pig.target_position = None
                                pig.target_description = f"sleeping in {facility.name}"
                                pig.log_behavior(f"Arrived at {facility.name}, sleeping")
                                successfully_using_facility = True
                            else:
                                # Hideout is full - mark as failed but sleep nearby anyway
                                pig.log_behavior(f"{facility.name} is full, sleeping nearby")
                                if pig.id not in self._failed_facilities:
                                    self._failed_facilities[pig.id] = set()
                                self._failed_facilities[pig.id].add(facility.id)
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
                        self._failed_facilities[pig.id] = set()
                        return

        # No suitable facility found or needs already satisfied - go idle
        # DON'T clear failed facilities - we want to remember them for next decision
        pig.behavior_state = BehaviorState.IDLE
        pig.target_position = None
        pig.target_facility_id = None
        pig.target_description = None
        pig.log_behavior("Arrived but nothing to do, idling")

    def _consume_from_nearby_facility(self, pig: GuineaPig, delta_seconds: float) -> None:
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
