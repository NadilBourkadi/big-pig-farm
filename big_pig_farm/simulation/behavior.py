"""AI state machine and decision making for guinea pigs."""

import random
from typing import Optional
from uuid import UUID

from big_pig_farm.data.config import NEEDS, SIMULATION, BEHAVIOR
from big_pig_farm.entities.guinea_pig import GuineaPig, BehaviorState, Personality, Position
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.simulation.needs import get_most_urgent_need, get_target_facility_for_need
from big_pig_farm.simulation.collision import CollisionHandler
from big_pig_farm.simulation.facility_manager import FacilityManager


class BehaviorController:
    """Controls guinea pig behavior and decision making."""

    def __init__(self, game_state):
        self.game_state = game_state
        self.collision = CollisionHandler(game_state)
        self.facility_manager = FacilityManager(game_state, self.collision)
        self._decision_timers: dict[UUID, float] = {}
        self._blocked_timers: dict[UUID, float] = {}  # Track how long pigs have been blocked
        self._stuck_positions: dict[UUID, tuple[int, int]] = {}  # Last known grid cell while blocked
        self._stuck_timers: dict[UUID, float] = {}  # Time stuck at same grid cell (not reset by facility switches)

    def cleanup_dead_pig(self, pig_id: UUID) -> None:
        """Remove tracking state for a pig that is no longer alive."""
        self._decision_timers.pop(pig_id, None)
        self._blocked_timers.pop(pig_id, None)
        self._stuck_positions.pop(pig_id, None)
        self._stuck_timers.pop(pig_id, None)
        self.facility_manager.cleanup_pig(pig_id)

    def reset_all_tracking(self) -> None:
        """Clear all internal tracking state for every pig.

        Used after auto-arrange repositions facilities, so pigs
        start fresh with no stale blocked/failed/stuck state.
        """
        self._decision_timers.clear()
        self._blocked_timers.clear()
        self._stuck_positions.clear()
        self._stuck_timers.clear()
        self.facility_manager.reset_all()

    def separate_overlapping_pigs(self) -> None:
        """Delegate to collision handler."""
        self.collision.separate_overlapping_pigs()

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

        # Clamp position inside walkable bounds (walls + buffer)
        self._clamp_to_bounds(pig)

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
                        self.facility_manager.add_failed_facility(pig.id, target_facility.id)
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
        elif self.facility_manager.get_failed_cooldown(pig.id) > 0:
            # Recently gave up on blocked facilities — count down before retrying
            self.facility_manager.tick_failed_cooldown(pig.id)
        else:
            # Clear failed facilities when making a completely fresh decision
            self.facility_manager.clear_failed_facilities(pig.id)

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
            facilities = self.facility_manager.get_reachable_facilities(pig, facility_type)
            if not facilities:
                continue

            # Sort by spread score so we try less crowded facilities first
            ranked = self.facility_manager.rank_facilities_by_spread(pig, facilities)

            # Try each facility in order until we find one with an open point
            for facility in ranked:
                target = self.facility_manager.find_open_interaction_point(pig, facility)
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
                        self.facility_manager.add_failed_facility(pig.id, facility.id)
                else:
                    pig.log_behavior(f"All points at {facility.name} occupied, trying alternatives")

        # No reachable facilities found
        pig.log_behavior(f"No reachable {need} facility, wandering")
        pig.target_description = None
        self._start_wandering(pig)

    def _seek_sleep(self, pig: GuineaPig) -> None:
        """Find a place to sleep."""
        hideouts = self.facility_manager.get_reachable_facilities(pig, FacilityType.HIDEOUT)

        for hideout in hideouts or []:
            target = self.facility_manager.find_open_interaction_point(pig, hideout)
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
                    self.facility_manager.add_failed_facility(pig.id, hideout.id)

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
            facilities = self.facility_manager.get_reachable_facilities(pig, facility_type)
            for facility in facilities or []:
                target = self.facility_manager.find_open_interaction_point(pig, facility)
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
                        self.facility_manager.add_failed_facility(pig.id, facility.id)

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
            if farm.is_walkable(ax, ay) and not self.collision.is_cell_occupied_by_pig(ax, ay, exclude_pig=pig):
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
            if target and not self.collision.is_cell_occupied_by_pig(target[0], target[1], exclude_pig=pig):
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

    def _clamp_to_bounds(self, pig: GuineaPig) -> None:
        """Clamp pig position to stay within the walkable area of the farm.

        Walls occupy the outermost ring (row/col 0 and height-1/width-1).
        The first walkable cells are at (1, 1), so we clamp to [1.0, w-2]
        and [1.0, h-2] — just enough to keep pigs off wall cells without
        blocking valid pathfinding waypoints along the border.
        """
        farm = self.game_state.farm
        pig.position.x = max(1.0, min(pig.position.x, float(farm.width - 2)))
        pig.position.y = max(1.0, min(pig.position.y, float(farm.height - 2)))

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
                    and not self.collision.is_position_blocked(new_x, new_y, pig)):
                pig.position.x = new_x
                pig.position.y = new_y
                return True
        return False

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
        self._stuck_positions.pop(pig.id, None)
        self._stuck_timers.pop(pig.id, None)

        # If hunger or thirst is critical, clear failed list so the pig
        # immediately retries on next decision — don't let cooldowns kill it
        has_critical_need = (
            pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
            or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD
        )
        if has_critical_need:
            self.facility_manager.clear_failed_facilities(pig.id)
            self.facility_manager.clear_failed_cooldown(pig.id)
        else:
            # Keep failed facilities for 3 decision cycles (~6 seconds) before retrying
            self.facility_manager.set_failed_cooldown(pig.id, BEHAVIOR.FAILED_COOLDOWN_CYCLES)

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
            if not self.collision.is_position_blocked(target_x, target_y, pig):
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
                    self._stuck_positions.pop(pig.id, None)
                    self._stuck_timers.pop(pig.id, None)
                else:
                    # Blocked - track how long and try to find alternative
                    blocked_time = self._blocked_timers.get(pig.id, 0) + delta_seconds
                    self._blocked_timers[pig.id] = blocked_time

                    # Track how long pig is stuck at the same grid cell.
                    # Unlike _blocked_timers, this is NOT reset by facility
                    # switches — only by actual physical movement.
                    grid_pos = (int(pig.position.x), int(pig.position.y))
                    if self._stuck_positions.get(pig.id) != grid_pos:
                        self._stuck_positions[pig.id] = grid_pos
                        self._stuck_timers[pig.id] = 0.0
                    self._stuck_timers[pig.id] = self._stuck_timers.get(pig.id, 0.0) + delta_seconds

                    if pig.target_description and "(blocked)" not in pig.target_description:
                        pig.target_description = f"{pig.target_description} (blocked)"

                    # If stuck at the same cell too long, force give-up regardless
                    # of whether alternative facilities exist (prevents corridor deadlock)
                    if self._stuck_timers.get(pig.id, 0) > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
                        self._give_up_and_fallback(pig)
                        return

                    # After 2 seconds of being blocked, try to find an alternative facility
                    if blocked_time > BEHAVIOR.BLOCKED_TIME_ALTERNATIVE:
                        current_target = pig.target_position
                        if current_target and self.facility_manager.try_alternative_facility(pig, current_target):
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

            # Check walkability and collision with other pigs
            farm = self.game_state.farm
            if (farm.is_walkable(int(new_x), int(new_y))
                    and not self.collision.is_position_blocked(new_x, new_y, pig, min_distance=BEHAVIOR.BLOCKING_DEFAULT)):
                pig.position.x = new_x
                pig.position.y = new_y
                # Clear blocked status and timer
                if pig.target_description and "(blocked)" in pig.target_description:
                    pig.target_description = pig.target_description.replace(" (blocked)", "")
                self._blocked_timers[pig.id] = 0
                self._stuck_positions.pop(pig.id, None)
                self._stuck_timers.pop(pig.id, None)
            elif self._try_dodge(pig, dx, dy, delta_seconds, speed):
                # Dodged sideways to get around blocking pig
                if pig.target_description and "(blocked)" in pig.target_description:
                    pig.target_description = pig.target_description.replace(" (blocked)", "")
                self._blocked_timers[pig.id] = 0
                self._stuck_positions.pop(pig.id, None)
                self._stuck_timers.pop(pig.id, None)
            else:
                # Blocked and can't dodge - track how long and try to find alternative
                blocked_time = self._blocked_timers.get(pig.id, 0) + delta_seconds
                self._blocked_timers[pig.id] = blocked_time

                # Track how long pig is stuck at the same grid cell
                grid_pos = (int(pig.position.x), int(pig.position.y))
                if self._stuck_positions.get(pig.id) != grid_pos:
                    self._stuck_positions[pig.id] = grid_pos
                    self._stuck_timers[pig.id] = 0.0
                self._stuck_timers[pig.id] = self._stuck_timers.get(pig.id, 0.0) + delta_seconds

                if pig.target_description and "(blocked)" not in pig.target_description:
                    pig.target_description = f"{pig.target_description} (blocked)"

                # If stuck at the same cell too long, force give-up regardless
                # of whether alternative facilities exist
                if self._stuck_timers.get(pig.id, 0) > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
                    self._give_up_and_fallback(pig)
                    return

                # After 2 seconds of being blocked, try to find an alternative facility
                if blocked_time > BEHAVIOR.BLOCKED_TIME_ALTERNATIVE:
                    current_target = pig.target_position
                    if current_target and self.facility_manager.try_alternative_facility(pig, current_target):
                        # Found alternative, reset blocked timer
                        self._blocked_timers[pig.id] = 0
                    elif blocked_time > BEHAVIOR.BLOCKED_TIME_GIVE_UP:
                        self._give_up_and_fallback(pig)

    def _update_current_behavior(self, pig: GuineaPig, delta_seconds: float) -> None:
        """Update behavior-specific effects."""
        # Check if pig just arrived at a facility (path complete, wandering state)
        if pig.behavior_state == BehaviorState.WANDERING and not pig.path:
            # Reset blocked/stuck timers since we arrived
            self._blocked_timers[pig.id] = 0
            self._stuck_positions.pop(pig.id, None)
            self._stuck_timers.pop(pig.id, None)
            self.facility_manager.check_arrived_at_facility(pig)

        # Consuming resources from facilities when eating/drinking
        if pig.behavior_state in (BehaviorState.EATING, BehaviorState.DRINKING):
            if not pig.path:  # At the facility
                self.facility_manager.consume_from_nearby_facility(pig, delta_seconds)
