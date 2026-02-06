"""Hunger, energy, happiness calculations for guinea pigs."""

from big_pig_farm.data.config import NEEDS
from big_pig_farm.entities.guinea_pig import GuineaPig, Personality, BehaviorState
from big_pig_farm.entities.facilities import FacilityType


def update_all_needs(pig: GuineaPig, game_minutes: float, game_state) -> None:
    """Update all needs for a guinea pig based on elapsed game time."""
    hours = game_minutes / 60.0

    # Apply personality modifiers
    hunger_modifier = 1.5 if pig.has_trait(Personality.GREEDY) else 1.0
    energy_modifier = 0.7 if pig.has_trait(Personality.LAZY) else 1.0
    boredom_modifier = 1.5 if pig.has_trait(Personality.PLAYFUL) else 1.0
    social_modifier = 1.3 if pig.has_trait(Personality.SOCIAL) else 1.0
    if pig.has_trait(Personality.SHY):
        social_modifier = 0.5

    # Decay primary needs
    pig.needs.hunger -= NEEDS.HUNGER_DECAY * hours * hunger_modifier
    pig.needs.thirst -= NEEDS.THIRST_DECAY * hours
    pig.needs.energy -= NEEDS.ENERGY_DECAY * hours * energy_modifier

    # Happiness decay - faster when other needs are low
    happiness_decay = NEEDS.HAPPINESS_BASE_DECAY
    if pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD:
        happiness_decay *= 2
    if pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD:
        happiness_decay *= 2
    if pig.needs.energy < NEEDS.CRITICAL_THRESHOLD:
        happiness_decay *= 1.5

    pig.needs.happiness -= happiness_decay * hours

    # Boredom increases over time
    pig.needs.boredom += 3.0 * hours * boredom_modifier
    if pig.needs.boredom > 70:
        pig.needs.happiness -= 1.0 * hours

    # Social need decay - reduced if near other pigs
    nearby_pigs = _count_nearby_pigs(pig, game_state, radius=8.0)
    if nearby_pigs > 0:
        # Being near other pigs satisfies social need passively
        # More pigs nearby = more social satisfaction
        social_boost = min(nearby_pigs * 3.0, 8.0) * hours
        pig.needs.social += social_boost
        # Slower decay when not alone
        pig.needs.social -= 0.5 * hours * social_modifier
    else:
        # Alone - normal decay
        pig.needs.social -= 2.0 * hours * social_modifier

    # Health effects from critically low needs
    if pig.needs.hunger < NEEDS.CRITICAL_THRESHOLD:
        pig.needs.health -= 0.5 * hours
    if pig.needs.thirst < NEEDS.CRITICAL_THRESHOLD:
        pig.needs.health -= 1.0 * hours

    # Recovery from current behavior
    _apply_behavior_recovery(pig, game_minutes, game_state)

    # Clamp all values
    pig.needs.clamp_all()


def _apply_behavior_recovery(pig: GuineaPig, game_minutes: float, game_state) -> None:
    """Apply need recovery based on current behavior."""
    hours = game_minutes / 60.0

    if pig.behavior_state == BehaviorState.EATING:
        pig.needs.hunger += NEEDS.FOOD_RECOVERY * hours * 2
        pig.needs.happiness += 2.0 * hours

    elif pig.behavior_state == BehaviorState.DRINKING:
        pig.needs.thirst += NEEDS.WATER_RECOVERY * hours * 2

    elif pig.behavior_state == BehaviorState.SLEEPING:
        pig.needs.energy += NEEDS.SLEEP_RECOVERY_PER_HOUR * hours
        pig.needs.health += 0.5 * hours

    elif pig.behavior_state == BehaviorState.PLAYING:
        pig.needs.happiness += NEEDS.PLAY_HAPPINESS_BOOST * hours
        pig.needs.boredom -= 15.0 * hours
        pig.needs.energy -= 1.0 * hours  # Playing uses energy

    elif pig.behavior_state == BehaviorState.SOCIALIZING:
        pig.needs.happiness += NEEDS.SOCIAL_HAPPINESS_BOOST * hours
        pig.needs.social += 10.0 * hours


def _count_nearby_pigs(pig: GuineaPig, game_state, radius: float) -> int:
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
        "hunger": [FacilityType.HAY_RACK, FacilityType.FOOD_BOWL],  # Prefer hay (tier 2, has health bonus)
        "thirst": [FacilityType.WATER_BOTTLE],
        "energy": [FacilityType.HIDEOUT],
        "happiness": [FacilityType.PLAY_AREA, FacilityType.EXERCISE_WHEEL, FacilityType.TUNNEL],
        "social": [FacilityType.PLAY_AREA],
    }
    return need_to_facilities.get(need)


def calculate_overall_wellbeing(pig: GuineaPig) -> float:
    """Calculate an overall wellbeing score (0-100)."""
    weights = {
        "hunger": 0.25,
        "thirst": 0.25,
        "energy": 0.15,
        "happiness": 0.20,
        "health": 0.15,
    }

    score = (
        pig.needs.hunger * weights["hunger"]
        + pig.needs.thirst * weights["thirst"]
        + pig.needs.energy * weights["energy"]
        + pig.needs.happiness * weights["happiness"]
        + pig.needs.health * weights["health"]
    )

    return score
