"""Reproduction, pregnancy, and birth mechanics."""

import random
from typing import Optional
from uuid import UUID

from big_pig_farm.data.config import BREEDING, GENETICS, SIMULATION
from big_pig_farm.data.names import generate_unique_name
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, BehaviorState, Position
from big_pig_farm.entities.genetics import breed as breed_genetics, calculate_phenotype
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.pigdex import phenotype_key, get_discovery_reward, key_to_rarity, get_milestone_reward


def check_breeding_opportunities(game_state) -> int:
    """Check for and process breeding opportunities. Returns number of births."""
    births = 0

    # Process existing pregnancies
    for pig in game_state.get_pigs_list():
        if pig.is_pregnant:
            if _check_birth(pig, game_state):
                births += 1

    # Check for new breeding pairs
    if not game_state.is_at_capacity:
        _check_for_new_breeding(game_state)

    return births


def _check_birth(mother: GuineaPig, game_state) -> bool:
    """Check if a pregnant pig should give birth. Returns True if birth occurred."""
    if not mother.is_pregnant:
        return False

    if mother.pregnancy_days >= BREEDING.GESTATION_DAYS:
        return _process_birth(mother, game_state)

    return False


def _process_birth(mother: GuineaPig, game_state) -> bool:
    """Process a birth event. Returns True if successful."""
    if game_state.is_at_capacity:
        mother.is_pregnant = False
        mother.pregnancy_days = 0.0
        mother.partner_id = None
        game_state.log_event(
            f"{mother.name}'s pregnancy ended - farm is at capacity.",
            event_type="birth",
        )
        return False

    # Find father
    father = None
    if mother.partner_id:
        father = game_state.get_guinea_pig(mother.partner_id)

    if father is None:
        mother.is_pregnant = False
        mother.pregnancy_days = 0.0
        mother.partner_id = None
        game_state.log_event(
            f"{mother.name}'s pregnancy ended - father is no longer on the farm.",
            event_type="birth",
        )
        return False

    # Determine litter size
    litter_size = random.randint(BREEDING.MIN_LITTER_SIZE, BREEDING.MAX_LITTER_SIZE)

    # Don't exceed capacity
    available_space = game_state.capacity - game_state.pig_count
    litter_size = min(litter_size, available_space)

    if litter_size <= 0:
        mother.is_pregnant = False
        mother.pregnancy_days = 0.0
        mother.partner_id = None
        game_state.log_event(
            f"{mother.name}'s pregnancy ended - farm is at capacity.",
            event_type="birth",
        )
        return False

    # Get existing names for uniqueness
    existing_names = {p.name for p in game_state.get_pigs_list()}

    # Determine mutation rate based on Genetics Lab
    mutation_rate = GENETICS.MUTATION_RATE
    genetics_labs = game_state.get_facilities_by_type(FacilityType.GENETICS_LAB)
    if genetics_labs:
        mutation_rate = GENETICS.MUTATION_RATE_WITH_LAB

    babies_born = []
    for _ in range(litter_size):
        # Generate genetics with mutations
        breed_result = breed_genetics(mother.genotype, father.genotype, mutation_rate=mutation_rate)
        baby_genotype = breed_result.genotype
        baby_phenotype = calculate_phenotype(baby_genotype)

        # Random gender
        gender = random.choice([Gender.MALE, Gender.FEMALE])

        # Generate unique name
        name = generate_unique_name(existing_names)
        existing_names.add(name)

        # Position near mother
        baby_pos = Position(
            x=mother.position.x + random.uniform(-1, 1),
            y=mother.position.y + random.uniform(-1, 1),
        )

        # Create baby
        baby = GuineaPig.create(
            name=name,
            gender=gender,
            genotype=baby_genotype,
            position=baby_pos,
            age_days=0,
            mother_id=mother.id,
            father_id=father.id,
            mother_name=mother.name,
            father_name=father.name,
        )

        game_state.add_guinea_pig(baby)
        game_state.total_pigs_born += 1
        babies_born.append(baby)

        # Log mutations
        if breed_result.mutations:
            mutation_desc = ", ".join(breed_result.mutations)
            game_state.log_event(
                f"{baby.name} was born with a mutation! ({mutation_desc})",
                event_type="mutation",
            )

        # Register in pigdex
        _register_pigdex(game_state, baby)

    # Reset mother's pregnancy state
    mother.is_pregnant = False
    mother.pregnancy_days = 0.0
    mother.last_birth_age = mother.age_days
    mother.partner_id = None

    # Log event
    baby_names = ", ".join(b.name for b in babies_born)
    game_state.log_event(
        f"{mother.name} gave birth to {litter_size} baby(s): {baby_names}",
        event_type="birth",
    )

    return True


def _check_for_new_breeding(game_state) -> None:
    """Check if any pigs should start breeding."""
    # Get eligible males and females
    males = [
        p for p in game_state.get_pigs_list()
        if p.gender == Gender.MALE and p.can_breed
    ]
    females = [
        p for p in game_state.get_pigs_list()
        if p.gender == Gender.FEMALE and p.can_breed and not p.is_pregnant
    ]

    if not males or not females:
        return

    # Check for pairs that are close enough and happy enough
    for female in females:
        for male in males:
            if _can_breed_together(male, female, game_state):
                if _attempt_breeding(male, female, game_state):
                    return  # One breeding per check


def _can_breed_together(male: GuineaPig, female: GuineaPig, game_state) -> bool:
    """Check if two guinea pigs can breed together."""
    # Both must be able to breed
    if not male.can_breed or not female.can_breed:
        return False

    # Must be close enough
    distance = male.position.distance_to(female.position)
    if distance > BREEDING.BREEDING_DISTANCE:
        return False

    # Check for inbreeding (warn but allow)
    if _are_closely_related(male, female, game_state):
        # Could add warning here
        pass

    return True


def _are_closely_related(pig1: GuineaPig, pig2: GuineaPig, game_state) -> bool:
    """Check if two pigs are closely related (parent/child or siblings)."""
    # Same parents = siblings
    if pig1.mother_id and pig1.mother_id == pig2.mother_id:
        return True
    if pig1.father_id and pig1.father_id == pig2.father_id:
        return True

    # Parent/child
    if pig1.id == pig2.mother_id or pig1.id == pig2.father_id:
        return True
    if pig2.id == pig1.mother_id or pig2.id == pig1.father_id:
        return True

    return False


def _attempt_breeding(male: GuineaPig, female: GuineaPig, game_state) -> bool:
    """Attempt to start a breeding event. Returns True if successful."""
    # Random chance based on conditions
    base_chance = BREEDING.BASE_BREEDING_CHANCE

    # Bonus from breeding den
    breeding_dens = game_state.get_facilities_by_type(FacilityType.BREEDING_DEN)
    if breeding_dens:
        base_chance += BREEDING.BREEDING_DEN_BONUS

    # Bonus from high happiness
    avg_happiness = (male.needs.happiness + female.needs.happiness) / 2
    if avg_happiness > BREEDING.HIGH_HAPPINESS_THRESHOLD:
        base_chance += BREEDING.HIGH_HAPPINESS_BONUS

    if random.random() > base_chance:
        return False

    # Start pregnancy
    female.is_pregnant = True
    female.pregnancy_days = 0.0
    female.partner_id = male.id

    # Set courting behavior
    male.behavior_state = BehaviorState.COURTING
    female.behavior_state = BehaviorState.COURTING

    game_state.log_event(
        f"{male.name} and {female.name} are expecting!",
        event_type="breeding",
    )

    return True


def advance_pregnancies(game_state, game_hours: float) -> None:
    """Advance pregnancy progress for all pregnant pigs."""
    game_days = game_hours / 24.0

    for pig in game_state.get_pigs_list():
        if pig.is_pregnant:
            pig.pregnancy_days += game_days


def _register_pigdex(game_state, pig: GuineaPig) -> None:
    """Register a pig's phenotype in the pigdex with rewards."""
    key = phenotype_key(pig.phenotype)
    game_day = game_state.game_time.day
    is_new = game_state.pigdex.register_phenotype(key, game_day)

    if is_new:
        rarity = key_to_rarity(key)
        reward = get_discovery_reward(rarity)
        game_state.add_money(reward)
        game_state.log_event(
            f"Pigdex: New discovery! {pig.phenotype.display_name} ({rarity.value.title()}) +{reward} Squeaks",
            event_type="pigdex",
        )

        # Check milestones
        milestones = game_state.pigdex.check_milestones()
        for threshold in milestones:
            milestone_reward = get_milestone_reward(threshold)
            game_state.pigdex.claim_milestone(threshold)
            game_state.add_money(milestone_reward)
            game_state.log_event(
                f"Pigdex Milestone: {threshold}% complete! +{milestone_reward} Squeaks",
                event_type="pigdex",
            )


def register_pig_in_pigdex(game_state, pig: GuineaPig) -> None:
    """Public function to register a pig in the pigdex (for adoption, loading, etc.)."""
    _register_pigdex(game_state, pig)


def age_all_pigs(game_state, game_hours: float) -> list[GuineaPig]:
    """Age all guinea pigs. Returns list of pigs that died of old age."""
    game_days = game_hours / 24.0
    deaths = []

    for pig in game_state.get_pigs_list():
        pig.age_days += game_days

        # Check for death from old age
        if pig.age_days >= SIMULATION.MAX_AGE_DAYS:
            if random.random() < BREEDING.OLD_AGE_DEATH_RATE * game_days:  # Increasing chance
                deaths.append(pig)

    # Process deaths
    for pig in deaths:
        game_state.remove_guinea_pig(pig.id)
        game_state.log_event(
            f"{pig.name} passed away peacefully at age {int(pig.age_days)} days.",
            event_type="death",
        )

    return deaths
