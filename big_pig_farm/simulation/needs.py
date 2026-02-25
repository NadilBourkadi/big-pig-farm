"""Hunger, energy, happiness calculations for guinea pigs."""

from typing import TYPE_CHECKING
from uuid import UUID

from big_pig_farm.data.config import BIOME, NEEDS
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.guinea_pig import BehaviorState, GuineaPig, Personality

if TYPE_CHECKING:
    from big_pig_farm.game.facades import NeedsContext
    from big_pig_farm.simulation.collision import SpatialGrid


def precompute_nearby_counts(
    pigs: list[GuineaPig], radius: float,
    spatial_grid: "SpatialGrid | None" = None,
) -> dict[UUID, int]:
    """Count nearby pigs for every pig.

    When a spatial_grid is provided (rebuilt earlier in the tick), uses
    O(n * k) bucket lookups instead of O(n²/2) all-pairs.
    """
    counts: dict[UUID, int] = {p.id: 0 for p in pigs}
    radius_sq = radius * radius

    if spatial_grid is not None:
        for pig in pigs:
            for other in spatial_grid.get_nearby(pig.position.x, pig.position.y):
                if other.id == pig.id:
                    continue
                dx = pig.position.x - other.position.x
                dy = pig.position.y - other.position.y
                if dx * dx + dy * dy <= radius_sq:
                    counts[pig.id] += 1
    else:
        for i in range(len(pigs)):
            a = pigs[i]
            for j in range(i + 1, len(pigs)):
                b = pigs[j]
                dx = a.position.x - b.position.x
                dy = a.position.y - b.position.y
                if dx * dx + dy * dy <= radius_sq:
                    counts[a.id] += 1
                    counts[b.id] += 1

    return counts


def update_all_needs(
    pig: GuineaPig, game_minutes: float, game_state: "NeedsContext",
    nearby_count: int | None = None,
) -> None:
    """Update all needs for a guinea pig based on elapsed game time."""
    hours = game_minutes / 60.0

    # Apply personality modifiers
    hunger_modifier = NEEDS.GREEDY_HUNGER_MULT if pig.has_trait(Personality.GREEDY) else 1.0
    energy_modifier = NEEDS.LAZY_ENERGY_MULT if pig.has_trait(Personality.LAZY) else 1.0
    boredom_modifier = NEEDS.PLAYFUL_BOREDOM_MULT if pig.has_trait(Personality.PLAYFUL) else 1.0
    social_modifier = NEEDS.SOCIAL_SOCIAL_MULT if pig.has_trait(Personality.SOCIAL) else 1.0
    if pig.has_trait(Personality.SHY):
        social_modifier = NEEDS.SHY_SOCIAL_MULT

    # Decay primary needs
    pig.needs.hunger -= NEEDS.HUNGER_DECAY * hours * hunger_modifier
    pig.needs.thirst -= NEEDS.THIRST_DECAY * hours
    pig.needs.energy -= NEEDS.ENERGY_DECAY * hours * energy_modifier

    # Contentment: happiness passively recovers when basic needs are met.
    # Energy uses the critical threshold (20) instead of low (40) so that
    # pigs with moderate energy still get passive happiness recovery —
    # prevents the eat→sleep death spiral where happiness stays at 0.
    needs_satisfied = (pig.needs.hunger >= NEEDS.LOW_THRESHOLD
                       and pig.needs.thirst >= NEEDS.LOW_THRESHOLD
                       and pig.needs.energy >= NEEDS.CRITICAL_THRESHOLD)
    if needs_satisfied:
        pig.needs.happiness += NEEDS.HAPPINESS_CONTENTMENT_RECOVERY * hours

    # Preferred biome bonus
    if pig.preferred_biome and game_state and hasattr(game_state, 'farm'):
        current_biome = game_state.farm.get_biome_at(int(pig.position.x), int(pig.position.y))
        if current_biome and current_biome.value == pig.preferred_biome:
            pig.needs.happiness += BIOME.PREFERRED_BIOME_HAPPINESS_BONUS * hours

    # Climate Control perk: all biomes grant +0.3 happiness/hr
    if game_state and game_state.has_upgrade("climate_control"):
        pig.needs.happiness += 0.3 * hours

    # Critical needs directly drain happiness
    if pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD:
        pig.needs.happiness -= NEEDS.HUNGER_HAPPINESS_DRAIN * hours
    if pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD:
        pig.needs.happiness -= NEEDS.THIRST_HAPPINESS_DRAIN * hours
    if pig.needs.energy < NEEDS.CRITICAL_THRESHOLD:
        pig.needs.happiness -= NEEDS.ENERGY_HAPPINESS_DRAIN * hours

    # Enrichment Program perk: boredom grows 20% slower
    if game_state and game_state.has_upgrade("enrichment_program"):
        boredom_modifier *= 0.8

    # Boredom increases over time
    pig.needs.boredom += NEEDS.BOREDOM_DECAY * hours * boredom_modifier
    if pig.needs.boredom > NEEDS.BOREDOM_EXTRA_HAPPINESS_THRESHOLD:
        pig.needs.happiness -= NEEDS.BOREDOM_EXTRA_HAPPINESS_DRAIN * hours

    # Social need decay - reduced if near other pigs
    nearby_pigs = nearby_count if nearby_count is not None else _count_nearby_pigs(pig, game_state, radius=NEEDS.SOCIAL_RADIUS)
    if nearby_pigs > 0:
        # Being near other pigs satisfies social need passively
        # More pigs nearby = more social satisfaction
        social_boost = min(nearby_pigs * NEEDS.SOCIAL_BOOST_PER_PIG, NEEDS.SOCIAL_BOOST_CAP) * hours
        pig.needs.social += social_boost
        # Slower decay when not alone
        pig.needs.social -= NEEDS.SOCIAL_DECAY_WITH_PIGS * hours * social_modifier
    else:
        # Alone - normal decay
        pig.needs.social -= NEEDS.SOCIAL_DECAY_ALONE * hours * social_modifier

    # Health effects from critically low needs
    if pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD:
        pig.needs.health -= NEEDS.HEALTH_DRAIN_HUNGER * hours
    if pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD:
        pig.needs.health -= NEEDS.HEALTH_DRAIN_THIRST * hours

    # Passive health recovery when no primary need is critical
    if (pig.needs.hunger >= NEEDS.CRITICAL_THRESHOLD
            and pig.needs.thirst >= NEEDS.CRITICAL_THRESHOLD):
        health_recovery = NEEDS.HEALTH_PASSIVE_RECOVERY
        # Pig Spa perk: passive health recovery doubled
        if game_state and game_state.has_upgrade("pig_spa"):
            health_recovery *= 2.0
        pig.needs.health += health_recovery * hours

    # Recovery from current behavior
    _apply_behavior_recovery(pig, game_minutes, game_state)

    # Clamp all values
    pig.needs.clamp_all()


def _apply_behavior_recovery(pig: GuineaPig, game_minutes: float, game_state: "NeedsContext") -> None:
    """Apply need recovery based on current behavior."""
    hours = game_minutes / 60.0

    if pig.behavior_state == BehaviorState.EATING:
        pig.needs.hunger += NEEDS.FOOD_RECOVERY * hours * 2
        pig.needs.happiness += NEEDS.EATING_HAPPINESS_BOOST * hours

    elif pig.behavior_state == BehaviorState.DRINKING:
        pig.needs.thirst += NEEDS.WATER_RECOVERY * hours * 2

    elif pig.behavior_state == BehaviorState.SLEEPING:
        sleep_recovery = NEEDS.SLEEP_RECOVERY_PER_HOUR
        # Premium Bedding perk: +25% sleep energy recovery
        if game_state and game_state.has_upgrade("premium_bedding"):
            sleep_recovery *= 1.25
        pig.needs.energy += sleep_recovery * hours
        pig.needs.health += NEEDS.HEALTH_SLEEP_RECOVERY * hours

    elif pig.behavior_state == BehaviorState.PLAYING:
        pig.needs.happiness += NEEDS.PLAY_HAPPINESS_BOOST * hours
        pig.needs.boredom -= NEEDS.BOREDOM_PLAY_RECOVERY * hours
        pig.needs.energy -= NEEDS.PLAY_ENERGY_COST * hours  # Playing uses energy

    elif pig.behavior_state == BehaviorState.SOCIALIZING:
        pig.needs.happiness += NEEDS.SOCIAL_HAPPINESS_BOOST * hours
        pig.needs.social += NEEDS.SOCIAL_RECOVERY * hours


def _count_nearby_pigs(pig: GuineaPig, game_state: "NeedsContext", radius: float) -> int:
    """Count how many other pigs are within the given radius."""
    count = 0
    for other in game_state.get_pigs_list():
        if other.id != pig.id:
            distance = pig.position.distance_to(other.position)
            if distance <= radius:
                count += 1
    return count


def get_most_urgent_need(pig: GuineaPig) -> str:
    """Determine which need is most urgent and should be addressed."""
    needs_priority = [
        ("thirst", pig.needs.thirst, NEEDS.CRITICAL_THRESHOLD),
        ("hunger", pig.needs.hunger, NEEDS.CRITICAL_THRESHOLD),
        ("energy", pig.needs.energy, NEEDS.LOW_THRESHOLD),
        ("happiness", pig.needs.happiness, NEEDS.LOW_THRESHOLD),
        ("social", pig.needs.social, NEEDS.LOW_THRESHOLD),
    ]

    # Find the most critical need
    for need_name, value, threshold in needs_priority:
        if value < threshold:
            return need_name

    # If no critical needs, check for moderately low needs
    for need_name, value, _ in needs_priority:
        if value < NEEDS.HIGH_THRESHOLD:
            return need_name

    return "none"


def get_target_facility_for_need(need: str) -> list[FacilityType] | None:
    """Get facility types that address a specific need (in priority order)."""
    need_to_facilities = {
        "hunger": [FacilityType.HAY_RACK, FacilityType.FEAST_TABLE, FacilityType.FOOD_BOWL],
        "thirst": [FacilityType.WATER_BOTTLE],
        "energy": [FacilityType.HIDEOUT],
        "happiness": [FacilityType.PLAY_AREA, FacilityType.EXERCISE_WHEEL, FacilityType.TUNNEL],
        "social": [FacilityType.PLAY_AREA],
    }
    return need_to_facilities.get(need)


def calculate_overall_wellbeing(pig: GuineaPig) -> float:
    """Calculate an overall wellbeing score (0-100)."""
    score = (
        pig.needs.hunger * NEEDS.WELLBEING_HUNGER_WEIGHT
        + pig.needs.thirst * NEEDS.WELLBEING_THIRST_WEIGHT
        + pig.needs.energy * NEEDS.WELLBEING_ENERGY_WEIGHT
        + pig.needs.happiness * NEEDS.WELLBEING_HAPPINESS_WEIGHT
        + pig.needs.health * NEEDS.WELLBEING_HEALTH_WEIGHT
    )

    return score
