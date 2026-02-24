"""Automatic resource management — drip system, auto-feeders, veggie garden."""

from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState

# Facility types affected by automation perks
FOOD_WATER_TYPES = frozenset({
    FacilityType.FOOD_BOWL,
    FacilityType.HAY_RACK,
    FacilityType.WATER_BOTTLE,
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
