"""Breeding pair selection, courtship initiation, and auto-pairing mechanics."""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from big_pig_farm.game.facades import BreedingContext

from big_pig_farm.data.config import BREEDING
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.genetics import (
    BaseColor,
    ColorIntensity,
    Pattern,
    RoanType,
    calculate_target_probability,
)
from big_pig_farm.entities.guinea_pig import BehaviorState, Gender, GuineaPig
from big_pig_farm.simulation.birth import check_births
from big_pig_farm.simulation.breeding_program import BreedingStrategy


def _is_permanently_unbreedable(pig: GuineaPig) -> bool:
    """True if a pig can never breed again (senior or manually locked)."""
    return pig.breeding_locked or pig.is_senior


def check_breeding_opportunities(game_state: "BreedingContext", run_expensive: bool = True) -> int:
    """Check for and process breeding opportunities. Returns number of births.

    When run_expensive is False, only births and manual pairs are processed
    (the O(m*f) auto-pair and new-pair scans are skipped).
    """
    births = check_births(game_state)

    # Process manual breeding pair before auto-breeding (cheap, runs every tick)
    _check_manual_breeding(game_state)

    if run_expensive:
        # Auto-pair from breeding program if slot is empty
        _auto_pair_from_program(game_state)

        # Check for new breeding pairs (re-fetch: births may have changed the list)
        if not game_state.is_at_capacity:
            _check_for_new_breeding(game_state)

    return births


def _check_manual_breeding(game_state: "BreedingContext") -> None:
    """Process the manually set breeding pair if conditions are met."""
    if game_state.breeding_pair is None:
        return

    pair = game_state.breeding_pair
    male = game_state.get_guinea_pig(pair.male_id)
    female = game_state.get_guinea_pig(pair.female_id)

    # Either pig no longer exists (sold/died)
    if male is None or female is None:
        gone = "male" if male is None else "female"
        game_state.log_event(
            f"Breeding pair cancelled — {gone} no longer on the farm.",
            event_type="breeding",
        )
        game_state.clear_breeding_pair()
        return

    # Female got pregnant by auto-breeding between ticks
    if female.is_pregnant:
        game_state.clear_breeding_pair()
        return

    # Clear pair if either pig permanently can't breed (senior, locked)
    if _is_permanently_unbreedable(male) or _is_permanently_unbreedable(female):
        gone = male.name if _is_permanently_unbreedable(male) else female.name
        game_state.log_event(
            f"Breeding pair cancelled — {gone} can no longer breed.",
            event_type="breeding",
        )
        game_state.clear_breeding_pair()
        return

    # Wait if either can't breed yet (happiness dip, recovery cooldown)
    if not male.can_breed or not female.can_breed:
        return

    # Don't initiate if either pig is already courting
    if male.behavior_state == BehaviorState.COURTING:
        return
    if female.behavior_state == BehaviorState.COURTING:
        return

    # Start physical courtship — male walks to female
    _initiate_courtship(male, female, game_state)
    game_state.clear_breeding_pair()


def _check_for_new_breeding(game_state: "BreedingContext") -> None:
    """Check if any pigs should start breeding."""
    pigs = game_state.get_pigs_list()
    # Get eligible males and females; exclude pigs already courting
    males = [
        p for p in pigs
        if p.gender == Gender.MALE and p.can_breed
        and p.behavior_state != BehaviorState.COURTING
    ]
    females = [
        p for p in pigs
        if p.gender == Gender.FEMALE and p.can_breed
        and not p.is_pregnant
        and p.behavior_state != BehaviorState.COURTING
    ]

    if not males or not females:
        return

    # Check for pairs that are close enough and happy enough
    for female in females:
        for male in males:
            if _can_breed_together(male, female, game_state):
                if _attempt_breeding(male, female, game_state):
                    return  # One breeding per check


def _can_breed_together(male: GuineaPig, female: GuineaPig, game_state: "BreedingContext") -> bool:
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
        pass

    return True


def _are_closely_related(pig1: GuineaPig, pig2: GuineaPig, game_state: "BreedingContext") -> bool:
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


def _attempt_breeding(male: GuineaPig, female: GuineaPig, game_state: "BreedingContext") -> bool:
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

    # Affinity bonus from socialization history
    affinity = game_state.get_affinity(male.id, female.id)
    base_chance += min(affinity * BREEDING.AFFINITY_CHANCE_BONUS, BREEDING.MAX_AFFINITY_CHANCE_BONUS)

    if random.random() > base_chance:
        return False

    # Defense-in-depth: caller already filters courting pigs, but guard here too
    if male.behavior_state == BehaviorState.COURTING:
        return False
    if female.behavior_state == BehaviorState.COURTING:
        return False

    # Start physical courtship instead of instant pregnancy
    _initiate_courtship(male, female, game_state)
    return True


def _initiate_courtship(male: GuineaPig, female: GuineaPig, game_state: "BreedingContext") -> None:
    """Start physical courtship — male will pathfind to female."""
    male.behavior_state = BehaviorState.COURTING
    female.behavior_state = BehaviorState.COURTING
    male.courting_partner_id = female.id
    female.courting_partner_id = male.id
    male.courting_initiator = True
    female.courting_initiator = False
    male.courting_timer = 0.0
    female.courting_timer = 0.0
    # Clear existing movement
    male.path = []
    female.path = []
    male.target_position = None
    female.target_position = None
    male.target_facility_id = None
    female.target_facility_id = None
    male.target_description = f"courting {female.name}"
    female.target_description = f"courting {male.name}"
    game_state.log_event(
        f"{male.name} is courting {female.name}!",
        event_type="breeding",
    )


def start_pregnancy_from_courtship(male: GuineaPig, female: GuineaPig, game_state: "BreedingContext") -> None:
    """Called when courtship completes — starts the actual pregnancy."""
    female.is_pregnant = True
    female.pregnancy_days = 0.0
    female.partner_id = male.id
    female.partner_genotype = male.genotype
    female.partner_name = male.name

    clear_courtship(male)
    clear_courtship(female)

    game_state.log_event(
        f"{male.name} and {female.name} are expecting!",
        event_type="breeding",
    )


def clear_courtship(pig: GuineaPig) -> None:
    """Reset all courtship fields on a pig."""
    pig.courting_partner_id = None
    pig.courting_initiator = False
    pig.courting_timer = 0.0
    if pig.behavior_state == BehaviorState.COURTING:
        pig.behavior_state = BehaviorState.IDLE
    pig.target_description = None


_last_breeding_warning_day: int = -1


def _auto_pair_from_program(game_state: "BreedingContext") -> None:
    """Auto-pair the best breeding pair based on the breeding program target."""
    global _last_breeding_warning_day

    if game_state.breeding_pair is not None:
        return  # Manual pair or previous auto-pair still active

    program = game_state.breeding_program
    if not program.should_auto_pair():
        return

    # Gather eligible pigs (shared across all strategy branches)
    pigs = game_state.get_pigs_list()
    males = [
        p for p in pigs
        if p.gender == Gender.MALE and p.can_breed
        and not p.breeding_locked
        and p.behavior_state != BehaviorState.COURTING
    ]
    females = [
        p for p in pigs
        if p.gender == Gender.FEMALE and p.can_breed
        and not p.is_pregnant and not p.breeding_locked
        and p.behavior_state != BehaviorState.COURTING
    ]

    if not males or not females:
        current_day = game_state.game_time.day
        if current_day != _last_breeding_warning_day:
            _last_breeding_warning_day = current_day
            reasons = []
            if not males:
                reasons.append("no eligible males")
            if not females:
                reasons.append("no eligible females")
            game_state.log_event(
                f"Breeding program: cannot auto-pair — {', '.join(reasons)}",
                event_type="breeding",
            )
        return

    # Diversity mode: pair for genetic distance and rare-color production
    if program.strategy == BreedingStrategy.DIVERSITY:
        _auto_pair_diversity(game_state, males, females)
        return

    # Target/Money modes: pair for target probability
    target_colors = program.target_colors
    target_patterns = program.target_patterns
    target_intensities = program.target_intensities
    target_roan = program.target_roan

    if not program.has_target:
        if program.strategy == BreedingStrategy.MONEY:
            target_colors, target_patterns, target_intensities, target_roan = (
                _derive_contract_targets(game_state)
            )
            if not (target_colors or target_patterns or target_intensities or target_roan):
                return  # No contracts to optimize toward
        else:
            return

    best_pair = None
    best_score = -1.0
    for male in males:
        for female in females:
            prob = calculate_target_probability(
                male.genotype, female.genotype,
                target_colors, target_patterns,
                target_intensities, target_roan,
            )
            affinity = game_state.get_affinity(male.id, female.id)
            affinity_bonus = min(affinity * BREEDING.AFFINITY_WEIGHT, BREEDING.MAX_AFFINITY_SELECTION_BONUS)
            score = prob + (affinity_bonus if prob > 0 else 0)
            if score > best_score:
                best_score = score
                best_pair = (male, female)

    if best_pair and best_score > 0:
        male, female = best_pair
        game_state.set_breeding_pair(male.id, female.id)
        prob = calculate_target_probability(
            male.genotype, female.genotype,
            target_colors, target_patterns,
            target_intensities, target_roan,
        )
        game_state.log_event(
            f"Breeding program paired {male.name} x {female.name} ({prob * 100:.1f}% target chance)",
            event_type="breeding",
        )


def _auto_pair_diversity(game_state: "BreedingContext", males: list[GuineaPig], females: list[GuineaPig]) -> None:
    """Pair pigs for maximum genetic distance and rare-color production."""
    all_pigs = game_state.get_pigs_list()

    # Find underrepresented colors: below average count, plus any absent colors
    color_counts: dict[BaseColor, int] = {}
    for pig in all_pigs:
        color = pig.phenotype.base_color
        color_counts[color] = color_counts.get(color, 0) + 1
    avg_count = len(all_pigs) / max(len(BaseColor), 1)
    underrepresented: set[BaseColor] = {
        color for color in BaseColor
        if color_counts.get(color, 0) < avg_count
    }

    best_pair = None
    best_score = -1.0
    for male in males:
        for female in females:
            score = _diversity_pair_score(male, female, underrepresented, game_state)
            if score > best_score:
                best_score = score
                best_pair = (male, female)

    if best_pair and best_score > 0:
        male, female = best_pair
        game_state.set_breeding_pair(male.id, female.id)
        game_state.log_event(
            f"Breeding program paired {male.name} x {female.name} (diversity score {best_score:.1f})",
            event_type="breeding",
        )


# Color-determining loci (from entities/genetics.py LOCUS_DEFINITIONS):
#   e_locus: eumelanin (E=black, e=golden)
#   b_locus: brown (B=black, b=chocolate)
#   d_locus: dilution (D=full, d=diluted)
# Pattern/intensity/roan loci are excluded because the problem being solved
# is specifically color dominance from biome-driven mutation pressure.
_COLOR_LOCI = ("e_locus", "b_locus", "d_locus")
_RARE_COLOR_WEIGHT = 5.0


def _diversity_pair_score(
    male: GuineaPig,
    female: GuineaPig,
    underrepresented: set[BaseColor],
    game_state: "BreedingContext",
) -> float:
    """Score a breeding pair for genetic distance and rare-color potential.

    Components:
    - Genetic distance (0-9): allele differences at color loci (e, b, d).
      Base distance = count of differing allele pairs (0-6), plus 0.5 bonus
      per locus where the allele *sets* differ (heterozygous vs homozygous).
    - Rare-color bonus: probability of producing underrepresented colors,
      scaled by _RARE_COLOR_WEIGHT.
    - Affinity bonus: existing social bond tiebreaker.
    """
    male_genotype = male.genotype
    female_genotype = female.genotype

    # Genetic distance at color loci
    distance = 0.0
    for locus_name in _COLOR_LOCI:
        male_alleles = getattr(male_genotype, locus_name)
        female_alleles = getattr(female_genotype, locus_name)
        # Count individual allele differences (0-2 per locus)
        for i in range(2):
            if male_alleles[i] != female_alleles[i]:
                distance += 1.0
        # Bonus if allele sets differ (one has variant the other doesn't)
        if set(male_alleles) != set(female_alleles):
            distance += 0.5

    # Rare-color production bonus
    rare_bonus = 0.0
    if underrepresented:
        prob = calculate_target_probability(
            male_genotype, female_genotype,
            underrepresented, set(), set(), set(),
        )
        rare_bonus = prob * _RARE_COLOR_WEIGHT

    # Affinity tiebreaker
    affinity = game_state.get_affinity(male.id, female.id)
    affinity_bonus = min(affinity * BREEDING.AFFINITY_WEIGHT, BREEDING.MAX_AFFINITY_SELECTION_BONUS)

    return distance + rare_bonus + affinity_bonus


def _derive_contract_targets(game_state: "BreedingContext") -> tuple[set, set, set, set]:
    """Derive implicit breeding targets from active contracts."""
    colors: set[BaseColor] = set()
    patterns: set[Pattern] = set()
    intensities: set[ColorIntensity] = set()
    roans: set[RoanType] = set()

    if not hasattr(game_state, "contract_board"):
        return colors, patterns, intensities, roans

    for contract in game_state.contract_board.active_contracts:
        if contract.fulfilled:
            continue
        if contract.required_color:
            colors.add(contract.required_color)
        if contract.required_pattern:
            patterns.add(contract.required_pattern)
        if contract.required_intensity:
            intensities.add(contract.required_intensity)
        if contract.required_roan:
            roans.add(contract.required_roan)

    return colors, patterns, intensities, roans
