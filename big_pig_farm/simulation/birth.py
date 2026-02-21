"""Birth, aging, pigdex registration, and breeding filter mechanics."""

import random

from big_pig_farm.data.config import BREEDING, GENETICS, SIMULATION
from big_pig_farm.data.names import generate_unique_name
from big_pig_farm.entities.biomes import BIOMES
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.genetics import breed as breed_genetics
from big_pig_farm.entities.genetics import calculate_phenotype
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.entities.pigdex import get_discovery_reward, get_milestone_reward, key_to_rarity, phenotype_key
from big_pig_farm.simulation.breeding_program import should_keep_pig


def check_births(game_state) -> int:
    """Check for and process births from existing pregnancies. Returns number of births."""
    births = 0
    for pig in game_state.get_pigs_list():
        if pig.is_pregnant:
            if _check_birth(pig, game_state):
                births += 1
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
        _cancel_pregnancy(mother, game_state, "farm is at capacity")
        return False

    # Find father — use stored genotype/name from conception so the birth
    # proceeds even if the father was sold after conception
    father = game_state.get_guinea_pig(mother.partner_id) if mother.partner_id else None
    father_genotype = mother.partner_genotype or (father.genotype if father else None)
    father_name = mother.partner_name or (father.name if father else "Unknown")
    father_id = mother.partner_id

    if father_genotype is None:
        _cancel_pregnancy(mother, game_state, "father's genetics unavailable")
        return False

    # Determine litter size
    litter_size = random.randint(BREEDING.MIN_LITTER_SIZE, BREEDING.MAX_LITTER_SIZE)

    # Don't exceed capacity
    available_space = game_state.capacity - game_state.pig_count
    litter_size = min(litter_size, available_space)

    if litter_size <= 0:
        _cancel_pregnancy(mother, game_state, "farm is at capacity")
        return False

    # Get existing names for uniqueness
    existing_names = {p.name for p in game_state.get_pigs_list()}

    # Determine mutation rate based on Genetics Lab
    mutation_rate = GENETICS.MUTATION_RATE
    genetics_labs = game_state.get_facilities_by_type(FacilityType.GENETICS_LAB)
    if genetics_labs:
        mutation_rate = GENETICS.MUTATION_RATE_WITH_LAB

    # Build per-locus rates with biome boosts
    mother_biome = game_state.farm.get_biome_at(int(mother.position.x), int(mother.position.y))
    locus_rates: dict[str, float] | None = None
    if mother_biome:
        biome_info = BIOMES[mother_biome]
        if biome_info.mutation_boost_loci:
            locus_rates = {}
            for locus in ("e_locus", "b_locus", "s_locus", "c_locus", "r_locus"):
                locus_rates[locus] = mutation_rate + biome_info.mutation_boost_loci.get(locus, 0.0)

    # Determine birth area for babies
    birth_area = game_state.farm.get_area_at(int(mother.position.x), int(mother.position.y))
    birth_area_id = birth_area.id if birth_area else None

    babies_born = []
    for _ in range(litter_size):
        # Generate genetics with mutations
        breed_result = breed_genetics(
            mother.genotype, father_genotype,
            mutation_rate=mutation_rate, locus_rates=locus_rates,
        )
        baby_genotype = breed_result.genotype
        calculate_phenotype(baby_genotype)

        # Random gender
        gender = random.choice([Gender.MALE, Gender.FEMALE])

        # Generate unique name
        name = generate_unique_name(existing_names, gender=gender.value)
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
            father_id=father_id,
            mother_name=mother.name,
            father_name=father_name,
        )

        # Set area/biome fields
        baby.birth_area_id = birth_area_id
        baby.current_area_id = birth_area_id
        if birth_area:
            baby.preferred_biome = birth_area.biome.value

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
        register_pig_in_pigdex(game_state, baby)

    # Apply breeding filter to newborns
    _apply_breeding_filter(game_state, babies_born)

    # Reset mother's pregnancy state
    mother.is_pregnant = False
    mother.pregnancy_days = 0.0
    mother.last_birth_age = mother.age_days
    mother.partner_id = None
    mother.partner_genotype = None
    mother.partner_name = None

    # Log event
    baby_names = ", ".join(b.name for b in babies_born)
    game_state.log_event(
        f"{mother.name} gave birth to {litter_size} baby(s): {baby_names}",
        event_type="birth",
    )

    return True


def _cancel_pregnancy(mother: GuineaPig, game_state, reason: str) -> None:
    """Cancel a pregnancy and log the event."""
    mother.is_pregnant = False
    mother.pregnancy_days = 0.0
    mother.partner_id = None
    mother.partner_genotype = None
    mother.partner_name = None
    game_state.log_event(
        f"{mother.name}'s pregnancy ended - {reason}.",
        event_type="birth",
    )


def advance_pregnancies(game_state, game_hours: float) -> None:
    """Advance pregnancy progress for all pregnant pigs."""
    game_days = game_hours / 24.0
    for pig in game_state.get_pigs_list():
        if pig.is_pregnant:
            pig.pregnancy_days += game_days


def age_all_pigs(game_state, game_hours: float) -> list[GuineaPig]:
    """Age all guinea pigs. Returns list of pigs that died of old age."""
    game_days = game_hours / 24.0
    deaths = []

    for pig in game_state.get_pigs_list():
        pig.age_days += game_days

        # Check for death from old age
        if pig.age_days >= SIMULATION.MAX_AGE_DAYS:
            if random.random() < BREEDING.OLD_AGE_DEATH_RATE * game_days:
                deaths.append(pig)

    # Process deaths
    for pig in deaths:
        game_state.remove_guinea_pig(pig.id)
        game_state.log_event(
            f"{pig.name} passed away peacefully at age {int(pig.age_days)} days.",
            event_type="death",
        )

    return deaths


def register_pig_in_pigdex(game_state, pig: GuineaPig) -> None:
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


def _apply_breeding_filter(game_state, babies: list[GuineaPig]) -> None:
    """Mark newborns that don't match the breeding program target for auto-sell."""
    program = game_state.breeding_program
    if not program.enabled:
        return

    # Skip filter when still growing toward the stock limit
    adults = [p for p in game_state.get_pigs_list() if not p.is_baby]
    effective_limit = max(program.stock_limit, BREEDING.MIN_BREEDING_POPULATION)
    if len(adults) <= effective_limit:
        return

    has_lab = bool(game_state.get_facilities_by_type(FacilityType.GENETICS_LAB))
    marked = []
    for baby in babies:
        if not should_keep_pig(program, baby, has_genetics_lab=has_lab):
            baby.marked_for_sale = True
            marked.append(baby.name)

    if marked:
        game_state.log_event(
            f"Breeding program: {len(marked)} of {len(babies)} marked for sale ({', '.join(marked)})",
            event_type="filter",
        )
