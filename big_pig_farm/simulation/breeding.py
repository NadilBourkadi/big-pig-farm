"""Reproduction, pregnancy, and birth mechanics."""

import random
from datetime import datetime
from typing import Optional
from uuid import UUID

from big_pig_farm.data.config import BREEDING
from big_pig_farm.data.names import generate_unique_name
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, BehaviorState, Position
from big_pig_farm.entities.genetics import breed as breed_genetics, calculate_phenotype


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
        return False

    # Find father
    father = None
    if mother.partner_id:
        father = game_state.get_guinea_pig(mother.partner_id)

    if father is None:
        # Can't give birth without father genetics on record
        mother.is_pregnant = False
        return False

    # Determine litter size
    litter_size = random.randint(BREEDING.MIN_LITTER_SIZE, BREEDING.MAX_LITTER_SIZE)

    # Don't exceed capacity
    available_space = game_state.capacity - game_state.pig_count
    litter_size = min(litter_size, available_space)

    if litter_size <= 0:
        return False

    # Get existing names for uniqueness
    existing_names = {p.name for p in game_state.get_pigs_list()}

    babies_born = []
    for _ in range(litter_size):
        # Generate genetics
        baby_genotype = breed_genetics(mother.genotype, father.genotype)
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

    # Reset mother's pregnancy state
    mother.is_pregnant = False
    mother.pregnancy_days = 0.0
    mother.last_birth_time = datetime.now()
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
    if distance > 3.0:
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
    base_chance = 0.05  # 5% per check

    # Bonus from breeding den
    from big_pig_farm.entities.facilities import FacilityType
    breeding_dens = game_state.get_facilities_by_type(FacilityType.BREEDING_DEN)
    if breeding_dens:
        base_chance += 0.10

    # Bonus from high happiness
    avg_happiness = (male.needs.happiness + female.needs.happiness) / 2
    if avg_happiness > 80:
        base_chance += 0.05

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


def age_all_pigs(game_state, game_hours: float) -> list[GuineaPig]:
    """Age all guinea pigs. Returns list of pigs that died of old age."""
    from big_pig_farm.data.config import SIMULATION

    game_days = game_hours / 24.0
    deaths = []

    for pig in game_state.get_pigs_list():
        pig.age_days += game_days

        # Check for death from old age
        if pig.age_days >= SIMULATION.MAX_AGE_DAYS:
            if random.random() < 0.1 * game_days:  # Increasing chance
                deaths.append(pig)

    # Process deaths
    for pig in deaths:
        game_state.remove_guinea_pig(pig.id)
        game_state.log_event(
            f"{pig.name} passed away peacefully at age {int(pig.age_days)} days.",
            event_type="death",
        )

    return deaths
