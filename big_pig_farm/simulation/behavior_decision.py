"""Decision-making logic for guinea pig AI."""

import random
from typing import TYPE_CHECKING

from big_pig_farm.data.config import BEHAVIOR, NEEDS
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.guinea_pig import BehaviorState, GuineaPig, Personality, Position
from big_pig_farm.simulation.auto_resources import AOE_ATTRACTION_RADIUS
from big_pig_farm.simulation.behavior_movement import start_wandering
from big_pig_farm.simulation.behavior_seeking import (
    seek_courting_partner,
    seek_facility_for_need,
    seek_play,
    seek_sleep,
    seek_social_interaction,
)
from big_pig_farm.simulation.breeding import clear_courtship
from big_pig_farm.simulation.needs import get_most_urgent_need

if TYPE_CHECKING:
    from big_pig_farm.simulation.behavior_controller import BehaviorController


def is_content(pig: GuineaPig) -> bool:
    """Check if a pig is content (no urgent needs, not heading to a facility).

    Content pigs use a longer decision interval to save CPU — they would
    just wander/idle anyway since get_most_urgent_need() returns "none".
    """
    if pig.behavior_state not in (BehaviorState.IDLE, BehaviorState.WANDERING):
        return False
    if pig.target_facility_id:
        return False
    needs = pig.needs
    return (
        needs.hunger >= NEEDS.HIGH_THRESHOLD
        and needs.thirst >= NEEDS.HIGH_THRESHOLD
        and needs.energy >= NEEDS.HIGH_THRESHOLD
        and needs.happiness >= NEEDS.HIGH_THRESHOLD
        and needs.social >= NEEDS.HIGH_THRESHOLD
        and needs.boredom < BEHAVIOR.BOREDOM_PLAY_THRESHOLD
    )


def make_decision(controller: "BehaviorController", pig: GuineaPig) -> None:
    """Make a behavioral decision for the pig."""
    # If pig is actively traveling to a facility with a valid path, check if still valid
    if pig.behavior_state == BehaviorState.WANDERING and pig.path and pig.target_facility_id:
        # Verify the target facility is still usable
        target_facility = controller.game_state.get_facility(pig.target_facility_id)
        if target_facility:
            # Check if consumable facility became empty
            if target_facility.facility_type in (FacilityType.FOOD_BOWL, FacilityType.WATER_BOTTLE, FacilityType.HAY_RACK, FacilityType.FEAST_TABLE):
                if target_facility.is_empty:
                    pig.log_behavior(f"{target_facility.name} became empty, seeking alternative")
                    # Mark as failed and force new decision
                    controller.facility_manager.add_failed_facility(pig.id, target_facility.id)
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
    elif controller.facility_manager.get_failed_cooldown(pig.id) > 0:
        # Recently gave up on blocked facilities — count down before retrying
        controller.facility_manager.tick_failed_cooldown(pig.id)
    else:
        # Clear failed facilities when making a completely fresh decision
        controller.facility_manager.clear_failed_facilities(pig.id)

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

    # If courting, validate partner and allow critical-need interruption
    if pig.behavior_state == BehaviorState.COURTING:
        partner = (
            controller.game_state.get_guinea_pig(pig.courting_partner_id)
            if pig.courting_partner_id else None
        )
        if partner is None or partner.behavior_state != BehaviorState.COURTING:
            pig.log_behavior("Courtship cancelled (partner unavailable)")
            clear_courtship(pig)
            return
        # Allow interruption by critical hunger/thirst
        if (pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD
                or pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD):
            pig.log_behavior("Courtship interrupted (critical need)")
            clear_courtship(partner)
            clear_courtship(pig)
            return
        # If initiator has no path, seek the partner
        if pig.courting_initiator and not pig.path:
            seek_courting_partner(controller, pig, partner)
        return  # Stay in COURTING state

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
        start_wandering(controller, pig)
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
        # Track affinity when socialization completes (only from smaller UUID
        # to avoid double-increment when both pigs finish on the same tick)
        if pig.behavior_state == BehaviorState.SOCIALIZING:
            for p in controller.collision.spatial_grid.get_nearby(pig.position.x, pig.position.y):
                if p.id != pig.id and p.behavior_state == BehaviorState.SOCIALIZING and pig.id < p.id:
                    if pig.position.distance_to(p.position) <= BEHAVIOR.MIN_PIG_DISTANCE + 2.0:
                        controller.game_state.increment_affinity(pig.id, p.id)
        pig.log_behavior(f"Finished {pig.behavior_state.value}, wandering away")
        pig.target_description = None
        start_wandering(controller, pig)
        return

    # Tick down unreachable facility backoff counters
    pig_backoffs = controller._unreachable_needs.get(pig.id)
    if pig_backoffs:
        expired = [k for k, v in pig_backoffs.items() if v <= 1]
        for k in expired:
            del pig_backoffs[k]
        for k in pig_backoffs:
            pig_backoffs[k] -= 1
        if not pig_backoffs:
            del controller._unreachable_needs[pig.id]

    # Check for urgent needs
    urgent_need = get_most_urgent_need(pig)

    if urgent_need == "energy" and pig.needs.energy < BEHAVIOR.ENERGY_SLEEP_THRESHOLD:
        # If happiness is critically low but energy isn't critical,
        # prioritize play to break the eat→sleep death spiral where
        # pigs never play and happiness stays at 0 forever.
        if (pig.needs.happiness < NEEDS.CRITICAL_THRESHOLD
                and pig.needs.energy >= NEEDS.CRITICAL_THRESHOLD):
            pig.log_behavior(
                f"Unhappy ({pig.needs.happiness:.0f}%), prioritizing play over sleep"
            )
            seek_play(controller, pig)
            return
        pig.log_behavior(f"Tired (energy={pig.needs.energy:.0f}), seeking sleep")
        seek_sleep(controller, pig)
        return

    if urgent_need in ("hunger", "thirst"):
        pig.log_behavior(f"Need {urgent_need} ({getattr(pig.needs, urgent_need):.0f}%), seeking facility")
        seek_facility_for_need(controller, pig, urgent_need)
        return

    if urgent_need == "happiness":
        pig.log_behavior(f"Unhappy ({pig.needs.happiness:.0f}%), seeking play")
        seek_play(controller, pig)
        return

    if urgent_need == "social" and not pig.has_trait(Personality.SHY):
        pig.log_behavior("Lonely, seeking social interaction")
        seek_social_interaction(controller, pig)
        return

    # Boredom drives exploration/play
    if pig.needs.boredom > BEHAVIOR.BOREDOM_PLAY_THRESHOLD:
        pig.log_behavior(f"Bored ({pig.needs.boredom:.0f}), seeking play")
        seek_play(controller, pig)
        return

    # Default behaviors based on personality
    if pig.has_trait(Personality.LAZY) and random.random() < BEHAVIOR.LAZY_SLEEP_CHANCE:
        pig.log_behavior("Feeling lazy, going to sleep")
        seek_sleep(controller, pig)
        return

    if pig.has_trait(Personality.PLAYFUL) and random.random() < BEHAVIOR.PLAYFUL_PLAY_CHANCE:
        pig.log_behavior("Feeling playful, seeking play")
        seek_play(controller, pig)
        return

    if pig.has_trait(Personality.SOCIAL) and random.random() < BEHAVIOR.SOCIAL_SOCIALIZE_CHANCE:
        pig.log_behavior("Feeling social, seeking friends")
        seek_social_interaction(controller, pig)
        return

    # Nighttime campfire attraction — idle pigs near a campfire wander toward it
    if not controller.game_state.game_time.is_daytime:
        _try_campfire_attraction(controller, pig)

    # Random wandering or idle
    if random.random() < BEHAVIOR.WANDER_CHANCE:
        pig.log_behavior("Nothing urgent, wandering")
        pig.target_description = None
        start_wandering(controller, pig)
    else:
        # Idle drift: if another pig is nearby, wander away instead of idling
        drift_r_sq = BEHAVIOR.IDLE_DRIFT_RADIUS ** 2
        has_nearby_pig = False
        for p in controller.collision.spatial_grid.get_nearby(pig.position.x, pig.position.y):
            if p.id == pig.id:
                continue
            dx = pig.position.x - p.position.x
            dy = pig.position.y - p.position.y
            if dx * dx + dy * dy < drift_r_sq:
                has_nearby_pig = True
                break
        if has_nearby_pig:
            pig.log_behavior("Too close to another pig, drifting away")
            pig.target_description = None
            start_wandering(controller, pig)
        else:
            pig.log_behavior("Nothing urgent, idling")
            pig.behavior_state = BehaviorState.IDLE
            pig.target_position = None
            pig.target_facility_id = None
            pig.target_description = None
            pig.path = []


def _try_campfire_attraction(
    controller: "BehaviorController", pig: GuineaPig,
) -> None:
    """At night, bias idle/wandering pigs to seek nearby campfires.

    If a campfire is within 10 cells, the pig seeks it for socializing.
    Only triggers if the pig isn't already heading somewhere.
    """
    if pig.target_facility_id or pig.path:
        return

    campfires = controller.game_state.get_facilities_by_type(FacilityType.CAMPFIRE)
    if not campfires:
        return

    failed = controller.facility_manager.get_failed_facilities(pig.id)
    radius_sq = AOE_ATTRACTION_RADIUS ** 2
    for campfire in campfires:
        if campfire.id in failed:
            continue
        center_x = campfire.position_x + campfire.width / 2.0
        center_y = campfire.position_y + campfire.height / 2.0
        dx = pig.position.x - center_x
        dy = pig.position.y - center_y
        if dx * dx + dy * dy <= radius_sq:
            # Try to path to the campfire
            result = controller.facility_manager.find_open_interaction_point(pig, campfire)
            if result:
                target, path = result
                pig.path = path
                if pig.path:
                    pig.log_behavior(f"Drawn to {campfire.name} at night")
                    pig.behavior_state = BehaviorState.WANDERING
                    pig.target_facility_id = campfire.id
                    pig.target_position = Position(x=float(target[0]), y=float(target[1]))
                    pig.target_description = f"going to {campfire.name}"
                    return
