"""Surplus breeder culling and auto-sell mechanics."""

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from big_pig_farm.game.facades import CullingContext

from big_pig_farm.data.config import BREEDING
from big_pig_farm.economy.market import sell_pig
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig
from big_pig_farm.simulation.breeding_program import (
    BreedingStrategy,
    breeding_value,
    build_diversity_counters,
    diversity_value,
    money_value,
    should_keep_pig,
)

# Minimum diversity score gap between best and worst adult to trigger
# active replacement.  Prevents oscillation when colors are already
# balanced (similar scores → gap < threshold → no replacement).
_DIVERSITY_REPLACEMENT_GAP = 2.0


def sell_marked_adults(
    game_state: "CullingContext",
) -> list[tuple[str, int, int, UUID]]:
    """Auto-sell pigs that were marked for sale and have reached adulthood.

    Returns list of (name, sale_total, contract_bonus, pig_id) for each pig sold.
    """
    sold = []
    for pig in game_state.get_pigs_list():
        if pig.marked_for_sale and not pig.is_baby:
            name = pig.name
            pig_id = pig.id
            result = sell_pig(game_state, pig)
            sold.append((name, result.total, result.contract_bonus, pig_id))
    return sold


def cull_surplus_breeders(game_state: "CullingContext") -> None:
    """Mark surplus pigs for sale when over the program's stock limit.

    Also performs active replacement: when at or below the stock limit,
    marks the single worst non-matching adult for sale so the farm
    turns over toward the target phenotype.
    """
    program = game_state.breeding_program
    if not program.enabled:
        return

    has_lab = bool(game_state.get_facilities_by_type(FacilityType.GENETICS_LAB))

    # Get all adult pigs not already marked for sale
    adults = [
        p for p in game_state.get_pigs_list()
        if not p.marked_for_sale and not p.is_baby
    ]

    effective_limit = max(program.stock_limit, BREEDING.MIN_BREEDING_POPULATION)
    if len(adults) < effective_limit:
        return  # Below limit — need more pigs, not fewer
    if len(adults) == effective_limit:
        _active_replacement(game_state, adults, program, has_lab)
        return

    scored = _score_adults(adults, program, has_lab, game_state)

    # Ensure gender balance: keep at least 1 male + 1 female in top N
    kept = []
    has_male = False
    has_female = False
    surplus = []

    for pig, score in scored:
        if len(kept) < effective_limit:
            kept.append(pig)
            if pig.gender == Gender.MALE:
                has_male = True
            else:
                has_female = True
        else:
            surplus.append(pig)

    # If missing a gender in kept, swap the worst kept with best surplus of needed gender
    if not has_male or not has_female:
        needed_gender = Gender.MALE if not has_male else Gender.FEMALE
        for pig in surplus:
            if pig.gender == needed_gender:
                # Swap: remove worst from kept, add this pig
                worst_kept = kept[-1]
                kept[-1] = pig
                surplus.remove(pig)
                surplus.append(worst_kept)
                break

    # Mark surplus for sale (skip pregnant pigs)
    marked_count = 0
    for pig in surplus:
        if pig.is_pregnant:
            continue
        pig.marked_for_sale = True
        marked_count += 1

    if marked_count:
        game_state.log_event(
            f"Breeding program: {marked_count} surplus pig(s) marked for sale",
            event_type="filter",
        )


def _score_adults(
    adults: list[GuineaPig],
    program,
    has_lab: bool,
    game_state: "CullingContext | None" = None,
) -> list[tuple[GuineaPig, tuple]]:
    """Score adult pigs by strategy-appropriate value.

    Returns a list of (pig, score_tuple) sorted best-first.
    """
    if program.strategy == BreedingStrategy.DIVERSITY:
        phenotype_counts, color_counts = build_diversity_counters(adults)
        scored = [
            (p, (diversity_value(p, adults, phenotype_counts, color_counts),
                 breeding_value(p, program, has_lab)))
            for p in adults
        ]
    elif program.strategy == BreedingStrategy.MONEY:
        scored = [
            (p, (money_value(p, program, has_lab, game_state),))
            for p in adults
        ]
    else:
        scored = [(p, (breeding_value(p, program, has_lab),)) for p in adults]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _would_break_gender_balance(pig: GuineaPig, adults: list[GuineaPig]) -> bool:
    """Return True if selling this pig would leave zero of its gender."""
    same_gender = [
        p for p in adults
        if p.gender == pig.gender and not p.marked_for_sale and p.id != pig.id
    ]
    return len(same_gender) == 0


def _active_replacement(game_state: "CullingContext", adults: list[GuineaPig], program, has_lab: bool) -> None:
    """Phase out the worst adult when at or below stock limit.

    Three modes:
    - With targets: sell the worst non-matching adult
    - Diversity (no targets): sell the worst-scoring adult only when the
      gap between best and worst diversity scores exceeds 2.0 points
      (prevents oscillation when colors are already balanced)
    - Money/Target (no targets): no replacement (surplus culling only)

    Marks at most 1 pig per call. Skips pregnant pigs and preserves
    gender balance (never sells the last male or last female).
    """
    if program.has_target:
        candidates = [
            p for p in adults
            if not should_keep_pig(program, p, has_genetics_lab=has_lab)
        ]
        reason = "non-matching"
    elif program.strategy == BreedingStrategy.DIVERSITY:
        # Score all adults; only replace if diversity gap is meaningful
        scored = _score_adults(adults, program, has_lab, game_state)
        best_score = scored[0][1]
        worst_score = scored[-1][1]
        gap = best_score[0] - worst_score[0]
        if gap < _DIVERSITY_REPLACEMENT_GAP:
            return  # Colors are balanced enough — no replacement needed
        candidates = [scored[-1][0]]
        reason = f"low diversity, gap {gap:.1f}"
    else:
        # Without targets, active replacement would sell the "worst" pig every
        # time population hits the limit, causing it to oscillate below the
        # stock limit permanently.  Only surplus culling (len > limit) should
        # fire for money/target mode without explicit targets.
        return

    if not candidates:
        return

    # Score candidates worst-first (diversity branch already has 1 candidate)
    scored = _score_adults(candidates, program, has_lab, game_state)
    scored.reverse()  # Worst first

    for pig, _score in scored:
        if pig.is_pregnant:
            continue
        if _would_break_gender_balance(pig, adults):
            continue
        pig.marked_for_sale = True
        game_state.log_event(
            f"Breeding program: replacing {pig.name} ({reason})",
            event_type="filter",
        )
        return
