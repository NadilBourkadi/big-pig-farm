"""Facility seeking and social interaction logic for guinea pig AI."""

import random
from typing import TYPE_CHECKING

from big_pig_farm.data.config import BEHAVIOR, NEEDS
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.entities.guinea_pig import BehaviorState, GuineaPig, Personality, Position
from big_pig_farm.simulation.behavior_movement import set_path_to, start_wandering
from big_pig_farm.simulation.breeding import clear_courtship
from big_pig_farm.simulation.needs import get_target_facility_for_need

if TYPE_CHECKING:
    from big_pig_farm.simulation.behavior_controller import BehaviorController


def seek_facility_for_need(
    controller: "BehaviorController", pig: GuineaPig, need: str,
) -> None:
    """Find and move towards a facility that addresses a need."""
    # Unreachable facility backoff — skip the expensive facility search
    # if we recently determined no reachable facility exists for this need
    backoff = controller._unreachable_needs.get(pig.id, {}).get(need, 0)
    if backoff > 0:
        pig.target_description = None
        start_wandering(controller, pig)
        return

    facility_types = get_target_facility_for_need(need)
    if facility_types is None:
        pig.log_behavior(f"No facility type for {need}, wandering")
        pig.target_description = None
        start_wandering(controller, pig)
        return

    # Try each facility type in order; get_candidate_facilities_ranked
    # filters + ranks without A*, then find_open_interaction_point does
    # a single A* pass per candidate (returns point + path together).
    for facility_type in facility_types:
        candidates = controller.facility_manager.get_candidate_facilities_ranked(pig, facility_type)
        if not candidates:
            continue

        for facility in candidates[:BEHAVIOR.MAX_FACILITY_CANDIDATES]:
            result = controller.facility_manager.find_open_interaction_point(pig, facility)
            if result:
                target, path = result
                pig.path = path
                if pig.path:
                    pig.log_behavior(f"Going to {facility.name} at ({target[0]}, {target[1]})")
                    pig.behavior_state = BehaviorState.WANDERING
                    pig.target_facility_id = facility.id
                    pig.target_position = Position(x=float(target[0]), y=float(target[1]))
                    pig.target_description = f"going to {facility.name}"
                    return
                else:
                    pig.log_behavior(f"Path to {facility.name} failed, trying alternatives")
                    controller.facility_manager.add_failed_facility(pig.id, facility.id)
            else:
                pig.log_behavior(f"All points at {facility.name} occupied, trying alternatives")

    # No reachable facilities found — set backoff to avoid retrying every 2s
    is_critical = getattr(pig.needs, need) < NEEDS.CRITICAL_THRESHOLD
    cycles = (BEHAVIOR.UNREACHABLE_CRITICAL_CYCLES if is_critical
              else BEHAVIOR.UNREACHABLE_BACKOFF_CYCLES)
    if pig.id not in controller._unreachable_needs:
        controller._unreachable_needs[pig.id] = {}
    controller._unreachable_needs[pig.id][need] = cycles

    pig.log_behavior(f"No reachable {need} facility, backing off {cycles} cycles")
    pig.target_description = None
    start_wandering(controller, pig)


def seek_sleep(controller: "BehaviorController", pig: GuineaPig) -> None:
    """Find a place to sleep."""
    candidates = controller.facility_manager.get_candidate_facilities_ranked(pig, FacilityType.HIDEOUT)

    for hideout in candidates[:BEHAVIOR.MAX_FACILITY_CANDIDATES]:
        result = controller.facility_manager.find_open_interaction_point(pig, hideout)
        if result:
            target, path = result
            pig.path = path
            if pig.path:
                pig.log_behavior(f"Going to {hideout.name} to sleep")
                pig.behavior_state = BehaviorState.WANDERING
                pig.target_facility_id = hideout.id
                pig.target_position = Position(x=float(target[0]), y=float(target[1]))
                pig.target_description = f"going to {hideout.name}"
                return
            else:
                pig.log_behavior(f"Path to {hideout.name} failed, trying alternatives")
                controller.facility_manager.add_failed_facility(pig.id, hideout.id)

    # No reachable hideout - sleep where standing
    pig.path = []
    pig.target_position = None
    pig.target_facility_id = None
    pig.target_description = "sleeping"
    pig.behavior_state = BehaviorState.SLEEPING
    pig.log_behavior("No reachable hideout, sleeping where standing")


def seek_play(controller: "BehaviorController", pig: GuineaPig) -> None:
    """Find something to play with."""
    play_types = [
        FacilityType.EXERCISE_WHEEL,
        FacilityType.PLAY_AREA,
        FacilityType.TUNNEL,
    ]

    # Collect candidate play facilities per type (already ranked),
    # capping per type so we don't waste A* calls on distant options
    all_play: list[Facility] = []
    for facility_type in play_types:
        candidates = controller.facility_manager.get_candidate_facilities_ranked(pig, facility_type)
        all_play.extend(candidates[:BEHAVIOR.MAX_FACILITY_CANDIDATES])

    for facility in all_play:
        result = controller.facility_manager.find_open_interaction_point(pig, facility)
        if result:
            target, path = result
            pig.path = path
            if pig.path:
                pig.log_behavior(f"Going to {facility.name} to play")
                pig.behavior_state = BehaviorState.WANDERING
                pig.target_facility_id = facility.id
                pig.target_position = Position(x=float(target[0]), y=float(target[1]))
                pig.target_description = f"going to {facility.name}"
                return
            else:
                pig.log_behavior(f"Path to {facility.name} failed, trying alternatives")
                controller.facility_manager.add_failed_facility(pig.id, facility.id)

    # No reachable play facilities — try socializing instead since it
    # also recovers happiness; prevents priority starvation where happiness
    # (priority 4) permanently blocks social (priority 5).
    # SHY pigs skip this fallback (they can be approached but won't initiate).
    if pig.needs.social < NEEDS.HIGH_THRESHOLD and not pig.has_trait(Personality.SHY):
        pig.log_behavior("No play facility, seeking social interaction instead")
        seek_social_interaction(controller, pig)
        return

    # Fallback: wander playfully
    pig.log_behavior("No reachable play facility, wandering playfully")
    pig.target_description = None
    start_wandering(controller, pig)
    if random.random() < BEHAVIOR.NO_PLAY_FACILITY_PLAY_CHANCE:
        pig.behavior_state = BehaviorState.PLAYING
        pig.target_description = "playing around"


def seek_social_interaction(
    controller: "BehaviorController", pig: GuineaPig,
) -> None:
    """Find another guinea pig to socialize with.

    SHY pigs don't initiate socializing (blocked in make_decision),
    but they can still be approached by non-shy pigs.
    """
    nearest = None
    best_dist_sq = float('inf')
    px, py = pig.position.x, pig.position.y
    for p in controller.collision.spatial_grid.get_nearby(px, py):
        if p.id == pig.id:
            continue
        dsq = (px - p.position.x) ** 2 + (py - p.position.y) ** 2
        if dsq < best_dist_sq:
            best_dist_sq = dsq
            nearest = p

    # Fall back to full list if no one nearby
    if nearest is None:
        for p in controller.game_state.get_pigs_list():
            if p.id == pig.id:
                continue
            dsq = (px - p.position.x) ** 2 + (py - p.position.y) ** 2
            if dsq < best_dist_sq:
                best_dist_sq = dsq
                nearest = p

    if nearest is None:
        pig.target_description = None
        start_wandering(controller, pig)
        return

    # Move to a cell adjacent to the other pig, not on top of them
    target_pos = find_adjacent_cell(
        controller,
        (int(nearest.position.x), int(nearest.position.y)),
        pig,
    )
    if target_pos:
        set_path_to(controller, pig, target_pos)
        if pig.path:
            pig.log_behavior(f"Going to socialize with {nearest.name}")
            pig.behavior_state = BehaviorState.SOCIALIZING
            pig.target_facility_id = None  # Not going to a facility
            pig.target_description = f"going to {nearest.name}"
            return

    # Can't reach any other pig - wander instead
    pig.log_behavior("Can't reach friends, wandering")
    pig.target_facility_id = None
    pig.target_description = None
    start_wandering(controller, pig)


def seek_courting_partner(
    controller: "BehaviorController", pig: GuineaPig, partner: GuineaPig,
) -> None:
    """Pathfind the initiator pig to its courting partner."""
    target_pos = find_adjacent_cell(
        controller,
        (int(partner.position.x), int(partner.position.y)),
        pig,
    )
    if target_pos:
        set_path_to(controller, pig, target_pos)
        if pig.path:
            pig.log_behavior(f"Walking to court {partner.name}")
            pig.target_description = f"courting {partner.name}"
            return

    # Can't reach partner — cancel courtship
    pig.log_behavior("Can't reach courting partner, cancelling")
    clear_courtship(partner)
    clear_courtship(pig)


def find_adjacent_cell(
    controller: "BehaviorController",
    target: tuple[int, int],
    pig: GuineaPig,
) -> tuple[int, int] | None:
    """Find a walkable cell near the target but with enough spacing."""
    tx, ty = target
    farm = controller.game_state.farm

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
        if farm.is_walkable(ax, ay) and not controller.collision.is_cell_occupied_by_pig(ax, ay, exclude_pig=pig):
            return (ax, ay)

    return target  # Fallback to original target
