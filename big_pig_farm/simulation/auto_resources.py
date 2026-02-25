"""Automatic resource management — drip system, auto-feeders, veggie garden, AoE."""

from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.guinea_pig import BehaviorState
from big_pig_farm.game.state import GameState

# Facility types affected by automation perks
FOOD_WATER_TYPES = frozenset({
    FacilityType.FOOD_BOWL,
    FacilityType.HAY_RACK,
    FacilityType.WATER_BOTTLE,
    FacilityType.FEAST_TABLE,
})

DRIP_RATE_PER_HOUR = 2.0
AUTO_REFILL_THRESHOLD = 0.25


def tick_auto_resources(state: GameState, game_hours: float) -> None:
    """Run all automatic resource systems for this tick."""
    has_drip = state.has_upgrade("drip_system")
    has_auto = state.has_upgrade("auto_feeders")

    if not has_drip and not has_auto:
        return

    for facility in state.get_facilities_list():
        if facility.facility_type not in FOOD_WATER_TYPES:
            continue

        # Drip first (passive trickle), then auto-refill if still low
        if has_drip:
            facility.refill(DRIP_RATE_PER_HOUR * game_hours)
        if has_auto and facility.fill_percentage < AUTO_REFILL_THRESHOLD * 100:
            facility.refill()


def apply_bulk_feeders(state: GameState) -> None:
    """Double max capacity of all existing food/water facilities.

    Called once when Bulk Feeders perk is purchased. New facilities
    created afterward also get doubled capacity via Facility.create()
    checking state.has_upgrade("bulk_feeders").
    """
    for facility in state.get_facilities_list():
        if facility.facility_type in FOOD_WATER_TYPES:
            facility.max_amount *= 2
            facility.current_amount *= 2


def tick_veggie_gardens(state: GameState, game_hours: float) -> None:
    """Veggie gardens produce food and distribute to nearby bowls/hay racks."""
    gardens = state.get_facilities_by_type(FacilityType.VEGGIE_GARDEN)
    if not gardens:
        return

    food_facilities = (
        state.get_facilities_by_type(FacilityType.FOOD_BOWL)
        + state.get_facilities_by_type(FacilityType.HAY_RACK)
        + state.get_facilities_by_type(FacilityType.FEAST_TABLE)
    )
    if not food_facilities:
        return

    for garden in gardens:
        production = garden.info.food_production * game_hours
        if production <= 0:
            continue

        # Distribute evenly to food facilities that aren't full
        targets = [f for f in food_facilities if f.current_amount < f.max_amount]
        if not targets:
            continue

        per_target = production / len(targets)
        for target in targets:
            target.refill(per_target)


# --- AoE facility effects ---

# Stage audience receives passive happiness/social within this radius
STAGE_AUDIENCE_RADIUS = 6.0
# Campfire and Stage draw idle/wandering pigs within this radius
AOE_ATTRACTION_RADIUS = 10.0
# Stage audience bonuses per game hour
STAGE_AUDIENCE_HAPPINESS_PER_HOUR = 2.0
STAGE_AUDIENCE_SOCIAL_PER_HOUR = 1.5


def tick_aoe_facilities(state: GameState, game_hours: float) -> None:
    """Apply AoE effects from Stage and Campfire facilities.

    Stage: pigs within 6 cells of an active performer get passive
    happiness and social recovery.

    Campfire: at night, idle/wandering pigs near a campfire get a
    small wander bias toward it (handled in behavior_decision).
    This function only applies the passive AoE bonuses.
    """
    pigs = state.get_pigs_list()
    if not pigs:
        return

    # Stage AoE: find stages with an active performer (PLAYING pig targeting it)
    stages = state.get_facilities_by_type(FacilityType.STAGE)
    for stage in stages:
        # Check if a performer is using the stage
        has_performer = any(
            pig.behavior_state == BehaviorState.PLAYING
            and pig.target_facility_id == stage.id
            for pig in pigs
        )
        if not has_performer:
            continue

        # Apply passive bonuses to all pigs within audience radius
        stage_x = stage.position_x + stage.width / 2.0
        stage_y = stage.position_y + stage.height / 2.0
        radius_sq = STAGE_AUDIENCE_RADIUS ** 2

        for pig in pigs:
            # Don't double-apply to the performer
            if pig.target_facility_id == stage.id and pig.behavior_state == BehaviorState.PLAYING:
                continue
            dx = pig.position.x - stage_x
            dy = pig.position.y - stage_y
            if dx * dx + dy * dy <= radius_sq:
                pig.needs.happiness = min(
                    100, pig.needs.happiness + STAGE_AUDIENCE_HAPPINESS_PER_HOUR * game_hours,
                )
                pig.needs.social = min(
                    100, pig.needs.social + STAGE_AUDIENCE_SOCIAL_PER_HOUR * game_hours,
                )
